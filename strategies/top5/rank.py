"""Every strategy on the lists, on one footing: dollars a day on $25,000, 2012 to September 2026.

    python strategies/top5/rank.py            # ranked over 2012-2026
    python strategies/top5/rank.py --by 3y    # ranked over the last three years

The lists quote different windows and sizes: the leveraged-fund top 50 leads
with the last six months (a semiconductor rally), the NQ set with compounding
returns, the quick trades with 2013-2026.  Here every strategy runs at its own
list's sizing over the same years and is ranked by dollars a day over the
whole stretch, with 2012-2018 and 2019-2026 beside it, the Sharpe, the worst
day, the worst losing stretch of a fixed $25,000 account, and what holding the
same funds made.

* leveraged-fund top 50 (profitable-strategies/leveraged-etfs): the whole
  account in one position, 8 bp slippage a side, the synthetic series before a
  fund existed (strategies/etf/synth.py);
* NQ E-mini at 2x (profitable-strategies/nq-2x): twice the account in
  notional, 0.2 bp commission and 1 bp slippage, back-adjusted NQ;
* the first fourteen (profitable-strategies/*.json): their own slots, 1 bp
  commission and 10 bp slippage, on TQQQ, SOXL and QLD, the funds with the
  history;
* the quick trades: the Nasdaq-100 breakout with its 0.30% stop (books.py) as
  booked on paper, QQQ at 4x and TQQQ at 2x buying power.

Anything that trades TSMX or TSM is left out.  The funded day trades ($2 to
$15 a session in their own report) and the scalpers (none held up on real
quotes) are listed from their reports, not rerun.
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
START, SPLIT, LAST3 = "2012-01-03", "2019-01-01", "2023-09-22"
WINDOWS = {"all": (START, C.END), "2012-18": (START, "2018-12-31"), "2019-26": (SPLIT, C.END), "3y": (LAST3, C.END)}
OUT = C.ROOT / "strategies" / "top5" / "rank.json"


def hold_usd(symbols, a: str, b: str) -> float:
    """Dollars a day of the same funds held in equal parts, $25,000 in all."""
    u, _ = C.market(symbols)
    rs = []
    for s in symbols:
        bars = u.bars[s] if hasattr(u, "bars") else u[s]
        d = list(bars.dates)
        c = np.asarray(bars.close, dtype=float)
        idx = [i for i, x in enumerate(d) if a <= x <= b and i > 0]
        rs.append(np.array([c[i] / c[i - 1] - 1 for i in idx]))
    n = min(len(r) for r in rs)
    return round(float(np.mean([r[-n:] for r in rs], axis=0).mean() * C.ACCOUNT), 1)


def row(name: str, family: str, source: str, result, symbols) -> dict:
    out = {"name": name, "list": source, "family": family, "symbols": list(symbols)}
    for tag, (a, b) in WINDOWS.items():
        _, r = C.daily_returns(result, a, b)
        out[tag] = C.day_stats(r)
    t = [x for x in result.journal.trades if x.exit_date >= START]
    out["trades"] = len(t)
    out["trades_3y"] = len([x for x in t if x.exit_date >= LAST3])
    out["hold_usd_per_day"] = hold_usd(symbols, START, C.END)
    out["hold_usd_per_day_3y"] = hold_usd(symbols, LAST3, C.END)
    return out


def family_of(name: str) -> str:
    n = name.lower()
    for key in ("uptrend dip", "quick dip", "trend breakout", "short-trend", "momentum", "52-week", "pullback",
                "volume momentum", "burst", "calm trend", "flush", "dip", "combo", "squeeze", "red day"):
        if key in n:
            return key
    return n


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    by = args[args.index("--by") + 1] if "--by" in args else "all"
    rows = []
    # the leveraged-fund top 50
    for p in sorted((PS / "leveraged-etfs").glob("[0-9][0-9]_*.json")):
        d = json.loads(p.read_text())
        if C.excluded(d["symbols"]):
            continue
        res = C.backtest(d["genome"], d["symbols"], start=START, slippage=8.0)
        rows.append(row(d["genome"]["name"], family_of(d["genome"]["name"]), f"leveraged-etfs #{p.name[:2]}", res, d["symbols"]))
        print(f"  {rows[-1]['list']:20s} {rows[-1]['name'][:60]:60s} ${rows[-1]['all']['usd_per_day']:+7.1f}", flush=True)
    # NQ E-mini at 2x
    for i, g in enumerate(json.loads((PS / "nq-2x" / "all.json").read_text())["genomes"], 1):
        res = C.backtest(g, ["NQ1!"], start=START, slippage=1.0, commission=0.2, leverage=2.0)
        rows.append(row(g["name"], "nq " + family_of(g["name"]), f"nq-2x #{i:02d}", res, ["NQ1!"]))
        print(f"  {rows[-1]['list']:20s} {rows[-1]['name'][:60]:60s} ${rows[-1]['all']['usd_per_day']:+7.1f}", flush=True)
    # the first fourteen
    for i, g in enumerate(json.loads((PS / "all.json").read_text())["genomes"], 1):
        syms = ["TQQQ", "SOXL", "QLD"]
        res = C.backtest(g, syms, start=START, slippage=10.0, commission=1.0)
        rows.append(row(g["name"], "etf " + family_of(g["name"]), f"first fourteen #{i:02d}", res, syms))
        print(f"  {rows[-1]['list']:20s} {rows[-1]['name'][:60]:60s} ${rows[-1]['all']['usd_per_day']:+7.1f}", flush=True)
    # the quick trades
    import books
    s = books.ndx_series(0.003)
    ds = np.array(sorted(s))
    r = np.array([s[d][0] for d in ds])
    b = books.btc_series()
    bds = np.array(sorted(b))
    br = np.array([b[d][0] for d in bds])
    legs = [(ds, r, 4, "Nasdaq-100 noise-area breakout, 0.30% stop, QQQ at 4x buying power", "intraday breakout"),
            (ds, r, 6, "Nasdaq-100 noise-area breakout, 0.30% stop, TQQQ at 2x buying power", "intraday breakout"),
            (bds, br, 1, "MSTR sleeve: Bitcoin's breakout in US hours x1.8, MSTR at 1x buying power", "intraday breakout")]
    for dd, rr, units, name, fam in legs:
        q = {"name": name, "list": "quick trades", "family": fam, "symbols": ["NQ (USATECH)" if units > 1 else "BTC/USD"], "trades": None}
        for tag, (a, z) in WINDOWS.items():
            m = (dd >= a) & (dd <= z)
            q[tag] = C.day_stats(rr[m] * units)
        rows.append(q)
    rows.sort(key=lambda x: -(x[by].get("usd_per_day") or -1e9))
    a0, z0 = WINDOWS[by]
    print(f"\n{len(rows)} strategies, ranked by dollars a day on $25,000, {a0} to {z0}")
    print(f"{'#':>3} {'strategy':62s} {'list':20s} {'$/day':>7} {'12-18':>7} {'19-26':>7} {'3 yrs':>7} {'Sharpe':>6} "
          f"{'worst stretch':>13} {'hold':>6}")
    for k, x in enumerate(rows, 1):
        a, o, n, t = x[by], x["2012-18"], x["2019-26"], x["3y"]
        hold = x.get("hold_usd_per_day_3y" if by == "3y" else "hold_usd_per_day") or 0
        print(f"{k:3d} {x['name'][:62]:62s} {x['list'][:20]:20s} {x['all'].get('usd_per_day', 0):+7.1f} {o.get('usd_per_day', 0):+7.1f} "
              f"{n.get('usd_per_day', 0):+7.1f} {t.get('usd_per_day', 0):+7.1f} {a['sharpe']:+6.2f} {a['worst_stretch']:+13,.0f} {hold:+6.1f}")
    OUT.write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
