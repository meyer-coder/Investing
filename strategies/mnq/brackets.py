"""Short average holds from stops and targets: cut losers fast, let winners run.

    python strategies/mnq/brackets.py

Fixed five-to-ten-minute holds found no edge (edges.py, model.py).  A trader
can still average five to ten minutes by leaving losers at a tight stop and
letting a winner run to a target, if prices trend over longer spans than they
revert.  This runs a few breakout entries (the first break of the 15- or
30-minute opening range, a new high or low of the day after 10:30, the day's
direction at 15:00) with resting stops of 10 to 30 bp, targets of one to four
times the stop and an hour at most, one position at a time, on Dukascopy's
Nasdaq-100 minutes: 2020-2023 against 2024-2026.
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
import sim                                                                   # noqa: E402
from edges import features                                                   # noqa: E402

SPLIT = "2024-01-01"


def first(mask):
    out = np.zeros(len(mask), dtype=int)
    idx = np.flatnonzero(mask)
    if len(idx):
        out[idx[0]] = 1
    return out


def entries():
    def orb(k):
        def sig(f):
            c, m = f["c"], f["mso"]
            up = first((c > f[f"orh{k}"]) & (m <= 240))
            dn = first((c < f[f"orl{k}"]) & (m <= 240))
            return np.where(up > 0, 1, np.where(dn > 0, -1, 0))
        return sig

    def extremes(f):
        m = f["mso"]
        w = (m >= 60) & (m <= 360)
        return np.where(w & (f["new_high"] > 0), 1, np.where(w & (f["new_low"] > 0), -1, 0))

    def three_pm(f):
        m = f["mso"]
        w = m == 330
        return np.where(w & (f["day_ret"] > 0.005), 1, np.where(w & (f["day_ret"] < -0.005), -1, 0))

    return {"15m opening range break": orb(15), "30m opening range break": orb(30),
            "new high/low of the day after 10:30": extremes, "15:00 with a day beyond 0.5%": three_pm}


def main() -> int:
    days = data.sessions("duka")
    dev = {d: v for d, v in days.items() if d < SPLIT}
    test = {d: v for d, v in days.items() if d >= SPLIT}
    out = {}
    for (name, sig), stop, mult in itertools.product(entries().items(), (10, 20, 30), (1, 2, 4)):
        rules = sim.Rules(signal=sig, hold=60, stop_bp=stop, target_bp=stop * mult)
        row = {}
        for part, ds in (("dev", dev), ("test", test)):
            r = sim.run(ds, rules, features)
            s = sim.summary(r)
            row[part] = {k: s[k] for k in ("trades_per_day", "avg_points", "win", "avg_minutes", "usd_per_day",
                                           "days_up", "worst_day", "years")}
        key = f"{name}, stop {stop}bp, target {stop * mult}bp"
        out[key] = row
        a, b = row["dev"], row["test"]
        print(f"{key:62s} dev {a['avg_points']:+6.2f}pts {a['avg_minutes']:4.1f}m ${a['usd_per_day']:6.1f}/d | "
              f"test {b['avg_points']:+6.2f}pts {b['avg_minutes']:4.1f}m ${b['usd_per_day']:6.1f}/d up {b['days_up']:.0%} "
              f"{b['trades_per_day']:.2f}tr/d", flush=True)
    (ROOT / "strategies" / "mnq" / "brackets.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
