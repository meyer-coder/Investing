"""Tests for the confluence strategy factory and intraday engine."""
from __future__ import annotations

import datetime as dt
import io
import zipfile

import numpy as np
import pytest

pytest.importorskip("numba")
pytest.importorskip("pandas")

from confluence.bars import SESSIONS, _tdm, minute_clock, resample
from confluence.components import LEGS, Ctx
from confluence.data import Minutes, parse_histdata, thin_days
from confluence.engine import ENTRY_CODE, run
from confluence.families import FAMILIES, generate
from confluence.metrics import Calendar, evaluate, max_drawdown


def _utc_minute(y, mo, d, h, mi):
    return int(dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc).timestamp()) // 60


def _minutes(start, prices, feed="TEST"):
    """1-minute bars from a list of (open, high, low, close) starting at ``start``."""
    t = np.arange(start, start + len(prices), dtype=np.int64)
    p = np.asarray(prices, dtype=float)
    return Minutes(feed, t, p[:, 0], p[:, 1], p[:, 2], p[:, 3], {})


# ------------------------------------------------------------------ data

def test_histdata_timestamps_are_new_york_time_with_dst():
    rows = "20240710 093000;1;1;1;1;0\n20240110 093000;2;2;2;2;0\n"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("DAT_ASCII_TEST_M1_2024.csv", rows)
    t, o, *_ = parse_histdata(buf.getvalue())
    july, jan = sorted(zip(t, o), key=lambda x: x[1])
    # 09:30 New York is 13:30 UTC in July (EDT) and 14:30 UTC in January (EST).
    assert july[0] == _utc_minute(2024, 7, 10, 13, 30)
    assert jan[0] == _utc_minute(2024, 1, 10, 14, 30)


def test_thin_days_flags_short_and_missing_weekdays():
    full = []
    d0 = dt.date(2024, 1, 8)  # Monday
    for k in range(10):
        day = d0 + dt.timedelta(days=k)
        if day.weekday() >= 5:
            continue
        n = 1440 if k != 2 else 400          # Wednesday is thin
        if k == 3:
            continue                          # Thursday is missing
        base = (day - dt.date(1970, 1, 1)).days * 1440
        full.append(np.arange(base, base + n))
    t = np.concatenate(full)
    thin = thin_days(t, d0, ref_from=d0)
    assert dt.date(2024, 1, 10) in thin and dt.date(2024, 1, 11) in thin
    assert dt.date(2024, 1, 9) not in thin


# ------------------------------------------------------------------ clock and bars

def test_trading_day_rolls_at_six_pm_new_york():
    # 17:59 ET and 18:00 ET on 2024-01-10 (EST = UTC-5) belong to different trading days.
    a = _utc_minute(2024, 1, 10, 22, 59)
    m = _minutes(a, [(1, 1, 1, 1)] * 2)
    ck = minute_clock(m)
    assert ck.day[1] == ck.day[0] + 1
    assert ck.tdm[0] == 1439 and ck.tdm[1] == 0


def test_resample_aggregates_ohlc():
    start = _utc_minute(2024, 1, 10, 15, 0)
    prices = [(10, 12, 9, 11), (11, 15, 10, 14), (14, 14, 8, 9), (9, 10, 9, 10), (10, 11, 10, 11),
              (11, 13, 11, 12)]
    f = resample(minute_clock(_minutes(start, prices)), 5)
    assert f.n == 2
    assert (f.o[0], f.h[0], f.l[0], f.c[0]) == (10, 15, 8, 11)
    assert list(f.lo) == [0, 5] and list(f.hi) == [5, 6]


def test_session_levels_are_not_visible_before_their_window_closes():
    # One trading day of flat-ish minutes from 18:00 ET to 12:00 ET (EST).
    start = _utc_minute(2024, 1, 9, 23, 0)          # 18:00 ET Jan 9 -> trading day Jan 10
    n = 18 * 60
    rng = np.random.default_rng(0)
    c = 100 + np.cumsum(rng.normal(0, 0.05, n))
    prices = np.c_[c, c + 0.02, c - 0.02, c]
    f = resample(minute_clock(_minutes(start, prices)), 5)
    ctx = Ctx(f)
    asia = f.cache["asia_h"]
    before = f.tdm_open < _tdm(0)
    assert np.all(np.isnan(asia[before]))
    assert np.all(~np.isnan(asia[f.tdm_open >= _tdm(0)]))
    orh = f.cache["or_h"]
    assert np.all(np.isnan(orh[f.tdm_open < _tdm(10)]))


def test_every_leg_evaluates_on_real_shaped_data():
    start = _utc_minute(2024, 1, 2, 23, 0)
    n = 6 * 1440
    rng = np.random.default_rng(1)
    c = 100 + np.cumsum(rng.normal(0, 0.05, n))
    hi = c + np.abs(rng.normal(0, 0.03, n))
    lo = c - np.abs(rng.normal(0, 0.03, n))
    o = np.r_[c[0], c[:-1]]
    m = _minutes(start, np.c_[o, np.maximum(hi, o), np.minimum(lo, o), c])
    ctx = Ctx(resample(minute_clock(m), 5))
    for code in LEGS:
        lo_, sh_ = ctx.leg(code)
        assert lo_.dtype == bool and lo_.size == ctx.f.n and sh_.size == ctx.f.n


# ------------------------------------------------------------------ engine

def _frame_for_engine(prices, start=None):
    start = start or _utc_minute(2024, 1, 10, 15, 0)      # 10:00 ET
    f = resample(minute_clock(_minutes(start, prices)), 1)
    return f


def _run(f, sig_l, sig_s, *, entry="market", stop_type=0, stop_k=1.0, target_r=1.0, trail=0,
         atr=None, exit_tdm=None, cost=0.0, window=None):
    n = f.n
    atr = np.full(n, 1.0) if atr is None else atr
    ws, we, ex = SESSIONS["all"]
    if window:
        ws, we = window
    m = f.clock.m
    return run(sig_l, sig_s, f.h, f.l, f.hi, f.tdm_close.astype(np.int64), f.day, atr,
               f.l.copy(), f.h.copy(), m.t, m.o, m.h, m.l, m.c, f.clock.tdm.astype(np.int64),
               f.clock.day, f.m1_bar, ENTRY_CODE[entry], stop_type, stop_k, target_r, trail,
               ws, we, ex if exit_tdm is None else exit_tdm, cost, 0.01, 0, 4, 100)[:7]


def test_mae_records_the_worst_open_loss():
    # long at 100 (next open), dips to 99.4 (0.6R against a 1.0 ATR stop), then hits the 1R target at 101
    prices = [(100, 100, 100, 100), (100, 100.1, 99.4, 99.6), (99.6, 101.2, 99.6, 101.0)] + [(101, 101, 101, 101)] * 5
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool); sig[0] = True
    m = f.clock.m
    ws, we, ex = SESSIONS["all"]
    out = run(sig, np.zeros(f.n, bool), f.h, f.l, f.hi, f.tdm_close.astype(np.int64), f.day, np.full(f.n, 1.0),
              f.l.copy(), f.h.copy(), m.t, m.o, m.h, m.l, m.c, f.clock.tdm.astype(np.int64), f.clock.day,
              f.m1_bar, ENTRY_CODE["market"], 0, 1.0, 1.0, 0, ws, we, ex, 0.0, 0.01, 0, 4, 100)
    gross, mae = out[4], out[7]
    assert gross[0] == pytest.approx(1.0) and mae[0] == pytest.approx(-0.6)


def test_market_entry_fills_next_open_and_hits_target():
    prices = [(100, 100, 100, 100), (100.5, 100.6, 100.4, 100.5), (100.5, 101.6, 100.5, 101.5),
              (101.5, 101.6, 101.4, 101.5)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    e, x, d, dirs, gross, cost, why = _run(f, sig, np.zeros(f.n, bool))
    assert len(gross) == 1
    assert e[0] == f.clock.m.t[1]                    # filled on the bar after the signal
    assert why[0] == 1 and gross[0] == pytest.approx(1.0)


def test_stop_is_assumed_first_when_both_are_hit_in_one_minute():
    prices = [(100, 100, 100, 100), (100, 100, 100, 100), (100, 101.5, 98.5, 100)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    *_, gross, cost, why = _run(f, sig, np.zeros(f.n, bool))
    # entry at 100 (open of minute 1); minute 1 is flat, minute 2 spans both levels
    assert why[0] == 0 and gross[0] == pytest.approx(-1.0)


def test_gap_through_the_stop_fills_at_the_open():
    prices = [(100, 100, 100, 100), (100, 100, 100, 100), (97, 97.5, 96.5, 97)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    *_, gross, cost, why = _run(f, sig, np.zeros(f.n, bool))
    assert why[0] == 0 and gross[0] == pytest.approx(-3.0)


def test_short_side_and_costs_in_r():
    prices = [(100, 100, 100, 100), (100, 100, 100, 100), (100, 100.2, 98.9, 99)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    *_, dirs, gross, cost, why = _run(f, np.zeros(f.n, bool), sig, cost=0.25)
    assert dirs[0] == -1 and why[0] == 1
    assert gross[0] == pytest.approx(1.0) and cost[0] == pytest.approx(0.25)


def test_time_exit_at_session_end():
    # Entries allowed; flat at 10:03 ET.
    prices = [(100, 100, 100, 100)] + [(100 + k * 0.1, 100 + k * 0.1, 100 + k * 0.1, 100 + k * 0.1)
                                       for k in range(1, 8)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    e, x, d, dirs, gross, cost, why = _run(f, sig, np.zeros(f.n, bool), target_r=0.0,
                                            exit_tdm=_tdm(10, 3))
    assert why[0] == 3
    assert x[0] == f.clock.m.t[3]
    assert gross[0] == pytest.approx(0.2)            # exit at the 10:03 open (100.3) vs 100.1 entry


def test_never_carries_a_position_into_the_next_trading_day():
    start = _utc_minute(2024, 1, 10, 21, 55)          # 16:55 ET, 5 minutes before the day ends
    prices = [(100, 100, 100, 100)] * 3 + [(100.5, 100.5, 100.5, 100.5)] * 2
    m = _minutes(start, prices)
    # jump the last two minutes to the next trading day with a big gap
    m.t[3:] += 60 * 20
    m.o[3:] = m.h[3:] = m.l[3:] = m.c[3:] = 150.0
    f = resample(minute_clock(m), 1)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    *_, gross, cost, why = _run(f, sig, np.zeros(f.n, bool), target_r=0.0, exit_tdm=1439,
                                window=(0, 1439))
    assert why[0] == 3 and gross[0] == pytest.approx(0.0)   # flat at 100, not at the 150 gap


def test_stop_entry_waits_for_the_break():
    prices = [(100, 101, 99, 100), (100, 100.5, 99.5, 100), (100.6, 101.5, 100.5, 101.4),
              (101.4, 103.2, 101.3, 103)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    e, *_ , gross, cost, why = _run(f, sig, np.zeros(f.n, bool), entry="stop")
    assert e[0] == f.clock.m.t[2]                    # minute 1 never reached 101.01
    assert why[0] == 1 and gross[0] == pytest.approx(1.0)


def test_fill_minute_low_below_stop_counts_as_stopped():
    # The path inside the fill minute is unknown, so a low through the stop is a loss.
    prices = [(100, 101, 99, 100), (100, 100.5, 99.5, 100), (100, 101.5, 99.9, 101.4)]
    f = _frame_for_engine(prices)
    sig = np.zeros(f.n, bool)
    sig[0] = True
    *_, gross, cost, why = _run(f, sig, np.zeros(f.n, bool), entry="stop")
    assert why[0] == 0 and gross[0] == pytest.approx(-1.0)


# ------------------------------------------------------------------ metrics and generator

def test_metrics_basics():
    days = np.array([100, 101, 102, 103], dtype=np.int32)
    cal = Calendar(days=np.arange(95, 110), start=95, d3y=95, d12m=100, d6m=102, end=109,
                   month_ends=np.array([109]), month_labels=["x"])
    tr = {"gross": np.array([1.0, -1.0, 2.0, -1.0]), "cost": np.full(4, 0.1), "day": days,
          "dir": np.ones(4, np.int8), "reason": np.zeros(4, np.int8)}
    r = evaluate(tr, cal, seed=1)
    assert r["trades"] == 4 and r["win"] == 0.5
    assert r["net_r"] == pytest.approx(0.15)
    assert r["n6"] == 2 and r["r6"] == pytest.approx(0.8)
    assert r["max_dd"] == pytest.approx(1.1)
    assert max_drawdown(np.cumsum([1, -2, 1])) == pytest.approx(2)
    assert 0.0 <= r["p_pass"] <= 1.0


def test_generator_is_balanced_and_unique():
    strats = generate(per_family=12, controls_per_cell=1)
    ids = [s.sid for s in strats]
    assert len(ids) == len(set(ids))
    real = [s for s in strats if s.group != "Control"]
    assert len(real) == 12 * (len(FAMILIES) - 1)
    for s in strats[:50]:
        assert s.market in s.name and f"{s.tf}m" in s.name
        assert all(code in LEGS for code in s.legs)


def test_explorer_embeds_a_decodable_payload():
    import base64
    import gzip
    import json
    import re

    from confluence.explorer_html import render

    html = render({"rows": [[1, float("nan")]], "cols": ["a", "b"]})
    assert html.startswith("<!doctype html>") and "<title>Confluence Trade Explorer</title>" in html
    blob = re.search(r'<script id="data" type="text/plain">([^<]+)</script>', html).group(1)
    data = json.loads(gzip.decompress(base64.b64decode(blob)))
    assert data == {"rows": [[1, None]], "cols": ["a", "b"]}
    frag = render({"x": 1}, standalone=False)
    assert frag.startswith("<title>") and "<html" not in frag


def test_macro_tags_only_use_information_from_before_the_day():
    from confluence.macro import DIM_BY_KEY, tag_days

    ep = dt.date(1970, 1, 1)
    day = lambda s: (dt.date.fromisoformat(s) - ep).days
    flat = {f"2024-01-{d:02d}": 100.0 for d in range(1, 32)}
    macro = {
        "series": {"vix": {"2024-03-04": 12.0, "2024-03-05": 35.0}, "vix3m": {"2024-03-04": 14.0, "2024-03-05": 30.0},
                   "irx": flat, "tnx": flat, "dxy": flat, "spx": flat},
        "cpi": {"2024-01": 3.0, "2024-02": 5.0}, "fomc": ["2024-03-20"], "nfp": ["2024-03-08"]}
    days = np.array([day("2024-03-05"), day("2024-03-06"), day("2024-03-14"), day("2024-03-15"),
                     day("2024-03-20"), day("2024-03-08")])
    t = tag_days(days, macro)
    vix = DIM_BY_KEY["vix"].order
    # On 03-05 only the 03-04 close (12) is known; the 35 print counts from 03-06.
    assert vix[t["vix"][0]] == "VIX < 15" and vix[t["vix"][1]] == "VIX ≥ 30"
    assert DIM_BY_KEY["curve"].order[t["curve"][1]] == "backwardation"
    # February's CPI (5%) is only known from March 15.
    cpi = DIM_BY_KEY["cpi"].order
    assert cpi[t["cpi"][2]] == "CPI 2.5–4%" and cpi[t["cpi"][4]] == "CPI ≥ 4%"
    ev = DIM_BY_KEY["event"].order
    assert ev[t["event"][4]] == "FOMC day" and ev[t["event"][5]] == "jobs report day"


def test_nfp_rule_matches_known_release_days():
    from confluence.macro import nfp_dates

    got = set(nfp_dates(dt.date(2020, 1, 1), dt.date(2025, 3, 1)))
    for d in ("2024-10-04", "2025-02-07", "2020-08-07", "2020-07-02", "2021-04-02"):
        assert d in got
