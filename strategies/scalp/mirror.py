"""Does the own-drop scalper's edge run the other way?  A name's own sharp rise, shorted.

    python strategies/scalp/mirror.py

The Own-Drop Scalper (owndrop.py) buys a name that falls hard on its own in the
opening minutes.  If the cause is one aggressive order pushing a single name
around, a name that jumps on its own should come back too.  This measures the
exact mirror, with no setting changed: from the 09:35 bar to the 09:45 bar, a
one-minute return above 0.75 of the 14-minute average range and a residual
more than two standard deviations above normal (resid_z > 2); short at the next
minute's open and cover at the open four minutes later, less a cent and 1 bp
each way.  The long side is measured the same way, for comparison.  The 17
original names are split into their first 14 sessions and last 7; the 30 fresh
names count whole.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from events import cost_bp                                                   # noqa: E402
from residbot import POOL, universe                                          # noqa: E402

OUT = ROOT / "strategies" / "scalp" / "mirror.json"
HOLD = 4


def study() -> Dict[str, dict]:
    days = minute.sessions(POOL)
    dev = set(days[:14])
    u, f = universe(days)
    sess = np.array([minute.session_of(t) for t in u.calendar])
    orig = set(minute.SCALP_NAMES)
    acc: Dict[str, Dict[str, list]] = {}
    for s in POOL:
        m = f.matrix[s]
        r1, atr, z, mso = (np.asarray(m[k], dtype=float) for k in ("ret1", "atr_pct", "resid_z", "minutes_since_open"))
        o = np.asarray(u.bars[s].open, dtype=float)
        c2 = 2 * cost_bp(np.asarray(u.bars[s].close, dtype=float))
        window = (mso >= 5) & (mso <= 15)
        for side, cond, sign in (("long own-drop", (r1 < -0.75 * atr) & (z < -2.0), 1.0),
                                 ("short own-rise", (r1 > 0.75 * atr) & (z > 2.0), -1.0)):
            idx = np.flatnonzero(np.nan_to_num((cond & window).astype(float))[: len(o) - HOLD - 2].astype(bool))
            j, k = idx + 1, idx + 1 + HOLD
            same = sess[j] == sess[k]
            idx, j, k = idx[same], j[same], k[same]
            net = sign * (o[k] / o[j] - 1.0) * 1e4 - c2
            group = "original" if s in orig else "fresh"
            for i, x in zip(idx, net):
                part = f"{group} {'first 14' if sess[i] in dev else 'last 7'}" if group == "original" else "fresh all 21"
                acc.setdefault(side, {}).setdefault(part, []).append(float(x))
                acc[side].setdefault("by_day", {}).setdefault(sess[i], []).append(float(x))
    out = {}
    for side, parts in acc.items():
        out[side] = {}
        for part, xs in parts.items():
            if part == "by_day":
                continue
            a = np.array(xs)
            n_days = 14 if "first 14" in part else 7 if "last 7" in part else len(days)
            out[side][part] = {"bp": round(float(a.mean()), 2), "win": round(float((a > 0).mean()), 3),
                               "per_day": round(len(a) / n_days, 1),
                               "t": round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2) if len(a) > 2 else None}
        byd = parts["by_day"]
        out[side]["days_with_edge"] = round(float(np.mean([np.mean(v) > 0 for v in byd.values()])), 3)
    return out


def main() -> int:
    out = study()
    for side, parts in out.items():
        print(side, f"(days whose trades averaged positive: {parts['days_with_edge']:.0%})")
        for part, x in parts.items():
            if isinstance(x, dict):
                print(f"   {part:18s} {x['bp']:+6.2f} bp  win {x['win']:.0%}  {x['per_day']:5.1f}/day  t {x['t']}")
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
