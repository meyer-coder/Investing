"""Short-hold stock scalpers on four years of minutes: which families earn $200 a day on $25,000?

    python strategies/scalp/families.py

Every rule holds one to three minutes and is flat long before the close.  The
families, each with a few settings:

* own drop, bought: a name falls hard on its own (a one-minute drop beyond k
  of its typical range and more than z standard deviations below the other
  names that minute), in four windows of the day;
* own rise, bought: the same upward, which the short test of the Own-Drop
  Scalper suggested keeps going at the open;
* first minute faded: a name's 09:30 minute moves hard on its own, trade the
  other way from 09:31;
* the short mirrors of the first two (sell an own rise, sell an own drop).

Each rule runs as a book of three slots (a third of buying power each; the
strongest signal first) over 2022-09 to 2024-08 (dev) and 2024-09 to 2026-09
(test), on all 72 names and on each half of them (names at even and odd
places), with each name's cost (a cent plus 1 bp each way).  Dollars are at
1x buying power on $25,000; they scale with buying power (2x doubles them, 4x,
the day-trading maximum, quadruples them).
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402

SPLIT = "2024-09-01"
WINDOWS = {"09:35-09:45": (5, 15), "09:45-10:30": (15, 60), "10:30-15:30": (60, 360), "15:30-15:50": (360, 380)}
_P: dict = {}


def rules() -> Dict[str, dict]:
    out = {}
    for (wn, (a, b)), k, z, hold in itertools.product(WINDOWS.items(), (0.75, 1.5), (2.0, 3.0), (1, 2, 3)):
        out[f"buy own drop {wn} k{k} z{z} hold {hold}m"] = dict(kind="own_drop", side=1, a=a, b=b, k=k, z=z, hold=hold)
        out[f"sell own drop {wn} k{k} z{z} hold {hold}m"] = dict(kind="own_drop", side=-1, a=a, b=b, k=k, z=z, hold=hold)
        out[f"buy own rise {wn} k{k} z{z} hold {hold}m"] = dict(kind="own_rise", side=1, a=a, b=b, k=k, z=z, hold=hold)
        out[f"sell own rise {wn} k{k} z{z} hold {hold}m"] = dict(kind="own_rise", side=-1, a=a, b=b, k=k, z=z, hold=hold)
    for k, hold in itertools.product((1.5, 3.0), (1, 2, 3)):
        out[f"fade the first minute k{k} hold {hold}m"] = dict(kind="first_min", side=-1, k=k, hold=hold)
        out[f"go with the first minute k{k} hold {hold}m"] = dict(kind="first_min", side=1, k=k, hold=hold)
    return out


def signal(f: Dict[str, np.ndarray], r: dict):
    n, T = f["r1"].shape
    side = np.zeros((n, T), dtype=int)
    prio = np.zeros((n, T))
    if r["kind"] in ("own_drop", "own_rise"):
        sgn = -1 if r["kind"] == "own_drop" else 1
        m = (sgn * f["r1"] > r["k"] * f["atr"]) & (sgn * f["resid_z"] > r["z"])
        m[:, :r["a"]] = False
        m[:, r["b"] + 1:] = False
        side[np.nan_to_num(m.astype(float)).astype(bool)] = r["side"]
        prio = np.nan_to_num(sgn * f["resid_z"])
    elif r["kind"] == "first_min":
        first = f["resid"][:, 0] / np.maximum(f["atr"][:, 0], 1e-6)
        m = np.abs(first) > r["k"]
        side[m, 0] = (r["side"] * np.sign(first[m])).astype(int)
        prio[:, 0] = np.abs(np.nan_to_num(first))
    return side, prio


def _run_days(job):
    days, rule_items, masks = job
    cube, dates, names = _P["cube"], _P["dates"], _P["names"]
    idx = {d: i for i, d in enumerate(dates)}
    out = {}
    for d in days:
        i = idx[d]
        if i == 0:
            continue
        f = panel.features(cube[i], cube[i - 1][:, -1, 3].astype(float), cube[i - 1])
        o = f["o"]
        for rname, r in rule_items:
            side, prio = signal(f, r)
            for mname, mask in masks.items():
                s = side * mask[:, None]
                pnl = 0.0
                n_tr = 0
                free_at = []
                for t in np.flatnonzero((s != 0).any(axis=0)):
                    t_in, t_out = t + 1, t + 1 + r["hold"]
                    if t_out >= 386:
                        continue
                    free_at = [x for x in free_at if x[0] > t_in]
                    held = {x[1] for x in free_at}
                    ks = np.flatnonzero(s[:, t] != 0)
                    ks = ks[np.argsort(-prio[ks, t])]
                    for k in ks:
                        if len(free_at) >= 3:
                            break
                        if k in held:
                            continue
                        px_in, px_out = o[k, t_in], o[k, t_out]
                        cost = 2 * (0.01 / px_in + 1e-4)
                        pnl += (panel.ACCOUNT / 3) * (s[k, t] * (px_out / px_in - 1.0) - cost)
                        n_tr += 1
                        free_at.append((t_out, k))
                        held.add(k)
                out.setdefault((rname, mname), {})[d] = (pnl, n_tr)
    return out


def main() -> int:
    import multiprocessing as mp
    cube, dates, names = panel.load_panel()
    _P.update(cube=cube, dates=dates, names=names)
    n = len(names)
    masks = {"all names": np.ones(n), "even names": (np.arange(n) % 2 == 0).astype(float),
             "odd names": (np.arange(n) % 2 == 1).astype(float)}
    items = list(rules().items())
    days = dates[1:]
    chunks = [days[i::4] for i in range(4)]
    with mp.get_context("fork").Pool(4) as pool:
        parts = pool.map(_run_days, [(c, items, masks) for c in chunks])
    acc: Dict[tuple, Dict[str, tuple]] = {}
    for part in parts:
        for key, byday in part.items():
            acc.setdefault(key, {}).update(byday)
    rows = {}
    for (rname, mname), byday in acc.items():
        ds = sorted(byday)
        dev = np.array([byday[d][0] for d in ds if d < SPLIT])
        test = np.array([byday[d][0] for d in ds if d >= SPLIT])
        tr = np.array([byday[d][1] for d in ds])
        rows.setdefault(rname, {})[mname] = {
            "dev_usd": round(float(dev.mean()), 1), "test_usd": round(float(test.mean()), 1),
            "dev_up": round(float((dev > 0).mean()), 3), "test_up": round(float((test > 0).mean()), 3),
            "trades_per_day": round(float(tr.mean()), 2),
            "years": {y: round(float(np.mean([byday[d][0] for d in ds if d[:4] == y])), 1) for y in sorted({d[:4] for d in ds})}}
    ranked = sorted(rows.items(), key=lambda kv: -min(kv[1]["all names"]["dev_usd"], kv[1]["all names"]["test_usd"]))
    print(f"{len(days)} sessions, {len(names)} names; $ a day on $25,000 at 1x (x4 at the day-trading maximum); dev before {SPLIT}")
    for rname, v in ranked[:40]:
        a, e, o_ = v["all names"], v["even names"], v["odd names"]
        print(f"  {rname:48s} all ${a['dev_usd']:+6.1f}/${a['test_usd']:+6.1f} up {a['test_up']:.0%} {a['trades_per_day']:5.2f} tr/d | "
              f"even ${e['dev_usd']:+6.1f}/${e['test_usd']:+6.1f} | odd ${o_['dev_usd']:+6.1f}/${o_['test_usd']:+6.1f} | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in a["years"].items()))
    (ROOT / "strategies" / "scalp" / "families.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
