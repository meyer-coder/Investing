import json
import urllib.error

import pytest

from evotrader import screener
from evotrader.screener import (Filter, PRESETS, Screen, ScreenerError, Snapshot,
                                preset, resolve_column, run_screen, yahoo_symbols)


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode() if isinstance(body, str) else body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _urlopen_returning(*bodies):
    """Fake urlopen replaying ``bodies``; an Exception instance is raised."""
    calls = {"n": 0}

    def fake(req, timeout=None):
        i = min(calls["n"], len(bodies) - 1)
        calls["n"] += 1
        item = bodies[i]
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)

    fake.calls = calls
    return fake


def _payload(rows, total=None):
    return json.dumps({"totalCount": total if total is not None else len(rows),
                       "data": rows})


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(screener, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(screener, "UNIVERSE_DIR", str(tmp_path / "universes"))
    monkeypatch.setattr(screener.time, "sleep", lambda *_: None)


def test_filter_parse_handles_each_operator():
    assert Filter.parse("mcap > 10e9") == Filter("mcap", "greater", 10e9)
    assert Filter.parse("rsi <= 30") == Filter("rsi", "eless", 30)
    assert Filter.parse("sector = Technology") == Filter("sector", "equal", "Technology")
    assert Filter.parse("primary = true") == Filter("primary", "equal", True)


def test_filter_parse_rejects_garbage():
    with pytest.raises(ScreenerError):
        Filter.parse("mcap is big")


def test_filter_rejects_unknown_operation():
    with pytest.raises(ScreenerError):
        Filter("mcap", "approximately", 5)


def test_aliases_resolve_and_unknown_columns_pass_through():
    assert resolve_column("mcap") == "market_cap_basic"
    assert resolve_column("Recommend.All") == "Recommend.All"


def test_payload_uses_tradingview_column_names():
    screen = Screen(filters=[Filter("mcap", "greater", 1e9)],
                    columns=("price", "rsi"), sort_by="mcap", limit=3)
    payload = screen.payload()
    assert payload["filter"] == [
        {"left": "market_cap_basic", "operation": "greater", "right": 1e9}]
    assert payload["columns"] == ["close", "RSI"]
    assert payload["sort"]["sortBy"] == "market_cap_basic"
    assert payload["range"] == [0, 3]


def test_fingerprint_tracks_the_query():
    a = Screen(filters=[Filter("mcap", "greater", 1e9)])
    b = Screen(filters=[Filter("mcap", "greater", 2e9)])
    assert a.fingerprint() == Screen(filters=[Filter("mcap", "greater", 1e9)]).fingerprint()
    assert a.fingerprint() != b.fingerprint()


def test_scan_splits_exchange_from_ticker(monkeypatch):
    body = _payload([{"s": "NASDAQ:NVDA", "d": ["NVDA", 211.9]}], total=450)
    monkeypatch.setattr(screener.urllib.request, "urlopen", _urlopen_returning(body))
    snap = run_screen(Screen(columns=("name", "price")), cache_ttl=0)
    assert snap.rows[0] == {"symbol": "NVDA", "exchange": "NASDAQ",
                            "name": "NVDA", "price": 211.9}
    assert snap.symbols == ["NVDA"] and snap.total_matches == 450


def test_dedupe_keeps_best_sorted_row_and_trims_to_limit(monkeypatch):
    rows = [{"s": f"EX{i}:BTCUSD", "d": ["BTC", 100 + i]} for i in range(3)]
    rows.append({"s": "EX0:ETHUSD", "d": ["ETH", 50]})
    monkeypatch.setattr(screener.urllib.request, "urlopen",
                        _urlopen_returning(_payload(rows)))
    screen = Screen(market="crypto", columns=("base", "price"),
                    dedupe="base", limit=2)
    snap = run_screen(screen, cache_ttl=0)
    assert [r["base"] for r in snap.rows] == ["BTC", "ETH"]
    assert snap.rows[0]["price"] == 100  # the first, best-sorted BTC row


def test_dedupe_over_fetches_so_duplicates_do_not_eat_the_limit():
    assert Screen(limit=25, dedupe="base").payload()["range"] == [0, 200]
    assert Screen(limit=25).payload()["range"] == [0, 25]


def test_empty_body_is_retried_then_succeeds(monkeypatch):
    fake = _urlopen_returning("", "   ", _payload([{"s": "AMEX:SPY", "d": ["SPY"]}]))
    monkeypatch.setattr(screener.urllib.request, "urlopen", fake)
    snap = run_screen(Screen(columns=("name",)), cache_ttl=0)
    assert snap.symbols == ["SPY"]
    assert fake.calls["n"] == 3


def test_bad_query_fails_without_retrying(monkeypatch):
    err = urllib.error.HTTPError("u", 400, "Bad Request", {}, None)
    fake = _urlopen_returning(err)
    monkeypatch.setattr(screener.urllib.request, "urlopen", fake)
    with pytest.raises(ScreenerError, match="rejected"):
        run_screen(Screen(), cache_ttl=0)
    assert fake.calls["n"] == 1


def test_exhausted_retries_raise(monkeypatch):
    fake = _urlopen_returning(TimeoutError("slow"))
    monkeypatch.setattr(screener.urllib.request, "urlopen", fake)
    with pytest.raises(ScreenerError, match="unreachable"):
        run_screen(Screen(), retries=3, cache_ttl=0)
    assert fake.calls["n"] == 3


def test_cache_hit_avoids_the_network(monkeypatch):
    fake = _urlopen_returning(_payload([{"s": "AMEX:SPY", "d": ["SPY"]}]))
    monkeypatch.setattr(screener.urllib.request, "urlopen", fake)
    screen = Screen(columns=("name",))
    first = run_screen(screen, cache_ttl=900)
    second = run_screen(screen, cache_ttl=900)
    assert fake.calls["n"] == 1
    assert first.symbols == second.symbols


def test_refresh_bypasses_the_cache(monkeypatch):
    fake = _urlopen_returning(_payload([{"s": "AMEX:SPY", "d": ["SPY"]}]))
    monkeypatch.setattr(screener.urllib.request, "urlopen", fake)
    screen = Screen(columns=("name",))
    run_screen(screen, cache_ttl=900)
    run_screen(screen, cache_ttl=900, refresh=True)
    assert fake.calls["n"] == 2


def test_unknown_market_and_preset_are_rejected():
    with pytest.raises(ScreenerError):
        run_screen(Screen(market="atlantis"))
    with pytest.raises(ScreenerError):
        preset("nope")


def test_lookahead_warning_fires_only_for_windows_before_capture():
    snap = Snapshot("s", "america", "2026-09-15T00:00:00+00:00", [], [])
    assert snap.lookahead_warning("2026-09-15") is None
    assert snap.lookahead_warning("2027-01-01") is None
    warning = snap.lookahead_warning("2015-01-01")
    assert warning and "look-ahead bias" in warning


def test_snapshot_round_trips_through_disk(tmp_path):
    snap = Snapshot("liquid", "america", "2026-09-15T00:00:00+00:00",
                    ["name"], [{"symbol": "SPY", "exchange": "AMEX", "name": "SPY"}], 12)
    path = snap.save(str(tmp_path))
    assert path.endswith("liquid-2026-09-15.json")
    assert Snapshot.load(path) == snap


def test_yahoo_symbols_translates_crypto_only():
    equity = Snapshot("e", "america", "2026-09-15T00:00:00+00:00", ["name"],
                      [{"symbol": "SPY", "exchange": "AMEX"}])
    assert yahoo_symbols(equity) == ["SPY"]
    crypto = Snapshot("c", "crypto", "2026-09-15T00:00:00+00:00", ["base"],
                      [{"symbol": "BTCUSD", "exchange": "BINANCE", "base": "BTC"}])
    assert yahoo_symbols(crypto) == ["BTC-USD"]


def test_every_preset_is_well_formed():
    for name, screen in PRESETS.items():
        assert screen.name == name
        assert screen.market in screener.MARKETS
        screen.payload()
        if screen.dedupe:
            assert screen.dedupe in screen.columns


def test_quote_screen_matches_equities_by_name():
    screen = screener.quote_screen(["spy", " nvda "])
    assert screen.filters == [Filter("name", "in_range", ["SPY", "NVDA"])]
    assert screen.dedupe is None


def test_quote_screen_matches_crypto_by_base_and_collapses_venues():
    screen = screener.quote_screen(["BTC-USD", "ETH"], market="crypto")
    assert screen.filters == [Filter("base", "in_range", ["BTC", "ETH"])]
    assert screen.dedupe == "base"


def test_quote_screen_needs_symbols():
    with pytest.raises(ScreenerError):
        screener.quote_screen(["  "])


def test_screen_command_reports_and_writes_config(monkeypatch, tmp_path, capsys):
    from evotrader import cli
    body = _payload([{"s": "NASDAQ:NVDA", "d": ["NVDA", "NVIDIA", 212.0, 5.1e12,
                                                1.4e8, 0.37, 45.0, 197.0, 12.0,
                                                "Technology", "stock"]}], total=450)
    monkeypatch.setattr(screener.urllib.request, "urlopen", _urlopen_returning(body))
    config = tmp_path / "universe.json"
    code = cli.main(["screen", "--preset", "liquid-large-cap", "--limit", "1",
                     "--config", str(config)])
    out = capsys.readouterr().out
    assert code == 0
    assert "NVDA" in out and "450 matches" in out
    assert json.loads(config.read_text())["symbols"] == ["NVDA"]


def test_screen_command_reports_failure(monkeypatch, capsys):
    from evotrader import cli
    monkeypatch.setattr(screener.urllib.request, "urlopen",
                        _urlopen_returning(TimeoutError("down")))
    code = cli.main(["screen", "--preset", "liquid-large-cap", "--refresh"])
    assert code == 1
    assert "screen failed" in capsys.readouterr().err
