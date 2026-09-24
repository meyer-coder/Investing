"""The short-hold families again, on mid prices: does going with a sharp move work once the bid artifact is gone?

    python strategies/scalp/midfamilies.py

On bid-only bars a sharp drop looks like it snaps back (the spread widening
and narrowing), which flatters buying drops and penalizes going with them.
On mid prices (panel.build_mid) neither bias is there.  Four ways to trade a
name's sharp own move (beyond k of its typical range and z of its residual
against the other names) in four windows, holding one to three minutes, as a
three-slot book with the tight and base costs: buy the drop, sell the drop
(momentum), buy the rise (momentum), sell the rise.
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

WINDOWS = {"09:35-09:45": (5, 15), "09:35-10:00": (5, 30), "10:00-15:50": (30, 380), "09:35-15:50": (5, 380)}


def main() -> int:
    d = book.load("mid")
    f = d["f"]
    res = {}
    for (move, side, name), (wn, (a, b)), k, z, hold in itertools.product(
            ((-1, 1, "buy the drop"), (-1, -1, "sell the drop"), (1, 1, "buy the rise"), (1, -1, "sell the rise")),
            WINDOWS.items(), (0.75, 1.5, 3.0), (2.0, 3.0), (1, 2, 3)):
        sig = (move * f["r1_atr"] > k) & (move * f["resid_z"] > z) & (f["minute"] >= a) & (f["minute"] <= b)
        prio = np.abs(f["resid_z"])
        for cost in ("tight", "base"):
            label = f"{name} {wn} k{k} z{z} hold {hold}m | {cost}"
            res[label] = book.report(book.replay(d, sig, np.full(len(sig), side), prio, hold=hold, slots=3, cost=cost))
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print(f"{len(res)} books on mid prices; best by the weaker of dev (to 2024-08) and test; $ a day at 1x")
    for k_, v in ranked[:25]:
        print(f"  {k_:52s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} (x4 ${4 * v['test_usd']:+5.0f}) up {v['test_up']:.0%} "
              f"{v['trades_per_day']:5.1f} tr/d {v['bp_per_trade']:+.2f} bp | " + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in v["years"].items()))
    (ROOT / "strategies" / "scalp" / "midfamilies.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
