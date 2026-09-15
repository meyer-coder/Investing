import numpy as np
import pytest

from evotrader import data
from evotrader.data import (BARS_PER_YEAR, DataError, INTERVALS, Bars,
                            bars_per_year, load_symbol, load_universe,
                            synthetic_bars)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "CACHE_DIR", str(tmp_path / "cache"))


def _fake_fetch(recorder):
    """Stand in for Yahoo, returning bars spanning exactly what was asked."""
    def fetch(symbol, start, end, *, timeout=30, retries=3, interval="1d"):
        recorder.append((symbol, start, end, interval))
        days = (np.datetime64(end) - np.datetime64(start)).astype(int)
        n = max(60, min(days, 4000))
        bars = synthetic_bars(symbol, n, seed=1, interval=interval)
        dates = [str(np.datetime64(start) + np.timedelta64(i, "D")) for i in range(n)]
        return Bars(symbol.upper(), dates, bars.open, bars.high, bars.low,
                    bars.close, bars.volume)
    return fetch


# ─── intervals ────────────────────────────────────────────────────────────────

def test_every_interval_has_an_annualisation_factor():
    assert set(INTERVALS) == set(BARS_PER_YEAR)
    assert bars_per_year("1d") == 252.0
    assert bars_per_year("1h") == pytest.approx(252.0 * 6.5)


def test_unknown_interval_falls_back_for_annualisation_but_is_rejected_for_loading():
    assert bars_per_year("banana") == 252.0
    with pytest.raises(DataError):
        load_universe(["AAA"], "2015-01-01", "2020-01-01", interval="banana")


def test_daily_keeps_its_historic_cache_filename():
    assert data._cache_path("SPY", "1d").endswith("SPY.csv")
    assert data._cache_path("SPY", "1h").endswith("SPY@1h.csv")


def test_intervals_do_not_share_a_cache_file():
    assert data._cache_path("SPY", "1h") != data._cache_path("SPY", "30m")


def test_synthetic_intraday_bars_carry_a_time_of_day():
    assert " " in synthetic_bars("AAA", 10, interval="1h").dates[0]
    assert " " not in synthetic_bars("AAA", 10, interval="1d").dates[0]


def test_intraday_requests_outside_the_served_window_are_refused():
    """Yahoo returns an empty series rather than an error, so fetch_yahoo
    has to catch this itself — and before any network call."""
    with pytest.raises(DataError, match="only served for the last 60 days"):
        data.fetch_yahoo("SPY", "2005-01-01", "2005-06-01", interval="5m")


# ─── coverage tracking ────────────────────────────────────────────────────────

def test_cache_is_reused_for_a_window_it_covers(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "fetch_yahoo", _fake_fetch(calls))
    load_symbol("AAA", "2015-01-01", "2020-01-01")
    load_symbol("AAA", "2016-01-01", "2019-01-01")
    assert len(calls) == 1, "a narrower window should come from the cache"


def test_a_wider_window_refetches_rather_than_silently_truncating(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "fetch_yahoo", _fake_fetch(calls))
    load_symbol("AAA", "2018-01-01", "2020-01-01")
    bars = load_symbol("AAA", "2010-01-01", "2020-01-01")
    assert len(calls) == 2, "the earlier start was not cached and must be fetched"
    assert bars.dates[0] <= "2010-01-02"


def test_refetching_widens_coverage_instead_of_replacing_it(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "fetch_yahoo", _fake_fetch(calls))
    load_symbol("AAA", "2015-01-01", "2020-01-01")
    load_symbol("AAA", "2010-01-01", "2016-01-01")   # widens backwards
    assert calls[-1][1] == "2010-01-01"
    assert calls[-1][2] == "2020-01-01", "the union is fetched, not just the gap"
    load_symbol("AAA", "2011-01-01", "2019-01-01")
    assert len(calls) == 2, "the widened range now covers this request"


def test_coverage_is_tracked_per_interval(monkeypatch):
    calls = []
    monkeypatch.setattr(data, "fetch_yahoo", _fake_fetch(calls))
    load_symbol("AAA", "2024-01-01", "2024-06-01")
    load_symbol("AAA", "2024-01-01", "2024-06-01", interval="1h")
    assert len(calls) == 2
    assert {c[3] for c in calls} == {"1d", "1h"}


def test_a_returned_window_never_exceeds_what_was_asked_for(monkeypatch):
    monkeypatch.setattr(data, "fetch_yahoo", _fake_fetch([]))
    bars = load_symbol("AAA", "2015-01-01", "2016-01-01")
    assert bars.dates[0] >= "2015-01-01"
    assert bars.dates[-1] <= "2016-01-01"


def test_corrupt_coverage_file_is_ignored(monkeypatch, tmp_path):
    import os
    os.makedirs(data.CACHE_DIR, exist_ok=True)
    with open(data._coverage_path(), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert data._read_coverage() == {}


def test_synthetic_bars_are_deterministic_across_processes():
    """hash() is salted per process, so offline runs used to differ every time
    despite being documented as reproducible."""
    import subprocess
    import sys
    code = ("from evotrader.data import synthetic_bars;"
            "print(round(float(synthetic_bars('AAA', 50).close[-1]), 8))")
    runs = {subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, cwd=".").stdout.strip() for _ in range(3)}
    assert len(runs) == 1, f"offline prices differed between processes: {runs}"


def test_different_symbols_still_get_different_series():
    from evotrader.data import synthetic_bars as sb
    assert float(sb("AAA", 50).close[-1]) != float(sb("BBB", 50).close[-1])
