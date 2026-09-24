"""The gap breakout entered on a pullback with a limit order instead of a stop order (it did not work).

    python strategies/quick/gap_retest.py

The gap breakout pays the spread twice on the day's widest spreads.  A limit
order resting at the breakout level after the first break would pay none
going in; it counts as filled only if the price trades back through the level
(by 0.5 or 2 bp) within 15, 30 or 60 minutes.  Exits: the stop pays a quarter
of the measured spread, the closing auction nothing; fees 0.5 bp and $0.007 a
share.  Result: the breakouts that come back to their level are the ones that
fail; it lost $72-76 a day from Sep 2024 at every setting.
"""
import itertools
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick")); sys.path.insert(0, str(ROOT / "strategies" / "scalp"))

import numpy as np, stock_orb as so, realistic
P = so.prepare()
O, H, L, C, dates, rng, fac = P["O"], P["H"], P["L"], P["C"], P["dates"], P["day_rng"], P["fac"]
names = P["names"]
sp = realistic.measured_spreads(names); spread_bp = np.array([sp.get(x, np.nan) for x in names])
nd = len(dates)
def run(gap_min=0.02, top=3, stop_atr=1.0, risk=0.02, window=30, through_bp=1.0, lev=4.0):
    pnl = np.full(nd, np.nan); ntr = np.zeros(nd)
    for i in range(15, nd):
        atr = rng[i - 14:i].mean(axis=0)
        gap = O[i, :, 0] / C[i - 1, :, -1] - 1.0
        first = np.sign(C[i, :, 4] - O[i, :, 0])
        ok = (np.abs(gap) >= gap_min) & (first != 0) & (atr > 0) & ~np.isnan(gap)
        cand = np.flatnonzero(ok)
        cand = cand[np.argsort(-np.abs(gap[cand]))][:top]
        day = 0.0
        for k in cand:
            h, l, c, o = H[i, k], L[i, k], C[i, k], O[i, k]
            side = int(first[k]); lvl = h[:5].max() if side > 0 else l[:5].min()
            brk = np.flatnonzero((h[5:389] >= lvl) if side > 0 else (l[5:389] <= lvl))
            if not len(brk): continue
            t_b = 5 + brk[0]
            # after the break, a resting limit at the level; filled only if price trades through it by through_bp
            thr = lvl * (1 - side * through_bp * 1e-4)
            seg = np.arange(t_b + 1, min(t_b + 1 + window, 389))
            hit = seg[(l[seg] <= thr) if side > 0 else (h[seg] >= thr)]
            if not len(hit): continue
            t0 = hit[0]; px = lvl
            stop = px - side * stop_atr * atr[k]
            out, why = c[389], "close"
            for u in range(t0, 390):
                if (side > 0 and l[u] <= stop) or (side < 0 and h[u] >= stop):
                    out = stop if u == t0 else (min(o[u], stop) if side > 0 else max(o[u], stop)); why = "stop"; break
            sh = min(risk * 25_000 / (stop_atr * atr[k]), lev * 25_000 / top / px)
            half = (spread_bp[k] / 2 if not np.isnan(spread_bp[k]) else 5.0) * 1e-4
            cost = sh * px * ((half / 2 if why == "stop" else 0.0) + 0.5e-4) + (sh / fac[i, k]) * 0.007
            day += side * sh * (out - px) - cost
            ntr[i] += 1
        pnl[i] = day
    return pnl, ntr
for window, thr in itertools.product((15, 30, 60), (0.5, 2.0)):
    pnl, ntr = run(window=window, through_bp=thr)
    so.summarize(dates, pnl, ntr, f"retest limit, {window} min, through {thr} bp")
