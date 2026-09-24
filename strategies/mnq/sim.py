"""A one-instrument MNQ day-trading simulator.

Decisions on a minute's close, fills at the next minute's open.  One position
at a time (long or short), a fixed number of contracts, out after a set number
of minutes or at a resting stop or target, whichever comes first; a bar that
reaches both counts the stop.  No entry after 15:45 and nothing held past
15:55 New York.  An optional daily loss limit stops the day's trading once
closed trades have lost that much.

Every trade's result is measured in index points at today's level: its return
times TODAY_LEVEL.  Years when the index was at 5,000 and years at 29,000 then
count alike, and the dollars are what the same trade is worth on an MNQ
contract now ($2 a point).  Costs are points a round trip per contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

TODAY_LEVEL = 29_000.0
POINT_USD = 2.0                      # one MNQ contract
COST_POINTS = 1.25                   # a round trip: commission plus a tick of slippage each way


@dataclass
class Rules:
    """signal(features) -> array of +1 (buy), -1 (sell short) or 0 per minute,
    or a pair (sides, holds) when each setup keeps its own holding time."""
    signal: Callable[[Dict[str, np.ndarray]], np.ndarray]
    hold: int = 10                   # minutes, at most
    stop_bp: float = 0.0             # resting stop, basis points from entry (0: none)
    target_bp: float = 0.0           # resting target
    last_entry: int = 375            # minutes since the open (15:45)
    flat_at: int = 385               # 15:55


@dataclass
class Trade:
    day: str
    side: int
    entry_i: int
    exit_i: int
    entry: float
    exit: float
    why: str

    @property
    def ret_bp(self) -> float:
        return self.side * (self.exit / self.entry - 1.0) * 1e4

    @property
    def minutes(self) -> int:
        return self.exit_i - self.entry_i


@dataclass
class Result:
    trades: List[Trade] = field(default_factory=list)
    days: List[str] = field(default_factory=list)

    def points(self, cost: float = COST_POINTS) -> np.ndarray:
        return np.array([t.ret_bp * TODAY_LEVEL / 1e4 - cost for t in self.trades])

    def daily_usd(self, contracts: int = 1, cost: float = COST_POINTS, day_loss: float = 0.0,
                  day_target: float = 0.0) -> Dict[str, float]:
        """Dollars a day on `contracts` MNQ.  With `day_loss`, no new trade once
        the day's closed trades have lost that much (the cap a funded account
        enforces); with `day_target`, none once they have made that much."""
        out = {d: 0.0 for d in self.days}
        for t, p in zip(self.trades, self.points(cost)):
            if day_loss and out[t.day] <= -day_loss:
                continue
            if day_target and out[t.day] >= day_target:
                continue
            out[t.day] += p * POINT_USD * contracts
        return out


def run(days: Dict[str, "object"], rules: Rules, features: Callable) -> Result:
    res = Result(days=sorted(days))
    keys = res.days
    for j, d in enumerate(keys):
        day = days[d]
        prev = days[keys[j - 1]] if j else None
        if prev is not None and (np.datetime64(d) - np.datetime64(prev.date)).astype(int) > 4:
            prev = None                                  # the gap between two islands
        f = features(day, prev)
        out = rules.signal(f)
        sig, holds = out if isinstance(out, tuple) else (out, None)
        sig = np.nan_to_num(sig).astype(int)
        o, h, l = day.o, day.h, day.l
        mso = f["mso"]
        n = len(o)
        i = 0
        while i < n - 1:
            if sig[i] == 0 or mso[i] > rules.last_entry:
                i += 1
                continue
            side, k = int(sig[i]), i + 1
            hold = int(holds[i]) if holds is not None else rules.hold
            entry = o[k]
            stop = entry * (1 - side * rules.stop_bp / 1e4) if rules.stop_bp else None
            target = entry * (1 + side * rules.target_bp / 1e4) if rules.target_bp else None
            exit_px, exit_i, why = None, None, ""
            for m in range(k, n):
                if m - k >= hold or mso[m] >= rules.flat_at or m == n - 1:
                    exit_px, exit_i, why = o[m], m, "time" if m - k >= hold else "close"
                    break
                lo, hi = (l[m], h[m]) if side > 0 else (h[m], l[m])
                if stop is not None and (side * (lo - stop) <= 0):
                    gapped = side * (o[m] - stop) < 0
                    exit_px, exit_i, why = (o[m] if gapped else stop), m + 1, "stop"
                    break
                if target is not None and (side * (hi - target) >= 0):
                    gapped = side * (o[m] - target) > 0
                    exit_px, exit_i, why = (o[m] if gapped else target), m + 1, "target"
                    break
            res.trades.append(Trade(d, side, k, exit_i, entry, exit_px, why))
            i = max(exit_i, k)                       # flat again: look for the next signal from here
    return res


def summary(res: Result, contracts: int = 1, cost: float = COST_POINTS, day_loss: float = 0.0,
            day_target: float = 0.0) -> dict:
    pts = res.points(cost)
    by_day = res.daily_usd(contracts, cost, day_loss, day_target)
    daily = np.array(list(by_day.values()))
    years: Dict[str, List[float]] = {}
    for d, v in by_day.items():
        years.setdefault(d[:4], []).append(v)
    return {"sessions": len(daily), "trades": len(pts), "trades_per_day": round(len(pts) / max(len(daily), 1), 2),
            "avg_points": round(float(pts.mean()), 2) if len(pts) else 0.0,
            "win": round(float((pts > 0).mean()), 3) if len(pts) else 0.0,
            "avg_minutes": round(float(np.mean([t.minutes for t in res.trades])), 1) if res.trades else 0.0,
            "usd_per_day": round(float(daily.mean()), 1), "median_day": round(float(np.median(daily)), 1),
            "days_up": round(float((daily > 0).mean()), 3), "days_flat": round(float((daily == 0).mean()), 3),
            "worst_day": round(float(daily.min()), 0), "best_day": round(float(daily.max()), 0),
            "years": {y: round(float(np.mean(v)), 1) for y, v in sorted(years.items())}}
