"""Leveraged-ETF grind pieces: synthetic funds, dollar fitness, fund Pine."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from evotrader.data import Bars
from evotrader.fitness import FitnessConfig, compute_metrics, fitness_score
from evotrader.genome import Genome
from evotrader.pine import genome_to_pine
from evotrader.styles import get_style

ROOT = Path(__file__).resolve().parents[1]


def _synth_module():
    spec = importlib.util.spec_from_file_location("synth", ROOT / "strategies" / "etf" / "synth.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_synthetic_2x_fund_moves_twice_its_stock_inside_the_day():
    synth = _synth_module()
    d = ["2026-01-02", "2026-01-05"]
    u = Bars("X", d, np.array([100.0, 101.0]), np.array([100.0, 104.0]), np.array([100.0, 98.0]),
             np.array([100.0, 102.0]), np.array([1.0, 1.0]))
    b = synth.synth(u, 2.0, "X.2X")
    drag = (0.01 + (3.9 / 100 + 0.03)) / 252
    assert b.close[1] == pytest.approx(100 * (1 + 2 * 0.02 - drag))
    assert b.open[1] == pytest.approx(102.0) and b.high[1] == pytest.approx(108.0)
    assert b.low[1] == pytest.approx(96.0)
    inv = synth.synth(u, -1.0, "X.-1X")
    assert inv.high[1] == pytest.approx(102.0) and inv.low[1] == pytest.approx(96.0)   # high from the stock's low


def test_the_dollar_and_consistency_terms_pay_for_average_and_weak_quarters():
    rng = np.random.default_rng(3)
    eq = 25_000 * np.cumprod(1 + rng.normal(0.002, 0.01, 400))
    m = compute_metrics(list(eq), [])
    assert m.mean_day == pytest.approx(float(np.mean(eq[1:] / eq[:-1] - 1)))
    assert m.p25_quarter != 0.0
    base = fitness_score(m, FitnessConfig(min_trades=0))
    more = fitness_score(m, FitnessConfig(min_trades=0, return_weight=1.0, consistency_weight=2.0))
    assert more == pytest.approx(base + m.mean_day * 252 + 2.0 * m.p25_quarter * 252)


def test_the_etf_style_trades_the_whole_account():
    st = get_style("etf_full")
    assert st.fixed_size == 1.0 and len(st.archetypes) >= 10


def test_a_fund_pine_script_puts_the_whole_account_in_each_trade():
    g = Genome.from_dict({"name": "Dip", "entry_rules": [{"when": "ret1 < -0.05 and close > sma50", "weight": 1.0}],
                          "exit_rules": [{"when": "bars_held >= 3"}], "risk": {"stop_loss_pct": 0.1}})
    src = genome_to_pine(g, fund="SOXL")
    assert "default_qty_type=strategy.percent_of_equity, default_qty_value=100" in src
    assert 'strategy.entry("L", strategy.long, comment="in", alert_message=' in src
    assert "daily SOXL chart" in src and "contracts" not in src


def test_a_pine_script_alerts_at_the_close_for_the_next_open():
    g = Genome.from_dict({"name": "Dip", "entry_rules": [{"when": "ret1 < -0.05 and close > sma50", "weight": 1.0}],
                          "exit_rules": [{"when": "bars_held >= 3"}], "risk": {"stop_loss_pct": 0.1}})
    src = genome_to_pine(g, fund="SOXL", title="Dip")
    assert 'alert("Dip: buy " + syminfo.ticker + " at the next open", alert.freq_once_per_bar_close)' in src
    assert 'alert("Dip: sell " + syminfo.ticker + " at the next open", alert.freq_once_per_bar_close)' in src
