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
from typing import Dict, Iterable, List, Sequence

import numpy as np

from .bars import SESSIONS
from .components import LEGS
from .families import (ENTRY_TEXT, FAMILIES, FAMILY_BY_NUM, GROUPS, STOP_TEXT, TARGET_TEXT,
                       TARGETS, Strategy)
from .markets import MARKETS
from .metrics import (EVAL_DAYS, EVAL_MLL, EVAL_TARGET, FUNDED_DAYS, PAYOUT_MIN_PROFIT,
                      PAYOUT_WIN_DAYS, PAYOUT_WIN_USD, RISK_USD, SHRINK, WEIGHTS, score_of)

MIN_TRADES_FOR_STATS = 30


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

def lessons(rows: List[dict], meta: dict) -> List[dict]:
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
    for f in FAMILIES:
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


# ------------------------------------------------------------------ explorer payload

COLS = ["id", "name", "fam", "grp", "mkt", "tf", "ses", "ent", "stp", "tgt", "xtra", "legs",
        "trades", "pw", "win", "rr", "net", "gross", "tot", "usd", "dd", "cost",
        "r12", "n12", "e3y", "n3y", "e6", "n6", "score", "uday", "dp10", "dp90",
        "edge", "t", "pf", "pp", "ppay", "green", "spre", "et", "yp", "yn"]


def _row_values(x: dict) -> list:
    s, r = x["s"], x["r"]
    short = s.fam.name if s.extra is None else f"{s.fam.name} + {LEGS[s.extra].label}"
    return [s.sid, short, s.family, GROUPS.index(s.group), s.market, s.tf,
            s.session, s.entry, s.stop, s.target, s.extra or "", s.confluences,
            r["trades"], _f(r["per_week"], 3), _f(r["win"], 4), _f(r["avg_rr"], 3),
            _f(r["net_r"], 4), _f(r["gross_r"], 4), _f(r["total_r"], 2), _f(r["usd"], 0),
            _f(r["max_dd"], 2), _f(r["cost_r"], 4), _f(r["r12"], 2), r["n12"],
            _f(r["e3y"], 4), r["n3y"], _f(r["e6"], 4), r["n6"], _f(r["score"], 4),
            _f(r["usd_day"], 2), _f(r["d_p10"], 0), _f(r["d_p90"], 0), _f(x["edge"], 4),
            _f(r["t"], 2), _f(r["pf"], 3), _f(r["p_pass"], 4), _f(r["p_payout"], 4),
            _f(r.get("green_days"), 3), _f(x["score_pre"], 4), _f(x["edge_t"], 2)] + list(_years_pos(r))


def _years_pos(r: dict):
    """(calendar years with positive net R, calendar years with trades)."""
    yrs = (r.get("profile") or {}).get("years", {})
    traded = [v for v in yrs.values() if v[0] > 0]
    return sum(1 for v in traded if v[1] > 0), len(traded)


def _profile_values(x: dict) -> dict:
    s, r = x["s"], x["r"]
    p = r.get("profile", {})
    eq = [round(v, 1) for v in p.get("eq", [])]
    return {
        "eq": eq, "yrs": p.get("years", {}), "ex": p.get("exits", []), "last": p.get("last", []),
        "side": p.get("side", []), "dq": [round(v) for v in r.get("d_q", [])],
        "dmin": _f(r.get("d_min"), 0), "dmax": _f(r.get("d_max"), 0),
        "lg": list(s.legs), "pd": _f(r.get("pass_days"), 1),
        "u3": _f(r.get("usd_day_3y"), 2), "u6": _f(r.get("usd_day_6m"), 2),
        "best": _f(r.get("best"), 2), "worst": _f(r.get("worst"), 2), "stk": r.get("streak", 0),
        "ad": r.get("active_days", 0), "r3": _f(r.get("r3y"), 2), "r6": _f(r.get("r6"), 2),
    }


def payload(rows: List[dict], meta: dict, month_labels: List[str]) -> dict:
    fams = {f.num: {"name": f.name, "grp": GROUPS.index(f.group), "thesis": f.thesis, "fid": f.fid,
                    "legs": list(f.legs)} for f in FAMILIES}
    legs = {c: {"kind": l.kind, "label": l.label, "text": l.text} for c, l in LEGS.items()}
    markets = {k: {"name": m.name, "kind": m.kind, "feed": m.feed, "cost": m.cost_note,
                   "yahoo": m.yahoo, "tv": m.tradingview} for k, m in MARKETS.items()}
    return {
        "cols": COLS,
        "rows": [_row_values(x) for x in rows],
        "prof": [_profile_values(x) for x in rows],
        "fams": fams, "legs": legs, "groups": GROUPS, "markets": markets,
        "months": month_labels, "meta": meta,
        "text": {"entry": ENTRY_TEXT, "stop": STOP_TEXT, "target": TARGET_TEXT},
        "sessions": {k: [v[0], v[1], v[2]] for k, v in SESSIONS.items()},
        "weights": WEIGHTS, "shrink": SHRINK, "risk": RISK_USD,
        "prop": {"target": EVAL_TARGET, "mll": EVAL_MLL, "days": EVAL_DAYS, "fdays": FUNDED_DAYS,
                 "wins": PAYOUT_WIN_DAYS, "winusd": PAYOUT_WIN_USD, "payout": PAYOUT_MIN_PROFIT},
        "t95": control_t95(rows),
        "lessons": lessons(rows, meta),
    }


# ------------------------------------------------------------------ writers

CSV_HEADER = ["rank", "id", "name", "family", "group", "market", "timeframe", "session", "entry", "stop",
              "target", "extra_filter", "confluence_legs", "trades", "trades_per_week", "win_pct", "avg_rr",
              "net_r_per_trade", "gross_r_per_trade", "total_net_r", "usd_at_250_risk", "max_dd_r", "cost_in_r",
              "last12m_net_r", "last12m_trades", "net_r_per_trade_3y", "trades_3y", "net_r_per_trade_6m",
              "trades_6m", "score", "usd_per_day_avg", "usd_per_day_p10", "usd_per_day_p90", "edge_vs_random_r",
              "t_stat", "edge_t_stat", "profit_factor", "years_positive", "years_traded", "p_pass_eval",
              "p_payout", "rules"]


def write_csv(rows: List[dict], path: str) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
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
                        _f(100 * r["p_pass"], 1), _f(100 * r["p_payout"], 1), " | ".join(s.rules())])


def write_jsonl(rows: List[dict], path: str) -> None:
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
            fh.write(json.dumps(rec, default=float) + "\n")


def write_run_log(rows: List[dict], meta: dict, path: str, quality: dict | None) -> None:
    real = [x for x in rows if x["s"].group != "Control"]
    lines = [f"# Confluence production run — {meta.get('generated', '')}", "",
             f"* strategies tested: **{len(rows):,}** ({len(real):,} confluence + {len(rows) - len(real):,} random controls)",
             f"* test window: **{meta['start']} → {meta['end']}** (8 years), intraday only, flat at each session's exit",
             f"* recency weights in the score: 8y {WEIGHTS['8y']:.2f} · 3y {WEIGHTS['3y']:.2f} · 6m {WEIGHTS['6m']:.2f} "
             f"(shrinkage {SHRINK:.0f} trades)",
             f"* wall clock: {meta.get('elapsed_s', 0) / 60:.1f} min on {meta.get('workers')} workers",
             f"* total trades simulated: **{sum(x['r']['trades'] for x in rows):,}**", "",
             "## Data", "",
             "| market | feed | cost model (round trip) | proxy check vs real contract (5-min returns, last 60 days) |",
             "|---|---|---|---|"]
    for code, m in MARKETS.items():
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
    lines += ["", "## Lessons", ""]
    for l in lessons(rows, meta):
        title = l["title"] if l["title"].endswith(("?", ".")) else l["title"] + "."
        lines += [f"**{title}** {l['body']}", ""]
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


def write_all(strategies: Sequence[Strategy], results: Dict[str, dict], meta: dict,
              out_dir: str = "results") -> None:
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
    write_csv(rows, os.path.join(out_dir, "strategies_ranked.csv"))
    write_jsonl(rows, os.path.join(out_dir, "test_log.jsonl.gz"))
    write_run_log(rows, meta, os.path.join(out_dir, "run_log.md"), quality)
    from .explorer_html import render
    html = render(payload(rows, meta, labels))
    with open(os.path.join(out_dir, "explorer.html"), "w") as fh:
        fh.write(html)
    print(f"wrote {out_dir}/explorer.html ({len(html) / 1e6:.1f} MB), strategies_ranked.csv, "
          f"test_log.jsonl.gz, run_log.md", flush=True)


def _month_labels(start: dt.date, end: dt.date) -> List[str]:
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out
