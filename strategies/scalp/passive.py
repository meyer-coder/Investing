"""Buying the drop with a limit order at the bid instead of paying the offer.

    python strategies/scalp/passive.py

On mid prices the bounce after a sharp one-name drop is small (realistic.py):
most of what bid-only bars show is the spread widening during the selling
and narrowing after it.  A buyer who pays the offer gives that back; a buyer
who waits at the bid collects it, when filled.  The fill is the catch: a
resting bid fills when sellers keep coming, which is when the price is more
likely to keep falling.  So the fill rule here is the strict one: the limit
(the bid at the open of the minute after the signal) fills only if the bid
trades below it during that minute (it cannot then have been skipped in the
queue); otherwise the order is cancelled.  A filled position is sold at the
bid (a market sell) at the open `hold` minutes after entry.  Fees: 0.5 bp for
the round trip (about half a cent a share each way on a $200 stock).

Bid-side one-minute bars (the Dukascopy CFD bid is a stand-in for the
exchange's best bid); dev 2022-09 to 2024-08, test 2024-09 to 2026-09.
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

FEE = 0.5e-4


def passive_returns(d: dict, cube: np.ndarray, hold: int = 3, through_bp: float = 0.5):
    """Per candidate: filled or not, and the bid-to-bid return if filled."""
    day, name = d["day"].astype(int), d["name"].astype(int)
    t = d["f"]["minute"].astype(int)
    t_in = np.minimum(t + 1, 389)
    t_out = np.minimum(t + 1 + hold, 389)
    limit = cube[day, name, t_in, 0].astype(float)                           # the bid when the order goes in
    low = cube[day, name, t_in, 2].astype(float)                             # the bid's low that minute
    filled = (low < limit * (1 - through_bp * 1e-4)) & (t + 1 + hold < 386)
    ret = cube[day, name, t_out, 0] / limit - 1.0 - FEE
    return filled, ret


def replay(d, sel, prio, ret, hold=3, slots=3):
    dd = dict(d)
    y = d["y"].copy()
    y[:, 0, list(d["horizons"]).index(hold)] = ret
    dd["y"] = y
    return book.replay(dd, sel, np.ones(len(sel)), prio, hold=hold, slots=slots, cost="none")


def main() -> int:
    d = book.load("bid")
    f = d["f"]
    cube = np.load(book.candidates.panel.CACHE / "panel.npz")["cube"]
    res = {}
    print("limit buy at the bid after a sharp own drop; filled only if the bid trades through it; market sell after the hold")
    for hold in (1, 2, 3):
        filled, ret = passive_returns(d, cube, hold)
        for (wn, (a, b)), k, z in itertools.product((("09:35-10:00", (5, 30)), ("09:35-10:30", (5, 60)), ("10:30-15:50", (60, 380)),
                                                     ("09:35-15:50", (5, 380))), (1.0, 1.5, 3.0), (2.0, 3.0)):
            sig = (f["r1_atr"] < -k) & (f["resid_z"] < -z) & (f["minute"] >= a) & (f["minute"] <= b)
            label = f"{wn} k{k} z{z} hold {hold}m"
            # an order that does not fill is cancelled within the minute and never takes a slot
            row = book.report(replay(d, sig & filled, -f["resid_z"], ret, hold=hold), f"passive {label}")
            row["fill_rate"] = round(float(filled[sig].mean()), 3)
            row["signals_per_day"] = round(float(sig.sum() / len(set(d["date_of"]))), 1)
            res[label] = row
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print("best by the weaker of dev and test:")
    for k_, v in ranked[:12]:
        print(f"  {k_:40s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} at 1x, fill rate {v['fill_rate']:.0%}, "
              f"{v['trades_per_day']:.1f} tr/d {v['bp_per_trade']:+.2f} bp | " + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in v["years"].items()))
    (ROOT / "strategies" / "scalp" / "passive.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
