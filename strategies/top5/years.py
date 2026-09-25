"""Year by year, 2020 to September 2026: the three-year leaders, the quick trades, the books, and holding.

    python strategies/top5/years.py

Dollars a day on $25,000 (the account's mean daily return x $25,000) for each
calendar year, every strategy at its list's size on its own funds and costs,
as rank.py runs them.  The books add the legs' daily dollars (the breakout at
TQQQ 2x, the MSTR sleeve at 1x, FBB5 with the whole account), and for them
each year also shows the worst day, the worst losing stretch inside the year
and the share of days of $100 or more.  Written to strategies/top5/years.json.
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
START = "2012-01-03"
YEARS = [str(y) for y in range(2020, 2027)]
LEV = ["09", "02", "25", "18", "08", "05", "12", "24"]                     # FBB5 first, then the others by 3-year rank
NQ = ["Calm Trend Champion", "Managed Long"]


def series_of(result) -> dict:
    dates, r = C.daily_returns(result, START, C.END)
    return {d: x * C.ACCOUNT for d, x in zip(dates, r)}


def hold(sym: str, lev: float = 1.0) -> dict:
    u, _ = C.market([sym])
    b = u.bars[sym]
    c = np.asarray(b.close, dtype=float)
    return {d: (c[i] / c[i - 1] - 1) * lev * C.ACCOUNT for i, d in enumerate(b.dates) if i > 0 and d >= START}


def by_year(s: dict) -> dict:
    out = {}
    for y in YEARS:
        v = np.array([x for d, x in s.items() if d[:4] == y])
        if v.size < 50:
            continue
        eq = np.cumsum(v)
        dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
        out[y] = {"usd": round(float(v.mean()), 1), "worst_day": round(float(v.min()), 0), "worst_stretch": round(dd, 0),
                  "days_100": round(float((v >= 100).mean()), 3), "days": int(v.size)}
    return out


def main() -> int:
    rows = []
    for num in LEV:
        p = next((PS / "leveraged-etfs").glob(f"{num}_*.json"))
        d = json.loads(p.read_text())
        s = series_of(C.backtest(d["genome"], d["symbols"], start=START, slippage=8.0))
        rows.append({"name": d["genome"]["name"], "kind": "leveraged-fund swing", "series": s})
    nq = json.loads((PS / "nq-2x" / "all.json").read_text())["genomes"]
    for name in NQ:
        g = next(x for x in nq if x["name"] == name)
        s = series_of(C.backtest(g, ["NQ1!"], start=START, slippage=1.0, commission=0.2, leverage=2.0))
        rows.append({"name": f"NQ at 2x: {name}", "kind": "NQ swing", "series": s})
    import books
    ndx = {d: v[0] * 6 * C.ACCOUNT for d, v in books.ndx_series(0.003).items()}
    mstr = {d: v[0] * C.ACCOUNT for d, v in books.btc_series().items()}
    rows.append({"name": "Nasdaq-100 breakout, TQQQ at 2x", "kind": "quick trade", "series": ndx})
    rows.append({"name": "MSTR sleeve (Bitcoin's breakout x1.8), 1x", "kind": "quick trade", "series": mstr})
    fbb5 = rows[0]["series"]
    days = sorted(ndx)
    books_ = {"Today's book: TQQQ 2x + MSTR 1x": (ndx, mstr), "TQQQ 2x + FBB5": (ndx, fbb5),
              "TQQQ 2x + MSTR 1x + FBB5": (ndx, mstr, fbb5)}
    for name, legs in books_.items():
        rows.append({"name": name, "kind": "book", "series": {d: sum(leg.get(d, 0.0) for leg in legs) for d in days}})
    for sym, lev, label in (("MU.2X", 1.0, "Holding Micron at 2x (MUU)"), ("SOXL", 1.0, "Holding SOXL"),
                            ("NQ1!", 2.0, "Holding NQ at 2x")):
        rows.append({"name": label, "kind": "holding", "series": hold(sym, lev)})
    out = []
    print(f"dollars a day on $25,000, by year ({YEARS[0]} to {C.END})")
    print(f"{'':44s} " + " ".join(f"{y:>7s}" for y in YEARS))
    for r in rows:
        yr = by_year(r["series"])
        out.append({"name": r["name"], "kind": r["kind"], "years": yr})
        print(f"{r['name'][:44]:44s} " + " ".join(f"{yr[y]['usd']:+7.0f}" if y in yr else f"{'':>7s}" for y in YEARS))
    print("\nthe books, each year: worst day / worst losing stretch inside the year / days of $100+")
    for r in out:
        if r["kind"] != "book":
            continue
        print(f"  {r['name']}")
        for y, v in r["years"].items():
            print(f"    {y}: ${v['usd']:+.0f} a day, worst day ${v['worst_day']:+,.0f}, worst stretch ${v['worst_stretch']:+,.0f}, "
                  f"$100+ on {v['days_100']:.0%} of days")
    (C.ROOT / "strategies" / "top5" / "years.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
