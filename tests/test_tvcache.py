"""The local candle store: merging, growth, and surviving a dead feed."""
import time

import numpy as np
import pytest

from evotrader import tvcache
from evotrader.data import Bars, DataError
from evotrader.tvdata import TradingViewError


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tvcache, "CACHE_DIR", str(tmp_path / "tv"))
    return tmp_path


def _bars(symbol, dates, close_from=1.0):
    n = len(dates)
    closes = np.arange(close_from, close_from + n, dtype=float)
    return Bars(symbol, list(dates), closes.copy(), closes + 1, closes - 1,
                closes.copy(), np.full(n, 100.0))


def test_round_trip_through_disk():
    bars = _bars("NASDAQ:AAPL", ["2024-01-02", "2024-01-03"])
    tvcache.write_cache(bars, "1D")
    again = tvcache.read_cache("NASDAQ:AAPL", "1D")
    assert again.dates == bars.dates
    assert float(again.close[-1]) == float(bars.close[-1])


def test_missing_cache_reads_as_none():
    assert tvcache.read_cache("NASDAQ:NOPE", "1D") is None


def test_symbols_with_punctuation_get_one_file_each():
    a = tvcache.cache_path("BINANCE:BTCUSDT", "5")
    b = tvcache.cache_path("NASDAQ:AAPL", "5")
    assert a != b and a.endswith("BINANCE_BTCUSDT__5.csv")


def test_merge_is_a_union_in_time_order():
    old = _bars("X", ["2024-01-01", "2024-01-02"])
    new = _bars("X", ["2024-01-02", "2024-01-03"], close_from=9.0)
    merged = tvcache.merge(old, new)
    assert merged.dates == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert float(merged.close[1]) == 9.0, "a re-fetched bar replaces the stored one"


def test_merge_tolerates_either_side_missing():
    bars = _bars("X", ["2024-01-01"])
    assert tvcache.merge(None, bars).dates == bars.dates
    assert tvcache.merge(bars, None).dates == bars.dates
    with pytest.raises(DataError):
        tvcache.merge(None, None)


def test_the_store_grows_past_one_request():
    """The point of the cache: history the feed no longer serves."""
    first = _bars("X", [f"2024-01-{d:02d}" for d in range(1, 11)])
    later = _bars("X", [f"2024-01-{d:02d}" for d in range(6, 16)], close_from=50.0)
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: first)
    grown = tvcache.cached_bars("X", "1D", 100, force=True,
                                fetch=lambda *a, **k: later)
    assert len(grown) == 15                       # neither window alone holds this
    assert grown.dates[0] == "2024-01-01" and grown.dates[-1] == "2024-01-15"


def test_only_the_requested_window_comes_back():
    bars = _bars("X", [f"2024-01-{d:02d}" for d in range(1, 21)])
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: bars)
    window = tvcache.cached_bars("X", "1D", 5, refresh=False)
    assert len(window) == 5 and window.dates[-1] == "2024-01-20"


def test_a_dead_feed_falls_back_to_the_store():
    stored = _bars("X", [f"2024-01-{d:02d}" for d in range(1, 11)])
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: stored)

    def offline(*a, **k):
        raise TradingViewError("connection refused")

    kept = tvcache.cached_bars("X", "1D", 100, force=True, fetch=offline)
    assert len(kept) == 10
    assert any("connection refused" in w for w in kept.warnings)


def test_a_dead_feed_with_no_store_still_raises():
    def offline(*a, **k):
        raise TradingViewError("connection refused")
    with pytest.raises(TradingViewError):
        tvcache.cached_bars("EMPTY", "1D", 100, fetch=offline)


def test_refresh_false_never_touches_the_network():
    bars = _bars("X", ["2024-01-01", "2024-01-02"])
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: bars)

    def explode(*a, **k):
        raise AssertionError("refresh=False must not fetch")

    assert len(tvcache.cached_bars("X", "1D", 100, refresh=False, fetch=explode)) == 2


def test_each_timeframe_is_stored_separately():
    tvcache.cached_bars("X", "1D", 100,
                        fetch=lambda *a, **k: _bars("X", ["2024-01-01"]))
    tvcache.cached_bars("X", "60", 100,
                        fetch=lambda *a, **k: _bars("X", ["2024-01-01 10:00",
                                                          "2024-01-01 11:00"]))
    summary = {(r["symbol"], r["timeframe"]): r["bars"] for r in tvcache.cache_summary()}
    assert summary[("X", "1D")] == 1 and summary[("X", "60")] == 2


def test_summary_of_an_empty_store():
    assert tvcache.cache_summary() == []


def test_a_recent_pull_is_not_repeated():
    """Cold fetches cost seconds; a client's tool timeout is not generous."""
    bars = _bars("X", ["2024-01-01", "2024-01-02"])
    calls = []
    tvcache.cached_bars("X", "1D", 100,
                        fetch=lambda *a, **k: (calls.append(1), bars)[1])
    tvcache.cached_bars("X", "1D", 100,
                        fetch=lambda *a, **k: (calls.append(1), bars)[1])
    assert len(calls) == 1, "the second call should read the store"


def test_a_stale_store_is_refreshed(monkeypatch):
    bars = _bars("X", ["2024-01-01"])
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: bars)
    path = tvcache.cache_path("X", "1D")
    import os
    stale = os.path.getmtime(path) - 86_400
    os.utime(path, (stale, stale))
    calls = []
    tvcache.cached_bars("X", "1D", 100,
                        fetch=lambda *a, **k: (calls.append(1), bars)[1])
    assert len(calls) == 1


def test_an_unchanged_refetch_still_records_the_check():
    import os
    bars = _bars("X", ["2024-01-01"])
    tvcache.cached_bars("X", "60", 100, fetch=lambda *a, **k: bars)
    path = tvcache.cache_path("X", "60")
    stale = os.path.getmtime(path) - 7200
    os.utime(path, (stale, stale))
    tvcache.cached_bars("X", "60", 100, fetch=lambda *a, **k: bars)
    assert time.time() - os.path.getmtime(path) < 5, "the check time is recorded"


def test_force_overrides_freshness():
    bars = _bars("X", ["2024-01-01"])
    calls = []
    tvcache.cached_bars("X", "1D", 100, fetch=lambda *a, **k: (calls.append(1), bars)[1])
    tvcache.cached_bars("X", "1D", 100, force=True,
                        fetch=lambda *a, **k: (calls.append(1), bars)[1])
    assert len(calls) == 2
