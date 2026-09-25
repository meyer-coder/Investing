"""Which strategies really trade, and which mostly sit in a fund?  And FBB5's rule on funds other than Micron.

    python strategies/top5/active.py

For the three-year leaders and the legs of the books, 2012 to September 2026
(and the last three years):

* nights held: the share of sessions that end with a position on;
* the average holding time and the trades a year;
* how closely the strategy's days follow simply holding its funds
  (the correlation of the daily P&L with the funds' own daily move);
* dollars a day on $25,000, the Sharpe, the worst losing stretch, and whether
  it trades Micron (MU.2X, the synthetic MUU).

Then FBB5, the one leveraged-fund rule that beat random entries in rigor.py,
unchanged on SOXL and TQQQ instead of MUU and SOXL, alone and together, and on
the synthetic 3x semiconductor and Nasdaq-100 funds from 2005 (so 2008 is in).
Written to strategies/top5/active.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "quick"))
import common as C                                                           # noqa: E402

PS = C.ROOT / "profitable-strategies"
START, LAST3 = "2012-01-03", "2023-09-22"
LEV = {"D609": "02", "CB51": "25", "CBE3": "18", "FBB5": "09", "MUU/SOXL Quick Dip 2/2/6/4": "08",
       "MUU Quick Dip (split bot 1)": "05", "852D": "12", "01D4": "35", "Short-Trend Rider (split bot 2)": "24"}
NQ = {"NQ Calm Trend Champion": "Calm Trend Champion", "NQ Managed Long": "Managed Long"}
FBB5_ON = [("FBB5 on SOXL + TQQQ", ["SOXL", "TQQQ"], START), ("FBB5 on SOXL", ["SOXL"], START), ("FBB5 on TQQQ", ["TQQQ"], START),
           ("FBB5 on SOXL + TQQQ + TECL", ["SOXL", "TQQQ", "TECL"], START),
           ("FBB5 on synthetic 3x semis + Nasdaq-100, from 2005", ["SMH.3X", "QQQ.3X"], "2005-01-03")]


def fund_move(symbols, dates):
    """The funds' equal-weight daily move on the strategy's days."""
    u, _ = C.market(symbols)
    cols = []
    for s in symbols:
        b = u.bars[s]
        c = np.asarray(b.close, dtype=float)
        m = {d: c[i] / c[i - 1] - 1 for i, d in enumerate(b.dates) if i > 0}
        cols.append([m.get(d, 0.0) for d in dates])
    return np.mean(np.array(cols), axis=0)


def daily_row(label, genome, symbols, start, **kw):
    res = C.backtest(genome, symbols, start=start, **kw)
    dates, r = C.daily_returns(res, start, C.END)
    ds = np.array(dates)
    trades = res.journal.trades
    held = sum(t.bars_held for t in trades)
    years = len(dates) / 252.0
    move = fund_move(symbols, dates) * kw.get("leverage", 1.0)
    out = {"label": label, "funds": list(symbols), "micron": any(s.startswith("MU.") or s == "MUU" for s in symbols),
           "from": dates[0], "nights_held": round(held / len(dates), 3), "avg_hold": f"{np.mean([t.bars_held for t in trades]):.1f} days",
           "trades_a_year": round(len(trades) / years, 1), "follows_the_fund": round(float(np.corrcoef(r, move)[0, 1]), 2),
           "all": C.day_stats(r), "3y": C.day_stats(r[ds >= LAST3])}
    yrs = {}
    for d, x in zip(dates, r):
        yrs.setdefault(d[:4], []).append(x * C.ACCOUNT)
    out["years"] = {y: round(float(np.mean(v)), 0) for y, v in sorted(yrs.items()) if y >= "2020"}
    return out


def breakout_row():
    import books
    import index
    import indexes
    import trend
    s = books.ndx_series(0.003)
    ds = np.array(sorted(s))
    r = np.array([s[d][0] for d in ds]) * 6                                  # TQQQ at 2x buying power
    old = indexes.load("USATECH")
    keep = np.array(old["dates"]) < "2020-09-01"
    old = {k: (old[k][keep] if k != "dates" else np.array(old["dates"])[keep]) for k in ("O", "H", "L", "C", "pc", "dates")}
    log, moves = [], {}
    for D in (old, index.load()):
        trend.noise_days(D, hard_stop=0.003, log=log)
        for d, o, c in zip(D["dates"], D["O"][:, 0], D["C"][:, -1]):
            moves[str(d)] = c / o - 1.0
    mins = np.array([b - a + 1 for _, _, a, b, _, _ in log])
    move = np.array([moves.get(d, 0.0) for d in ds]) * 6
    out = {"label": "Nasdaq-100 breakout, TQQQ at 2x", "funds": ["TQQQ (or MNQ)"], "micron": False, "from": str(ds[0]),
           "nights_held": 0.0, "avg_hold": f"{mins.mean():.0f} minutes", "trades_a_year": round(len(log) / (len(ds) / 252.0), 1),
           "follows_the_fund": round(float(np.corrcoef(r, move)[0, 1]), 2),
           "all": C.day_stats(r), "3y": C.day_stats(r[ds >= LAST3])}
    yrs = {}
    for d, x in zip(ds, r):
        yrs.setdefault(d[:4], []).append(x * C.ACCOUNT)
    out["years"] = {y: round(float(np.mean(v)), 0) for y, v in sorted(yrs.items()) if y >= "2020"}
    return out


def main() -> int:
    rows = []
    for label, num in LEV.items():
        d = json.loads(next((PS / "leveraged-etfs").glob(f"{num}_*.json")).read_text())
        rows.append(daily_row(label, d["genome"], d["symbols"], START, slippage=8.0))
    nq = json.loads((PS / "nq-2x" / "all.json").read_text())["genomes"]
    for label, name in NQ.items():
        g = next(x for x in nq if x["name"] == name)
        rows.append(daily_row(label, g, ["NQ1!"], START, slippage=1.0, commission=0.2, leverage=2.0))
    rows.append(breakout_row())
    fbb5 = json.loads(next((PS / "leveraged-etfs").glob("09_*.json")).read_text())["genome"]
    for label, syms, start in FBB5_ON:
        rows.append(daily_row(label, fbb5, syms, start, slippage=8.0))
    print(f"{'strategy':50s} {'Micron':>6} {'nights held':>11} {'avg hold':>12} {'trades/yr':>9} {'follows fund':>12} "
          f"{'$/day':>7} {'3 yrs':>7} {'Sharpe':>6} {'worst stretch':>13}")
    for x in rows:
        a, t = x["all"], x["3y"]
        print(f"{x['label'][:50]:50s} {'yes' if x['micron'] else 'no':>6} {x['nights_held']:11.0%} {x['avg_hold']:>12} "
              f"{x['trades_a_year']:9.1f} {x['follows_the_fund']:+12.2f} {a['usd_per_day']:+7.1f} {t['usd_per_day']:+7.1f} "
              f"{a['sharpe']:+6.2f} {a['worst_stretch']:+13,.0f}")
    print("\nby year, $ a day:")
    for x in rows:
        print(f"  {x['label'][:50]:50s} " + " ".join(f"{y}:{v:+5.0f}" for y, v in x["years"].items()))
    (C.ROOT / "strategies" / "top5" / "active.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
