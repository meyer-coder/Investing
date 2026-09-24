"""Fidget with the Nasdaq-100 breakout: which settings, chosen on 2013-2019 alone, still lead on 2020-2026?

    python strategies/top5/tune_ndx.py

The rule as booked (trend.py, books.py): the band from 14 sessions, checks
every 30 minutes, the VWAP exit, a resting stop 0.30% from the entry.  Here
162 settings (checks every 15, 30 or 60 minutes; bands from 10, 14 or 20
sessions; band width x0.8, x1 or x1.25; stops 0.2%, 0.3% or 0.4%; with and
without the VWAP exit) run over USATECH one-minute bars, 2013 to September
2026.  Each is ranked by its Sharpe over 2013-2019 only; the years after show
whether the pick, and the settings in general, carry over.  Written to
strategies/top5/tune_ndx.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import index                                                                 # noqa: E402
import indexes                                                               # noqa: E402
import trend                                                                 # noqa: E402

SPLIT = "2020-01-01"
BASE = {"every": 30, "lookback": 14, "band_mult": 1.0, "hard_stop": 0.003, "vwap_stop": True}
GRID = {"every": (15, 30, 60), "lookback": (10, 14, 20), "band_mult": (0.8, 1.0, 1.25), "hard_stop": (0.002, 0.003, 0.004),
        "vwap_stop": (True, False)}


def data():
    old = indexes.load("USATECH")
    keep = np.array(old["dates"]) < "2020-09-01"
    old = {k: (old[k][keep] if k != "dates" else np.array(old["dates"])[keep]) for k in ("O", "H", "L", "C", "pc", "dates")}
    return [old, index.load()]


def series(parts, **kw):
    out = {}
    for D in parts:
        r, lo, n, m = trend.noise_days(D, **kw)
        for d, x, y, k in zip(D["dates"], r, lo, n):
            if not np.isnan(x):
                out[str(d)] = (x, y, k)
    ds = np.array(sorted(out))
    return ds, np.array([out[d][0] for d in ds]), np.array([out[d][1] for d in ds]), np.array([out[d][2] for d in ds])


def stats(r: np.ndarray, n: np.ndarray) -> dict:
    return {"bp_per_day": round(float(r.mean() * 1e4), 2), "sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 2),
            "trades_per_day": round(float(n.mean()), 2), "worst_day_bp": round(float(r.min() * 1e4), 0)}


def main() -> int:
    parts = data()
    rows = []
    keys = list(GRID)
    for vals in itertools.product(*(GRID[k] for k in keys)):
        kw = dict(zip(keys, vals))
        ds, r, lo, n = series(parts, **kw)
        dev, test = ds < SPLIT, ds >= SPLIT
        rows.append({"settings": kw, "dev": stats(r[dev], n[dev]), "test": stats(r[test], n[test]), "all": stats(r, n),
                     "sessions": int(len(ds)), "trades": int(n.sum())})
    rows.sort(key=lambda x: -x["dev"]["sharpe"])
    base = next(x for x in rows if x["settings"] == BASE)
    pick = rows[0]
    test_sharpes = np.array([x["test"]["sharpe"] for x in rows])
    rank_of = lambda x: int((test_sharpes > x["test"]["sharpe"]).sum()) + 1
    res = {"grid": GRID, "split": SPLIT, "variants": len(rows), "base": base, "pick_on_dev": pick,
           "base_test_rank": rank_of(base), "pick_test_rank": rank_of(pick),
           "test_sharpe_median": round(float(np.median(test_sharpes)), 2), "test_positive": int((test_sharpes > 0).sum()),
           "dev_top10_test_sharpe_mean": round(float(np.mean([x["test"]["sharpe"] for x in rows[:10]])), 2),
           "dev_bottom10_test_sharpe_mean": round(float(np.mean([x["test"]["sharpe"] for x in rows[-10:]])), 2),
           "rows": rows}
    print(f"{len(rows)} settings; test (2020-2026) Sharpe median {res['test_sharpe_median']:+.2f}, positive in {res['test_positive']}")
    for label, x in (("as booked", base), ("best on 2013-2019", pick)):
        print(f"  {label:18s} {x['settings']}: dev {x['dev']['bp_per_day']:+.2f} bp Sharpe {x['dev']['sharpe']:+.2f} | "
              f"test {x['test']['bp_per_day']:+.2f} bp Sharpe {x['test']['sharpe']:+.2f} (rank {rank_of(x)} of {len(rows)} on test) | "
              f"{x['all']['trades_per_day']:.2f} trades a day")
    print(f"  the ten best on 2013-2019 averaged a test Sharpe of {res['dev_top10_test_sharpe_mean']:+.2f}; the ten worst "
          f"{res['dev_bottom10_test_sharpe_mean']:+.2f}")
    for x in rows[:10]:
        print(f"    {x['settings']} dev {x['dev']['sharpe']:+.2f} test {x['test']['sharpe']:+.2f} ({x['test']['bp_per_day']:+.2f} bp)")
    (ROOT / "strategies" / "top5" / "tune_ndx.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
