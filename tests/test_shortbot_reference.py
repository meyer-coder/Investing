"""Differential tests: a second, deliberately plain implementation of the
fill rules and the Topstep account rules, checked against the real engine on
the real cached market data, trade by trade and attempt by attempt.

The reference code below is written separately from shortbot/backtest.py,
with longs and shorts spelled out instead of mirrored, so a sign error or an
off-by-one in the engine shows up as a mismatch.  Skipped when the cached
Yahoo data is not present (run `python -m shortbot backtest` once to fetch it).
"""
import math
import os

import pytest

from shortbot import backtest as bt
from shortbot.config import BotConfig
from shortbot.data import CACHE_DIR, Session, load_sessions
from shortbot.strategy import DayState, ShortStrategy

TICK = 0.25
PV = 2.0
COMM = 1.22
SLIP = 0.25


def _cached(source):
    name = {"yahoo": "NQ_F_5m_60d_ohlcv.csv", "yahoo-hourly": "NQ_F_60m_730d_ohlcv.csv"}[source]
    return os.path.exists(os.path.join(CACHE_DIR, name))


CONFIGS = {
    "default": BotConfig(),
    "bigdrop": BotConfig.load("configs/shortbot-bigdrop.json"),
    "bigdrop-100k": BotConfig.load("configs/shortbot-bigdrop-100k.json"),
    "basic-follow": BotConfig.load("configs/shortbot-basic.json"),
}
_fade = BotConfig.load("configs/shortbot-basic.json")
_fade.strategy.basic_mode = "fade"
CONFIGS["basic-fade"] = _fade

CASES = [(src, name) for src in ("yahoo", "yahoo-hourly") for name in CONFIGS]


# ---------------------------------------------------------------- reference fills

def ref_trade(s: Session, k: int, side: int, stop: float, target: float,
              max_hold: int, flat_at: int):
    """Enter at the open of bar k (price already includes slippage in
    ``entry`` below) and walk forward.  Returns (exit price, reason, worst price)."""
    entry_min = int(s.minute[k])
    if side == 1:
        entry = float(s.open[k]) + SLIP
    else:
        entry = float(s.open[k]) - SLIP
    worst = entry
    for j in range(k, len(s)):
        m, o, h, lo, c = (int(s.minute[j]), float(s.open[j]), float(s.high[j]),
                          float(s.low[j]), float(s.close[j]))
        if side == 1:                                    # ---- long
            if m >= flat_at:
                return o - SLIP, "flatten", min(worst, o - SLIP)
            if j > k and o <= stop:
                return o - SLIP, "stop (gap)", min(worst, o - SLIP)
            if lo <= stop:
                return stop - SLIP, "stop", min(worst, stop - SLIP)
            worst = min(worst, lo)
            if h >= target + TICK:
                return target, "target", worst
            if m + s.bar_minutes > flat_at:
                return c - SLIP, "flatten", worst
            if m + s.bar_minutes - entry_min >= max_hold:
                return c - SLIP, "time", worst
            if j == len(s) - 1:
                return c - SLIP, "session end", worst
        else:                                            # ---- short
            if m >= flat_at:
                return o + SLIP, "flatten", max(worst, o + SLIP)
            if j > k and o >= stop:
                return o + SLIP, "stop (gap)", max(worst, o + SLIP)
            if h >= stop:
                return stop + SLIP, "stop", max(worst, stop + SLIP)
            worst = max(worst, h)
            if lo <= target - TICK:
                return target, "target", worst
            if m + s.bar_minutes > flat_at:
                return c + SLIP, "flatten", worst
            if m + s.bar_minutes - entry_min >= max_hold:
                return c + SLIP, "time", worst
            if j == len(s) - 1:
                return c + SLIP, "session end", worst
    raise AssertionError("trade never closed")


@pytest.mark.parametrize("source,name", CASES)
def test_every_trade_matches_the_reference_fills(source, name):
    if not _cached(source):
        pytest.skip("no cached data")
    cfg = CONFIGS[name]
    sessions = {s.date: s for s in load_sessions(source)}
    trades = bt.run(list(sessions.values()), cfg)
    strat = ShortStrategy(cfg.strategy)
    assert trades, "expected some trades"
    for t in trades:
        s = sessions[t.date]
        k = int(list(s.minute).index(t.entry_minute))
        # the signal bar is the one just before the entry bar, and they touch
        assert k >= 1 and int(s.minute[k - 1]) + s.bar_minutes == t.entry_minute
        exit_px, why, worst = ref_trade(s, k, t.side, t.stop, t.target,
                                        cfg.strategy.max_hold_minutes,
                                        strat.deadline(t.date, t.entry_minute))
        # stops and targets are real prices: on the 0.25 tick grid
        assert (t.stop / TICK) == pytest.approx(round(t.stop / TICK))
        assert (t.target / TICK) == pytest.approx(round(t.target / TICK))
        assert why == t.exit_reason, (t, why)
        assert exit_px == pytest.approx(t.exit), (t, exit_px)
        if t.side == 1:
            pts, adverse = exit_px - t.entry, worst - t.entry
        else:
            pts, adverse = t.entry - exit_px, t.entry - worst
        assert t.pnl_usd == pytest.approx(round(pts * PV * t.contracts - COMM * t.contracts, 2))
        mae = min(0.0, adverse * PV * t.contracts) - COMM * t.contracts
        assert t.mae_usd == pytest.approx(round(min(mae, t.pnl_usd), 2))
        # stop and target sit on the correct sides of the entry
        if t.side == 1:
            assert t.stop < t.entry < t.target
        else:
            assert t.target < t.entry < t.stop


@pytest.mark.parametrize("source,name", CASES)
def test_trades_respect_the_day_rules(source, name):
    if not _cached(source):
        pytest.skip("no cached data")
    cfg = CONFIGS[name]
    p, r = cfg.strategy, cfg.risk
    sessions = load_sessions(source)
    bar = sessions[0].bar_minutes
    trades = bt.run(sessions, cfg)
    by_day = {}
    for t in trades:
        by_day.setdefault(t.date, []).append(t)
    for day, ts in by_day.items():
        assert len(ts) <= p.max_trades_per_day
        losses, pnl = 0, 0.0
        for a, b in zip(ts, ts[1:]):
            assert b.entry_minute >= a.exit_minute            # one position at a time
        for t in ts:
            assert not (losses >= p.max_losses_per_day)       # no entry after the loss cap
            assert -r.daily_loss_stop_usd < pnl < r.daily_profit_stop_usd
            assert 1 <= t.contracts <= min(r.max_contracts, cfg.account.max_contracts)
            losses += t.pnl_usd < 0
            pnl += t.pnl_usd
        for t in ts:
            # out by the deadline, or at the close of the bar it falls inside
            flat = ShortStrategy(p).deadline(day, t.entry_minute)
            assert t.exit_minute <= flat or t.exit_minute - bar < flat, (day, t)
            assert t.entry_minute - bar >= 9 * 60 + 30     # the signal bar began at/after 09:30


@pytest.mark.parametrize("source", ["yahoo", "yahoo-hourly"])
def test_decisions_on_real_data_never_use_later_bars(source):
    if not _cached(source):
        pytest.skip("no cached data")
    cfg = BotConfig()
    cfg.strategy.basic = True
    strat = ShortStrategy(cfg.strategy)
    sessions = load_sessions(source)
    need = cfg.strategy.profile_days
    checked = fired = 0
    for d in range(need, min(len(sessions), need + 60)):
        full = sessions[d]
        prof = strat.profile(sessions[d - need:d])
        for i in range(len(full) - 1):
            cut = Session(full.date, full.bar_minutes, full.minute[:i + 1], full.open[:i + 1],
                          full.high[:i + 1], full.low[:i + 1], full.close[:i + 1],
                          full.volume[:i + 1])
            a, b = strat.decide(full, i, DayState(), prof), strat.decide(cut, i, DayState(), prof)
            assert (a is None) == (b is None)
            if a:
                fired += 1
                assert (a.setup, a.side, a.stop_pts, a.target_pts) == \
                    (b.setup, b.side, b.stop_pts, b.target_pts)
            checked += 1
    assert checked > 100 and fired > 0


# ---------------------------------------------------------- reference account rules

def ref_combine(trades_by_day, dates, rules):
    """Topstep Combine, written out step by step.  Returns (outcome, days, profit)."""
    balance = rules.start_balance
    highest_eod = rules.start_balance
    best_day = 0.0
    for n, d in enumerate(dates, 1):
        day_start = balance
        loss_limit = min(highest_eod - rules.max_loss, rules.start_balance)
        daily_floor = day_start - rules.daily_loss if rules.daily_loss else None
        for t in trades_by_day.get(d, []):
            lowest_point = balance + t.mae_usd
            if daily_floor is not None and daily_floor > loss_limit and lowest_point <= daily_floor:
                balance = daily_floor                    # flattened for the day, not failed
                break
            if lowest_point <= loss_limit:
                return "failed", n, loss_limit - rules.start_balance
            balance += t.pnl_usd
        best_day = max(best_day, balance - day_start)
        highest_eod = max(highest_eod, balance)
        profit = balance - rules.start_balance
        if profit >= max(rules.profit_target, best_day / rules.consistency):
            return "passed", n, profit
    return "unfinished", len(dates), balance - rules.start_balance


def run_ref_combine(trades_by_day, dates, rules):
    return ref_combine(trades_by_day, dates, rules)


@pytest.mark.parametrize("source,name", CASES)
def test_combine_matches_the_reference_from_every_start_day(source, name):
    if not _cached(source):
        pytest.skip("no cached data")
    cfg = CONFIGS[name]
    sessions = load_sessions(source)
    trades = bt.run(sessions, cfg)
    dates = [s.date for s in sessions[ShortStrategy(cfg.strategy).warmup_days():]]
    by_day = {}
    for t in trades:
        by_day.setdefault(t.date, []).append(t)
    for k in range(len(dates)):
        got = bt.combine_attempt(by_day, dates[k:], cfg.account)
        want = run_ref_combine(by_day, dates[k:], cfg.account)
        assert (got.outcome, got.days) == want[:2], (dates[k], got, want)
        assert got.profit == pytest.approx(want[2])


def ref_funded(trades_by_day, dates, rules):
    """Topstep Express Funded Account, step by step.  Returns (outcome, days, payouts, paid)."""
    balance, highest_eod, payouts, paid = 0.0, 0.0, 0, 0.0
    winning_days, profit_since_payout = 0, 0.0
    for n, d in enumerate(dates, 1):
        loss_limit = 0.0 if payouts else min(highest_eod - rules.max_loss, 0.0)
        day_start = balance
        daily_floor = day_start - rules.daily_loss if rules.daily_loss else None
        for t in trades_by_day.get(d, []):
            lowest_point = balance + t.mae_usd
            if daily_floor is not None and daily_floor > loss_limit and lowest_point <= daily_floor:
                balance = daily_floor
                break
            if lowest_point <= loss_limit:
                return "blown", n, payouts, paid
            balance += t.pnl_usd
        day_profit = balance - day_start
        profit_since_payout += day_profit
        if day_profit >= rules.winning_day:
            winning_days += 1
        if not payouts:
            highest_eod = max(highest_eod, balance)
        if (winning_days >= rules.winning_days and profit_since_payout >= rules.min_cycle_profit
                and (payouts == 0 or profit_since_payout > 0)):
            amount = min(balance / 2, rules.payout_cap)
            if amount >= rules.min_payout:
                balance -= amount
                paid += amount * rules.payout_split
                payouts += 1
                winning_days, profit_since_payout = 0, 0.0
    return "running", len(dates), payouts, paid


@pytest.mark.parametrize("source,name", CASES)
def test_funded_account_matches_the_reference_from_every_start_day(source, name):
    if not _cached(source):
        pytest.skip("no cached data")
    cfg = CONFIGS[name]
    sessions = load_sessions(source)
    trades = bt.run(sessions, cfg)
    dates = [s.date for s in sessions[ShortStrategy(cfg.strategy).warmup_days():]]
    by_day = {}
    for t in trades:
        by_day.setdefault(t.date, []).append(t)
    for k in range(len(dates)):
        got = bt.funded_attempt(by_day, dates[k:], cfg.account)
        want = ref_funded(by_day, dates[k:], cfg.account)
        assert (got.outcome, got.days, got.payouts) == want[:3], (dates[k], got, want)
        assert got.paid_to_trader == pytest.approx(want[3])
