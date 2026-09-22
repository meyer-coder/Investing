"""Tests for the intraday session features.

The load-bearing one is :func:`test_opening_range_is_invisible_while_forming`.
Every other intraday feature here is trivially causal; the opening range is the
one that could quietly leak the future into a rule, so it is tested twice —
directly, and by recomputing on a truncated history.
"""
from __future__ import annotations

import numpy as np
import pytest

from evotrader.features import FEATURE_DOCS, FEATURE_SET
from evotrader.sessions import SESSION_FEATURES, session_features


def _bars(day="2026-06-15", n=26, step=15, first_utc_hour=13, first_utc_min=30):
    """One RTH day of bars. 13:30 UTC == 09:30 New York in summer."""
    dates = []
    for i in range(n):
        total = first_utc_hour * 60 + first_utc_min + step * i
        dates.append(f"{day} {total // 60:02d}:{total % 60:02d}")
    high = np.arange(100.0, 100.0 + n)
    low = high - 1.0
    close = high - 0.5
    volume = np.full(n, 1000.0)
    return dates, high, low, close, volume


# ------------------------------------------------------------------ clock
def test_utc_stamps_convert_to_new_york_including_dst():
    summer, *rest = _bars("2026-06-15", n=2)
    f = session_features(summer, *rest)
    assert f["hour_et"][0] == 9 and f["minute_of_day"][0] == 570      # 09:30 EDT
    winter = _bars("2026-01-15", n=2, first_utc_hour=14, first_utc_min=30)
    g = session_features(winter[0], *winter[1:])
    assert g["hour_et"][0] == 9 and g["minute_of_day"][0] == 570      # 09:30 EST


def test_day_of_week_is_monday_zero():
    d, *r = _bars("2026-06-15", n=2)          # a Monday
    assert session_features(d, *r)["day_of_week"][0] == 0
    d, *r = _bars("2026-06-19", n=2)          # the Friday
    assert session_features(d, *r)["day_of_week"][0] == 4


def test_hour_flags_mark_the_right_windows():
    d, *r = _bars(n=26)                        # 15-minute bars, 09:30 onward
    f = session_features(d, *r)
    assert [int(x) for x in f["is_first_hour"][:4]] == [1, 1, 1, 1]      # 09:30-10:30
    assert int(f["is_first_hour"][4]) == 0
    assert [int(x) for x in f["is_second_hour"][4:8]] == [1, 1, 1, 1]    # 10:30-11:30
    assert int(f["is_rth"][0]) == 1
    assert int(f["is_power_hour"][22]) == 1                              # 15:00+


def test_minutes_since_open_is_negative_before_the_bell():
    d, *r = _bars(n=4, first_utc_hour=12, first_utc_min=30)   # 08:30 ET, pre-market
    f = session_features(d, *r)
    assert f["minutes_since_open"][0] == -60
    assert int(f["is_rth"][0]) == 0


# --------------------------------------------------------- no look-ahead
def test_opening_range_is_invisible_while_forming():
    d, *r = _bars(n=26)
    f = session_features(d, *r)
    # 09:30-10:30 is four 15-minute bars; none may see the range they form.
    assert np.all(np.isnan(f["opening_range_high"][:4]))
    assert np.all(np.isnan(f["opening_range_low"][:4]))
    # Published from the fifth bar on, and equal to the first hour's extremes.
    assert f["opening_range_high"][4] == pytest.approx(103.0)   # highs 100..103
    assert f["opening_range_low"][4] == pytest.approx(99.0)     # lows 99..102


def test_no_session_feature_depends_on_a_later_bar():
    d, h, l, c, v = _bars(n=26)
    full = session_features(d, h, l, c, v)
    cut = 20
    part = session_features(d[:cut], h[:cut], l[:cut], c[:cut], v[:cut])
    for name in SESSION_FEATURES:
        a, b = full[name][cut - 1], part[name][cut - 1]
        assert (np.isnan(a) and np.isnan(b)) or a == pytest.approx(b), \
            f"{name} depends on the future"


def test_opening_range_break_flags_latch_and_do_not_unlatch():
    d, h, l, c, v = _bars(n=26)
    f = session_features(d, h, l, c, v)
    broke = f["or_broken_up"][4:]
    assert int(broke[0]) == 1                       # highs rise past the range
    assert all(int(x) == 1 for x in broke)          # latched, never reset mid-session


# ------------------------------------------------------------- vwap/state
def test_session_vwap_is_the_running_volume_weighted_mean():
    d, h, l, c, v = _bars(n=4)
    f = session_features(d, h, l, c, v)
    typical = (h + l + c) / 3.0
    assert f["session_vwap"][0] == pytest.approx(typical[0])
    assert f["session_vwap"][3] == pytest.approx(typical[:4].mean())   # equal volumes
    assert f["dist_session_vwap"][3] == pytest.approx(c[3] / f["session_vwap"][3] - 1)


def test_session_state_resets_on_a_new_day():
    d1, h1, l1, c1, v1 = _bars("2026-06-15", n=8)
    d2, h2, l2, c2, v2 = _bars("2026-06-16", n=8)
    f = session_features(d1 + d2, np.r_[h1, h2], np.r_[l1, l2],
                         np.r_[c1, c2], np.r_[v1, v2])
    assert f["bars_since_open"][8] == 0                 # first bar of day two
    assert np.isnan(f["opening_range_high"][8])         # range forms again
    assert f["session_vwap"][8] == pytest.approx((h2[0] + l2[0] + c2[0]) / 3.0)


def test_daily_bars_yield_no_session_features():
    dates = ["1999-03-10", "1999-03-11", "1999-03-12"]
    arr = np.array([1.0, 2.0, 3.0])
    f = session_features(dates, arr, arr, arr, arr)
    for name in SESSION_FEATURES:
        assert np.all(np.isnan(f[name])), f"{name} should be NaN on daily bars"


# --------------------------------------------------------------- wiring
def test_every_session_feature_is_registered_and_documented():
    for name in SESSION_FEATURES:
        assert name in FEATURE_SET, f"{name} is not usable in a rule"
        assert FEATURE_DOCS.get(name), f"{name} has no description for the breeder"
