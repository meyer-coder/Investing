"""Do big option strikes act as levels?  Six years of a proxy for the options walls.

    python strategies/mnq/strikes.py                # fade the first touch
    python strategies/mnq/strikes.py --breakout     # go with it

The call and put walls almost always sit on round QQQ strikes (730, 745,
750), where open interest piles up.  There is no free history of open
interest, but there is of prices: this maps each day's round QQQ strikes onto
Dukascopy's Nasdaq-100 minutes (at the previous close's ratio of the two)
and fades the first touch of each, the way the options-level paper trader
does: in at the next minute's open against the direction price came from, a
stop 5 bp away and a target 15 bp away (15 and 45 points at 29,000), out at
15:55 at the latest, less 1.25 points a round trip.

Each touch is scored on its own.  The control is the same trade at prices
halfway between two dollar strikes (730.50), where no option can pile up:
if round strikes are levels, their touches should win clearly more often
than the control's.  First three years and a quarter against the rest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import data                                                                  # noqa: E402

LEVEL, COST = 29_000.0, 1.25
STOP_BP, TARGET_BP = 5.0, 15.0
SPLIT = "2024-01-01"
QQQ = json.loads((ROOT / "data" / "cache" / "qqq_daily_close.json").read_text())


def groups(q: float) -> Dict[str, List[float]]:
    """QQQ prices within 1.5% of `q`, by kind."""
    lo, hi = q * 0.985, q * 1.015
    ints = np.arange(np.ceil(lo), np.floor(hi) + 1)
    return {"multiple of 10": [x for x in ints if x % 10 == 0],
            "multiple of 5 (not 10)": [x for x in ints if x % 5 == 0 and x % 10 != 0],
            "other dollar strikes": [x for x in ints if x % 5 != 0],
            "control: half-dollar, no strike": [x + 0.5 for x in ints if x + 0.5 <= hi]}


BREAKOUT = "--breakout" in sys.argv                       # go with the approach instead of fading it


def trade(day: data.Day, lvl: float) -> dict | None:
    o, h, l, c = day.o, day.h, day.l, day.c
    n = len(o)
    for i in range(5, min(n - 2, 361)):
        if not (l[i] <= lvl <= h[i]):
            continue
        prev = c[i - 1]
        if prev == lvl:
            return None
        side = -1 if prev < lvl else 1                      # came up to it: sell; came down to it: buy
        if BREAKOUT:
            side = -side
        k = i + 1
        entry = o[k]
        stop = entry * (1 - side * STOP_BP / 1e4)
        target = entry * (1 + side * TARGET_BP / 1e4)
        for m in range(k, n):
            if m >= 385 or m == n - 1:
                px, why = o[m], "15:55"
                break
            adverse, favour = (l[m], h[m]) if side > 0 else (h[m], l[m])
            if side * (adverse - stop) <= 0:
                px, why = (o[m] if side * (o[m] - stop) < 0 else stop), "stop"
                break
            if side * (favour - target) >= 0:
                px, why = (o[m] if side * (o[m] - target) > 0 else target), "target"
                break
        pts = side * (px / entry - 1.0) * LEVEL - COST
        return {"pts": pts, "why": why}
    return None


def main() -> int:
    days = data.sessions("duka")
    keys = sorted(days)
    acc: Dict[str, Dict[str, list]] = {}
    for j in range(1, len(keys)):
        d, p = keys[j], keys[j - 1]
        if p not in QQQ:
            continue
        ratio = days[p].c[-1] / QQQ[p]                        # index points per QQQ dollar at the last close
        for kind, prices in groups(QQQ[p]).items():
            for q in prices:
                t = trade(days[d], q * ratio)
                if t is None:
                    continue
                r = acc.setdefault(kind, {"dev": [], "test": [], "why": [], "years": {}})
                r["dev" if d < SPLIT else "test"].append(t["pts"])
                r["why"].append(t["why"])
                r["years"].setdefault(d[:4], []).append(t["pts"])
    out = {}
    how = "go with the first touch (breakout)" if BREAKOUT else "fade the first touch"
    print(f"{len(keys)} sessions; {how}, stop {STOP_BP:g} bp, target {TARGET_BP:g} bp, points at {LEVEL:,.0f} after {COST} a round trip")
    for kind, r in acc.items():
        a, b = np.array(r["dev"]), np.array(r["test"])
        allp = np.concatenate([a, b])
        why = np.array(r["why"])
        row = {"touches": len(allp), "per_day": round(len(allp) / (len(keys) - 1), 2),
               "target_hit": round(float((why == "target").mean()), 3), "stop_hit": round(float((why == "stop").mean()), 3),
               "dev_points": round(float(a.mean()), 2), "dev_t": round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2),
               "test_points": round(float(b.mean()), 2), "test_t": round(float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b)))), 2),
               "years": {y: round(float(np.mean(v)), 2) for y, v in sorted(r["years"].items())}}
        out[kind] = row
        print(f"  {kind:32s} {row['touches']:5d} touches ({row['per_day']:.2f}/day) target {row['target_hit']:.0%} stop {row['stop_hit']:.0%} | "
              f"2020-23 {row['dev_points']:+6.2f} pts (t{row['dev_t']:+.1f}) | 2024-26 {row['test_points']:+6.2f} pts (t{row['test_t']:+.1f}) | "
              + " ".join(f"{y[2:]}:{v:+.1f}" for y, v in row["years"].items()))
    name = "strikes_breakout.json" if BREAKOUT else "strikes.json"
    (ROOT / "strategies" / "mnq" / name).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
