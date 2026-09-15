"""A named, parameterised strategy library written in evotrader's rule language.

Evolution invents its own genomes, but a backtester is far more useful when a
caller can say ``rsi_pullback`` instead of writing rules.  Each spec here is a
template plus default parameters; :func:`build` substitutes the parameters and
returns a :class:`~evotrader.genome.Genome` that runs through the same engine
as any evolved agent — same next-open fills, same costs, same portfolio limits.

Parameters are what makes a sweep possible: ``build("rsi", {"oversold": 25})``
differs from the default only in the threshold, so :mod:`evotrader.backtest_api`
can grid-search a strategy without any of these definitions changing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .genome import EntryRule, ExitRule, Genome, RiskParams, compile_genome
from .population import ARCHETYPES


class StrategyError(ValueError):
    pass


@dataclass(frozen=True)
class StrategySpec:
    """One strategy: rule templates, default parameters and risk limits."""

    name: str
    family: str
    thesis: str
    entries: Tuple[Tuple[str, float], ...]
    exits: Tuple[str, ...]
    params: Mapping[str, float] = field(default_factory=dict)
    risk: Mapping[str, float] = field(default_factory=dict)

    def render(self, overrides: Mapping[str, Any] | None = None) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Substitute parameters into the templates."""
        params = dict(self.params)
        for key, value in (overrides or {}).items():
            if key not in params:
                raise StrategyError(
                    f"{self.name} has no parameter {key!r}; "
                    f"it takes {', '.join(sorted(params)) or 'none'}")
            params[key] = value
        try:
            entries = [tpl.format(**params) for tpl, _ in self.entries]
            exits = [tpl.format(**params) for tpl in self.exits]
        except KeyError as exc:  # a template referencing an undeclared parameter
            raise StrategyError(f"{self.name}: template needs parameter {exc}") from exc
        return entries, exits, params


#: Every strategy, keyed by name.  ``family`` groups them for readability only.
SPECS: Dict[str, StrategySpec] = {}


def _register(spec: StrategySpec) -> None:
    SPECS[spec.name] = spec


# ── Mean reversion ────────────────────────────────────────────────────────────
_register(StrategySpec(
    "rsi", "mean-reversion",
    "Buy oversold, sell into the bounce.",
    entries=(("rsi14 < {oversold}", 0.25),),
    exits=("rsi14 > {overbought}", "bars_held > {max_hold}"),
    params={"oversold": 30, "overbought": 60, "max_hold": 40},
    risk={"max_position_pct": 0.25, "stop_loss_pct": 0.10}))

_register(StrategySpec(
    "rsi_pullback", "mean-reversion",
    "Dip-buy only inside a confirmed uptrend; the trend filter is the edge.",
    entries=(("sma50 > sma200 and rsi14 < {oversold}", 0.30),),
    exits=("rsi14 > {overbought}", "close < sma50"),
    params={"oversold": 40, "overbought": 70},
    risk={"max_position_pct": 0.30, "stop_loss_pct": 0.08, "cooldown_bars": 5}))

_register(StrategySpec(
    "bollinger", "mean-reversion",
    "Price stretched below the band snaps back to the mean.",
    entries=(("bb_pct < {entry_pct}", 0.25),),
    exits=("bb_pct > {exit_pct}", "bars_held > {max_hold}"),
    params={"entry_pct": 0.05, "exit_pct": 0.75, "max_hold": 20},
    risk={"max_position_pct": 0.25, "stop_loss_pct": 0.07}))

_register(StrategySpec(
    "zscore_reversion", "mean-reversion",
    "Fade statistically extreme moves away from the 20-bar mean.",
    entries=(("zscore20 < {entry_z} and close > sma200", 0.25),),
    exits=("zscore20 > {exit_z}", "bars_held > {max_hold}"),
    params={"entry_z": -2.0, "exit_z": 0.5, "max_hold": 25},
    risk={"max_position_pct": 0.25, "stop_loss_pct": 0.08}))

# ── Trend following ───────────────────────────────────────────────────────────
_register(StrategySpec(
    "macd", "trend",
    "Trade the momentum turn signalled by a MACD cross.",
    entries=(("cross_above(macd, macd_signal)", 0.25),),
    exits=("cross_below(macd, macd_signal)",),
    params={},
    risk={"max_position_pct": 0.25, "stop_loss_pct": 0.10}))

_register(StrategySpec(
    "ma_cross", "trend",
    "Golden/death cross on the 20 and 50 bar averages.",
    entries=(("cross_above(sma20, sma50)", 0.30),),
    exits=("cross_below(sma20, sma50)",),
    params={},
    risk={"max_position_pct": 0.30, "stop_loss_pct": 0.10}))

_register(StrategySpec(
    "triple_ma", "trend",
    "A fast cross, taken only above the long-term average.",
    entries=(("cross_above(sma20, sma50) and close > sma200", 0.30),),
    exits=("cross_below(sma20, sma50)", "close < sma200"),
    params={},
    risk={"max_position_pct": 0.30, "stop_loss_pct": 0.10}))

_register(StrategySpec(
    "trend_follow", "trend",
    "Hold what is already going up; step aside when the trend breaks.",
    entries=(("close > sma50 and sma50 > sma200 and mkt_above_sma200 == 1", 0.34),),
    exits=("close < sma50", "position_return < {max_loss}"),
    params={"max_loss": -0.10},
    risk={"max_position_pct": 0.34, "max_positions": 3, "stop_loss_pct": 0.12}))

_register(StrategySpec(
    "momentum", "trend",
    "Buy the strongest quarterly momentum, cut it when it stalls.",
    entries=(("ret60 > {min_ret} and close > sma50", 0.34),),
    exits=("ret20 < {exit_ret}", "close < sma50"),
    params={"min_ret": 0.12, "exit_ret": -0.05},
    risk={"max_position_pct": 0.34, "max_positions": 3}))

# ── Breakout and volatility ───────────────────────────────────────────────────
_register(StrategySpec(
    "keltner_breakout", "breakout",
    "Close above an ATR envelope marks a genuine expansion, not noise.",
    entries=(("close > ema26 + {mult} * atr14", 0.25),),
    exits=("close < ema26", "position_return < {max_loss}"),
    params={"mult": 2.0, "max_loss": -0.08},
    risk={"max_position_pct": 0.25, "trailing_stop_pct": 0.10}))

_register(StrategySpec(
    "donchian_breakout", "breakout",
    "New highs on heavy volume tend to keep going.",
    entries=(("pct_of_52w_high > {threshold} and volume_ratio > {min_rvol}", 0.25),),
    exits=("close < sma20", "position_return < {max_loss}"),
    params={"threshold": 0.98, "min_rvol": 1.3, "max_loss": -0.07},
    risk={"max_position_pct": 0.25, "trailing_stop_pct": 0.12}))

_register(StrategySpec(
    "squeeze", "breakout",
    "Quiet markets precede expansion; buy the squeeze.",
    entries=(("vol_ratio_20_60 < {max_ratio} and close > sma50", 0.30),),
    exits=("vol_ratio_20_60 > {exit_ratio}", "position_return > {target}"),
    params={"max_ratio": 0.75, "exit_ratio": 1.4, "target": 0.15},
    risk={"max_position_pct": 0.30, "trailing_stop_pct": 0.08}))

# ── Regime ────────────────────────────────────────────────────────────────────
_register(StrategySpec(
    "regime_filter", "regime",
    "Full risk above the 200-day, flat below it.",
    entries=(("mkt_above_sma200 == 1 and dist_sma20 > 0", 0.50),),
    exits=("mkt_above_sma200 == 0", "dist_sma20 < {exit_dist}"),
    params={"exit_dist": -0.03},
    risk={"max_position_pct": 0.50, "max_positions": 2}))

_register(StrategySpec(
    "buy_and_hold", "regime",
    "Own the universe throughout — the benchmark, expressed as a strategy.",
    entries=(("close > 0", 1.0),),
    # A genome must declare an exit; this one fires only on near-total loss,
    # so the position is held for the whole window.
    exits=("position_return < {ruin}",),
    params={"ruin": -0.99},
    risk={"max_position_pct": 1.0, "max_positions": 20, "stop_loss_pct": 0.0}))


def _register_archetypes() -> None:
    """Expose the seed archetypes under ``archetype:<name>``.

    They carry no parameters — they are fixed starting points for evolution —
    but backtesting them by name is the cheapest way to sanity-check a
    universe before spending a run on it.
    """
    for name, thesis, entries, exits, risk in ARCHETYPES:
        key = "archetype:" + name.lower().replace(" ", "_")
        _register(StrategySpec(
            key, "archetype", thesis,
            entries=tuple((rule.replace("{", "{{").replace("}", "}}"), 0.25)
                          for rule in entries),
            exits=tuple(rule.replace("{", "{{").replace("}", "}}") for rule in exits),
            params={}, risk=dict(risk)))


_register_archetypes()


def build(name: str, params: Mapping[str, Any] | None = None,
          risk: Mapping[str, Any] | None = None) -> Genome:
    """Instantiate a named strategy as a runnable genome.

    Raises :class:`StrategyError` if the name is unknown, a parameter is not
    one the strategy declares, or the rendered rules do not compile.
    """
    spec = SPECS.get(name)
    if spec is None:
        raise StrategyError(
            f"unknown strategy {name!r}; {len(SPECS)} available, "
            f"see list_strategies()")
    entries, exits, resolved = spec.render(params)
    risk_params = dict(spec.risk)
    risk_params.update(risk or {})
    label = spec.name
    if params:
        label += " (" + ", ".join(f"{k}={resolved[k]}" for k in sorted(params)) + ")"
    genome = Genome(
        name=label,
        thesis=spec.thesis,
        entry_rules=[EntryRule(rule, weight) for rule, (_, weight)
                     in zip(entries, spec.entries)],
        exit_rules=[ExitRule(rule) for rule in exits],
        risk=RiskParams.from_dict(risk_params),
        origin="library",
        rationale=f"{spec.family} strategy from evotrader's library",
    )
    compile_genome(genome)   # fail here, not deep inside a backtest
    return genome


def describe(name: str) -> Dict[str, Any]:
    """The spec for one strategy, as plain data."""
    spec = SPECS.get(name)
    if spec is None:
        raise StrategyError(f"unknown strategy {name!r}")
    return {
        "name": spec.name,
        "family": spec.family,
        "thesis": spec.thesis,
        "entries": [rule for rule, _ in spec.entries],
        "exits": list(spec.exits),
        "params": dict(spec.params),
        "risk": dict(spec.risk),
    }


def names(family: str | None = None) -> List[str]:
    """Strategy names, optionally restricted to one family."""
    return sorted(n for n, s in SPECS.items()
                  if family is None or s.family == family)


def families() -> List[str]:
    return sorted({s.family for s in SPECS.values()})
