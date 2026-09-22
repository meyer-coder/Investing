"""Fill the template's blanks and refuse to emit a prompt with any left over."""
from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Dict, List

from .feasibility import FeasibilityReport, TRADING_DAYS_PER_YEAR
from .grid import Grid, grid_notes
from .spec import Spec

_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates",
                         "backtest_prompt.template.md")
_SLOT = re.compile(r"\{\{[A-Z_]+\}\}")


def _bullets(items: List[str]) -> str:
    return "\n".join(f"* {i}" for i in items)


def _numbered(items: List[str]) -> str:
    return "\n".join(f"{n}. {i}" for n, i in enumerate(items, 1))


def _session_clause(spec: Spec) -> str:
    s = spec.strategy
    if s.session_in_spec and s.override_session:
        return (f"**Session override.** The specification above was written for "
                f"`{s.session_in_spec}`. Ignore that restriction: test around the clock "
                f"and report the original window as one bucket among the others, so we "
                f"can see whether it was the right choice.")
    if s.session_in_spec:
        return f"**Session.** Trade only `{s.session_in_spec}`, as specified."
    return ("**Session.** The specification names no trading window, so test around "
            "the clock and let the session breakdown in §3 decide whether one matters.")


def _data_ladder(spec: Spec) -> str:
    rows = []
    for i, src in enumerate(spec.sources, 1):
        note = f" — {src.note}" if src.note else ""
        rows.append(f"{src.name}{note}")
    return _numbered(rows)


def _axes_block(spec: Spec) -> str:
    out = []
    for ax in spec.axes:
        vals = ", ".join(
            f"`{v.label}`" + (f" (≈{v.pass_rate:.0%} of signals survive)"
                              if v.pass_rate < 1.0 else "")
            for v in ax.values)
        out.append(f"* **{ax.name}** — {vals}")
    return "\n".join(out)


def _stats_block(rep: FeasibilityReport) -> str:
    s = rep.stats
    return (
        f"With {s.n_tests} variations, the expected best-of-{s.n_tests} t-statistic "
        f"under the null — that is, if every variation were worthless — is about "
        f"**{s.expected_max_t:.1f}**. A naive reading would call that highly "
        f"significant. So do not report a winner on its raw p-value. A family-wise 5% "
        f"error rate needs p < {s.bonferroni_alpha:.1e} per variation "
        f"(|z| > {s.bonferroni_z:.2f}) by Bonferroni. {s.fdr_note}. State which "
        f"correction you used and show the corrected figure next to the raw one.")


def _feasibility_block(spec: Spec, rep: FeasibilityReport) -> str:
    head = (
        f"At the assumed base rate of {spec.base_signals_per_day:g} signals per trading "
        f"day, and with roughly {rep.history_days} trading days "
        f"({rep.history_years:.1f} years) of history, "
        f"**{rep.n_feasible} of {rep.n_total}** variations can reach the "
        f"{rep.min_trades}-trade floor.")
    if rep.all_feasible:
        return (head + " The whole grid is feasible on the stated history. Re-check this "
                "against the data you actually obtain — if the history comes up short, "
                "the most selective variations fail first.")
    worst_years = rep.years_needed_for_all / 1.0
    return (
        head + f" The remaining **{rep.n_infeasible}** cannot: the most selective "
        f"variation would need about {rep.worst_required_days} trading days "
        f"({worst_years:.1f} years) to reach {rep.min_trades} trades, against the "
        f"{rep.history_days} available. Report those as `insufficient sample` and "
        f"exclude them from ranking — do not lower the floor to admit them, and do not "
        f"present their returns. This is expected: stacking filters is exactly what "
        f"makes a variation both attractive-looking and unprovable.")


def _recent_floor_clause(spec: Spec) -> str:
    w = spec.window
    if not w.emphasis_days:
        return ""
    return (
        f"The emphasis window carries its **own, lower floor of "
        f"{w.min_trades_recent} trades** — it is {w.emphasis_days} of "
        f"{spec.history_days} days, so demanding {spec.min_trades} trades inside it "
        f"would be arithmetically impossible. A variation that clears the full-window "
        f"floor but not the recent one is reported as `full window only`, and its "
        f"recent-period numbers are shown with an explicit health warning rather than "
        f"used for ranking.")


def _recency_block(spec: Spec, rep) -> str:
    w = spec.window
    if not w.emphasis_days:
        return ("No recency emphasis: every trade in the window counts equally, and "
                "results are reported on the whole period.")

    method = {
        "weighted": (
            f"**Weighted score.** Compute every metric twice — once over the full "
            f"{spec.history_days}-day window, once over the last {w.emphasis_days} days — "
            f"and rank on `{w.recent_weight:.0%} x recent + {1 - w.recent_weight:.0%} x full`. "
            f"Report both components next to the blended figure so the weighting can be "
            f"undone by eye."),
        "half_life": (
            f"**Exponential decay.** Weight each trade by `0.5 ** (age_in_days / "
            f"{w.half_life_days})`, so a trade {w.half_life_days} days old counts half as "
            f"much as today's. Report the effective sample size "
            f"(`(sum w)^2 / sum(w^2)`) alongside the raw trade count — decay shrinks it, "
            f"often by more than people expect."),
        "gate": (
            f"**Gate.** Rank on the full window, but disqualify any variation that is not "
            f"also profitable over the last {w.emphasis_days} days. Recency acts as a "
            f"filter rather than a weight."),
    }[w.method]

    parts = [
        f"The market is assumed to be changing, so the last "
        f"**{w.emphasis_months:g} months ({w.emphasis_days} trading days)** of the "
        f"{w.lookback_years:g}-year window carry extra weight.",
        "",
        method,
    ]
    if w.require_recent_positive:
        parts += ["", "A variation whose recent-window performance is negative is reported "
                      "as `regime-failed`, whatever its full-window numbers say. A strategy "
                      "that stopped working six months ago is not a strategy that works."]
    parts += [
        "",
        "**Two warnings that matter more than the weighting itself.**",
        "",
        f"1. *Recency shrinks the sample.* Only **{rep.n_feasible_recent} of "
        f"{rep.n_total}** variations produce even {w.min_trades_recent} trades inside the "
        f"emphasis window, and **{rep.n_feasible_both}** clear both floors. A variation "
        f"that looks transformed in the recent window on a few dozen trades is noise "
        f"wearing a regime-change costume. Say the trade count every single time you "
        f"quote a recent-window number.",
        f"2. *Do not both emphasise and validate on the same bars.* The out-of-sample "
        f"split in §6.2 is chronological, which means it lands on exactly the recent "
        f"period being emphasised — selecting on it and testing on it are then the same "
        f"act. Resolve it with **walk-forward**: roll the window forward in folds, apply "
        f"the recency weighting only inside each fold's training portion, and keep the "
        f"final {w.emphasis_days} days as a fold that nothing was selected on. Report "
        f"that last fold separately from everything else. If you cannot run walk-forward, "
        f"say so and treat the entire result as in-sample.",
    ]
    return "\n".join(parts)


def _seasonality(spec: Spec) -> str:
    names = {"month": "**Month to month** — calendar-month buckets pooled across years.",
             "year": "**Year to year** — one row per year, so a single exceptional year "
                     "cannot hide inside an average.",
             "day_of_week": "**Day of week** — Monday through Friday.",
             "week_of_month": "**Week of month** — including monthly option expiry weeks."}
    return _bullets([names.get(k, f"**{k}**") for k in spec.seasonality])


def _events_clause(spec: Spec) -> str:
    if not spec.events:
        return "No event study requested."
    return (
        "**Event study.** Identify the periods in the sample where volume and realised "
        "volatility spiked well above their trailing norms, and name the event behind "
        "each one (macro releases, rate decisions, elections, crises, index rebalances, "
        "expiries). Then test whether strategy performance on and around those dates "
        "differs from the rest of the sample at a level that survives the trade-count "
        "floor in §6.1. Report the correlation **with its sample size**; a relationship "
        "resting on four events is an anecdote, and should be labelled as one.")


def _session_buckets(spec: Spec) -> str:
    if spec.session_buckets:
        return _bullets([f"`{b}`" for b in spec.session_buckets])
    return _bullets([
        "Every clock hour of the 24-hour session, as its own bucket.",
        "**New York open 09:30–10:30** and **10:30–11:30**, called out separately.",
        "The London and Asia sessions as named buckets.",
    ])


def render(spec: Spec, grid: Grid, rep: FeasibilityReport, *,
           spec_path: str, manifest_path: str) -> str:
    with open(_TEMPLATE, "r", encoding="utf-8") as fh:
        text = fh.read()

    oos = int(round(spec.oos_fraction * 100))
    risk = "\n".join(f"* `{k}`: {v}" for k, v in spec.strategy.risk.items())
    target = (f"{spec.target_trades[0]}–{spec.target_trades[-1]}"
              if len(spec.target_trades) > 1 else str(spec.target_trades[0]))

    values: Dict[str, str] = {
        "STRATEGY_NAME": spec.strategy.name,
        "INSTRUMENT": spec.strategy.instrument,
        "TIMEFRAME": spec.strategy.timeframe,
        "DIRECTION": spec.strategy.direction,
        "THESIS": spec.strategy.thesis,
        "ENTRY_RULES": _bullets(spec.strategy.entry_rules),
        "EXIT_RULES": _bullets(spec.strategy.exit_rules),
        "RISK_BLOCK": risk,
        "SESSION_CLAUSE": _session_clause(spec),
        "DATA_LADDER": _data_ladder(spec),
        "HISTORY_CLAIM": f"{spec.history_days} trading days "
                         f"({spec.history_days / TRADING_DAYS_PER_YEAR:.1f} years) "
                         f"of {spec.strategy.timeframe} bars",
        "TIMEZONE": spec.timezone,
        "SESSION_BUCKETS": _session_buckets(spec),
        "SEASONALITY": _seasonality(spec),
        "EVENTS_CLAUSE": _events_clause(spec),
        "VARIATION_COUNT": str(len(grid.variations)),
        "GRID_SHAPE": "; ".join(grid_notes(spec, grid)),
        "AXES_BLOCK": _axes_block(spec),
        "MIN_TRADES": str(spec.min_trades),
        "TARGET_TRADES": target,
        "IS_PCT": str(100 - oos),
        "OOS_PCT": str(oos),
        "STATS_BLOCK": _stats_block(rep),
        "RECENCY_BLOCK": _recency_block(spec, rep),
        "RECENT_FLOOR_CLAUSE": _recent_floor_clause(spec),
        "LOOKBACK_CLAIM": f"the last {spec.window.lookback_years:g} years"
                          + (f", weighted toward the last {spec.window.emphasis_months:g} months"
                             if spec.window.emphasis_days else ""),
        "FEASIBILITY_BLOCK": _feasibility_block(spec, rep),
        "DELIVERABLES": _bullets([_deliverable(d) for d in spec.deliverables]),
        "MANIFEST_PATH": manifest_path,
        "SPEC_PATH": spec_path,
        "GENERATED_AT": _dt.date.today().isoformat(),
    }

    for key, val in values.items():
        text = text.replace("{{" + key + "}}", str(val))

    leftover = sorted(set(_SLOT.findall(text)))
    if leftover:
        raise RuntimeError(f"template has unfilled slots: {', '.join(leftover)}")
    return text


def _deliverable(name: str) -> str:
    known = {
        "pdf": "**PDF report** — the narrative: what was tested, what was found, "
               "what it means, and what would falsify it.",
        "html_dashboard": "**HTML dashboard** — one self-contained file, with the "
                          "comparative PnL chart, sortable per-variation table, and "
                          "the session/seasonality breakdowns as filterable views.",
    }
    return known.get(name, f"**{name}**")
