"""The MNQ strategy.

Three short-only setups, checked at the close of every bar, in this order:

``momentum``     The last hour fell ``mom_k`` times its normal range for that
                 time of day, and price is under VWAP.  Research showed big
                 hourly drops in NQ tended to keep falling.
``orb``          The first close below the opening range (09:30 + or_minutes)
                 while under VWAP, before ``orb_last_minute``.  Most of the
                 day's sharpest selloff candles come in the first hour.
``vwap_reject``  On a day trading below its open, a bar rallies up to VWAP,
                 fails, and closes red below it.

and one ``basic`` setup that trades both ways: after a run of green (or red)
candles that is big for that time of day, go with it (``follow``: buy
green, short red) or against it (``fade``: short green, buy red).

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
    stop_pts: float        # distance from the entry to the stop (against the trade)
    target_pts: float      # distance from the entry to the target (with the trade)
    reason: str
    side: int = -1         # +1 buy (long), -1 sell short


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
        return [self.p.unit_minutes, self.p.mom_minutes, self.p.basic_minutes]

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

    def deadline(self, date: str, entry_minute: int) -> int:
        """Minute by which a position opened at ``entry_minute`` must be closed:
        before a Fed statement if it was opened ahead of it, otherwise the
        end-of-day flatten time."""
        if self.is_fomc(date) and entry_minute < self.p.fomc_flat_minute:
            return self.p.fomc_flat_minute
        return self.p.flatten_minute

    def entry_unit(self, s: Session, i: int, day: DayState, prof: Profile) -> float:
        """The size of one unit if a new trade may be opened after bar ``i``
        (time window, day limits, cooldown, Fed days), else 0."""
        p = self.p
        now = int(s.minute[i]) + s.bar_minutes           # the moment bar i closed
        if day.in_position or day.done:
            return 0.0
        if day.trades >= p.max_trades_per_day or day.losses >= p.max_losses_per_day:
            return 0.0
        if now - day.last_exit_minute < p.cooldown_minutes:
            return 0.0
        if not (p.first_entry_minute <= now <= p.last_entry_minute):
            return 0.0
        if now >= p.flatten_minute:
            return 0.0
        if self.is_fomc(s.date) and p.fomc_flat_minute - 30 <= now < p.fomc_resume_minute:
            return 0.0
        if int(s.minute[i]) < RTH_OPEN:
            return 0.0                      # a bar that began before the 09:30 open (hourly data)
        unit = prof.normal(p.unit_minutes, int(s.minute[i]))
        return unit if unit > 0 else 0.0

    def decide(self, s: Session, i: int, day: DayState, prof: Profile) -> Optional[Entry]:
        """Called after bar ``i`` closes.  Returns an entry for the next bar, or None."""
        p = self.p
        now = int(s.minute[i]) + s.bar_minutes
        unit = self.entry_unit(s, i, day, prof)
        if not unit:
            return None
        close = float(s.close[i])
        vwap = session_vwap(s, i)
        below_vwap = close < vwap
        shorts_ok = below_vwap or not p.require_below_vwap

        def entry(name: str, why: str, side: int = -1) -> Entry:
            return Entry(name, p.stop_units * unit, p.target_units * unit, why, side)

        # 1) big drop keeps going
        if p.momentum and shorts_ok:
            n = prof.bars_for(p.mom_minutes)
            if i >= n - 1:
                move = close - float(s.open[i - n + 1])
                normal = prof.normal(p.mom_minutes, int(s.minute[i]))
                if normal > 0 and move <= -p.mom_k * normal:
                    return entry("momentum", f"fell {-move:.0f} pts in {p.mom_minutes}m "
                                             f"(normal {normal:.0f}, k={-move / normal:.1f})")

        # 2) break below the opening range
        or_end = RTH_OPEN + p.or_minutes
        if (p.orb and shorts_ok and s.bar_minutes <= p.or_minutes and not day.setups_used.get("orb")
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

        # 4) basic, both ways: a big run of same-coloured candles
        if p.basic:
            n = prof.bars_for(p.basic_minutes)
            if i >= n - 1:
                o_run, c_run = s.open[i - n + 1:i + 1], s.close[i - n + 1:i + 1]
                move = close - float(o_run[0])
                normal = prof.normal(p.basic_minutes, int(s.minute[i]))
                colour = 1 if bool((c_run > o_run).all()) else -1 if bool((c_run < o_run).all()) else 0
                if colour and normal > 0 and colour * move >= p.basic_k * normal:
                    side = colour if p.basic_mode == "follow" else -colour
                    word = "green" if colour > 0 else "red"
                    return entry("basic", f"{n} {word} candle(s), {move:+.0f} pts in "
                                          f"{p.basic_minutes}m (normal {normal:.0f})", side)
        return None


class RandomStrategy(ShortStrategy):
    """The benchmark: enters at random moments in a random direction, with
    the same stops, targets, sizing, time windows and day limits as the real
    setups.  A strategy that cannot beat this has no edge -- whatever its
    backtest says."""

    def __init__(self, params: StrategyParams, rate: float, seed: int, long_share: float = 0.5):
        super().__init__(params)
        self.rate = rate
        self.long_share = long_share        # match the strategy: 0 for a short-only one
        self.rng = np.random.default_rng(seed)

    def decide(self, s: Session, i: int, day: DayState, prof: Profile) -> Optional[Entry]:
        unit = self.entry_unit(s, i, day, prof)
        if not unit or self.rng.random() > self.rate:
            return None
        side = 1 if self.rng.random() < self.long_share else -1
        return Entry("random", self.p.stop_units * unit, self.p.target_units * unit,
                     "coin flip", side)
