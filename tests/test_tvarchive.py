"""Deep futures history stitched from expired quarterly contracts."""
from datetime import date

import numpy as np
import pytest

from evotrader import tvarchive, tvcache
from evotrader.data import Bars, DataError


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tvcache, "CACHE_DIR", str(tmp_path / "tv"))


def _bars(symbol, stamps, base=100.0):
    n = len(stamps)
    close = np.arange(base, base + n, dtype=float)
    return Bars(symbol, list(stamps), close.copy(), close + 1, close - 1,
                close.copy(), np.full(n, 10.0))


# ------------------------------------------------------------------ contracts

def test_quarterly_codes_and_expiries():
    assert tvarchive.third_friday(2016, 3) == date(2016, 3, 18)
    assert tvarchive.third_friday(2024, 12) == date(2024, 12, 20)


def test_contracts_are_quarterly_and_ordered():
    rows = tvarchive.contracts("NQ", 2020, today=date(2021, 6, 1))
    codes = [c for c, _ in rows]
    assert codes[:4] == ["NQH2020", "NQM2020", "NQU2020", "NQZ2020"]
    assert rows == sorted(rows, key=lambda r: r[1])


def test_contracts_stop_shortly_past_today():
    codes = [c for c, _ in tvarchive.contracts("NQ", 2024, today=date(2024, 6, 1),
                                               ahead_days=200)]
    # September expires inside the horizon; December (2024-12-20) is 202 days
    # out and the next March is further still.
    assert codes == ["NQH2024", "NQM2024", "NQU2024"]
    codes = [c for c, _ in tvarchive.contracts("NQ", 2024, today=date(2024, 6, 1),
                                               ahead_days=250)]
    assert "NQZ2024" in codes and "NQH2025" not in codes


# ------------------------------------------------------------------- sessions

def test_evening_bars_belong_to_the_next_session():
    """CME equity futures open the evening before; 22:00 UTC is the boundary."""
    assert tvarchive.session_date("2024-03-05 20:00") == "2024-03-05"
    assert tvarchive.session_date("2024-03-05 23:00") == "2024-03-06"
    assert tvarchive.session_date("2024-03-05") == "2024-03-05"


def test_coverage_counts_sessions_not_bars():
    bars = _bars("X", ["2024-03-04 14:00", "2024-03-04 15:00",
                       "2024-03-05 14:00", "2024-03-29 14:00"])
    report = tvarchive.coverage(bars)
    assert report["sessions"] == 3
    assert report["largest_gap_days"] == 24
    assert report["covered"] < 0.2, "three sessions in a month is not coverage"


def test_coverage_of_nothing():
    assert tvarchive.coverage(_bars("X", []))["sessions"] == 0


# ------------------------------------------------------------------ stitching

def test_stitch_prefers_the_newer_contract():
    old = _bars("NQH2024", ["2024-03-01", "2024-03-02"], base=100)
    new = _bars("NQM2024", ["2024-03-02", "2024-03-03"], base=200)
    stitched, _ = tvarchive.stitch([("NQH2024", old), ("NQM2024", new)],
                                   back_adjust=False)
    assert stitched.dates == ["2024-03-01", "2024-03-02", "2024-03-03"]
    # the shared day comes from the newer contract
    assert float(stitched.close[1]) == 200.0
    assert stitched.sources[1] == "NQM2024"


def test_back_adjustment_removes_the_roll_jump():
    """Two contracts, same shape, 100 points apart: the splice must be smooth."""
    old = _bars("NQH2024", ["2024-03-01", "2024-03-02"], base=100)
    new = _bars("NQM2024", ["2024-03-02", "2024-03-03"], base=200)
    raw, _ = tvarchive.stitch([("NQH2024", old), ("NQM2024", new)],
                              back_adjust=False)
    adjusted, rolls = tvarchive.stitch([("NQH2024", old), ("NQM2024", new)],
                                       back_adjust=True)
    jump_raw = abs(float(raw.close[1]) - float(raw.close[0]))
    jump_adj = abs(float(adjusted.close[1]) - float(adjusted.close[0]))
    assert jump_raw > 90, "the unadjusted splice should show the roll basis"
    assert jump_adj <= 2, "back-adjustment should leave a normal bar-to-bar move"
    # measured where they overlap: the old contract's 101 against the new's 200
    assert rolls[0]["basis"] == 99.0 and rolls[0]["overlapping_bars"] == 1


def test_a_roll_with_no_overlap_is_recorded_not_guessed():
    old = _bars("NQH2024", ["2024-03-01"], base=100)
    new = _bars("NQM2024", ["2024-06-01"], base=200)
    _, rolls = tvarchive.stitch([("NQH2024", old), ("NQM2024", new)])
    assert rolls[0]["basis"] is None and rolls[0]["overlapping_bars"] == 0


def test_stitch_needs_something_to_stitch():
    with pytest.raises(DataError):
        tvarchive.stitch([("NQH2024", _bars("NQH2024", []))])


# ---------------------------------------------------------------------- build

def test_build_pulls_every_contract_and_reports_the_holes(monkeypatch):
    asked = []

    def fake_fetch(symbol, timeframe, bars, **kwargs):
        asked.append(symbol)
        if symbol.endswith("1!"):
            return _bars(symbol, ["2024-12-02 14:00", "2024-12-03 14:00"], base=500)
        year = int(symbol[-4:])
        return _bars(symbol, [f"{year}-03-0{d} 14:00" for d in (1, 2)], base=100)

    report = tvarchive.build("CME_MINI", "NQ", "5", since_year=2023,
                             today=date(2024, 12, 20), pause=0,
                             fetch=fake_fetch)
    assert asked[0] == "CME_MINI:NQ1!", "the continuous series is pulled too"
    assert any("NQH2023" in s for s in asked)
    assert report["contracts"] == len(set(asked))   # each pulled intraday and daily
    assert report["bars"] > 0
    assert report["covered"] < 0.2, "islands should not read as full coverage"
    assert "sessions" in report and report["largest_gap_days"] > 100

    # and the stitched series is in the store under its own symbol
    stored = tvcache.read_cache("CME_MINI:NQ#ARCHIVE", "5")
    assert stored is not None and len(stored) == report["bars"]


def test_build_survives_a_contract_that_fails(monkeypatch):
    from evotrader.tvdata import TradingViewError

    def fake_fetch(symbol, timeframe, bars, **kwargs):
        if "NQM" in symbol:
            raise TradingViewError("no bars for this contract")
        return _bars(symbol, ["2024-03-01 14:00"], base=100)

    report = tvarchive.build("CME_MINI", "NQ", "5", since_year=2024,
                             today=date(2024, 12, 20), pause=0, fetch=fake_fetch)
    assert any("NQM" in f for f in report["failures"])
    assert report["bars"] > 0, "one bad contract must not sink the archive"


def test_build_raises_when_everything_fails():
    from evotrader.tvdata import TradingViewError

    def fake_fetch(*a, **k):
        raise TradingViewError("nothing here")

    with pytest.raises(TradingViewError):
        tvarchive.build("CME_MINI", "NQ", "5", since_year=2024,
                        today=date(2024, 12, 20), pause=0, fetch=fake_fetch)


def test_describe_says_what_the_coverage_means():
    report = {"symbol": "CME_MINI:NQ#ARCHIVE", "timeframe": "5", "bars": 1000,
              "contracts": 40, "start": "2015-03-01", "end": "2026-09-01",
              "sessions": 200, "weekdays": 3000, "covered": 0.066,
              "largest_gap_days": 60, "bars_per_session": 5.0,
              "back_adjusted": True, "rolls": [{"basis": 1.0}, {"basis": None}],
              "failures": []}
    text = tvarchive.describe(report)
    assert "7% covered" in text or "6% covered" in text
    assert "not a continuous history" in text
    assert "1 with no overlap" in text


def test_the_basis_falls_back_to_daily_overlap():
    """Intraday windows rarely overlap; the contracts' daily lives always do."""
    old = _bars("NQH2024", ["2024-03-01 14:00"], base=100)
    new = _bars("NQM2024", ["2024-06-01 14:00"], base=200)
    old_daily = _bars("NQH2024", ["2024-02-01", "2024-02-02"], base=100)
    new_daily = _bars("NQM2024", ["2024-02-01", "2024-02-02"], base=150)

    _, without = tvarchive.stitch([("NQH2024", old), ("NQM2024", new)])
    assert without[0]["basis"] is None

    adjusted, rolls = tvarchive.stitch(
        [("NQH2024", old), ("NQM2024", new)],
        daily={"NQH2024": old_daily, "NQM2024": new_daily})
    assert rolls[0]["basis"] == 50.0
    assert rolls[0]["measured_on"] == "daily"
    assert float(adjusted.close[0]) == 150.0, "the older contract was lifted"


def test_build_fetches_daily_for_the_basis(monkeypatch):
    seen = []

    def fake_fetch(symbol, timeframe, bars, **kwargs):
        seen.append((symbol, timeframe))
        return _bars(symbol, ["2024-03-01 14:00"] if timeframe != "1D"
                     else ["2024-02-01", "2024-02-02"], base=100)

    tvarchive.build("CME_MINI", "NQ", "5", since_year=2024,
                    today=date(2024, 6, 1), pause=0, fetch=fake_fetch)
    assert any(tf == "1D" for _, tf in seen), "no daily pull, no measurable basis"

    seen.clear()
    tvarchive.build("CME_MINI", "NQ", "5", since_year=2024, back_adjust=False,
                    today=date(2024, 6, 1), pause=0, fetch=fake_fetch)
    assert not any(tf == "1D" for _, tf in seen), "raw prices need no basis"
