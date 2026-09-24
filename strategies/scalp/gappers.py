"""Names gapping on news, in the first hour: go with a sharp move in the gap's direction, or fade it.

    python strategies/scalp/gappers.py

The families (midfamilies.py) look at every name.  Earnings and other news
gaps are where the first minutes trend, if anywhere: names that opened more
than 2, 4 or 7% from the previous close, a sharp one-minute move in the gap's
direction (beyond k of the typical range, residual z above 1.5), traded with
the gap or against it for one to three minutes, on mid prices with the tight
cost (a cent and 1 bp a round trip).
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import book                                                                  # noqa: E402


def main() -> int:
    d = book.load("mid")
    f = d["f"]
    g = f["gap"]
    res = {}
    for G, (wn, (a, b)), k, hold, mode in itertools.product(
            (0.02, 0.04, 0.07), (("09:31-09:45", (1, 15)), ("09:35-10:00", (5, 30)), ("09:31-10:30", (1, 60))),
            (0.5, 1.5), (1, 2, 3), ("with the gap", "against the gap")):
        same = (np.sign(g) == np.sign(f["r1"])) & (np.abs(f["r1_atr"]) > k) & (np.abs(f["resid_z"]) > 1.5)
        sig = (np.abs(g) > G) & same & (f["minute"] >= a) & (f["minute"] <= b)
        side = np.sign(g) * (1 if mode == "with the gap" else -1)
        res[f"gap>{G:.0%} {wn} k{k} hold {hold}m {mode}"] = book.report(
            book.replay(d, sig, side, np.abs(f["resid_z"]), hold=hold, slots=3, cost="tight"))
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print(f"{len(res)} gapper books on mid prices; best by the weaker of dev and test ($ a day at 1x)")
    for k_, v in ranked[:12]:
        print(f"  {k_:48s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} {v['trades_per_day']:5.1f} tr/d {v['bp_per_trade']:+.2f} bp")
    (ROOT / "strategies" / "scalp" / "gappers.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
