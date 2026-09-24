"""Replay a scalping book from the candidate table (candidates.py) in seconds.

    from book import load, replay, report

A selection is a boolean mask over candidate minutes, a side for each (+1 buy,
-1 sell) and a priority (higher first when more names signal than slots are
free).  `replay` fills at the next minute's open (or a minute later with
delay=1), holds `hold` minutes, keeps at most `slots` positions each a
`slots`-th of the buying power, never two in one name at once, and charges
each trade its cost on the price actually paid:

* base:  a cent plus 1 bp each way (what every search here has used);
* tight: a cent and 1 bp for the round trip (one spread on a liquid name).

Dollars are a day on $25,000 at 1x buying power; 4x is the day-trading maximum.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import candidates                                                            # noqa: E402

ACCOUNT = 25_000.0
SPLIT = "2024-09-01"
COSTS = {"base": lambda px: 2 * (0.01 / px + 1e-4), "tight": lambda px: 0.01 / px + 1e-4, "none": lambda px: np.zeros_like(px)}


def load(kind: str = "bid") -> dict:
    d = candidates.load(kind)
    d["f"] = {k: d["x"][:, j] for j, k in enumerate(d["features"])}
    d["date_of"] = np.array(d["dates"])[d["day"]]
    return d


def replay(d: dict, mask: np.ndarray, side: np.ndarray, prio: np.ndarray, hold: int = 3, slots: int = 3,
           delay: int = 0, cost: str = "base", max_per_day: Optional[int] = None,
           taken: Optional[list] = None) -> Dict[str, tuple]:
    """{date: (dollars at 1x, trades, sum of net returns)} for every session in the table.

    Pass a list as `taken` to get the candidate rows actually traded."""
    hz = list(d["horizons"]).index(hold)
    idx = np.flatnonzero(mask & ~np.isnan(d["y"][:, delay, hz]))
    day, t, nm = d["day"][idx].astype(int), d["f"]["minute"][idx].astype(int), d["name"][idx].astype(int)
    order = np.lexsort((-prio[idx], t, day))
    idx, day, t, nm = idx[order], day[order], t[order], nm[order]
    gross = side[idx] * d["y"][idx, delay, hz]
    net = gross - COSTS[cost](d["f"]["px"][idx])
    size = ACCOUNT / slots
    out: Dict[str, tuple] = {dt: (0.0, 0, 0.0) for dt in d["dates"][1:]}
    j, n = 0, len(idx)
    while j < n:
        k = j
        while k < n and day[k] == day[j]:
            k += 1
        busy = []                                  # (minute the slot frees, name)
        pnl, cnt, s = 0.0, 0, 0.0
        for e in range(j, k):
            t_in = t[e] + 1 + delay
            busy = [b for b in busy if b[0] > t_in]
            if len(busy) >= slots or any(b[1] == nm[e] for b in busy):
                continue
            if max_per_day is not None and cnt >= max_per_day:
                break
            pnl += size * net[e]
            cnt += 1
            if taken is not None:
                taken.append(int(idx[e]))
            s += net[e]
            busy.append((t_in + hold, nm[e]))
        out[d["dates"][day[j]]] = (pnl, cnt, s)
        j = k
    return out


def report(byday: Dict[str, tuple], label: str = "", lev: float = 4.0) -> dict:
    ds = sorted(byday)
    v = np.array([byday[x][0] for x in ds])
    dev = np.array([byday[x][0] for x in ds if x < SPLIT])
    test = np.array([byday[x][0] for x in ds if x >= SPLIT])
    ntr = sum(byday[x][1] for x in ds)
    years = {}
    for x in ds:
        years.setdefault(x[:4], []).append(byday[x][0])
    row = {"dev_usd": round(float(dev.mean()), 1), "test_usd": round(float(test.mean()), 1),
           "test_up": round(float((test > 0).mean()), 3), "trades_per_day": round(ntr / len(ds), 1),
           "bp_per_trade": round(float(sum(byday[x][2] for x in ds) / max(ntr, 1) * 1e4), 2),
           "worst_day": round(float(v.min()), 0), "years": {y: round(float(np.mean(x)), 1) for y, x in sorted(years.items())}}
    if label:
        print(f"  {label:60s} ${row['dev_usd']:+6.1f}/${row['test_usd']:+6.1f} (x{lev:.0f} test ${lev * row['test_usd']:+5.0f}) "
              f"up {row['test_up']:.0%} {row['trades_per_day']:5.1f} tr/d {row['bp_per_trade']:+5.2f} bp | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in row["years"].items()), flush=True)
    return row
