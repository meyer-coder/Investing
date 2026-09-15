"""TradingView screener: rule-based symbol universe selection.

The public ``scanner.tradingview.com`` endpoint (no key required) evaluates a
filter expression across a whole market and returns the matching symbols with
indicator and fundamental columns computed server-side.  That makes it a good
way to *choose what to evolve on* — the one input to a run that no amount of
backtesting rigour can fix.

What it is not is a source of history.  The scanner reports **current values
only**, so it cannot feed a backtest; bars still come from ``data.py``.  This
distinction has teeth: a screen run today describes today's market, and
selecting on it before backtesting an earlier window is look-ahead selection.
See :func:`Snapshot.lookahead_warning` — snapshots are stamped with their
capture date precisely so that mistake is detectable rather than silent.

The honest uses are forward selection (screen today, trade or paper-trade
forward), screening on slow-moving structural traits, and accumulating dated
snapshots until you have a point-in-time universe worth trusting.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence, Tuple

CACHE_DIR = os.environ.get("EVOTRADER_CACHE", os.path.join("data", "cache"))
UNIVERSE_DIR = os.environ.get("EVOTRADER_UNIVERSES", os.path.join("data", "universes"))

_SCANNER = "https://scanner.tradingview.com/{market}/scan"
_UA = "Mozilla/5.0 (compatible; evotrader/0.1)"

#: Markets the scanner accepts as a URL segment.
MARKETS = ("america", "crypto", "forex", "futures", "uk", "germany", "japan",
           "india", "canada", "australia")

#: Readable aliases for the TradingView column names worth asking for.
COLUMNS: Dict[str, str] = {
    "name":        "name",
    "description": "description",
    "base":        "base_currency",
    "price":       "close",
    "change":      "change",
    "volume":      "volume",
    "avg_volume":  "average_volume_90d_calc",
    "rel_volume":  "relative_volume_10d_calc",
    "mcap":        "market_cap_basic",
    "crypto_mcap": "market_cap_calc",
    "aum":         "aum",
    "rsi":         "RSI",
    "sma50":       "SMA50",
    "sma200":      "SMA200",
    "atr":         "ATR",
    "perf_ytd":    "Perf.YTD",
    "perf_y":      "Perf.Y",
    "volatility":  "Volatility.D",
    "beta":        "beta_1_year",
    "sector":      "sector",
    "industry":    "industry",
    "exchange":    "exchange",
    "type":        "type",
    "primary":     "is_primary",
}

#: Filter operations the scanner understands.
OPERATIONS = ("greater", "egreater", "less", "eless", "equal", "nequal",
              "in_range", "not_in_range", "match", "crosses")

_DEFAULT_COLUMNS = ("name", "description", "price", "mcap", "avg_volume",
                    "rel_volume", "rsi", "sma200", "perf_y", "sector", "type")


class ScreenerError(RuntimeError):
    pass


def resolve_column(name: str) -> str:
    """Map a friendly alias to a TradingView column, passing through unknowns.

    Unknown names are forwarded verbatim so the full column vocabulary stays
    reachable without this module having to enumerate it.
    """
    return COLUMNS.get(name, name)


@dataclass(frozen=True)
class Filter:
    """One screener predicate, e.g. ``Filter("mcap", "greater", 1e10)``."""

    column: str
    operation: str
    value: Any = None

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise ScreenerError(
                f"unknown operation {self.operation!r}; choose from {', '.join(OPERATIONS)}")

    def payload(self) -> Dict[str, Any]:
        return {"left": resolve_column(self.column),
                "operation": self.operation,
                "right": self.value}

    @classmethod
    def parse(cls, text: str) -> "Filter":
        """Parse ``"mcap > 10e9"`` / ``"sector = Technology"`` from the CLI."""
        symbols = [(">=", "egreater"), ("<=", "eless"), ("!=", "nequal"),
                   (">", "greater"), ("<", "less"), ("=", "equal")]
        for token, op in symbols:
            if token in text:
                left, right = text.split(token, 1)
                return cls(left.strip(), op, _coerce(right.strip()))
        raise ScreenerError(
            f"could not parse filter {text!r}; expected something like 'mcap > 10e9'")


def _coerce(raw: str) -> Any:
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return float(raw) if ("." in raw or "e" in low) else int(raw)
    except ValueError:
        return raw


@dataclass
class Screen:
    """A named, reproducible screen definition."""

    name: str = "custom"
    market: str = "america"
    filters: List[Filter] = field(default_factory=list)
    columns: Sequence[str] = _DEFAULT_COLUMNS
    sort_by: str = "mcap"
    sort_order: str = "desc"
    limit: int = 50
    #: Column to collapse duplicates on, keeping the best-sorted row.  Crypto
    #: lists the same coin on every venue, so a raw scan is mostly repeats.
    dedupe: str | None = None

    def payload(self) -> Dict[str, Any]:
        return {
            "filter": [f.payload() for f in self.filters],
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": [resolve_column(c) for c in self.columns],
            "sort": {"sortBy": resolve_column(self.sort_by),
                     "sortOrder": self.sort_order},
            "range": [0, self._fetch_size()],
        }

    def _fetch_size(self) -> int:
        """Rows to request: over-fetch when duplicates will be collapsed."""
        limit = max(1, int(self.limit))
        return min(limit * 8, 500) if self.dedupe else limit

    def fingerprint(self) -> str:
        blob = json.dumps({"market": self.market, **self.payload()}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class Snapshot:
    """The result of one screen, stamped with when it was taken."""

    screen: str
    market: str
    captured_at: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_matches: int = 0

    @property
    def symbols(self) -> List[str]:
        """Bare tickers, in scan order, suitable for ``load_universe``."""
        return [r["symbol"] for r in self.rows]

    def lookahead_warning(self, start: str) -> str | None:
        """Explain the selection bias when backtesting from before capture.

        A universe chosen on today's market and tested on an earlier window
        embeds the outcome in the selection.  The run will happily produce a
        number; this is the sentence that says what the number is worth.
        """
        if start >= self.captured_at[:10]:
            return None
        return (f"universe '{self.screen}' was screened on {self.captured_at[:10]} but the "
                f"backtest starts {start}. Symbols were selected using data from after the "
                f"test window, so results carry survivorship and look-ahead bias — treat "
                f"them as a hypothesis, not a measurement.")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, directory: str = UNIVERSE_DIR) -> str:
        """Write the snapshot, dated, so universes accumulate point-in-time."""
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{self.screen}-{self.captured_at[:10]}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
        return path

    @classmethod
    def load(cls, path: str) -> "Snapshot":
        with open(path, encoding="utf-8") as fh:
            return cls(**json.load(fh))


def _post(url: str, payload: Dict[str, Any], *, timeout: float,
          retries: int, backoff: float, rng: random.Random) -> Dict[str, Any]:
    """POST with bounded retries.

    The scanner intermittently answers a valid request with an empty body, so
    a short read is retried rather than raised.  Jitter keeps concurrent
    callers from resynchronising into a retry storm.
    """
    body = json.dumps(payload).encode()
    headers = {"User-Agent": _UA, "Content-Type": "application/json",
               "Origin": "https://www.tradingview.com",
               "Referer": "https://www.tradingview.com/"}
    last = "no attempt made"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            if not raw.strip():
                last = "empty response body"
            else:
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):  # a bad query will not become good
                raise ScreenerError(f"scanner rejected the query ({exc.code})") from exc
            last = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = f"{type(exc).__name__}: {exc}"
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt) * rng.uniform(0.8, 1.2))
    raise ScreenerError(f"scanner unreachable after {retries} attempts ({last})")


def _cache_path(screen: Screen) -> str:
    return os.path.join(CACHE_DIR, "screener", f"{screen.fingerprint()}.json")


def run_screen(screen: Screen, *, timeout: float = 20.0, retries: int = 4,
               backoff: float = 0.5, cache_ttl: float = 900.0,
               refresh: bool = False, seed: int | None = None) -> Snapshot:
    """Execute a screen and return a dated snapshot.

    Results are cached on disk for ``cache_ttl`` seconds, keyed by the exact
    query, so repeated calls during a session cost nothing.
    """
    if screen.market not in MARKETS:
        raise ScreenerError(
            f"unknown market {screen.market!r}; try one of {', '.join(MARKETS)}")

    path = _cache_path(screen)
    if not refresh and cache_ttl > 0 and os.path.exists(path):
        if time.time() - os.path.getmtime(path) < cache_ttl:
            return Snapshot.load(path)

    rng = random.Random(seed)
    data = _post(_SCANNER.format(market=screen.market), screen.payload(),
                 timeout=timeout, retries=retries, backoff=backoff, rng=rng)
    snapshot = _to_snapshot(screen, data)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snapshot.to_dict(), fh)
    return snapshot


def _to_snapshot(screen: Screen, data: Dict[str, Any]) -> Snapshot:
    columns = list(screen.columns)
    rows: List[Dict[str, Any]] = []
    for entry in data.get("data") or []:
        ticker = entry.get("s", "")
        exchange, _, symbol = ticker.partition(":")
        row: Dict[str, Any] = {"symbol": symbol or ticker, "exchange": exchange}
        row.update(dict(zip(columns, entry.get("d") or [])))
        rows.append(row)
    if screen.dedupe:
        seen: set = set()
        unique = []
        for row in rows:
            key = row.get(screen.dedupe)
            if key is None or key in seen:
                continue
            seen.add(key)
            unique.append(row)
        rows = unique
    rows = rows[:max(1, int(screen.limit))]
    return Snapshot(
        screen=screen.name,
        market=screen.market,
        captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        columns=columns,
        rows=rows,
        total_matches=int(data.get("totalCount") or len(rows)),
    )


# ─── Presets ──────────────────────────────────────────────────────────────────
# Screens worth having by name.  Each is a starting point to edit, not a
# recommendation; the filters encode liquidity and tradability, which is what
# a backtest's fill assumptions actually depend on.

def _common_stock() -> List[Filter]:
    return [Filter("type", "equal", "stock"), Filter("primary", "equal", True)]


PRESETS: Dict[str, Screen] = {
    "liquid-large-cap": Screen(
        name="liquid-large-cap",
        filters=_common_stock() + [Filter("mcap", "greater", 10e9),
                                   Filter("avg_volume", "greater", 2e6)],
        sort_by="mcap", limit=50),
    "liquid-mid-cap": Screen(
        name="liquid-mid-cap",
        filters=_common_stock() + [Filter("mcap", "in_range", [2e9, 10e9]),
                                   Filter("avg_volume", "greater", 1e6)],
        sort_by="avg_volume", limit=50),
    "high-volatility": Screen(
        name="high-volatility",
        filters=_common_stock() + [Filter("mcap", "greater", 2e9),
                                   Filter("avg_volume", "greater", 2e6),
                                   Filter("volatility", "greater", 3.0)],
        sort_by="volatility", limit=50),
    # Sorting funds by assets rather than volume matters: the most-traded
    # ETFs are leveraged and inverse products, which a long-only daily
    # backtest has no business holding.  AUM surfaces the plain index funds.
    "etf-liquid": Screen(
        name="etf-liquid",
        filters=[Filter("type", "equal", "fund"),
                 Filter("avg_volume", "greater", 1e6)],
        columns=("name", "description", "price", "aum", "avg_volume", "rsi",
                 "sma200", "perf_y"),
        sort_by="aum", limit=40),
    "crypto-major": Screen(
        name="crypto-major", market="crypto",
        filters=[Filter("crypto_mcap", "greater", 1e9)],
        columns=("base", "name", "price", "change", "crypto_mcap", "rsi", "perf_y"),
        sort_by="crypto_mcap", dedupe="base", limit=25),
}


#: Yahoo quotes crypto as ``BTC-USD``; TradingView names the base currency.
def yahoo_symbols(snapshot: "Snapshot") -> List[str]:
    """Snapshot tickers translated into symbols ``data.py`` can fetch.

    Equities pass through unchanged.  Crypto is rewritten from the base
    currency, which is why ``crypto-major`` asks for that column.
    """
    if snapshot.market != "crypto":
        return snapshot.symbols
    out = []
    for row in snapshot.rows:
        base = row.get("base")
        out.append(f"{base}-USD" if base else row["symbol"])
    return out


def quote_screen(symbols: Sequence[str], *, market: str = "america",
                 columns: Sequence[str] | None = None) -> Screen:
    """A screen that reports current values for named tickers.

    ``in_range`` on a string column behaves as set membership, which is how
    the scanner is asked about a specific list rather than a whole market.
    Crypto keys on the base currency and lists each coin once per venue, so
    it matches on ``base`` and collapses the repeats; ``BTC-USD`` and ``BTC``
    are both accepted there.
    """
    tickers = [s.strip().upper() for s in symbols if s.strip()]
    if not tickers:
        raise ScreenerError("no symbols given")
    if market == "crypto":
        tickers = [t[:-4] if t.endswith("-USD") else t for t in tickers]
        return Screen(name="quote", market=market,
                      filters=[Filter("base", "in_range", tickers)],
                      columns=columns or ("base", "name", "price", "change",
                                          "crypto_mcap", "rsi"),
                      sort_by="crypto_mcap", dedupe="base", limit=len(tickers))
    return Screen(name="quote", market=market,
                  filters=[Filter("name", "in_range", tickers)],
                  columns=columns or ("name", "price", "change", "volume",
                                      "rsi", "sma50", "sma200"),
                  sort_by="name", sort_order="asc", limit=len(tickers) * 4)


def preset(name: str) -> Screen:
    if name not in PRESETS:
        raise ScreenerError(
            f"unknown preset {name!r}; choose from {', '.join(sorted(PRESETS))}")
    return PRESETS[name]
