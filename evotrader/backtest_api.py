"""A backtesting API over evotrader's engine, shaped for callers and caches.

The engine in :mod:`evotrader.runner` is the honest part: decisions on a bar's
close, fills at the *next* open, commission and slippage on both sides, real
portfolio accounting with position and exposure limits.  This module wraps it
so a caller can ask for a backtest by strategy name and get a compact answer,
without re-downloading or re-deriving anything it already has.

Two costs dominate, and both are cached:

* **Loading and aligning bars** — seconds, and network-bound.  Handled by
  :mod:`evotrader.data`'s on-disk CSV cache.
* **Computing the feature matrix** — tens of milliseconds per symbol, and
  repeated for every backtest over the same window.  Handled here by
  :func:`load_dataset`, which memoises the whole ``(universe, features,
  benchmark)`` triple.

With both warm, a backtest is ~0.2s of pure CPU, so comparing thirty
strategies or sweeping a parameter grid is seconds rather than minutes.

Two kinds of validation are offered, and they answer different questions:

* :func:`walk_forward` runs one *fixed* strategy across anchored folds.  No
  parameter is chosen from the data, so this measures **consistency across
  regimes**, not overfitting.
* :func:`optimize` picks parameters on a training window and reports the
  winners on a window it never saw.  Because the selection happens on the
  data, this is where overfitting is actually measurable — and usually
  visible.
"""
from __future__ import annotations

import itertools
import math
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from . import strategies
from .data import DataError, Universe, bars_per_year, load_universe
from .features import FeatureSet, build_features
from .fitness import FitnessConfig, Metrics, compute_metrics, fitness_score
from .genome import EntryRule, ExitRule, Genome, GenomeError, RiskParams, compile_genome
from .runner import buy_and_hold, run_backtest

#: How many prepared datasets to keep in memory.  Each is roughly
#: ``symbols × bars × features × 8`` bytes — a few MB for a typical window.
MAX_CACHED_DATASETS = 6


@dataclass(frozen=True)
class DataSpec:
    """Identifies a window of market data; hashable so it can key the cache."""

    symbols: Tuple[str, ...]
    start: str
    end: str
    interval: str = "1d"
    offline: bool = False

    @staticmethod
    def of(symbols: Sequence[str], start: str, end: str, *,
           interval: str = "1d", offline: bool = False) -> "DataSpec":
        cleaned = tuple(sorted({s.strip().upper() for s in symbols if s.strip()}))
        if not cleaned:
            raise DataError("no symbols given")
        return DataSpec(cleaned, start, end, interval, offline)


@dataclass(frozen=True)
class Costs:
    """Trading frictions and starting capital."""

    starting_cash: float = 100_000.0
    commission_bps: float = 1.0
    slippage_bps: float = 5.0


@dataclass
class Dataset:
    """Bars, features and the buy-and-hold benchmark for one window."""

    spec: DataSpec
    universe: Universe
    features: FeatureSet
    benchmark: List[float]
    periods_per_year: float

    @property
    def bars(self) -> int:
        return len(self.features.dates)

    @property
    def dates(self) -> Tuple[str, str]:
        return self.universe.date_range()


_CACHE: "OrderedDict[DataSpec, Dataset]" = OrderedDict()


def _prepare(universe: Universe, spec: DataSpec) -> Dataset:
    periods = bars_per_year(spec.interval)
    features = build_features(universe, periods)
    benchmark = buy_and_hold(universe, features)
    return Dataset(spec, universe, features, benchmark, periods)


def load_dataset(spec: DataSpec, *, refresh: bool = False,
                 min_bars: int = 250) -> Dataset:
    """Load, align and prepare a window, memoised by spec."""
    if not refresh and spec in _CACHE:
        _CACHE.move_to_end(spec)
        return _CACHE[spec]
    universe = load_universe(list(spec.symbols), spec.start, spec.end,
                             offline=spec.offline, refresh=refresh,
                             min_bars=min_bars, interval=spec.interval)
    dataset = _prepare(universe, spec)
    _CACHE[spec] = dataset
    _CACHE.move_to_end(spec)
    while len(_CACHE) > MAX_CACHED_DATASETS:
        _CACHE.popitem(last=False)
    return dataset


def clear_cache() -> None:
    _CACHE.clear()


def cache_info() -> Dict[str, Any]:
    return {"entries": len(_CACHE), "limit": MAX_CACHED_DATASETS,
            "windows": [{"symbols": list(s.symbols), "start": s.start,
                         "end": s.end, "interval": s.interval,
                         "bars": d.bars} for s, d in _CACHE.items()]}


# ─── Building genomes from a request ──────────────────────────────────────────

def make_genome(strategy: Optional[str] = None, *,
                params: Optional[Mapping[str, Any]] = None,
                entries: Optional[Sequence[Any]] = None,
                exits: Optional[Sequence[str]] = None,
                risk: Optional[Mapping[str, Any]] = None,
                name: str = "custom") -> Genome:
    """Resolve a request into a genome: a library strategy or explicit rules.

    ``entries`` accepts either bare rule strings or ``{"when": ..., "weight":
    ...}`` mappings, so a caller can size positions without learning the
    genome schema.
    """
    if strategy:
        return strategies.build(strategy, params, risk)
    if not entries:
        raise strategies.StrategyError(
            "give either a strategy name or at least one entry rule")
    entry_rules: List[EntryRule] = []
    for item in entries:
        if isinstance(item, Mapping):
            entry_rules.append(EntryRule(str(item["when"]),
                                         float(item.get("weight", 0.25)),
                                         str(item.get("note", ""))))
        else:
            entry_rules.append(EntryRule(str(item), 0.25))
    genome = Genome(
        name=name,
        thesis="caller-supplied rules",
        entry_rules=entry_rules,
        exit_rules=[ExitRule(str(rule)) for rule in (exits or [])],
        risk=RiskParams.from_dict(dict(risk or {})),
        origin="custom",
    )
    compile_genome(genome)
    return genome


# ─── Running ──────────────────────────────────────────────────────────────────

def _metrics_for(genome: Genome, dataset: Dataset, costs: Costs):
    compiled = compile_genome(genome)
    result = run_backtest(compiled, dataset.universe, dataset.features,
                          starting_cash=costs.starting_cash,
                          commission_bps=costs.commission_bps,
                          slippage_bps=costs.slippage_bps)
    metrics = compute_metrics(result.journal.equity, result.journal.trades,
                              benchmark=dataset.benchmark,
                              turnover=result.turnover,
                              exposure=result.exposure,
                              bars_per_year=dataset.periods_per_year)
    return result, metrics


def _round(value: Any, places: int = 4) -> Any:
    if isinstance(value, float):
        return round(value, places) if math.isfinite(value) else None
    return value


def run(genome: Genome, dataset: Dataset, costs: Costs = Costs(), *,
        include_trades: bool = False, include_equity: bool = False,
        max_trades: int = 50) -> Dict[str, Any]:
    """Backtest one genome and shape the outcome for a caller."""
    try:
        result, metrics = _metrics_for(genome, dataset, costs)
    except (GenomeError, ValueError) as exc:
        return {"strategy": genome.name, "error": str(exc)}

    start, end = dataset.dates
    out: Dict[str, Any] = {
        "strategy": genome.name,
        "symbols": list(dataset.spec.symbols),
        "interval": dataset.spec.interval,
        "period": {"start": start, "end": end, "bars": dataset.bars,
                   "years": _round(metrics.years, 2)},
        "metrics": {k: _round(v) for k, v in metrics.to_dict().items()},
        "fitness": _round(fitness_score(metrics)),
        "final_equity": _round(result.final_equity, 2),
        "costs_paid": _round(result.total_costs, 2),
    }
    if include_trades:
        trades = result.journal.trades
        out["trade_count"] = len(trades)
        out["trades"] = [_trade_row(t) for t in trades[:max_trades]]
        if len(trades) > max_trades:
            out["trades_truncated"] = len(trades) - max_trades
    if include_equity:
        out["equity"] = [_round(v, 2) for v in result.journal.equity]
        out["equity_dates"] = list(result.journal.equity_dates)
    return out


def _trade_row(trade: Any) -> Dict[str, Any]:
    """One trade as plain data, tolerating journal schema differences."""
    if isinstance(trade, Mapping):
        source: Mapping[str, Any] = trade
    elif hasattr(trade, "to_dict"):
        source = trade.to_dict()
    else:
        source = {k: v for k, v in vars(trade).items() if not k.startswith("_")}
    return {k: _round(v) for k, v in source.items()}


# ─── Comparing many ───────────────────────────────────────────────────────────

_WORKER_DATASET: Optional[Dataset] = None
_WORKER_COSTS: Costs = Costs()


def _init_worker(dataset: Dataset, costs: Costs) -> None:  # pragma: no cover
    global _WORKER_DATASET, _WORKER_COSTS
    _WORKER_DATASET, _WORKER_COSTS = dataset, costs


def _run_in_worker(payload: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
    assert _WORKER_DATASET is not None
    return run(Genome.from_dict(payload), _WORKER_DATASET, _WORKER_COSTS)


def run_many(genomes: Sequence[Genome], dataset: Dataset, costs: Costs = Costs(),
             *, workers: int = 1) -> List[Dict[str, Any]]:
    """Backtest several genomes, in parallel when it is worth the setup cost."""
    if workers > 1 and len(genomes) > 4:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker,
                                 initargs=(dataset, costs)) as pool:
            return list(pool.map(_run_in_worker, [g.to_dict() for g in genomes],
                                 chunksize=4))
    return [run(g, dataset, costs) for g in genomes]


def _sort_key(row: Mapping[str, Any], rank_by: str) -> float:
    if "error" in row:
        return float("-inf")
    if rank_by == "fitness":
        return float(row.get("fitness") or float("-inf"))
    value = (row.get("metrics") or {}).get(rank_by)
    return float(value) if isinstance(value, (int, float)) else float("-inf")


def compare(genomes: Sequence[Genome], dataset: Dataset, costs: Costs = Costs(),
            *, rank_by: str = "fitness", workers: int = 1) -> List[Dict[str, Any]]:
    """Backtest several genomes and rank them.

    ``fitness`` is evotrader's composite: Sharpe plus excess return over
    buy-and-hold, charged for drawdown, turnover and trade counts too small to
    mean anything.  Ranking on raw return instead just surfaces whichever
    strategy took the most risk in this particular window.
    """
    rows = run_many(genomes, dataset, costs, workers=workers)
    rows.sort(key=lambda r: _sort_key(r, rank_by), reverse=True)
    return rows


# ─── Validation ───────────────────────────────────────────────────────────────

def slice_dataset(dataset: Dataset, lo: int, hi: int) -> Optional[Dataset]:
    """A window of a prepared dataset, reusing its features.

    The features are causal, so slicing leaks nothing forward while leaving
    the indicators warm — a 60-bar validation fold keeps all 60 bars instead
    of losing them to a fresh 200-bar warmup.  Returns None when the window
    is too short to trade.
    """
    lo, hi = max(0, lo), min(hi, dataset.bars)
    if hi - lo < 30:
        return None
    features = dataset.features.index_slice(lo, hi)
    universe = dataset.universe.slice(lo, hi)
    if hi - lo - features.warmup < 20:
        return None
    benchmark = buy_and_hold(universe, features)
    return Dataset(dataset.spec, universe, features, benchmark,
                   dataset.periods_per_year)


def fold_indices(bars: int, folds: int = 3, test_frac: float = 0.25
                 ) -> List[Tuple[str, int, int, int, int]]:
    """Anchored walk-forward folds as ``(name, train_lo, train_hi, test_lo, test_hi)``.

    Anchored means every fold trains on all history before its test window,
    so no fold ever sees its own future.
    """
    if bars < 200 or folds < 1:
        cut = max(1, int(bars * (1 - test_frac)))
        return [("full", 0, cut, cut, bars)]
    test_len = max(30, int(bars * test_frac / folds))
    out: List[Tuple[str, int, int, int, int]] = []
    for k in range(folds):
        test_end = bars - (folds - 1 - k) * test_len
        test_start = test_end - test_len
        if test_start < 100:
            continue
        out.append((f"fold{k + 1}", 0, test_start, test_start, test_end))
    if out:
        return out
    cut = max(1, int(bars * 0.75))
    return [("full", 0, cut, cut, bars)]


def walk_forward(genome: Genome, spec: DataSpec, costs: Costs = Costs(), *,
                 folds: int = 3, test_frac: float = 0.25,
                 refresh: bool = False) -> Dict[str, Any]:
    """Run one fixed strategy across anchored folds.

    Nothing is fitted here, so a gap between in-sample and out-of-sample folds
    measures **regime dependence**, not overfitting: the same rules simply
    worked in one period and not another.  Use :func:`optimize` when you want
    to know whether a *choice* was overfitted.
    """
    dataset = load_dataset(spec, refresh=refresh)
    rows: List[Dict[str, Any]] = []
    for name, tr_lo, tr_hi, te_lo, te_hi in fold_indices(dataset.bars, folds, test_frac):
        train = slice_dataset(dataset, tr_lo, tr_hi)
        test = slice_dataset(dataset, te_lo, te_hi)
        if train is None or test is None:
            rows.append({"fold": name, "skipped": "window too short to trade"})
            continue
        rows.append({
            "fold": name,
            "train": _fold_summary(run(genome, train, costs)),
            "test": _fold_summary(run(genome, test, costs)),
        })

    scored = [r for r in rows if "test" in r and r["test"].get("trades")]
    consistency = _consistency(scored)
    return {
        "strategy": genome.name,
        "symbols": list(spec.symbols),
        "interval": spec.interval,
        "folds": rows,
        "evaluated_folds": len(scored),
        "consistency": consistency,
        "note": ("Fixed parameters, so this measures consistency across regimes, "
                 "not overfitting. Use optimize() to measure selection bias."),
    }


def _fold_summary(row: Mapping[str, Any]) -> Dict[str, Any]:
    if "error" in row:
        return {"error": row["error"]}
    m = row.get("metrics") or {}
    return {
        "period": row.get("period", {}),
        "total_return": m.get("total_return"),
        "benchmark_return": m.get("benchmark_return"),
        "excess_return": m.get("excess_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "trades": m.get("trades"),
        "win_rate": m.get("win_rate"),
        "fitness": row.get("fitness"),
    }


def _consistency(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """How alike the out-of-sample folds were, and whether any of them worked."""
    if not rows:
        return {"verdict": "no fold produced trades", "positive_folds": 0}
    tests = [r["test"] for r in rows]
    returns = [t.get("total_return") or 0.0 for t in tests]
    excess = [t.get("excess_return") or 0.0 for t in tests]
    positive = sum(1 for r in returns if r > 0)
    beat_bh = sum(1 for e in excess if e > 0)
    mean = sum(returns) / len(returns)
    spread = max(returns) - min(returns)
    if beat_bh == len(returns):
        verdict = "beat buy-and-hold in every fold"
    elif beat_bh == 0:
        verdict = "never beat buy-and-hold"
    else:
        verdict = f"beat buy-and-hold in {beat_bh} of {len(returns)} folds"
    return {
        "verdict": verdict,
        "folds_tested": len(returns),
        "positive_folds": positive,
        "folds_beating_benchmark": beat_bh,
        "mean_test_return": _round(mean),
        "return_spread": _round(spread),
    }


def optimize(strategy: str, grid: Mapping[str, Sequence[Any]], spec: DataSpec,
             costs: Costs = Costs(), *, test_frac: float = 0.25,
             rank_by: str = "fitness", top: int = 5, workers: int = 1,
             refresh: bool = False) -> Dict[str, Any]:
    """Grid-search a strategy on a training window, then score the winners
    on a window the search never saw.

    This is the honest form of a parameter sweep.  The best in-sample
    combination is almost always better in-sample than it will ever be again;
    the held-out column is what says by how much, and ``degradation``
    summarises it.
    """
    if not grid:
        raise strategies.StrategyError("optimize needs at least one parameter to vary")
    keys = list(grid)
    combos = [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]
    if not combos:
        raise strategies.StrategyError("the parameter grid is empty")

    full = load_dataset(spec, refresh=refresh)
    cut = max(1, int(full.bars * (1 - test_frac)))
    train = slice_dataset(full, 0, cut)
    test = slice_dataset(full, cut, full.bars)
    if train is None:
        raise DataError("training window is too short to produce signals")

    genomes = [strategies.build(strategy, combo) for combo in combos]
    in_sample = run_many(genomes, train, costs, workers=workers)
    ranked = sorted(zip(combos, in_sample),
                    key=lambda pair: _sort_key(pair[1], rank_by), reverse=True)

    results: List[Dict[str, Any]] = []
    for combo, train_row in ranked[:max(1, top)]:
        entry: Dict[str, Any] = {"params": combo, "train": _fold_summary(train_row)}
        if test is not None:
            entry["test"] = _fold_summary(run(strategies.build(strategy, combo),
                                              test, costs))
        results.append(entry)

    return {
        "strategy": strategy,
        "symbols": list(spec.symbols),
        "interval": spec.interval,
        "combinations_tested": len(combos),
        "train_window": train.dates,
        "test_window": test.dates if test is not None else None,
        "results": results,
        "degradation": _degradation(results),
        "note": ("Parameters were chosen on the training window only. The test "
                 "column is the same parameters on unseen bars — the gap "
                 "between them is the cost of the search."),
    }


def _degradation(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Quantify how much the best in-sample choice gave back out of sample."""
    if not results or "test" not in results[0]:
        return {"verdict": "no held-out window was available"}
    best = results[0]
    train_return = best["train"].get("total_return") or 0.0
    test_return = best["test"].get("total_return") or 0.0
    kept = (test_return / train_return) if train_return > 0 else None
    if train_return <= 0:
        verdict = "the best in-sample parameters did not make money even in sample"
    elif test_return <= 0:
        verdict = "the best in-sample parameters lost money out of sample — overfitted"
    elif kept is not None and kept >= 0.6:
        verdict = "held up out of sample"
    else:
        verdict = "degraded out of sample — treat the in-sample number as fiction"
    return {
        "best_train_return": _round(train_return),
        "best_test_return": _round(test_return),
        "return_retained": _round(kept) if kept is not None else None,
        "verdict": verdict,
    }
