"""Toward $100 a day on $25,000 at the risk of the $70-80 book: which legs, at which sizes?

    python strategies/top5/book.py

Legs (daily P&L per unit, net of costs):

* ndx   - the Nasdaq-100 breakout as booked, 0.30% stop (books.py); TQQQ at 1x
          buying power is 3 units;
* mstr  - Bitcoin's breakout in US hours times 1.8, for MSTR at 1x buying power
          (books.py, from mid-2017);
* nq    - NQ E-mini at 2x, Managed Long (profitable-strategies/nq-2x #15), the
          list's best Sharpe, held for days; one unit is the strategy at 2x on
          $25,000 (1 MNQ is about 2.5x);
* plus any of the top five that rigor.py found to time its entries.

Sizes are fixed in advance or set on 2013-2019 alone (each leg scaled to the
same risk there, then the whole book scaled so its worst losing stretch on
2013-2019 fits the budget); 2020 to September 2026 then shows what they did.
The budget is the $70-80 book's own worst stretch, about $16,000 (64%).
Written to strategies/top5/book.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quick"))
import common as C                                                           # noqa: E402

SPLIT = "2020-01-01"
BUDGET = 16_000.0
NQ_FILE = C.ROOT / "profitable-strategies" / "nq-2x" / "all.json"


def legs(extra=()):
    import books
    ndx = {d: v[0] for d, v in books.ndx_series(0.003).items()}
    btc = {d: v[0] for d, v in books.btc_series().items()}
    g = next(x for x in json.loads(NQ_FILE.read_text())["genomes"] if x["name"] == "Managed Long")
    res = C.backtest(g, ["NQ1!"], start="2012-01-03", slippage=1.0, commission=0.2, leverage=2.0)
    dts, r = C.daily_returns(res, "2012-01-03", C.END)
    nq = dict(zip(dts, r))
    cols = {"ndx": ndx, "mstr": btc, "nq": nq}
    for name, series in extra:
        cols[name] = series
    days = sorted(set(ndx) & set(nq))
    X = np.array([[cols[k].get(d, 0.0) for k in cols] for d in days])
    return days, list(cols), X


def evaluate(days, X, w, label):
    usd = X @ np.asarray(w) * C.ACCOUNT
    ds = np.array(days)
    out = {"label": label, "weights": [round(float(x), 3) for x in w]}
    for tag, m in (("all", np.ones(len(ds), bool)), ("2013-19", ds < SPLIT), ("2020-26", ds >= SPLIT)):
        v = usd[m]
        eq = np.cumsum(v)
        dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
        out[tag] = {"usd": round(float(v.mean()), 1), "median": round(float(np.median(v)), 1),
                    "sharpe": round(float(v.mean() / v.std() * np.sqrt(252)), 2), "worst_day": round(float(v.min()), 0),
                    "worst_stretch": round(dd, 0), "days_100": round(float((v >= 100).mean()), 3),
                    "days_down": round(float((v < 0).mean()), 3)}
    return out


def main() -> int:
    days, names, X = legs()
    ds = np.array(days)
    dev = ds < SPLIT
    print(f"{len(days)} sessions {days[0]} to {days[-1]}; legs {names}")
    print("correlation of the legs, all days:\n" + "\n".join(f"  {n:5s} " + " ".join(f"{x:+.2f}" for x in row)
                                                              for n, row in zip(names, np.corrcoef(X.T))))
    for j, n in enumerate(names):
        v = X[:, j] * C.ACCOUNT
        print(f"  {n:5s} one unit: ${v.mean():+6.1f} a day, Sharpe {v.mean() / v.std() * np.sqrt(252):+.2f}; "
              f"2013-19 ${v[dev].mean():+6.1f}, 2020-26 ${v[~dev].mean():+6.1f}")
    books_ = []
    fixed = [((6, 1, 0), "the $70-80 book: TQQQ 2x + MSTR 1x"), ((6, 0, 1), "TQQQ 2x + NQ Managed Long"),
             ((6, 1, 1), "TQQQ 2x + MSTR 1x + NQ Managed Long"), ((9, 1, 1), "TQQQ 3x + MSTR 1x + NQ Managed Long"),
             ((6, 0, 1.5), "TQQQ 2x + NQ Managed Long x1.5"), ((9, 0, 1), "TQQQ 3x + NQ Managed Long")]
    for w, label in fixed:
        books_.append(evaluate(days, X, w, label))
    # equal risk on 2013-2019, the whole book scaled to the budget on 2013-2019
    for sub, label in (((0, 2), "ndx + nq, equal risk, sized on 2013-19"), ((0, 1, 2), "ndx + mstr + nq, equal risk, sized on 2013-19")):
        w = np.zeros(len(names))
        live = dev & (X[:, 1] != 0) if 1 in sub else dev
        for j in sub:
            w[j] = 1.0 / X[live, j].std()
        usd = X[dev] @ w * C.ACCOUNT
        eq = np.cumsum(usd)
        dd = -(eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min()
        w *= BUDGET / dd
        books_.append(evaluate(days, X, w, label))
    print(f"\n{'book':48s} {'weights (ndx, mstr, nq)':26s} {'$/day':>7} {'13-19':>7} {'20-26':>7} {'Sharpe':>6} {'worst day':>9} "
          f"{'worst stretch':>13} {'$100+ days':>10}")
    for b in books_:
        a, o, n = b["all"], b["2013-19"], b["2020-26"]
        print(f"{b['label'][:48]:48s} {str(b['weights']):26s} {a['usd']:+7.1f} {o['usd']:+7.1f} {n['usd']:+7.1f} {a['sharpe']:+6.2f} "
              f"{a['worst_day']:+9,.0f} {a['worst_stretch']:+13,.0f} {a['days_100']:10.0%}")
    (C.ROOT / "strategies" / "top5" / "book.json").write_text(json.dumps({"legs": names, "books": books_}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
