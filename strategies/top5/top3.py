"""The top three that actually trade, with no Micron: the Nasdaq-100 breakout, FBB5 on SOXL / TQQQ / TECL,
and the gap breakout, alone and together, by year.

    python strategies/top5/top3.py

active.py splits the list into rules that mostly sit in a fund and rules
that trade in and out.  Of the ones that trade:

* the Nasdaq-100 breakout: intraday, never held overnight, about 240 trades a
  year; booked at TQQQ 2x (rigor_ndx.py: 3,176 trades, t 4.2);
* FBB5's dip rule (leveraged-etfs #9), held about 3 days, a position on about
  a quarter of the nights; it beat random entries over 41,791 trades
  (rigor.py) and here runs on SOXL, TQQQ and TECL instead of MUU and SOXL, the
  whole $25,000 in one fund at a time;
* the gap breakout as it was backtested (stock_orb.run, the combo.py
  settings): of the large caps that open 2% or more from their last close,
  the three whose first five minutes are widest against their own recent
  first five minutes; intraday, 2% of $25,000 at risk a trade as on paper,
  half the opening spread measured on 2026-09-24 plus 2 bp.  Its one-minute
  bars start in September 2022.  (Taking the three biggest gaps instead, as
  the paper bot did until 2026-09-24, lost money at those costs.)

Dollars a day on $25,000 each, and the three summed as if run side by side
(each on its own $25,000 of buying power).  Written to
strategies/top5/top3.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quick"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scalp"))
import common as C                                                           # noqa: E402

PS = C.ROOT / "profitable-strategies"
FBB5_FUNDS = ["SOXL", "TQQQ", "TECL"]
LAST3 = "2023-09-22"


def legs():
    import books
    import realistic
    import stock_orb
    ndx = {d: v[0] * 6 * C.ACCOUNT for d, v in books.ndx_series(0.003).items()}
    g = json.loads(next((PS / "leveraged-etfs").glob("09_*.json")).read_text())["genome"]
    res = C.backtest(g, FBB5_FUNDS, start="2012-01-03", slippage=8.0)
    dts, r = C.daily_returns(res, "2012-01-03", C.END)
    fbb5 = {d: x * C.ACCOUNT for d, x in zip(dts, r)}
    P = stock_orb.prepare()
    sp = realistic.measured_spreads(P["names"])
    half = np.array([sp.get(n, np.nan) for n in P["names"]]) / 2
    pnl, _ = stock_orb.run(P, minutes=5, top=3, rr_min=0.0, stop_atr=1.0, gap_min=0.02, first_bar=True, risk=0.02,
                           spread_bp=half)
    gap = {str(d): float(x) for d, x in zip(P["dates"], pnl) if not np.isnan(x)}
    return {"Nasdaq-100 breakout, TQQQ 2x": ndx, "FBB5 on SOXL / TQQQ / TECL": fbb5, "Gap breakout, 2% risk": gap}


def stats(v: np.ndarray) -> dict:
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    return {"usd": round(float(v.mean()), 1), "sharpe": round(float(v.mean() / v.std() * np.sqrt(252)), 2),
            "worst_day": round(float(v.min()), 0), "worst_stretch": round(dd, 0), "days_100": round(float((v >= 100).mean()), 3),
            "days_down": round(float((v < 0).mean()), 3), "days": int(v.size)}


def report(name: str, days, cols) -> dict:
    v = np.array([sum(c.get(d, 0.0) for c in cols) for d in days])
    ds = np.array(days)
    out = {"name": name, "from": days[0], "all": stats(v), "3y": stats(v[ds >= LAST3]) if (ds >= LAST3).sum() > 50 else None}
    out["years"] = {y: round(float(v[np.array([d[:4] == y for d in days])].mean()), 0)
                    for y in sorted({d[:4] for d in days}) if y >= "2020" and sum(d[:4] == y for d in days) > 50}
    return out


def main() -> int:
    L = legs()
    names = list(L)
    ndx, fbb5, gap = (L[n] for n in names)
    long_days = sorted(set(ndx) & set(fbb5))
    gap_days = sorted(set(ndx) & set(fbb5) & set(gap))
    X = np.array([[L[n].get(d, 0.0) for n in names] for d in gap_days])
    print(f"daily correlation, {gap_days[0]} to {gap_days[-1]}:")
    for n, row in zip(names, np.corrcoef(X.T)):
        print(f"  {n:30s} " + " ".join(f"{x:+.2f}" for x in row))
    rows = [report(names[0], long_days, [ndx]), report(names[1], long_days, [fbb5]),
            report(names[0] + " + " + names[1], long_days, [ndx, fbb5]),
            report(names[2] + " (from Sep 2022)", gap_days, [gap]),
            report("All three (from Sep 2022)", gap_days, [ndx, fbb5, gap]),
            report("Breakout + FBB5, same window (from Sep 2022)", gap_days, [ndx, fbb5])]
    print(f"\n{'':52s} {'from':>10} {'$/day':>7} {'3 yrs':>7} {'Sharpe':>6} {'worst day':>9} {'worst stretch':>13} {'$100+ days':>10}")
    for x in rows:
        a, t = x["all"], x["3y"] or {"usd": float("nan")}
        print(f"{x['name'][:52]:52s} {x['from']:>10} {a['usd']:+7.1f} {t['usd']:+7.1f} {a['sharpe']:+6.2f} {a['worst_day']:+9,.0f} "
              f"{a['worst_stretch']:+13,.0f} {a['days_100']:10.0%}")
    print("\nby year, $ a day:")
    for x in rows:
        print(f"  {x['name'][:52]:52s} " + " ".join(f"{y}:{v:+5.0f}" for y, v in x["years"].items()))
    (C.ROOT / "strategies" / "top5" / "top3.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
