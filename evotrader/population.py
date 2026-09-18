"""Seed archetypes and the non-LLM genetic operators.

Two jobs:

1. Build generation 0 from a library of readable strategy archetypes, jittered
   so the population starts diverse instead of identical.
2. Provide mutation and crossover that need no API access.  These run every
   generation alongside Claude's offspring (cheap diversity), and they are the
   complete breeder when the run is offline or the API budget is spent.
"""
from __future__ import annotations

import random
import re
from typing import Callable, Dict, List, Sequence, Tuple

from .genome import EntryRule, ExitRule, Genome, GenomeError, RiskParams, compile_genome

# ------------------------------------------------------------------ archetypes
#: (name, thesis, entry rules, exit rules, risk overrides)
ARCHETYPES: List[Tuple[str, str, List[str], List[str], Dict[str, float]]] = [
    ("Trend Rider", "Hold what is already going up; step aside when the trend breaks.",
     ["close > sma50 and sma50 > sma200 and mkt_above_sma200 == 1"],
     ["close < sma50", "position_return < -0.10"],
     {"max_position_pct": 0.34, "max_positions": 3, "stop_loss_pct": 0.12}),
    ("Oversold Dip Buyer", "Buy fear inside an intact uptrend, sell into the bounce.",
     ["rsi14 < 32 and close > sma200"],
     ["rsi14 > 60", "bars_held > 30"],
     {"max_position_pct": 0.30, "stop_loss_pct": 0.08, "cooldown_bars": 5}),
    ("Breakout Hunter", "New highs on heavy volume tend to keep going.",
     ["pct_of_52w_high > 0.98 and volume_ratio > 1.3"],
     ["close < sma20", "position_return < -0.07"],
     {"max_position_pct": 0.25, "trailing_stop_pct": 0.12}),
    ("MACD Crosser", "Trade the momentum turn signalled by a MACD cross.",
     ["cross_above(macd, macd_signal) and close > sma100_placeholder"],
     ["cross_below(macd, macd_signal)"],
     {"max_position_pct": 0.25}),
    ("Bollinger Reverter", "Price stretched below the band snaps back to the mean.",
     ["bb_pct < 0.05 and dist_sma200 > -0.10"],
     ["bb_pct > 0.75", "bars_held > 20"],
     {"max_position_pct": 0.25, "stop_loss_pct": 0.07}),
    ("Momentum Chaser", "Buy the strongest quarterly momentum, cut it when it stalls.",
     ["ret60 > 0.12 and close > sma50"],
     ["ret20 < -0.05", "close < sma50"],
     {"max_position_pct": 0.34, "max_positions": 3}),
    ("Volatility Contraction", "Quiet markets precede expansion; buy the squeeze.",
     ["vol_ratio_20_60 < 0.75 and close > sma50"],
     ["vol_ratio_20_60 > 1.4", "position_return > 0.15"],
     {"max_position_pct": 0.30, "trailing_stop_pct": 0.08}),
    ("Regime Switcher", "Full risk above the 200-day, flat below it.",
     ["mkt_above_sma200 == 1 and dist_sma20 > 0"],
     ["mkt_above_sma200 == 0", "dist_sma20 < -0.03"],
     {"max_position_pct": 0.50, "max_positions": 2}),
    ("Patient Accumulator", "Rarely trade; buy deep drawdowns and hold for months.",
     ["dist_sma200 < -0.08 and rsi14 < 40"],
     ["position_return > 0.25", "bars_held > 120"],
     {"max_position_pct": 0.50, "max_positions": 2, "stop_loss_pct": 0.20,
      "min_hold_bars": 10}),
    ("Fast Swing", "Short holds off oversold 7-day RSI, tight stops.",
     ["rsi7 < 25"],
     ["rsi7 > 55", "bars_held > 8"],
     {"max_position_pct": 0.25, "stop_loss_pct": 0.05, "max_hold_bars": 15,
      "cooldown_bars": 3}),
    ("Pullback To Trend", "Buy shallow pullbacks to the 20-day inside an uptrend.",
     ["dist_sma20 < -0.02 and sma20 > sma50 and sma50 > sma200"],
     ["dist_sma20 > 0.04", "close < sma50"],
     {"max_position_pct": 0.34, "stop_loss_pct": 0.08}),
    ("Risk Parity Lite", "Size down when volatility is high, stay invested otherwise.",
     ["vol20 < 0.22 and close > sma100_placeholder", "vol20 < 0.35 and close > sma200"],
     ["vol20 > 0.45", "close < sma200"],
     {"max_position_pct": 0.40, "max_positions": 3}),
    ("Gap Fader", "Fade one-day overreactions against the prevailing trend.",
     ["ret1 < -0.025 and close > sma200"],
     ["ret5 > 0.03", "bars_held > 10"],
     {"max_position_pct": 0.25, "stop_loss_pct": 0.06, "cooldown_bars": 2}),
    ("Always In", "Stay invested unless the market breaks its long-term average.",
     ["mkt_above_sma200 == 1"],
     ["mkt_above_sma200 == 0"],
     {"max_position_pct": 0.50, "max_positions": 2, "stop_loss_pct": 0.0}),
]

#: Liquidity-sweep and order-flow archetypes.
#:
#: The shared premise: the obvious highs and lows on a chart are where stop
#: orders rest, price is drawn to them, and what matters is not that a level
#: broke but whether it *held* once it did.  A level taken and reclaimed in the
#: same bar (`sweep_low`) is a failed breakdown; a level taken and accepted
#: (`breakout_20`) is a real one.  The order-flow features then ask whether
#: volume agrees with the move.  Long-only, so the short-side reads
#: (`sweep_high`, `cmf20 < 0`) mostly appear as exits.
LIQUIDITY_ARCHETYPES: List[Tuple[str, str, List[str], List[str], Dict[str, float]]] = [
    ("Stop Run Reclaim",
     "Price dips through the 20-bar low to trigger sell stops, then closes back "
     "above it. Buy the reclaim while the long-term trend is intact.",
     ["sweep_low == 1 and close > sma200"],
     ["dist_prior_high_20 > -0.005", "sweep_high == 1", "bars_held > 20"],
     {"max_position_pct": 0.30, "max_positions": 4, "stop_loss_pct": 0.05,
      "cooldown_bars": 3}),
    ("Failed Breakdown",
     "A raid on the quarter-low that the sellers cannot hold is a capitulation "
     "low, not a trend change — especially on heavy volume.",
     ["sweep_low_60 == 1 and volume_ratio > 1.2"],
     ["clv_avg5 < -0.3", "position_return > 0.12", "bars_held > 30"],
     {"max_position_pct": 0.34, "max_positions": 3, "stop_loss_pct": 0.07}),
    ("Sweep And Go",
     "Enter in the days right after a sweep, while price is still holding above "
     "the level it raided and closing strong.",
     ["bars_since_sweep_low <= 3 and dist_prior_low_20 > 0 and clv > 0.3"],
     ["dist_prior_low_20 < 0", "position_return > 0.08", "bars_held > 15"],
     {"max_position_pct": 0.25, "max_positions": 4, "stop_loss_pct": 0.05,
      "min_hold_bars": 1}),
    ("Liquidity Pool Raid",
     "The more bars stall at the same low, the more stops sit under it and the "
     "more fuel a reversal has once they are taken.",
     ["equal_lows_20 > 2 and sweep_low == 1"],
     ["dist_prior_high_20 > -0.01", "position_drawdown < -0.05", "bars_held > 25"],
     {"max_position_pct": 0.30, "max_positions": 3, "stop_loss_pct": 0.06}),
    ("Absorption Buyer",
     "Heavy volume that does not move price is someone filling a large order. "
     "Buy when that absorption comes with positive money flow.",
     ["absorption == 1 and cmf20 > 0.05 and close > sma50"],
     ["cmf20 < -0.05", "close < sma50", "bars_held > 25"],
     {"max_position_pct": 0.25, "max_positions": 4, "stop_loss_pct": 0.06}),
    ("Flow Divergence",
     "Price falling while signed volume stays positive means the selling is "
     "thin. Buy the divergence, exit when the flow finally turns.",
     ["ret5 < -0.03 and cum_flow_20 > 0.05"],
     ["cum_flow_20 < -0.05", "position_return > 0.10", "bars_held > 20"],
     {"max_position_pct": 0.25, "max_positions": 4, "stop_loss_pct": 0.07,
      "cooldown_bars": 2}),
    ("VWAP Reclaim",
     "The 20-bar VWAP is where the recent volume actually traded. Reclaiming it "
     "with on-balance volume rising says buyers took control.",
     ["cross_above(close, vwap20) and obv_slope > 0"],
     ["cross_below(close, vwap20)", "position_return < -0.06"],
     {"max_position_pct": 0.30, "max_positions": 4, "stop_loss_pct": 0.07}),
    ("Imbalance Runner",
     "A fast, high-volume move leaves an untraded gap behind it. Ride the "
     "displacement while the imbalance is fresh.",
     ["fvg_up == 1 and displacement > 1.0 and volume_ratio > 1.3"],
     ["close < vwap20", "fvg_down == 1", "bars_held > 20"],
     {"max_position_pct": 0.25, "max_positions": 4, "trailing_stop_pct": 0.08,
      "stop_loss_pct": 0.06}),
    ("Gap Sweep Fade",
     "An overnight gap down that gets bought back through the session is a "
     "liquidity grab, not news the market believes.",
     ["gap_pct < -0.015 and clv > 0.2 and close > sma200"],
     ["ret5 > 0.03", "bars_held > 10", "clv_avg5 < -0.4"],
     {"max_position_pct": 0.25, "max_positions": 4, "stop_loss_pct": 0.05,
      "max_hold_bars": 20, "cooldown_bars": 2}),
    ("Breakout Acceptance",
     "Distinguish a real break from a sweep: take the break only when the bar "
     "closes above the level on a volume surge.",
     ["breakout_20 == 1 and volume_z20 > 1.0 and clv > 0.3"],
     ["sweep_high == 1", "close < vwap20", "position_return < -0.05"],
     {"max_position_pct": 0.30, "max_positions": 4, "trailing_stop_pct": 0.10}),
    ("Effort Without Result",
     "When sellers spend heavy volume and price barely moves, the supply is "
     "being absorbed. Buy that stalemate while flow is positive.",
     ["effort_result < 0.5 and net_flow > 0 and dist_sma200 > -0.12"],
     ["position_return > 0.07", "bars_held > 12", "cmf20 < -0.10"],
     {"max_position_pct": 0.25, "max_positions": 5, "stop_loss_pct": 0.05,
      "max_hold_bars": 30}),
    ("Flow Leads Price",
     "On-balance volume turning up before price does is accumulation. Buy it "
     "flat, sell it when the flow rolls over.",
     ["obv_slope > 0.10 and dist_sma20 < 0.01"],
     ["obv_slope < -0.05", "position_return < -0.08", "bars_held > 40"],
     {"max_position_pct": 0.30, "max_positions": 4, "stop_loss_pct": 0.08}),
    ("Acceptance Above Volume",
     "Price above almost all of the last quarter's traded volume, pulling back "
     "to the 60-bar VWAP, is a trend pausing rather than ending.",
     ["volume_below_pct > 0.75 and dist_vwap60 < 0.01 and close > sma50"],
     ["volume_below_pct < 0.35", "close < vwap60", "bars_held > 35"],
     {"max_position_pct": 0.34, "max_positions": 3, "stop_loss_pct": 0.08}),
    ("Deep Raid Reversal",
     "Only the deepest sweeps — more than half an ATR through the level — are "
     "worth trading; a shallow poke is just noise.",
     ["sweep_low_depth > 0.5 and lower_wick > 0.4"],
     ["upper_wick > 0.5", "position_return > 0.10", "bars_held > 18"],
     {"max_position_pct": 0.25, "max_positions": 4, "stop_loss_pct": 0.06,
      "cooldown_bars": 3}),
]

#: Which archetype library a run starts from.
FOCUSES = ("all", "liquidity")


def archetypes_for(focus: str = "all") -> List[Tuple[str, str, List[str], List[str], Dict[str, float]]]:
    """Seed library for a focus.  A liquidity run still gets a few classic
    archetypes: a population with exactly one idea in it has nothing to
    recombine, and the trend/regime seeds give the sweep seeds something to be
    measured against."""
    if focus == "liquidity":
        return LIQUIDITY_ARCHETYPES + ARCHETYPES[:3]
    return ARCHETYPES + LIQUIDITY_ARCHETYPES


# `sma100` is not in the feature set; archetypes referencing it are repaired here
# rather than silently dropped.
_REPAIRS = {"sma100_placeholder": "sma50"}

#: Building blocks for random clause mutation: (feature, low, high, decimals).
_CONDITION_BANK: List[Tuple[str, float, float, int]] = [
    ("rsi14", 15, 85, 0), ("rsi7", 10, 90, 0),
    ("dist_sma20", -0.10, 0.10, 3), ("dist_sma50", -0.15, 0.15, 3),
    ("dist_sma200", -0.30, 0.30, 3),
    ("ret1", -0.05, 0.05, 3), ("ret5", -0.10, 0.10, 3),
    ("ret20", -0.20, 0.20, 3), ("ret60", -0.30, 0.40, 3),
    ("atr_pct", 0.005, 0.06, 4), ("vol20", 0.08, 0.60, 3),
    ("vol_ratio_20_60", 0.5, 1.8, 2),
    ("bb_pct", 0.0, 1.0, 2), ("zscore20", -2.5, 2.5, 2),
    ("pct_of_52w_high", 0.70, 1.0, 3), ("pct_off_52w_low", 0.0, 1.0, 2),
    ("volume_ratio", 0.6, 2.5, 2), ("macd_hist", -2.0, 2.0, 2),
    ("mkt_ret20", -0.10, 0.10, 3), ("mkt_vol20", 0.08, 0.50, 3),
]

_EXIT_ONLY_BANK: List[Tuple[str, float, float, int]] = [
    ("position_return", -0.20, 0.40, 3),
    ("position_drawdown", -0.20, -0.01, 3),
    ("bars_held", 3, 120, 0),
    ("portfolio_drawdown", -0.30, -0.05, 3),
]

#: Liquidity and order-flow clauses, sampled heavily under `focus="liquidity"`.
_LIQUIDITY_BANK: List[Tuple[str, float, float, int]] = [
    ("dist_prior_high_20", -0.15, 0.02, 3), ("dist_prior_low_20", -0.02, 0.20, 3),
    ("equal_highs_20", 1, 6, 0), ("equal_lows_20", 1, 6, 0),
    ("sweep_low_depth", 0.1, 1.5, 2), ("sweep_high_depth", 0.1, 1.5, 2),
    ("bars_since_sweep_low", 1, 20, 0), ("bars_since_sweep_high", 1, 20, 0),
    ("clv", -0.8, 0.8, 2), ("clv_avg5", -0.6, 0.6, 2),
    ("upper_wick", 0.1, 0.7, 2), ("lower_wick", 0.1, 0.7, 2),
    ("body_pct", 0.1, 0.9, 2), ("range_atr", 0.4, 2.5, 2),
    ("gap_pct", -0.03, 0.03, 3), ("displacement", -2.0, 2.0, 2),
    ("net_flow", -1.5, 1.5, 2), ("cum_flow_5", -1.0, 1.0, 2),
    ("cum_flow_20", -0.6, 0.6, 2), ("cmf20", -0.25, 0.25, 3),
    ("obv_slope", -0.3, 0.3, 3), ("volume_z20", -1.0, 3.0, 2),
    ("effort_result", 0.2, 2.0, 2), ("volume_below_pct", 0.1, 0.95, 2),
    ("dist_vwap20", -0.08, 0.08, 3), ("dist_vwap60", -0.15, 0.15, 3),
    ("bars_since_fvg_up", 1, 15, 0), ("bars_since_fvg_down", 1, 15, 0),
]

#: Binary features; comparing these to a threshold only makes sense as == 0/1.
_FLAGS = ["sweep_low", "sweep_high", "sweep_low_60", "sweep_high_60",
          "breakout_20", "breakdown_20", "absorption", "fvg_up", "fvg_down"]

_LIQUIDITY_CROSSES = [
    "cross_above(close, vwap20)", "cross_below(close, vwap20)",
    "cross_above(close, vwap60)", "cross_below(close, vwap60)",
    "cross_above(close, prior_high_20)", "cross_below(close, prior_low_20)",
    "cross_above(cmf20, 0)", "cross_below(cmf20, 0)",
    "cross_above(obv_slope, 0)", "cross_below(obv_slope, 0)",
]

_CROSSES = [
    "cross_above(macd, macd_signal)", "cross_below(macd, macd_signal)",
    "cross_above(close, sma50)", "cross_below(close, sma50)",
    "cross_above(close, sma200)", "cross_below(close, sma200)",
    "cross_above(sma20, sma50)", "cross_below(sma20, sma50)",
    "cross_above(close, bb_upper)", "cross_below(close, bb_lower)",
]

_NUMBER_RE = re.compile(r"(?<![A-Za-z_0-9.])(\d+\.\d+|\d+)")
_OPS = ["<", "<=", ">", ">=", "=="]


def _repair(rule: str) -> str:
    for bad, good in _REPAIRS.items():
        rule = rule.replace(bad, good)
    return rule


def _bank_for(focus: str, exit_side: bool) -> List[Tuple[str, float, float, int]]:
    """Condition bank for a focus.  A liquidity run weights the sweep and
    order-flow clauses three to one so drift stays on theme, without walling off
    the classic features a hybrid rule still needs."""
    base = _CONDITION_BANK + (_EXIT_ONLY_BANK if exit_side else [])
    if focus == "liquidity":
        return _LIQUIDITY_BANK * 3 + base
    return base + _LIQUIDITY_BANK


def random_condition(rng: random.Random, *, exit_side: bool = False,
                     focus: str = "all") -> str:
    """One random comparison drawn from the feature bank."""
    if focus == "liquidity" and rng.random() < 0.15:
        return f"{rng.choice(_FLAGS)} == {rng.choice([0, 1])}"
    if rng.random() < 0.12:
        crosses = _CROSSES + _LIQUIDITY_CROSSES * (3 if focus == "liquidity" else 1)
        return rng.choice(crosses)
    bank = _bank_for(focus, exit_side)
    feat, lo, hi, dec = rng.choice(bank)
    value = round(rng.uniform(lo, hi), dec)
    if dec == 0:
        value = int(value)
    op = rng.choice(["<", ">"])
    return f"{feat} {op} {value}"


def random_rule(rng: random.Random, *, exit_side: bool = False,
                focus: str = "all") -> str:
    """One to three conditions joined by and/or."""
    parts = [random_condition(rng, exit_side=exit_side, focus=focus)]
    while len(parts) < 3 and rng.random() < 0.45:
        parts.append(random_condition(rng, exit_side=exit_side, focus=focus))
    joiner = " and " if (exit_side is False or rng.random() < 0.5) else " or "
    return joiner.join(parts)


# ------------------------------------------------------------------- mutation

def _jitter_number(match: "re.Match[str]", rng: random.Random) -> str:
    raw = match.group(0)
    value = float(raw)
    if value == 0:
        return f"{rng.uniform(-0.05, 0.05):.3f}"
    scaled = value * rng.uniform(0.7, 1.35)
    if "." not in raw:
        return str(max(1, int(round(scaled))))
    decimals = len(raw.split(".")[1])
    return f"{round(scaled, max(decimals, 2))}"


def mutate_rule_text(rule: str, rng: random.Random) -> str:
    """Perturb thresholds and comparison operators inside a rule string."""
    out = _NUMBER_RE.sub(lambda m: _jitter_number(m, rng) if rng.random() < 0.6 else m.group(0), rule)
    if rng.random() < 0.15:
        for op in sorted(_OPS, key=len, reverse=True):
            if f" {op} " in out:
                out = out.replace(f" {op} ", f" {rng.choice(_OPS)} ", 1)
                break
    return out


def _mutate_risk(risk: RiskParams, rng: random.Random) -> RiskParams:
    d = risk.to_dict()
    for key in rng.sample(list(d), k=rng.randint(1, 3)):
        value = d[key]
        if key in ("max_positions", "max_hold_bars", "min_hold_bars", "cooldown_bars"):
            delta = rng.choice([-3, -2, -1, 1, 2, 3])
            d[key] = max(0, int(value) + delta)
        elif value == 0:
            d[key] = round(rng.uniform(0.03, 0.2), 3)
        else:
            d[key] = round(float(value) * rng.uniform(0.7, 1.35), 4)
    return RiskParams.from_dict(d)


def mutate(genome: Genome, rng: random.Random, *, generation: int = 0,
           strength: float = 1.0, focus: str = "all") -> Genome:
    """Return a mutated copy.  Never mutates in place."""
    child = genome.copy(generation=generation, origin="mutation",
                        parents=[genome.id], rationale="random mutation")
    child.name = _mutated_name(genome.name, rng)

    ops: List[Callable[[], None]] = []

    def tweak_entry() -> None:
        r = rng.choice(child.entry_rules)
        r.when = mutate_rule_text(r.when, rng)

    def tweak_exit() -> None:
        r = rng.choice(child.exit_rules)
        r.when = mutate_rule_text(r.when, rng)

    def tweak_weight() -> None:
        r = rng.choice(child.entry_rules)
        r.weight = max(0.02, min(1.0, r.weight * rng.uniform(0.6, 1.5)))

    def add_entry() -> None:
        if len(child.entry_rules) < 4:
            child.entry_rules.append(EntryRule(random_rule(rng, focus=focus),
                                               round(rng.uniform(0.1, 0.5), 2),
                                               "mutation: new entry"))

    def add_exit() -> None:
        if len(child.exit_rules) < 4:
            child.exit_rules.append(ExitRule(random_rule(rng, exit_side=True, focus=focus),
                                             "mutation: new exit"))

    def drop_entry() -> None:
        if len(child.entry_rules) > 1:
            child.entry_rules.pop(rng.randrange(len(child.entry_rules)))

    def drop_exit() -> None:
        if len(child.exit_rules) > 1:
            child.exit_rules.pop(rng.randrange(len(child.exit_rules)))

    def narrow_entry() -> None:
        r = rng.choice(child.entry_rules)
        r.when = f"({r.when}) and {random_condition(rng, focus=focus)}"

    def widen_entry() -> None:
        r = rng.choice(child.entry_rules)
        r.when = f"({r.when}) or {random_condition(rng, focus=focus)}"

    def risk_op() -> None:
        child.risk = _mutate_risk(child.risk, rng)

    weights = [(tweak_entry, 5), (tweak_exit, 4), (tweak_weight, 3), (risk_op, 4),
               (add_entry, 2), (add_exit, 2), (drop_entry, 1), (drop_exit, 1),
               (narrow_entry, 2), (widen_entry, 2)]
    ops = [op for op, w in weights for _ in range(w)]

    count = max(1, int(round(rng.randint(1, 3) * strength)))
    for _ in range(count):
        rng.choice(ops)()

    if not _compiles(child):
        return genome.copy(generation=generation, origin="mutation",
                           parents=[genome.id], rationale="mutation reverted (invalid)")
    return child


def crossover(a: Genome, b: Genome, rng: random.Random, *, generation: int = 0,
              focus: str = "all") -> Genome:
    """Blend two parents: entries from one side, exits from the other, mixed risk."""
    child = a.copy(generation=generation, origin="crossover", parents=[a.id, b.id],
                   rationale=f"crossover of {a.name!r} and {b.name!r}")
    child.name = f"{a.name.split()[0]}-{b.name.split()[-1]}"
    child.thesis = (a.thesis if a.thesis.strip() == b.thesis.strip()
                    else f"{a.thesis} Combined with: {b.thesis}").strip()[:1200]

    # Draw from both parents' rule pools, dropping rules that duplicate one
    # already taken — two similar parents should not produce a child that says
    # the same thing three times.
    pool_entries = [EntryRule(r.when, r.weight, r.note) for r in a.entry_rules + b.entry_rules]
    pool_exits = [ExitRule(r.when, r.note) for r in a.exit_rules + b.exit_rules]
    rng.shuffle(pool_entries)
    rng.shuffle(pool_exits)
    child.entry_rules = _dedupe(pool_entries)[:3]
    child.exit_rules = _dedupe(pool_exits)[:3]

    ra, rb = a.risk.to_dict(), b.risk.to_dict()
    child.risk = RiskParams.from_dict({k: (ra[k] if rng.random() < 0.5 else rb[k]) for k in ra})

    if not _compiles(child):
        return mutate(a, rng, generation=generation, focus=focus)
    return child


def _dedupe(rules: List) -> List:
    seen = set()
    out = []
    for rule in rules:
        key = rule.when.strip()
        if key not in seen:
            seen.add(key)
            out.append(rule)
    return out


def _compiles(genome: Genome) -> bool:
    try:
        compile_genome(genome)
        return True
    except GenomeError:
        return False


_ADJECTIVES = ["Sharper", "Patient", "Bolder", "Leaner", "Wider", "Tighter", "Faster",
               "Calmer", "Greedier", "Cautious", "Adaptive", "Stubborn"]


def _mutated_name(name: str, rng: random.Random) -> str:
    base = re.sub(r"^(?:%s)\s+" % "|".join(_ADJECTIVES), "", name)
    return f"{rng.choice(_ADJECTIVES)} {base}"[:80]


# ---------------------------------------------------------------- seeding

def seed_population(size: int, rng: random.Random, *, generation: int = 0,
                    focus: str = "all") -> List[Genome]:
    """Generation 0: every archetype once, then jittered variants to fill out
    the population, then a tail of fully random genomes for diversity."""
    out: List[Genome] = []
    for name, thesis, entries, exits, risk in archetypes_for(focus):
        g = Genome(
            name=name, thesis=thesis,
            entry_rules=[EntryRule(_repair(e), round(1.0 / max(len(entries), 1) * 0.5, 2),
                                   "archetype") for e in entries],
            exit_rules=[ExitRule(_repair(e), "archetype") for e in exits],
            risk=RiskParams.from_dict(risk), generation=generation, origin="seed",
            rationale="hand-written archetype",
        )
        if _compiles(g):
            out.append(g)
        if len(out) >= size:
            return out[:size]

    base = list(out)
    while len(out) < size:
        if rng.random() < 0.75 and base:
            parent = rng.choice(base)
            child = mutate(parent, rng, generation=generation, strength=1.5, focus=focus)
            child.origin = "seed"
            child.rationale = f"jittered variant of {parent.name!r}"
            out.append(child)
        else:
            out.append(random_genome(rng, generation=generation, focus=focus))
    return out[:size]


def random_genome(rng: random.Random, *, generation: int = 0,
                  focus: str = "all") -> Genome:
    """A genome assembled entirely from random clauses."""
    for _ in range(20):
        g = Genome(
            name=f"Random {rng.randrange(10_000):04d}",
            thesis="randomly generated; no prior belief",
            entry_rules=[EntryRule(random_rule(rng, focus=focus),
                                   round(rng.uniform(0.1, 0.5), 2), "random")
                         for _ in range(rng.randint(1, 2))],
            exit_rules=[ExitRule(random_rule(rng, exit_side=True, focus=focus), "random")
                        for _ in range(rng.randint(1, 2))],
            risk=RiskParams.from_dict({
                "max_position_pct": round(rng.uniform(0.1, 0.6), 2),
                "max_positions": rng.randint(1, 8),
                "max_gross_exposure": round(rng.uniform(0.5, 1.0), 2),
                "stop_loss_pct": round(rng.choice([0.0, 0.05, 0.08, 0.12, 0.2]), 3),
                "take_profit_pct": round(rng.choice([0.0, 0.0, 0.15, 0.3]), 3),
                "trailing_stop_pct": round(rng.choice([0.0, 0.0, 0.08, 0.15]), 3),
                "max_hold_bars": rng.choice([0, 0, 10, 30, 90]),
                "min_hold_bars": rng.choice([0, 0, 2, 5]),
                "cooldown_bars": rng.choice([0, 0, 2, 5]),
            }),
            generation=generation, origin="seed", rationale="random genome",
        )
        if _compiles(g):
            return g
    raise GenomeError("could not build a valid random genome")  # pragma: no cover
