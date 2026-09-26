"""What we learned: every trade, split by the macro regime it was taken in.

Reads the per-trade logs written by the runner (``runs/trades/*.npz``) and
the regime tags from ``macro.py``, and produces

* per strategy: trades and net R in each regime (for the inspector), the
  three named episodes, and a histogram of trade outcomes;
* across strategies: for every regime, the median strategy's net R per
  trade, the share of strategies that made money there, the median cost in
  R, and the same numbers for the random controls, so that a regime which
  lifts everything (or sinks everything) is not mistaken for skill;
* by strategy group and by market, the median edge over the controls in
  each regime (the heatmaps);
* a monthly timeline of VIX and of the pooled result of all strategies;
* plain-language findings computed from those numbers.
"""
from __future__ import annotations

import datetime as dt
import glob
import os
from collections import defaultdict
from typing import Dict, List, Optional, Sequence

import numpy as np

from .families import GROUPS, Strategy
from .macro import DIMENSIONS, EPISODES, EPOCH, episodes, tag_days
from .markets import MARKET_ORDER

HIST_EDGES = [-2.0, -1.5, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
MIN_TRADES = 30          # strategy-level floor, same as the explorer
MIN_IN_REGIME = 10       # trades a strategy needs inside a regime to be counted there


def _median(x) -> Optional[float]:
    x = [v for v in x if v is not None and not np.isnan(v)]
    return float(np.median(x)) if x else None


def load_trades(trades_dir: str) -> Dict[str, Dict[str, np.ndarray]]:
    out: Dict[str, Dict[str, np.ndarray]] = {}
    for path in sorted(glob.glob(os.path.join(trades_dir, "*.npz"))):
        if os.path.basename(path).startswith("cal_"):     # the runner's calendars
            continue
        z = np.load(path)
        sid = z["sid"]
        order = np.argsort(sid, kind="stable")
        sid = sid[order]
        cut = np.flatnonzero(np.concatenate(([True], sid[1:] != sid[:-1])))
        ends = np.append(cut[1:], sid.size)
        cols = {k: z[k][order] for k in ("day", "gross", "cost", "dir", "entry")}
        for a, b in zip(cut, ends):
            out[str(sid[a])] = {k: v[a:b] for k, v in cols.items()}
    return out


def analyse(strategies: Sequence[Strategy], results: Dict[str, dict], macro: Dict[str, object],
            trades_dir: str, start: dt.date, end: dt.date, groups: Sequence[str] = GROUPS,
            market_order: Sequence[str] = MARKET_ORDER) -> Dict[str, object]:
    trades = load_trades(trades_dir)
    d0 = (start - EPOCH).days - 5
    d1 = (end - EPOCH).days + 5
    all_days = np.arange(d0, d1 + 1)
    tags = tag_days(all_days, macro)
    epi = episodes(all_days)
    weekday = np.array([(EPOCH + dt.timedelta(days=int(d))).weekday() for d in all_days]) < 5

    per: Dict[str, dict] = {}
    rows = []   # (strategy, regime stats) for aggregation
    for s in strategies:
        t = trades.get(s.sid)
        if t is None or t["day"].size == 0:
            per[s.sid] = {"rg": {}, "ep": [[0, 0.0]] * len(EPISODES), "hist": [0] * (len(HIST_EDGES) + 1)}
            continue
        net = t["gross"] - t["cost"]
        idx = t["day"].astype(np.int64) - d0
        rg = {}
        for dim in DIMENSIONS:
            lab = tags[dim.key][idx]
            k = len(dim.order)
            ok = lab >= 0
            n = np.bincount(lab[ok], minlength=k)
            r = np.bincount(lab[ok], weights=net[ok], minlength=k)
            c = np.bincount(lab[ok], weights=t["cost"][ok], minlength=k)
            rg[dim.key] = [[int(n[j]), round(float(r[j]), 2), round(float(c[j]), 2)] for j in range(k)]
        e = epi[idx]
        ep = [[int((e == j).sum()), round(float(net[e == j].sum()), 2)] for j in range(len(EPISODES))]
        hist = np.bincount(np.searchsorted(HIST_EDGES, net, side="right"), minlength=len(HIST_EDGES) + 1)
        per[s.sid] = {"rg": {k: [v[:2] for v in vals] for k, vals in rg.items()}, "ep": ep,
                      "hist": [int(x) for x in hist]}
        rows.append((s, results.get(s.sid, {}), rg, ep, t["day"], net))

    trading = all_days[weekday]
    trading_tags = {k: v[weekday] for k, v in tags.items()}
    in_test = (trading >= (start - EPOCH).days) & (trading <= (end - EPOCH).days)

    def e_of(cell):
        n, r = cell[0], cell[1]
        return r / n if n >= MIN_IN_REGIME else None

    agg = {}
    for dim in DIMENSIONS:
        k = len(dim.order)
        lab = trading_tags[dim.key][in_test]
        days_share = [float((lab == j).mean()) for j in range(k)]
        real = [x for x in rows if x[0].group != "Control" and x[1].get("trades", 0) >= MIN_TRADES]
        ctrl = [x for x in rows if x[0].group == "Control" and x[1].get("trades", 0) >= MIN_TRADES]
        out_rows = []
        for j in range(k):
            re = [e_of(x[2][dim.key][j]) for x in real]
            ce = [e_of(x[2][dim.key][j]) for x in ctrl]
            costs = [x[2][dim.key][j][2] / x[2][dim.key][j][0] for x in real if x[2][dim.key][j][0] >= MIN_IN_REGIME]
            re_ok = [v for v in re if v is not None]
            pooled_n = sum(x[2][dim.key][j][0] for x in real)
            pooled_r = sum(x[2][dim.key][j][1] for x in real)
            cm = _median(ce)
            out_rows.append({
                "value": dim.order[j], "days": days_share[j], "strategies": len(re_ok),
                "med": _median(re_ok), "pos": (sum(v > 0 for v in re_ok) / len(re_ok)) if re_ok else None,
                "ctrl": cm, "edge": (_median(re_ok) - cm) if (re_ok and cm is not None) else None,
                "cost": _median(costs), "trades": pooled_n, "pooled": pooled_r / pooled_n if pooled_n else None,
            })
        # heatmaps: median edge over controls by group and by market
        cm_by_val = [r["ctrl"] for r in out_rows]
        by_group = []
        for g in groups:
            if g == "Control":
                continue
            xs = [x for x in real if x[0].group == g]
            vals = []
            for j in range(k):
                m = _median([e_of(x[2][dim.key][j]) for x in xs])
                vals.append(None if (m is None or cm_by_val[j] is None) else m - cm_by_val[j])
            by_group.append({"name": g, "vals": vals})
        by_market = []
        for mk in market_order:
            xs = [x for x in real if x[0].market == mk]
            cs = [x for x in ctrl if x[0].market == mk]
            vals = []
            for j in range(k):
                m = _median([e_of(x[2][dim.key][j]) for x in xs])
                c = _median([e_of(x[2][dim.key][j]) for x in cs])
                vals.append(None if (m is None or c is None) else m - c)
            by_market.append({"name": mk, "vals": vals})
        # families that do best / worst here (median net R per trade, at least 20 strategies counted)
        fam_best = []
        for j in range(k):
            f = defaultdict(list)
            for x in real:
                v = e_of(x[2][dim.key][j])
                if v is not None:
                    f[x[0].fam.name].append(v)
            ranked = sorted(((name, float(np.median(v)), len(v)) for name, v in f.items() if len(v) >= 20),
                            key=lambda t: -t[1])
            fam_best.append({"top": ranked[:3], "bottom": ranked[-3:][::-1]})
        agg[dim.key] = {"rows": out_rows, "by_group": by_group, "by_market": by_market, "families": fam_best}

    # episodes
    ep_rows = []
    real = [x for x in rows if x[0].group != "Control" and x[1].get("trades", 0) >= MIN_TRADES]
    ctrl = [x for x in rows if x[0].group == "Control" and x[1].get("trades", 0) >= MIN_TRADES]
    for j, (name, a, b) in enumerate(EPISODES):
        re = [x[3][j][1] / x[3][j][0] for x in real if x[3][j][0] >= 5]
        ce = [x[3][j][1] / x[3][j][0] for x in ctrl if x[3][j][0] >= 5]
        by_g = []
        for g in groups:
            if g == "Control":
                continue
            v = [x[3][j][1] / x[3][j][0] for x in real if x[0].group == g and x[3][j][0] >= 5]
            by_g.append([g, _median(v)])
        ep_rows.append({"name": name, "from": a, "to": b, "strategies": len(re), "med": _median(re),
                        "pos": (sum(v > 0 for v in re) / len(re)) if re else None, "ctrl": _median(ce),
                        "groups": by_g})
    overall = _median([x[1].get("net_r") for x in real])

    # monthly timeline
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    midx = {mo: i for i, mo in enumerate(months)}
    rn = np.zeros(len(months)); rr = np.zeros(len(months)); cn = np.zeros(len(months)); cr = np.zeros(len(months))
    day_month = {}
    for x in rows:
        if x[1].get("trades", 0) < MIN_TRADES:
            continue
        days, net = x[4], x[5]
        mo = np.array([day_month.setdefault(int(d), (EPOCH + dt.timedelta(days=int(d))).strftime("%Y-%m")) for d in days])
        ids = np.array([midx.get(v, -1) for v in mo])
        ok = ids >= 0
        tgt_n, tgt_r = (cn, cr) if x[0].group == "Control" else (rn, rr)
        np.add.at(tgt_n, ids[ok], 1)
        np.add.at(tgt_r, ids[ok], net[ok])
    vix = macro["series"]["vix"]
    vix_m = []
    for mo in months:
        v = [val for k, val in vix.items() if k.startswith(mo)]
        vix_m.append(round(float(np.mean(v)), 2) if v else None)
    strips = {}
    for dim in DIMENSIONS:
        if dim.key == "event":
            continue
        lab = trading_tags[dim.key]
        tm = np.array([(EPOCH + dt.timedelta(days=int(d))).strftime("%Y-%m") for d in trading])
        vals = []
        for mo in months:
            sel = lab[tm == mo]
            sel = sel[sel >= 0]
            vals.append(int(np.bincount(sel).argmax()) if sel.size else -1)
        strips[dim.key] = vals
    timeline = {
        "months": months, "vix": vix_m, "strips": strips,
        "strat": [round(rr[i] / rn[i], 4) if rn[i] else None for i in range(len(months))],
        "ctrl": [round(cr[i] / cn[i], 4) if cn[i] else None for i in range(len(months))],
        "strat_n": [int(v) for v in rn], "ctrl_n": [int(v) for v in cn],
    }

    findings = _findings(agg, ep_rows, overall, timeline)
    return {
        "per": per,
        "page": {
            "dims": [{"key": d.key, "title": d.title, "question": d.question, "order": list(d.order),
                      "note": d.note} for d in DIMENSIONS],
            "agg": agg, "episodes": ep_rows, "overall": overall, "timeline": timeline,
            "hist_edges": HIST_EDGES, "findings": findings, "groups": [g for g in groups if g != "Control"],
            "markets": list(market_order),
            "sources": {"fomc_days": len(macro["fomc"]), "nfp_days": len(macro["nfp"]),
                        "cpi_last": max(macro["cpi"]) if macro["cpi"] else None},
        },
    }


def _fmt(v, d=3):
    return "n/a" if v is None else f"{v:+.{d}f}R"


def _periods(timeline, key: str, value: int) -> str:
    """Contiguous month ranges where a regime strip holds ``value``: '2021-05 to 2023-06, ...'."""
    months, strip = timeline["months"], timeline["strips"][key]
    runs, start = [], None
    for i, v in enumerate(strip + [-99]):
        if v == value and start is None:
            start = i
        elif v != value and start is not None:
            if i - start >= 2:
                runs.append(months[start] if i - 1 == start else f"{months[start]} to {months[i - 1]}")
            start = None
    return ", ".join(runs) if runs else "no sustained stretch"


def _findings(agg, ep_rows, overall, timeline) -> List[dict]:
    out = []
    dimt = {d.key: d for d in DIMENSIONS}
    # 1. Volatility: best/worst regime for the median strategy and why (cost drag)
    v = agg["vix"]["rows"]
    lo, hi = v[0], v[-1]
    out.append({
        "tone": "good" if (hi["med"] or -9) > (lo["med"] or -9) else "warn",
        "title": "Volatility decides how much the costs hurt",
        "body": (f"With VIX under 15 the median strategy made {_fmt(lo['med'])} per trade and paid a median "
                 f"{lo['cost']:.3f}R in costs; with VIX at 30 or more it made {_fmt(hi['med'])} and paid "
                 f"{hi['cost']:.3f}R. Wider ranges mean wider stops, so the same commission and spread are a "
                 f"smaller slice of each trade. Random controls moved from {_fmt(lo['ctrl'])} to {_fmt(hi['ctrl'])}, "
                 f"so most of that shift is the market, not the setups.")})
    # 2. Which groups gain an edge in stress
    bg = agg["vix"]["by_group"]
    stress = sorted(((g["name"], g["vals"][-1]) for g in bg if g["vals"][-1] is not None), key=lambda t: -t[1])
    calm = sorted(((g["name"], g["vals"][0]) for g in bg if g["vals"][0] is not None), key=lambda t: -t[1])
    if stress and calm:
        out.append({
            "tone": "info", "title": "Different setups for calm and panic",
            "body": (f"Measured against random entries in the same regime, the best group when VIX was 30 or more was "
                     f"{stress[0][0]} ({_fmt(stress[0][1])} edge) and the weakest {stress[-1][0]} ({_fmt(stress[-1][1])}). "
                     f"With VIX under 15 the best was {calm[0][0]} ({_fmt(calm[0][1])}) and the weakest {calm[-1][0]} "
                     f"({_fmt(calm[-1][1])}).")})
    # 3. Fed cycle
    f = agg["fed"]["rows"]
    best = max((r for r in f if r["med"] is not None), key=lambda r: r["med"])
    worst = min((r for r in f if r["med"] is not None), key=lambda r: r["med"])
    out.append({
        "tone": "info", "title": "The Fed cycle mattered less than volatility",
        "body": (f"By policy cycle the median strategy ranged from {_fmt(worst['med'])} per trade ({worst['value']}) to "
                 f"{_fmt(best['med'])} ({best['value']}); edge over random stayed between "
                 f"{_fmt(min(r['edge'] for r in f if r['edge'] is not None))} and "
                 f"{_fmt(max(r['edge'] for r in f if r['edge'] is not None))}. "
                 f"Hiking months: {_periods(timeline, 'fed', 0)}. Cutting months: {_periods(timeline, 'fed', 2)}.")})
    # 4. Equity trend
    s = agg["spx"]["rows"]
    out.append({
        "tone": "info", "title": "Bear tapes paid the median strategy more than bull tapes",
        "body": (f"With the S&P 500 below its 200-day average the median strategy made {_fmt(s[1]['med'])} per trade "
                 f"({100 * (s[1]['pos'] or 0):.0f}% of strategies profitable) against {_fmt(s[0]['med'])} "
                 f"({100 * (s[0]['pos'] or 0):.0f}%) above it. Controls: {_fmt(s[1]['ctrl'])} vs {_fmt(s[0]['ctrl'])}.")
        if (s[1]["med"] or -9) > (s[0]["med"] or -9) else
        (f"With the S&P 500 above its 200-day average the median strategy made {_fmt(s[0]['med'])} per trade against "
         f"{_fmt(s[1]['med'])} below it; controls {_fmt(s[0]['ctrl'])} vs {_fmt(s[1]['ctrl'])}.")})
    if "Bear tapes" in out[-1]["title"] and (s[1]["med"] or -9) <= (s[0]["med"] or -9):
        out[-1]["title"] = "Bull tapes paid the median strategy more than bear tapes"
    # 5. Inflation
    c = agg["cpi"]["rows"]
    out.append({
        "tone": "info", "title": "Hot inflation years",
        "body": (f"When the latest CPI print was 4% or higher the median strategy made {_fmt(c[2]['med'])} per trade, "
                 f"versus {_fmt(c[0]['med'])} below 2.5% (controls {_fmt(c[2]['ctrl'])} and {_fmt(c[0]['ctrl'])}). "
                 f"CPI was 4% or more in {_periods(timeline, 'cpi', 2)}, which overlaps the 2022 bear market and "
                 f"its high VIX, so this is not an independent effect.")})
    # 6. Event days
    e = agg["event"]["rows"]
    out.append({
        "tone": "warn" if (e[1]["med"] or 0) < (e[0]["med"] or 0) else "good",
        "title": "FOMC and jobs-report days",
        "body": (f"Median net R per trade: normal days {_fmt(e[0]['med'])}, FOMC days {_fmt(e[1]['med'])}, jobs-report "
                 f"days {_fmt(e[2]['med'])}. Only strategies with at least {MIN_IN_REGIME} trades on those days count, "
                 f"so these rest on {e[1]['strategies']:,} and {e[2]['strategies']:,} strategies. Controls: "
                 f"{_fmt(e[1]['ctrl'])} and {_fmt(e[2]['ctrl'])}.")})
    # 7. Episodes
    parts = []
    for r in ep_rows:
        parts.append(f"{r['name']} ({r['from']} to {r['to']}): median {_fmt(r['med'])}, "
                     f"{100 * (r['pos'] or 0):.0f}% of strategies profitable, controls {_fmt(r['ctrl'])}")
    out.append({"tone": "info", "title": "Named episodes",
                "body": "; ".join(parts) + f". Across the whole 8 years the median was {_fmt(overall)}."})
    return out
