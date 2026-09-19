"""The local candle store: merging, growth, and surviving a dead feed."""
import os
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
    assert a != b and a.endswith("BINANCE_BTCUSDT__5.npz")


def test_merge_is_a_union_in_time_order():
    old = _bars("X", ["2024-01-01", "2024-01-02"])
    new = _bars("X", ["2024-01-02", "2024-01-03"], close_from=9.0)
    merged = tvcache.merge_series(old, new)
    assert merged.dates == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert float(merged.close[1]) == 9.0, "a re-fetched bar replaces the stored one"


def test_merge_tolerates_either_side_missing():
    bars = _bars("X", ["2024-01-01"])
    assert tvcache.merge_series(None, bars).dates == bars.dates
    assert tvcache.merge_series(bars, None).dates == bars.dates
    with pytest.raises(DataError):
        tvcache.merge_series(None, None)


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


# ------------------------------------------------- bulk import and interchange

def test_import_csv_from_another_tool(cache_dir, tmp_path):
    """Any exporter's column names, as long as there is a date and OHLC."""
    src = tmp_path / "nq.csv"
    src.write_text("timestamp,Open,High,Low,Close,Volume\n"
                   "2024-01-02 09:30,100,101,99,100.5,1200\n"
                   "2024-01-02 09:31,100.5,102,100,101.5,900\n")
    bars = tvcache.import_csv(str(src), "CME_MINI:NQ1!", "1")
    assert len(bars) == 2
    assert bars.dates[0] == "2024-01-02 09:30"
    assert float(bars.close[-1]) == 101.5
    # and it is in the store afterwards
    again = tvcache.read_cache("CME_MINI:NQ1!", "1")
    assert again is not None and len(again) == 2


def test_import_merges_with_what_is_already_stored(cache_dir, tmp_path):
    tvcache.cached_bars("X", "1", 100,
                        fetch=lambda *a, **k: _bars("X", ["2024-01-01 09:30"]))
    src = tmp_path / "more.csv"
    src.write_text("date,open,high,low,close,volume\n"
                   "2024-01-01 09:31,1,2,0.5,1.5,10\n")
    merged = tvcache.import_csv(str(src), "X", "1")
    assert len(merged) == 2, "the import replaced the store instead of adding to it"


def test_import_without_a_volume_column(cache_dir, tmp_path):
    src = tmp_path / "novol.csv"
    src.write_text("date,open,high,low,close\n2024-01-01,1,2,0.5,1.5\n")
    bars = tvcache.import_csv(str(src), "Y", "1D")
    assert float(bars.volume[0]) == 0.0


def test_import_rejects_a_file_with_no_prices(cache_dir, tmp_path):
    src = tmp_path / "junk.csv"
    src.write_text("a,b\n1,2\n")
    with pytest.raises(DataError):
        tvcache.import_csv(str(src), "Z", "1D")


def test_export_csv_round_trips(cache_dir, tmp_path):
    tvcache.cached_bars("R", "1D", 100,
                        fetch=lambda *a, **k: _bars("R", ["2024-01-01", "2024-01-02"]))
    out = tvcache.export_csv("R", "1D", str(tmp_path / "out.csv"))
    back = tvcache.import_csv(out, "R2", "1D")
    assert back.dates == ["2024-01-01", "2024-01-02"]


def test_the_store_is_binary(cache_dir):
    tvcache.cached_bars("B", "1D", 100,
                        fetch=lambda *a, **k: _bars("B", ["2024-01-01"]))
    path = tvcache.cache_path("B", "1D")
    assert path.endswith(".npz") and os.path.exists(path)


def test_a_legacy_csv_store_is_still_readable(cache_dir):
    """Anything written before the switch must keep working."""
    import csv as _csv
    os.makedirs(tvcache.CACHE_DIR, exist_ok=True)
    with open(tvcache.csv_path("OLD", "1D"), "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        w.writerow(["2024-01-01", 1, 2, 0.5, 1.5, 10])
    bars = tvcache.read_cache("OLD", "1D")
    assert bars is not None and float(bars.close[0]) == 1.5
