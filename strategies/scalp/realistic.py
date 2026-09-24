"""The drop books with everything a real bot would face: mid prices, seconds of delay, each name's spread.

    python strategies/scalp/realistic.py

The minute backtests fill at the bid-side open of the next minute, instantly,
paying a cent and 1 bp each way.  The checks since then:

* mid prices (panel.build_mid, candidates --mid): the bid alone overstated
  the bounce, most at the open when the spread is still settling;
* one-second quotes around the books' own trades (onesec.py): a bot reading
  minute bars is in two or three seconds after the minute ends, and keeps
  LATENCY_KEEP of the mid-price bounce there;
* each name's real spread (spreads.py, sampled live from Nasdaq's best bid
  and offer): a bot that buys at the offer and sells at the bid pays one full
  spread a round trip, plus 1 bp of slippage and fees here.

This replays the opening-window own-drop book and the model book (refitted
on mid-price returns, dev years only) under those conditions, for assumed
spreads (1 cent, 2, 4 and 6 bp) and, once spreads.json exists, the measured
ones, restricted or not to names whose bounce clears their spread.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import book                                                                  # noqa: E402
import dropmodel                                                             # noqa: E402

SPREADS = ROOT / "strategies" / "scalp" / "spreads.json"


def latency_keep(d: dict) -> tuple:
    """Share of the minute-bar mid bounce left 2-3 s after the minute, on the books' own trades (onesec.py).

    The one-second quotes of each sampled trade are matched to the same row of the
    mid-price table: kept = mean one-second mid return entering 2-3 s late over
    the mean minute-bar mid return (entering at the next minute's first quote)."""
    import onesec
    key = {(str(d["date_of"][i]), str(d["names"][d["name"][i]]), int(d["f"]["minute"][i])): i for i in range(len(d["day"]))}
    one, minute = [], []
    for which, every in (("open", 3), ("model", 60)):
        for t in onesec.trades("2025-09-24", which)[::every]:
            i = key.get((t["date"], t["name"], t["minute"]))
            if i is None or np.isnan(d["y"][i, 0, 2]):
                continue
            r = onesec.measure(t)                                            # cached quotes; no download
            if r is None:
                continue
            one.append((r["mid_2"] + r["mid_3"]) / 2)
            minute.append(float(d["y"][i, 0, 2]))
    return float(np.mean(one) / np.mean(minute)), len(one), float(np.mean(one) * 1e4), float(np.mean(minute) * 1e4)


def measured_spreads(names) -> dict:
    """Median spread in bp per name over the sampled sessions (empty until spreads.py has run)."""
    if not SPREADS.exists():
        return {}
    by = {}
    for s in json.loads(SPREADS.read_text())["sessions"]:
        for n, v in s["names"].items():
            by.setdefault(n, []).append(v["median_bp"])
    return {n: float(np.median(v)) for n, v in by.items() if n in names}


def replay_net(d, sel, prio, net, hold=3, slots=3):
    """book.replay with a per-trade net return supplied (overrides the table's return and cost)."""
    dd = dict(d)
    y = d["y"].copy()
    y[:, 0, list(d["horizons"]).index(hold)] = net
    dd["y"] = y
    f = dict(d["f"])
    f["px"] = np.full(len(net), np.inf)                                      # costs are already in `net`
    dd["f"] = f
    return book.replay(dd, sel, np.ones(len(sel)), prio, hold=hold, slots=slots, cost="none")


def main() -> int:
    d = book.load("mid")
    f = d["f"]
    names = list(d["names"])
    keep, n_keep, one_bp, min_bp = latency_keep(d)
    print(f"{n_keep} sampled trades: minute-bar mid {min_bp:+.2f} bp, one-second mid 2-3 s late {one_bp:+.2f} bp")
    y3 = d["y"][:, 0, 2].astype(float)
    gross = y3 * keep                                                        # what is left 2-3 s after the minute
    px = f["px"].astype(float)
    spreads = measured_spreads(names)
    print(f"mid prices; bounce kept after 2-3 s: {keep:.0%}; measured spreads for {len(spreads)} names")
    dev = d["date_of"] < book.SPLIT
    drop = (f["r1_atr"] < -0.5) & (f["resid_z"] < -1.5) & (f["minute"] >= 5) & (f["minute"] <= 380)
    open_rule = (f["r1_atr"] < -1.5) & (f["resid_z"] < -1.5) & (f["minute"] >= 5) & (f["minute"] <= 30)
    model, X = dropmodel.fit(d, drop & dev, y3)
    pred = np.full(len(y3), np.nan)
    pred[drop] = model.predict(X[drop], num_threads=4) * keep
    res = {"latency_keep": round(keep, 3), "books": {}}
    cost_sets = {"1 cent spread": 0.01 / px, "2 bp spread": np.full(len(px), 2e-4), "4 bp spread": np.full(len(px), 4e-4),
                 "6 bp spread": np.full(len(px), 6e-4)}
    if spreads:
        sp = np.array([spreads.get(n, np.nan) for n in names]) * 1e-4
        cost_sets["measured spreads"] = sp[d["name"]]
    for cname, spread in cost_sets.items():
        cost = np.maximum(spread, 0.01 / px) + 1e-4                          # never under a cent; plus 1 bp
        net = gross - cost
        ok = ~np.isnan(cost)
        row = book.report(replay_net(d, open_rule & ok, -f["resid_z"], net), f"opening own drop, {cname}")
        res["books"][f"opening own drop | {cname}"] = row
        sel = drop & ok & (pred - cost > 2e-4)
        row = book.report(replay_net(d, sel, np.nan_to_num(pred - cost), net), f"model pick (edge > 2 bp), {cname}")
        res["books"][f"model pick | {cname}"] = row
    (ROOT / "strategies" / "scalp" / "realistic.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
