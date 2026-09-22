"""The TradingView client: WebSocket framing, the chart protocol, symbol search.

The live feed is not reachable from a test run, so the socket is stubbed with
recorded frames — which is also the only way to test the parts that matter:
partial series, heartbeats, and the error messages TradingView sends instead of
data.
"""
import io
import json
import socket
import struct
import time

import pytest

from evotrader.data import DataError
from evotrader import tvdata
from evotrader.tvdata import (TradingViewError, _frame, _packet, _split_frames,
                              _to_bars, _WebSocket, bars_per_year, fetch_bars,
                              load_universe, normalise_timeframe, search_symbols)


# ------------------------------------------------------------------ framing

def test_timeframe_aliases():
    assert normalise_timeframe("4h") == "240"
    assert normalise_timeframe("1d") == "1D"
    assert normalise_timeframe("weekly") == "1W"
    assert normalise_timeframe("1D") == "1D"
    assert bars_per_year("1D") == 252.0
    assert bars_per_year("1h") > bars_per_year("1D")


def test_unknown_timeframe_names_the_valid_ones():
    with pytest.raises(TradingViewError) as exc:
        normalise_timeframe("fortnightly")
    assert "1D" in str(exc.value)


def test_packet_framing_round_trips():
    packet = _packet("set_auth_token", ["tok"])
    assert packet.startswith("~m~")
    body = _split_frames(packet)[0]
    assert json.loads(body) == {"m": "set_auth_token", "p": ["tok"]}


def test_several_packets_in_one_frame():
    raw = _frame("~h~7") + _packet("series_completed", ["cs"])
    parts = _split_frames(raw)
    assert parts[0] == "~h~7"
    assert json.loads(parts[1])["m"] == "series_completed"


def test_split_frames_ignores_trailing_garbage():
    assert _split_frames("~m~2~m~hi!!!trailing") == ["hi"]
    assert _split_frames("nonsense") == []


def test_to_bars_formats_daily_and_intraday():
    points = [[1700000000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    daily = _to_bars("NASDAQ:AAPL", "1D", points)
    assert daily.dates == ["2023-11-14"] and daily.symbol == "NASDAQ:AAPL"
    assert float(daily.close[0]) == 1.5 and float(daily.volume[0]) == 100.0
    intraday = _to_bars("NASDAQ:AAPL", "60", points)
    assert intraday.dates[0].startswith("2023-11-14 ")


def test_to_bars_tolerates_a_missing_volume():
    bars = _to_bars("X", "1D", [[1700000000, 1.0, 2.0, 0.5, 1.5]])
    assert float(bars.volume[0]) == 0.0


# ------------------------------------------------- websocket frames on a pipe

def _read_one_frame(sock):
    """Decode a single client frame straight off the wire."""
    head = sock.recv(2)
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", sock.recv(8))[0]
    mask = sock.recv(4)
    payload = b""
    while len(payload) < length:
        payload += sock.recv(length - len(payload))
    assert head[0] == 0x81 and head[1] & 0x80, "client frames must be masked text"
    return bytes(b ^ mask[i % 4] for i, b in enumerate(payload)).decode()


def _server_frame(text):
    payload = text.encode()
    n = len(payload)
    if n < 126:
        return struct.pack("!BB", 0x81, n) + payload
    return struct.pack("!BBH", 0x81, 126, n) + payload


def test_client_frames_are_masked_and_server_frames_parse():
    a, b = socket.socketpair()
    try:
        ws = _WebSocket(a)
        ws.send("hello")
        assert _read_one_frame(b) == "hello"
        long_text = "x" * 300                     # crosses into 16-bit lengths
        ws.send(long_text)
        assert _read_one_frame(b) == long_text
        b.sendall(_server_frame("one") + _server_frame(long_text))
        b.sendall(struct.pack("!BB", 0x88, 0))    # close
        assert list(ws.frames()) == ["one", long_text]
    finally:
        a.close()
        b.close()


# --------------------------------------------------------- the chart protocol

class FakeSocket:
    """Replays recorded server frames and records what the client sent."""

    def __init__(self, frames):
        # One continuous stream, as a socket is: reading twice must not rewind.
        self._stream = iter(list(frames))
        self.sent = []
        self.closed = False

    def send(self, text):
        self.sent.append(text)

    def frames(self):
        for frame in self._stream:
            yield frame

    def close(self):
        self.closed = True

    def methods(self):
        out = []
        for packet in self.sent:
            for part in _split_frames(packet):
                try:
                    out.append(json.loads(part)["m"])
                except (ValueError, KeyError):
                    out.append(part)
        return out


def _timescale(series, points):
    return _packet("timescale_update", ["cs", {series: {"s": [
        {"i": i, "v": v} for i, v in enumerate(points)]}}])


def _factory(frames):
    return lambda **kwargs: FakeSocket(frames)


def test_fetch_bars_reads_a_series():
    points = [[1700000000 + i * 86400, 1.0 + i, 2.0 + i, 0.5 + i, 1.5 + i, 10.0]
              for i in range(3)]
    fake = FakeSocket([_timescale("sds_1", points),
                       _packet("series_completed", ["cs"])])
    bars = fetch_bars("NASDAQ:AAPL", "1D", 500, socket_factory=lambda **k: fake)
    assert len(bars) == 3 and bars.dates[0] == "2023-11-14"
    assert float(bars.close[-1]) == 3.5
    assert fake.methods()[:4] == ["set_auth_token", "chart_create_session",
                                  "resolve_symbol", "create_series"]
    assert fake.closed is True


def test_fetch_bars_echoes_heartbeats():
    points = [[1700000000, 1.0, 2.0, 0.5, 1.5, 10.0]] * 2
    fake = FakeSocket([_frame("~h~3"), _timescale("sds_1", points),
                       _packet("series_completed", ["cs"])])
    fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)
    assert "~h~3" in fake.methods(), "the server drops clients that stop answering"


def test_fetch_bars_merges_updates_arriving_in_pieces():
    first = [[1700000000, 1.0, 2.0, 0.5, 1.5, 10.0]]
    fake = FakeSocket([
        _timescale("sds_1", first),
        _packet("timescale_update", ["cs", {"sds_1": {"s": [
            {"i": 1, "v": [1700086400, 2.0, 3.0, 1.5, 2.5, 20.0]}]}}]),
        _packet("series_completed", ["cs"])])
    bars = fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)
    assert len(bars) == 2 and float(bars.close[-1]) == 2.5


def test_fetch_bars_reports_a_symbol_error():
    fake = FakeSocket([_packet("symbol_error", ["cs", "sds_sym_1", "invalid symbol"])])
    with pytest.raises(TradingViewError) as exc:
        fetch_bars("NOPE:NOPE", "1D", 100, socket_factory=lambda **k: fake)
    assert "symbol_error" in str(exc.value)


def test_fetch_bars_explains_an_empty_series():
    fake = FakeSocket([_packet("series_completed", ["cs"])])
    with pytest.raises(TradingViewError) as exc:
        fetch_bars("NASDAQ:AAPL", "1D", 100, socket_factory=lambda **k: fake)
    assert "TRADINGVIEW_SESSION" in str(exc.value)


def test_a_session_token_argument_is_exchanged_before_use(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: _Response(
                            b'{"user": {"auth_token": "exchanged-token"}}'))
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    fetch_bars("X", "1D", 100, session_token="secret-cookie",
               socket_factory=lambda **k: fake)
    auth = json.loads(_split_frames(fake.sent[0])[0])
    assert auth["p"] == ["exchanged-token"]
    assert "secret-cookie" not in fake.sent[0]


def test_fetch_bars_uses_an_anonymous_token_by_default(monkeypatch):
    monkeypatch.delenv("TRADINGVIEW_SESSION", raising=False)
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)
    assert json.loads(_split_frames(fake.sent[0])[0])["p"] == ["unauthorized_user_token"]


def test_resolve_symbol_asks_for_split_adjusted_bars():
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    fetch_bars("NASDAQ:AAPL", "4h", 100, socket_factory=lambda **k: fake)
    resolve = json.loads(_split_frames(fake.sent[2])[0])
    assert json.loads(resolve["p"][2][1:]) == {"symbol": "NASDAQ:AAPL",
                                               "adjustment": "splits"}
    series = json.loads(_split_frames(fake.sent[3])[0])
    assert series["p"][4] == "240"            # the alias was resolved


# -------------------------------------------------------------- symbol search

class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_search_symbols_parses_and_strips_markup(monkeypatch):
    payload = {"symbols": [
        {"symbol": "<em>AAPL</em>", "description": "<em>Apple</em> Inc.",
         "exchange": "NASDAQ", "type": "stock", "currency_code": "USD"}]}
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: _Response(json.dumps(payload).encode()))
    found = search_symbols("aapl")
    assert found[0] == {"symbol": "NASDAQ:AAPL", "ticker": "AAPL",
                        "exchange": "NASDAQ", "description": "Apple Inc.",
                        "type": "stock", "currency": "USD"}


def test_search_symbols_wraps_network_failures(monkeypatch):
    def boom(*a, **k):
        raise OSError("connection reset")
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", boom)
    with pytest.raises(TradingViewError) as exc:
        search_symbols("aapl")
    assert "symbol search failed" in str(exc.value)


# ------------------------------------------------------------------ universe

def _bars_for(symbol, timeframe, count, **kwargs):
    from evotrader.data import synthetic_bars
    bars = synthetic_bars(symbol, 400)
    bars.symbol = symbol.upper()
    return bars


def test_load_universe_aligns_symbols():
    universe = load_universe(["NASDAQ:AAPL", "NASDAQ:MSFT"], "1D", 400,
                             fetch=_bars_for, min_bars=100)
    assert universe.symbols == ["NASDAQ:AAPL", "NASDAQ:MSFT"]
    assert len(universe) == 400


def test_load_universe_skips_short_symbols_but_keeps_going():
    def fetch(symbol, timeframe, count, **kwargs):
        if symbol == "SHORT":
            from evotrader.data import synthetic_bars
            bars = synthetic_bars("SHORT", 20)
            bars.symbol = "SHORT"
            return bars
        return _bars_for(symbol, timeframe, count)
    universe = load_universe(["NASDAQ:AAPL", "SHORT"], "1D", 400, fetch=fetch,
                             min_bars=100)
    assert universe.symbols == ["NASDAQ:AAPL"]
    assert any("SHORT" in w for w in universe.warnings)


def test_load_universe_reports_why_nothing_loaded():
    def fetch(symbol, timeframe, count, **kwargs):
        raise DataError("no such symbol")
    with pytest.raises(TradingViewError) as exc:
        load_universe(["NOPE"], "1D", 400, fetch=fetch)
    assert "no such symbol" in str(exc.value)


def test_load_universe_needs_symbols():
    with pytest.raises(TradingViewError):
        load_universe([], "1D", 400, fetch=_bars_for)


def test_the_session_token_never_appears_in_an_error():
    """A credential in an error message ends up in logs and transcripts."""
    fake = FakeSocket([_packet("critical_error", ["cs", "bad session"])])
    with pytest.raises(TradingViewError) as exc:
        fetch_bars("X", "1D", 100, session_token="super-secret-cookie",
                   socket_factory=lambda **k: fake)
    assert "super-secret-cookie" not in str(exc.value)


def test_a_dropped_connection_is_reported_as_a_tradingview_error():
    class Dropping(FakeSocket):
        def frames(self):
            raise ConnectionResetError("connection reset by peer")

    with pytest.raises(TradingViewError) as exc:
        fetch_bars("X", "1D", 100, socket_factory=lambda **k: Dropping([]))
    assert "lost the TradingView connection" in str(exc.value)


# ------------------------------------------------------------- authentication

@pytest.fixture(autouse=True)
def _no_ambient_credentials(monkeypatch):
    for name in ("TRADINGVIEW_SESSION", "TRADINGVIEW_SESSION_SIGN",
                 "TRADINGVIEW_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    tvdata.clear_auth_cache()


def _page(token="tv-auth-token-abc123"):
    return _Response(json.dumps({"user": {"auth_token": token}}).encode())


def test_anonymous_by_default():
    assert tvdata.auth_token() == ("unauthorized_user_token", "anonymous")


def test_an_explicit_token_is_used_as_is(monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_AUTH_TOKEN", "given-token")
    assert tvdata.auth_token() == ("given-token", "token")


def test_a_session_cookie_is_exchanged_for_an_auth_token(monkeypatch):
    seen = {}

    def urlopen(req, *a, **k):
        seen["cookie"] = req.headers.get("Cookie")
        return _page()

    monkeypatch.setattr(tvdata.urllib.request, "urlopen", urlopen)
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    monkeypatch.setenv("TRADINGVIEW_SESSION_SIGN", "signature-value")
    token, how = tvdata.auth_token()
    assert (token, how) == ("tv-auth-token-abc123", "session")
    assert seen["cookie"] == "sessionid=cookie-value; sessionid_sign=signature-value"


def test_the_exchange_happens_once_per_process(monkeypatch):
    calls = []
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: (calls.append(1), _page())[1])
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    assert tvdata.auth_token()[0] == tvdata.auth_token()[0]
    assert len(calls) == 1


def test_an_expired_cookie_says_so(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: _Response(b"<html>signed out</html>"))
    monkeypatch.setenv("TRADINGVIEW_SESSION", "stale-cookie")
    with pytest.raises(TradingViewError) as exc:
        tvdata.auth_token()
    assert "expired" in str(exc.value)
    assert "stale-cookie" not in str(exc.value)


def test_an_anonymous_token_in_the_page_counts_as_not_signed_in(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: _page("unauthorized_user_token"))
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    with pytest.raises(TradingViewError):
        tvdata.auth_token()


def test_a_network_failure_during_exchange_hides_the_cookie(monkeypatch):
    def boom(*a, **k):
        raise OSError("connect failed for sessionid=cookie-value")
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", boom)
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    with pytest.raises(TradingViewError) as exc:
        tvdata.auth_token()
    assert "cookie-value" not in str(exc.value)


def test_fetch_bars_sends_the_exchanged_token_not_the_cookie(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", lambda *a, **k: _page())
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)
    sent = json.loads(_split_frames(fake.sent[0])[0])
    assert sent["p"] == ["tv-auth-token-abc123"]
    assert "cookie-value" not in fake.sent[0]


def test_more_history_is_requested_a_page_at_a_time():
    """One series request is shallow; earlier bars are paged in."""
    first = [[1700000000 + i * 300, 1, 2, 0.5, 1.5, 1] for i in range(3)]
    earlier = _packet("timescale_update", ["cs", {"sds_1": {"s": [
        {"i": -2, "v": [1699000000, 1, 2, 0.5, 1.4, 1]},
        {"i": -1, "v": [1699000300, 1, 2, 0.5, 1.45, 1]}]}}])
    fake = FakeSocket([_timescale("sds_1", first),
                       _packet("series_completed", ["cs"]),
                       earlier, _packet("series_completed", ["cs"]),
                       _packet("series_completed", ["cs"])])
    bars = fetch_bars("X", "5", 5, socket_factory=lambda **k: fake)
    assert "request_more_data" in fake.methods()
    assert len(bars) == 5
    assert bars.dates == sorted(bars.dates), "paged bars must stay in time order"
    assert float(bars.close[0]) == 1.4      # the earliest page sorts first


def test_paging_stops_when_the_server_stops_adding_bars():
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"]),
                       _packet("series_completed", ["cs"])])
    bars = fetch_bars("X", "1D", 5000, socket_factory=lambda **k: fake)
    assert len(bars) == 1
    assert fake.methods().count("request_more_data") == 1, "one try, then give up"


def test_the_still_forming_bar_is_dropped():
    """Filling on a candle that has not closed is trading the future."""
    now = int(time.time())
    points = [[now - 7200, 1, 2, 0.5, 1.5, 1],      # closed hours ago
              [now - 60, 2, 3, 1.5, 2.5, 1]]        # this minute, still open
    fake = FakeSocket([_timescale("sds_1", points),
                       _packet("series_completed", ["cs"])])
    bars = fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)
    assert len(bars) == 1 and float(bars.close[0]) == 1.5


def test_closed_bars_are_kept():
    old = int(time.time()) - 86_400 * 5
    fake = FakeSocket([_timescale("sds_1", [[old, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    assert len(fetch_bars("X", "1D", 100, socket_factory=lambda **k: fake)) == 1


def test_interval_seconds_matches_the_timeframe():
    from evotrader.tvdata import interval_seconds
    assert interval_seconds("1D") == 86_400
    assert interval_seconds("4h") == 14_400
    assert interval_seconds("5") == 300


# -------------------------------------------------------- stored credentials

def test_a_stored_file_is_used_when_the_environment_is_empty(tmp_path, monkeypatch):
    """An MCP client starts the server itself and inherits no shell exports."""
    path = tmp_path / "tradingview.json"
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    tvdata.save_credentials("cookie-from-file", sign="sig", path=str(path))
    stored, source = tvdata.load_credentials()
    assert stored["sessionid"] == "cookie-from-file"
    assert stored["sessionid_sign"] == "sig"
    assert source.startswith("file ")


def test_the_credentials_file_is_not_world_readable(tmp_path, monkeypatch):
    import stat
    path = tmp_path / "tradingview.json"
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    tvdata.save_credentials("secret", path=str(path))
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"a credential readable by others: {oct(mode)}"


def test_the_environment_wins_over_a_stored_file(tmp_path, monkeypatch):
    path = tmp_path / "tradingview.json"
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    tvdata.save_credentials("from-file", path=str(path))
    monkeypatch.setenv("TRADINGVIEW_SESSION", "from-env")
    stored, source = tvdata.load_credentials()
    assert stored["sessionid"] == "from-env" and source == "environment"


def test_a_stored_login_is_exchanged_like_any_other(tmp_path, monkeypatch):
    path = tmp_path / "tradingview.json"
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    tvdata.save_credentials("cookie-from-file", path=str(path))
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", lambda *a, **k: _page())
    token, how = tvdata.auth_token()
    assert token == "tv-auth-token-abc123" and how.startswith("file ")


def test_a_corrupt_credentials_file_falls_back_to_anonymous(tmp_path, monkeypatch):
    path = tmp_path / "tradingview.json"
    path.write_text("{not json")
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    assert tvdata.load_credentials() == ({}, "none")
    assert tvdata.auth_token()[1] == "anonymous"


def test_forgetting_a_login(tmp_path, monkeypatch):
    path = tmp_path / "tradingview.json"
    monkeypatch.setenv("TRADINGVIEW_CREDENTIALS", str(path))
    tvdata.save_credentials("secret", path=str(path))
    assert tvdata.forget_credentials(str(path)) is True
    assert tvdata.forget_credentials(str(path)) is False
    assert tvdata.load_credentials() == ({}, "none")


# --------------------------------------------------------------- the scanner

def _scan_response(payload):
    return _Response(json.dumps(payload).encode())


def test_quotes_map_columns_back_to_names(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", lambda *a, **k: _scan_response(
        {"totalCount": 1, "data": [{"s": "NASDAQ:AAPL",
                                    "d": ["AAPL", "Apple Inc.", 336.13, -0.25,
                                          -0.87, 86588048, 4905541689620]}]}))
    rows = tvdata.quotes(["NASDAQ:AAPL"])
    assert rows[0]["symbol"] == "NASDAQ:AAPL"
    assert rows[0]["close"] == 336.13 and rows[0]["description"] == "Apple Inc."


def test_quotes_reject_an_unknown_field():
    with pytest.raises(TradingViewError) as exc:
        tvdata.quotes(["NASDAQ:AAPL"], fields=["moon_phase"])
    assert "moon_phase" in str(exc.value)


def test_quotes_need_a_symbol():
    with pytest.raises(TradingViewError):
        tvdata.quotes([])


def test_screen_builds_the_request(monkeypatch):
    sent = {}

    def urlopen(req, *a, **k):
        sent["body"] = json.loads(req.data.decode())
        return _scan_response({"data": [{"s": "NYSE:BAC", "d": ["BAC", "Bank",
                                                                57.73, -0.77,
                                                                29.1, 52483860,
                                                                4.0e11, "Finance"]}]})

    monkeypatch.setattr(tvdata.urllib.request, "urlopen", urlopen)
    rows = tvdata.screen([{"field": "rsi", "op": "less", "value": 35}], limit=5)
    body = sent["body"]
    # TradingView's own spelling goes on the wire, not ours
    assert {"left": "RSI", "operation": "less", "right": 35} in body["filter"]
    assert body["range"] == [0, 5]
    assert body["sort"]["sortBy"] == "market_cap_basic"
    assert rows[0]["symbol"] == "NYSE:BAC" and rows[0]["rsi"] == 29.1


def test_screen_excludes_preferred_shares_by_default(monkeypatch):
    sent = {}
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda req, *a, **k: (sent.update(body=json.loads(req.data.decode())),
                                              _scan_response({"data": []}))[1])
    tvdata.screen([{"field": "rsi", "op": "less", "value": 35}])
    lefts = [f["left"] for f in sent["body"]["filter"]]
    assert "type" in lefts and "is_primary" in lefts and "typespecs" in lefts

    tvdata.screen([{"field": "rsi", "op": "less", "value": 35}],
                  common_stock_only=False)
    assert [f["left"] for f in sent["body"]["filter"]] == ["RSI"]


def test_screen_rejects_unknown_fields_and_operations():
    with pytest.raises(TradingViewError):
        tvdata.screen([{"field": "vibes", "op": "less", "value": 1}])
    with pytest.raises(TradingViewError):
        tvdata.screen([{"field": "rsi", "op": "wobbles", "value": 1}])
    with pytest.raises(TradingViewError):
        tvdata.screen([{"field": "rsi", "op": "less", "value": 1}], sort_by="vibes")


def test_technicals_returns_one_row(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", lambda *a, **k: _scan_response(
        {"data": [{"s": "NASDAQ:AAPL",
                   "d": [336.13, -0.25, 64.25, 5.51, 3.91, 330.0, 320.14,
                         286.34, 7.3, 1.2, 0.5, 2.0, 23.46, 0.3]}]}))
    row = tvdata.technicals("NASDAQ:AAPL")
    assert row["rsi"] == 64.25 and row["sma200"] == 286.34


def test_technicals_explains_an_empty_answer(monkeypatch):
    monkeypatch.setattr(tvdata.urllib.request, "urlopen",
                        lambda *a, **k: _scan_response({"data": []}))
    with pytest.raises(TradingViewError) as exc:
        tvdata.technicals("NOPE")
    assert "exchange prefix" in str(exc.value)


def test_a_scanner_failure_is_a_tradingview_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("connection reset")
    monkeypatch.setattr(tvdata.urllib.request, "urlopen", boom)
    with pytest.raises(TradingViewError) as exc:
        tvdata.quotes(["NASDAQ:AAPL"])
    assert "scanner refused" in str(exc.value)
