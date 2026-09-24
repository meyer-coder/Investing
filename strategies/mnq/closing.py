"""Into the close: does the day's direction carry through its last half hour?

    python strategies/mnq/closing.py

Leveraged funds on the Nasdaq-100 (TQQQ, SQQQ, QLD and the rest) must trade
in the direction of the day's move near the close to keep their leverage, and
option dealers short gamma do the same; both flows are known to push the index
further the way it already went late in the day.  This measures it on
Dukascopy's Nasdaq-100 minutes, September 2020 on: at a set minute from 15:30
to 15:50, when the index is up or down more than a threshold since the
previous close, buy or sell at the next minute's open and leave 5 to 10
minutes later (never after 15:55), less today's MNQ cost.  First three years
against the rest, year by year.
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
from edges import COST_BP                                                    # noqa: E402

SPLIT = "2024-01-01"


def main() -> int:
    days = data.sessions("duka")
    keys = sorted(days)
    rows = {}
    for at, k, hold, side_name in itertools.product((360, 365, 370, 375, 380), (0.0025, 0.005, 0.01),
                                                    (5, 7, 10), ("with", "against")):
        if at + 1 + hold > 385:
            continue
        net = {"dev": [], "test": []}
        years: dict = {}
        for j, d in enumerate(keys[1:], 1):
            prev, day = days[keys[j - 1]], days[d]
            if (np.datetime64(d) - np.datetime64(prev.date)).astype(int) > 4 or len(day.o) < at + 2 + hold:
                continue
            move = day.c[at] / prev.c[-1] - 1.0
            if abs(move) <= k:
                continue
            side = np.sign(move) * (1 if side_name == "with" else -1)
            r = side * (day.o[at + 1 + hold] / day.o[at + 1] - 1.0) * 1e4 - COST_BP
            net["dev" if d < SPLIT else "test"].append(r)
            years.setdefault(d[:4], []).append(r)
        a, b = np.array(net["dev"]), np.array(net["test"])
        if len(a) < 20 or len(b) < 20:
            continue
        key = f"{'go with' if side_name == 'with' else 'fade'} a day beyond {k:.2%} at 15:{30 + at - 360:02d}, {hold}m"
        rows[key] = {"dev_bp": round(float(a.mean()), 2), "dev_n": len(a),
                     "dev_t": round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2),
                     "test_bp": round(float(b.mean()), 2), "test_n": len(b),
                     "test_t": round(float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b)))), 2),
                     "win": round(float((np.concatenate([a, b]) > 0).mean()), 3),
                     "years": {y: round(float(np.mean(v)), 1) for y, v in sorted(years.items())}}
    ranked = sorted(rows.items(), key=lambda kv: -(kv[1]["dev_t"]))
    print(f"{len(keys)} sessions {keys[0]} to {keys[-1]}; dev before {SPLIT}")
    for k, v in ranked[:30]:
        print(f"  {k:48s} dev {v['dev_bp']:+6.2f}bp t{v['dev_t']:+4.1f} n{v['dev_n']:4d} | test {v['test_bp']:+6.2f}bp "
              f"t{v['test_t']:+4.1f} n{v['test_n']:4d} | win {v['win']:.0%} | " + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in v["years"].items()))
    (ROOT / "strategies" / "mnq" / "closing.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
