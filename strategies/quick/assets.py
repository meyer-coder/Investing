"""Intraday trend across markets that do not move together: Nasdaq-100, crude oil, gold, bonds, the euro.

    python strategies/quick/assets.py

One market's intraday trend edge is small (Sharpe about 1 on the Nasdaq-100,
trend.py).  Edges in unrelated markets add up faster than their risk, so a book
across several can be steadier than any one.  Each market is traded in its
busiest hours (indexes.SESSIONS), with the noise-area breakout (trend.py) and
the first half hour predicting the last (index.first_last_half_hour), net of
a round-trip cost in basis points that fits its micro future (MNQ, MCL, MGC,
the bond and euro futures).

The book gives each market the same risk: its exposure is set so that its
own daily P&L has the same standard deviation over the past 60 sessions, then
the whole is scaled to a target daily risk on $25,000.  Dev Sep 2020 to Dec
2023, test Jan 2024 to Sep 2026.
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

SPLIT = "2024-01-01"
ACCOUNT = 25_000.0
MARKETS = {"NDX": (None, 1.0), "WTI": ("WTI", 3.0), "GOLD": ("GOLD", 1.5), "TBOND": ("TBOND", 3.0), "EURUSD": ("EURUSD", 1.5)}


def first_last(D: dict, cost_bp: float):
    """Gao et al. on any session: the return from the previous close to 30 minutes in sets the side for the last 30."""
    O, C, pc = D["O"], D["C"], D["pc"]
    T = O.shape[1]
    r1 = C[:, 29] / pc - 1.0
    side = np.sign(r1)
    ret = side * (C[:, T - 1] / O[:, T - 30] - 1.0) - np.where(side != 0, cost_bp * 1e-4, 0.0)
    return np.where(np.isnan(pc), np.nan, ret)


def stats(ds, v, label):
    ds = np.array(ds)
    ok = ~np.isnan(v)
    ds, v = ds[ok], v[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean() * 1e4), 1) for y in sorted({x[:4] for x in ds})}
    row = {"dev_bp": round(float(v[dev].mean() * 1e4), 2), "test_bp": round(float(v[test].mean() * 1e4), 2),
           "sharpe_dev": round(float(v[dev].mean() / (v[dev].std() + 1e-12) * np.sqrt(252)), 2),
           "sharpe_test": round(float(v[test].mean() / (v[test].std() + 1e-12) * np.sqrt(252)), 2), "years_bp": years}
    print(f"  {label:44s} dev {row['dev_bp']:+6.2f} / test {row['test_bp']:+6.2f} bp a day | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} | "
          + " ".join(f"{y[2:]}:{x:+.1f}" for y, x in years.items()), flush=True)
    return row


def main() -> int:
    series = {}
    res = {"markets": {}, "book": {}}
    for name, (inst, cost_bp) in MARKETS.items():
        D = index.load() if inst is None else indexes.load(inst)
        dates = list(D["dates"])
        print(f"-- {name}: {len(dates)} sessions {dates[0]} to {dates[-1]}, {D['O'].shape[1]} minutes a day, cost {cost_bp} bp")
        for bm in (1.0, 1.5):
            r, lo, n, m = trend.noise_days(D, band_mult=bm, cost=cost_bp * 1e-4)
            res["markets"][f"{name} noise area x{bm}"] = stats(dates, r, f"{name} noise area x{bm}")
            series[f"{name} noise area x{bm}"] = dict(zip(dates, r))
        r = first_last(D, cost_bp)
        res["markets"][f"{name} first->last half hour"] = stats(dates, r, f"{name} first->last half hour")
        series[f"{name} first->last half hour"] = dict(zip(dates, r))
    # the book: one rule per market (the band x1.0 breakout), equal risk, scaled to a daily risk target
    legs = [f"{k} noise area x1.0" for k in MARKETS]
    common = sorted(set.intersection(*[set(d for d, x in series[l].items() if not np.isnan(x)) for l in legs]))
    X = np.array([[series[l][d] for l in legs] for d in common])
    print(f"book over {len(common)} common sessions; daily correlation of the legs:")
    print("\n".join("  " + " ".join(f"{x:+.2f}" for x in row) for row in np.corrcoef(X.T)))
    w = np.zeros_like(X)
    for i in range(60, len(X)):
        sd = X[i - 60:i].std(axis=0)
        w[i] = (1 / np.where(sd > 0, sd, np.inf)) / len(legs)
    book = (w * X).sum(axis=1)
    book[:60] = np.nan
    ds = np.array(common)
    ok = ~np.isnan(book)
    for target in (0.005, 0.01, 0.02):                                       # daily risk as a share of the account
        scale = target / np.nanstd(book[ok][:300])                           # sized on the first 300 sessions only
        usd = book * scale * ACCOUNT
        v = usd[ok]
        eq = np.cumsum(v)
        dd = float((eq - np.maximum.accumulate(eq)).min())
        dsx = ds[ok]
        dev, test = dsx < SPLIT, dsx >= SPLIT
        years = {y: round(float(v[np.array([x[:4] == y for x in dsx])].mean()), 0) for y in sorted({x[:4] for x in dsx})}
        row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
               "sharpe_dev": round(float(v[dev].mean() / v[dev].std() * np.sqrt(252)), 2),
               "sharpe_test": round(float(v[test].mean() / v[test].std() * np.sqrt(252)), 2),
               "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0), "years": years}
        res["book"][f"daily risk {target:.1%}"] = row
        print(f"  book at {target:.1%} daily risk: ${row['dev_usd']:+.0f}/${row['test_usd']:+.0f} a day | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} | "
              f"worst day ${row['worst_day']:+.0f} | worst stretch ${row['max_drawdown']:+.0f} | " + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()))
    (ROOT / "strategies" / "quick" / "assets.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
