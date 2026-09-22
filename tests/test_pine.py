"""The genome -> Pine translation keeps the engine's meaning."""
import pytest

from evotrader.dsl import parse
from evotrader.genome import Genome
from evotrader.pine import PineError, _Emitter, _definitions, genome_to_pine, warmup_bars


def emit(rule):
    em = _Emitter()
    return em.boolean(parse(rule), 0, 1), em.names


def test_prev_is_one_bar_back_however_deeply_nested():
    s, _ = emit("low < prev(low) and prev(low) < prev(prev(low))")
    assert "(low < low[1])" in s
    assert "(low[1] < low[1])" in s          # the engine's prev(prev(x)) is x one bar back


def test_cross_above_compares_this_bar_with_the_last():
    s, names = emit("cross_above(close, sma50)")
    assert s == "(close > f_sma50 and close[1] <= f_sma50[1])"
    assert names == {"close", "sma50"}


def test_division_by_zero_is_zero_and_comparisons_of_equality_are_tolerant():
    s, _ = emit("volume / volume_ratio > 2 and day_of_week == 0")
    assert "(f_volume_ratio != 0 ? volume / f_volume_ratio : 0.0)" in s
    assert "math.abs(f_day_of_week - 0.0) <= 1e-9" in s


def test_numbers_become_booleans_and_booleans_numbers_where_needed():
    s, _ = emit("rsi7")
    assert s == "(f_rsi7 != 0)"
    s, _ = emit("(close > open) + 1 > 1")
    assert "((close > open) ? 1.0 : 0.0)" in s


def test_definitions_come_with_their_dependencies_in_order():
    lines = _definitions({"bb_pct", "zscore20", "macd_hist", "vol_ratio_20_60"})
    text = "\n".join(lines)
    assert lines[0].startswith("[f_macd, f_macd_signal, f_macd_hist] = ta.macd")
    assert text.index("f_sma20 =") < text.index("f_bb_upper =") < text.index("f_bb_pct =")
    assert text.index("f_ret1 =") < text.index("f_vol20 =") < text.index("f_vol_ratio_20_60 =")
    assert "ta.stdev(close, 20, false)" in text          # sample deviation, as the engine


def test_a_whole_genome_becomes_a_strategy_with_its_risk_rules():
    g = Genome.from_dict({
        "name": "Calm Trend", "thesis": "trend with a calm filter",
        "entry_rules": [{"when": "close > sma50 and vol20 < 0.25", "weight": 1.0}],
        "exit_rules": [{"when": "vol20 > 0.45"}],
        "risk": {"max_position_pct": 1.0, "stop_loss_pct": 0.042, "take_profit_pct": 0.071,
                 "trailing_stop_pct": 0.051, "max_hold_bars": 13, "cooldown_bars": 2}})
    src = genome_to_pine(g)
    assert src.startswith("//@version=6")
    assert 'strategy("Calm Trend [evotrader]"' in src
    assert "process_orders_on_close=false" in src
    assert "trailPct > 0 and f_position_drawdown <= -trailPct" in src
    assert "var float posPeak = na" in src
    assert "cooldown <= 0 or bar_index - lastExitBar >= cooldown" in src
    assert f"warm = bar_index >= {warmup_bars({'close', 'sma50', 'vol20', 'position_drawdown'})}" in src


def test_intraday_features_are_refused_for_a_daily_translation():
    g = Genome.from_dict({"name": "Intraday", "entry_rules": [{"when": "is_first_hour == 1", "weight": 1.0}],
                          "exit_rules": [{"when": "bars_held >= 1"}], "risk": {}})
    with pytest.raises(PineError):
        genome_to_pine(g)
