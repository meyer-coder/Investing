"""The 08:30 New York data releases: does the first minute's jump carry on or snap back?

    python strategies/mnq/releases.py

Most US economic numbers (jobs, CPI, retail sales, jobless claims every
Thursday) come out at 08:30 New York, an hour before the stock market opens,
and the Nasdaq-100 future jumps within the minute.  For every weekday on
Dukascopy's Nasdaq-100 minutes (September 2020 on), the 08:30 bar's move is
scaled by the typical one-minute move of the half hour before it; when it is
large, buy or sell at the open of the next minute (or the one after, a minute
to let the spread settle) and leave 5, 7 or 10 minutes later.  Costs are
doubled here, because the spread is widest right after a number.  First
three years against the rest.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import duka                                                                  # noqa: E402
from edges import COST_BP                                                    # noqa: E402

SPLIT = "2024-01-01"


def main() -> int:
    pre = duka.premarket()
    rows = {}
    for d, bars in pre.items():
        bars = sorted(bars)
        minutes = {b[0][11:16]: b for b in bars}
        # the 08:30 New York bar, in UTC: 12:30 in summer, 13:30 in winter
        at = next((t for t in minutes if duka.dt.datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
                   .replace(tzinfo=duka.dt.timezone.utc).astimezone(duka.NY).strftime("%H:%M") == "08:30"), None)
        if at is None:
            continue
        seq = [b for b in bars]
        i = next(k for k, b in enumerate(seq) if b[0][11:16] == at)
        if i < 20 or i + 13 >= len(seq):
            continue
        c = np.array([b[4] for b in seq])
        o = np.array([b[1] for b in seq])
        r = np.diff(c[i - 20:i]) / c[i - 20:i - 1]
        sd = max(float(np.std(r)), 1e-6)
        z = (c[i] / c[i - 1] - 1.0) / sd
        rows[d] = (z, o, i)
    out = {}
    for k, delay, hold, how in itertools.product((3.0, 5.0, 8.0, 12.0), (1, 2), (5, 7, 10), ("with", "fade")):
        res = {"dev": [], "test": []}
        for d, (z, o, i) in rows.items():
            if abs(z) < k:
                continue
            j = i + delay
            if j + hold >= len(o):
                continue
            side = np.sign(z) * (1 if how == "with" else -1)
            net = side * (o[j + hold] / o[j] - 1.0) * 1e4 - 2 * COST_BP
            res["dev" if d < SPLIT else "test"].append(net)
        a, b = np.array(res["dev"]), np.array(res["test"])
        if len(a) < 20 or len(b) < 15:
            continue
        key = f"08:30 move beyond {k:g} typical minutes: {'go with it' if how == 'with' else 'fade it'}, in {delay}m later, {hold}m hold"
        out[key] = {"dev_bp": round(float(a.mean()), 2), "dev_n": len(a),
                    "dev_t": round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2),
                    "test_bp": round(float(b.mean()), 2), "test_n": len(b),
                    "test_t": round(float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b)))), 2),
                    "win": round(float((np.concatenate([a, b]) > 0).mean()), 3)}
    ranked = sorted(out.items(), key=lambda kv: -kv[1]["dev_t"])
    print(f"{len(rows)} weekdays with an 08:30 bar; dev before {SPLIT}; costs doubled ({2 * COST_BP:.2f} bp)")
    for key, v in ranked[:24]:
        print(f"  {key:78s} dev {v['dev_bp']:+6.2f}bp t{v['dev_t']:+4.1f} n{v['dev_n']:4d} | test {v['test_bp']:+6.2f}bp "
              f"t{v['test_t']:+4.1f} n{v['test_n']:4d} | win {v['win']:.0%}")
    (ROOT / "strategies" / "mnq" / "releases.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
