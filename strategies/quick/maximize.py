"""Push the quick-trade book's daily dollars as high as they go, and show what each step costs in risk.

    python strategies/quick/maximize.py

The legs that held up (each a daily return per unit of exposure, net of costs):

* ndx   - the Nasdaq-100 noise-area breakout (trend.py), one-minute bars; traded
          through QQQ (1 unit of exposure per unit of buying power) or TQQQ (3);
* gap   - the gap breakout on the day's three biggest large-cap gappers
          (stock_orb.py) at 1% of the account at risk a trade, costs at half the
          spread measured at the open; it also reports the buying power it used;
* mstr  - Bitcoin's noise-area breakout in US hours (crypto.py) times 1.8, what it
          moves MSTR (the long history MSTR itself does not have);
* semis - the noise-area breakout on the equal-weight chip basket, for SOXL (3 units
          per unit of buying power).

A book is a size for each leg.  Its buying power (the stock account's 4x cap)
counts TQQQ and SOXL at a third of their exposure.  Sizes are chosen on Sep 2022
to Aug 2024 only, to make the most dollars a day there with the worst losing
stretch kept inside a budget (25%, 50%, 75% of $25,000, or no budget within 4x);
then Sep 2024 to Sep 2026 shows what those sizes did on days they never saw.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import index                                                                 # noqa: E402
import indexes                                                               # noqa: E402
import trend                                                                 # noqa: E402

ACCOUNT = 25_000.0
SPLIT = "2024-09-01"


def gap_leg():
    """Per day: P&L as a share of the account at 1% risk a trade, and the peak buying power used (x account)."""
    import panel
    import realistic
    import stock_orb as so
    import splits
    P = so.prepare()
    names = P["names"]
    sp = realistic.measured_spreads(names)
    half = np.array([sp.get(n, np.nan) for n in names]) / 2
    O, H, L, C, dates, rng = P["O"], P["H"], P["L"], P["C"], P["dates"], P["day_rng"]
    ret, bp = {}, {}
    for i in range(15, len(dates)):
        atr = rng[i - 14:i].mean(axis=0)
        gap = O[i, :, 0] / C[i - 1, :, -1] - 1.0
        first = np.sign(C[i, :, 4] - O[i, :, 0])
        ok = (np.abs(gap) >= 0.02) & (first != 0) & (atr > 0) & ~np.isnan(gap)
        cand = np.flatnonzero(ok)
        cand = cand[np.argsort(-np.abs(gap[cand]))][:3]
        day, used = 0.0, 0.0
        for k in cand:
            h, l, c, o = H[i, k], L[i, k], C[i, k], O[i, k]
            side = int(first[k])
            lvl = h[:5].max() if side > 0 else l[:5].min()
            hit = np.flatnonzero((h[5:389] >= lvl) if side > 0 else (l[5:389] <= lvl))
            if not len(hit):
                continue
            t = 5 + hit[0]
            px = max(o[t], lvl) if side > 0 else min(o[t], lvl)
            stop = px - side * atr[k]
            out = c[389]
            for u in range(t, 390):
                if (side > 0 and l[u] <= stop) or (side < 0 and h[u] >= stop):
                    out = stop if u == t else (min(o[u], stop) if side > 0 else max(o[u], stop))
                    break
            shares = 0.01 * ACCOUNT / atr[k]
            cost_bp = (half[k] if not np.isnan(half[k]) else 5.0) + 2.0
            day += side * shares * (out - px) - shares * px * cost_bp * 1e-4
            used += shares * px
        ret[dates[i]] = day / ACCOUNT
        bp[dates[i]] = used / ACCOUNT
    return ret, bp


def legs():
    D = index.load()
    r, lo, n, m = trend.noise_days(D)
    ndx = dict(zip(D["dates"], r))
    g, gbp = gap_leg()
    B = indexes.load("BTCUSD")
    rb, _, _, _ = trend.noise_days(B, cost=3e-4)
    mstr = {d: 1.8 * x for d, x in zip(B["dates"], rb)}
    import panel
    cube, dates, names = panel.load_panel("mid")
    chips = ["NVDA", "AMD", "AVGO", "MU", "INTC", "QCOM", "TXN", "AMAT", "LRCX", "ADI", "MCHP", "ON", "MRVL", "TSM"]
    k = [names.index(c) for c in chips]
    sub = cube[:, k].astype(float)
    pc = np.concatenate([np.full((1, len(k)), np.nan), sub[:-1, :, -1, 3]], axis=0)
    basket = {x: np.nanmean(sub[..., j] / pc[:, :, None], axis=1) for j, x in enumerate("OHLC")}
    okd = ~np.isnan(basket["C"]).any(axis=1)
    S = {x: basket[x][okd] for x in "OHLC"}
    S["pc"] = np.ones(okd.sum())
    S["dates"] = np.array(dates)[okd]
    rs, _, _, _ = trend.noise_days(S, cost=2e-4)
    semis = dict(zip(S["dates"], rs))
    common = sorted(set(ndx) & set(g) & set(mstr) & set(semis))
    common = [d for d in common if not any(np.isnan(v[d]) for v in (ndx, g, mstr, semis))]
    X = np.array([[ndx[d], g[d], mstr[d], semis[d]] for d in common])
    return common, X, np.array([gbp[d] for d in common])


def evaluate(dates, X, gbp, e, label=None):
    """e = exposures (ndx, gap, mstr, semis) in units; returns stats in dollars on $25,000."""
    usd = (X @ np.asarray(e)) * ACCOUNT
    ds = np.array(dates)
    dev, test = ds < SPLIT, ds >= SPLIT

    def part(m):
        v = usd[m]
        eq = np.cumsum(v)
        dd = float((eq - np.maximum.accumulate(eq)).min())
        return {"usd": round(float(v.mean()), 1), "median": round(float(np.median(v)), 1), "up": round(float((v > 0).mean()), 3),
                "days_200": round(float((v >= 200).mean()), 3), "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0),
                "sharpe": round(float(v.mean() / (v.std() + 1e-9) * np.sqrt(252)), 2)}
    return {"exposure": [round(x, 2) for x in e], "dev": part(dev), "test": part(test), "all": part(np.ones(len(ds), bool))}


def buying_power(e, gbp, tqqq=True):
    """Peak buying power (x account) the book needs: TQQQ and SOXL at a third, the gap leg at its busiest day."""
    ndx_bp = e[0] / 3 if tqqq else e[0]
    return ndx_bp + e[1] * float(np.percentile(gbp, 99)) + e[2] + e[3] / 3


def main() -> int:
    dates, X, gbp = legs()
    ds = np.array(dates)
    dev = ds < SPLIT
    print(f"{len(dates)} common sessions {dates[0]} to {dates[-1]}; dev to {SPLIT}")
    names = ["ndx", "gap", "mstr", "semis"]
    print("legs at one unit (per day, dev / test, $ on $25,000):")
    for j, n in enumerate(names):
        v = X[:, j] * ACCOUNT
        print(f"  {n:6s} ${v[dev].mean():+6.1f} / ${v[~dev].mean():+6.1f} | Sharpe {v[dev].mean() / v[dev].std() * np.sqrt(252):+.2f} / "
              f"{v[~dev].mean() / v[~dev].std() * np.sqrt(252):+.2f}")
    print("daily correlation:\n" + "\n".join("  " + " ".join(f"{x:+.2f}" for x in row) for row in np.corrcoef(X.T)))
    print(f"gap leg buying power at 1% risk: median {np.median(gbp):.2f}x, 99th percentile {np.percentile(gbp, 99):.2f}x")
    # grid of sizes: ndx exposure 0-12 (TQQQ up to 4x buying power), gap risk 0-3%, mstr 0-4, semis 0-12
    grid = itertools.product(np.arange(0, 12.01, 1.0), np.arange(0, 3.01, 0.5), np.arange(0, 4.01, 0.5), np.arange(0, 12.01, 1.5))
    rows = []
    for e in grid:
        if buying_power(e, gbp) > 4.0 + 1e-9 or sum(e) == 0:
            continue
        usd = (X[dev] @ np.asarray(e)) * ACCOUNT
        eq = np.cumsum(usd)
        dd = float((eq - np.maximum.accumulate(eq)).min())
        rows.append((float(usd.mean()), dd, e))
    res = {"legs": names, "sessions": len(dates), "budgets": {}}
    for budget in (0.25, 0.5, 0.75, None):
        ok = [r for r in rows if budget is None or -r[1] <= budget * ACCOUNT]
        best = max(ok, key=lambda r: r[0])
        st = evaluate(dates, X, gbp, best[2])
        tag = f"worst stretch within {budget:.0%}" if budget else "no budget (4x buying power)"
        res["budgets"][tag] = st
        e = st["exposure"]
        print(f"\n{tag}: ndx {e[0]:.0f} (TQQQ {e[0] / 3:.2f}x BP), gap {e[1]:.1f}% risk, mstr {e[2]:.1f}x, semis {e[3]:.1f} (SOXL {e[3] / 3:.2f}x BP) "
              f"| buying power {buying_power(best[2], gbp):.2f}x")
        for part in ("dev", "test"):
            p = st[part]
            print(f"  {part:4s} ${p['usd']:+7.1f} a day (median ${p['median']:+.0f}) | up {p['up']:.0%} | $200+ {p['days_200']:.0%} | "
                  f"worst day ${p['worst_day']:+.0f} | worst stretch ${p['max_drawdown']:+.0f} | Sharpe {p['sharpe']:+.2f}")
    (ROOT / "strategies" / "quick" / "maximize.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
