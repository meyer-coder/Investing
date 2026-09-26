"""Logs and the explorer.

``write_all`` produces, under ``results/``:

* ``explorer.html``          — the self-contained, sortable explorer (open it in any browser)
* ``strategies_ranked.csv``  — the same table for Excel, ranked by the recency-weighted score
* ``test_log.jsonl.gz``      — one JSON line per strategy test: definition, rules, every metric
* ``run_log.md``             — what was run, on what data, how long it took, and what it found
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from .bars import SESSIONS
from .components import LEGS
from .families import (ENTRY_TEXT, FAMILIES, FAMILY_BY_NUM, GROUPS, STOP_TEXT, TARGET_TEXT,
                       TARGETS, Strategy)
from .markets import MARKETS
from .metrics import (EVAL_DAYS, EVAL_MLL, EVAL_TARGET, FUNDED_DAYS, PAYOUT_MIN_PROFIT,
                      PAYOUT_WIN_DAYS, PAYOUT_WIN_USD, RISK_USD, SHRINK, WEIGHTS, score_of)

MIN_TRADES_FOR_STATS = 30


@dataclass
class Universe:
    """What a run covers: strategy groups and families, markets, sessions, where the trades are."""
    key: str = "run1"
    title: str = "Confluence production run"
    groups: List[str] = field(default_factory=lambda: list(GROUPS))
    families: list = field(default_factory=lambda: list(FAMILIES))
    markets: dict = field(default_factory=lambda: dict(MARKETS))
    sessions: dict = field(default_factory=lambda: dict(SESSIONS))
    trades_dir: str = os.path.join("runs", "trades")
    accounts: Optional[Dict[str, dict]] = None      # sid -> best prop account (second run)
    plans: Optional[dict] = None                    # plan key -> description
    category: Optional[Dict[str, str]] = None       # leg code -> confluence category


RUN1 = Universe()


def _f(x, nd=4):
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(xf) or math.isinf(xf):
        return None
    return round(xf, nd)


def _median(xs: Iterable[float]) -> float:
    v = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.median(v)) if v else float("nan")


def _pct(xs: Sequence[bool]) -> float:
    return 100.0 * sum(xs) / len(xs) if xs else float("nan")


# ------------------------------------------------------------------ table

def build_rows(strategies: Sequence[Strategy], results: Dict[str, dict]) -> List[dict]:
    rows = []
    for s in strategies:
        r = results.get(s.sid)
        if r is None:
            continue
        rows.append({"s": s, "r": r})
    # Random-control baseline per (market, target): median gross R/trade.
    cells = defaultdict(list)
    ctrl_t = []
    for row in rows:
        s, r = row["s"], row["r"]
        if s.group == "Control" and r["trades"] >= MIN_TRADES_FOR_STATS:
            cells[(s.market, s.target)].append(r["gross_r"])
            ctrl_t.append(r["t"])
    base = {k: float(np.median(v)) for k, v in cells.items()}
    for row in rows:
        s, r = row["s"], row["r"]
        r["score"] = score_of(r["total_r"], r["trades"], r["r3y"], r["n3y"], r["r6"], r["n6"])
        b = base.get((s.market, s.target))
        row["edge"] = (r["gross_r"] - b) if (b is not None and r["trades"] > 0) else float("nan")
        se = r.get("gsd", 0.0) / math.sqrt(r["trades"]) if r["trades"] > 1 else 0.0
        row["edge_t"] = row["edge"] / se if se > 0 and not math.isnan(row["edge"]) else float("nan")
        # Score as it stood six months ago (same weights, last 6 months removed).
        n_pre, r_pre = r["trades"] - r["n6"], r["total_r"] - r["r6"]
        n3_pre, r3_pre = r["n3y"] - r["n6"], r["r3y"] - r["r6"]
        row["score_pre"] = (WEIGHTS["8y"] * r_pre / (n_pre + SHRINK) +
                            (WEIGHTS["3y"] + WEIGHTS["6m"]) * r3_pre / (n3_pre + SHRINK))
    return rows


def control_t95(rows) -> float:
    """The luck bar: 95th percentile of the random controls' own edge t-statistic."""
    ts = [row["edge_t"] for row in rows if row["s"].group == "Control"
          and row["r"]["trades"] >= MIN_TRADES_FOR_STATS and not math.isnan(row["edge_t"])]
    return float(np.percentile(ts, 95)) if ts else 2.0


# ------------------------------------------------------------------ lessons

def lessons(rows: List[dict], meta: dict, u: Universe = RUN1) -> List[dict]:
    """Findings computed from the results — numbers, not opinions."""
    out: List[dict] = []
    real = [x for x in rows if x["s"].group != "Control"]
    ctrl = [x for x in rows if x["s"].group == "Control"]
    enough = lambda xs: [x for x in xs if x["r"]["trades"] >= MIN_TRADES_FOR_STATS]
    real_e, ctrl_e = enough(real), enough(ctrl)
    t95 = control_t95(rows)

    def net_pos(xs):
        return _pct([x["r"]["total_r"] > 0 for x in xs])

    beat = [x for x in real_e if x["edge_t"] > t95 and x["edge"] > 0]
    out.append({
        "title": "The luck baseline: random entries",
        "tone": "warn",
        "body": (f"{len(ctrl):,} coin-flip strategies were run through the same markets, sessions, stops, "
                 f"targets and costs. {net_pos(ctrl_e):.0f}% of them finished the 8 years net-profitable "
                 f"(median {_median(x['r']['net_r'] for x in ctrl_e):+.3f}R/trade). Measured against each other, the 95th "
                 f"percentile of the controls' edge t-statistic is {t95:.2f} — the bar a real strategy's edge must clear "
                 f"to look like more than luck. "
                 f"{len(beat):,} of {len(real_e):,} confluence strategies with 30+ trades clear it with a positive edge over "
                 f"the matching controls ({100 * len(beat) / max(len(real_e), 1):.1f}% vs 5% expected from luck alone)."),
    })
    g_pos = _pct([x["r"]["gross_r"] > 0 for x in real_e])
    n_pos = _pct([x["r"]["net_r"] > 0 for x in real_e])
    by_tf = defaultdict(list)
    for x in real_e:
        by_tf[x["s"].tf].append(x["r"]["cost_r"])
    tf_cost = ", ".join(f"{tf}m {np.median(v):.3f}R" for tf, v in sorted(by_tf.items()))
    out.append({
        "title": "Costs decide more than signals on low timeframes",
        "tone": "warn",
        "body": (f"Before costs {g_pos:.0f}% of strategies are profitable per trade; after commission, spread and "
                 f"slippage only {n_pos:.0f}% are. The median cost per trade, in R, by timeframe: {tf_cost}. "
                 f"A 1-minute strategy has to out-earn roughly ten times the friction of a 60-minute one."),
    })
    by_n = defaultdict(list)
    for x in real_e:
        by_n[x["s"].confluences].append(x)
    parts = []
    for k in sorted(by_n):
        xs = by_n[k]
        parts.append(f"{k} legs: {len(xs):,} strategies, median {_median(x['r']['net_r'] for x in xs):+.3f}R net, "
                     f"{_median(x['edge'] for x in xs):+.3f}R edge vs random, "
                     f"{_median(x['r']['per_week'] for x in xs):.2f} trades/week")
    out.append({
        "title": "Does stacking confluence help?",
        "tone": "info",
        "body": "Grouped by how many legs each strategy requires. " + "; ".join(parts) + ".",
    })
    # families
    fam_stats = []
    for f in u.families:
        if f.group == "Control":
            continue
        xs = [x for x in real_e if x["s"].family == f.num]
        if not xs:
            continue
        fam_stats.append((f, _median(x["edge"] for x in xs), net_pos(xs), len(xs)))
    fam_stats.sort(key=lambda t: -t[1] if not math.isnan(t[1]) else 1e9)
    if fam_stats:
        top = "; ".join(f"{f.name} ({e:+.3f}R, {p:.0f}% profitable)" for f, e, p, _ in fam_stats[:5])
        bot = "; ".join(f"{f.name} ({e:+.3f}R)" for f, e, p, _ in fam_stats[-3:])
        out.append({"title": "Families with the largest edge over random",
                    "tone": "good",
                    "body": f"Median gross edge over the matching random controls. Best: {top}. Weakest: {bot}."})
    # markets & sessions
    for dim, label in (("market", "Market"), ("session", "Session"), ("target", "Exit style")):
        agg = defaultdict(list)
        for x in real_e:
            agg[getattr(x["s"], dim)].append(x)
        items = sorted(((k, _median(x["r"]["net_r"] for x in v), net_pos(v)) for k, v in agg.items()),
                       key=lambda t: -t[1])
        txt = "; ".join(f"{k}: {m:+.3f}R median, {p:.0f}% profitable" for k, m, p in items)
        if dim == "target":
            cagg = defaultdict(list)
            for x in ctrl_e:
                cagg[x["s"].target].append(x["r"]["gross_r"])
            ctxt = ", ".join(f"{k} {np.median(v):+.3f}R" for k, v in sorted(cagg.items()))
            txt += (f". Random controls, gross, by exit: {ctxt} — exit style alone moves results, which is why "
                    f"edge is measured against controls with the same exit")
        out.append({"title": f"{label}: where the numbers were best", "tone": "info", "body": txt + "."})
    # recency persistence
    pos8 = [x for x in real_e if x["r"]["total_r"] > 0]
    both3 = [x for x in pos8 if x["r"]["r3y"] > 0]
    all3 = [x for x in both3 if x["r"]["r6"] > 0 and x["r"]["n6"] > 0]
    out.append({
        "title": "Do winners stay winners?",
        "tone": "info",
        "body": (f"{len(pos8):,} strategies were net-profitable over 8 years. {100 * len(both3) / max(len(pos8), 1):.0f}% of "
                 f"those were also profitable over the last 3 years, and {100 * len(all3) / max(len(pos8), 1):.0f}% were "
                 f"profitable in all three windows (8y, 3y, 6m). Filter 'profitable 8y + 3y + 6m' to see them."),
    })
    # honest holdout: rank six months ago, look at the next six months
    ranked = sorted([x for x in real_e if x["r"]["n6"] >= 5], key=lambda x: -x["score_pre"])
    if ranked:
        k = max(len(ranked) // 20, 10)
        top, rest = ranked[:k], ranked
        e6 = lambda xs: _median(x["r"]["e6"] for x in xs)
        p6 = lambda xs: _pct([x["r"]["r6"] > 0 for x in xs])
        cr = [x for x in ctrl_e if x["r"]["n6"] >= 5]
        out.append({
            "title": "Blind test: would the ranking have worked six months ago?",
            "tone": "good" if e6(top) > e6(rest) else "warn",
            "body": (f"Scoring every strategy with data up to 6 months ago (same 8y/3y weights) and keeping the top 5% "
                     f"({k:,} strategies): in the following 6 months their median was {e6(top):+.3f}R/trade and "
                     f"{p6(top):.0f}% made money, versus {e6(rest):+.3f}R and {p6(rest):.0f}% for all strategies and "
                     f"{e6(cr):+.3f}R / {p6(cr):.0f}% for random controls. This is the only number here that was not "
                     f"visible when the ranking was made — weigh the leaderboard by it."),
        })
    if u.accounts is not None:
        out += account_lessons(rows, u)
        return out
    # prop
    cp = [x["r"]["p_pass"] for x in ctrl_e]
    rp = [x for x in real_e if x["r"]["p_pass"] > (np.percentile(cp, 95) if cp else 1)]
    out.append({
        "title": "Prop evaluations reward variance as well as edge",
        "tone": "warn",
        "body": (f"With ${RISK_USD:.0f} risked per trade, a ${EVAL_TARGET:,.0f} target is {EVAL_TARGET / RISK_USD:.0f}R and the "
                 f"${EVAL_MLL:,.0f} trailing drawdown is {EVAL_MLL / RISK_USD:.0f}R. Random controls average "
                 f"{100 * np.mean(cp) if cp else 0:.1f}% P(pass) (95th percentile {100 * np.percentile(cp, 95) if cp else 0:.1f}%), "
                 f"because frequent trading alone gives a coin-flip a real chance to hit +12R before -8R. "
                 f"{len(rp):,} strategies beat the 95th-percentile control; judge P(pass) against that, not against zero."),
    })
    return out


def account_lessons(rows: List[dict], u: Universe) -> List[dict]:
    """What the prop-account optimiser found (second run)."""
    acc = u.accounts or {}
    plans = u.plans or {}
    real = [x for x in rows if x["s"].group != "Control" and x["s"].sid in acc]
    ctrl = [x for x in rows if x["s"].group == "Control" and x["s"].sid in acc]
    if not real:
        return []
    from .accounts import RISK_GRID as RISK_LEVELS
    ev = lambda x: acc[x["s"].sid]["best"]["ev"]
    cev = sorted(ev(x) for x in ctrl)
    bar = float(np.percentile(cev, 95)) if cev else 0.0
    pos = [x for x in real if ev(x) > 0]
    above = [x for x in real if ev(x) > bar]
    out = [{
        "title": "The luck bar for account value",
        "tone": "warn",
        "body": (f"The optimiser tries {len(plans)} plans x {len(RISK_LEVELS)} risk levels on every strategy and keeps the best, so even "
                 f"coin-flip strategies can look worth an attempt. Of {len(ctrl):,} random controls, "
                 f"{_pct([v > 0 for v in cev]):.0f}% show a positive expected value per attempt and the 95th percentile "
                 f"is {_usd_signed(bar)}. {len(pos):,} of {len(real):,} confluence strategies have a positive expected value; "
                 f"{len(above):,} ({100 * len(above) / max(len(real), 1):.1f}%) beat the controls' 95th percentile. "
                 f"Treat an account's EV as real only above that bar."),
    }]
    by_plan = defaultdict(list)
    for x in above or pos:
        by_plan[acc[x["s"].sid]["best"]["plan"]].append(x)
    items = sorted(by_plan.items(), key=lambda kv: -len(kv[1]))
    txt = "; ".join(f"{plans.get(k, {}).get('label', k)}: {len(v):,} (median EV {_usd_signed(_median(ev(x) for x in v))})"
                    for k, v in items[:8])
    out.append({"title": "Which account wins", "tone": "info",
                "body": ("Best account among strategies above the luck bar" if above else
                         "Best account among strategies with a positive EV") + f": {txt}. "
                        "Plans with daily payouts and no consistency rule (FundedNext Rapid Daily) or large payout caps "
                        "(Topstep 150K) tend to win because an attempt can lose only its fee while payouts keep coming."})
    # blind test: account chosen with data up to six months ago, last six months replayed once, in order
    bl = lambda x: acc[x["s"].sid].get("blind")
    rb = [x for x in real if bl(x)]
    cb = [x for x in ctrl if bl(x)]
    if rb and cb:
        cbar = float(np.percentile([bl(x)["ev"] for x in cb], 95))
        pick = [x for x in rb if bl(x)["ev"] > cbar]

        def summ(xs):
            if not xs:
                return "none"
            return (f"{_pct([bl(x)['outcome'] == 1 for x in xs]):.0f}% passed, "
                    f"{_pct([bl(x)['paid'] > 0 for x in xs]):.0f}% were paid, "
                    f"{_pct([bl(x)['outcome'] == -1 for x in xs]):.0f}% blew the evaluation, "
                    f"average net {_usd_signed(np.mean([bl(x)['net'] for x in xs]))} per account")
        good = pick and np.mean([bl(x)["net"] for x in pick]) > np.mean([bl(x)["net"] for x in cb])
        out.append({"title": "Blind test: pick the account six months ago, trade the last six months",
                    "tone": "good" if good else "warn",
                    "body": (f"Using only data up to six months ago (same weights, measured from that date), the optimiser chose "
                             f"each strategy's plan and risk; the last six months were then traded once, in order, from a "
                             f"fresh evaluation. {len(pick):,} confluence strategies had a pre-cut-off EV above the random "
                             f"controls' 95th percentile ({_usd_signed(cbar)}): {summ(pick)}. All {len(rb):,} confluence strategies: "
                             f"{summ(rb)}. Random controls: {summ(cb)}. Split by the sign of the EV six months ago: "
                             f"positive {summ([x for x in rb if bl(x)['ev'] > 0])}; zero or negative "
                             f"{summ([x for x in rb if bl(x)['ev'] <= 0])}. This is the only account number here that the "
                             f"choice could not see.")})
    risks = defaultdict(int)
    for x in above or pos:
        risks[acc[x["s"].sid]["best"]["risk"]] += 1
    rtxt = ", ".join(f"${int(k):,}: {v:,}" for k, v in sorted(risks.items()))
    hi = [x for x in (above or pos) if acc[x["s"].sid]["best"]["risk"] >= 500]
    out.append({"title": "More risk per trade often pays — with more blown accounts", "tone": "warn",
                "body": (f"Risk per trade chosen for the best account: {rtxt}. {len(hi):,} of those strategies do best at "
                         f"$500 or more per trade; their median chance of blowing the evaluation is "
                         f"{100 * _median(acc[x['s'].sid]['best']['p_bust'] for x in hi) if hi else 0:.0f}%. "
                         "A prop attempt's loss is capped at its fee, so the expected value can rise with risk even as "
                         "most attempts fail. Size down if you cannot afford a string of resets.")})
    return out


def _usd_signed(v: float) -> str:
    return f"{'−' if v < 0 else '+'}${abs(v):,.0f}"


def _fid(f) -> str:
    if f.group == "Control":
        return "CTRL"
    return f"{f.num - 100:02d}" if f.num >= 100 else f"{f.num:02d}"


# ------------------------------------------------------------------ explorer payload

COLS = ["id", "name", "fam", "grp", "mkt", "tf", "ses", "ent", "stp", "tgt", "xtra", "legs",
        "trades", "pw", "win", "rr", "net", "gross", "tot", "usd", "dd", "cost",
        "r12", "n12", "e3y", "n3y", "e6", "n6", "score", "uday", "dp10", "dp90",
        "edge", "t", "pf", "pp", "ppay", "green", "spre", "et", "yp", "yn",
        "acc", "risk", "ctr", "ev", "apass", "abust", "apay", "aroi", "adays", "bout", "bnet"]


def _acct_values(x: dict, u: Universe) -> list:
    a = (u.accounts or {}).get(x["s"].sid)
    if not a:
        return [None] * 11
    b, bl = a["best"], a.get("blind")
    return [b["plan"], _f(b["risk"], 0), b["contracts"], _f(b["ev"], 0), _f(b["p_pass"], 4),
            _f(b["p_bust"], 4), _f(b["p_payout"], 4), _f(b["ev"] / b["cost"], 3) if b["cost"] else None,
            _f(b["days_pass"], 1), bl["outcome"] if bl else None, _f(bl["net"], 0) if bl else None]


def _row_values(x: dict, u: Universe = RUN1) -> list:
    s, r = x["s"], x["r"]
    short = s.fam.name if s.extra is None else f"{s.fam.name} + {LEGS[s.extra].label}"
    return [s.sid, short, s.family, u.groups.index(s.group), s.market, s.tf,
            s.session, s.entry, s.stop, s.target, s.extra or "", s.confluences,
            r["trades"], _f(r["per_week"], 3), _f(r["win"], 4), _f(r["avg_rr"], 3),
            _f(r["net_r"], 4), _f(r["gross_r"], 4), _f(r["total_r"], 2), _f(r["usd"], 0),
            _f(r["max_dd"], 2), _f(r["cost_r"], 4), _f(r["r12"], 2), r["n12"],
            _f(r["e3y"], 4), r["n3y"], _f(r["e6"], 4), r["n6"], _f(r["score"], 4),
            _f(r["usd_day"], 2), _f(r["d_p10"], 0), _f(r["d_p90"], 0), _f(x["edge"], 4),
            _f(r["t"], 2), _f(r["pf"], 3), _f(r["p_pass"], 4), _f(r["p_payout"], 4),
            _f(r.get("green_days"), 3), _f(x["score_pre"], 4), _f(x["edge_t"], 2)] + list(_years_pos(r)) + \
        _acct_values(x, u)


def _years_pos(r: dict):
    """(calendar years with positive net R, calendar years with trades)."""
    yrs = (r.get("profile") or {}).get("years", {})
    traded = [v for v in yrs.values() if v[0] > 0]
    return sum(1 for v in traded if v[1] > 0), len(traded)


def _profile_values(x: dict, u: Universe = RUN1) -> dict:
    s, r = x["s"], x["r"]
    p = r.get("profile", {})
    extra = {}
    a = (u.accounts or {}).get(s.sid)
    if a:
        keys = ("plan", "risk", "p_pass", "p_bust", "p_payout", "ev", "cost", "paid_if", "pay_n", "days_pass",
                "f_bust", "contracts", "skipped")
        nd = {"risk": 0, "ev": 0, "cost": 0, "paid_if": 0, "pay_n": 2, "days_pass": 1}
        pk = lambda d: [d[k] if k in ("plan", "contracts") else _f(d[k], nd.get(k, 3)) for k in keys]
        # the per-plan table: the six best plans, seven fields (keeps the page under the size limit)
        prow = lambda d: [d["plan"], _f(d["risk"], 0), d["contracts"], _f(d["p_pass"], 2), _f(d["p_bust"], 2),
                          _f(d["p_payout"], 2), _f(d["ev"], 0)]
        plans = sorted(a["plans"], key=lambda d: -d["ev"])[:6]
        bl = a.get("blind")
        extra["acct"] = {"best": pk(a["best"]), "safe": pk(a["safe"]) if a.get("safe") else None,
                         "blind": [bl["plan"], _f(bl["risk"], 0), _f(bl["ev"], 0), bl["outcome"], _f(bl["days"], 0),
                                   _f(bl["paid"], 0), _f(bl["cost"], 0), _f(bl["net"], 0)] if bl else None,
                         "plans": [prow(d) for d in plans], "nplans": len(a["plans"]),
                         "curve": [[_f(v, 2 if i >= 2 else 0) for i, v in enumerate(c)] for c in a["curve"]]}
    eq = [round(v, 1) for v in p.get("eq", [])]
    if u.key != "run1":
        # month-end equity as deltas in tenths of R: same chart, a third of the bytes; none under 30 trades
        tenths = [int(round(v * 10)) for v in eq] if r["trades"] >= MIN_TRADES_FOR_STATS else []
        eq = [t - (tenths[i - 1] if i else 0) for i, t in enumerate(tenths)]
    return {
        "eq": eq, "yrs": p.get("years", {}), "ex": p.get("exits", []),
        "last": p.get("last", [])[-3:] if u.key != "run1" else p.get("last", []),
        "side": p.get("side", []), "dq": [round(v) for v in r.get("d_q", [])],
        "dmin": _f(r.get("d_min"), 0), "dmax": _f(r.get("d_max"), 0),
        "lg": list(s.legs), "pd": _f(r.get("pass_days"), 1),
        "u3": _f(r.get("usd_day_3y"), 2), "u6": _f(r.get("usd_day_6m"), 2),
        "best": _f(r.get("best"), 2), "worst": _f(r.get("worst"), 2), "stk": r.get("streak", 0),
        "ad": r.get("active_days", 0), "r3": _f(r.get("r3y"), 2), "r6": _f(r.get("r6"), 2),
        **extra,
    }


def payload(rows: List[dict], meta: dict, month_labels: List[str], u: Universe = RUN1) -> dict:
    fams = {f.num: {"name": f.name, "grp": u.groups.index(f.group), "thesis": f.thesis, "fid": _fid(f),
                    "legs": list(f.legs)} for f in u.families}
    used = {c for f in u.families for c in f.legs} | {c for f in u.families for c in (f.extras or ())}
    legs = {c: {"kind": l.kind, "label": l.label, "text": l.text, "cat": (u.category or {}).get(c)}
            for c, l in LEGS.items() if c in used or u.key == "run1"}
    markets = {k: {"name": m.name, "kind": m.kind, "feed": m.feed, "cost": m.cost_note,
                   "yahoo": m.yahoo, "tv": m.tradingview} for k, m in u.markets.items()}
    return {
        "cols": COLS,
        "run": u.key, "title": u.title, "eqd": u.key != "run1",
        "rows": [_row_values(x, u) for x in rows],
        "prof": [_profile_values(x, u) for x in rows],
        "fams": fams, "legs": legs, "groups": u.groups, "markets": markets, "plans": u.plans,
        "months": month_labels, "meta": meta,
        "text": {"entry": ENTRY_TEXT, "stop": STOP_TEXT, "target": TARGET_TEXT},
        "sessions": {k: [v[0], v[1], v[2]] for k, v in u.sessions.items()},
        "weights": WEIGHTS, "shrink": SHRINK, "risk": RISK_USD,
        "prop": {"target": EVAL_TARGET, "mll": EVAL_MLL, "days": EVAL_DAYS, "fdays": FUNDED_DAYS,
                 "wins": PAYOUT_WIN_DAYS, "winusd": PAYOUT_WIN_USD, "payout": PAYOUT_MIN_PROFIT},
        "t95": control_t95(rows),
        "lessons": lessons(rows, meta, u),
        **(_account_meta(rows, u) if u.accounts is not None else {}),
    }


def _account_meta(rows: List[dict], u: Universe) -> dict:
    from .accounts import RISK_GRID
    acc = u.accounts or {}
    cev = [acc[x["s"].sid]["best"]["ev"] for x in rows if x["s"].group == "Control" and x["s"].sid in acc]
    return {"evbar": float(np.percentile(cev, 95)) if cev else 0.0, "risks": list(RISK_GRID)}


# ------------------------------------------------------------------ writers

CSV_HEADER = ["rank", "id", "name", "family", "group", "market", "timeframe", "session", "entry", "stop",
              "target", "extra_filter", "confluence_legs", "trades", "trades_per_week", "win_pct", "avg_rr",
              "net_r_per_trade", "gross_r_per_trade", "total_net_r", "usd_at_250_risk", "max_dd_r", "cost_in_r",
              "last12m_net_r", "last12m_trades", "net_r_per_trade_3y", "trades_3y", "net_r_per_trade_6m",
              "trades_6m", "score", "usd_per_day_avg", "usd_per_day_p10", "usd_per_day_p90", "edge_vs_random_r",
              "t_stat", "edge_t_stat", "profit_factor", "years_positive", "years_traded", "p_pass_eval",
              "p_payout", "rules"]
ACCOUNT_HEADER = ["best_account", "risk_per_trade_usd", "contracts_median", "ev_per_attempt_usd", "account_p_pass",
                  "account_p_bust", "account_p_payout", "ev_over_cost", "median_days_to_pass",
                  "blind_replay_outcome", "blind_replay_net_usd"]


def write_csv(rows: List[dict], path: str, u: Universe = RUN1) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER + (ACCOUNT_HEADER if u.accounts is not None else []))
        for i, x in enumerate(rows, 1):
            s, r = x["s"], x["r"]
            w.writerow([i, s.sid, s.name, s.fam.name, s.group, s.market, f"{s.tf}m", s.session, s.entry,
                        s.stop, s.target, s.extra or "", s.confluences, r["trades"], _f(r["per_week"], 3),
                        _f(100 * r["win"], 1) if r["trades"] else "", _f(r["avg_rr"], 3), _f(r["net_r"], 4),
                        _f(r["gross_r"], 4), _f(r["total_r"], 2), _f(r["usd"], 0), _f(r["max_dd"], 2),
                        _f(r["cost_r"], 4), _f(r["r12"], 2), r["n12"], _f(r["e3y"], 4), r["n3y"],
                        _f(r["e6"], 4), r["n6"], _f(r["score"], 4), _f(r["usd_day"], 2), _f(r["d_p10"], 0),
                        _f(r["d_p90"], 0), _f(x["edge"], 4), _f(r["t"], 2), _f(x["edge_t"], 2), _f(r["pf"], 3),
                        *_years_pos(r),
                        _f(100 * r["p_pass"], 1), _f(100 * r["p_payout"], 1), " | ".join(s.rules())] +
                       (_acct_values(x, u) if u.accounts is not None else []))


def write_jsonl(rows: List[dict], path: str, u: Universe = RUN1) -> None:
    with gzip.open(path, "wt") as fh:
        for x in rows:
            s, r = x["s"], x["r"]
            rec = {"id": s.sid, "name": s.name, "strategy": s.to_dict(), "family": s.fam.name,
                   "thesis": s.fam.thesis, "rules": s.rules(), "edge_vs_random": _f(x["edge"]),
                   "edge_t_stat": _f(x["edge_t"])}
            rec["metrics"] = {k: (_f(v) if isinstance(v, (float, np.floating)) else v)
                              for k, v in r.items() if k not in ("profile", "d_q")}
            rec["metrics"]["daily_usd_quantiles_p5_p10_p25_p50_p75_p90_p95"] = r.get("d_q")
            rec["profile"] = r.get("profile")
            if u.accounts is not None and s.sid in u.accounts:
                rec["account"] = u.accounts[s.sid]
            fh.write(json.dumps(rec, default=float) + "\n")


def write_run_log(rows: List[dict], meta: dict, path: str, quality: dict | None, u: Universe = RUN1) -> None:
    real = [x for x in rows if x["s"].group != "Control"]
    lines = [f"# {u.title} — {meta.get('generated', '')}", "",
             f"* strategies tested: **{len(rows):,}** ({len(real):,} confluence + {len(rows) - len(real):,} random controls)",
             f"* test window: **{meta['start']} → {meta['end']}** (8 years), intraday only, flat at each session's exit",
             f"* recency weights in the score: 8y {WEIGHTS['8y']:.2f} · 3y {WEIGHTS['3y']:.2f} · 6m {WEIGHTS['6m']:.2f} "
             f"(shrinkage {SHRINK:.0f} trades)",
             f"* wall clock: {meta.get('elapsed_s', 0) / 60:.1f} min on {meta.get('workers')} workers",
             f"* total trades simulated: **{sum(x['r']['trades'] for x in rows):,}**", "",
             "## Data", "",
             "| market | feed | cost model (round trip) | proxy check vs real contract (5-min returns, last 60 days) |",
             "|---|---|---|---|"]
    for code, m in u.markets.items():
        q = (quality or {}).get(code, {})
        chk = (f"corr {q['ret_corr_5m']:.3f} vs {q['yahoo']} over {q['overlap_bars']:,} bars"
               if "ret_corr_5m" in q else q.get("error", "not run"))
        lines.append(f"| {code} | {m.feed} | {m.cost_note} | {chk} |")
    tv = (quality or {}).get("_tradingview_spotcheck") or {}
    for code, q in tv.items():
        lines.append(f"* TradingView spot check: {q['tradingview']} vs {q['feed']}, 5-min return corr "
                     f"{q['ret_corr_5m']:.4f} over {q['bars']} bars ({q['window']})")
    lines += ["", "## Top 25 by recency-weighted score (min 30 trades)", "",
              "| # | id | strategy | trades | win% | net R/tr | 3y R/tr | 6m R/tr | score | $/day | P(pass) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    top = [x for x in rows if x["r"]["trades"] >= MIN_TRADES_FOR_STATS][:25]
    for i, x in enumerate(top, 1):
        s, r = x["s"], x["r"]
        lines.append(f"| {i} | {s.sid} | {s.name} | {r['trades']} | {100 * r['win']:.0f} | {r['net_r']:+.3f} | "
                     f"{(r['e3y'] if r['n3y'] else float('nan')):+.3f} | "
                     f"{(r['e6'] if r['n6'] else float('nan')):+.3f} | {r['score']:+.3f} | {r['usd_day']:+.1f} | "
                     f"{100 * r['p_pass']:.0f}% |")
    if u.accounts is not None:
        lines += ["", "## Top 25 by expected value per prop attempt (min 30 trades)", "",
                  "| # | id | strategy | best account | risk/trade | contracts | P(pass) | P(bust) | P(payout) | EV/attempt |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        acc = [x for x in rows if x["s"].sid in u.accounts and x["r"]["trades"] >= MIN_TRADES_FOR_STATS]
        acc.sort(key=lambda x: -u.accounts[x["s"].sid]["best"]["ev"])
        for i, x in enumerate(acc[:25], 1):
            b = u.accounts[x["s"].sid]["best"]
            lines.append(f"| {i} | {x['s'].sid} | {x['s'].name} | {(u.plans or {}).get(b['plan'], {}).get('label', b['plan'])} | "
                         f"${b['risk']:,.0f} | {b['contracts']} | {100 * b['p_pass']:.0f}% | {100 * b['p_bust']:.0f}% | "
                         f"{100 * b['p_payout']:.0f}% | ${b['ev']:,.0f} |")
    lines += ["", "## Lessons", ""]
    for l in lessons(rows, meta, u):
        title = l["title"] if l["title"].endswith(("?", ".")) else l["title"] + "."
        lines += [f"**{title}** {l['body']}", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_all(strategies: Sequence[Strategy], results: Dict[str, dict], meta: dict,
              out_dir: str = "results", u: Universe = RUN1) -> None:
    from .metrics import Calendar
    os.makedirs(out_dir, exist_ok=True)
    rows = build_rows(strategies, results)
    rows.sort(key=lambda x: (x["r"]["trades"] < MIN_TRADES_FOR_STATS, -x["r"]["score"]))
    start, end = dt.date.fromisoformat(meta["start"]), dt.date.fromisoformat(meta["end"])
    labels = _month_labels(start, end)
    quality = None
    qpath = os.path.join(out_dir, "data_quality.json")
    if os.path.exists(qpath):
        with open(qpath) as fh:
            quality = json.load(fh)
    meta = dict(meta)
    meta["quality"] = quality
    write_csv(rows, os.path.join(out_dir, "strategies_ranked.csv"), u)
    write_jsonl(rows, os.path.join(out_dir, "test_log.jsonl.gz"), u)
    write_run_log(rows, meta, os.path.join(out_dir, "run_log.md"), quality, u)
    learned = _learned(strategies, results, meta, start, end, out_dir, u)
    pl = payload(rows, meta, labels, u)
    if learned:
        per = learned["per"]
        for x, prof in zip(rows, pl["prof"]):
            prof.update(_compact_regimes(per.get(x["s"].sid, {}), x["r"]["trades"]))
        pl["learned"] = learned["page"]
        _append_learned_log(os.path.join(out_dir, "run_log.md"), learned["page"])
    from .explorer_html import render
    html = render(pl)
    with open(os.path.join(out_dir, "explorer.html"), "w") as fh:
        fh.write(html)
    print(f"wrote {out_dir}/explorer.html ({len(html) / 1e6:.1f} MB), strategies_ranked.csv, "
          f"test_log.jsonl.gz, run_log.md", flush=True)


INSPECTOR_REGIMES = ("vix", "fed", "spx", "cpi", "event")     # the regime blocks the inspector draws


def _compact_regimes(per: dict, trades: int) -> dict:
    """Only what the inspector shows, at 0.1R: keeps a 20k-strategy page under the artifact size limit."""
    if not per:
        return {}
    out = {"hist": per.get("hist", [])}
    if trades >= MIN_TRADES_FOR_STATS:
        out["rg"] = {k: [[n, round(r, 1)] for n, r in v] for k, v in per.get("rg", {}).items() if k in INSPECTOR_REGIMES}
        out["ep"] = [[n, round(r, 1)] for n, r in per.get("ep", [])]
    return out


def _learned(strategies, results, meta, start: dt.date, end: dt.date, out_dir: str, u: Universe = RUN1):
    """Macro-regime analysis for the 'What we learned' page (skipped if trades or macro data are missing)."""
    trades_dir = u.trades_dir
    if not os.path.isdir(trades_dir):
        print(f"what we learned: no per-trade logs in {trades_dir}, skipping the macro page", flush=True)
        return None
    try:
        from .insights import analyse
        from .macro import DIMENSIONS, fetch_all, tag_days
        macro = fetch_all(dt.date(start.year - 1, 1, 1), end)
    except Exception as exc:  # noqa: BLE001 - the explorer still builds without it
        print(f"what we learned: macro data unavailable ({exc}); skipping the macro page", flush=True)
        return None
    learned = analyse(strategies, results, macro, trades_dir, start, end, u.groups, list(u.markets))
    # The daily regime table, for anyone who wants to check a tag.
    days = np.arange((start - dt.date(1970, 1, 1)).days, (end - dt.date(1970, 1, 1)).days + 1)
    tags = tag_days(days, macro)
    with open(os.path.join(out_dir, "macro_regimes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date"] + [d.key for d in DIMENSIONS])
        for i, d in enumerate(days):
            day = dt.date(1970, 1, 1) + dt.timedelta(days=int(d))
            if day.weekday() >= 5:
                continue
            w.writerow([day.isoformat()] + [d_.order[tags[d_.key][i]] if tags[d_.key][i] >= 0 else ""
                                            for d_ in DIMENSIONS])
    return learned


def _append_learned_log(path: str, page: dict) -> None:
    lines = ["", "## What we learned: results by macro regime", "",
             "Median net R per trade across confluence strategies (30+ trades overall, 10+ in the regime), "
             "with the random controls alongside.", ""]
    for d in page["dims"]:
        lines += [f"**{d['title']}** ({d['note']})", "", "| regime | days | strategies | median R/trade | controls | edge | cost R |",
                  "|---|---|---|---|---|---|---|"]
        for r in page["agg"][d["key"]]["rows"]:
            sg = lambda v: "n/a" if v is None else f"{v:+.3f}"
            cost = "n/a" if r["cost"] is None else f"{r['cost']:.3f}"
            lines.append(f"| {r['value']} | {100 * r['days']:.0f}% | {r['strategies']:,} | {sg(r['med'])} | "
                         f"{sg(r['ctrl'])} | {sg(r['edge'])} | {cost} |")
        lines.append("")
    for fnd in page["findings"]:
        lines += [f"**{fnd['title']}.** {fnd['body']}", ""]
    with open(path, "a") as fh:
        fh.write("\n".join(lines) + "\n")


def _month_labels(start: dt.date, end: dt.date) -> List[str]:
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out
