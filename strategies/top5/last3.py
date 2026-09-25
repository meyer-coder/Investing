"""The last three years alone: which strategies led, and did their trades beat random entries then?

    python strategies/top5/last3.py

rank.py --by 3y ranks every strategy by dollars a day from 2023-09-22 to
2026-09-22.  For the leaders that rigor.py has run over the 173 funds, this
takes the trades that opened in those three years and asks rigor.py's
questions inside the window:

* the average trade, and the same number of random entries on the same funds
  with the same holding times, 500 times;
* on how many of the funds the rule made more than holding the fund, both
  counted as dollars a day on $25,000 (the rule's trades at a fixed $25,000
  each, at the account leverage it runs at);
* the Nasdaq-100 breakout's trades on the four indexes the same way, with the
  side drawn at random for the comparison.

Written to strategies/top5/last3.json.
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C                                                           # noqa: E402
import rigor                                                                 # noqa: E402

LAST3 = "2023-09-22"
KEYS = ("d609", "cb51", "cbe3", "L09", "L08", "L42", "q05", "852d", "L14", "01d4", "r24", "ml")


def ledger(key: str):
    path = rigor.OUT / key / "trades.csv.gz"
    if not path.exists():
        return None
    with gzip.open(path, "rt") as fh:
        rows = list(csv.reader(fh))[1:]
    return [(r[0], r[1], r[2], float(r[3]), int(r[4])) for r in rows]


def fund_days(sym: str, lev: float):
    """Sessions in the window and holding's dollars a day on $25,000 over them."""
    u, _ = C.market([sym])
    bars = u.bars[sym]
    c = np.asarray(bars.close, dtype=float)
    idx = [i for i, d in enumerate(bars.dates) if d >= LAST3 and i > 0]
    r = np.array([c[i] / c[i - 1] - 1 for i in idx]) * lev
    return len(idx), float(r.mean() * C.ACCOUNT) if r.size else 0.0


def main() -> int:
    out = {"window": [LAST3, C.END], "strategies": {}}
    rng = np.random.default_rng(3)
    print(f"trades that opened {LAST3} to {C.END}, on the 173 funds")
    print(f"{'strategy':52s} {'trades':>7} {'mean':>8} {'random':>8} {'edge':>7} {'p':>6} {'$/day, median fund':>18} {'holding':>8} {'beat holding':>12}")
    for key in KEYS:
        trades = ledger(key)
        if trades is None:
            continue
        sp = rigor.spec(key)
        win = [t for t in trades if t[1] >= LAST3]
        rets = np.array([t[3] for t in win])
        st = C.trade_stats(rets)
        cost = sp["wide_kw"]["slippage"] + sp["wide_kw"].get("commission", 0.0)
        rnd = rigor.random_means(win, rng, 500, cost, LAST3)
        st["random_mean_bp"] = round(float(rnd.mean() * 1e4), 1)
        st["timing_edge_bp"] = round(float((rets.mean() - rnd.mean()) * 1e4), 1)
        st["p_value_vs_random"] = round(float((rnd >= rets.mean()).mean()), 3)
        by = {}
        for t in win:
            by.setdefault(t[0], []).append(t[3])
        lev = sp["hold_lev"]
        per = []
        for sym, _ in sp["members"]:
            try:
                n, hold = fund_days(sym, lev)
            except Exception:                                                # an underlying Yahoo no longer serves
                continue
            if n < 100:
                continue
            usd = sum(by.get(sym, [])) * C.ACCOUNT * lev / n
            per.append((usd, hold))
        per = np.array(per)
        st["funds"] = int(len(per))
        st["usd_per_day_median_fund"] = round(float(np.median(per[:, 0])), 1)
        st["hold_usd_per_day_median_fund"] = round(float(np.median(per[:, 1])), 1)
        st["funds_beat_holding"] = round(float((per[:, 0] > per[:, 1]).mean()), 3)
        st["funds_profitable"] = round(float((per[:, 0] > 0).mean()), 3)
        out["strategies"][key] = {"name": sp["name"], **st}
        print(f"{sp['name'][:52]:52s} {st['trades']:7,d} {st['mean_bp']:+7.1f}bp {st['random_mean_bp']:+7.1f}bp {st['timing_edge_bp']:+6.1f} "
              f"{st['p_value_vs_random']:6.3f} {st['usd_per_day_median_fund']:+18.1f} {st['hold_usd_per_day_median_fund']:+8.1f} "
              f"{st['funds_beat_holding']:12.0%}", flush=True)
    # the Nasdaq-100 breakout
    path = rigor.OUT / "ndx" / "trades.csv.gz"
    if path.exists():
        with gzip.open(path, "rt") as fh:
            rows = [r for r in list(csv.reader(fh))[1:] if r[1] >= LAST3]
        res = {}
        for label, keep in (("Nasdaq-100", lambda r: r[0] == "USATECH"), ("all four indexes", lambda r: True)):
            r = np.array([float(x[5]) for x in rows if keep(x)])
            gross = r + 1e-4
            flips = rng.choice([-1.0, 1.0], size=(2000, r.size))
            rnd = (flips * gross[None, :]).mean(axis=1) - 1e-4
            st = C.trade_stats(r)
            st["random_direction_mean_bp"] = round(float(rnd.mean() * 1e4), 2)
            st["p_value_vs_random"] = round(float((rnd >= r.mean()).mean()), 4)
            res[label] = st
            print(f"breakout, {label:18s} {st['trades']:7,d} trades, mean {st['mean_bp']:+.1f} bp, t {st['t_stat']:+.1f}; random side "
                  f"{st['random_direction_mean_bp']:+.2f} bp, p = {st['p_value_vs_random']}")
        out["ndx"] = res
    (C.ROOT / "strategies" / "top5" / "last3.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
