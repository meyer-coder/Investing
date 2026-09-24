"""Opening-range breakouts on the day's stocks in play (Zarattini, Barbon and Aziz, 2024), on four years of minutes.

    python strategies/quick/stock_orb.py

The published rule: each morning take the stocks trading far more than usual
in the first five minutes, trade only in the direction of that first
five-minute bar, buy a break of its high (sell a break of its low), stop at a
tenth of the stock's 14-day average daily range, and hold to the close.  Size
each trade to lose 1% of the account at its stop, with at most 4x buying power
in all.

The panel has no volume, so "in play" here is the first five minutes' range
against its own 14-day average (relative range), plus the opening gap.  The
72 large caps of the mid-price panel (bid and offer averaged,
strategies/scalp/panel.py), Sep 2022 to Sep 2026; dev to Aug 2024, test after.
Each share pays a cent of spread and $0.007 of commission for the round
trip, on the price actually paid (split factors), and the stop fills at the
stop or at a worse open.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402
import splits                                                                # noqa: E402

SPLIT = "2024-09-01"
ACCOUNT = 25_000.0
PER_SHARE = 0.017                                                            # a cent of spread + $0.0035 a side
_P: dict = {}


def prepare():
    cube, dates, names = panel.load_panel("mid")
    O, H, L, C = (cube[..., j].astype(np.float64) for j in range(4))
    day_rng = H.max(axis=2) - L.min(axis=2)                                   # (days, names) daily range in price
    fac = splits.matrix(dates, names)
    return {"O": O, "H": H, "L": L, "C": C, "dates": dates, "names": names, "day_rng": day_rng, "fac": fac}


def run(P, minutes=5, top=10, rr_min=1.0, stop_atr=0.10, risk=0.01, lev=4.0, gap_min=0.0, first_bar=True,
        exit_at=389, target_r=None, spread_bp=None):
    """Per-day dollars on $25,000 and trade counts.  With `spread_bp` (per name, measured), each trade pays
    that spread plus 2 bp of its notional for the round trip instead of a cent and $0.007 a share."""
    O, H, L, C, dates, rng, fac = P["O"], P["H"], P["L"], P["C"], P["dates"], P["day_rng"], P["fac"]
    nd, nn, T = O.shape
    or_hi = H[:, :, :minutes].max(axis=2)
    or_lo = L[:, :, :minutes].min(axis=2)
    or_rng = (or_hi - or_lo) / O[:, :, 0]
    pnl = np.full(nd, np.nan)
    ntr = np.zeros(nd)
    for i in range(15, nd):
        past = or_rng[i - 14:i].mean(axis=0)
        rr = or_rng[i] / np.where(past > 0, past, np.nan)
        atr = rng[i - 14:i].mean(axis=0)
        gap = O[i, :, 0] / C[i - 1, :, -1] - 1.0
        first = np.sign(C[i, :, minutes - 1] - O[i, :, 0])
        ok = (rr >= rr_min) & (np.abs(gap) >= gap_min) & ~np.isnan(rr) & (atr > 0)
        if first_bar:
            ok &= first != 0
        cand = np.flatnonzero(ok)
        if not len(cand):
            pnl[i] = 0.0
            continue
        cand = cand[np.argsort(-rr[cand])][:top]
        day = 0.0
        budget = lev * ACCOUNT
        per_cap = budget / top
        for k in cand:
            h, l, c, o = H[i, k], L[i, k], C[i, k], O[i, k]
            sides = [first[k]] if first_bar else [1, -1]
            best = None
            for side in sides:
                lvl = or_hi[i, k] if side > 0 else or_lo[i, k]
                hit = np.flatnonzero((h[minutes:exit_at] >= lvl) if side > 0 else (l[minutes:exit_at] <= lvl))
                if len(hit):
                    t = minutes + hit[0]
                    if best is None or t < best[1]:
                        best = (side, t, lvl)
            if best is None:
                continue
            side, t, lvl = best
            px_in = max(o[t], lvl) if side > 0 else min(o[t], lvl)
            stop = px_in - side * stop_atr * atr[k]
            tgt = px_in + side * target_r * stop_atr * atr[k] if target_r else None
            px_out = c[exit_at]
            for u in range(t, exit_at + 1):
                if (side > 0 and l[u] <= stop) or (side < 0 and h[u] >= stop):
                    px_out = (min(o[u], stop) if side > 0 else max(o[u], stop)) if u > t else stop
                    break
                if tgt is not None and ((side > 0 and h[u] >= tgt) or (side < 0 and l[u] <= tgt)):
                    px_out = (max(o[u], tgt) if side > 0 else min(o[u], tgt)) if u > t else tgt
                    break
            shares_risk = risk * ACCOUNT / (stop_atr * atr[k])
            shares = min(shares_risk, per_cap / px_in)
            paid = px_in * fac[i, k]                                             # the real share price
            real_shares = shares / fac[i, k]                                     # adjusted shares -> real shares
            if spread_bp is not None and not np.isnan(spread_bp[k]):
                cost = shares * px_in * (spread_bp[k] + 2.0) * 1e-4
            else:
                cost = real_shares * PER_SHARE
            day += side * shares * (px_out - px_in) - cost
            ntr[i] += 1
        pnl[i] = day
    return pnl, ntr


def summarize(dates, pnl, ntr, label=""):
    ok = ~np.isnan(pnl)
    ds, v, n = np.array(dates)[ok], pnl[ok], ntr[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean()), 1) for y in sorted({x[:4] for x in ds})}
    row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
           "test_up": round(float((v[test] > 0).mean()), 3), "trades_per_day": round(float(n.mean()), 2),
           "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0),
           "sharpe_dev": round(float(v[dev].mean() / (v[dev].std() + 1e-9) * np.sqrt(252)), 2),
           "sharpe_test": round(float(v[test].mean() / (v[test].std() + 1e-9) * np.sqrt(252)), 2),
           "days_200_test": round(float((v[test] >= 200).mean()), 3), "years": years}
    if label:
        print(f"  {label:62s} ${row['dev_usd']:+6.1f}/${row['test_usd']:+6.1f} a day | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} "
              f"| worst ${row['worst_day']:+.0f} dd ${row['max_drawdown']:+.0f} | {row['trades_per_day']:.1f} tr/d | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()), flush=True)
    return row


def _job(args):
    label, kw = args
    pnl, ntr = run(_P, **kw)
    return label, pnl, ntr


def main() -> int:
    import multiprocessing as mp
    _P.update(prepare())
    dates = _P["dates"]
    print(f"{len(dates)} sessions, {len(_P['names'])} names; dollars a day on $25,000 (1% risk a trade, 4x cap)")
    jobs = []
    for minutes, top, rr, sa, fb in itertools.product((5, 15, 30), (5, 10, 20), (1.0, 1.5, 2.0), (0.05, 0.1, 0.2, 0.5), (True, False)):
        jobs.append((f"ORB {minutes}m top {top} rr>{rr} stop {sa} ATR {'first-bar side' if fb else 'either side'}",
                     dict(minutes=minutes, top=top, rr_min=rr, stop_atr=sa, first_bar=fb)))
    with mp.get_context("fork").Pool(4) as pool:
        out = pool.map(_job, jobs, chunksize=4)
    res = {}
    for label, pnl, ntr in out:
        res[label] = summarize(dates, pnl, ntr)
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print("best by the weaker of dev and test:")
    for k_, v in ranked[:20]:
        print(f"  {k_:62s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} | Sharpe {v['sharpe_dev']:+.2f}/{v['sharpe_test']:+.2f} | worst ${v['worst_day']:+.0f} "
              f"dd ${v['max_drawdown']:+.0f} | {v['trades_per_day']:.1f} tr/d | $200+ days {v['days_200_test']:.0%} | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in v["years"].items()))
    (ROOT / "strategies" / "quick" / "stock_orb.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
