"""Second run: the futures universe, the new confluence legs and the prop-account optimiser."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from confluence import components2  # noqa: F401  (registers the legs)
from confluence.accounts import (PLAN_BY_KEY, PLANS, _simulate, check_plans, daily_arrays, describe_units,
                                 price_trades, sizing_for)
from confluence.bars import PROP_SESSIONS, _tdm, minute_clock, resample
from confluence.components import LEGS, Ctx
from confluence.components2 import CATEGORY
from confluence.data import Minutes
from confluence.families2 import CATEGORIES, FAMILIES2, generate2
from confluence.futures import UNDERLYINGS, backtest_markets, load_propfirms


@pytest.fixture(scope="module")
def pf():
    return load_propfirms()


def _walk(n_days=12, seed=3, start=(2024, 3, 4)):
    t0 = int(dt.datetime(*start, 23, 0, tzinfo=dt.timezone.utc).timestamp()) // 60
    n = n_days * 1440
    rng = np.random.default_rng(seed)
    # trending stretches and reversals, so swings, patterns and breakouts appear
    drift = np.repeat(rng.normal(0, 0.02, n // 240 + 1), 240)[:n]
    c = 100 + np.cumsum(drift + rng.normal(0, 0.06, n))
    hi = c + np.abs(rng.normal(0, 0.04, n))
    lo = c - np.abs(rng.normal(0, 0.04, n))
    o = np.r_[c[0], c[:-1]]
    v = rng.integers(1, 50, n).astype(float)
    t = np.arange(t0, t0 + n, dtype=np.int64)
    return Minutes("TEST", t, o, np.maximum(hi, o), np.minimum(lo, o), c, {}, v)


def _cut(m: Minutes, k: int) -> Minutes:
    return Minutes(m.feed, m.t[:k], m.o[:k], m.h[:k], m.l[:k], m.c[:k], {}, m.v[:k])


# ------------------------------------------------------------------ legs

def test_new_legs_never_look_ahead():
    """Every leg's value on a bar must not change when later data is added."""
    m = _walk()
    tf = 5
    full = Ctx(resample(minute_clock(m), tf))
    k = int(m.t.size * 0.7)
    k -= k % tf                                   # cut on a bar boundary
    part = Ctx(resample(minute_clock(_cut(m, k)), tf))
    n = part.f.n - 1                              # the last bar of the cut series may be incomplete
    assert n > 1000
    fired = 0
    for code in CATEGORY:
        a_l, a_s = full.leg(code)
        b_l, b_s = part.leg(code)
        bad = np.flatnonzero((a_l[:n] != b_l[:n]) | (a_s[:n] != b_s[:n]))
        assert bad.size == 0, f"{code} changes on bar {bad[0]} when later data arrives"
        fired += int(a_l.any() or a_s.any())
    assert fired > 0.7 * len(CATEGORY)            # most legs actually fire on this data


def test_every_family_is_categorised_and_uses_known_legs():
    for f in FAMILIES2:
        if f.group == "Control":
            continue
        assert f.group in CATEGORIES
        assert all(c in LEGS for c in f.legs + f.extras)
    cats = {f.group for f in FAMILIES2 if f.group != "Control"}
    assert cats == set(CATEGORIES)                 # all 19 requested confluences are covered


def test_generator_reaches_twenty_thousand_unique_strategies():
    ss = generate2()
    assert len(ss) >= 20_000
    assert len({s.sid for s in ss}) == len(ss)
    assert {s.market for s in ss} == set(UNDERLYINGS)
    assert all(s.session in PROP_SESSIONS for s in ss)


def test_prop_sessions_are_flat_before_the_firms_cutoff():
    for ws, we, ex in PROP_SESSIONS.values():
        assert ex <= _tdm(16, 10)                  # 3:10 PM Chicago = 4:10 PM New York


# ------------------------------------------------------------------ products and plans

def test_plans_match_the_researched_rules(pf):
    assert check_plans(pf) == []
    assert len(PLANS) == 15


def test_backtest_costs_use_the_smallest_contract(pf):
    mk = backtest_markets(pf)
    # MNQ: $1.22 round trip / $2 a point + 2 ticks of 0.25
    assert mk["NQ"].cost_rt == pytest.approx(1.22 / 2.0 + 0.5)
    assert set(mk) == set(UNDERLYINGS)


def test_sizing_respects_each_firms_product_list(pf):
    fn_6e = sizing_for(pf, "FundedNext", UNDERLYINGS["6E"])
    assert fn_6e.unit.symbol == "6E"               # FundedNext does not list M6E
    ts_si = sizing_for(pf, "Topstep", UNDERLYINGS["SI"])
    assert ts_si.unit.symbol == "SIL" and [c.symbol for c, _, _ in ts_si.ladder] == ["SIL"]   # SI is capped at 0
    assert ts_si.product_cap[50_000] == 2
    assert sizing_for(pf, "FundedNext", UNDERLYINGS["ZB"]) is None


def test_price_trades_buys_minis_for_ten_micros_and_charges_costs(pf):
    sz = sizing_for(pf, "Topstep", UNDERLYINGS["NQ"])
    gross = np.array([1.0, -1.0])
    risk_pts = np.array([12.5, 12.5])              # 12.5 NQ points = $25 per MNQ
    pnl, u = price_trades(gross, risk_pts, sz, 250.0, cap_minis=5, size=50_000)
    assert list(u) == [10, 10]                      # 10 MNQ = 1 NQ
    assert describe_units(sz, 10) == "1 NQ"
    cost = 3.78 + 2 * 0.25 * 20.0
    assert pnl[0] == pytest.approx(250.0 - cost) and pnl[1] == pytest.approx(-250.0 - cost)
    # capped at 2 minis
    pnl, u = price_trades(np.array([1.0]), np.array([12.5]), sz, 2000.0, cap_minis=2, size=50_000)
    assert list(u) == [20]
    # a stop so wide that one micro risks more than 1.5x the target is skipped
    pnl, u = price_trades(np.array([1.0]), np.array([200.0]), sz, 250.0, cap_minis=5, size=50_000)
    assert list(u) == [0] and pnl[0] == 0.0


def test_daily_arrays_apply_a_soft_daily_loss_limit():
    day = np.array([0, 0, 0, 1], dtype=np.int64)
    pnl = np.array([-300.0, -300.0, 900.0, 100.0])
    out, low, cnt = daily_arrays(day, pnl, 3, 500.0)
    assert out[0] == -600.0 and low[0] == -600.0 and cnt[0] == 2   # stopped after the limit
    assert out[1] == 100.0 and cnt[2] == 0


def _run(plan, daily, sims=4, days=40, low=None):
    n = daily.size
    e_low = np.minimum(daily, 0.0) if low is None else low
    cnt = (daily != 0).astype(np.int32)
    starts = np.zeros((sims, days // 5), dtype=np.int64)
    starts[:] = np.arange(0, days, 5)[None, :] % max(n - 5, 1)
    fp = np.stack([daily] * len(plan.f_caps))
    fl = np.stack([e_low] * len(plan.f_caps))
    fc = np.stack([cnt] * len(plan.f_caps))
    return _simulate(daily, e_low, cnt, fp, fl, fc, np.array(plan.f_tiers, dtype=np.float64), starts, starts,
                     plan.target, plan.mll, plan.lock, plan.cons, plan.min_days, plan.price, plan.monthly,
                     plan.activation, plan.f_mll, plan.f_lock, plan.f_lock_paid, plan.pay_mode, plan.pay_thr,
                     plan.pay_cap, plan.pay_min, plan.pay_frac, plan.split, plan.fee, plan.max_pay, days, days, 5, 21)


def test_topstep_combine_passes_pays_and_charges_fees():
    plan = PLAN_BY_KEY["TS-50K"]
    outcome, edays, cost, paid, npay, fbust = _run(plan, np.full(60, 1000.0))
    assert outcome[0] == 1 and edays[0] == 3            # $3,000 target in three $1,000 days
    assert cost[0] == pytest.approx(49.0 + 149.0)       # one month plus activation
    # funded: 5 winning days, then 50% of the balance capped at $2,000, 90% to the trader
    assert npay[0] >= 1 and paid[0] >= 2000.0 * 0.9


def test_consistency_rule_raises_the_target():
    plan = PLAN_BY_KEY["TS-50K"]
    daily = np.r_[2200.0, np.full(59, 100.0)]            # best day 2,200 > 55% of 3,000
    outcome, edays, *_ = _run(plan, daily)
    # target becomes 2,200 / 0.55 = 4,000: 2,200 + 18 x 100
    assert outcome[0] == 1 and edays[0] == 19


def test_trailing_max_loss_and_inactivity_end_the_evaluation():
    plan = PLAN_BY_KEY["FN-RP-50K"]
    outcome, edays, cost, paid, *_ = _run(plan, np.full(60, -500.0))
    assert outcome[0] == -1 and edays[0] == 4 and paid[0] == 0.0
    assert cost[0] == pytest.approx(plan.price)
    outcome, edays, *_ = _run(plan, np.zeros(60))
    assert outcome[0] == -1 and edays[0] == 21           # ~30 calendar days without a trade
