import pytest

from evotrader import strategies
from evotrader.genome import compile_genome
from evotrader.population import ARCHETYPES
from evotrader.strategies import SPECS, StrategyError, build, describe, families, names


def test_every_strategy_compiles():
    """A library strategy that does not compile is worse than none at all."""
    broken = []
    for name in names():
        try:
            compile_genome(build(name))
        except Exception as exc:  # noqa: BLE001 - reporting every failure at once
            broken.append((name, str(exc)))
    assert broken == []


def test_every_archetype_is_registered():
    for archetype, *_ in ARCHETYPES:
        assert "archetype:" + archetype.lower().replace(" ", "_") in SPECS


def test_parameters_substitute_into_rules():
    genome = build("rsi", {"oversold": 22})
    assert genome.entry_rules[0].when == "rsi14 < 22"
    assert "oversold=22" in genome.name


def test_defaults_apply_when_no_params_given():
    assert build("rsi").entry_rules[0].when == "rsi14 < 30"


def test_unknown_parameter_is_rejected_with_the_valid_names():
    with pytest.raises(StrategyError) as exc:
        build("rsi", {"oversold_level": 22})
    assert "oversold" in str(exc.value)


def test_unknown_strategy_is_rejected():
    with pytest.raises(StrategyError):
        build("no_such_strategy")


def test_risk_overrides_merge_over_the_spec():
    genome = build("rsi", risk={"max_positions": 2})
    assert genome.risk.max_positions == 2
    assert genome.risk.stop_loss_pct == pytest.approx(0.10)  # from the spec


def test_archetype_braces_survive_rendering():
    """Archetype rules are literal; formatting must not eat their characters."""
    for name in names("archetype"):
        entries, exits, params = SPECS[name].render()
        assert params == {}
        assert all("{" not in rule for rule in entries + exits)


def test_describe_reports_the_spec():
    spec = describe("rsi_pullback")
    assert spec["family"] == "mean-reversion"
    assert "oversold" in spec["params"]
    assert any("rsi14" in rule for rule in spec["entries"])


def test_names_filter_by_family_and_families_are_covered():
    assert set(names("trend")) <= set(names())
    for family in families():
        assert names(family), f"{family} has no strategies"


def test_buy_and_hold_holds():
    """The benchmark-as-strategy must not exit on ordinary drawdowns."""
    genome = build("buy_and_hold")
    assert genome.exit_rules[0].when == "position_return < -0.99"


def test_compiled_genome_reports_only_the_features_its_rules_read():
    compiled = compile_genome(build("rsi"))
    assert compiled.feature_names == frozenset({"rsi14", "bars_held"})


def test_feature_names_unions_entries_and_exits():
    from evotrader.backtest_api import make_genome
    compiled = compile_genome(make_genome(
        entries=["rsi14 < 30 and close > sma200"],
        exits=["macd > macd_signal", "bars_held > 20"]))
    assert compiled.feature_names == frozenset(
        {"rsi14", "close", "sma200", "macd", "macd_signal", "bars_held"})


def test_feature_names_sees_through_functions():
    """cross_above reads its arguments on two bars; both must be requested."""
    from evotrader.backtest_api import make_genome
    compiled = compile_genome(make_genome(
        entries=["cross_above(sma20, sma50)"], exits=["close < prev(low)"]))
    assert {"sma20", "sma50", "close", "low"} <= compiled.feature_names
