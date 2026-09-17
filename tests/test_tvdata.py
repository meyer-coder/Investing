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
        self._frames = list(frames)
        self.sent = []
        self.closed = False

    def send(self, text):
        self.sent.append(text)

    def frames(self):
        for frame in self._frames:
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


def test_fetch_bars_sends_the_session_token_when_given():
    fake = FakeSocket([_timescale("sds_1", [[1700000000, 1, 2, 0.5, 1.5, 1]]),
                       _packet("series_completed", ["cs"])])
    fetch_bars("X", "1D", 100, session_token="secret-cookie",
               socket_factory=lambda **k: fake)
    auth = json.loads(_split_frames(fake.sent[0])[0])
    assert auth["p"] == ["secret-cookie"]


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
