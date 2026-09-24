"""A day-trading bot's trades replayed as Topstep 100K accounts.

Topstep's rules for the 100K Trading Combine and Express Funded Account, from
help.topstep.com (September 2026):

* Maximum Loss Limit $3,000.  It trails the highest end-of-day balance,
  never moves down, locks once it reaches the starting balance, and is
  watched in real time: an open loss that touches it ends the account.
* Daily Loss Limit $2,000, optional: hitting it only ends that day.
* At most 10 NQ or 100 MNQ contracts.
* Combine: pass at the profit target (taken here as $6,000, the usual 100K
  target; check the plan bought) with the best day under half the profit.
* Express Funded, standard path: a payout needs five winning days of $150
  or more.

`replay` starts a fresh account on every fifth session of a window and runs
the bot's own days through these rules, with each trade's worst moment while
open counted against the limit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np

import sim


@dataclass(frozen=True)
class Plan:
    name: str = "Topstep 100K"
    max_loss: float = 3_000.0
    daily_loss: float = 2_000.0
    target: float = 6_000.0
    consistency: float = 0.5
    win_day: float = 150.0          # a winning day for the payout rule
    win_days: int = 5               # needed for a payout
    max_micros: int = 100


TOPSTEP_100K = Plan()


def days_of(res: sim.Result, contracts: int, cost: float = sim.COST_POINTS,
            daily_loss: float = TOPSTEP_100K.daily_loss) -> Dict[str, tuple]:
    """Per session: (closed P&L, the lowest the day's P&L went counting open
    losses), in dollars on `contracts` MNQ, with the daily loss limit ending
    the day once the closed P&L reaches it."""
    out = {d: [0.0, 0.0] for d in res.days}
    usd = sim.POINT_USD * contracts * sim.TODAY_LEVEL / 1e4
    for t, pts in zip(res.trades, res.points(cost)):
        day = out[t.day]
        if daily_loss and day[0] <= -daily_loss:
            continue
        low = day[0] + t.worst_bp * usd - cost * sim.POINT_USD * contracts / 2
        day[1] = min(day[1], low)
        day[0] += pts * sim.POINT_USD * contracts
        day[1] = min(day[1], day[0])
    return {d: (v[0], v[1]) for d, v in out.items()}


def _run_combine(seq: Sequence[tuple], plan: Plan) -> tuple:
    """(outcome, sessions used): 'pass', 'breach' or 'open'."""
    bal, peak = 0.0, 0.0
    floor = -plan.max_loss
    best = 0.0
    for n, (pnl, low) in enumerate(seq, 1):
        if bal + low <= floor:
            return "breach", n
        bal += pnl
        best = max(best, pnl)
        peak = max(peak, bal)
        floor = min(0.0, max(floor, peak - plan.max_loss))
        if bal >= plan.target and best <= plan.consistency * bal:
            return "pass", n
    return "open", len(seq)


def _run_funded(seq: Sequence[tuple], plan: Plan) -> tuple:
    """(first payout reached?, sessions to it or to the breach, breached?)."""
    bal, peak = 0.0, 0.0
    floor = -plan.max_loss
    wins = 0
    for n, (pnl, low) in enumerate(seq, 1):
        if bal + low <= floor:
            return False, n, True
        bal += pnl
        wins += pnl >= plan.win_day
        peak = max(peak, bal)
        floor = min(0.0, max(floor, peak - plan.max_loss))
        if wins >= plan.win_days and bal > 0:
            return True, n, False
    return False, len(seq), False


def replay(res: sim.Result, contracts: int, plan: Plan = TOPSTEP_100K, start: str = "", end: str = "9999",
           horizon: int = 126) -> dict:
    """Fresh Combines and funded accounts started every fifth session between
    `start` and `end`, each followed for up to `horizon` sessions."""
    by = days_of(res, contracts, daily_loss=plan.daily_loss)
    keys = [d for d in sorted(by) if start <= d <= end]
    seq = [by[d] for d in keys]
    starts = range(0, max(len(seq) - 20, 1), 5)
    comb = [_run_combine(seq[i:i + horizon], plan) for i in starts]
    fund = [_run_funded(seq[i:i + horizon], plan) for i in starts]
    pnl = np.array([p for p, _ in seq])
    return {"contracts": contracts, "sessions": len(seq),
            "usd_per_day": round(float(pnl.mean()), 1), "median_day": round(float(np.median(pnl)), 1),
            "days_150_plus": round(float((pnl >= plan.win_day).mean()), 3),
            "days_down": round(float((pnl < 0).mean()), 3), "worst_day": round(float(pnl.min()), 0),
            "combine_pass": round(float(np.mean([o == "pass" for o, _ in comb])), 3),
            "combine_breach": round(float(np.mean([o == "breach" for o, _ in comb])), 3),
            "days_to_pass": float(np.median([n for o, n in comb if o == "pass"])) if any(o == "pass" for o, _ in comb) else None,
            "funded_payout_first": round(float(np.mean([p for p, _, _ in fund])), 3),
            "funded_breach_first": round(float(np.mean([b for _, _, b in fund])), 3),
            "days_to_payout": float(np.median([n for p, n, _ in fund if p])) if any(p for p, _, _ in fund) else None}
