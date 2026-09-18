"""Liquidity-sweep and order-flow features, and the strategies built on them.

The load-bearing property here is lag-safety: a sweep is only a sweep because
the level it took out was set by *earlier* bars.  If any of these features could
see the current bar's own high in the level it compares against, every sweep
strategy in the population would be trading a look-ahead.
"""
import random

import numpy as np
import pytest

from evotrader import indicators as ind
from evotrader.cli import _config_from_args, build_parser
from evotrader.config import EvolutionConfig
from evotrader.data import Bars, Universe, synthetic_bars
from evotrader.dsl import compile_rule
from evotrader.features import (FEATURE_DOCS, FEATURE_SET, LIQUIDITY_FEATURES,
                                MARKET_FEATURES, build_features)
from evotrader.genome import EntryRule, ExitRule, Genome, RiskParams, compile_genome
from evotrader.evolution import Evolution
from evotrader.population import (LIQUIDITY_ARCHETYPES, archetypes_for, mutate,
                                  random_condition, seed_population, _repair)
from evotrader.prompts import build_breeding_prompt
from evotrader.runner import backtest_genome


def _universe(o, h, l, c, v=None, symbol="AAA"):
    n = len(c)
    dates = [f"2020-{i:05d}" for i in range(n)]
    volume = np.full(n, 1e6) if v is None else np.asarray(v, dtype=float)
    bars = Bars(symbol, dates, np.asarray(o, float), np.asarray(h, float),
                np.asarray(l, float), np.asarray(c, float), volume)
    return Universe({symbol: bars}, dates)


def _synthetic_universe(n=900, symbols=("AAA", "BBB"), gaps=False):
    bars = {s: synthetic_bars(s, n, seed=i + 1) for i, s in enumerate(symbols)}
    if gaps:
        bars = {s: _with_gaps(b, seed=i + 1) for i, (s, b) in enumerate(bars.items())}
    return Universe(bars, list(next(iter(bars.values())).dates))


def _with_gaps(bars, seed):
    """Synthetic bars open where the last one closed; real ones gap. Several
    liquidity features (gap_pct, true range, sweeps through the open) only have
    anything to read when overnight gaps exist."""
    rng = np.random.default_rng(seed)
    o = bars.close * (1.0 + rng.normal(0.0, 0.012, len(bars)))
    o[0] = bars.open[0]
    o[1:] = bars.close[:-1] * (1.0 + rng.normal(0.0, 0.012, len(bars) - 1))
    return Bars(bars.symbol, bars.dates, o, np.maximum(bars.high, o),
                np.minimum(bars.low, o), bars.close, bars.volume)


# ------------------------------------------------------------------ primitives

def test_shift_moves_values_forward_and_pads_with_nan():
    out = ind.shift(np.array([1.0, 2.0, 3.0]), 1)
    assert np.isnan(out[0]) and out[1] == 1.0 and out[2] == 2.0


def test_rolling_sum_matches_manual_window():
    out = ind.rolling_sum(np.arange(1.0, 6.0), 3)
    assert np.isnan(out[:2]).all()
    assert out[2] == 6.0 and out[-1] == 12.0


def test_bars_since_counts_from_the_event_bar():
    out = ind.bars_since(np.array([0.0, 1.0, 0.0, 0.0, 1.0]), cap=999.0)
    assert out[0] == 999.0        # never happened yet
    assert out[1] == 0.0          # the event bar itself
    assert list(out[2:]) == [1.0, 2.0, 0.0]


def test_obv_signs_volume_by_the_close():
    out = ind.obv([10.0, 11.0, 10.5], [100.0, 200.0, 50.0])
    assert out[0] == 0.0 and out[1] == 200.0 and out[2] == 150.0


# -------------------------------------------------------------------- features

def test_every_liquidity_feature_is_built_and_documented():
    fs = build_features(_synthetic_universe())
    built = fs.matrix["AAA"]
    for name in LIQUIDITY_FEATURES:
        assert name in built, f"{name} is declared but never computed"
        assert FEATURE_DOCS.get(name), f"{name} has no description for the breeder"
        assert name in FEATURE_SET and name in MARKET_FEATURES


def test_sweep_low_fires_only_when_the_level_is_taken_and_reclaimed():
    n = 60
    close = np.full(n, 100.0)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    # bar 40 pokes below the 20-bar low but closes back above it: a sweep.
    low[40] = 95.0
    # bar 50 breaks the low and closes there: a breakdown, not a sweep.
    low[50], close[50], high[50] = 94.0, 94.5, 98.0
    fs = build_features(_universe(close, high, low, close))
    f = fs.matrix["AAA"]
    assert f["sweep_low"][40] == 1.0
    assert f["sweep_low"][50] == 0.0 and f["breakdown_20"][50] == 1.0
    assert f["sweep_low"].sum() == 1.0
    assert f["sweep_low_depth"][40] > 0.0
    assert f["bars_since_sweep_low"][40] == 0.0 and f["bars_since_sweep_low"][43] == 3.0
    assert f["bars_since_sweep_low"][10] == 999.0


def test_sweep_high_fires_when_the_high_is_taken_and_rejected():
    n = 60
    close = np.full(n, 100.0)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    high[40] = 106.0                       # runs the buy stops
    fs = build_features(_universe(close, high, low, close))
    f = fs.matrix["AAA"]
    assert f["sweep_high"][40] == 1.0 and f["sweep_high"].sum() == 1.0
    assert f["upper_wick"][40] > 0.5


def test_a_bar_cannot_sweep_its_own_level():
    """The pool levels are built from shifted data, so a single runaway bar
    makes a new extreme rather than sweeping the extreme it just set."""
    n = 60
    close = np.full(n, 100.0)
    high, low = np.full(n, 101.0), np.full(n, 99.0)
    low[40], close[40] = 90.0, 100.0
    f = build_features(_universe(close, high, low, close)).matrix["AAA"]
    assert f["prior_low_20"][40] == 99.0            # not the 90.0 of this bar
    assert f["prior_low_20"][41] == 90.0            # visible only from the next bar


def test_liquidity_features_never_look_ahead():
    """Recomputing on a truncated history must not change any past value."""
    universe = _synthetic_universe(n=700)
    full = build_features(universe).matrix["AAA"]
    cut = 600
    truncated = build_features(universe.slice(0, cut)).matrix["AAA"]
    i = cut - 1                       # the last bar both runs can see
    for name in LIQUIDITY_FEATURES:
        a, b = full[name][i], truncated[name][i]
        assert (np.isnan(a) and np.isnan(b)) or a == b, f"{name} depends on the future"


def test_bar_internals_have_the_expected_scale():
    f = build_features(_synthetic_universe()).matrix["AAA"]
    for name, lo, hi in [("clv", -1.0, 1.0), ("upper_wick", 0.0, 1.0),
                         ("lower_wick", 0.0, 1.0), ("body_pct", 0.0, 1.0),
                         ("cmf20", -1.0, 1.0), ("obv_slope", -1.0, 1.0),
                         ("volume_below_pct", 0.0, 1.0)]:
        series = f[name][~np.isnan(f[name])]
        assert series.min() >= lo - 1e-9 and series.max() <= hi + 1e-9, name


def test_clv_and_net_flow_sign_with_where_the_bar_closed():
    n = 40
    close = np.array([100.0] * n)
    high, low = np.full(n, 101.0), np.full(n, 99.0)
    close[-1], high[-1], low[-1] = 101.0, 101.0, 99.0     # closes on its high
    f = build_features(_universe(close, high, low, close)).matrix["AAA"]
    assert f["clv"][-1] == 1.0 and f["net_flow"][-1] > 0
    assert f["clv"][-2] == 0.0                            # closed mid-range


def test_fair_value_gap_needs_an_untraded_three_bar_window():
    n = 40
    close = np.full(n, 100.0)
    high, low = np.full(n, 101.0), np.full(n, 99.0)
    high[20], low[20], close[20] = 108.0, 104.0, 106.0    # jumps clear of bar 18
    f = build_features(_universe(close, high, low, close)).matrix["AAA"]
    assert f["fvg_up"][20] == 1.0
    assert f["bars_since_fvg_up"][22] == 2.0


def test_absorption_needs_volume_without_range():
    universe = _synthetic_universe()
    f = build_features(universe).matrix["AAA"]
    fired = f["absorption"] == 1.0
    assert fired.any(), "absorption never fires on ordinary data"
    assert (f["volume_ratio"][fired] > 1.5).all()
    assert (f["range_atr"][fired] < 0.8).all()


# ----------------------------------------------------------------- strategies

def test_every_liquidity_archetype_compiles():
    for name, thesis, entries, exits, risk in LIQUIDITY_ARCHETYPES:
        genome = Genome(
            name=name, thesis=thesis,
            entry_rules=[EntryRule(_repair(e), 0.25, "") for e in entries],
            exit_rules=[ExitRule(_repair(e), "") for e in exits],
            risk=RiskParams.from_dict(risk))
        compile_genome(genome)


def test_liquidity_archetypes_actually_trade():
    """A seed that never fires teaches the breeder nothing.

    Two synthetic regimes, because neither alone is a market: the smooth walk
    has no overnight gaps at all, and the gapped one pushes so much of each
    bar's range into the gap that wick-shaped signals thin out.  An archetype
    that trades in neither is dead on arrival.
    """
    universes = [_synthetic_universe(n=1200, symbols=("AAA", "BBB", "CCC")),
                 _synthetic_universe(n=1200, symbols=("AAA", "BBB", "CCC"), gaps=True)]
    windows = [(u, build_features(u)) for u in universes]
    silent = []
    for name, thesis, entries, exits, risk in LIQUIDITY_ARCHETYPES:
        genome = Genome(
            name=name, thesis=thesis,
            entry_rules=[EntryRule(_repair(e), 0.25, "") for e in entries],
            exit_rules=[ExitRule(_repair(e), "") for e in exits],
            risk=RiskParams.from_dict(risk))
        if not any(backtest_genome(genome, u, f).journal.trades for u, f in windows):
            silent.append(name)
    assert not silent, f"archetypes that never traded: {silent}"


def test_liquidity_focus_seeds_from_the_liquidity_library():
    names = {a[0] for a in LIQUIDITY_ARCHETYPES}
    population = seed_population(20, random.Random(11), focus="liquidity")
    assert {g.name for g in population} & names
    assert [a[0] for a in archetypes_for("liquidity")[:len(names)]]
    # the unfocused library still carries them, just not first
    assert names <= {a[0] for a in archetypes_for("all")}


def test_focused_mutation_reaches_for_liquidity_features():
    rng = random.Random(5)
    liquid = set(LIQUIDITY_FEATURES)
    hits = sum(1 for _ in range(200)
               if liquid & compile_rule(random_condition(rng, focus="liquidity"),
                                        FEATURE_SET).features)
    assert hits > 120, f"only {hits}/200 focused clauses used a liquidity feature"


def test_mutation_keeps_genomes_valid_under_focus():
    rng = random.Random(2)
    genome = seed_population(4, rng, focus="liquidity")[0]
    for _ in range(50):
        genome = mutate(genome, rng, generation=1, focus="liquidity")
        compile_genome(genome)


# ------------------------------------------------------------ run wiring

def test_config_accepts_the_liquidity_focus_and_rejects_nonsense():
    EvolutionConfig(focus="liquidity").validate()
    with pytest.raises(ValueError):
        EvolutionConfig(focus="orderbook").validate()


def test_cli_focus_flag_reaches_the_config():
    args = build_parser().parse_args(["run", "--focus", "liquidity", "--offline"])
    assert _config_from_args(args).focus == "liquidity"


def test_the_breeder_is_briefed_on_the_focus():
    kwargs = dict(generation=3, elites=[], evals=[], history=[], n_offspring=6)
    focused = build_breeding_prompt(focus="liquidity", **kwargs)
    plain = build_breeding_prompt(**kwargs)
    assert "FOCUS: LIQUIDITY SWEEPS AND ORDER FLOW" in focused
    assert "FOCUS: LIQUIDITY" not in plain
    # the vocabulary itself is always documented, focus or not
    for prompt in (focused, plain):
        assert "sweep_low:" in prompt and "cmf20:" in prompt


def test_a_focused_run_seeds_and_breeds_on_theme(tmp_path):
    cfg = EvolutionConfig(
        symbols=["AAA", "BBB", "CCC"], offline=True, population=12, generations=2,
        elites=3, survivor_reports=3, breeder="mutation", focus="liquidity", seed=5,
        verbose=False, workers=1, validate_top=3, db_path=str(tmp_path / "run.sqlite"))
    evolution = Evolution(cfg)
    assert len(evolution.run()) == 2
    liquid = set(LIQUIDITY_FEATURES)
    on_theme = 0
    for genome in evolution.population:
        used = set().union(*(rule.features for rule, _ in compile_genome(genome).entries))
        on_theme += bool(used & liquid)
    assert on_theme > len(evolution.population) // 2, (
        f"only {on_theme}/{len(evolution.population)} agents entered on a "
        f"liquidity signal after a focused run")
