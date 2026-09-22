import numpy as np

from evotrader.fitness import (Evaluation, FitnessConfig, Metrics, compute_metrics,
                               fitness_score, rank)
from evotrader.journal import Trade


def _trade(ret, pnl, bars=10):
    return Trade("AAA", "d0", "d1", 100.0, 100.0 * (1 + ret), 10.0, pnl, ret, bars,
                 "in", "out")


def test_metrics_on_a_simple_curve():
    equity = list(np.linspace(100_000, 150_000, 252))
    m = compute_metrics(equity, [_trade(0.1, 100.0), _trade(-0.05, -50.0)],
                        benchmark=[100_000, 120_000], turnover=4.0)
    assert abs(m.total_return - 0.5) < 1e-9
    assert m.trades == 2 and abs(m.win_rate - 0.5) < 1e-9
    assert abs(m.profit_factor - 2.0) < 1e-9
    assert abs(m.excess_return - 0.3) < 1e-9
    assert m.max_drawdown == 0.0
    assert m.turnover == 4.0     # one year of bars, so annualised == raw


def test_turnover_is_annualised():
    equity = list(np.linspace(100.0, 110.0, 504))    # two years
    m = compute_metrics(equity, [], turnover=10.0)
    assert abs(m.turnover - 5.0) < 1e-6


def test_drawdown_is_measured_from_the_peak():
    m = compute_metrics([100.0, 200.0, 100.0], [])
    assert abs(m.max_drawdown + 0.5) < 1e-9


def test_fitness_penalises_inactivity_and_deep_drawdowns():
    cfg = FitnessConfig()
    active = Metrics(sharpe=1.0, trades=50, years=1.0)
    idle = Metrics(sharpe=1.0, trades=0, years=1.0)
    drawn = Metrics(sharpe=1.0, trades=50, max_drawdown=-0.50, years=1.0)
    assert fitness_score(active, cfg) > fitness_score(idle, cfg)
    assert fitness_score(active, cfg) > fitness_score(drawn, cfg)


def test_fitness_rewards_beating_buy_and_hold():
    cfg = FitnessConfig()
    beat = Metrics(sharpe=1.0, trades=50, excess_return=0.30, years=1.0)
    lag = Metrics(sharpe=1.0, trades=50, excess_return=-0.30, years=1.0)
    assert fitness_score(beat, cfg) - fitness_score(lag, cfg) > 0.5


def test_fitness_ignores_nan_and_inf():
    assert fitness_score(Metrics(sharpe=float("nan"), trades=50, years=1.0)) == 0.0
    assert fitness_score(Metrics(sharpe=float("inf"), trades=50, years=1.0)) == 0.0


def test_rank_sorts_best_first_and_failures_last():
    good = Evaluation("a", "good", 0, 1.0, Metrics())
    bad = Evaluation("b", "bad", 0, 5.0, Metrics(), error="boom")
    mid = Evaluation("c", "mid", 0, 0.5, Metrics())
    assert [e.genome_id for e in rank([mid, bad, good])] == ["a", "c", "b"]


def test_worst_day_is_the_minimum_bar_return():
    m = compute_metrics([100.0, 110.0, 99.0, 104.0], [])
    assert abs(m.worst_day - (99.0 / 110.0 - 1.0)) < 1e-9


def test_recency_score_blends_toward_the_tail():
    from evotrader.fitness import blended_score, recency_score
    rng = np.random.default_rng(3)
    n = 400
    equity = list(100_000 * np.cumprod(1 + rng.normal(0.0004, 0.01, n)))
    dates = [f"d{i:04d}" for i in range(n)]
    trades = [_trade(0.02 if i % 3 else -0.01, 50.0 if i % 3 else -25.0) for i in range(60)]
    for k, t in enumerate(trades):
        t.exit_date = dates[int(k * n / 60)]
    cfg = FitnessConfig(recent_bars=126, recent_weight=0.5, min_trades=10)
    full = fitness_score(compute_metrics(equity, trades), cfg)
    recent = recency_score(equity, trades, dates, cfg)
    assert recent is not None
    tail_trades = [t for t in trades if t.exit_date > dates[-127]]
    manual = fitness_score(compute_metrics(equity[-127:], tail_trades),
                           FitnessConfig(**{**cfg.to_dict(), "min_trades": 3}))
    assert abs(recent - manual) < 1e-9
    assert abs(blended_score(full, recent, cfg) - (0.5 * full + 0.5 * recent)) < 1e-9
    assert blended_score(full, recent, FitnessConfig()) == full          # weight 0: unchanged
    assert recency_score(equity[:50], trades, dates[:50], cfg) is None   # too short a curve
