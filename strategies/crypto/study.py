"""Can AAVE, BNB, BTC, INJ and MSTR be traded at a profit?  Daily bars, 2017 (or the coin's start) to
September 2026.

    python strategies/crypto/study.py

For each of the five:

* holding it;
* simple rules that have been tested on crypto for years, each with one
  setting and its neighbours shown so no one number is picked after the fact:
  - trend: in while the close is above its N-day average (N = 20, 50, 100,
    200), out below it;
  - breakout: in on a close above the highest close of the last 20 (or 55)
    days, out on a close under the lowest of the last 10 (or 20);
  - dip: in after a 3-day drop of 10% or more while above the 100-day
    average, out after 5 days or 8% up;
* our four leveraged-fund rules unchanged (D609, CB51, CBE3, FBB5), through
  evotrader's engine.

Signals on the close (00:00 UTC for the coins), fills at the next open, the
whole $25,000 in the one asset (no leverage: these already move like 2x-4x
funds).  Costs 10 bp a side for the coins (a spot taker fee) and 2 bp for
MSTR.  Dollars a day on $25,000 (mean daily return x $25,000), Sharpe, the
deepest fall of the account, the worst losing stretch in dollars, the years.

Then every rule on 29 coins (SHIB left out: Yahoo prices it at zero) against random timing, as in
strategies/top5/rigor.py: on each coin as many trades as the rule made there,
with its own holding times, entered on random days, 500 times.  And a book
with the five side by side, $5,000 each under the 50-day trend rule, for
variety next to the Micron bots.  Written to strategies/crypto/study.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "top5"))
import common as C                                                           # noqa: E402

START = "2017-01-01"
LAST3 = "2023-09-22"
FIVE = ["BTC-USD", "BNB-USD", "AAVE-USD", "INJ-USD", "MSTR"]
WIDE = ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
        "LTC-USD", "BCH-USD", "UNI7083-USD", "ATOM-USD", "NEAR-USD", "FIL-USD", "ALGO-USD", "XLM-USD", "TRX-USD", "ETC-USD",
        "XMR-USD", "HBAR-USD", "ICP-USD", "APT21794-USD", "ARB11841-USD", "OP-USD", "SUI20947-USD", "AAVE-USD",
        "INJ-USD"]
LEV = {"D609": "02", "CB51": "25", "CBE3": "18", "FBB5": "09"}


def clean_cache(sym: str) -> int:
    """Drop a coin's leading bars that are not real prices: a zero open or close, or a first print more than
    ten times away from the next (AAVE's first Yahoo bar closes at $0.52, the next at $53).  SHIB is left out
    altogether: Yahoo rounds its price to zero for hundreds of days."""
    from evotrader.data import _read_cache, _write_cache
    b = _read_cache(sym)
    if b is None:
        return 0
    o, c = np.asarray(b.open, float), np.asarray(b.close, float)
    k = 0
    while k + 1 < len(c) and (o[k] <= 0 or c[k] <= 0 or not (0.1 < c[k + 1] / c[k] < 10)):
        k += 1
    if k:
        _write_cache(b.index_slice(k, len(b)))
    return k


def cost_bp(sym: str) -> float:
    return 2.0 if not sym.endswith("-USD") else 10.0


def bars(sym: str):
    u, _ = C.market([sym], data_start="2014-01-01")
    b = u.bars[sym]
    return list(b.dates), np.asarray(b.open, float), np.asarray(b.high, float), np.asarray(b.low, float), np.asarray(b.close, float)


# ------------------------------------------------------------------ simple rules: a position (0 or 1) decided on each close

def sma(x, n):
    out = np.full(len(x), np.nan)
    c = np.cumsum(np.insert(x, 0, 0.0))
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def trend(c, n):
    m = sma(c, n)
    return np.where(np.isnan(m), 0, (c > m).astype(float))


def breakout(c, n_in, n_out):
    pos = np.zeros(len(c))
    for t in range(max(n_in, n_out), len(c)):
        hi, lo = c[t - n_in:t].max(), c[t - n_out:t].min()
        prev = pos[t - 1]
        pos[t] = 1.0 if (prev == 0 and c[t] > hi) else (0.0 if (prev == 1 and c[t] < lo) else prev)
    return pos


def dip(c, drop=0.10, days=3, trend_n=100, hold=5, target=0.08):
    m = sma(c, trend_n)
    pos = np.zeros(len(c))
    t_in = -1
    for t in range(max(days, trend_n), len(c)):
        if pos[t - 1] == 1:
            held = t - t_in
            pos[t] = 0.0 if (held >= hold or c[t] / c[t_in] - 1 >= target) else 1.0
        elif c[t] / c[t - days] - 1 <= -drop and c[t] > m[t]:
            pos[t], t_in = 1.0, t
    return pos


def run_positions(sym, dates, o, pos):
    """Position decided on close t, held from open t+1 to open t+2; costs on each change.  Returns the daily
    returns (dated t+1) and the trades (symbol, entry date, exit date, return, days held)."""
    k = cost_bp(sym) * 1e-4
    n = len(o)
    r = np.zeros(n)
    for t in range(n - 2):
        r[t + 1] = pos[t] * (o[t + 2] / o[t + 1] - 1.0) - k * abs(pos[t] - (pos[t - 1] if t > 0 else 0.0))
    trades, t_in = [], None
    for t in range(n - 1):
        prev = pos[t - 1] if t > 0 else 0.0
        if pos[t] == 1 and prev == 0:
            t_in = t + 1
        elif pos[t] == 0 and prev == 1 and t_in is not None:
            trades.append((sym, dates[t_in], dates[t + 1], o[t + 1] / o[t_in] - 1.0 - 2 * k, t + 1 - t_in))
            t_in = None
    return r, trades


def window(dates, r, a=START, b="9999"):
    ds = np.array(dates)
    m = (ds >= a) & (ds <= b)
    return ds[m], r[m]


def summary(dates, r) -> dict:
    ds, v = window(dates, r)
    ds = ds[np.cumsum(np.abs(v)) > 0] if np.any(v) else ds                   # from the first live day
    v = v[-len(ds):]
    st = C.day_stats(v)
    eq = np.cumprod(1 + v)
    st["max_fall_pct"] = round(float((eq / np.maximum.accumulate(eq) - 1).min() * 100), 0)
    st["from"] = str(ds[0]) if len(ds) else None
    yrs = {}
    for d, x in zip(ds, v):
        yrs.setdefault(d[:4], []).append(x * C.ACCOUNT)
    st["years"] = {y: round(float(np.mean(x)), 0) for y, x in sorted(yrs.items())}
    l3 = v[ds >= LAST3]
    st["last3_usd"] = round(float(l3.mean() * C.ACCOUNT), 1) if l3.size else None
    return st


RULES = {"trend 20": lambda c: trend(c, 20), "trend 50": lambda c: trend(c, 50), "trend 100": lambda c: trend(c, 100),
         "trend 200": lambda c: trend(c, 200), "breakout 20/10": lambda c: breakout(c, 20, 10),
         "breakout 55/20": lambda c: breakout(c, 55, 20), "dip 10% in 3 days": lambda c: dip(c)}


def random_log_means(trades, rng, n, cost, start):
    """rigor.random_means on log returns: crypto trades run from -90% to +10,000%, and a plain mean is one
    coin's one trade."""
    by = {}
    for t in trades:
        by.setdefault(t[0], []).append(t)
    sums, count = np.zeros(n), 0
    for sym, ts in by.items():
        dates, o, h, lo_, c = bars(sym)
        first = max(C.first_on_or_after(dates, start), 252)
        holds = np.array([max(int(t[4]), 1) for t in ts])
        hi = len(o) - 1
        starts = rng.integers(first, np.maximum(hi - holds, first + 1), size=(n, len(ts)))
        ends = np.minimum(starts + holds[None, :], hi)
        sums += np.log(o[ends] / o[starts] * (1 - cost * 1e-4) ** 2).sum(axis=1)
        count += len(ts)
    return sums / max(count, 1)


def main() -> int:
    for sym in set(FIVE + WIDE):
        k = clean_cache(sym)
        if k:
            print(f"{sym}: dropped {k} leading bar(s) that are not real prices")
    out = {"five": {}, "wide": {}}
    genomes = {k: json.loads(next((ROOT / "profitable-strategies" / "leveraged-etfs").glob(f"{v}_*.json")).read_text())["genome"]
               for k, v in LEV.items()}
    series = {}
    # ---- the five
    for sym in FIVE:
        dates, o, h, lo_, c = bars(sym)
        rows = {"hold": summary(dates, np.concatenate([[0.0], o[2:] / o[1:-1] - 1.0, [0.0]])[:len(o)])}
        for name, f in RULES.items():
            r, trades = run_positions(sym, dates, o, f(c))
            rows[name] = {**summary(dates, r), "trades": len([t for t in trades if t[1] >= START])}
            if name == "trend 50":
                series[sym] = dict(zip(dates, r))
        for name, g in genomes.items():
            res = C.backtest(g, [sym], start=START, slippage=cost_bp(sym), data_start="2014-01-01")
            d2, r2 = C.daily_returns(res, START, C.END)
            rows[name] = {**summary(d2, r2), "trades": len(res.journal.trades)}
        out["five"][sym] = rows
        print(f"\n{sym}  (from {rows['hold']['from']})")
        print(f"  {'rule':20s} {'$/day':>7} {'3 yrs':>7} {'Sharpe':>6} {'deepest fall':>12} {'worst stretch':>13} {'trades':>6}  years")
        for name, st in rows.items():
            print(f"  {name:20s} {st['usd_per_day']:+7.1f} {st['last3_usd'] or 0:+7.1f} {st['sharpe']:+6.2f} {st['max_fall_pct']:+11.0f}% "
                  f"{st['worst_stretch']:+13,.0f} {st.get('trades', '-'):>6}  " + " ".join(f"{y[2:]}:{v:+.0f}" for y, v in st["years"].items()),
                  flush=True)
    # ---- every rule on the wide set of coins, against random timing
    rng = np.random.default_rng(30)
    print(f"\nthe rules on {len(WIDE)} coins from {START}: per trade (log returns), random entries with the same holds, "
          f"edge, p, coins profitable, coins with a better Sharpe than holding")
    for name in list(RULES) + list(genomes):
        trades, usd, better = [], [], []
        for sym in WIDE:
            try:
                dates, o, h, lo_, c = bars(sym)
            except Exception:
                continue
            hold = summary(dates, np.concatenate([[0.0], o[2:] / o[1:-1] - 1.0, [0.0]])[:len(o)])
            if name in RULES:
                r, tr = run_positions(sym, dates, o, RULES[name](c))
                st = summary(dates, r)
                tr = [t for t in tr if t[1] >= START]
            else:
                res = C.backtest(genomes[name], [sym], start=START, slippage=cost_bp(sym), data_start="2014-01-01")
                d2, r2 = C.daily_returns(res, START, C.END)
                st = summary(d2, r2)
                tr = [(t.symbol, t.entry_date, t.exit_date, t.ret, t.bars_held) for t in res.journal.trades]
            trades += tr
            usd.append(st["usd_per_day"])
            better.append(st["sharpe"] > hold["sharpe"])
        rets = np.array([t[3] for t in trades])
        logs = np.log1p(np.maximum(rets, -0.999))
        rnd = random_log_means(trades, rng, 500, 10.0, START)
        row = {**C.trade_stats(rets), "mean_log_bp": round(float(logs.mean() * 1e4), 1),
               "random_mean_log_bp": round(float(rnd.mean() * 1e4), 1),
               "timing_edge_log_bp": round(float((logs.mean() - rnd.mean()) * 1e4), 1),
               "p_value_vs_random": round(float((rnd >= logs.mean()).mean()), 3),
               "coins_profitable": round(float(np.mean([u > 0 for u in usd])), 2),
               "coins_better_sharpe_than_holding": round(float(np.mean(better)), 2)}
        out["wide"][name] = row
        print(f"  {name:20s} {row['trades']:6,d} trades, median {row['median_bp']:+7.1f} bp, mean log {row['mean_log_bp']:+7.1f} bp, "
              f"random {row['random_mean_log_bp']:+7.1f} bp, edge {row['timing_edge_log_bp']:+6.1f} bp, p = {row['p_value_vs_random']:.3f}; "
              f"profitable on {row['coins_profitable']:.0%}, "
              f"better Sharpe than holding on {row['coins_better_sharpe_than_holding']:.0%}", flush=True)
    # ---- the five side by side under the 50-day trend, $5,000 each
    days = sorted(set().union(*[set(s) for s in series.values()]))
    days = [d for d in days if d >= "2021-01-01"]                            # when all five trade
    v = np.array([sum(series[s].get(d, 0.0) for s in series) / len(series) for d in days])
    out["book_trend50"] = {**summary(days, v), "note": "$5,000 in each of the five under the 50-day trend rule"}
    b = out["book_trend50"]
    print(f"\nthe five together, trend 50, $5,000 each, from 2021: ${b['usd_per_day']:+.1f} a day, 3 yrs ${b['last3_usd']:+.1f}, "
          f"Sharpe {b['sharpe']:+.2f}, deepest fall {b['max_fall_pct']:+.0f}%, worst stretch ${b['worst_stretch']:+,.0f} | "
          + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in b["years"].items()))
    (ROOT / "strategies" / "crypto" / "study.json").write_text(json.dumps(out, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
