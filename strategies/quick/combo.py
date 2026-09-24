"""The quick trades that held up, run together on one $25,000 account.

    python strategies/quick/combo.py

Two kinds of edge survived the tests in this folder:

* the noise-area breakout on an index (trend.py): Nasdaq-100, S&P 500,
  Russell 2000 and Dow, each on its own one-minute bars (indexes.py);
* the opening-range breakout on the day's biggest gappers among the 72 large
  caps (stock_orb.py, gap over 2%, the first five minutes, stop at one 14-day
  average range, 2% of the account at risk a trade).

This puts them on one account.  The index book splits its exposure evenly
across the indexes that trade that day; the stock book keeps its own risk
sizing; together they stay within the day-trading buying power (4x).  The
report gives each part and the whole at three sizes, from QQQ/SPY-type funds at
up to 4x to the 3x funds (TQQQ, UPRO, TNA, UDOW) at up to 4x, with the worst
day, the worst stretch and the share of days at $200 or more.  Sessions common
to all the data (Sep 2022 to Sep 2026); dev to Dec 2023, test after.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import index                                                                 # noqa: E402
import indexes                                                               # noqa: E402
import trend                                                                 # noqa: E402

ACCOUNT = 25_000.0
SPLIT = "2024-01-01"
NAMES = {"NDX": None, "SPX": "USA500", "RUT": "USSC2000", "DJI": "USA30"}


def index_days():
    """{index: (dates, net return a day on the notional, the day's low, trades)}."""
    out = {}
    for name, inst in NAMES.items():
        D = index.load() if inst is None else indexes.load(inst)
        r, lo, n, m = trend.noise_days(D)
        out[name] = (list(D["dates"]), r, lo, n)
    return out


def stock_days():
    import stock_orb
    P = stock_orb.prepare()
    pnl, ntr = stock_orb.run(P, minutes=5, top=3, rr_min=0.0, stop_atr=1.0, gap_min=0.02, first_bar=True, risk=0.02)
    return list(P["dates"]), pnl, ntr


def stats(ds, v, label):
    ds = np.array(ds)
    dev, test = ds < SPLIT, ds >= SPLIT
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean()), 0) for y in sorted({x[:4] for x in ds})}
    row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
           "up_days": round(float((v > 0).mean()), 3), "days_200": round(float((v >= 200).mean()), 3),
           "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0),
           "sharpe": round(float(v.mean() / (v.std() + 1e-9) * np.sqrt(252)), 2), "years": years}
    print(f"  {label:44s} ${row['dev_usd']:+5.0f}/${row['test_usd']:+5.0f} a day | Sharpe {row['sharpe']:+.2f} | up {row['up_days']:.0%} "
          f"$200+ {row['days_200']:.0%} | worst day ${row['worst_day']:+.0f} | worst stretch ${row['max_drawdown']:+.0f} | "
          + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()), flush=True)
    return row


def main() -> int:
    idx = index_days()
    sd, spnl, sntr = stock_days()
    common = sorted(set(sd).intersection(*[set(v[0]) for v in idx.values()]))
    pos = {k: {d: i for i, d in enumerate(v[0])} for k, v in idx.items()}
    spos = {d: i for i, d in enumerate(sd)}
    R = np.array([[idx[k][1][pos[k][d]] for k in idx] for d in common])     # (days, indexes) net return on notional
    N = np.array([[idx[k][3][pos[k][d]] for k in idx] for d in common])
    S = np.array([spnl[spos[d]] for d in common])                            # stock book dollars at its own sizing
    ok = ~np.isnan(R).any(axis=1) & ~np.isnan(S)
    common = [d for d, o in zip(common, ok) if o]
    R, N, S = R[ok], N[ok], S[ok]
    print(f"{len(common)} common sessions {common[0]} to {common[-1]}")
    corr = np.corrcoef(np.column_stack([R, S]).T)
    print("daily correlation (NDX SPX RUT DJI stocks):\n" + "\n".join("  " + " ".join(f"{x:+.2f}" for x in row) for row in corr))
    res = {"sessions": len(common), "from": common[0], "to": common[-1], "correlation": corr.round(3).tolist(), "books": {}}
    for k, name in enumerate(idx):
        res["books"][f"{name} alone, 4x"] = stats(common, R[:, k] * 4 * ACCOUNT, f"{name} noise area alone, 4x")
    # the index book: exposure split over the indexes that trade that day
    active = np.maximum((N > 0).sum(axis=1), 1)
    split_ret = np.nansum(R, axis=1) / active
    for lev, mult, tag in ((2, 1, "index book, 2x (QQQ/SPY/IWM/DIA)"), (4, 1, "index book, 4x (QQQ/SPY/IWM/DIA)"),
                           (4, 3, "index book, 4x in 3x funds")):
        res["books"][tag] = stats(common, split_ret * lev * mult * ACCOUNT, tag)
    res["books"]["gap breakout stocks (2% risk, 4x cap)"] = stats(common, S, "gap breakout stocks (2% risk, 4x cap)")
    # both: half the buying power each
    for lev, mult, tag in ((4, 1, "both, 4x (index funds 1x-type)"), (4, 3, "both, 4x with 3x index funds")):
        v = split_ret * (lev / 2) * mult * ACCOUNT + S / 2
        res["books"][tag] = stats(common, v, tag)
    (ROOT / "strategies" / "quick" / "combo.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
