"""Does the own-drop edge grow with volatility?  The rule on each day's most volatile names.

    python strategies/scalp/volsubset.py

The one-month result for buying a stock's own sharp drop at the open came from
very volatile names (MSTR, COIN, SOXL, IONQ...); on four years of 72 large caps
the same rule makes a few dollars a day.  If the edge scales with how much a
name moves, restricting it to the most volatile names of the moment should
show it.  Each session, only the N names with the highest realized one-minute
volatility over the previous 20 sessions (known before the open) may trade.
Buy own drops (families.py) from 09:35 to 09:45 or 10:00, hold 2 or 3 minutes,
3 or 5 slots; dev 2022-09 to 2024-08, test 2024-09 to 2026-09.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402

SPLIT = "2024-09-01"
_P: dict = {}


def trailing_vol(cube: np.ndarray) -> np.ndarray:
    """(days, names): realized one-minute volatility of each session."""
    c = cube[:, :, :, 3].astype(float)
    r = c[:, :, 1:] / c[:, :, :-1] - 1.0
    return np.nanstd(r, axis=2)


def _run(job):
    days_idx, configs = job
    cube, dates, names, vol = _P["cube"], _P["dates"], _P["names"], _P["vol"]
    out = {}
    for i in days_idx:
        if i < 21:
            continue
        f = panel.features(cube[i], cube[i - 1][:, -1, 3].astype(float), cube[i - 1])
        o = f["o"]
        past = np.nanmean(vol[i - 20:i], axis=0)
        order = np.argsort(-np.nan_to_num(past))
        for key, (top, a, b, k, z, hold, slots) in configs.items():
            allowed = np.zeros(len(names), dtype=bool)
            allowed[order[:top]] = True
            m = (-f["r1"] > k * f["atr"]) & (-f["resid_z"] > z) & allowed[:, None]
            m[:, :a] = False
            m[:, b + 1:] = False
            m = np.nan_to_num(m.astype(float)).astype(bool)
            prio = np.nan_to_num(-f["resid_z"])
            pnl, n_tr, rets = 0.0, 0, []
            free_at = []
            for t in np.flatnonzero(m.any(axis=0)):
                t_in, t_out = t + 1, t + 1 + hold
                free_at = [x for x in free_at if x[0] > t_in]
                held = {x[1] for x in free_at}
                ks = np.flatnonzero(m[:, t])
                ks = ks[np.argsort(-prio[ks, t])]
                for kk in ks:
                    if len(free_at) >= slots:
                        break
                    if kk in held:
                        continue
                    ret = o[kk, t_out] / o[kk, t_in] - 1.0 - 2 * (0.01 / o[kk, t_in] + 1e-4)
                    pnl += panel.ACCOUNT / slots * ret
                    rets.append(ret)
                    n_tr += 1
                    free_at.append((t_out, kk))
                    held.add(kk)
            out.setdefault(key, {})[dates[i]] = (pnl, n_tr, sum(rets))
    return out


def main() -> int:
    import multiprocessing as mp
    cube, dates, names = panel.load_panel()
    _P.update(cube=cube, dates=dates, names=names, vol=trailing_vol(cube))
    configs = {}
    for top, (wn, (a, b)), k, z, hold, slots in itertools.product((10, 20, 36, 72), (("09:35-09:45", (5, 15)), ("09:35-10:00", (5, 30))),
                                                                  (0.75, 1.5), (1.5, 2.0), (2, 3), (3, 5)):
        configs[f"top {top} by volatility | own drop {wn} k{k} z{z} | hold {hold}m | {slots} slots"] = (top, a, b, k, z, hold, slots)
    idx = list(range(1, len(dates)))
    with mp.get_context("fork").Pool(4) as pool:
        parts = pool.map(_run, [(idx[j::4], configs) for j in range(4)])
    acc: Dict[str, Dict[str, tuple]] = {}
    for part in parts:
        for key, byday in part.items():
            acc.setdefault(key, {}).update(byday)
    rows = {}
    for key, byday in acc.items():
        ds = sorted(byday)
        dev = np.array([byday[d][0] for d in ds if d < SPLIT])
        test = np.array([byday[d][0] for d in ds if d >= SPLIT])
        ntr = sum(byday[d][1] for d in ds)
        rows[key] = {"dev_usd": round(float(dev.mean()), 1), "test_usd": round(float(test.mean()), 1),
                     "test_up": round(float((test > 0).mean()), 3), "trades_per_day": round(ntr / len(ds), 2),
                     "bp_per_trade": round(float(sum(byday[d][2] for d in ds) / max(ntr, 1) * 1e4), 2),
                     "years": {y: round(float(np.mean([byday[d][0] for d in ds if d[:4] == y])), 1) for y in sorted({d[:4] for d in ds})}}
    ranked = sorted(rows.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print(f"{len(dates)} sessions; $ a day on $25,000 at 1x (x4 at the day-trading maximum)")
    for key, v in ranked[:30]:
        print(f"  {key:72s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} (x4 ${4 * v['test_usd']:+6.0f}) up {v['test_up']:.0%} "
              f"{v['trades_per_day']:.1f} tr/d {v['bp_per_trade']:+.1f} bp | " + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in v["years"].items()))
    (ROOT / "strategies" / "scalp" / "volsubset.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
