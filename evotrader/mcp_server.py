"""MCP server: a live view of a training run, for Claude Code and other clients.

An evolution run is a long-lived process that writes everything it learns to
SQLite.  This module serves that record over the Model Context Protocol, so a
Claude Code session can watch training as it happens — where fitness is, what
the champion's rules are, how it actually traded, what Claude said when it bred
the last generation, and whether the held-out window agrees with any of it.

The view is read-only.  Nothing here starts, steers or stops a run; the one
tool that computes, ``backtest_genome``, replays a stored genome over a window
you choose and writes nothing back.

Start it with ``evotrader mcp`` (or ``python -m evotrader.mcp_server``) and
point a client at it::

    {"mcpServers": {"evotrader": {"command": "python3",
                                  "args": ["-m", "evotrader.mcp_server"]}}}

The protocol is spoken directly — newline-delimited JSON-RPC 2.0 over stdin and
stdout — so the server needs nothing beyond this package.  Only protocol
messages may go to stdout; diagnostics go to stderr.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO, Tuple

from .config import EvolutionConfig
from .fitness import Metrics
from .prompts import genome_schema_text, rule_reference
from .report import lineage, markdown_report, sparkline
from .store import Store

SERVER_NAME = "evotrader-training-view"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = """\
A read-only window onto evotrader training runs: populations of paper-trading
agents evolved over generations, with Claude breeding each generation from the
last one's winners.

Start with `training_status` for the run's current state, then `leaderboard`
and `inspect_genome` for the agents themselves, `genome_trades` for how one
traded, and `reflections` for Claude's own analysis of each generation.

Two things are worth saying out loud whenever you report on a run:
fitness on the training window is an in-sample number, and the held-out window
(the last slice of history, never used for selection) is the only one that
carries any evidence. `overfitting_report` puts the two side by side. A
champion is a hypothesis, not a signal worth trading.
"""

# Every tool takes an optional database path so one server can serve several runs.
_DB_PROPERTY = {
    "type": "string",
    "description": "SQLite path (default: $EVOTRADER_DB, else runs/evotrader.sqlite)",
}
_RUN_PROPERTY = {
    "type": "string",
    "description": "run id (default: the most recently updated run)",
}

_METRIC_FIELDS = {f.name for f in dataclasses.fields(Metrics)}


class ViewError(RuntimeError):
    """A problem the caller can fix: unknown run, missing database, bad argument."""


# --------------------------------------------------------------- tool registry

ToolResult = Tuple[str, Dict[str, Any]]
Handler = Callable[["TrainingView", Dict[str, Any]], ToolResult]


@dataclass
class Tool:
    name: str
    title: str
    description: str
    schema: Dict[str, Any]
    handler: Handler

    def spec(self) -> Dict[str, Any]:
        return {"name": self.name, "title": self.title,
                "description": self.description, "inputSchema": self.schema,
                "annotations": {"readOnlyHint": True, "openWorldHint": False}}


TOOLS: Dict[str, Tool] = {}


def tool(name: str, title: str, description: str,
         properties: Optional[Dict[str, Any]] = None,
         required: Sequence[str] = ()) -> Callable[[Handler], Handler]:
    """Register one tool.  ``db`` is appended to every schema."""

    def decorate(fn: Handler) -> Handler:
        props = dict(properties or {})
        props.setdefault("db", _DB_PROPERTY)
        TOOLS[name] = Tool(name, title, description,
                           {"type": "object", "properties": props,
                            "required": list(required)}, fn)
        return fn

    return decorate


# ------------------------------------------------------------ argument helpers

def _str_arg(args: Dict[str, Any], key: str, default: str = "") -> str:
    value = args.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ViewError(f"{key} must be a string")
    return value.strip()


def _required_str(args: Dict[str, Any], key: str) -> str:
    value = _str_arg(args, key)
    if not value:
        raise ViewError(f"{key} is required")
    return value


def _int_arg(args: Dict[str, Any], key: str, default: int, *,
             lo: int = 1, hi: int = 500) -> int:
    value = args.get(key, default)
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ViewError(f"{key} must be a whole number") from None
    return max(lo, min(hi, n))


def _choice_arg(args: Dict[str, Any], key: str, allowed: Sequence[str]) -> str:
    value = _str_arg(args, key, allowed[0]) or allowed[0]
    if value not in allowed:
        raise ViewError(f"{key} must be one of {', '.join(allowed)}")
    return value


# ----------------------------------------------------------------- formatting

def _metrics_dict(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _metrics_line(raw: Optional[str]) -> str:
    d = _metrics_dict(raw)
    if not d:
        return "-"
    return Metrics(**{k: v for k, v in d.items() if k in _METRIC_FIELDS}).summary()


def _score(value: Optional[float]) -> str:
    return f"{value:+.3f}" if value is not None and math.isfinite(value) else "  -   "


def _age(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f}s ago"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m ago"
    if seconds < 172800:
        return f"{seconds / 3600:.1f}h ago"
    return f"{seconds / 86400:.1f}d ago"


def _clip(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


# -------------------------------------------------------------- the view state

class TrainingView:
    """Opens (and reuses) one :class:`Store` per database path."""

    def __init__(self, db_path: str = ""):
        self.db_path = (db_path or os.environ.get("EVOTRADER_DB")
                        or EvolutionConfig().db_path)
        self._stores: Dict[str, Store] = {}

    def store(self, args: Optional[Dict[str, Any]] = None) -> Store:
        path = _str_arg(args or {}, "db") or self.db_path
        if path not in self._stores:
            if not os.path.exists(path):
                raise ViewError(f"no evotrader database at {path!r} — run "
                                f"`evotrader run` first, or pass db=<path>")
            # WAL means a reader sees a run's writes as they land.
            self._stores[path] = Store(path)
        return self._stores[path]

    def resolve_run(self, store: Store, run_id: str = "") -> str:
        if run_id:
            if store.get_run(run_id) is None:
                known = ", ".join(r["id"] for r in store.list_runs(5)) or "none"
                raise ViewError(f"unknown run {run_id!r}; known runs: {known}")
            return run_id
        rows = store.list_runs(1)
        if not rows:
            raise ViewError("this database has no runs yet")
        return rows[0]["id"]

    def close(self) -> None:
        for store in self._stores.values():
            try:
                store.close()
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass
        self._stores.clear()


def _run_cost(store: Store, run_id: str) -> float:
    row = store.conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM generations WHERE run_id=?",
        (run_id,)).fetchone()
    return float(row[0] or 0.0)


def _history(store: Store, run_id: str) -> List[Dict[str, Any]]:
    """Per-generation scores, with the held-out score of that generation's best."""
    sql = ("SELECT g.generation, g.best_score, g.mean_score, g.median_score,"
           " g.best_genome_id, g.cost_usd, g.elapsed_s,"
           " (SELECT name FROM genomes n WHERE n.id = g.best_genome_id) AS best_name,"
           " (SELECT test_score FROM evaluations e WHERE e.run_id = g.run_id"
           "  AND e.genome_id = g.best_genome_id AND e.generation = g.generation)"
           "  AS best_test_score"
           " FROM generations g WHERE g.run_id=? ORDER BY g.generation")
    return [dict(r) for r in store.conn.execute(sql, (run_id,)).fetchall()]


# ----------------------------------------------------------------- the tools

@tool("list_runs", "List runs",
      "Every evolution run in the database, newest first: status, generations "
      "completed, population, breeder and what it has spent on Claude so far.",
      {"limit": {"type": "integer", "description": "how many runs (default 20)"}})
def _list_runs(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    rows = store.list_runs(_int_arg(args, "limit", 20, hi=200))
    if not rows:
        return "no runs in this database yet", {"runs": []}
    now = time.time()
    runs, lines = [], []
    for row in rows:
        cfg = json.loads(row["config"])
        cost = _run_cost(store, row["id"])
        runs.append({
            "run_id": row["id"], "status": row["status"],
            "generations_done": row["generations"] or 0,
            "generations_planned": cfg.get("generations"),
            "population": cfg.get("population"), "breeder": cfg.get("breeder"),
            "model": cfg.get("model"), "symbols": cfg.get("symbols", []),
            "cost_usd": round(cost, 4), "note": row["note"],
            "updated_age_s": round(now - float(row["updated_at"] or now), 1),
        })
        lines.append(
            f"{row['id']}  {row['status']:<9} "
            f"gen {row['generations'] or 0:>4}/{cfg.get('generations', '?'):<5} "
            f"pop {cfg.get('population', '?'):<4} {cfg.get('breeder', '?'):<8} "
            f"${cost:>7.2f}  {_age(now - float(row['updated_at'] or now)):<9} "
            f"{(row['note'] or '')[:32]}")
    return "\n".join(lines), {"runs": runs}


@tool("training_status", "Training status",
      "Where a run stands right now: generations done, fitness trend, the "
      "current champion on both windows, spend against budget, and Claude's "
      "most recent analysis. The first call to make on any run.",
      {"run_id": _RUN_PROPERTY})
def _training_status(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    run = store.get_run(run_id)
    cfg = json.loads(run["config"])
    history = _history(store, run_id)
    cost = _run_cost(store, run_id)
    age = time.time() - float(run["updated_at"] or time.time())
    board = store.leaderboard(run_id, limit=1)
    champion = board[0] if board else None

    best = [h["best_score"] for h in history if h["best_score"] is not None]
    mean = [h["mean_score"] for h in history if h["mean_score"] is not None]
    scored = [h for h in history if h["best_score"] is not None]
    peak_row = max(scored, key=lambda h: h["best_score"]) if scored else None
    peak = peak_row["best_score"] if peak_row else None
    peak_gen = peak_row["generation"] if peak_row else None

    lines = [f"run {run_id}  [{run['status']}]{('  ' + run['note']) if run['note'] else ''}",
             f"  {len(history)}/{cfg.get('generations', '?')} generations · "
             f"{cfg.get('population', '?')} agents · breeder {cfg.get('breeder')} · "
             f"model {cfg.get('model')}",
             f"  {cfg.get('start')}..{cfg.get('end')} on "
             f"{','.join(cfg.get('symbols', [])[:8])}"
             f"{'...' if len(cfg.get('symbols', [])) > 8 else ''} "
             f"(last {cfg.get('test_frac', 0) * 100:.0f}% held out)",
             f"  spend ${cost:.2f}"
             + (f" of ${cfg['budget_usd']:.2f}" if cfg.get("budget_usd") else "")
             + f" · last write {_age(age)}"]
    if run["status"] == "running" and age > 600:
        lines.append(f"  note: status says running but nothing has been written in "
                     f"{_age(age)} — the run may have died")
    if best:
        lines.append(f"  best fitness  {sparkline(best)}  {best[0]:+.2f} -> {best[-1]:+.2f}"
                     f"  (peak {peak:+.2f} at gen {peak_gen})")
    if mean:
        lines.append(f"  mean fitness  {sparkline(mean)}  {mean[0]:+.2f} -> {mean[-1]:+.2f}")
    if champion:
        lines.append(f"\n  champion {champion['name']} (id={champion['genome_id']}, "
                     f"gen {champion['gen']}, {champion['origin']}) "
                     f"fitness {champion['score']:+.3f}")
        lines.append(f"    training  {_metrics_line(champion['metrics'])}")
        lines.append(f"    held-out  {_metrics_line(champion['test_metrics'])}"
                     if champion["test_metrics"] else
                     "    held-out  not scored on the held-out window")

    reflections = store.generation_reflections(run_id, limit=1)
    if reflections:
        lines.append(f"\n  Claude after generation {reflections[0]['generation']}:")
        lines.append("    " + _clip(reflections[0]["analysis"], 700).replace("\n", "\n    "))

    structured = {
        "run_id": run_id, "status": run["status"], "note": run["note"],
        "generations_done": len(history),
        "generations_planned": cfg.get("generations"),
        "population": cfg.get("population"), "breeder": cfg.get("breeder"),
        "model": cfg.get("model"), "symbols": cfg.get("symbols", []),
        "window": {"start": cfg.get("start"), "end": cfg.get("end"),
                   "test_frac": cfg.get("test_frac")},
        "cost_usd": round(cost, 4), "budget_usd": cfg.get("budget_usd"),
        "seconds_since_write": round(age, 1),
        "stalled": bool(run["status"] == "running" and age > 600),
        "best_score_latest": best[-1] if best else None,
        "best_score_peak": peak, "best_score_peak_generation": peak_gen,
        "mean_score_latest": mean[-1] if mean else None,
        "champion": {
            "genome_id": champion["genome_id"], "name": champion["name"],
            "generation": champion["gen"], "origin": champion["origin"],
            "score": champion["score"], "test_score": champion["test_score"],
            "metrics": _metrics_dict(champion["metrics"]),
            "test_metrics": _metrics_dict(champion["test_metrics"]),
        } if champion else None,
        "latest_analysis": reflections[0] if reflections else None,
    }
    return "\n".join(lines), structured


@tool("generation_history", "Generation history",
      "Fitness by generation: best, mean and median on the training window, "
      "plus the held-out score of each generation's champion. Read the two "
      "series together — training climbing while held-out does not is "
      "overfitting happening in real time.",
      {"run_id": _RUN_PROPERTY,
       "limit": {"type": "integer",
                 "description": "most recent N generations (default 40)"}})
def _generation_history(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    rows = _history(store, run_id)
    rows = rows[-_int_arg(args, "limit", 40, hi=1000):]
    if not rows:
        return f"run {run_id} has no completed generations yet", {
            "run_id": run_id, "generations": []}
    lines = [f"run {run_id} — last {len(rows)} generations",
             "  gen |    best |    mean |  median | held-out | cost   | champion"]
    for r in rows:
        lines.append(
            f"  {r['generation']:>3} | {_score(r['best_score'])} | "
            f"{_score(r['mean_score'])} | {_score(r['median_score'])} | "
            f"{_score(r['best_test_score']):>8} | "
            f"${r['cost_usd'] or 0:>5.2f} | {(r['best_name'] or '')[:34]}")
    best = [r["best_score"] for r in rows if r["best_score"] is not None]
    if len(best) > 1:
        lines.append(f"\n  best {sparkline(best)} {best[0]:+.2f} -> {best[-1]:+.2f}")
    return "\n".join(lines), {"run_id": run_id, "generations": rows}


@tool("leaderboard", "Leaderboard",
      "The best distinct strategies of a run, ranked on the training window or "
      "on the held-out window. One row per strategy: an elite carried across "
      "generations appears once.",
      {"run_id": _RUN_PROPERTY,
       "limit": {"type": "integer", "description": "rows to return (default 10)"},
       "rank_by": {"type": "string", "enum": ["train", "holdout"],
                   "description": "which window to rank on (default train)"}})
def _leaderboard(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    rank_by = _choice_arg(args, "rank_by", ["train", "holdout"])
    limit = _int_arg(args, "limit", 10, hi=100)
    rows = store.leaderboard(run_id, limit=limit, by_test=(rank_by == "holdout"))
    if not rows:
        return f"run {run_id} has no scored genomes yet", {"run_id": run_id, "rows": []}
    window = "held-out" if rank_by == "holdout" else "training"
    lines = [f"run {run_id} — top {len(rows)} by {window} fitness"]
    out = []
    for r in rows:
        primary = r["test_score"] if rank_by == "holdout" else r["score"]
        metrics = r["test_metrics"] if rank_by == "holdout" else r["metrics"]
        lines.append(f"  {_score(primary)}  gen {r['gen']:>4}  {r['name'][:30]:<30} "
                     f"{r['genome_id']}  {_metrics_line(metrics)}")
        out.append({"genome_id": r["genome_id"], "name": r["name"],
                    "generation": r["gen"], "origin": r["origin"],
                    "score": r["score"], "test_score": r["test_score"],
                    "metrics": _metrics_dict(r["metrics"]),
                    "test_metrics": _metrics_dict(r["test_metrics"])})
    if rank_by == "train":
        lines.append("\n  training fitness is in-sample; check `overfitting_report` "
                     "before believing any of it")
    return "\n".join(lines), {"run_id": run_id, "rank_by": rank_by, "rows": out}


@tool("inspect_genome", "Inspect an agent",
      "One agent in full: its thesis, entry and exit rules, risk limits, why "
      "Claude wrote it, how it scored on each window, and its ancestry back "
      "towards generation 0.",
      {"genome_id": {"type": "string", "description": "genome id, as shown on the leaderboard"},
       "ancestry": {"type": "integer",
                    "description": "how many ancestors to walk back (default 8, 0 to skip)"}},
      required=["genome_id"])
def _inspect_genome(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    genome_id = _required_str(args, "genome_id")
    genome = store.get_genome(genome_id)
    if genome is None:
        raise ViewError(f"unknown genome {genome_id!r}")
    lines = [genome.describe()]
    if genome.rationale:
        lines.append(f"  rationale: {genome.rationale}")

    evals = [dict(r) for r in store.conn.execute(
        "SELECT * FROM evaluations WHERE genome_id=? ORDER BY generation",
        (genome_id,)).fetchall()]
    for row in evals:
        lines.append(f"\n  generation {row['generation']}: fitness {_score(row['score'])}"
                     + (f" (held-out {_score(row['test_score'])})"
                        if row["test_score"] is not None else ""))
        lines.append(f"    training  {_metrics_line(row['metrics'])}")
        if row["test_metrics"]:
            lines.append(f"    held-out  {_metrics_line(row['test_metrics'])}")
        if row["error"]:
            lines.append(f"    error: {row['error']}")

    depth = _int_arg(args, "ancestry", 8, lo=0, hi=40)
    chain = lineage(store, genome_id, max_depth=max(depth, 1))[:depth] if depth else []
    if len(chain) > 1:
        lines.append("\n  ancestry (newest first)")
        for g in chain:
            lines.append(f"    gen {g.generation:>4} {g.origin:<9} "
                         f"{g.name[:36]:<36} {g.id}")
    return "\n".join(lines), {
        "genome": genome.to_dict(),
        "describe": genome.describe(),
        "evaluations": [{
            "run_id": r["run_id"], "generation": r["generation"],
            "score": r["score"], "test_score": r["test_score"],
            "metrics": _metrics_dict(r["metrics"]),
            "test_metrics": _metrics_dict(r["test_metrics"]),
            "error": r["error"]} for r in evals],
        "ancestry": [{"id": g.id, "generation": g.generation, "origin": g.origin,
                      "name": g.name} for g in chain],
    }


@tool("genome_trades", "Trade journal",
      "The trades one agent actually made, with the rule that fired on the way "
      "in and on the way out. Sort by return to see what the edge really was, "
      "or where it broke.",
      {"genome_id": {"type": "string", "description": "genome id"},
       "limit": {"type": "integer", "description": "trades to return (default 20)"},
       "order": {"type": "string", "enum": ["sequence", "best", "worst"],
                 "description": "chronological, most profitable, or worst first"}},
      required=["genome_id"])
def _genome_trades(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    genome_id = _required_str(args, "genome_id")
    order = _choice_arg(args, "order", ["sequence", "best", "worst"])
    limit = _int_arg(args, "limit", 20, hi=200)
    clause = {"sequence": "generation, seq", "best": "ret DESC", "worst": "ret ASC"}[order]
    rows = [dict(r) for r in store.conn.execute(
        f"SELECT * FROM trades WHERE genome_id=? ORDER BY {clause} LIMIT ?",
        (genome_id, limit)).fetchall()]
    if not rows:
        if store.get_genome(genome_id) is None:
            raise ViewError(f"unknown genome {genome_id!r}")
        return (f"no trades stored for {genome_id} — journals are kept for the "
                f"elites of each generation"), {"genome_id": genome_id, "trades": []}
    wins = sum(1 for r in rows if r["ret"] > 0)
    lines = [f"{len(rows)} trades for {genome_id} ({order} first, {wins} winners)"]
    for t in rows:
        lines.append(f"  {t['symbol']:<5} {t['entry_date']} -> {t['exit_date']} "
                     f"({t['bars_held']:>3}b) {t['ret'] * 100:+6.1f}%  "
                     f"in: {t['entry_reason']}  out: {t['exit_reason']}")
    return "\n".join(lines), {"genome_id": genome_id, "order": order, "trades": rows}


@tool("reflections", "Claude's analyses",
      "What Claude said when it bred each generation: its read of why the "
      "winners won, and the lessons carried into the next batch of agents.",
      {"run_id": _RUN_PROPERTY,
       "limit": {"type": "integer", "description": "most recent N (default 3)"}})
def _reflections(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    rows = store.generation_reflections(run_id, limit=_int_arg(args, "limit", 3, hi=50))
    if not rows:
        return (f"run {run_id} has no analyses — a mutation-only run never calls "
                f"Claude"), {"run_id": run_id, "reflections": []}
    lines, out = [], []
    for row in rows:
        lessons = json.loads(row["lessons"] or "[]")
        lines.append(f"generation {row['generation']} (${row['cost_usd'] or 0:.2f})")
        lines.append("  " + _clip(row["analysis"], 2000).replace("\n", "\n  "))
        for lesson in lessons:
            lines.append(f"    - {lesson}")
        lines.append("")
        out.append({"generation": row["generation"], "analysis": row["analysis"],
                    "lessons": lessons, "cost_usd": row["cost_usd"]})
    return "\n".join(lines).rstrip(), {"run_id": run_id, "reflections": out}


@tool("overfitting_report", "Overfitting check",
      "Training fitness against held-out fitness for the top agents, with the "
      "rank correlation between the two. The held-out window is the last slice "
      "of history and is never used for selection, so it is the only evidence "
      "that an edge is real.",
      {"run_id": _RUN_PROPERTY,
       "limit": {"type": "integer", "description": "agents to compare (default 15)"}})
def _overfitting_report(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    import numpy as np

    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    limit = _int_arg(args, "limit", 15, hi=100)
    rows = [r for r in store.leaderboard(run_id, limit=limit)
            if r["test_score"] is not None]
    if len(rows) < 2:
        return (f"run {run_id} has fewer than two agents scored on the held-out "
                f"window — nothing to compare yet"),\
               {"run_id": run_id, "agents": [], "rank_correlation": None}

    train = np.asarray([r["score"] for r in rows], dtype=float)
    test = np.asarray([r["test_score"] for r in rows], dtype=float)
    gaps = train - test
    # Spearman: Pearson correlation of the ranks, which is what we care about —
    # does the training order say anything about the held-out order?
    tr = np.argsort(np.argsort(-train)).astype(float)
    te = np.argsort(np.argsort(-test)).astype(float)
    corr = float(np.corrcoef(tr, te)[0, 1]) if tr.std() > 0 and te.std() > 0 else 0.0
    corr = 0.0 if math.isnan(corr) else corr

    median_test = float(np.median(test))
    if corr > 0.5 and median_test > 0:
        verdict = ("the training ranking largely survives on held-out data — "
                   "weak evidence, but not nothing")
    elif corr > 0.5:
        verdict = ("the training order mostly holds out of sample, but held-out "
                   "fitness is negative: the ranking is consistent about agents "
                   "that do not work")
    elif corr > 0.0:
        verdict = ("the training ranking only loosely survives; treat the "
                   "leaderboard order as noisy")
    else:
        verdict = ("training rank tells you nothing about held-out rank — this "
                   "is what overfitting looks like")

    lines = [f"run {run_id} — {len(rows)} agents on both windows",
             "  training | held-out |   gap | agent"]
    for r in rows:
        lines.append(f"  {_score(r['score']):>8} | {_score(r['test_score']):>8} | "
                     f"{r['score'] - r['test_score']:+.3f} | {r['name'][:38]}")
    lines += [f"\n  mean gap (train - held-out): {float(np.mean(gaps)):+.3f}",
              f"  median held-out fitness: {median_test:+.3f}",
              f"  rank correlation: {corr:+.2f}",
              f"  {verdict}"]
    return "\n".join(lines), {
        "run_id": run_id,
        "agents": [{"genome_id": r["genome_id"], "name": r["name"],
                    "score": r["score"], "test_score": r["test_score"],
                    "gap": r["score"] - r["test_score"]} for r in rows],
        "mean_gap": float(np.mean(gaps)), "median_gap": float(np.median(gaps)),
        "median_test_score": median_test, "rank_correlation": corr,
        "verdict": verdict,
    }


@tool("search_genomes", "Search agents",
      "Find agents whose rules, name or thesis mention something — a feature "
      "like rsi14, a function like cross_above, or a word from the thesis. "
      "Useful for asking what the population is actually trading on.",
      {"query": {"type": "string", "description": "substring to look for"},
       "run_id": _RUN_PROPERTY,
       "limit": {"type": "integer", "description": "rows to return (default 20)"}},
      required=["query"])
def _search_genomes(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    store = view.store(args)
    run_id = view.resolve_run(store, _str_arg(args, "run_id"))
    query = _required_str(args, "query")
    limit = _int_arg(args, "limit", 20, hi=100)
    # The genome body is JSON, so one LIKE covers name, thesis and every rule.
    sql = ("SELECT n.id, n.name, n.generation, n.origin, n.body,"
           " (SELECT MAX(score) FROM evaluations e WHERE e.genome_id = n.id) AS score"
           " FROM genomes n WHERE n.run_id=? AND n.body LIKE ? ESCAPE '\\'"
           " GROUP BY n.fingerprint ORDER BY score DESC LIMIT ?")
    pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = store.conn.execute(sql, (run_id, pattern, limit)).fetchall()
    if not rows:
        return f"no agents in {run_id} mention {query!r}", {
            "run_id": run_id, "query": query, "matches": []}
    lines = [f"{len(rows)} agents in {run_id} mention {query!r}"]
    out = []
    for r in rows:
        body = json.loads(r["body"])
        rules = [e["when"] for e in body.get("entry_rules", [])]
        rules += [e["when"] for e in body.get("exit_rules", [])]
        hits = [rule for rule in rules if query.lower() in rule.lower()]
        lines.append(f"  {_score(r['score'])}  gen {r['generation']:>4}  "
                     f"{r['name'][:30]:<30} {r['id']}")
        for hit in hits[:3]:
            lines.append(f"      {hit}")
        out.append({"genome_id": r["id"], "name": r["name"],
                    "generation": r["generation"], "origin": r["origin"],
                    "score": r["score"], "matching_rules": hits})
    return "\n".join(lines), {"run_id": run_id, "query": query, "matches": out}


@tool("strategy_language", "Strategy language",
      "The vocabulary agents trade on: every market and portfolio feature, the "
      "functions rules may call, and the shape of a genome. Read this before "
      "interpreting or writing any rule.")
def _strategy_language(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    from .dsl import FUNCTION_DOCS
    from .features import FEATURE_DOCS, MARKET_FEATURES, PORTFOLIO_FEATURES

    text = rule_reference() + "\n" + genome_schema_text()
    return text, {
        "market_features": {n: FEATURE_DOCS.get(n, "") for n in MARKET_FEATURES},
        "portfolio_features": {n: FEATURE_DOCS.get(n, "") for n in PORTFOLIO_FEATURES},
        "functions": dict(FUNCTION_DOCS),
    }


@tool("backtest_genome", "Replay an agent",
      "Re-run a stored agent over any window or symbol list and report what it "
      "would have done. This computes a backtest (and may fetch price data); "
      "it writes nothing. The honest use is to check a champion on dates it "
      "never evolved on.",
      {"genome_id": {"type": "string", "description": "genome id"},
       "start": {"type": "string", "description": "first date YYYY-MM-DD (default: the run's)"},
       "end": {"type": "string", "description": "last date YYYY-MM-DD (default: the run's)"},
       "symbols": {"type": "string", "description": "comma separated tickers (default: the run's)"},
       "trades": {"type": "integer", "description": "sample trades to show (default 10)"}},
      required=["genome_id"])
def _backtest_genome(view: TrainingView, args: Dict[str, Any]) -> ToolResult:
    from .evolution import replay_genome

    store = view.store(args)
    genome_id = _required_str(args, "genome_id")
    genome = store.get_genome(genome_id)
    if genome is None:
        raise ViewError(f"unknown genome {genome_id!r}")
    owner = store.conn.execute("SELECT run_id FROM genomes WHERE id=?",
                               (genome_id,)).fetchone()
    cfg = EvolutionConfig.from_dict(store.run_config(owner["run_id"]) or {})
    raw_symbols = _str_arg(args, "symbols")
    symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()] or None
    try:
        outcome = replay_genome(genome, cfg, symbols=symbols,
                                start=_str_arg(args, "start"),
                                end=_str_arg(args, "end"))
    except Exception as exc:  # noqa: BLE001 - data fetches fail in ordinary ways
        raise ViewError(f"backtest failed: {type(exc).__name__}: {exc}") from exc
    if outcome.error:
        raise ViewError(outcome.error)

    window = (f"{_str_arg(args, 'start') or cfg.start}..{_str_arg(args, 'end') or cfg.end}"
              f" on {','.join(symbols or cfg.symbols)}")
    lines = [genome.describe(), "",
             f"replayed {window}",
             f"  fitness {outcome.score:+.3f} | {outcome.metrics.summary()}"]
    sample = outcome.journal.trades[:_int_arg(args, "trades", 10, lo=0, hi=100)] \
        if outcome.journal else []
    if sample:
        lines.append(f"\n  first {len(sample)} trades")
        lines += [f"    {t.summary()}" for t in sample]
    lines.append("\n  a backtest on a window chosen after the fact is still not a "
                 "forecast; it is one more test the hypothesis has not yet failed")
    return "\n".join(lines), {
        "genome_id": genome_id, "window": window, "score": outcome.score,
        "metrics": outcome.metrics.to_dict(),
        "trades": [t.to_dict() for t in sample],
    }


# ------------------------------------------------------------------ resources

def _resources(view: TrainingView) -> List[Dict[str, Any]]:
    out = [{"uri": "evotrader://strategy-language",
            "name": "strategy language",
            "description": "features, functions and genome shape",
            "mimeType": "text/plain"}]
    try:
        store = view.store()
    except ViewError:
        return out
    for row in store.list_runs(20):
        out.append({"uri": f"evotrader://run/{row['id']}",
                    "name": f"run {row['id']}",
                    "description": f"{row['status']}, {row['generations'] or 0} "
                                   f"generations — full Markdown report",
                    "mimeType": "text/markdown"})
    return out


def _read_resource(view: TrainingView, uri: str) -> Dict[str, Any]:
    if uri == "evotrader://strategy-language":
        return {"uri": uri, "mimeType": "text/plain",
                "text": rule_reference() + "\n" + genome_schema_text()}
    prefix = "evotrader://run/"
    if uri.startswith(prefix):
        store = view.store()
        run_id = view.resolve_run(store, uri[len(prefix):])
        return {"uri": uri, "mimeType": "text/markdown",
                "text": markdown_report(store, run_id)}
    raise ViewError(f"unknown resource {uri!r}")


# --------------------------------------------------------------- the protocol

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPServer:
    """Newline-delimited JSON-RPC 2.0, the subset of MCP this view needs."""

    def __init__(self, view: Optional[TrainingView] = None):
        self.view = view or TrainingView()
        self.initialized = False

    # --------------------------------------------------------------- routing
    def handle(self, message: Any) -> Optional[Dict[str, Any]]:
        """Return the response to one message, or None for a notification."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error(None, INVALID_REQUEST, "expected a JSON-RPC 2.0 object")
        method = message.get("method")
        msg_id = message.get("id")
        if not isinstance(method, str):
            return _error(msg_id, INVALID_REQUEST, "missing method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(msg_id, INVALID_PARAMS, "params must be an object")

        if method.startswith("notifications/"):
            if method == "notifications/initialized":
                self.initialized = True
            return None
        if msg_id is None:
            return None          # an unknown notification: nothing to answer

        try:
            if method == "initialize":
                return _result(msg_id, self._initialize(params))
            if method == "ping":
                return _result(msg_id, {})
            if method == "tools/list":
                return _result(msg_id, {"tools": [t.spec() for t in TOOLS.values()]})
            if method == "tools/call":
                return _result(msg_id, self._call_tool(params))
            if method == "resources/list":
                return _result(msg_id, {"resources": _resources(self.view)})
            if method == "resources/templates/list":
                return _result(msg_id, {"resourceTemplates": [{
                    "uriTemplate": "evotrader://run/{run_id}",
                    "name": "run report",
                    "description": "Markdown report for one run",
                    "mimeType": "text/markdown"}]})
            if method == "resources/read":
                uri = params.get("uri")
                if not isinstance(uri, str) or not uri:
                    return _error(msg_id, INVALID_PARAMS, "uri is required")
                return _result(msg_id, {"contents": [_read_resource(self.view, uri)]})
        except ViewError as exc:
            return _error(msg_id, INVALID_PARAMS, str(exc))
        except Exception as exc:  # noqa: BLE001 - a bad call must not kill the server
            return _error(msg_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")
        return _error(msg_id, METHOD_NOT_FOUND, f"unknown method {method!r}")

    def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False},
                             "resources": {"listChanged": False, "subscribe": False}},
            "serverInfo": {"name": SERVER_NAME, "title": "evotrader training view",
                           "version": _version()},
            "instructions": INSTRUCTIONS,
        }

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        tool_impl = TOOLS.get(name) if isinstance(name, str) else None
        if tool_impl is None:
            return _tool_error(f"unknown tool {name!r}; available: "
                               f"{', '.join(sorted(TOOLS))}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return _tool_error("arguments must be an object")
        for key in tool_impl.schema.get("required", []):
            if not args.get(key):
                return _tool_error(f"{tool_impl.name} needs {key!r}")
        try:
            text, structured = tool_impl.handler(self.view, args)
        except ViewError as exc:
            return _tool_error(str(exc))
        except Exception as exc:  # noqa: BLE001 - report, don't crash the session
            return _tool_error(f"{type(exc).__name__}: {exc}")
        return {"content": [{"type": "text", "text": text}],
                "structuredContent": structured, "isError": False}


def _version() -> str:
    from . import __version__
    return __version__


def _result(msg_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _tool_error(message: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def serve(server: Optional[MCPServer] = None, stdin: Optional[TextIO] = None,
          stdout: Optional[TextIO] = None) -> int:
    """Read messages until stdin closes.  Only JSON goes to stdout."""
    server = server or MCPServer()
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError as exc:
            response = _error(None, PARSE_ERROR, f"invalid JSON: {exc}")
        else:
            response = server.handle(message)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
    server.view.close()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evotrader-mcp",
        description="Serve the evotrader training view over MCP on stdio.")
    parser.add_argument("--db", dest="db_path", default="",
                        help="SQLite path (default: $EVOTRADER_DB, "
                             "else runs/evotrader.sqlite)")
    args = parser.parse_args(argv)
    print(f"{SERVER_NAME} {_version()} on stdio", file=sys.stderr)
    try:
        return serve(MCPServer(TrainingView(args.db_path)))
    except KeyboardInterrupt:  # pragma: no cover - interactive
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
