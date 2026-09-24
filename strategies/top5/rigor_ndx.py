"""The Nasdaq-100 breakout over 10,000+ trades: the rule as booked, on the four US index CFDs, 2013 to
September 2026, every trade simulated minute by minute.

    python strategies/top5/rigor_ndx.py

The quick-trade leg of the book is not one of the top five, but it carries
the book, so it gets the same treatment.  On the Nasdaq-100 alone it makes
about 3,000 trades in 13.7 years; the S&P 500, the Russell 2000 and the Dow
(Dukascopy's USA500, USSC2000 and USA30 one-minute bars, indexes.py) take the
same rule past 10,000.  The rule is trend.py's as booked: the band from 14
sessions, checks every 30 minutes, the VWAP exit, a resting stop 0.30% from
the entry, flat at the close, 1 bp a round trip.

* per index and pooled: trades, the mean trade, win rate, profit factor,
  t-statistic, the years, longs and shorts apart;
* random direction: the same trades at the same minutes with the side drawn
  at random, 2,000 times; the rule's edge is which way it bets, so this is
  the test of it;
* costs at 2 and 3 bp a round trip.

Written to profitable-strategies/top5/ndx/ (summary.json, trades.csv.gz) and
strategies/top5/rigor_ndx.json.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import index                                                                 # noqa: E402
import indexes                                                               # noqa: E402
import trend                                                                 # noqa: E402

KW = {"lookback": 14, "every": 30, "band_mult": 1.0, "vwap_stop": True, "cost": 1e-4, "hard_stop": 0.003}
NAMES = {"USATECH": "Nasdaq-100", "USA500": "S&P 500", "USSC2000": "Russell 2000", "USA30": "Dow"}
OUT = ROOT / "profitable-strategies" / "top5" / "ndx"
FLIPS = 2000


def load(inst: str):
    if inst != "USATECH":
        return [indexes.load(inst)]
    old = indexes.load("USATECH")
    keep = np.array(old["dates"]) < "2020-09-01"
    old = {k: (old[k][keep] if k != "dates" else np.array(old["dates"])[keep]) for k in ("O", "H", "L", "C", "pc", "dates")}
    return [old, index.load()]


def stats(r: np.ndarray) -> dict:
    n = r.size
    if not n:
        return {"trades": 0}
    w, lo = r[r > 0], r[r <= 0]
    return {"trades": int(n), "mean_bp": round(float(r.mean() * 1e4), 2), "win_rate": round(float(w.size / n), 3),
            "avg_win_bp": round(float(w.mean() * 1e4), 1) if w.size else 0.0, "avg_loss_bp": round(float(lo.mean() * 1e4), 1) if lo.size else 0.0,
            "profit_factor": round(float(w.sum() / -lo.sum()), 2) if lo.sum() < 0 else 99.0,
            "t_stat": round(float(r.mean() / (r.std(ddof=1) / np.sqrt(n))), 2) if n > 1 else 0.0}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    rows, res = [], {"rule": KW, "indexes": {}}
    for inst in NAMES:
        for D in load(inst):
            log = []
            trend.noise_days(D, log=log, **KW)
            dates = np.array(D["dates"])
            rows += [(inst, str(dates[i]), int(side), int(a), int(b), float(r), why) for i, side, a, b, r, why in log]
        mine = np.array([x[5] for x in rows if x[0] == inst])
        yrs = {}
        for x in rows:
            if x[0] == inst:
                yrs.setdefault(x[1][:4], []).append(x[5])
        st = stats(mine)
        st["from"] = min(x[1] for x in rows if x[0] == inst)
        st["long"] = stats(np.array([x[5] for x in rows if x[0] == inst and x[2] > 0]))
        st["short"] = stats(np.array([x[5] for x in rows if x[0] == inst and x[2] < 0]))
        st["years_bp"] = {y: round(float(np.mean(v) * 1e4), 1) for y, v in sorted(yrs.items())}
        st["years_up"] = int(sum(np.mean(v) > 0 for v in yrs.values()))
        st["years"] = len(yrs)
        res["indexes"][inst] = st
        print(f"  {NAMES[inst]:13s} from {st['from']}: {st['trades']:5d} trades, mean {st['mean_bp']:+6.2f} bp, win {st['win_rate']:.0%}, "
              f"PF {st['profit_factor']:.2f}, t {st['t_stat']:+.1f}, {st['years_up']}/{st['years']} years up | longs "
              f"{st['long']['mean_bp']:+.1f} bp, shorts {st['short']['mean_bp']:+.1f} bp", flush=True)
    r = np.array([x[5] for x in rows])
    gross = r + KW["cost"]                                                   # before costs, in the rule's direction
    pooled = stats(r)
    # random direction: the same trades, the side drawn at random
    flips = rng.choice([-1.0, 1.0], size=(FLIPS, r.size))
    rnd = (flips * gross[None, :]).mean(axis=1) - KW["cost"]
    pooled["random_direction_mean_bp"] = round(float(rnd.mean() * 1e4), 2)
    pooled["random_direction_p95_bp"] = round(float(np.percentile(rnd, 95) * 1e4), 2)
    pooled["p_value_vs_random"] = round(float((rnd >= r.mean()).mean()), 4)
    pooled["mean_bp_at_2bp"] = round(float((r.mean() - 1e-4) * 1e4), 2)
    pooled["mean_bp_at_3bp"] = round(float((r.mean() - 2e-4) * 1e4), 2)
    nq = np.array([x[5] for x in rows if x[0] == "USATECH"])
    others = np.array([x[5] for x in rows if x[0] != "USATECH"])
    res["pooled"] = pooled
    res["nasdaq_only"] = stats(nq)
    res["other_three"] = stats(others)
    print(f"  pooled: {pooled['trades']:,} trades, mean {pooled['mean_bp']:+.2f} bp, PF {pooled['profit_factor']:.2f}, t {pooled['t_stat']:+.1f}; "
          f"random direction {pooled['random_direction_mean_bp']:+.2f} bp (95th pct {pooled['random_direction_p95_bp']:+.2f}), "
          f"p = {pooled['p_value_vs_random']}; at 2 bp {pooled['mean_bp_at_2bp']:+.2f}, at 3 bp {pooled['mean_bp_at_3bp']:+.2f}")
    print(f"  the Nasdaq-100 alone: {res['nasdaq_only']['trades']:,} trades, {res['nasdaq_only']['mean_bp']:+.2f} bp, t {res['nasdaq_only']['t_stat']:+.1f}; "
          f"the other three: {res['other_three']['trades']:,} trades, {res['other_three']['mean_bp']:+.2f} bp, t {res['other_three']['t_stat']:+.1f}")
    (OUT / "summary.json").write_text(json.dumps(res, indent=1))
    (ROOT / "strategies" / "top5" / "rigor_ndx.json").write_text(json.dumps(res, indent=1))
    with gzip.open(OUT / "trades.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "date", "side", "entry_minute", "exit_minute", "return", "why"])
        w.writerows([(x[0], x[1], x[2], x[3], x[4], round(x[5], 6), x[6]) for x in rows])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
