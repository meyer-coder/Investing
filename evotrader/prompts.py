"""Prompt construction for the breeding step.

The breeder's job is the interesting one: read how the best agents of a
generation actually traded — their rules, their journals, their winners and
losers — work out *why* they worked, and write the next generation.  These
helpers assemble that briefing and keep it inside a sane token budget.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from .dsl import FUNCTION_DOCS
from .features import (FEATURE_DOCS, LIQUIDITY_FEATURES, PORTFOLIO_FEATURES,
                       PRICE_FEATURES)
from .fitness import Evaluation
from .genome import MAX_ENTRY_RULES, MAX_EXIT_RULES, Genome
from .journal import Journal

SYSTEM_PROMPT = """\
You are the breeding engine of an evolutionary paper-trading system.

Each generation, a population of trading agents is backtested on historical
market data. You are shown the best performers, how they actually traded, and
what the rest of the population did. Your job has two halves:

1. ANALYSE. Work out *why* the top agents did well and where they were
   fragile. Distinguish a real, repeatable edge from luck: a rule that fired
   three times in one bull year is noise; an edge that shows up across many
   trades, symbols and regimes is a signal. Say plainly when a result looks
   like overfitting or like a beta bet dressed up as a strategy.
2. BREED. Write the next generation of agents, in the strict JSON schema
   given below. Mix three kinds of offspring:
     - refinements of what worked (small, deliberate changes to one idea),
     - recombinations of two different agents' ideas,
     - at least a couple of genuinely different hypotheses, so the population
       does not collapse onto one lineage.

You are writing strategies, not prose. Every genome must be mechanically
valid: rules use only the listed features and functions, and every numeric
threshold must be on the scale of the feature it is compared against (rsi14
is 0-100; dist_sma200 is a fraction like 0.05; ret20 is a fraction like -0.08).

Hard constraints, applied by the runtime whatever you write:
* Long-only. No shorting, no leverage, no options.
* Orders decided on a bar fill at the NEXT bar's open, with commission and
  slippage charged. A rule that only works with same-bar fills will not work.
* An agent that never trades scores badly; so does one that churns.
"""


def _docs_for(names) -> str:
    return "\n".join(f"  {name}: {FEATURE_DOCS.get(name, '')}" for name in names)


def _rule_reference() -> str:
    feats = _docs_for(PRICE_FEATURES)
    liquidity = _docs_for(LIQUIDITY_FEATURES)
    port = _docs_for(PORTFOLIO_FEATURES)
    funcs = "\n".join(f"  {sig}: {doc}" for sig, doc in FUNCTION_DOCS.items())
    return f"""\
RULE LANGUAGE
Rules are boolean expressions. Operators: < <= > >= == != + - * / and or not,
parentheses. Numbers are plain decimals. Nothing else is allowed — no Python,
no function definitions, no lookups.

Price and technical features (available in entry and exit rules):
{feats}

Liquidity and order-flow features (available in entry and exit rules):
{liquidity}

Portfolio features (most useful in exit rules):
{port}

Functions:
{funcs}

Examples of valid rules:
  rsi14 < 30 and close > sma200
  cross_above(macd, macd_signal) and volume_ratio > 1.4
  dist_sma20 < -0.03 and mkt_above_sma200 == 1 and vol20 < 0.35
  position_return > 0.18 or bars_held > 40 or position_drawdown < -0.06
"""


LIQUIDITY_PLAYBOOK = """\
=== FOCUS: LIQUIDITY SWEEPS AND ORDER FLOW ===

This run breeds agents that trade liquidity and order flow, not indicators.
The premise, and its limits, stated plainly:

* Resting orders cluster where everyone can see them — under obvious lows, above
  obvious highs, and the tighter the cluster of equal highs or lows, the thicker
  the pool (`equal_highs_20`, `equal_lows_20`).
* Price is drawn to those pools, and what matters is what happens *after* it
  gets there. A level taken intrabar and given straight back is a sweep
  (`sweep_low`, `sweep_high`): stops were harvested and the move failed. A level
  taken and held into the close is acceptance (`breakout_20`, `breakdown_20`):
  the move is real. The same broken level means opposite things in the two cases,
  and telling them apart is most of the edge here.
* What the bar cost tells you as much as what it did. Heavy volume with no range
  is absorption (`absorption`, `effort_result`); a large range on thin volume is
  a move nobody is defending. Signed volume (`net_flow`, `cum_flow_20`, `cmf20`,
  `obv_slope`) says which side the volume leaned to.
* These are daily bars. There is no order book and no trade tape here, so every
  "order flow" feature is a bar-derived proxy: `clv` infers who won the bar from
  where it closed in its range, `net_flow` weights that by volume. Treat them as
  evidence, not as measurement, and do not write a thesis that claims to see
  individual participants.

What tends to separate a real edge from a curve fit in this family:
* Direction of the sweep versus the trend. A sweep of the lows inside an
  uptrend (`close > sma200`) is a different trade from one in a downtrend.
* Depth and rejection. `sweep_low_depth > 0.5` with a long `lower_wick` is a
  genuine raid; a two-tick poke is noise.
* Confirmation from flow rather than more price. A sweep with `cmf20` already
  positive is an accumulation signal; the same sweep with flow falling is a
  falling knife.
* Time. Sweep reversals resolve in days, not quarters — `bars_since_sweep_low`
  and a `max_hold_bars` cap keep an agent from turning a failed sweep trade into
  an accidental long-term hold.
* Frequency. Sweeps of a 20-bar level happen often; sweeps of a 60-bar level are
  rare. An agent keyed only to the rare case will show a handful of trades and a
  meaningless Sharpe. Prefer edges with enough occurrences to believe.

Long-only, so the bearish reads are exits and filters: `sweep_high` and a
rolling-over `cmf20` are reasons to be out, not reasons to be short.

Breed inside this theme. Classic trend and mean-reversion features are still
available and are useful as *context* (regime, trend, volatility) around a
liquidity trigger, but the entry logic of every offspring should turn on
liquidity or order flow, and the set as a whole should test several different
claims about it rather than re-tuning one.
"""

#: focus name -> extra briefing inserted into the breeding prompt.
FOCUS_BRIEFS: Dict[str, str] = {"liquidity": LIQUIDITY_PLAYBOOK}


def focus_brief(focus: str) -> str:
    """The themed briefing for a run's focus (empty for an unfocused run)."""
    return FOCUS_BRIEFS.get(focus or "all", "")


def _genome_schema_text() -> str:
    return f"""\
GENOME FIELDS
  name          short distinctive name
  thesis        one or two sentences: the belief this agent trades on
  rationale     why you are creating this agent now, given the evidence above
  entry_rules   1..{MAX_ENTRY_RULES} objects: {{"when": <rule>, "weight": 0.01-1.0}}
                weight is the target position size as a fraction of equity;
                the first rule that matches for a symbol wins
  exit_rules    1..{MAX_EXIT_RULES} objects: {{"when": <rule>}}; any match closes the position
  risk          max_position_pct (0.01-1), max_positions (1-20),
                max_gross_exposure (0.05-1), stop_loss_pct (0-0.9, 0 = off),
                take_profit_pct (0-5, 0 = off), trailing_stop_pct (0-0.9, 0 = off),
                max_hold_bars (0 = off), min_hold_bars, cooldown_bars
"""


GENOME_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "string",
            "description": "Why the top agents performed as they did, and what "
                           "is repeatable versus lucky. A few hundred words.",
        },
        "lessons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short, concrete, testable claims carried into the next generation.",
        },
        "genomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "thesis": {"type": "string"},
                    "rationale": {"type": "string"},
                    "parents": {"type": "array", "items": {"type": "string"}},
                    "entry_rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "when": {"type": "string"},
                                "weight": {"type": "number"},
                            },
                            "required": ["when", "weight"],
                            "additionalProperties": False,
                        },
                    },
                    "exit_rules": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"when": {"type": "string"}},
                            "required": ["when"],
                            "additionalProperties": False,
                        },
                    },
                    "risk": {
                        "type": "object",
                        "properties": {
                            "max_position_pct": {"type": "number"},
                            "max_positions": {"type": "integer"},
                            "max_gross_exposure": {"type": "number"},
                            "stop_loss_pct": {"type": "number"},
                            "take_profit_pct": {"type": "number"},
                            "trailing_stop_pct": {"type": "number"},
                            "max_hold_bars": {"type": "integer"},
                            "min_hold_bars": {"type": "integer"},
                            "cooldown_bars": {"type": "integer"},
                        },
                        "required": ["max_position_pct", "max_positions",
                                     "max_gross_exposure", "stop_loss_pct",
                                     "take_profit_pct", "trailing_stop_pct",
                                     "max_hold_bars", "min_hold_bars",
                                     "cooldown_bars"],
                        "additionalProperties": False,
                    },
                },
                "required": ["name", "thesis", "rationale", "parents",
                             "entry_rules", "exit_rules", "risk"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["analysis", "lessons", "genomes"],
    "additionalProperties": False,
}


def elite_report(genome: Genome, ev: Evaluation, journal: Optional[Journal],
                 *, max_trades: int = 4) -> str:
    """One elite's genome, score, and the evidence of how it traded."""
    lines = [genome.describe(), f"  score: {ev.score:+.3f} | {ev.metrics.summary()}"]
    if ev.test_metrics is not None:
        lines.append(f"  held-out window: {ev.test_metrics.summary()}")
    m = ev.metrics
    lines.append(f"  turnover {m.turnover:.1f}x/yr, avg hold {m.avg_bars_held:.0f} bars, "
                 f"time invested {m.exposure * 100:.0f}%, profit factor "
                 f"{m.profit_factor:.2f}, sortino {m.sortino:.2f}")
    if journal is not None:
        if journal.trades:
            lines.append("  best trades:")
            lines += [f"    {t.summary()}" for t in journal.best_trades(max_trades)]
            lines.append("  worst trades:")
            lines += [f"    {t.summary()}" for t in journal.worst_trades(max_trades)]
        if journal.rule_hits:
            hits = sorted(journal.rule_hits.items(), key=lambda kv: -kv[1])[:6]
            lines.append("  rule fire counts: " + "; ".join(f"{v}x {k}" for k, v in hits))
        if journal.rejected_entries:
            lines.append(f"  signals blocked by risk limits: {journal.rejected_entries}")
        notes = [t for t in journal.thoughts if t.kind == "entry"][:3]
        if notes:
            lines.append("  sample reasoning at entry:")
            lines += [f"    {t.date} {t.symbol}: {t.text} {t.context}" for t in notes]
    return "\n".join(lines)


def population_summary(evals: Sequence[Evaluation], *, elites: int) -> str:
    """What the rest of the population did — the failures matter too."""
    scored = [e for e in evals if not e.error]
    if not scored:
        return "No genome completed a backtest this generation."
    scores = sorted((e.score for e in scored), reverse=True)
    body = [
        f"population {len(evals)} ({len(evals) - len(scored)} failed to run)",
        f"score distribution: best {scores[0]:+.3f}, "
        f"median {scores[len(scores) // 2]:+.3f}, worst {scores[-1]:+.3f}",
    ]
    tail = sorted(scored, key=lambda e: e.score)[:5]
    body.append("worst performers and what they did:")
    for e in tail:
        body.append(f"  {e.name}: score {e.score:+.3f} | {e.metrics.summary()}")
    dead = [e for e in scored if e.metrics.trades == 0]
    if dead:
        body.append(f"{len(dead)} agents never traded at all "
                    f"(their entry conditions never fired).")
    return "\n".join(body)


def history_summary(history: Sequence[Dict[str, Any]], *, limit: int = 8) -> str:
    if not history:
        return "This is the first generation."
    rows = history[-limit:]
    lines = ["generation history (best score and champion each generation):"]
    for h in rows:
        lines.append(f"  gen {h['generation']:>4}: best {h['best_score']:+.3f} "
                     f"mean {h.get('mean_score', 0.0):+.3f} — {h.get('best_name', '?')}")
    return "\n".join(lines)


def build_breeding_prompt(*, generation: int, elites: Sequence[tuple],
                          evals: Sequence[Evaluation], history: Sequence[Dict[str, Any]],
                          n_offspring: int, lessons: Sequence[str] = (),
                          window: str = "", extra: str = "", focus: str = "all") -> str:
    """Assemble the full briefing for one breeding call.

    ``elites`` is a sequence of ``(genome, evaluation, journal)`` triples.
    """
    parts = [
        f"GENERATION {generation}. Backtest window: {window or 'unspecified'}.",
        "",
        _rule_reference(),
        _genome_schema_text(),
    ]
    brief = focus_brief(focus)
    if brief:
        parts += ["", brief]
    parts += [
        "",
        "=== TOP PERFORMERS THIS GENERATION ===",
    ]
    for genome, ev, journal in elites:
        parts.append(elite_report(genome, ev, journal))
        parts.append("")
    parts.append("=== REST OF THE POPULATION ===")
    parts.append(population_summary(evals, elites=len(elites)))
    parts.append("")
    parts.append(history_summary(history))
    if lessons:
        parts.append("")
        parts.append("lessons carried forward from earlier generations:")
        parts += [f"  - {l}" for l in list(lessons)[-12:]]
    if extra:
        parts.append("")
        parts.append(extra)
    parts += [
        "",
        "=== YOUR TASK ===",
        f"Write exactly {n_offspring} new genomes for generation {generation + 1}.",
        "In `parents`, list the ids of the agents each offspring draws on "
        "(empty list for a genuinely new idea).",
        "Do not simply restate the elites: every offspring must differ from its "
        "parents in a way you can justify, and the set as a whole must cover "
        "more than one hypothesis about what makes money in this market.",
        *([f"Every offspring must trade the run's focus: {focus}. Keep the "
           "entry logic anchored in the liquidity and order-flow features, and "
           "say in each `rationale` which claim about liquidity it tests."]
          if focus_brief(focus) else []),
        "Before the genomes, write the `analysis` — the honest read on what the "
        "evidence above supports — and `lessons`, the short claims you want the "
        "next generation to test.",
    ]
    return "\n".join(parts)
