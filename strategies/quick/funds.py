"""The two quick trades on other funds and stocks: TQQQ, SOXL, MSTR and more.

    python strategies/quick/funds.py

The Nasdaq-100 noise-area breakout (trend.py) and the opening-range breakout
(stock_orb.py) were found on one-minute bars that go back years.  For leveraged
funds and names like MSTR there are no such bars here, so this uses what
Yahoo keeps:

* hourly bars for two years: the noise-area breakout checked at each hourly
  close (10:30 ... 15:30), and a first-hour range breakout in the first hour's
  direction, both flat at the close;
* five-minute bars for 60 days: the noise-area breakout checked every half
  hour (the rule as tested on the Nasdaq), and 5- and 30-minute range
  breakouts.

QQQ runs first as the check: its hourly and five-minute results can be set
against the one-minute Nasdaq-100 results over the same days.  Each round trip
pays two cents a share of spread and slippage plus 2 bp; dollars are on
$25,000 at 1x and at the 4x day-trading maximum (on a 3x fund, 4x is twelve
times the index).  Two years is too short to prove an edge, and 60 days far
shorter: the halves and the Sharpe say how much weight a line can bear.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import gap_volatile as gv                                                    # noqa: E402
import trend                                                                 # noqa: E402

ACCOUNT = 25_000.0
FUNDS = ["QQQ", "TQQQ", "SQQQ", "SOXL", "SOXS", "SMH", "UPRO", "SPY", "TNA", "IWM", "TSLL", "NVDL", "MSTU", "CONL",
         "LABU", "FNGU", "TECL", "ARKK", "IBIT", "GLD", "TLT", "XLE"]
STOCKS = ["MSTR", "COIN", "TSLA", "NVDA", "AMD", "PLTR", "SMCI", "MARA", "HOOD", "META", "AVGO", "MU"]


def arrays(sym: str, interval: str, rng: str, per_day: int):
    """{dates, O, H, L, C (days x bars), pc} from Yahoo bars, full sessions only."""
    raw = gv.yahoo(sym, interval, rng)
    if not raw:
        return None
    by = gv.sessions(raw)
    dates = [d for d in sorted(by) if len(by[d]) == per_day]
    if len(dates) < 30:
        return None
    X = np.array([[b[1:5] for b in by[d]] for d in dates], dtype=float)
    daily = gv.yahoo(sym, "1d", "3y")
    closes = {}
    if daily:
        import datetime as dt
        for t, c in zip(daily["t"], daily["c"]):
            if c is not None:
                closes[dt.datetime.fromtimestamp(t, tz=gv.NY).strftime("%Y-%m-%d")] = c
    alld = sorted(closes)
    pc = []
    for d in dates:
        prior = [x for x in alld if x < d]
        pc.append(closes[prior[-1]] if prior else np.nan)
    return {"dates": np.array(dates), "O": X[:, :, 0], "H": X[:, :, 1], "L": X[:, :, 2], "C": X[:, :, 3], "pc": np.array(pc)}


def orb_days(D: dict, bars: int = 1, stop: str = "range"):
    """Break of the first `bars` bars' range in their direction, stop at the other side, out at the close."""
    O, H, L, C = D["O"], D["H"], D["L"], D["C"]
    nd, T = O.shape
    ret = np.full(nd, np.nan)
    ntr = np.zeros(nd)
    for i in range(nd):
        hi, lo = H[i, :bars].max(), L[i, :bars].min()
        side = np.sign(C[i, bars - 1] - O[i, 0])
        if side == 0:
            ret[i] = 0.0
            continue
        lvl = hi if side > 0 else lo
        stp = lo if side > 0 else hi
        k0 = next((k for k in range(bars, T) if (side > 0 and H[i, k] >= lvl) or (side < 0 and L[i, k] <= lvl)), None)
        if k0 is None:
            ret[i] = 0.0
            continue
        px = max(O[i, k0], lvl) if side > 0 else min(O[i, k0], lvl)
        out = C[i, -1]
        for k in range(k0, T):
            if (side > 0 and L[i, k] <= stp) or (side < 0 and H[i, k] >= stp):
                out = stp if k == k0 else (min(O[i, k], stp) if side > 0 else max(O[i, k], stp))
                break
        ret[i] = side * (out / px - 1.0)
        ntr[i] = 1
    return ret, ntr


def stats(dates, r, n, cost_bp, label):
    ok = ~np.isnan(r)
    ds, v, k = np.array(dates)[ok], r[ok], n[ok]
    net = v - k * cost_bp * 1e-4
    half = len(net) // 2
    usd = net * ACCOUNT
    eq = np.cumsum(usd * 4)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    row = {"sessions": int(len(net)), "from": str(ds[0]) if len(ds) else None, "bp_per_day": round(float(net.mean() * 1e4), 2),
           "first_half_bp": round(float(net[:half].mean() * 1e4), 2), "second_half_bp": round(float(net[half:].mean() * 1e4), 2),
           "usd_1x": round(float(usd.mean()), 1), "usd_4x": round(float(usd.mean() * 4), 1),
           "worst_day_4x": round(float(usd.min() * 4), 0), "max_drawdown_4x": round(dd, 0),
           "sharpe": round(float(net.mean() / (net.std() + 1e-12) * np.sqrt(252)), 2),
           "trades_per_day": round(float(k.mean()), 2), "cost_bp": round(cost_bp, 1)}
    print(f"  {label:34s} {row['sessions']:4d} d | {row['bp_per_day']:+6.2f} bp/d (halves {row['first_half_bp']:+6.2f} / {row['second_half_bp']:+6.2f}) "
          f"| Sharpe {row['sharpe']:+5.2f} | $25k 1x ${row['usd_1x']:+5.0f}, 4x ${row['usd_4x']:+6.0f} | worst 4x ${row['worst_day_4x']:+6.0f} "
          f"| worst stretch 4x ${row['max_drawdown_4x']:+7.0f} | {row['trades_per_day']:.2f} tr/d", flush=True)
    return row


def main() -> int:
    res: Dict[str, dict] = {}
    for sym in FUNDS + STOCKS:
        hourly = arrays(sym, "60m", "730d", 7)
        five = arrays(sym, "5m", "60d", 78)
        if hourly is None and five is None:
            print(f"{sym}: no bars")
            continue
        px = float(np.nanmedian((hourly or five)["C"][:, -1]))
        cost = 2 * 0.02 / px * 1e4 / 2 + 2.0                                   # two cents a share round trip, plus 2 bp
        print(f"-- {sym} (about ${px:.0f}; {cost:.1f} bp a round trip)")
        res[sym] = {"price": round(px, 2), "cost_bp": round(cost, 1)}
        if hourly is not None:
            r, lo, n, m = trend.noise_days(hourly, lookback=14, every=1, cost=0.0)
            res[sym]["noise_hourly"] = stats(hourly["dates"], r, n, cost, "noise area, hourly checks, 2y")
            r, n = orb_days(hourly, 1)
            res[sym]["orb_hourly"] = stats(hourly["dates"], r, n, cost, "first-hour range breakout, 2y")
        if five is not None:
            r, lo, n, m = trend.noise_days(five, lookback=14, every=6, cost=0.0)
            res[sym]["noise_5m"] = stats(five["dates"], r, n, cost, "noise area, 30-min checks, 60d")
            for bars, name in ((1, "5-min"), (6, "30-min")):
                r, n = orb_days(five, bars)
                res[sym][f"orb_{name}"] = stats(five["dates"], r, n, cost, f"{name} range breakout, 60d")
    (ROOT / "strategies" / "quick" / "funds.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
