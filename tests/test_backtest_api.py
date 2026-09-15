import pytest

from evotrader import backtest_api as api
from evotrader import strategies
from evotrader.backtest_api import (Costs, DataSpec, cache_info, clear_cache,
                                    compare, fold_indices, load_dataset,
                                    make_genome, optimize, run, slice_dataset,
                                    walk_forward)
from evotrader.data import DataError
from evotrader.genome import GenomeError


SYMBOLS = ["AAA", "BBB", "CCC"]


def _spec(**kw):
    base = dict(symbols=SYMBOLS, start="2015-01-01", end="2030-01-01", offline=True)
    base.update(kw)
    return DataSpec.of(**base)


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    yield
    clear_cache()


# ─── DataSpec ─────────────────────────────────────────────────────────────────

def test_spec_normalises_symbols():
    spec = DataSpec.of([" spy ", "qqq", "SPY"], "2015-01-01", "2020-01-01")
    assert spec.symbols == ("QQQ", "SPY")   # upper-cased, de-duplicated, sorted


def test_spec_is_hashable_so_it_can_key_the_cache():
    assert hash(_spec()) == hash(_spec())


def test_spec_rejects_an_empty_universe():
    with pytest.raises(DataError):
        DataSpec.of([" "], "2015-01-01", "2020-01-01")


# ─── Dataset cache ────────────────────────────────────────────────────────────

def test_dataset_is_memoised():
    first = load_dataset(_spec())
    assert load_dataset(_spec()) is first


def test_cache_evicts_least_recently_used(monkeypatch):
    monkeypatch.setattr(api, "MAX_CACHED_DATASETS", 2)
    load_dataset(_spec(start="2015-01-01"))
    load_dataset(_spec(start="2015-02-01"))
    load_dataset(_spec(start="2015-03-01"))
    assert cache_info()["entries"] == 2


def test_clear_cache_empties_it():
    load_dataset(_spec())
    clear_cache()
    assert cache_info()["entries"] == 0


# ─── make_genome ──────────────────────────────────────────────────────────────

def test_make_genome_from_a_named_strategy():
    assert make_genome("rsi").entry_rules[0].when == "rsi14 < 30"


def test_make_genome_from_plain_rules():
    genome = make_genome(entries=["rsi14 < 25"], exits=["rsi14 > 70"])
    assert genome.entry_rules[0].weight == pytest.approx(0.25)


def test_make_genome_accepts_weighted_entries():
    genome = make_genome(entries=[{"when": "rsi14 < 25", "weight": 0.5}],
                         exits=["rsi14 > 70"])
    assert genome.entry_rules[0].weight == pytest.approx(0.5)


def test_make_genome_needs_a_strategy_or_rules():
    with pytest.raises(strategies.StrategyError):
        make_genome()


def test_make_genome_rejects_unknown_features():
    with pytest.raises(GenomeError):
        make_genome(entries=["rsi14 < 30 and close > wishful_thinking"],
                    exits=["rsi14 > 70"])


# ─── run ──────────────────────────────────────────────────────────────────────

def test_run_reports_metrics_and_a_benchmark():
    row = run(make_genome("rsi"), load_dataset(_spec()))
    assert "error" not in row
    assert row["metrics"]["benchmark_return"] is not None
    assert row["period"]["bars"] > 0
    assert row["final_equity"] > 0


def test_run_can_include_trades_and_truncates_them():
    row = run(make_genome("rsi"), load_dataset(_spec()),
              include_trades=True, max_trades=3)
    assert row["trade_count"] >= len(row["trades"])
    if row["trade_count"] > 3:
        assert len(row["trades"]) == 3
        assert row["trades_truncated"] == row["trade_count"] - 3


def test_costs_reduce_the_final_equity():
    dataset = load_dataset(_spec())
    genome = make_genome("rsi")
    free = run(genome, dataset, Costs(commission_bps=0.0, slippage_bps=0.0))
    dear = run(genome, dataset, Costs(commission_bps=50.0, slippage_bps=50.0))
    assert dear["final_equity"] < free["final_equity"]
    assert dear["costs_paid"] > free["costs_paid"]


# ─── compare ──────────────────────────────────────────────────────────────────

def test_compare_ranks_descending_by_fitness():
    rows = compare([strategies.build(n) for n in ("rsi", "macd", "squeeze")],
                   load_dataset(_spec()))
    scores = [r["fitness"] for r in rows if "fitness" in r]
    assert scores == sorted(scores, reverse=True)


def test_compare_can_rank_by_any_metric():
    rows = compare([strategies.build(n) for n in ("rsi", "macd", "squeeze")],
                   load_dataset(_spec()), rank_by="sharpe")
    sharpes = [r["metrics"]["sharpe"] for r in rows]
    assert sharpes == sorted(sharpes, reverse=True)


# ─── folds and slicing ────────────────────────────────────────────────────────

def test_fold_indices_are_anchored_and_ordered():
    folds = fold_indices(2000, folds=3, test_frac=0.3)
    assert len(folds) == 3
    for _, tr_lo, tr_hi, te_lo, te_hi in folds:
        assert tr_lo == 0              # anchored: train always starts at the top
        assert tr_hi == te_lo          # train ends exactly where test begins
        assert te_lo < te_hi
    starts = [f[3] for f in folds]
    assert starts == sorted(starts)    # test windows march forward


def test_fold_indices_degrade_to_one_split_when_history_is_short():
    assert len(fold_indices(120, folds=3)) == 1


def test_slice_preserves_feature_values_exactly():
    """Slicing must be identical to the same bars of the full series —
    that equality is what makes it leak-free."""
    dataset = load_dataset(_spec())
    window = slice_dataset(dataset, 300, 600)
    assert window is not None
    symbol = dataset.features.symbols[0]
    full = dataset.features.matrix[symbol]["sma200"][300:600]
    assert (window.features.matrix[symbol]["sma200"] == full).all()


def test_slice_leaves_indicators_warm():
    dataset = load_dataset(_spec())
    window = slice_dataset(dataset, 800, 1000)
    assert window is not None
    assert window.features.warmup == 0     # warmup was consumed before bar 800


def test_slice_refuses_a_window_too_short_to_trade():
    assert slice_dataset(load_dataset(_spec()), 0, 5) is None


# ─── validation ───────────────────────────────────────────────────────────────

def test_walk_forward_reports_each_fold_and_says_what_it_measures():
    report = walk_forward(make_genome("rsi"), _spec(), folds=3)
    assert report["folds"]
    assert "consistency" in report
    assert "not overfitting" in report["note"]
    for fold in report["folds"]:
        if "skipped" not in fold:
            assert set(fold) == {"fold", "train", "test"}


def test_optimize_holds_out_a_window_the_search_never_saw():
    report = optimize("rsi", {"oversold": [25, 30, 35]}, _spec(), top=2)
    assert report["combinations_tested"] == 3
    assert report["train_window"] != report["test_window"]
    assert len(report["results"]) == 2
    assert "test" in report["results"][0]
    assert report["degradation"]["verdict"]


def test_optimize_explores_the_full_grid():
    report = optimize("rsi", {"oversold": [25, 30], "overbought": [60, 65, 70]},
                      _spec(), top=1)
    assert report["combinations_tested"] == 6


def test_optimize_rejects_an_empty_grid():
    with pytest.raises(strategies.StrategyError):
        optimize("rsi", {}, _spec())


def test_optimize_rejects_parameters_the_strategy_does_not_have():
    with pytest.raises(strategies.StrategyError):
        optimize("rsi", {"not_a_param": [1, 2]}, _spec())
