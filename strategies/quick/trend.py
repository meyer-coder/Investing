"""The index noise-area breakout, sized for a $25,000 account and for a Topstep 100K, with its worst moments.

    python strategies/quick/trend.py

index.py found one quick trade on the Nasdaq-100 that made money in every
year from 2020 to 2026: the noise-area breakout of Zarattini and Aziz (2023).
This file turns it into dollars and risk:

* per day, the closed P&L and the lowest the day's P&L went with the open
  position marked at each bar's worst price;
* sizing: a fixed multiple of the account, or the paper's volatility target
  (exposure = account x target daily move / the index's 14-day daily
  volatility, capped at the buying power);
* the $25,000 account traded through QQQ (up to 4x) or TQQQ (3x the index, so
  up to 12x), and a Topstep 100K traded with N MNQ, replayed through its
  $3,000 trailing loss limit and $2,000 daily limit from every fifth session;
* the same rule on the S&P 500, Russell 2000 and Dow (indexes.py), and a book
  that trades all four with the exposure split between them.

Dev is Sep 2020 to Dec 2023, test Jan 2024 to Sep 2026.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import index                                                                 # noqa: E402

SPLIT = index.SPLIT
ACCOUNT = 25_000.0
T = 390


def noise_days(D: dict, lookback: int = 14, every: int = 30, band_mult: float = 1.0, vwap_stop: bool = True,
               cost: float = 1e-4, start_check: int = 0, hard_stop: float = 0.0):
    """Per day: net return on the notional, the day's lowest running return (open trade marked at bar extremes),
    trades, and minutes in the market."""
    O, H, L, C, pc = D["O"], D["H"], D["L"], D["C"], D["pc"]
    nd, T = O.shape
    move = np.abs(C / O[:, :1] - 1.0)
    ret = np.full(nd, np.nan)
    low = np.full(nd, np.nan)
    ntr = np.zeros(nd)
    mins = np.zeros(nd)
    checks = [t for t in range(every - 1, T - 1, every) if t >= start_check]
    for i in range(lookback + 1, nd):
        sig = band_mult * move[i - lookback:i].mean(axis=0)
        o, h, l, c = O[i], H[i], L[i], C[i]
        up = max(o[0], pc[i]) * (1 + sig)
        dn = min(o[0], pc[i]) * (1 - sig)
        vwap = np.cumsum((h + l + c) / 3) / np.arange(1, T + 1)
        pos, px, t_in, total, worst, n, m = 0, 0.0, 0, 0.0, 0.0, 0, 0
        for t in checks:
            if pos and hard_stop:
                # a resting stop hard_stop away from the entry, watched every minute since the last look
                stop_px = px * (1 - pos * hard_stop)
                seg = np.arange(max(t_in, t - every + 1), t + 1)
                hit = seg[(l[seg] <= stop_px) if pos > 0 else (h[seg] >= stop_px)]
                if len(hit):
                    k = hit[0]
                    fill = min(o[k], stop_px) if pos > 0 else max(o[k], stop_px)
                    if k == t_in:
                        fill = stop_px
                    worst = min(worst, total + pos * (fill / px - 1.0) - cost / 2)
                    total += pos * (fill / px - 1.0) - cost
                    m += k + 1 - t_in
                    pos = 0
                    worst = min(worst, total)
                    continue
            if pos:
                seg_lo = l[t_in:t + 1].min() if pos > 0 else h[t_in:t + 1].max()
                worst = min(worst, total + pos * (seg_lo / px - 1.0) - cost / 2)
                out = c[t] < (max(up[t], vwap[t]) if vwap_stop else up[t]) if pos > 0 else \
                      c[t] > (min(dn[t], vwap[t]) if vwap_stop else dn[t])
                if out:
                    total += pos * (o[t + 1] / px - 1.0) - cost
                    m += t + 1 - t_in
                    pos = 0
                    worst = min(worst, total)
                    continue                                                  # re-entry waits for the next check
            if pos == 0:
                side = 1 if c[t] > up[t] else (-1 if c[t] < dn[t] else 0)
                if side:
                    pos, px, t_in = side, o[t + 1], t + 1
                    n += 1
        if pos and hard_stop:
            stop_px = px * (1 - pos * hard_stop)
            seg = np.arange(max(t_in, checks[-1] + 1 if checks else t_in), T)
            hit = seg[(l[seg] <= stop_px) if pos > 0 else (h[seg] >= stop_px)]
            if len(hit):
                k = hit[0]
                fill = stop_px if k == t_in else (min(o[k], stop_px) if pos > 0 else max(o[k], stop_px))
                worst = min(worst, total + pos * (fill / px - 1.0) - cost / 2)
                total += pos * (fill / px - 1.0) - cost
                m += k + 1 - t_in
                pos = 0
        if pos:
            seg_lo = l[t_in:].min() if pos > 0 else h[t_in:].max()
            worst = min(worst, total + pos * (seg_lo / px - 1.0) - cost / 2)
            total += pos * (c[T - 1] / px - 1.0) - cost
            m += T - t_in
        ret[i], low[i], ntr[i], mins[i] = total, min(worst, total), n, m
    return ret, low, ntr, mins


def daily_vol(D: dict, lookback: int = 14) -> np.ndarray:
    r = D["C"][:, -1] / D["pc"] - 1.0
    out = np.full(len(r), np.nan)
    for i in range(lookback + 1, len(r)):
        out[i] = np.nanstd(r[i - lookback:i])
    return out


def exposure(D: dict, account: float, max_lev: float, target: Optional[float] = None) -> np.ndarray:
    """Dollars of index exposure per day: fixed, or the volatility target capped at the buying power."""
    if target is None:
        return np.full(len(D["O"]), account * max_lev)
    return np.minimum(account * max_lev, account * target / daily_vol(D))


def account_stats(dates, usd, low_usd, account=ACCOUNT, label=""):
    ds = np.array(dates)
    ok = ~np.isnan(usd)
    ds, v, lo = ds[ok], usd[ok], low_usd[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean()), 0) for y in sorted({x[:4] for x in ds})}
    row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
           "test_up": round(float((v[test] > 0).mean()), 3), "days_200_test": round(float((v[test] >= 200).mean()), 3),
           "worst_day": round(float(v.min()), 0), "worst_intraday": round(float(lo.min()), 0),
           "max_drawdown": round(dd, 0), "max_drawdown_pct_of_account": round(-dd / account * 100, 1),
           "sharpe_test": round(float(v[test].mean() / (v[test].std() + 1e-9) * np.sqrt(252)), 2),
           "sharpe_all": round(float(v.mean() / (v.std() + 1e-9) * np.sqrt(252)), 2), "years": years}
    if label:
        print(f"  {label:50s} ${row['dev_usd']:+6.0f}/${row['test_usd']:+6.0f} a day | up {row['test_up']:.0%} $200+ {row['days_200_test']:.0%} | "
              f"worst day ${row['worst_day']:+.0f} (intraday ${row['worst_intraday']:+.0f}) | max dd ${row['max_drawdown']:+.0f} "
              f"({row['max_drawdown_pct_of_account']:.0f}% of account) | Sharpe {row['sharpe_all']:+.2f} | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()), flush=True)
    return row


def topstep(dates, pnl_usd, low_usd, max_loss=3000.0, daily_loss=2000.0, target=6000.0, every=5):
    """Fresh combines from every fifth session: share passed, breached, still open after the data ends."""
    ds = list(dates)
    ok = [i for i in range(len(ds)) if not np.isnan(pnl_usd[i])]
    out = {"pass": 0, "breach": 0, "open": 0, "days_to_pass": []}
    for s in ok[::every]:
        bal, peak, floor, best = 0.0, 0.0, -max_loss, 0.0
        res = "open"
        for n, i in enumerate([j for j in ok if j >= s], 1):
            day, lo = pnl_usd[i], low_usd[i]
            if daily_loss and lo <= -daily_loss:                              # the daily limit closes the day there
                lo = day = -daily_loss
            if bal + lo <= floor:
                res = "breach"
                break
            bal += day
            best = max(best, day)
            peak = max(peak, bal)
            floor = min(0.0, max(floor, peak - max_loss))
            if bal >= target and best <= 0.5 * bal:
                res = "pass"
                out["days_to_pass"].append(n)
                break
        out[res] += 1
    tot = max(1, out["pass"] + out["breach"] + out["open"])
    return {"pass": round(out["pass"] / tot, 3), "breach": round(out["breach"] / tot, 3), "open": round(out["open"] / tot, 3),
            "median_days_to_pass": float(np.median(out["days_to_pass"])) if out["days_to_pass"] else None}


def main() -> int:
    D = index.load()
    dates = list(D["dates"])
    level = 29_000.0                                                           # today's Nasdaq-100 level for MNQ dollars
    res: Dict[str, dict] = {}
    print("Nasdaq-100 noise-area breakout (lookback 14, checks every 30 minutes, VWAP exit); dollars a day, dev / test")
    variants = {"base": dict(), "band x1.5": dict(band_mult=1.5), "from 10:30": dict(start_check=59),
                "band exit only": dict(vwap_stop=False), "lookback 20": dict(lookback=20)}
    for vname, kw in variants.items():
        r, lo, n, m = noise_days(D, **kw)
        print(f"-- {vname}: {np.nanmean(n):.2f} trades a day, {np.nanmean(m):.0f} minutes in the market, "
              f"{np.nanmean(r) * 1e4:+.2f} bp a day, daily sd {np.nanstd(r) * 1e4:.0f} bp")
        for inst, mult, levs in (("QQQ", 1, (1, 2, 4)), ("TQQQ", 3, (1, 2, 4))):
            for lev in levs:
                ex = exposure(D, ACCOUNT, lev) * mult
                res[f"{vname} | {inst} {lev}x"] = account_stats(dates, r * ex, lo * ex, label=f"{vname} | $25k in {inst} at {lev}x")
        for tv in (0.01, 0.02):
            ex = exposure(D, ACCOUNT, 4, tv) * 3
            res[f"{vname} | TQQQ vol target {tv:.0%}"] = account_stats(dates, r * ex, lo * ex,
                                                                     label=f"{vname} | $25k in TQQQ, vol target {tv:.0%} (max 4x)")
        for mnq in (2, 5, 10, 20):
            ex = np.full(len(r), mnq * 2.0 * level)
            usd, lusd = r * ex, lo * ex
            st = account_stats(dates, usd, lusd, account=3000.0, label=f"{vname} | {mnq} MNQ")
            st["topstep_100k"] = topstep(dates, usd, lusd)
            print(f"      Topstep 100K with {mnq} MNQ: pass {st['topstep_100k']['pass']:.0%}, breach {st['topstep_100k']['breach']:.0%}, "
                  f"still open {st['topstep_100k']['open']:.0%}, median {st['topstep_100k']['median_days_to_pass']} sessions to pass")
            res[f"{vname} | {mnq} MNQ"] = st
    (ROOT / "strategies" / "quick" / "trend.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
