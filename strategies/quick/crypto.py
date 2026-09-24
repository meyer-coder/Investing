"""Is the intraday trend on MSTR and COIN really Bitcoin's?  The noise-area breakout on Bitcoin, US hours, 2017-2026.

    python strategies/quick/crypto.py

funds.py found the noise-area breakout (and a first-hour range breakout)
positive on MSTR, COIN and CONL over two years of hourly bars and the last
60 days of five-minute bars, while it lost on most funds.  Those names move
with Bitcoin, which trades around the clock and has years of one-minute bars
(Dukascopy's BTC/USD, indexes.py).  If Bitcoin's own moves during the US stock
session (09:30-16:00 New York, weekdays) trend the same way, year after year,
the MSTR/COIN result is an effect and not two lucky years.

The rule is trend.py's, unchanged: the band from the last 14 sessions,
checks every half hour, the VWAP exit, flat at 16:00; 3 bp a round trip (the
spot ETF or micro futures).  Also the first half hour predicting the last
(Gao et al.), and a check of how Bitcoin's US-hours move lines up with MSTR's
and COIN's own (hourly bars).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import assets                                                                # noqa: E402
import indexes                                                               # noqa: E402
import trend                                                                 # noqa: E402

COST_BP = 3.0


def main() -> int:
    D = indexes.load("BTCUSD")
    dates = list(D["dates"])
    print(f"Bitcoin, US hours: {len(dates)} weekday sessions {dates[0]} to {dates[-1]}")
    res = {}
    for label, kw in (("noise area", {}), ("noise area x1.5", {"band_mult": 1.5}), ("noise area, 0.5% stop", {"hard_stop": 0.005}),
                      ("noise area, checks every 15 min", {"every": 15})):
        r, lo, n, m = trend.noise_days(D, cost=COST_BP * 1e-4, **kw)
        yrs = {}
        for d, x in zip(dates, r):
            if not np.isnan(x):
                yrs.setdefault(d[:4], []).append(x)
        v = r[~np.isnan(r)]
        row = {"bp_per_day": round(float(v.mean() * 1e4), 2), "sharpe": round(float(v.mean() / v.std() * np.sqrt(252)), 2),
               "trades_per_day": round(float(np.nanmean(n)), 2),
               "years_bp": {y: round(float(np.mean(x) * 1e4), 1) for y, x in sorted(yrs.items())},
               "years_positive": int(sum(np.mean(x) > 0 for x in yrs.values())), "years": len(yrs),
               "usd_1x": round(float(v.mean() * 25_000), 1)}
        res[label] = row
        print(f"  {label:34s} {row['bp_per_day']:+6.2f} bp a day, Sharpe {row['sharpe']:+.2f}, {row['years_positive']}/{row['years']} years up, "
              f"$25k 1x ${row['usd_1x']:+.0f} | " + " ".join(f"{y[2:]}:{x:+.1f}" for y, x in row["years_bp"].items()), flush=True)
    r = assets.first_last(D, COST_BP)
    res["first half hour -> last"] = assets.stats(dates, r, "first half hour -> last half hour")
    # how closely MSTR's and COIN's open-to-close moves follow Bitcoin's over the same hours
    import datetime as dt
    import gap_volatile as gv
    btc = dict(zip(dates, D["C"][:, -1] / D["O"][:, 0] - 1.0))
    for sym in ("MSTR", "COIN", "IBIT"):
        d = gv.yahoo(sym, "1d", "3y")
        if not d:
            continue
        pairs = []
        for t, o, c in zip(d["t"], d["o"], d["c"]):
            day = dt.datetime.fromtimestamp(t, tz=gv.NY).strftime("%Y-%m-%d")
            if o and c and day in btc:
                pairs.append((btc[day], c / o - 1.0))
        a = np.array(pairs)
        if len(a) > 30:
            beta = float(np.polyfit(a[:, 0], a[:, 1], 1)[0])
            corr = float(np.corrcoef(a[:, 0], a[:, 1])[0, 1])
            res[f"{sym} vs Bitcoin, open to close"] = {"days": len(a), "correlation": round(corr, 2), "beta": round(beta, 2)}
            print(f"  {sym} open-to-close vs Bitcoin's 09:30-16:00 move: correlation {corr:.2f}, beta {beta:.2f} ({len(a)} days)")
    (ROOT / "strategies" / "quick" / "crypto.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
