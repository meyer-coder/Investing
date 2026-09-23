"""Where is the edge in one-to-four-minute trades?  A fast event study.

    python strategies/scalp/events.py

For every minute of every name in the universe, and for each candidate setup
(a condition on that minute's close), the net result of buying at the next
minute's open and selling at the open h minutes later, less that name's cost
both ways.  Averaged per setup: basis points a trade, win rate, how often it
fires, on the first 14 sessions and the last 7 separately.  A setup worth a
bot keeps its edge in both halves and across most names.

Only minutes inside 09:35-15:45 New York count, and the exit is always inside
the same session: nothing is held past the close.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
import minute                                                                # noqa: E402
from evotrader.features import build_features                               # noqa: E402

NAMES = list(minute.SCALP_NAMES)
HOLDS = (1, 2, 3, 4)
OUT = ROOT / "strategies" / "scalp" / "events.json"


def cost_bp(prices: np.ndarray) -> float:
    """A cent and a basis point each way: the spread at the next open, and a little more."""
    return 1e4 * 0.01 / float(np.median(prices)) + 1.0


def setups(F: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Candidate conditions, each a boolean array over the minutes."""
    r1, r1p = F["ret1"], np.concatenate([[np.nan], F["ret1"][:-1]])
    r2 = r1 + r1p
    atr, z, rsi7 = F["atr_pct"], F["zscore20"], F["rsi7"]
    vr, dv = F["volume_ratio"], F["dist_session_vwap"]
    mso = F["minutes_since_open"]
    out: Dict[str, np.ndarray] = {}
    for k, zz in itertools.product((1.5, 2.0, 3.0, 4.0), (1.5, 2.0, 2.5, 3.0)):
        out[f"fade drop 2m>{k}atr z<-{zz}"] = (r2 < -k * atr) & (z < -zz)
        out[f"fade rise 2m>{k}atr z>{zz}"] = (r2 > k * atr) & (z > zz)
        out[f"chase rise 2m>{k}atr z>{zz}"] = out[f"fade rise 2m>{k}atr z>{zz}"]
    for k in (1.0, 1.5, 2.0, 3.0):
        out[f"fade drop 1m>{k}atr"] = r1 < -k * atr
        out[f"chase rise 1m>{k}atr"] = r1 > k * atr
    for k, v in itertools.product((1.0, 2.0), (2.0, 3.0, 5.0)):
        out[f"chase rise 1m>{k}atr vol>{v}x above vwap"] = (r1 > k * atr) & (vr > v) & (dv > 0)
        out[f"fade drop 1m>{k}atr vol>{v}x"] = (r1 < -k * atr) & (vr > v)
    for r, m in itertools.product((10, 20), (2.0, 4.0)):
        out[f"fade rsi7<{r} under vwap {m}atr"] = (rsi7 < r) & (dv < -m * atr)
    for k in (1.0, 2.0, 3.0):
        out[f"chase rise 1m>{k}atr first 30m"] = (r1 > k * atr) & (mso >= 1) & (mso <= 30)
        out[f"fade drop 1m>{k}atr first 30m"] = (r1 < -k * atr) & (mso >= 1) & (mso <= 30)
        out[f"short chase drop 1m>{k}atr"] = r1 < -k * atr
        out[f"short chase drop 1m>{k}atr first 30m"] = (r1 < -k * atr) & (mso >= 1) & (mso <= 30)
        out[f"short fade rise 1m>{k}atr"] = r1 > k * atr
    return out


def study() -> dict:
    days = minute.sessions(NAMES)
    dev = set(days[:14])
    u = minute.universe(NAMES)
    f = build_features(u)
    stamps = u.calendar
    sess = np.array([minute.session_of(t) for t in stamps])
    is_dev = np.array([s in dev for s in sess])
    rows: Dict[str, Dict[str, list]] = {}
    for name in NAMES:
        b = u.bars[name]
        o = np.asarray(b.open, dtype=float)
        F = {k: np.asarray(f.matrix[name][k], dtype=float) for k in
             ("ret1", "atr_pct", "zscore20", "rsi7", "volume_ratio", "dist_session_vwap",
              "minutes_since_open", "minute_of_day")}
        c2 = 2 * cost_bp(o)
        mod = F["minute_of_day"]
        ok_time = (F["minutes_since_open"] >= 5) & (mod < 945)
        n = len(o)
        for label, cond in setups(F).items():
            cond = np.nan_to_num(cond.astype(float)).astype(bool) & ok_time
            idx = np.flatnonzero(cond[: n - 6])
            for h in HOLDS:
                j = idx + 1
                k = idx + 1 + h
                same = sess[j] == sess[k]
                j, k, i0 = j[same], k[same], idx[same]
                if label.startswith("fade rise") or label.startswith("short"):
                    net = (o[j] / o[k] - 1.0) * 1e4 - c2      # a short: the name falls
                else:
                    net = (o[k] / o[j] - 1.0) * 1e4 - c2
                key = f"{label} | hold {h}m"
                r = rows.setdefault(key, {"dev": [], "test": [], "names_dev": {}, "sess": []})
                for part, mask in (("dev", is_dev[i0]), ("test", ~is_dev[i0])):
                    r[part].extend(net[mask].tolist())
                r["names_dev"][name] = float(np.mean(net[is_dev[i0]])) if is_dev[i0].any() else np.nan
    ndev, ntest = len(dev), len(days) - len(dev)
    res = []
    for key, r in rows.items():
        d, t = np.array(r["dev"]), np.array(r["test"])
        if len(d) < 30:
            continue
        names_pos = sum(1 for v in r["names_dev"].values() if v == v and v > 0)
        res.append({"setup": key, "dev_bp": round(float(d.mean()), 2), "dev_n_day": round(len(d) / ndev, 1),
                    "dev_win": round(float((d > 0).mean()), 3),
                    "dev_t": round(float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))), 2) if len(d) > 1 else 0.0,
                    "test_bp": round(float(t.mean()), 2) if len(t) else None, "test_n_day": round(len(t) / ntest, 1),
                    "test_win": round(float((t > 0).mean()), 3) if len(t) else None,
                    "names_up_dev": names_pos})
    res.sort(key=lambda x: x["dev_bp"] * np.sqrt(x["dev_n_day"]), reverse=True)
    return {"sessions": {"dev": days[:14], "test": days[14:]}, "setups": res}


if __name__ == "__main__":
    out = study()
    OUT.write_text(json.dumps(out, indent=1))
    print(f"{len(out['setups'])} setups; best by dev edge x frequency:")
    for x in out["setups"][:30]:
        print(f"  {x['setup'][:58]:58s} dev {x['dev_bp']:+6.1f}bp x{x['dev_n_day']:6.1f}/day win {x['dev_win']:.0%} "
              f"t {x['dev_t']:+5.1f} names+ {x['names_up_dev']:2d}/17 | test {x['test_bp']:+6.1f}bp x{x['test_n_day']:6.1f}/day "
              f"win {x['test_win']:.0%}")


def fine() -> list:
    """The dip-buy family in detail: drop size, window, filter, hold."""
    days = minute.sessions(NAMES)
    dev = set(days[:14])
    u = minute.universe(NAMES)
    f = build_features(u)
    sess = np.array([minute.session_of(t) for t in u.calendar])
    is_dev = np.array([s in dev for s in sess])
    acc: Dict[str, Dict[str, list]] = {}
    for name in NAMES:
        o = np.asarray(u.bars[name].open, dtype=float)
        F = {k: np.asarray(f.matrix[name][k], dtype=float) for k in
             ("ret1", "atr_pct", "zscore20", "volume_ratio", "dist_session_vwap", "sma20_slope",
              "minutes_since_open", "minute_of_day")}
        c2 = 2 * cost_bp(o)
        mso, n = F["minutes_since_open"], len(o)
        filters = {"none": np.ones(n, bool), "above vwap": F["dist_session_vwap"] > 0,
                   "below vwap": F["dist_session_vwap"] < 0, "z<-1": F["zscore20"] < -1,
                   "rising 20m": F["sma20_slope"] > 0, "vol>1.5x": F["volume_ratio"] > 1.5}
        for k, w, (fn, fm), h in itertools.product((0.5, 0.75, 1.0, 1.5, 2.0), (15, 30, 45, 60, 120, 380),
                                                   filters.items(), HOLDS):
            cond = (F["ret1"] < -k * F["atr_pct"]) & fm & (mso >= 5) & (mso <= w) & (F["minute_of_day"] < 945)
            idx = np.flatnonzero(np.nan_to_num(cond.astype(float))[: n - 6].astype(bool))
            j, kk = idx + 1, idx + 1 + h
            same = sess[j] == sess[kk]
            j, kk, i0 = j[same], kk[same], idx[same]
            net = (o[kk] / o[j] - 1.0) * 1e4 - c2
            r = acc.setdefault(f"buy 1m drop>{k}atr, 09:35+{w}m, {fn}, hold {h}m", {"dev": [], "test": [], "names": {}})
            r["dev"].extend(net[is_dev[i0]].tolist())
            r["test"].extend(net[~is_dev[i0]].tolist())
            r["names"][name] = float(net[is_dev[i0]].mean()) if is_dev[i0].any() else float("nan")
    out = []
    for key, r in acc.items():
        d, t = np.array(r["dev"]), np.array(r["test"])
        if len(d) < 40 or len(t) < 20:
            continue
        out.append({"setup": key, "dev_bp": round(float(d.mean()), 2), "dev_n_day": round(len(d) / 14, 1),
                    "dev_win": round(float((d > 0).mean()), 3),
                    "dev_t": round(float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))), 2),
                    "test_bp": round(float(t.mean()), 2), "test_n_day": round(len(t) / 7, 1),
                    "test_win": round(float((t > 0).mean()), 3),
                    "names_up_dev": sum(1 for v in r["names"].values() if v == v and v > 0)})
    return out
