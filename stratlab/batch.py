"""Batches: many cards from one file, logged before they run, with random controls.

A batch file (JSON):

    {
      "name": "confluence-nas100",
      "base": { ...card fields shared by all... },
      "variants": [ {...overrides...}, ... ],        # optional, default [{}]
      "grid": { "filters": [[], [{"type": "vwap_side"}]], "tf": [5, 15] },   # optional
      "controls": 20                                 # random controls per exit template
    }

Each variant is combined with every grid combination.  Random controls use
the random_control family with the same market, candles, session, direction,
entry and exits as the batch's cards, at a rate set so they trade about as
often as the median card; they are ranked alongside the real cards.
"""
from __future__ import annotations

import copy
import itertools
import json
from typing import Dict, List, Tuple

import numpy as np

from . import log
from .engine import run
from .evaluate import evaluate, verdict
from .spec import normalize

TEMPLATE = ("market", "tf", "session", "direction", "entry", "stop", "target", "trailing", "partial",
            "time_stop_bars", "max_trades_day", "flat")


def expand(batch: dict) -> List[dict]:
    base = batch.get("base", {})
    variants = batch.get("variants") or [{}]
    grid = batch.get("grid") or {}
    names = list(grid)
    specs = []
    for v in variants:
        for combo in itertools.product(*(grid[k] for k in names)):
            s = copy.deepcopy(base)
            s.update(copy.deepcopy(v))
            s.update({k: copy.deepcopy(x) for k, x in zip(names, combo)})
            specs.append(normalize(s))
    return specs


def _template(spec: dict) -> str:
    return json.dumps({k: spec[k] for k in TEMPLATE}, sort_keys=True)


def run_batch(batch: dict, controls: int = None, echo=print) -> List[str]:
    name = batch["name"]
    specs = expand(batch)
    ids = log.register(specs, name)
    echo(f"batch {name}: {len(specs)} cards logged ({ids[0]}..{ids[-1]}) before testing")
    trades_n: Dict[str, List[int]] = {}
    for rid, spec in zip(ids, specs):
        rec = log.get(rid)
        if rec["results"] is None:
            tr = run(spec)
            res = evaluate(tr, spec["market"])
            log.update(rid, results=res, verdict=verdict(res))
            rec = log.get(rid)
        s = rec["results"]["search"]
        echo(f"   {rid} {spec['family']:<24} {spec['market']:<7} {spec['tf']:>2}m {spec['session']:<9} "
             f"search n={s['n']:>5} {s['net_r']:+.3f}R t={s['t']:+.1f} -> {rec['verdict']}")
        total = sum(x["n"] for x in rec["results"].values())
        trades_n.setdefault(_template(spec), []).append(total)
    k = batch.get("controls", 20) if controls is None else controls
    if k:
        _controls(batch, specs, ids, trades_n, k, echo)
    log.write_board()
    return ids


def _controls(batch: dict, specs: List[dict], ids: List[str], trades_n: Dict[str, List[int]], k: int,
              echo) -> None:
    groups: Dict[str, Tuple[dict, List[str]]] = {}
    for rid, spec in zip(ids, specs):
        groups.setdefault(_template(spec), (spec, []))[1].append(rid)
    for tpl, (spec, members) in groups.items():
        want = max(1, int(np.median(trades_n[tpl])))
        probe = dict(spec, family="random_control", settings={"rate": 0.02, "seed": 0}, filters=[])
        got = max(1, sum(x["n"] for x in evaluate(run(probe), spec["market"]).values()))
        rate = float(np.clip(0.02 * want / got, 1e-4, 0.9))
        cspecs = [dict(spec, family="random_control", settings={"rate": round(rate, 5), "seed": j}, filters=[])
                  for j in range(1, k + 1)]
        cids = log.register(cspecs, batch["name"], control=True)
        ctrl = {"search": [], "confirm": []}
        for rid, cs in zip(cids, cspecs):
            rec = log.get(rid)
            if rec["results"] is None:
                res = evaluate(run(cs), cs["market"])
                log.update(rid, results=res, verdict=verdict(res))
                rec = log.get(rid)
            for p in ctrl:
                ctrl[p].append(rec["results"][p]["net_r"])
        for rid in members:
            rec = log.get(rid)
            beats = {p: float(np.mean(np.array(v) < rec["results"][p]["net_r"]) * 100) for p, v in ctrl.items()}
            log.update(rid, beats_controls=beats, verdict=verdict(rec["results"], beats))
        means = np.array(ctrl["search"])
        echo(f"   {len(cids)} random controls for {spec['market']} {spec['tf']}m {spec['session']}: search net R "
             f"a trade from {means.min():+.3f} to {means.max():+.3f} (median {np.median(means):+.3f})")
