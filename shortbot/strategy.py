"""The short-only MNQ strategy.

Three setups, checked at the close of every bar, in this order:

``momentum``     The last hour fell ``mom_k`` times its normal range for that
                 time of day, and price is under VWAP.  Research showed big
                 hourly drops in NQ tended to keep falling.
``orb``          The first close below the opening range (09:30 + or_minutes)
                 while under VWAP, before ``orb_last_minute``.  Most of the
                 day's sharpest selloff candles come in the first hour.
``vwap_reject``  On a day trading below its open, a bar rallies up to VWAP,
                 fails, and closes red below it.

``decide`` sees only bars that have already closed; the entry fills at the
next bar's open.  The backtester and the live bot both call it, so what is
tested is exactly what trades.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from .config import FOMC_DATES, StrategyParams
from .data import RTH_OPEN, Session


class Profile:
    """Normal price range of an n-minute window ending at each time of day,
    averaged over earlier sessions only."""

    def __init__(self, prior: Sequence[Session], windows_minutes: Iterable[int]):
        self.table: Dict[int, Dict[int, float]] = {}
        self.bar_minutes = prior[-1].bar_minutes if prior else 5
        for w in set(windows_minutes):
            n = self.bars_for(w)
            acc: Dict[int, List[float]] = defaultdict(list)
            for s in prior:
                for j in range(n - 1, len(s)):
                    acc[int(s.minute[j])].append(float(s.high[j - n + 1:j + 1].max()
                                                       - s.low[j - n + 1:j + 1].min()))
            self.table[w] = {m: float(np.mean(v)) for m, v in acc.items()}

    def bars_for(self, minutes: int) -> int:
        return max(1, int(math.floor(minutes / self.bar_minutes + 0.5)))

    def normal(self, window_minutes: int, slot: int) -> float:
        """Normal range for the window ending at the bar starting at ``slot``;
        falls back to the nearest slot within two bars, else NaN."""
        t = self.table.get(window_minutes, {})
        if slot in t:
            return t[slot]
        for k in (1, 2):
            for s in (slot - k * self.bar_minutes, slot + k * self.bar_minutes):
                if s in t:
                    return t[s]
        return float("nan")


@dataclass
class DayState:
    """What has happened so far today; the strategy reads it, the caller updates it."""

    trades: int = 0
    losses: int = 0
    pnl_usd: float = 0.0
    in_position: bool = False
    last_exit_minute: int = -10_000
    done: bool = False                  # daily stop hit
    setups_used: Dict[str, int] = field(default_factory=dict)

    def record_exit(self, pnl_usd: float, minute: int) -> None:
        self.trades += 1
        self.losses += 1 if pnl_usd < 0 else 0
        self.pnl_usd += pnl_usd
        self.in_position = False
        self.last_exit_minute = minute


@dataclass
class Entry:
    setup: str
    stop_pts: float        # distance above the entry
    target_pts: float      # distance below the entry
    reason: str


def session_vwap(s: Session, i: int) -> float:
    typical = (s.high[:i + 1] + s.low[:i + 1] + s.close[:i + 1]) / 3.0
    vol = s.volume[:i + 1]
    if float(vol.sum()) <= 0:
        return float(typical.mean())
    return float((typical * vol).sum() / vol.sum())


class ShortStrategy:
    def __init__(self, params: StrategyParams):
        self.p = params
        self._fomc = set(FOMC_DATES)

    def windows(self) -> List[int]:
        return [self.p.unit_minutes, self.p.mom_minutes]

    def profile(self, prior: Sequence[Session]) -> Profile:
        return Profile(prior, self.windows())

    def warmup_days(self) -> int:
        """Earlier sessions needed before the bot can trade a day."""
        return max(self.p.profile_days, self.p.trend_days + 1 if self.p.trend_filter else 0)

    def day_allowed(self, prior: Sequence[Session]) -> bool:
        """Whether today may be traded at all, judged before the open."""
        if not self.p.trend_filter:
            return True
        n = self.p.trend_days
        if len(prior) < n + 1:
            return False
        closes = [float(s.close[-1]) for s in prior[-(n + 1):]]
        return closes[-1] < float(np.mean(closes[:-1]))

    def is_fomc(self, date: str) -> bool:
        return self.p.skip_fomc and date in self._fomc

    def flatten_minute(self, date: str) -> int:
        """Minute by which any position must be closed today."""
        return self.p.fomc_flat_minute if self.is_fomc(date) else self.p.flatten_minute

    def decide(self, s: Session, i: int, day: DayState, prof: Profile) -> Optional[Entry]:
        """Called after bar ``i`` closes.  Returns a short entry for the next bar, or None."""
        p = self.p
        now = int(s.minute[i]) + s.bar_minutes           # the moment bar i closed
        if day.in_position or day.done:
            return None
        if day.trades >= p.max_trades_per_day or day.losses >= p.max_losses_per_day:
            return None
        if now - day.last_exit_minute < p.cooldown_minutes:
            return None
        if not (p.first_entry_minute <= now <= p.last_entry_minute):
            return None
        if now >= self.flatten_minute(s.date):
            return None
        if self.is_fomc(s.date) and p.fomc_flat_minute - 30 <= now < p.fomc_resume_minute:
            return None

        unit = prof.normal(p.unit_minutes, int(s.minute[i]))
        if not unit > 0:
            return None
        close = float(s.close[i])
        vwap = session_vwap(s, i)
        below_vwap = close < vwap
        if p.require_below_vwap and not below_vwap:
            return None

        def entry(name: str, why: str) -> Entry:
            return Entry(name, p.stop_units * unit, p.target_units * unit, why)

        # 1) big drop keeps going
        if p.momentum:
            n = prof.bars_for(p.mom_minutes)
            if i >= n - 1:
                move = close - float(s.open[i - n + 1])
                normal = prof.normal(p.mom_minutes, int(s.minute[i]))
                if normal > 0 and move <= -p.mom_k * normal:
                    return entry("momentum", f"fell {-move:.0f} pts in {p.mom_minutes}m "
                                             f"(normal {normal:.0f}, k={-move / normal:.1f})")

        # 2) break below the opening range
        or_end = RTH_OPEN + p.or_minutes
        if (p.orb and s.bar_minutes <= p.or_minutes and not day.setups_used.get("orb")
                and or_end <= now <= p.orb_last_minute and int(s.minute[0]) <= RTH_OPEN):
            in_or = s.minute[:i + 1] < or_end
            if in_or.any() and i > 0 and not in_or[i]:
                or_low = float(s.low[:i + 1][in_or].min())
                if close < or_low <= float(s.close[i - 1]):
                    return entry("orb", f"closed {or_low - close:.0f} pts under the "
                                        f"{p.or_minutes}m opening range low {or_low:.2f}")

        # 3) rally to VWAP fails on a down day
        if p.vwap_reject and now >= p.vr_first_minute and i > 0:
            down_day = close < float(s.open[0])
            prev_below = float(s.close[i - 1]) < session_vwap(s, i - 1)
            touched = float(s.high[i]) >= vwap - p.vr_tolerance * unit
            red = close < float(s.open[i])
            if down_day and prev_below and touched and red and below_vwap:
                return entry("vwap_reject", f"high {s.high[i]:.2f} tagged VWAP {vwap:.2f} "
                                            f"and closed red below it")
        return None
