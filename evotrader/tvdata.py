"""TradingView as a data source: symbol search and OHLCV history.

TradingView has no documented REST API for chart data.  Symbol search is a
plain HTTPS call, but bars arrive over the same WebSocket protocol the charts
themselves use: a session is opened, a symbol resolved, a series created, and
the server streams ``timescale_update`` messages until it says
``series_completed``.  Both are implemented here directly — a WebSocket client
is a hundred lines of framing, which is cheaper than a dependency for a package
that otherwise needs only numpy.

    bars = fetch_bars("NASDAQ:AAPL", "1D", 2000)
    universe = load_universe(["NASDAQ:AAPL", "NASDAQ:MSFT"], "1D", 2000)

An anonymous session is enough for recent history on most symbols.  To sign in,
``evotrader tv-login`` stores the browser's ``sessionid`` cookie for this user
only; ``TRADINGVIEW_SESSION`` and ``TRADINGVIEW_SESSION_SIGN`` override it where
a shell is doing the launching.  The cookie is not itself the socket's auth
token: it is exchanged for one, once, and the result cached for the process.
``TRADINGVIEW_AUTH_TOKEN`` supplies a token directly.  No credential is ever put
in an error message.

Bars are what TradingView serves for the symbol as asked: ``adjustment`` is set
to ``splits``, matching a default chart, so dividends are *not* reinjected the
way :mod:`evotrader.data` gets them from Yahoo.  Two sources, two conventions —
do not mix them inside one backtest.
"""
from __future__ import annotations

import base64
import json
import os
import random
import re
import socket
import ssl
import struct
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Sequence, Tuple

import numpy as np

from .data import Bars, DataError, Universe, align

DATA_HOST = "data.tradingview.com"
#: One series request tops out a few thousand bars short of a deep intraday
#: history; earlier bars come a page at a time.  Ten years of one-minute bars
#: is roughly 3.5 million of them, which is hundreds of pages — so the ceiling
#: is a time budget rather than a page count, and an account that is entitled
#: to the history is what decides how far it actually gets.
MAX_PAGES = 2_000
PAGE_SIZE = 20_000
MAX_BARS = 10_000_000
SEARCH_URL = "https://symbol-search.tradingview.com/symbol_search/v3/"
ORIGIN = "https://www.tradingview.com"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

#: TradingView resolutions, and how many of those bars a year holds.  The
#: intraday figures assume a 6.5-hour equity session; a 24/7 market trades more
#: of them, so annualised numbers there are conservative.
TIMEFRAMES: Dict[str, float] = {
    "1": 252 * 390, "3": 252 * 130, "5": 252 * 78, "15": 252 * 26,
    "30": 252 * 13, "45": 252 * 8.67, "60": 252 * 6.5, "120": 252 * 3.25,
    "180": 252 * 2.17, "240": 252 * 1.625, "1D": 252.0, "1W": 52.0, "1M": 12.0,
}

_ALIASES = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30", "45m": "45",
    "1h": "60", "2h": "120", "3h": "180", "4h": "240",
    "d": "1D", "1d": "1D", "daily": "1D",
    "w": "1W", "1w": "1W", "weekly": "1W",
    "mo": "1M", "1mo": "1M", "monthly": "1M",
}


class TradingViewError(DataError):
    """TradingView refused, or the socket did not produce a series."""


def normalise_timeframe(timeframe: str) -> str:
    """Accept ``4h``/``1d``/``D`` and return TradingView's own resolution."""
    tf = (timeframe or "1D").strip()
    if tf in TIMEFRAMES:
        return tf
    resolved = _ALIASES.get(tf.lower())
    if resolved:
        return resolved
    raise TradingViewError(f"unknown timeframe {timeframe!r}; "
                           f"try one of {', '.join(TIMEFRAMES)}")


def bars_per_year(timeframe: str) -> float:
    return TIMEFRAMES[normalise_timeframe(timeframe)]


def interval_seconds(timeframe: str) -> float:
    """How long one bar of this timeframe covers."""
    tf = normalise_timeframe(timeframe)
    if tf == "1D":
        return 86_400.0
    if tf == "1W":
        return 604_800.0
    if tf == "1M":
        return 2_592_000.0
    return float(tf) * 60.0


# ------------------------------------------------------------- symbol search

def search_symbols(text: str, *, exchange: str = "", limit: int = 20,
                   timeout: int = 20) -> List[Dict[str, str]]:
    """Resolve a ticker to the exchange-qualified symbols TradingView knows."""
    query = urllib.parse.urlencode({
        "text": text, "hl": "0", "lang": "en", "domain": "production",
        "exchange": exchange or "",
    })
    req = urllib.request.Request(
        f"{SEARCH_URL}?{query}",
        headers={"User-Agent": _UA, "Origin": ORIGIN, "Referer": ORIGIN + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - network, JSON, HTTP all land here
        raise TradingViewError(f"symbol search failed: {type(exc).__name__}: {exc}") from exc
    out: List[Dict[str, str]] = []
    for item in (payload.get("symbols") or [])[:limit]:
        ticker = _strip_tags(item.get("symbol", ""))
        venue = item.get("exchange", "") or item.get("source_id", "")
        out.append({
            "symbol": f"{venue}:{ticker}" if venue and ":" not in ticker else ticker,
            "ticker": ticker,
            "exchange": venue,
            "description": _strip_tags(item.get("description", "")),
            "type": item.get("type", ""),
            "currency": item.get("currency_code", ""),
        })
    return out


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


# ------------------------------------------------------------- authentication

ANONYMOUS_TOKEN = "unauthorized_user_token"
CREDENTIALS_ENV = "TRADINGVIEW_CREDENTIALS"
_TOKEN_CACHE: Dict[str, str] = {}
_AUTH_TOKEN_RE = re.compile(r'"auth_token"\s*:\s*"([^"]+)"')


def clear_auth_cache() -> None:
    _TOKEN_CACHE.clear()


def resolve_auth_token(session_id: str, *, sign: str = "",
                       timeout: float = 20.0) -> str:
    """Exchange a ``sessionid`` cookie for the socket's auth token.

    The chart feed does not take the cookie; it takes a token the web app holds
    for a signed-in user.  One authenticated page load carries it.
    """
    cached = _TOKEN_CACHE.get(session_id)
    if cached:
        return cached
    cookie = f"sessionid={session_id}"
    if sign:
        cookie += f"; sessionid_sign={sign}"
    req = urllib.request.Request(ORIGIN + "/", headers={
        "User-Agent": _UA, "Referer": ORIGIN + "/", "Cookie": cookie})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            page = resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - never let a cookie into the message
        raise TradingViewError(
            f"could not reach TradingView to exchange the session cookie: "
            f"{type(exc).__name__}") from None
    match = _AUTH_TOKEN_RE.search(page)
    token = match.group(1) if match else ""
    if not token or token == ANONYMOUS_TOKEN:
        raise TradingViewError(
            "TradingView did not accept the session cookie — it has expired or "
            "belongs to another device. Log in again and copy a fresh sessionid "
            "(and sessionid_sign) from the browser's cookies.")
    _TOKEN_CACHE[session_id] = token
    return token


def credentials_path() -> str:
    """Where a stored login lives, if one has been saved."""
    return os.environ.get(CREDENTIALS_ENV) or os.path.join(
        os.path.expanduser("~"), ".config", "evotrader", "tradingview.json")


def load_credentials() -> Tuple[Dict[str, str], str]:
    """Find a login, and say where it came from.

    The environment wins, but a desktop client does not inherit the shell it
    was never launched from, so a saved file is what actually works when an
    MCP client starts the server itself.
    """
    env = {
        "auth_token": os.environ.get("TRADINGVIEW_AUTH_TOKEN", ""),
        "sessionid": os.environ.get("TRADINGVIEW_SESSION", ""),
        "sessionid_sign": os.environ.get("TRADINGVIEW_SESSION_SIGN", ""),
    }
    if env["auth_token"] or env["sessionid"]:
        return {k: v for k, v in env.items() if v}, "environment"
    for path in (os.path.join(os.getcwd(), ".tradingview.json"),
                 credentials_path()):
        if not os.path.exists(path):
            continue
        try:
            with open(path) as fh:
                stored = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(stored, dict) and (stored.get("sessionid")
                                         or stored.get("auth_token")):
            return {k: str(v) for k, v in stored.items() if v}, f"file {path}"
    return {}, "none"


def save_credentials(sessionid: str, *, sign: str = "",
                     path: str = "") -> str:
    """Store a login for this user only (0600), never in the repo by default."""
    target = path or credentials_path()
    directory = os.path.dirname(os.path.abspath(target))
    if directory:
        os.makedirs(directory, mode=0o700, exist_ok=True)
    payload = {"sessionid": sessionid}
    if sign:
        payload["sessionid_sign"] = sign
    # Create with restrictive permissions before anything is written to it.
    handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w") as fh:
        json.dump(payload, fh)
    os.chmod(target, 0o600)
    return target


def forget_credentials(path: str = "") -> bool:
    target = path or credentials_path()
    if os.path.exists(target):
        os.remove(target)
        return True
    return False


def auth_token(session_token: str = "", *, sign: str = "",
               timeout: float = 20.0) -> Tuple[str, str]:
    """Return ``(token, how)`` — how being anonymous, token, session, or a file."""
    if session_token:
        return (resolve_auth_token(session_token, sign=sign, timeout=timeout),
                "session")
    stored, source = load_credentials()
    if stored.get("auth_token"):
        return stored["auth_token"], "token"
    session_id = stored.get("sessionid", "")
    if not session_id:
        return ANONYMOUS_TOKEN, "anonymous"
    token = resolve_auth_token(session_id,
                               sign=sign or stored.get("sessionid_sign", ""),
                               timeout=timeout)
    return token, "session" if source == "environment" else source


# ------------------------------------------------------------ websocket layer

class _WebSocket:
    """The slice of RFC 6455 this needs: text frames, masked, client side."""

    def __init__(self, sock: ssl.SSLSocket, pending: bytes = b""):
        self.sock = sock
        self._buf = pending

    def send(self, text: str) -> None:
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            header = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 65536:
            header = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else:
            header = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        self.sock.sendall(header + mask
                          + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _fill(self, want: int) -> bool:
        while len(self._buf) < want:
            chunk = self.sock.recv(65536)
            if not chunk:
                return False
            self._buf += chunk
        return True

    def frames(self) -> Iterator[str]:
        """Yield the payload of each text frame until the peer closes."""
        while True:
            if not self._fill(2):
                return
            opcode = self._buf[0] & 0x0F
            length = self._buf[1] & 0x7F
            offset = 2
            if length == 126:
                if not self._fill(4):
                    return
                length = struct.unpack("!H", self._buf[2:4])[0]
                offset = 4
            elif length == 127:
                if not self._fill(10):
                    return
                length = struct.unpack("!Q", self._buf[2:10])[0]
                offset = 10
            if not self._fill(offset + length):
                return
            payload = self._buf[offset:offset + length]
            self._buf = self._buf[offset + length:]
            if opcode == 0x8:            # close
                return
            if opcode == 0x9:            # ping -> pong
                self.sock.sendall(struct.pack("!BB", 0x8A, 0x80) + os.urandom(4))
                continue
            if opcode in (0x1, 0x0):
                yield payload.decode("utf-8", "replace")

    def close(self) -> None:
        try:
            self.sock.sendall(struct.pack("!BB", 0x88, 0x80) + os.urandom(4))
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


def _tcp_connect(host: str, port: int, timeout: float) -> socket.socket:
    """Open a socket, tunnelling through HTTPS_PROXY when one is set."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return socket.create_connection((host, port), timeout=timeout)
    parsed = urllib.parse.urlparse(proxy)
    sock = socket.create_connection(
        (parsed.hostname, parsed.port or 8080), timeout=timeout)
    request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
    if parsed.username:
        token = base64.b64encode(
            f"{parsed.username}:{parsed.password or ''}".encode()).decode()
        request += f"Proxy-Authorization: Basic {token}\r\n"
    sock.sendall((request + "\r\n").encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = sock.recv(4096)
        if not chunk:
            raise TradingViewError("proxy closed the connection during CONNECT")
        head += chunk
    status = head.split(b"\r\n", 1)[0].decode("latin-1")
    if " 200 " not in status:
        raise TradingViewError(f"proxy refused CONNECT: {status}")
    return sock


def open_socket(host: str = DATA_HOST, *, timeout: float = 30.0) -> _WebSocket:
    """TLS + the WebSocket upgrade handshake."""
    raw = _tcp_connect(host, 443, timeout)
    context = ssl.create_default_context()
    bundle = os.environ.get("SSL_CERT_FILE")
    if bundle and os.path.exists(bundle):
        context.load_verify_locations(bundle)
    sock = context.wrap_socket(raw, server_hostname=host)
    sock.settimeout(timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    handshake = (
        "GET /socket.io/websocket?from=chart%2F&type=chart HTTP/1.1\r\n"
        f"Host: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
        f"Origin: {ORIGIN}\r\nUser-Agent: {_UA}\r\n\r\n")
    sock.sendall(handshake.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise TradingViewError("connection closed during the WebSocket handshake")
        buf += chunk
    head, rest = buf.split(b"\r\n\r\n", 1)
    status = head.split(b"\r\n", 1)[0].decode("latin-1")
    if "101" not in status:
        raise TradingViewError(f"TradingView refused the WebSocket upgrade: {status}")
    return _WebSocket(sock, rest)


# --------------------------------------------------------- TradingView frames

def _frame(text: str) -> str:
    return f"~m~{len(text)}~m~{text}"


def _packet(method: str, params: Sequence[Any]) -> str:
    return _frame(json.dumps({"m": method, "p": list(params)},
                             separators=(",", ":")))


def _split_frames(raw: str) -> List[str]:
    """One WebSocket frame can carry several ``~m~<len>~m~`` packets."""
    out, pos = [], 0
    pattern = re.compile(r"~m~(\d+)~m~")
    while pos < len(raw):
        match = pattern.match(raw, pos)
        if not match:
            break
        length = int(match.group(1))
        start = match.end()
        out.append(raw[start:start + length])
        pos = start + length
    return out


def _session_id(prefix: str) -> str:
    return prefix + "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                            for _ in range(12))


def fetch_bars(symbol: str, timeframe: str = "1D", bars: int = 2000, *,
               session_token: str = "", timeout: float = 30.0,
               page_timeout: float = 15.0, drop_forming: bool = True,
               progress=None, socket_factory=open_socket) -> Bars:
    """Pull one symbol's OHLCV history from TradingView's chart feed.

    ``timeout`` is the budget for the whole pull, not one message: ten years of
    one-minute bars is millions of them and hundreds of pages, so a deep pull
    wants minutes, not seconds.  ``progress`` is called with the running bar
    count every tenth page.
    """
    resolution = normalise_timeframe(timeframe)
    count = max(10, min(int(bars), MAX_BARS))
    deadline = time.monotonic() + max(timeout, page_timeout * 4)
    token, _how = auth_token(session_token, timeout=timeout)
    ws = socket_factory(timeout=timeout)
    chart, series, sym_ref = _session_id("cs_"), "sds_1", "sds_sym_1"
    try:
        ws.send(_packet("set_auth_token", [token]))
        ws.send(_packet("chart_create_session", [chart, ""]))
        ws.send(_packet("resolve_symbol", [
            chart, sym_ref,
            "=" + json.dumps({"symbol": symbol, "adjustment": "splits"},
                             separators=(",", ":"))]))
        ws.send(_packet("create_series",
                        [chart, series, "s1", sym_ref, resolution, count, ""]))
        rows: Dict[int, List[float]] = {}
        _read_series(ws, series, rows, timeout=timeout)
        # One series tops out well short of a long intraday history, so ask for
        # earlier pages until the server stops adding bars.
        pages = 0
        while len(rows) < count and pages < MAX_PAGES:
            if time.monotonic() > deadline:
                break                      # a deep pull, but not an endless one
            before = len(rows)
            ws.send(_packet("request_more_data",
                            [chart, series, min(count - before, PAGE_SIZE)]))
            _read_series(ws, series, rows, timeout=page_timeout)
            if len(rows) <= before:
                break                      # the feed has nothing older to give
            pages += 1
            if progress is not None and pages % 10 == 0:
                progress(len(rows))
        points = [rows[i] for i in sorted(rows)]
    except OSError as exc:
        raise TradingViewError(
            f"lost the TradingView connection while reading {symbol!r}: "
            f"{type(exc).__name__}: {exc}") from exc
    finally:
        ws.close()
    if drop_forming and points:
        # The newest bar is the one still being traded; a backtest that fills on
        # it is trading a candle that has not closed.
        newest = float(points[-1][0])
        if time.time() - newest < interval_seconds(resolution):
            points = points[:-1]
    if not points:
        raise TradingViewError(
            f"TradingView returned no bars for {symbol!r} at {resolution}; "
            f"check the exchange prefix (for example NASDAQ:AAPL) and, for long "
            f"history, set TRADINGVIEW_SESSION")
    return _to_bars(symbol, resolution, points)


def _read_series(ws: _WebSocket, series: str, rows: Dict[int, List[float]], *,
                 timeout: float) -> Dict[int, List[float]]:
    """Collect ``timescale_update`` payloads into ``rows`` until the page ends.

    Bars are keyed by TradingView's own index, which runs negative into the
    past, so successive pages merge without overlapping or reordering.
    """
    deadline = time.monotonic() + timeout
    for raw in ws.frames():
        if time.monotonic() > deadline:
            raise TradingViewError("timed out waiting for TradingView bars")
        for packet in _split_frames(raw):
            if packet.startswith("~h~"):
                ws.send(_frame(packet))          # heartbeat, echoed verbatim
                continue
            try:
                message = json.loads(packet)
            except ValueError:
                continue
            name = message.get("m")
            if name in ("timescale_update", "du"):
                payload = message.get("p", [None, {}])[1] or {}
                for point in (payload.get(series) or {}).get("s", []):
                    values = point.get("v") or []
                    if len(values) >= 5:
                        rows[int(point.get("i", len(rows)))] = values
            elif name in ("series_completed", "series_loading"):
                if name == "series_completed":
                    return rows
            elif name in ("symbol_error", "series_error", "critical_error",
                          "protocol_error"):
                raise TradingViewError(
                    f"TradingView reported {name}: "
                    f"{json.dumps(message.get('p', []))[:200]}")
    return rows


def _to_bars(symbol: str, resolution: str, points: Sequence[Sequence[float]]) -> Bars:
    intraday = resolution not in ("1D", "1W", "1M")
    dates: List[str] = []
    cols: List[List[float]] = [[], [], [], [], []]
    for values in points:
        stamp = datetime.fromtimestamp(float(values[0]), tz=timezone.utc)
        dates.append(stamp.strftime("%Y-%m-%d %H:%M" if intraday else "%Y-%m-%d"))
        for col, value in zip(cols, values[1:6]):
            col.append(float(value))
        if len(values) < 6:                      # some feeds omit volume
            cols[4].append(0.0)
    return Bars(symbol.upper(), dates,
                *[np.asarray(c, dtype=float) for c in cols])


def load_universe(symbols: Sequence[str], timeframe: str = "1D",
                  bars: int = 2000, *, session_token: str = "",
                  min_bars: int = 250, timeout: float = 30.0,
                  fetch=fetch_bars) -> Universe:
    """Fetch several symbols and align them on their shared calendar."""
    if not symbols:
        raise TradingViewError("at least one symbol is required")
    loaded: Dict[str, Bars] = {}
    errors: List[str] = []
    for symbol in symbols:
        try:
            series = fetch(symbol, timeframe, bars, session_token=session_token,
                           timeout=timeout)
        except DataError as exc:
            errors.append(f"{symbol}: {exc}")
            continue
        if len(series) < min_bars:
            errors.append(f"{symbol}: only {len(series)} bars (need {min_bars})")
            continue
        loaded[series.symbol] = series
    if not loaded:
        raise TradingViewError("no symbols loaded from TradingView. "
                               + "; ".join(errors))
    universe = align(loaded)
    universe.warnings = errors
    return universe


# ------------------------------------------------------- scanner (HTTPS only)

SCANNER_URL = "https://scanner.tradingview.com/{market}/scan"

#: Columns worth having by name rather than by TradingView's spelling.
SCAN_FIELDS: Dict[str, str] = {
    "close": "close", "change": "change", "change_abs": "change_abs",
    "volume": "volume", "relative_volume": "relative_volume_10d_calc",
    "market_cap": "market_cap_basic", "pe": "price_earnings_ttm",
    "rsi": "RSI", "macd": "MACD.macd", "macd_signal": "MACD.signal",
    "sma20": "SMA20", "sma50": "SMA50", "sma200": "SMA200",
    "atr": "ATR", "volatility": "volatility.D",
    "perf_week": "Perf.W", "perf_month": "Perf.1M", "perf_ytd": "Perf.YTD",
    "gap": "gap", "sector": "sector", "name": "name",
    "description": "description", "exchange": "exchange",
    "recommendation": "Recommend.All",
}

#: Keeps a screen to real companies: no preferred shares, no second listings.
COMMON_STOCK_FILTERS = [
    {"left": "type", "operation": "equal", "right": "stock"},
    {"left": "is_primary", "operation": "equal", "right": True},
    {"left": "typespecs", "operation": "has", "right": ["common"]},
]


def _scan(payload: Dict[str, Any], *, market: str = "america",
          timeout: float = 20.0) -> List[Dict[str, Any]]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        SCANNER_URL.format(market=market), data=body,
        headers={"Content-Type": "application/json", "User-Agent": _UA,
                 "Origin": ORIGIN, "Referer": ORIGIN + "/"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - network, HTTP and JSON alike
        raise TradingViewError(
            f"the TradingView scanner refused the request: "
            f"{type(exc).__name__}: {exc}") from exc
    return parsed.get("data") or []


def _rows(raw: List[Dict[str, Any]], fields: Sequence[str]) -> List[Dict[str, Any]]:
    out = []
    for item in raw:
        values = item.get("d") or []
        row: Dict[str, Any] = {"symbol": item.get("s", "")}
        for name, value in zip(fields, values):
            row[name] = value
        out.append(row)
    return out


def quotes(symbols: Sequence[str], *, fields: Sequence[str] = (),
           market: str = "america", timeout: float = 20.0) -> List[Dict[str, Any]]:
    """Last price and the day's numbers for exchange-qualified symbols."""
    if not symbols:
        raise TradingViewError("at least one symbol is required")
    wanted = list(fields) or ["name", "description", "close", "change",
                              "change_abs", "volume", "market_cap"]
    unknown = [f for f in wanted if f not in SCAN_FIELDS]
    if unknown:
        raise TradingViewError(f"unknown field(s): {', '.join(unknown)}; "
                               f"available: {', '.join(sorted(SCAN_FIELDS))}")
    raw = _scan({"symbols": {"tickers": [s.upper() for s in symbols],
                             "query": {"types": []}},
                 "columns": [SCAN_FIELDS[f] for f in wanted]},
                market=market, timeout=timeout)
    return _rows(raw, wanted)


def screen(filters: Sequence[Dict[str, Any]], *, fields: Sequence[str] = (),
           sort_by: str = "market_cap", descending: bool = True,
           limit: int = 25, market: str = "america",
           common_stock_only: bool = True,
           timeout: float = 25.0) -> List[Dict[str, Any]]:
    """Scan a market for symbols matching conditions.

    ``filters`` are ``{"field": "rsi", "op": "less", "value": 35}`` — the field
    names of :data:`SCAN_FIELDS`, not TradingView's own spelling.
    """
    wanted = list(fields) or ["name", "description", "close", "change",
                              "rsi", "volume", "market_cap", "sector"]
    unknown = [f for f in wanted if f not in SCAN_FIELDS]
    if unknown:
        raise TradingViewError(f"unknown field(s): {', '.join(unknown)}; "
                               f"available: {', '.join(sorted(SCAN_FIELDS))}")
    built = list(COMMON_STOCK_FILTERS) if common_stock_only else []
    for f in filters:
        field = str(f.get("field", ""))
        if field not in SCAN_FIELDS:
            raise TradingViewError(f"unknown filter field {field!r}; "
                                   f"available: {', '.join(sorted(SCAN_FIELDS))}")
        op = str(f.get("op", "greater"))
        if op not in ("greater", "less", "egreater", "eless", "equal",
                      "nequal", "in_range", "above%", "below%"):
            raise TradingViewError(f"unknown operation {op!r}")
        built.append({"left": SCAN_FIELDS[field], "operation": op,
                      "right": f.get("value")})
    if sort_by not in SCAN_FIELDS:
        raise TradingViewError(f"cannot sort by {sort_by!r}")
    raw = _scan({
        "filter": built,
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [SCAN_FIELDS[f] for f in wanted],
        "sort": {"sortBy": SCAN_FIELDS[sort_by],
                 "sortOrder": "desc" if descending else "asc"},
        "range": [0, max(1, min(int(limit), 100))],
    }, market=market, timeout=timeout)
    return _rows(raw, wanted)


TECHNICAL_FIELDS = ["close", "change", "rsi", "macd", "macd_signal", "sma20",
                    "sma50", "sma200", "atr", "volatility", "perf_week",
                    "perf_month", "perf_ytd", "recommendation"]


def technicals(symbol: str, *, market: str = "america",
               timeout: float = 20.0) -> Dict[str, Any]:
    """TradingView's own indicator snapshot for one symbol."""
    rows = quotes([symbol], fields=TECHNICAL_FIELDS, market=market,
                  timeout=timeout)
    if not rows:
        raise TradingViewError(f"no data for {symbol!r} — check the exchange "
                               f"prefix, e.g. NASDAQ:AAPL")
    return rows[0]
