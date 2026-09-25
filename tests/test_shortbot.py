"""shortbot: fills, short P&L, no look-ahead, and the Topstep account rules."""
from dataclasses import replace

import numpy as np
import pytest

from shortbot import backtest as bt
from shortbot.config import AccountRules, BotConfig, RiskParams, StrategyParams
from shortbot.data import Session, session_from_bars, to_sessions
from shortbot.strategy import DayState, Entry, Profile, ShortStrategy

RISK = RiskParams(risk_per_trade_usd=250, max_contracts=1, max_stop_risk_usd=10_000,
                  commission_rt=1.22, slippage_ticks=1)


def make_session(date, closes, start=570, bar=5, wick=2.0, volume=100.0):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    rows = [(start + bar * k, o, max(o, c) + wick, min(o, c) - wick, c, volume)
            for k, (o, c) in enumerate(zip(opens, closes))]
    return session_from_bars(date, bar, rows)


class EnterAt(ShortStrategy):
    """Signals a short with fixed stop/target once, after bar ``at`` closes."""

    def __init__(self, at, stop=20.0, target=30.0, params=None):
        super().__init__(params or StrategyParams(skip_fomc=False))
        self.at, self.stop, self.target = at, stop, target

    def decide(self, s, i, day, prof):
        if i == self.at and day.trades == 0 and not day.in_position:
            return Entry("test", self.stop, self.target, "test")
        return None


# ------------------------------------------------------------------- fills

def test_short_profits_when_price_falls_and_pays_costs():
    closes = [100.0] * 5 + [100.0 - 5 * k for k in range(1, 40)]
    s = make_session("2026-01-05", [x + 20000 for x in closes])
    (t,) = bt.run_session(s, EnterAt(at=3, stop=50, target=30), None, RISK)
    assert t.exit_reason == "target"
    assert t.entry == pytest.approx(s.open[4] - 0.25)            # one tick of slippage
    assert t.pnl_usd == pytest.approx(30 * 2.0 - 1.22)            # $2/pt, minus commission
    assert t.pnl_usd > 0


def test_short_loses_when_price_rises_and_stop_fills_worse():
    closes = [100.0] * 5 + [100.0 + 5 * k for k in range(1, 40)]
    s = make_session("2026-01-05", [x + 20000 for x in closes])
    (t,) = bt.run_session(s, EnterAt(at=3, stop=20, target=30), None, RISK)
    assert t.exit_reason == "stop"
    assert t.exit == pytest.approx(t.entry + 20 + 0.25)
    assert t.pnl_usd == pytest.approx(-(20.25 * 2.0) - 1.22)
    assert t.mae_usd <= t.pnl_usd


def test_stop_assumed_first_when_one_bar_hits_both():
    closes = [20000.0] * 60
    s = make_session("2026-01-05", closes)
    s.high[5] = s.open[5] + 100      # the bar after entry spikes both ways
    s.low[5] = s.open[5] - 100
    (t,) = bt.run_session(s, EnterAt(at=3, stop=20, target=30), None, RISK)
    assert t.exit_reason == "stop"


def test_target_needs_a_tick_of_trade_through():
    s = make_session("2026-01-05", [20000.0] * 60, wick=0.0)
    entry = s.open[4] - 0.25
    s.low[6] = entry - 30             # touches the target exactly, no trade-through
    (t,) = bt.run_session(s, EnterAt(at=3, stop=500, target=30), None, RISK)
    assert t.exit_reason != "target"


def test_positions_are_flat_by_the_flatten_time():
    closes = [20000.0] * 78            # 09:30 .. 15:55
    s = make_session("2026-01-05", closes)
    p = StrategyParams(skip_fomc=False, max_hold_minutes=10_000)
    at = int((15 * 60 + 30 - 570) / 5)  # enter around 15:35
    (t,) = bt.run_session(s, EnterAt(at=at, stop=500, target=500, params=p), None, RISK)
    assert t.exit_reason == "flatten"
    assert t.exit_minute <= p.flatten_minute
    assert t.exit_minute < AccountRules().flat_by_minute


def test_decisions_never_use_future_bars():
    rng = np.random.default_rng(3)
    prior = [make_session(f"2026-01-{d:02d}", 20000 + np.cumsum(rng.normal(0, 8, 78)))
             for d in range(5, 17)]
    today_closes = 20000 + np.cumsum(rng.normal(-3, 12, 78))
    full = make_session("2026-01-19", today_closes)
    strat = ShortStrategy(StrategyParams(skip_fomc=False))
    prof = strat.profile(prior)
    for i in range(len(full) - 1):
        cut = Session(full.date, 5, full.minute[:i + 1], full.open[:i + 1], full.high[:i + 1],
                      full.low[:i + 1], full.close[:i + 1], full.volume[:i + 1])
        a = strat.decide(full, i, DayState(), prof)
        b = strat.decide(cut, i, DayState(), prof)
        assert (a is None) == (b is None)
        if a is not None:
            assert (a.setup, a.stop_pts, a.target_pts) == (b.setup, b.stop_pts, b.target_pts)


def test_momentum_fires_on_a_big_drop_below_vwap():
    prior = [make_session(f"2026-01-{d:02d}", [20000.0 + (k % 2) * 4 for k in range(78)])
             for d in range(5, 17)]
    closes = [20000.0] * 20 + [20000.0 - 10 * k for k in range(1, 20)] + [19810.0] * 39
    s = make_session("2026-01-19", closes)
    strat = ShortStrategy(StrategyParams(skip_fomc=False, orb=False, vwap_reject=False))
    prof = strat.profile(prior)
    hits = [strat.decide(s, i, DayState(), prof) for i in range(len(s) - 1)]
    fired = [e for e in hits if e is not None]
    assert fired and fired[0].setup == "momentum"


def test_day_limits_cap_trades():
    rng = np.random.default_rng(0)
    sessions = [make_session(f"2026-02-{d:02d}", 20000 + np.cumsum(rng.normal(-2, 15, 78)))
                for d in range(2, 28) if d % 7 not in (0, 1)]
    cfg = BotConfig()
    cfg.strategy = replace(cfg.strategy, max_trades_per_day=2, skip_fomc=False)
    trades = bt.run(sessions, cfg)
    per_day = {}
    for t in trades:
        per_day[t.date] = per_day.get(t.date, 0) + 1
    assert trades and max(per_day.values()) <= 2
    assert all(t.contracts <= cfg.risk.max_contracts for t in trades)


def test_size_trade_skips_stops_that_are_too_wide():
    r = RiskParams(risk_per_trade_usd=250, max_contracts=3, max_stop_risk_usd=400)
    assert bt.size_trade(Entry("x", 300, 300, ""), r) == 0      # $600 a lot: skip
    assert bt.size_trade(Entry("x", 40, 60, ""), r) == 3        # $81 a lot: capped at 3
    assert bt.size_trade(Entry("x", 150, 200, ""), r) == 1


# --------------------------------------------------------- Topstep account

def T(date, pnl, mae=None):
    return bt.Trade(date, "t", 600, 610, 0, 0, 1, 0, 0, pnl, pnl if mae is None else mae, "x", "")


def test_combine_passes_at_target():
    days = [f"d{k:02d}" for k in range(10)]
    trades = {d: [T(d, 700)] for d in days}
    a = bt.combine_attempt(trades, days, AccountRules())
    assert a.outcome == "passed" and a.days == 5          # 5 x $700 = $3,500 >= $3,000


def test_consistency_rule_raises_the_target():
    days = [f"d{k:02d}" for k in range(10)]
    trades = {days[0]: [T(days[0], 2500)], **{d: [T(d, 100)] for d in days[1:]}}
    a = bt.combine_attempt(trades, days, AccountRules())
    # best day $2,500 -> target becomes $2,500 / 0.55 = $4,545, not reached in 10 days
    assert a.outcome == "unfinished"


def test_trailing_max_loss_fails_the_account():
    days = ["d1", "d2", "d3"]
    rules = AccountRules(daily_loss=0)                      # no DLL: only the MLL protects
    trades = {"d1": [T("d1", 1000)], "d2": [T("d2", -500)], "d3": [T("d3", -600, mae=-1600)]}
    # EOD high 51,000 -> MLL 49,000; d3 starts at 50,500 and dips to 48,900
    a = bt.combine_attempt(trades, days, rules)
    assert a.outcome == "failed" and a.days == 3


def test_max_loss_stops_trailing_at_the_start_balance():
    days = ["d1", "d2", "d3"]
    rules = AccountRules(daily_loss=0, profit_target=10_000, consistency=0)
    trades = {"d1": [T("d1", 2900)], "d2": [T("d2", -2800)], "d3": [T("d3", 0)]}
    # after d1 the MLL would be 50,900 but locks at 50,000; d2 ends at 50,100 -> alive
    a = bt.combine_attempt(trades, days, rules)
    assert a.outcome == "unfinished"


def test_daily_loss_limit_pauses_instead_of_failing():
    days = ["d1", "d2"]
    trades = {"d1": [T("d1", -300, mae=-1200), T("d1", -300)], "d2": []}
    a = bt.combine_attempt(trades, days, AccountRules())
    assert a.outcome == "unfinished"
    assert a.profit == pytest.approx(-1000)                # flattened at the DLL, day over


def test_config_round_trip_and_rejects_typos():
    cfg = BotConfig()
    assert BotConfig.from_dict(cfg.to_dict()) == cfg
    with pytest.raises(ValueError):
        BotConfig.from_dict({"strategy": {"mom_kk": 2}})


def test_sessions_group_rth_in_new_york_time():
    # 2026-01-05 14:30 UTC = 09:30 New York (EST)
    rows = [(1767623400 + 300 * k, 1, 2, 0.5, 1.5, 10) for k in range(3)]
    rows.append((1767623400 - 3600, 1, 2, 0.5, 1.5, 10))    # 08:30: pre-market, dropped
    (s,) = to_sessions(rows, 5)
    assert s.date == "2026-01-05" and list(s.minute) == [570, 575, 580]


def test_profile_uses_the_same_time_of_day():
    a = make_session("2026-01-05", [100.0, 110.0, 100.0, 100.0], wick=0.0)
    prof = Profile([a], [5])
    assert prof.normal(5, 575) == pytest.approx(10.0)
    assert np.isnan(prof.normal(5, 900))


# ------------------------------------------------ Express Funded + whole plan

def test_funded_account_pays_half_after_five_winning_days():
    rules = AccountRules(daily_loss=0)
    days = [f"d{k:02d}" for k in range(5)]
    f = bt.funded_attempt({d: [T(d, 400)] for d in days}, days, rules)
    # $2,000 balance -> request half ($1,000, under the $2,000 cap) -> 90% to the trader
    assert (f.outcome, f.payouts) == ("running", 1)
    assert f.paid_to_trader == pytest.approx(900.0) and f.first_payout_day == 5


def test_after_the_first_payout_the_balance_is_the_only_cushion():
    rules = AccountRules(daily_loss=0)
    days = [f"d{k:02d}" for k in range(6)]
    trades = {d: [T(d, 400)] for d in days[:5]}
    trades[days[5]] = [T(days[5], -1100)]         # balance after payout is $1,000
    f = bt.funded_attempt(trades, days, rules)
    assert f.outcome == "blown" and f.payouts == 1


def test_whole_plan_charges_fees_and_counts_payouts():
    rules = AccountRules(daily_loss=0)
    days = [f"d{k:02d}" for k in range(20)]
    trades = {d: [T(d, 700)] for d in days}       # passes in 5 days, then pays out
    c = bt.cycle(trades, days, rules)
    assert c.combines_passed == 1 and c.payouts >= 1
    assert c.fees == pytest.approx(rules.monthly_fee + rules.activation_fee + rules.api_fee)
    assert c.net == pytest.approx(c.paid_to_trader - c.fees)
    assert c.story[0].startswith("d00  Combine passed")


def test_failed_combine_reports_the_loss_at_the_limit():
    days = ["d1"]
    rules = AccountRules(daily_loss=0)
    a = bt.combine_attempt({"d1": [T("d1", -2500, mae=-2600)]}, days, rules)
    assert a.outcome == "failed" and a.profit == pytest.approx(-2000)



def test_long_profits_when_price_rises():
    closes = [20000.0] * 5 + [20000.0 + 5 * k for k in range(1, 40)]
    s = make_session("2026-01-05", closes)

    class Long(EnterAt):
        def decide(self, s, i, day, prof):
            e = super().decide(s, i, day, prof)
            return Entry(e.setup, e.stop_pts, e.target_pts, e.reason, +1) if e else None

    (t,) = bt.run_session(s, Long(at=3, stop=50, target=30), None, RISK)
    assert t.side == 1 and t.exit_reason == "target"
    assert t.entry == pytest.approx(s.open[4] + 0.25)          # a buy pays a tick up
    assert t.pnl_usd == pytest.approx(30 * 2.0 - 1.22) and t.points == pytest.approx(30)


def test_basic_follow_buys_green_runs_and_fade_sells_them():
    prior = [make_session(f"2026-01-{d:02d}", [20000.0 + (k % 2) * 4 for k in range(78)])
             for d in range(5, 17)]
    closes = [20000.0] * 20 + [20000.0 + 12 * k for k in range(1, 10)] + [20108.0] * 49
    s = make_session("2026-01-19", closes)
    for mode, side in (("follow", 1), ("fade", -1)):
        strat = ShortStrategy(StrategyParams(skip_fomc=False, orb=False, momentum=False,
                                             vwap_reject=False, basic=True, basic_mode=mode))
        prof = strat.profile(prior)
        fired = [e for e in (strat.decide(s, i, DayState(), prof) for i in range(len(s) - 1)) if e]
        assert fired and fired[0].setup == "basic" and fired[0].side == side


def test_config_rejects_an_unknown_basic_mode():
    with pytest.raises(ValueError):
        BotConfig.from_dict({"strategy": {"basic_mode": "sideways"}})


# --------------------------------------------------- fixes found in review

def test_expiry_weeks_are_the_weeks_of_the_third_friday():
    from shortbot.data import expiry_week
    assert expiry_week("2025-12-16") and expiry_week("2025-12-19")       # Dec 2025 expiry: 19th
    assert expiry_week("2026-09-14") and not expiry_week("2026-09-11")   # Sep 2026: 18th
    assert not expiry_week("2025-12-22") and not expiry_week("2025-11-18")


def test_broken_price_jumps_and_expiry_weeks_are_dropped():
    from shortbot.data import clean_sessions
    ok = make_session("2026-01-05", [20000.0 + k for k in range(78)])
    jumpy = make_session("2026-01-06", [20000.0 + k for k in range(78)])
    jumpy.open[40] += 240                                   # contract switch mid-session
    expiry = make_session("2026-03-18", [20000.0 + k for k in range(78)])
    dropped = []
    kept = clean_sessions([ok, jumpy, expiry], True, dropped)
    assert [s.date for s in kept] == ["2026-01-05"]
    assert {d for d, _ in dropped} == {"2026-01-06", "2026-03-18"}


def test_unfinished_today_and_off_grid_rows_are_dropped():
    from datetime import datetime, timezone
    from shortbot.data import NY, _drop_unfinished_today, _on_grid, to_sessions
    base = 1767623400                                        # 2026-01-05 09:30 New York
    rows = [(base + 300 * k, 1, 2, 0.5, 1.5, 10) for k in range(70)]
    rows.append((base + 300 * 69 + 43, 1, 9, 0.1, 1.5, 10))  # a live quote at 15:15:43
    assert len(_on_grid(rows, 5)) == 70
    ss = to_sessions(_on_grid(rows, 5), 5)
    during = datetime(2026, 1, 5, 15, 20, tzinfo=NY)
    after = datetime(2026, 1, 5, 16, 30, tzinfo=NY)
    assert _drop_unfinished_today(ss, during) == []
    assert len(_drop_unfinished_today(ss, after)) == 1


def test_a_csv_with_the_wrong_bar_size_is_refused(tmp_path):
    from shortbot.data import load_sessions
    path = tmp_path / "one_minute.csv"
    path.write_text("\n".join(f"{1767623400 + 60 * k},1,2,0.5,1.5,10" for k in range(500)))
    with pytest.raises(ValueError, match="1-minute bars"):
        load_sessions(str(path), bar_minutes=5)


def test_fed_days_flatten_before_2pm_and_resume_after():
    strat = ShortStrategy(StrategyParams(skip_fomc=True))
    fed = "2026-07-29"
    assert strat.deadline(fed, 12 * 60) == 13 * 60 + 55     # opened before: out by 13:55
    assert strat.deadline(fed, 14 * 60 + 50) == 15 * 60 + 50  # opened after the resume
    s = make_session(fed, [20000.0] * 78)
    prof = Profile([make_session("2026-07-28", [20000.0 + (k % 2) * 4 for k in range(78)])], [30])
    at = lambda hhmm: int((hhmm - 570) / 5) - 1                # bar whose close is hhmm
    assert strat.entry_unit(s, at(13 * 60 + 40), DayState(), prof) == 0   # blackout
    assert strat.entry_unit(s, at(14 * 60 + 50), DayState(), prof) > 0    # resumed


def test_no_signal_from_a_bar_that_began_before_the_open():
    strat = ShortStrategy(StrategyParams(skip_fomc=False, first_entry_minute=0))
    rows = [(540 + 60 * k, 20000.0, 20010.0, 19990.0, 20000.0, 1.0) for k in range(7)]
    s = session_from_bars("2026-01-05", 60, rows)             # hourly: 09:00 .. 15:00
    prof = Profile([session_from_bars("2026-01-02", 60, rows)], [30, 60])
    assert strat.entry_unit(s, 0, DayState(), prof) == 0      # the 09:00 bar
    assert strat.entry_unit(s, 1, DayState(), prof) > 0       # the 10:00 bar


def test_stops_and_targets_sit_on_the_tick_grid():
    assert bt.stop_price(20000.25, -1, 40.1, 0.25) == 20040.5    # short: rounded up, away
    assert bt.stop_price(20000.25, +1, 40.1, 0.25) == 19960.0    # long: rounded down, away
    assert bt.target_price(20000.25, -1, 60.1, 0.25) == 19940.25


def test_backtest_caps_size_at_the_account_limit():
    closes = [20000.0] * 5 + [20000.0 - 5 * k for k in range(1, 40)]
    s = make_session("2026-01-05", closes)
    r = RiskParams(risk_per_trade_usd=1e9, max_contracts=500, max_stop_risk_usd=1e9)
    (t,) = bt.run_session(s, EnterAt(at=3, stop=5, target=30), None, r, max_contracts=50)
    assert t.contracts == 50


def test_a_signal_is_skipped_when_the_next_bar_is_missing():
    s = make_session("2026-01-05", [20000.0] * 60)
    keep = np.ones(len(s), bool)
    keep[4] = False                                          # bar after the signal is missing
    gap = Session(s.date, 5, s.minute[keep], s.open[keep], s.high[keep], s.low[keep],
                  s.close[keep], s.volume[keep])
    assert bt.run_session(gap, EnterAt(at=3), None, RISK) == []


def test_fees_follow_topstep_billing():
    rules = AccountRules(daily_loss=0, api_fee=0.0)
    days = [f"d{k:02d}" for k in range(60)]
    # fail on day 3, then pass on day 8: purchase + one paid reset (no credit yet)
    trades = {"d02": [T("d02", -2100, mae=-2100)], **{d: [T(d, 700)] for d in days[3:8]}}
    c = bt.cycle(trades, days[:8], rules)
    assert c.combine_fails == 1 and c.combines_passed == 1
    assert c.fees == pytest.approx(rules.monthly_fee + rules.reset_fee)   # passed on the last day: no activation
    # an attempt that runs 30 trading days pays one rebill and earns a credit,
    # which then covers the reset after it fails
    long = {"d29": [T("d29", -2100, mae=-2100)], **{d: [T(d, 700)] for d in days[30:35]}}
    c = bt.cycle(long, days[:40], rules)
    assert c.fees == pytest.approx(2 * rules.monthly_fee + rules.activation_fee)
    # failing on the last day of data buys no reset
    c = bt.cycle({"d02": [T("d02", -2100, mae=-2100)]}, days[:3], rules)
    assert c.fees == pytest.approx(rules.monthly_fee)


def test_fundednext_billing_is_per_challenge():
    from shortbot.config import FUNDEDNEXT_ACCOUNTS
    rules = FUNDEDNEXT_ACCOUNTS["fn-legacy-25k"]
    days = [f"d{k:02d}" for k in range(80)]
    # a 30-day attempt that fails, then a pass: no rebill, one reset, no activation
    trades = {"d29": [T("d29", -1100, mae=-1100)], **{d: [T(d, 300)] for d in days[30:36]}}
    c = bt.cycle(trades, days[:40], rules)
    assert c.combine_fails == 1 and c.combines_passed == 1
    assert c.fees == pytest.approx(79.99 + 73.99)


def test_fundednext_payouts_need_500_since_the_last_one():
    from shortbot.config import FUNDEDNEXT_ACCOUNTS
    rules = FUNDEDNEXT_ACCOUNTS["fn-legacy-25k"]
    days = [f"d{k:02d}" for k in range(6)]
    small = bt.funded_attempt({d: [T(d, 99 + 2)] for d in days}, days, rules)
    # day 5: five $101 benchmark days and $505 profit -> half of it, 80% to the trader
    assert small.payouts == 1 and small.paid_to_trader == pytest.approx(0.8 * 252.5)
    four = bt.funded_attempt({d: [T(d, 101)] for d in days[:4]}, days[:4], rules)
    assert four.payouts == 0                                                    # only 4 benchmark days
    tiny = bt.funded_attempt({d: [T(d, 95)] for d in days}, days, rules)        # no benchmark days
    assert tiny.payouts == 0


def test_payout_keep_leaves_a_cushion():
    rules = AccountRules(daily_loss=0, payout_keep=1_500.0)
    days = [f"d{k:02d}" for k in range(5)]
    f = bt.funded_attempt({d: [T(d, 400)] for d in days}, days, rules)
    # balance $2,000: half would be $1,000, but only $500 can go while keeping $1,500
    assert f.payouts == 1 and f.paid_to_trader == pytest.approx(0.9 * 500)
