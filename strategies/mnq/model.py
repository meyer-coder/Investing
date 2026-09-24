"""Can a model that weighs many minute-level signals at once find a five-to-ten-
minute edge in the Nasdaq-100 that no single setup has?

    python strategies/mnq/model.py

Every minute from 09:45 to 15:45 of every session (Dukascopy's Nasdaq-100,
September 2020 on) is a row: about thirty features computed only from bars
already closed (returns over 1 to 60 minutes scaled by the recent one-minute
move, volatility and its change, where the price sits in the day's range and
against the session average, the opening range, the gap, the day's move, the
minute of the day) and the next ten minutes' return from the next minute's
open, in basis points.

A gradient-boosted tree model (LightGBM) is fit on September 2020 to 2022;
2023 picks how confident a call must be to trade; then the model is refit on
2020 to 2023 with that setting and judged once on 2024 to September 2026,
which it never saw.  The trade rule is the MNQ bot's: one position at a
time, in at the next minute's open, out ten minutes later, today's MNQ cost.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import data                                                                  # noqa: E402
from edges import COST_BP                                                    # noqa: E402

HOLD = 10
FIRST, LAST = 15, 375                     # 09:45 to 15:45
OUT = ROOT / "strategies" / "mnq" / "model.json"


def day_rows(day: data.Day, prev: data.Day, prev2: data.Day) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Features and labels for one session's minutes FIRST..LAST."""
    o, h, l, c = day.o, day.h, day.l, day.c
    n = len(c)
    r1 = np.concatenate([[c[0] / o[0] - 1.0], c[1:] / c[:-1] - 1.0])
    sd_prev = float(np.std(prev.c[1:] / prev.c[:-1] - 1.0))
    sd = np.full(n, sd_prev)
    for i in range(15, n):
        sd[i] = np.std(r1[max(0, i - 29):i + 1])
    sd = np.maximum(sd, 1e-6)

    def back(k):
        out = np.full(n, np.nan)
        out[k:] = c[k:] / c[:-k] - 1.0
        return out / (sd * np.sqrt(k))

    hod, lod = np.maximum.accumulate(h), np.minimum.accumulate(l)
    rng = np.maximum(hod - lod, 1e-9)
    twap = np.cumsum((h + l + c) / 3.0) / np.arange(1, n + 1)
    or_h, or_l = h[:15].max(), l[:15].min()
    mso = np.arange(n, dtype=float)
    body = (c - o) / np.maximum(h - l, 1e-9)
    since_high = np.zeros(n)
    since_low = np.zeros(n)
    for i in range(1, n):
        since_high[i] = 0 if h[i] >= hod[i - 1] else since_high[i - 1] + 1
        since_low[i] = 0 if l[i] <= lod[i - 1] else since_low[i - 1] + 1
    feats = {
        "z1": back(1), "z2": back(2), "z3": back(3), "z5": back(5), "z10": back(10), "z15": back(15),
        "z30": back(30), "z60": back(60),
        "vol": sd / sd_prev, "vol_prev": np.full(n, sd_prev / max(np.std(prev2.c[1:] / prev2.c[:-1] - 1.0), 1e-6)),
        "range_pos": (c - lod) / rng, "from_high": (hod - c) / (c * sd), "from_low": (c - lod) / (c * sd),
        "twap": (c / twap - 1.0) / sd, "or_high": (c / or_h - 1.0) / sd, "or_low": (c / or_l - 1.0) / sd,
        "day_ret": (c / prev.c[-1] - 1.0) / (sd_prev * np.sqrt(390)),
        "open_ret": (c / o[0] - 1.0) / (sd_prev * np.sqrt(390)),
        "gap": np.full(n, (o[0] / prev.c[-1] - 1.0) / (sd_prev * np.sqrt(390))),
        "prev_day": np.full(n, (prev.c[-1] / prev2.c[-1] - 1.0) / (sd_prev * np.sqrt(390))),
        "mso": mso, "dow": np.full(n, float(np.datetime64(day.date).astype("datetime64[D]").view("int64") % 7)),
        "body": body, "bar_range": (h - l) / (c * sd), "since_high": since_high, "since_low": since_low,
        "range_day": rng / (c * sd_prev * np.sqrt(390)),
    }
    names = list(feats)
    X = np.column_stack([feats[k] for k in names])
    y = np.full(n, np.nan)
    ok = np.arange(n - 1 - HOLD)
    y[ok] = (o[ok + 1 + HOLD] / o[ok + 1] - 1.0) * 1e4
    idx = np.arange(FIRST, min(LAST + 1, n - 1 - HOLD))
    return X[idx], y[idx], names


def table(days: Dict[str, data.Day]):
    keys = sorted(days)
    Xs, ys, ds, ms = [], [], [], []
    names = None
    for j in range(2, len(keys)):
        d, p, p2 = days[keys[j]], days[keys[j - 1]], days[keys[j - 2]]
        X, y, names = day_rows(d, p, p2)
        Xs.append(X)
        ys.append(y)
        ds += [d.date] * len(y)
        ms += list(range(FIRST, FIRST + len(y)))
    return np.vstack(Xs), np.concatenate(ys), np.array(ds), np.array(ms), names


def fit(X, y, seed: int = 0):
    import lightgbm as lgb
    params = {"objective": "regression", "learning_rate": 0.03, "num_leaves": 31, "min_data_in_leaf": 500,
              "bagging_fraction": 0.7, "bagging_freq": 1, "feature_fraction": 0.7, "lambda_l2": 10.0,
              "seed": seed, "verbose": -1, "num_threads": 4}
    clip = np.clip(y, -60, 60)                   # a few crash minutes should not steer the fit
    return lgb.train(params, lgb.Dataset(X, clip), num_boost_round=400)


CACHE = ROOT / "data" / "cache" / "duka" / "model_table.npz"


def cached_table():
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        return z["X"], z["y"], z["dates"], z["mins"], list(z["names"])
    X, y, dates, mins, names = table(data.sessions("duka"))
    np.savez_compressed(CACHE, X=X, y=y, dates=dates, mins=mins, names=np.array(names))
    return X, y, dates, mins, names


def trade(pred: np.ndarray, y: np.ndarray, dates: np.ndarray, mins: np.ndarray, thr: float) -> dict:
    """One position at a time: the first minute a call clears `thr`, hold ten
    minutes, then look again."""
    pnl: Dict[str, float] = {}
    trades = []
    busy_until = {}
    for p, r, d, m in zip(pred, y, dates, mins):
        pnl.setdefault(d, 0.0)
        if abs(p) < thr or m < busy_until.get(d, -1):
            continue
        net = np.sign(p) * r - COST_BP
        trades.append(net)
        pnl[d] += net
        busy_until[d] = m + 1 + HOLD
    t = np.array(trades)
    daily = np.array(list(pnl.values()))
    return {"trades": len(t), "per_day": round(len(t) / max(len(daily), 1), 2),
            "bp_per_trade": round(float(t.mean()), 2) if len(t) else 0.0,
            "t": round(float(t.mean() / (t.std(ddof=1) / np.sqrt(len(t)))), 2) if len(t) > 2 else 0.0,
            "win": round(float((t > 0).mean()), 3) if len(t) else 0.0,
            "bp_per_day": round(float(daily.mean()), 2), "days_up": round(float((daily > 0).mean()), 3)}


def main() -> int:
    X, y, dates, mins, names = cached_table()
    print(f"{len(y)} rows, {len(names)} features, {len(set(dates))} sessions", flush=True)
    train = dates < "2023-01-01"
    tune = (dates >= "2023-01-01") & (dates < "2024-01-01")
    test = dates >= "2024-01-01"
    m1 = fit(X[train], y[train])
    p_tune = m1.predict(X[tune])
    print("tune 2023: corr of prediction and outcome", round(float(np.corrcoef(p_tune, y[tune])[0, 1]), 4), flush=True)
    out = {"features": names, "tune": {}, "test": {}}
    for q in (0.9, 0.95, 0.98, 0.99, 0.995):
        thr = float(np.quantile(np.abs(m1.predict(X[train])), q))
        out["tune"][q] = dict(trade(p_tune, y[tune], dates[tune], mins[tune], thr), thr=round(thr, 3))
        print(f"  tune 2023 | top {1 - q:.1%} of calls (|pred| > {thr:.2f} bp): {out['tune'][q]}", flush=True)
    best_q = max(out["tune"], key=lambda q: out["tune"][q]["bp_per_day"])
    m2 = fit(X[train | tune], y[train | tune])
    p_test = m2.predict(X[test])
    thr = float(np.quantile(np.abs(m2.predict(X[train | tune])), best_q))
    print("test 2024-2026: corr", round(float(np.corrcoef(p_test, y[test])[0, 1]), 4), flush=True)
    for q in (0.9, 0.95, 0.98, 0.99, 0.995):
        th = float(np.quantile(np.abs(m2.predict(X[train | tune])), q))
        out["test"][q] = dict(trade(p_test, y[test], dates[test], mins[test], th), thr=round(th, 3))
        mark = " <- picked on 2023" if q == best_q else ""
        print(f"  test 2024-26 | top {1 - q:.1%} of calls: {out['test'][q]}{mark}", flush=True)
        yrs = {}
        for yy in ("2024", "2025", "2026"):
            sel = np.array([str(d).startswith(yy) for d in dates[test]])
            yrs[yy] = trade(p_test[sel], y[test][sel], dates[test][sel], mins[test][sel], th)["bp_per_day"]
        out["test"][q]["bp_per_day_by_year"] = yrs
    imp = sorted(zip(names, m2.feature_importance()), key=lambda x: -x[1])
    out["importance"] = [(k, int(v)) for k, v in imp]
    out["picked_quantile"] = best_q
    print("importance:", imp[:12])
    OUT.write_text(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
