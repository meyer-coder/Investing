"""Prop-firm rules: replay a strategy as a funded-account challenge.

A backtest's percentage return says nothing about whether a $25,000 prop
account survives the strategy. This module takes a strategy's trades, prices
them at today's contract size (one micro contract, whatever the index level
was when the trade happened), and replays them as a fresh account from many
start dates under the firm's rules:

* the maximum loss limit trails the highest end-of-day balance and locks once
  it reaches the starting balance; a floating loss that touches it during the
  day breaches the account at once (the day's low is used for that);
* the challenge is passed when profit reaches the target and the largest
  single day is no more than the consistency share of total profit (otherwise
  the target rises to largest day / share);
* costs are per contract: commission each side, a tick of slippage on
  market fills and two on stop fills.

Rules for FundedNext Futures Legacy, from fundednext.com (September 2026):
25K: $1,250 target, $1,000 maximum loss limit; 50K: $3,000 and $2,000; 100K:
$6,000 and $3,000.  The limit trails the highest end-of-day balance and locks
at the initial balance; 40% consistency in the challenge only; no daily loss
limit; no position may be held past 15:10 Chicago time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from .data import Bars


@dataclass(frozen=True)
class Rules:
    label: str
    account: float
    target: float
    max_loss: float
    consistency: float          # best day <= this share of profit; 0 = no rule


LEGACY_25K = Rules("FundedNext Futures Legacy 25K", 25_000.0, 1_250.0, 1_000.0, 0.40)
LEGACY_25K_FUNDED = Rules("FundedNext Futures Legacy 25K, funded", 25_000.0, 0.0, 1_000.0, 0.0)
LEGACY_50K = Rules("FundedNext Futures Legacy 50K", 50_000.0, 3_000.0, 2_000.0, 0.40)
LEGACY_50K_FUNDED = Rules("FundedNext Futures Legacy 50K, funded", 50_000.0, 0.0, 2_000.0, 0.0)
LEGACY_100K = Rules("FundedNext Futures Legacy 100K", 100_000.0, 6_000.0, 3_000.0, 0.40)
LEGACY_100K_FUNDED = Rules("FundedNext Futures Legacy 100K, funded", 100_000.0, 0.0, 3_000.0, 0.0)
#: one-time challenge fees, fundednext.com/futures/legacy, September 2026
LEGACY_FEES = {"25K": 79.99, "50K": 199.99, "100K": 239.99}


@dataclass(frozen=True)
class Micro:
    name: str
    data_symbol: str
    point_value: float          # dollars per index point
    tick: float                 # index points per tick
    commission: float = 0.75    # dollars per contract per side, all-in


MICROS: Dict[str, Micro] = {
    "MNQ": Micro("MNQ", "NQ1!", 2.0, 0.25),
    "MES": Micro("MES", "ES1!", 5.0, 0.25),
    "MYM": Micro("MYM", "YM1!", 0.5, 1.0),
    "M2K": Micro("M2K", "RTY1!", 5.0, 0.1),
}


@dataclass
class TradePath:
    entry_bar: int
    exit_bar: int
    days: List[int]             # bars the position is held through, entry bar first
    eod: List[float]            # trade P&L at each of those bars' close, costs in
    worst: List[float]          # trade P&L at each of those bars' low, costs in
    realized: float             # final P&L, costs in
    stopped: bool = False


def trade_paths(trades: Sequence, bars: Bars, *, micro: Micro, contracts: int,
                price_now: float, slippage_bps: float = 0.0) -> List[TradePath]:
    """Each trade's day-by-day P&L at today's contract size.

    Returns are measured on the backtest's own (back-adjusted) prices and
    applied to today's notional, so a 2012 trade carries the risk the same
    trade would carry today.  The backtest's own slippage is taken back out of
    its fills (``slippage_bps``, as the broker applied it): here costs are
    charged per contract instead.
    """
    slip = slippage_bps / 10_000.0
    index = {d: i for i, d in enumerate(bars.dates)}
    notional = contracts * micro.point_value * price_now
    tick_usd = contracts * micro.point_value * micro.tick
    comm = contracts * micro.commission
    out: List[TradePath] = []
    for t in trades:
        j, k = index.get(t.entry_date), index.get(t.exit_date)
        if j is None or k is None:
            continue
        entry = float(t.entry_price) / (1.0 + slip)
        exit_px = float(t.exit_price) / (1.0 - slip)
        stopped = "stop order" in t.exit_reason
        entry_cost = comm + tick_usd
        exit_cost = comm + tick_usd * (2 if stopped else 1)
        days, eod, worst = [], [], []
        for b in range(j, k):
            days.append(b)
            eod.append(notional * (float(bars.close[b]) / entry - 1.0) - entry_cost)
            worst.append(notional * (float(bars.low[b]) / entry - 1.0) - entry_cost)
        realized = notional * (exit_px / entry - 1.0) - entry_cost - exit_cost
        if k == j:
            # A same-day trade: flat by the close, so its day ends at the exit.
            # The day's low is its worst point unless a stop took it out above
            # the low (a target may have filled before or after the low: the
            # low is kept either way).
            low = exit_px if stopped else float(bars.low[j])
            days = [j]
            eod = [realized]
            worst = [min(realized, notional * (low / entry - 1.0) - entry_cost)]
        out.append(TradePath(j, k, days, eod, worst, realized, stopped))
    return out


@dataclass
class Outcome:
    result: str                 # "pass", "breach" or "open"
    days: int                   # trading days from the start to the result
    pnl: float                  # account P&L at the result (or at the horizon)
    best_day: float
    sessions_in_market: int


def replay(paths: Sequence[TradePath], start_bar: int, rules: Rules, *,
           horizon: int, first_path: Optional[int] = None) -> Outcome:
    """A fresh account from ``start_bar``: it takes every trade entered on or after it."""
    realized = 0.0
    peak_eod = 0.0
    floor = -rules.max_loss
    prev_eod = 0.0
    best_day = 0.0
    in_market = 0
    end_bar = start_bar + horizon
    i0 = first_path if first_path is not None else next(
        (i for i, p in enumerate(paths) if p.entry_bar >= start_bar), len(paths))

    def end_of_day(eod_pnl: float, bar: int) -> Optional[Outcome]:
        nonlocal prev_eod, best_day, peak_eod, floor
        day = eod_pnl - prev_eod
        prev_eod = eod_pnl
        best_day = max(best_day, day)
        if rules.target > 0:
            need = rules.target
            if rules.consistency > 0:
                need = max(need, best_day / rules.consistency)
            if eod_pnl >= need:
                return Outcome("pass", bar - start_bar + 1, eod_pnl, best_day, in_market)
        peak_eod = max(peak_eod, eod_pnl)
        floor = min(0.0, max(floor, peak_eod - rules.max_loss))   # trails, locks at the start
        return None

    for p in paths[i0:]:
        if p.entry_bar >= end_bar:
            break
        for b, e, w in zip(p.days, p.eod, p.worst):
            if b >= end_bar:
                return Outcome("open", horizon, realized + e, best_day, in_market)
            in_market += 1
            if realized + w <= floor:
                return Outcome("breach", b - start_bar + 1, floor, best_day, in_market)
            hit = end_of_day(realized + e, b)
            if hit:
                return hit
        if p.exit_bar >= end_bar:
            return Outcome("open", horizon, realized + (p.eod[-1] if p.eod else 0.0), best_day, in_market)
        realized += p.realized
        if realized <= floor:                                   # the exit itself breached
            return Outcome("breach", p.exit_bar - start_bar + 1, floor, best_day, in_market)
        hit = end_of_day(realized, p.exit_bar)
        if hit:
            return hit
    return Outcome("open", horizon, realized, best_day, in_market)


@dataclass
class Stats:
    starts: int
    passed: int
    breached: int
    still_open: int
    median_days_to_pass: float
    median_days_to_breach: float
    mean_pnl_per_day_funded: float = 0.0
    breach_63: float = 0.0
    breach_126: float = 0.0
    breach_252: float = 0.0
    extra: Dict[str, float] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.starts if self.starts else 0.0

    @property
    def breach_rate(self) -> float:
        return self.breached / self.starts if self.starts else 0.0


def challenge_stats(paths: Sequence[TradePath], starts: Sequence[int], rules: Rules = LEGACY_25K,
                    horizon: int = 252) -> Stats:
    outs = [replay(paths, s, rules, horizon=horizon) for s in starts]
    passed = [o for o in outs if o.result == "pass"]
    breached = [o for o in outs if o.result == "breach"]
    return Stats(len(outs), len(passed), len(breached), len(outs) - len(passed) - len(breached),
                 float(np.median([o.days for o in passed])) if passed else float("nan"),
                 float(np.median([o.days for o in breached])) if breached else float("nan"))


def funded_stats(paths: Sequence[TradePath], starts: Sequence[int],
                 rules: Rules = LEGACY_25K_FUNDED) -> Stats:
    """Funded accounts from each start: how often the floor is hit within
    three, six and twelve months, and the average profit per session."""
    outs = [replay(paths, s, rules, horizon=252) for s in starts]
    br = [o for o in outs if o.result == "breach"]
    days = np.array([o.days for o in br]) if br else np.array([])
    st = Stats(len(outs), 0, len(br), len(outs) - len(br), float("nan"),
               float(np.median(days)) if br else float("nan"))
    st.breach_63 = float(np.sum(days <= 63) / len(outs)) if outs else 0.0
    st.breach_126 = float(np.sum(days <= 126) / len(outs)) if outs else 0.0
    st.breach_252 = float(len(br) / len(outs)) if outs else 0.0
    st.mean_pnl_per_day_funded = float(np.mean([o.pnl / max(o.days, 1) for o in outs])) if outs else 0.0
    return st
