"""A model that picks which sharp drops bounce hardest, fitted on the dev years only.

    python strategies/scalp/dropmodel.py

The rules pick drops by two numbers (the drop in typical ranges and the
residual z).  The candidate table has 25 things a trader could see at the
signal minute's close.  LightGBM learns the three-minute return from the next
open on drop candidates from 2022-09 to 2024-08 only; the test years
(2024-09 to 2026-09) are scored blind.  The book then buys the candidates the
model rates above their own cost, best first, three slots, three-minute hold,
and is reported with the base and tight costs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import book                                                                  # noqa: E402

DROP_FEATURES = ["minute", "r1_atr", "resid_z", "r1", "atr", "resid", "gap", "mkt_r1", "mkt_r5", "ret5", "ret15", "ret30",
                 "day_ret", "range_pos", "clv", "bar_range", "breadth_down", "breadth_up", "prev_z", "prev_r1_atr",
                 "vol20", "atr_ratio", "prev_day_ret", "sector_z"]


def fit(d: dict, mask_train: np.ndarray, target: np.ndarray, seed: int = 7):
    import lightgbm as lgb
    X = np.column_stack([d["f"][k] for k in DROP_FEATURES]).astype(np.float32)
    ok = mask_train & ~np.isnan(target)
    params = {"objective": "huber", "alpha": 0.002, "learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 2000,
              "feature_fraction": 0.8, "bagging_fraction": 0.7, "bagging_freq": 1, "lambda_l2": 10.0, "verbose": -1,
              "seed": seed, "num_threads": 4}
    ds = lgb.Dataset(X[ok], target[ok])
    model = lgb.train(params, ds, num_boost_round=300)
    return model, X


def main() -> int:
    d = book.load()
    f = d["f"]
    drop = (f["r1_atr"] < -0.5) & (f["resid_z"] < -1.5) & (f["minute"] >= 5) & (f["minute"] <= 380)
    dev = d["date_of"] < book.SPLIT
    y3 = d["y"][:, 0, 2].astype(float)
    tight = 0.01 / f["px"] + 1e-4
    base = 2 * tight
    model, X = fit(d, drop & dev, y3)
    pred = np.full(len(y3), np.nan)
    pred[drop] = model.predict(X[drop], num_threads=4)
    imp = dict(zip(DROP_FEATURES, model.feature_importance("gain").round(1).tolist()))
    test = drop & ~dev
    corr = float(np.corrcoef(pred[test & ~np.isnan(y3)], y3[test & ~np.isnan(y3)])[0, 1])
    print(f"{drop.sum()} drop candidates; test correlation of predicted and actual 3-min return {corr:.3f}")
    # deciles of the prediction on the test years
    q = np.nanpercentile(pred[test], np.arange(0, 101, 10))
    q[-1] += 1e-9
    n_days = len(set(d["date_of"][test]))
    for a, b in zip(q[:-1], q[1:]):
        m = test & (pred >= a) & (pred < b)
        print(f"  predicted {a * 1e4:+6.2f}..{b * 1e4:+6.2f} bp: actual {np.nanmean(y3[m]) * 1e4:+6.2f} bp, late {np.nanmean(d['y'][m, 1, 2]) * 1e4:+6.2f} bp "
              f"({m.sum() / n_days:.0f} a day)")
    res = {"test_corr": round(corr, 4), "importance": imp, "books": {}}
    for cost_name, cost in (("base", base), ("tight", tight)):
        for edge_bp in (0.0, 1.0, 2.0, 4.0):
            for slots in (3, 5):
                sel = drop & (pred - cost > edge_bp * 1e-4)
                label = f"model pick, {cost_name} cost, edge > {edge_bp:.0f} bp, {slots} slots"
                taken: list = []
                row = book.report(book.replay(d, sel, np.ones(len(sel)), np.nan_to_num(pred - cost), hold=3, slots=slots,
                                              cost=cost_name, taken=taken), label)
                res["books"][label] = row
                if cost_name == "base" and edge_bp == 2.0 and slots == 3:
                    np.save(book.candidates.panel.CACHE / "model_trades.npy", np.array(taken))
    (ROOT / "strategies" / "scalp" / "dropmodel.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
