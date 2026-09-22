"""Per-genome warm-up: a genome trades from the bar its own features exist."""
import numpy as np

from evotrader.data import Bars, Universe
from evotrader.evolution import Context, score_genome
from evotrader.features import build_features
from evotrader.fitness import FitnessConfig
from evotrader.genome import Genome, compile_genome
from evotrader.runner import backtest_genome, buy_and_hold


def _universe(n=400, seed=0):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.cumprod(1.0 + rng.normal(0.0005, 0.02, n))
    dates = [f"d{i:04d}" for i in range(n)]
    bars = Bars("AAA", dates, close * 0.995, close * 1.01, close * 0.99, close,
                np.full(n, 1e6))
    return Universe({"AAA": bars}, dates)


def _genome(rule, name="g"):
    return Genome.from_dict({
        "name": name,
        "entry_rules": [{"when": rule, "weight": 1.0}],
        "exit_rules": ["bars_held >= 2"],
        "risk": {"max_position_pct": 1.0, "max_positions": 1, "stop_loss_pct": 0.0},
    })


def test_warmup_for_follows_the_features_a_genome_reads():
    features = build_features(_universe())
    assert features.warmup >= 199
    assert features.warmup_for({"rsi7"}) < 30
    assert features.warmup_for({"sma20", "ret1"}) < 30
    assert features.warmup_for({"sma200"}) >= 199
    assert features.warmup_for({"pct_of_52w_high"}) >= 251
    assert features.warmup_for({"in_position", "bars_held"}) == 1   # portfolio: always defined
    assert features.warmup_for(set()) == 1
    assert compile_genome(_genome("rsi7 < 40 and bars_held < 1")).feature_names() \
        == frozenset({"rsi7", "bars_held"})


def test_fast_genome_trades_long_before_a_slow_one():
    universe = _universe()
    features = build_features(universe)
    fast = backtest_genome(_genome("rsi7 < 101", "fast"), universe, features)
    slow = backtest_genome(_genome("close > sma200 * 0.01", "slow"), universe, features)
    assert fast.start_bar < 30 <= 199 <= slow.start_bar
    assert fast.journal.trades and slow.journal.trades
    assert fast.journal.trades[0].entry_date < slow.journal.trades[0].entry_date
    # nothing a genome reads is undefined on the bar it starts trading
    for name in compile_genome(_genome("rsi7 < 101")).feature_names():
        if name in features.matrix["AAA"]:
            assert not np.isnan(features.matrix["AAA"][name][fast.start_bar])


def test_warmup_is_never_past_the_end_of_a_short_window():
    features = build_features(_universe(120))
    assert features.warmup_for({"sma200"}) <= 90
    assert features.warmup <= 90


def test_buy_and_hold_can_start_at_any_bar():
    universe = _universe()
    features = build_features(universe)
    full = buy_and_hold(universe, features, start=0)
    late = buy_and_hold(universe, features, start=100)
    default = buy_and_hold(universe, features)
    assert len(full) == 400 and len(late) == 300
    assert len(default) == 400 - features.warmup
    assert abs(full[0] - 100_000.0) < 1e-6 and abs(late[0] - 100_000.0) < 1e-6


def test_fast_genome_is_benchmarked_over_its_own_window():
    universe = _universe()
    features = build_features(universe)
    ctx = Context(train=universe, train_features=features,
                  train_benchmark=buy_and_hold(universe, features),
                  test=None, test_features=None, test_benchmark=None,
                  starting_cash=100_000.0, commission_bps=1.0, slippage_bps=5.0,
                  fitness=FitnessConfig())
    fast = _genome("rsi7 < 101", "fast")
    outcome = score_genome(fast, ctx)
    start = backtest_genome(fast, universe, features).start_bar
    own = buy_and_hold(universe, features, start=start)
    assert abs(outcome.metrics.benchmark_return - (own[-1] / own[0] - 1.0)) < 1e-9
    slow = score_genome(_genome("close > sma200 * 0.01", "slow"), ctx)
    glob = ctx.train_benchmark
    assert abs(slow.metrics.benchmark_return - (glob[-1] / glob[0] - 1.0)) < 1e-9
