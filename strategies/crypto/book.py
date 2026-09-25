"""A crypto book the owner can trade on Robinhood, sized for $150 a day, that cannot lose the whole account.

    python strategies/crypto/book.py

study.py found that trend and breakout rules beat random timing on 29
coins, and brackets.py that leverage and capped targets ruin them.  This
builds the book from those rules and asks what $150 a day would take.

* Coins: the 24 of study.py's 29 that Robinhood lists as tradable
  (get_currency_pairs, 2026-09-25).  A coin joins the book once it has a
  year of prices.
* Rules on each coin, from study.py: in while the close is above its 20,
  50 or 100-day average, or the 20/10 and 55/20-day breakouts.  Signals on
  the close (00:00 UTC), fills at the next open, 10 bp a side.
* Weights: equal across the coins in the book, or by the inverse of each
  coin's 60-day volatility.  Never more than the account: no leverage, so
  the most it can lose is what is in it.
* Brakes, each tried on and off:
  - Bitcoin's regime: hold nothing while Bitcoin closes below its 200-day
    average;
  - a drawdown brake: half size while the book is more than 25% below its
    best.
* The setting is chosen on 2017-2020 (the best Sharpe) and shown on
  2021-2026.  Dollars a day are the mean daily return times the account;
  the account needed for $150 a day follows from that.  The deepest fall
  is of the compounded account.

Written to book.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study as S                                                            # noqa: E402

#: study.py's coins that Robinhood lists as tradable (get_currency_pairs, 2026-09-25)
COINS = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
         "LTC-USD", "BCH-USD", "UNI7083-USD", "ATOM-USD", "NEAR-USD", "ALGO-USD", "XLM-USD", "ETC-USD", "HBAR-USD",
         "ARB11841-USD", "OP-USD", "SUI20947-USD", "AAVE-USD", "INJ-USD"]
RULES = {"trend 20": lambda c: S.trend(c, 20), "trend 50": lambda c: S.trend(c, 50), "trend 100": lambda c: S.trend(c, 100),
         "breakout 20/10": lambda c: S.breakout(c, 20, 10), "breakout 55/20": lambda c: S.breakout(c, 55, 20)}
SPLIT, TARGET, ACCOUNT = "2021-01-01", 150.0, 25_000.0
COST = 10e-4


def panel():
    """Every coin on one calendar of dates: open prices, closes, and whether it has a year of history."""
    data = {}
    for sym in COINS:
        try:
            dates, o, h, lo, c = S.bars(sym)
        except Exception as e:
            print(f"  {sym}: {str(e)[:60]}")
            continue
        data[sym] = (dates, o, c)
    cal = sorted({d for v in data.values() for d in v[0] if d >= "2016-01-01"})
    ix = {d: i for i, d in enumerate(cal)}
    n, k = len(cal), len(data)
    O, C = np.full((n, k), np.nan), np.full((n, k), np.nan)
    for j, (sym, (dates, o, c)) in enumerate(data.items()):
        for d, oo, cc in zip(dates, o, c):
            if d in ix:
                O[ix[d], j], C[ix[d], j] = oo, cc
    for A in (O, C):                                                           # the odd missing day: carry forward
        for j in range(k):
            col = A[:, j]
            first = np.flatnonzero(~np.isnan(col))
            if first.size:
                for t in range(first[0] + 1, n):
                    if np.isnan(col[t]):
                        col[t] = col[t - 1]
    return cal, list(data), O, C


def positions(C: np.ndarray, rule) -> np.ndarray:
    P = np.zeros_like(C)
    for j in range(C.shape[1]):
        col = C[:, j]
        ok = ~np.isnan(col)
        if ok.sum() < 400:
            continue
        s = np.flatnonzero(ok)[0]
        p = rule(col[s:])
        p[:365] = 0.0                                                          # a year of history before it trades
        P[s:, j] = p
    return P


def book(cal, O, C, P, weights: str, btc_regime: bool, brake: bool, btc_col: int) -> np.ndarray:
    """Daily returns of the account: position on close t, held from open t+1 to open t+2."""
    n, k = O.shape
    live = ~np.isnan(C)
    age = np.cumsum(live, axis=0)
    member = live & (age > 365)
    ret = np.zeros((n, k))
    ret[1:-1] = np.where(member[:-2], O[2:] / O[1:-1] - 1.0, 0.0)             # open t+1 -> open t+2, dated t+1
    ret = np.nan_to_num(ret)
    vol = np.full((n, k), np.nan)
    lr = np.vstack([np.zeros((1, k)), np.diff(np.log(C), axis=0)])
    for t in range(60, n):
        vol[t] = np.nanstd(lr[t - 60:t], axis=0)
    btc_ok = np.ones(n, bool)
    if btc_regime:
        b = C[:, btc_col]
        m = S.sma(np.nan_to_num(b, nan=np.nanmean(b)), 200)
        btc_ok = ~np.isnan(m) & (b > m)
    r = np.zeros(n)
    w_prev = np.zeros(k)
    eq, peak = 1.0, 1.0
    for t in range(1, n - 1):
        s = t - 1                                                              # the close the positions come from
        m = member[s]
        if not m.any():
            continue
        if weights == "equal":
            w = np.where(m, 1.0 / m.sum(), 0.0)
        else:
            iv = np.where(m & (vol[s] > 0), 1.0 / np.where(vol[s] > 0, vol[s], 1.0), 0.0)
            w = iv / iv.sum() if iv.sum() > 0 else np.zeros(k)
        w = w * P[s] * (1.0 if btc_ok[s] else 0.0)
        if brake and eq < 0.75 * peak:
            w = w * 0.5
        r[t] = float(w @ ret[t]) - COST * float(np.abs(w - w_prev).sum())
        w_prev = w
        eq *= 1 + r[t]
        peak = max(peak, eq)
    return r


def stats(cal, r, a="2017-01-01", b="9999") -> dict:
    ds = np.array(cal)
    x = r[(ds >= a) & (ds < b)]
    eq = np.cumprod(1 + x)
    fall = float((eq / np.maximum.accumulate(eq) - 1).min())
    usd = x * ACCOUNT
    cum = np.cumsum(usd)
    stretch = float((cum - np.maximum.accumulate(np.r_[0.0, cum])[1:]).min())
    mean = float(x.mean())
    years = {}
    for d, v in zip(ds[(ds >= a) & (ds < b)], x):
        years.setdefault(d[:4], []).append(v)
    return {"usd_per_day": round(mean * ACCOUNT, 1), "sharpe": round(float(mean / (x.std() + 1e-12) * np.sqrt(365)), 2),
            "deepest_fall_pct": round(fall * 100, 1), "worst_day_pct": round(float(x.min()) * 100, 1),
            "worst_stretch_usd": round(stretch, 0), "in_market": round(float((x != 0).mean()), 2),
            "account_for_150": round(TARGET / mean, -3) if mean > 0 else None,
            "years_usd_per_day": {y: round(float(np.mean(v)) * ACCOUNT, 1) for y, v in sorted(years.items())}}


def main() -> int:
    for sym in COINS:                                                          # fetch, then drop bad first prints
        try:
            S.bars(sym)
        except Exception:
            continue
        if S.clean_cache(sym):
            S.C._markets.clear()
    cal, syms, O, C = panel()
    btc = syms.index("BTC-USD")
    print(f"{len(syms)} coins, {cal[0]} to {cal[-1]}")
    out = {}
    for rule, weights, regime, brake in itertools.product(RULES, ("equal", "inverse vol"), (False, True), (False, True)):
        P = positions(C, RULES[rule])
        r = book(cal, O, C, P, weights, regime, brake, btc)
        name = f"{rule}, {weights}" + (", BTC above its 200-day" if regime else "") + (", half size 25% down" if brake else "")
        out[name] = {"2017-2020": stats(cal, r, "2017-01-01", SPLIT), "2021-2026": stats(cal, r, SPLIT), "all": stats(cal, r)}
        d, t = out[name]["2017-2020"], out[name]["2021-2026"]
        print(f"{name:60s} 17-20 ${d['usd_per_day']:+6.1f} Sh {d['sharpe']:.2f} fall {d['deepest_fall_pct']:+.0f}% | "
              f"21-26 ${t['usd_per_day']:+6.1f} Sh {t['sharpe']:.2f} fall {t['deepest_fall_pct']:+.0f}% "
              f"stretch ${t['worst_stretch_usd']:,.0f}; $150/day needs ${t['account_for_150'] or 0:,.0f}", flush=True)
    pick = max(out, key=lambda k: out[k]["2017-2020"]["sharpe"])
    out["_picked_on_2017_2020"] = pick
    print(f"\npicked on 2017-2020 by Sharpe: {pick}")
    print(json.dumps(out[pick], indent=1))
    (HERE / "book.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
