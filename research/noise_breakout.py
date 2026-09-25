"""Bot A, the Nasdaq-100 noise-area breakout, re-implemented from its written
rules to check the numbers reported on the profitable-strategies branch
(profitable-strategies/futures/breakout-bot/README.md).  The rules follow
Zarattini and Aziz (2023):

* the noise band: for each minute of the session, the average over the last
  14 sessions of how far the price was from that day's open
  (|close / open - 1|); the band is max(open, yesterday's close) x (1 + that)
  above and min(open, yesterday's close) x (1 - that) below;
* every 30 minutes (the closes at 10:00, 10:30, ... 15:30), a close above the
  band buys and a close below it sells short, at the next minute's open;
* out at the next open when a check's close is back inside the band or on
  the wrong side of the session's average price (unweighted: the data has no
  exchange volume), or at a resting stop 0.30% from the entry, or at the
  16:00 close;
* 1 bp of the price per round trip in costs.

Returns are fractions of the price.  Dollars are priced at one MNQ at today's
level (NQ 30,478 -> $60,957 of index), as the branch's report does.

    python research/noise_breakout.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duka import sessions as duka_sessions  # noqa: E402

MINUTES = 390                     # 09:30 .. 15:59
MNQ_NOTIONAL = 30_478 * 2.0


@dataclass
class NoiseTrade:
    day: str
    side: int
    entry_min: int                # minute index in the session, 0 = 09:30
    exit_min: int
    ret: float                    # net of costs, fraction of the entry price
    worst: float                  # worst open return during the trade (<= 0), net of costs
    why: str


def day_arrays(sessions) -> Dict[str, np.ndarray]:
    """Full 390-minute arrays per session; a missing minute repeats the last close."""
    n = len(sessions)
    O, H, L, C = (np.full((n, MINUTES), np.nan) for _ in range(4))
    for d, s in enumerate(sessions):
        k = (s.minute - 570).astype(int)
        ok = (k >= 0) & (k < MINUTES)
        O[d, k[ok]], H[d, k[ok]], L[d, k[ok]], C[d, k[ok]] = s.open[ok], s.high[ok], s.low[ok], s.close[ok]
        for j in range(MINUTES):
            if np.isnan(C[d, j]):
                prev = C[d, j - 1] if j else s.open[0]
                O[d, j] = H[d, j] = L[d, j] = C[d, j] = prev
    pc = np.r_[np.nan, C[:-1, -1]]
    return {"dates": np.array([s.date for s in sessions]), "O": O, "H": H, "L": L, "C": C, "pc": pc}


def run(D: Dict[str, np.ndarray], lookback: int = 14, every: int = 30, stop: float = 0.003,
        cost: float = 1e-4) -> List[NoiseTrade]:
    O, H, L, C, pc, dates = D["O"], D["H"], D["L"], D["C"], D["pc"], D["dates"]
    dist = np.abs(C / O[:, :1] - 1.0)                       # distance from the day's open, each minute
    checks = list(range(every - 1, MINUTES - 1, every))     # bar indices closing at 10:00 .. 15:30
    trades: List[NoiseTrade] = []
    for d in range(lookback, len(dates)):
        if np.isnan(pc[d]):
            continue
        sigma = dist[d - lookback:d].mean(axis=0)
        o, h, lo, c = O[d], H[d], L[d], C[d]
        upper = max(o[0], pc[d]) * (1 + sigma)
        lower = min(o[0], pc[d]) * (1 - sigma)
        vwap = np.cumsum((h + lo + c) / 3.0) / np.arange(1, MINUTES + 1)
        side, entry, t_in, worst = 0, 0.0, 0, 0.0

        def close_trade(k: int, px: float, why: str) -> None:
            r = side * (px / entry - 1.0) - cost
            trades.append(NoiseTrade(str(dates[d]), side, t_in, k, r, min(worst - cost, r), why))

        def watch_stop(a: int, b: int) -> bool:
            """Walk minutes a..b for the resting stop; True if it filled."""
            nonlocal side, worst
            level = entry * (1 - side * stop)
            for k in range(a, b + 1):
                adverse = lo[k] if side > 0 else h[k]
                if (side > 0 and adverse <= level) or (side < 0 and adverse >= level):
                    px = level if k == t_in else (min(o[k], level) if side > 0 else max(o[k], level))
                    worst = min(worst, side * (px / entry - 1.0))
                    close_trade(k, px, "stop")
                    side = 0
                    return True
                worst = min(worst, side * (adverse / entry - 1.0))
            return False

        last = -1
        for t in checks:
            if side and watch_stop(max(t_in, last + 1), t):
                last = t
                continue
            last = t
            if side:
                out = c[t] < max(upper[t], vwap[t]) if side > 0 else c[t] > min(lower[t], vwap[t])
                if out:
                    close_trade(t + 1, o[t + 1], "band or average")
                    side = 0
                    continue                                   # a new entry waits for the next check
            if side == 0:
                s = 1 if c[t] > upper[t] else (-1 if c[t] < lower[t] else 0)
                if s:
                    side, entry, t_in, worst = s, o[t + 1], t + 1, 0.0
        if side and not watch_stop(max(t_in, last + 1), MINUTES - 1):
            close_trade(MINUTES - 1, c[MINUTES - 1], "close")
    return trades


def daily(trades: List[NoiseTrade], dates) -> np.ndarray:
    idx = {str(d): i for i, d in enumerate(dates)}
    r = np.zeros(len(dates))
    for t in trades:
        r[idx[t.day]] += t.ret
    return r


def report(trades: List[NoiseTrade], dates, first: int) -> None:
    days = np.array([str(d) for d in dates[first:]])
    r = daily(trades, dates)[first:]
    usd = r * MNQ_NOTIONAL
    sd = usd.std(ddof=1)
    print(f"{len(trades):,} trades over {len(days):,} sessions ({days[0]} .. {days[-1]}), "
          f"{len(trades) / len(days):.2f} a day")
    print(f"$ a day at 1 MNQ: {usd.mean():+.1f}   Sharpe {usd.mean() / sd * np.sqrt(252):.2f}   "
          f"t = {usd.mean() / sd * np.sqrt(len(usd)):.1f}   worst day ${usd.min():+,.0f}")
    eq = np.cumsum(usd)
    dd = eq - np.maximum.accumulate(np.maximum(eq, 0))
    print(f"worst losing stretch ${dd.min():+,.0f}")
    for label, lo_, hi_ in (("2013-2019", "2013", "2019-99"), ("2020-2026", "2020", "2099"),
                            ("last 3 years", "2023-09-25", "2099")):
        m = (days >= lo_) & (days <= hi_)
        print(f"   {label:<13} ${usd[m].mean():+6.1f} a day")
    years = sorted({d[:4] for d in days})
    print("   by year: " + "  ".join(f"{y} {usd[np.char.startswith(days, y)].mean():+.0f}" for y in years))


def main() -> None:
    dropped: list = []
    ss = duka_sessions(1, dropped=dropped)
    D = day_arrays(ss)
    trades = run(D)
    print(f"sessions: {len(ss)} (dropped {len(dropped)} broken or partial days)")
    report(trades, D["dates"], 14)


if __name__ == "__main__":
    main()
