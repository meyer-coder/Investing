"""Quiet day, afternoon breakout: does the first break of a calm day's range carry on?

    python strategies/mnq/calmbreak.py

The one filter in winrate.py that cleared break-even in both halves was
narrow (31 trades in six years): on a calm day, after 14:00, go with a break
through a QQQ strike.  If that is a real effect it should not need the
strike.  This tests the general form on Dukascopy's Nasdaq-100 minutes: on
days whose range by 14:00 is below k times the typical pace (the median
full-day range of the last 20 sessions, scaled by the square root of the time
elapsed), take the first break of the day's high or low between 14:00 and
15:30 in its direction, at the next minute's open, with a resting stop and
target, out at 15:55; 2020-2023 against 2024-2026.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import data                                                                  # noqa: E402
from winrate import COST_BP, LEVEL, SPLIT, outcome                           # noqa: E402


def main() -> int:
    days = data.sessions("duka")
    keys = sorted(days)
    ranges, rows = [], {}
    for j in range(1, len(keys)):
        d, p = keys[j], keys[j - 1]
        prev, day = days[p], days[d]
        ranges.append((prev.h.max() - prev.l.min()) / prev.c[-1])
        if len(ranges) < 21:
            continue
        typical = float(np.median(ranges[-21:-1]))
        o, h, l, c = day.o, day.h, day.l, day.c
        n = len(o)
        if n < 380:
            continue
        rng_2pm = (h[:270].max() - l[:270].min()) / c[269]
        pace = typical * np.sqrt(270 / 390)
        hi, lo = h[:270].max(), l[:270].min()
        brk = None
        for i in range(270, min(360, n - 2)):
            if c[i] > hi:
                brk = (i, 1)
                break
            if c[i] < lo:
                brk = (i, -1)
                break
            hi, lo = max(hi, h[i]), min(lo, l[i])
        if brk is None:
            continue
        i, side = brk
        for k, (sb, tb), how in itertools.product((0.6, 0.8, 1.0, 99.0), ((5, 15), (10, 20), (10, 30), (10, 10)), ("with", "fade")):
            if rng_2pm >= k * pace:
                continue
            w, bp = outcome(o, h, l, i + 1, side if how == "with" else -side, sb, tb, n)
            key = f"{'any day' if k > 50 else f'range by 14:00 < {k:g}x typical pace'} | {how} the break | {sb}/{tb} bp"
            r = rows.setdefault(key, {"dev": [], "test": [], "wins_dev": [], "wins_test": [], "be": (sb + COST_BP) / (sb + tb)})
            part = "dev" if d < SPLIT else "test"
            r[part].append(bp)
            r["wins_" + part].append(w == 1)
    out = {}
    print(f"{len(keys)} sessions; first break of the day's range 14:00-15:30, next-minute open, out by 15:55")
    for key, r in sorted(rows.items()):
        a, b = np.array(r["dev"]), np.array(r["test"])
        if len(a) < 10 or len(b) < 10:
            continue
        row = {"n": [len(a), len(b)], "win": [round(float(np.mean(r["wins_dev"])), 3), round(float(np.mean(r["wins_test"])), 3)],
               "breakeven": round(r["be"], 3),
               "pts": [round(float(a.mean() * LEVEL / 1e4), 2), round(float(b.mean() * LEVEL / 1e4), 2)],
               "t": [round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2), round(float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b)))), 2)]}
        out[key] = row
        print(f"  {key:62s} n {row['n'][0]:4d}/{row['n'][1]:4d} win {row['win'][0]:.0%}/{row['win'][1]:.0%} be {row['breakeven']:.0%} "
              f"| {row['pts'][0]:+6.2f}/{row['pts'][1]:+6.2f} pts t {row['t'][0]:+.1f}/{row['t'][1]:+.1f}")
    (ROOT / "strategies" / "mnq" / "calmbreak.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
