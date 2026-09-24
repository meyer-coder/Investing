"""Fixed books (sizes decided up front, not fitted), on the longest history each leg has.

    python strategies/quick/books.py

maximize.py showed that fitting sizes to 2022-2024 simply loaded up on whatever
did best then (Bitcoin's 2023-24 trend), which then failed.  Here the books are
fixed in advance and run over every year each leg has:

* the Nasdaq-100 noise-area breakout from 2013 (USATECH one-minute bars:
  indexes.py to Aug 2020, index.py after), with and without a resting stop
  from the entry, through TQQQ at 1x to 4x buying power (3x to 12x the index);
* the same plus a Bitcoin-driven MSTR sleeve (crypto.py's rule times 1.8) from
  2017.

The stop's width is chosen here too: the best Sharpe on 2013-2019 among
STOPS, with 2020-2026 only reporting what that width then did (it picks 0.30%,
what paper.py and the Pine script use).

For each: dollars a day on $25,000 by year, the worst day, the worst losing
stretch, how long the account stayed under water, and the half-Kelly size (the
bet that maximizes long-run growth, halved for the error in the estimate).
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
STOPS = (0.0015, 0.002, 0.0025, 0.003, 0.004, 0.005, 0.0075)
SPLIT = "2020-01-01"                                                         # stop chosen on the years before this


def ndx_series(hard_stop=0.0):
    out = {}
    old = indexes.load("USATECH")
    keep = np.array(old["dates"]) < "2020-09-01"
    for k in ("O", "H", "L", "C", "pc"):
        old[k] = old[k][keep]
    old["dates"] = np.array(old["dates"])[keep]
    for D in (old, index.load()):
        r, lo, n, m = trend.noise_days(D, hard_stop=hard_stop)
        for d, x, y in zip(D["dates"], r, lo):
            if not np.isnan(x):
                out[str(d)] = (x, y)
    return out


def btc_series():
    B = indexes.load("BTCUSD")
    r, lo, n, m = trend.noise_days(B, cost=3e-4)
    return {str(d): (1.8 * x, 1.8 * y) for d, x, y in zip(B["dates"], r, lo) if not np.isnan(x)}


def report(ds, usd, low, label):
    ds = np.array(ds)
    eq = np.cumsum(usd)
    peak = np.maximum.accumulate(eq)
    dd = float((eq - peak).min())
    # longest time under water, in sessions
    under, longest = 0, 0
    for e, p in zip(eq, peak):
        under = under + 1 if e < p else 0
        longest = max(longest, under)
    years = {y: round(float(usd[np.array([x[:4] == y for x in ds])].mean()), 0) for y in sorted({x[:4] for x in ds})}
    row = {"from": ds[0], "to": ds[-1], "usd": round(float(usd.mean()), 1), "worst_day": round(float(low.min()), 0),
           "max_drawdown": round(dd, 0), "max_drawdown_pct": round(-dd / ACCOUNT * 100, 0), "longest_under_water_days": longest,
           "sharpe": round(float(usd.mean() / usd.std() * np.sqrt(252)), 2), "years": years,
           "years_positive": sum(v > 0 for v in years.values()), "days_200": round(float((usd >= 200).mean()), 3)}
    print(f"  {label:44s} ${row['usd']:+6.1f} a day | worst day ${row['worst_day']:+7.0f} | worst stretch ${row['max_drawdown']:+8.0f} "
          f"({row['max_drawdown_pct']:.0f}%) | {row['longest_under_water_days']} days under water | Sharpe {row['sharpe']:+.2f} | "
          f"{row['years_positive']}/{len(years)} yrs up | " + " ".join(f"{y[2:]}:{v:+.0f}" for y, v in years.items()), flush=True)
    return row


def sharpe(r):
    return float(r.mean() / r.std() * np.sqrt(252))


def choose_stop(series):
    """The stop width with the best Sharpe before SPLIT; the years after only show what each width then did."""
    rows = {}
    print(f"-- stop width chosen on the years before {SPLIT[:4]}, then the years after (bp a day on the index)")
    for hs, s in series.items():
        ds = np.array(sorted(s))
        r = np.array([s[d][0] for d in ds])
        lo = np.array([s[d][1] for d in ds])
        a, b = ds < SPLIT, ds >= SPLIT
        rows[hs] = {"dev_bp": round(float(r[a].mean() * 1e4), 2), "dev_sharpe": round(sharpe(r[a]), 2),
                    "test_bp": round(float(r[b].mean() * 1e4), 2), "test_sharpe": round(sharpe(r[b]), 2),
                    "test_worst_day_bp": round(float(lo[b].min() * 1e4), 0)}
        x = rows[hs]
        print(f"  stop {hs:.2%}: before {x['dev_bp']:+5.2f} bp (Sharpe {x['dev_sharpe']:+.2f}) | after {x['test_bp']:+5.2f} bp "
              f"(Sharpe {x['test_sharpe']:+.2f}) | worst day after {x['test_worst_day_bp']:+.0f} bp", flush=True)
    best = max(STOPS, key=lambda hs: rows[hs]["dev_sharpe"])
    print(f"  chosen: stop {best:.2%}")
    return best, rows


def main() -> int:
    series = {hs: ndx_series(hs) for hs in (0.0,) + STOPS}
    stop, scan = choose_stop(series)
    res = {"stop": stop, "stop_scan": {f"{hs:.2%}": row for hs, row in scan.items()}}
    for hs in (0.0, stop):
        ndx = series[hs]
        ds = sorted(ndx)
        r = np.array([ndx[d][0] for d in ds])
        lo = np.array([ndx[d][1] for d in ds])
        tag = f"stop {hs:.2%}" if hs else "no stop"
        kelly = r.mean() / r.var()
        print(f"-- Nasdaq breakout, {tag}: {len(ds)} sessions {ds[0]} to {ds[-1]}; {r.mean() * 1e4:+.2f} bp a day, "
              f"full Kelly {kelly:.1f}x the index, half Kelly {kelly / 2:.1f}x (TQQQ at {kelly / 6:.2f}x buying power)")
        res[f"kelly {tag}"] = round(float(kelly), 2)
        for bp in (1, 2, 3, 4):
            units = 3 * bp
            res[f"ndx {tag} | TQQQ {bp}x"] = report(ds, r * units * ACCOUNT, lo * units * ACCOUNT, f"TQQQ at {bp}x buying power ({units}x index), {tag}")
    ndx = series[stop]
    btc = btc_series()
    ds = sorted(set(ndx) & set(btc))
    R = np.array([[ndx[d][0], btc[d][0]] for d in ds])
    L = np.array([[ndx[d][1], btc[d][1]] for d in ds])
    print(f"-- Nasdaq breakout (stop {stop:.2%}) with an MSTR sleeve: {len(ds)} sessions {ds[0]} to {ds[-1]}; "
          f"correlation {np.corrcoef(R.T)[0, 1]:+.2f}")
    for bp_ndx, bp_mstr in ((4, 0), (3, 1), (2, 2), (2, 1), (0, 2)):
        e = np.array([3 * bp_ndx, bp_mstr])
        res[f"TQQQ {bp_ndx}x + MSTR {bp_mstr}x"] = report(ds, R @ e * ACCOUNT, L @ e * ACCOUNT,
                                                          f"TQQQ {bp_ndx}x + MSTR {bp_mstr}x buying power")
    (ROOT / "strategies" / "quick" / "books.json").write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
