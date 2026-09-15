"""MCP server for backtesting and symbol selection.

Two halves, sharing one process and one set of caches:

* **Backtesting** over evotrader's engine — decisions on a bar's close, fills
  at the *next* open, commission and slippage on both sides, real portfolio
  accounting with position and exposure limits, and buy-and-hold as the
  benchmark in every result.  Strategies are named from a library or written
  as rules in evotrader's sandboxed expression language.
* **Screening** over TradingView's public scanner, for choosing which symbols
  to test on in the first place.

The scanner reports current values only and cannot feed a backtest; bars come
from the data layer.  A universe screened today and tested on an earlier
window is selection on the outcome, so screen results carry an explicit bias
note rather than leaving a caller to rediscover it.

Run it with ``python -m evotrader.mcp_server`` (stdio transport).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Mapping, Optional, Sequence

from mcp.server.mcpserver import MCPServer

from . import strategies
from .backtest_api import (Costs, DataSpec, cache_info, clear_cache, compare,
                           load_dataset, make_genome, optimize, run, walk_forward)
from .data import DataError, INTERVALS
from .features import FEATURE_DOCS, MARKET_FEATURES, PORTFOLIO_FEATURES
from .dsl import FUNCTIONS, DslError
from .genome import GenomeError
from .screener import (COLUMNS, MARKETS, OPERATIONS, PRESETS, Filter, Screen,
                       ScreenerError, preset, quote_screen, run_screen,
                       yahoo_symbols)

mcp = MCPServer(
    name="evotrader",
    instructions=(
        "Backtesting with realistic fills (decide on close, fill at next open), "
        "commission and slippage, portfolio limits, and buy-and-hold as the "
        "benchmark in every result. Strategies come from a named library or "
        "from rules written in the expression language that list_features "
        "describes. TradingView screening is included for choosing a symbol "
        "universe, but returns current values only and never history."),
    version="0.2.0",
)


def _spec(symbols: Sequence[str], start: str, end: str, interval: str,
          offline: bool) -> DataSpec:
    return DataSpec.of(symbols, start, end, interval=interval, offline=offline)


def _costs(starting_cash: float, commission_bps: float,
           slippage_bps: float) -> Costs:
    return Costs(starting_cash=starting_cash, commission_bps=commission_bps,
                 slippage_bps=slippage_bps)


def _failure(exc: Exception) -> Dict[str, Any]:
    """Turn an expected failure into a result a caller can act on."""
    return {"error": f"{type(exc).__name__}: {exc}"}


_EXPECTED = (DataError, GenomeError, DslError, ScreenerError,
             strategies.StrategyError, ValueError, KeyError)


def _build(preset_name: Optional[str], filters: Optional[Sequence[str]],
           market: str, sort_by: Optional[str], limit: Optional[int],
           name: str) -> Screen:
    screen = preset(preset_name) if preset_name else Screen(name=name, market=market)
    if filters:
        screen = replace(screen,
                         filters=list(screen.filters) + [Filter.parse(f) for f in filters])
    if sort_by:
        screen = replace(screen, sort_by=sort_by)
    if limit:
        screen = replace(screen, limit=limit)
    return screen


def _result(snapshot, backtest_start: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "screen": snapshot.screen,
        "market": snapshot.market,
        "captured_at": snapshot.captured_at,
        "total_matches": snapshot.total_matches,
        "returned": len(snapshot.rows),
        "symbols": yahoo_symbols(snapshot),
        "rows": snapshot.rows,
    }
    warning = (snapshot.lookahead_warning(backtest_start) if backtest_start
               else None)
    if warning:
        out["bias_warning"] = warning
    return out


# ─── Backtesting ──────────────────────────────────────────────────────────────

@mcp.tool(title="Backtest a strategy")
def backtest(
    symbols: List[str],
    strategy: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    entry_rules: Optional[List[str]] = None,
    exit_rules: Optional[List[str]] = None,
    risk: Optional[Dict[str, Any]] = None,
    start: str = "2015-01-01",
    end: str = "2030-01-01",
    interval: str = "1d",
    starting_cash: float = 100_000.0,
    commission_bps: float = 1.0,
    slippage_bps: float = 5.0,
    include_trades: bool = False,
    offline: bool = False,
) -> Dict[str, Any]:
    """Backtest one strategy over a symbol universe.

    Decisions are made on a bar's close and filled at the NEXT bar's open,
    with commission and slippage charged both ways, so the result does not
    assume a fill nobody could have got. Buy-and-hold over the same window is
    reported alongside as ``benchmark_return`` — a strategy that merely rode
    the market up is not a discovery.

    Give either ``strategy`` (a name from list_strategies) or ``entry_rules``
    and ``exit_rules`` written in the language list_features describes.

    Args:
        symbols: Tickers to trade, e.g. ["SPY", "QQQ", "IWM"].
        strategy: Name from the library; ``params`` tunes its thresholds.
        params: Parameter overrides for the named strategy.
        entry_rules: Buy conditions, e.g. ["rsi14 < 30 and close > sma200"].
        exit_rules: Sell conditions, e.g. ["rsi14 > 60", "bars_held > 30"].
        risk: Limits — max_position_pct, max_positions, stop_loss_pct,
            trailing_stop_pct, max_hold_bars, cooldown_bars.
        start: First date, YYYY-MM-DD.
        end: Last date, YYYY-MM-DD.
        interval: Bar size — 1d, 1h, 30m, 15m or 5m. Intraday history is
            capped (730 days hourly, 60 days finer).
        starting_cash: Starting capital.
        commission_bps: Commission per side in basis points.
        slippage_bps: Slippage per side in basis points.
        include_trades: Return the individual trades as well as the metrics.
        offline: Use deterministic synthetic prices instead of real data.
    """
    try:
        genome = make_genome(strategy, params=params, entries=entry_rules,
                             exits=exit_rules, risk=risk)
        dataset = load_dataset(_spec(symbols, start, end, interval, offline))
        return run(genome, dataset, _costs(starting_cash, commission_bps, slippage_bps),
                   include_trades=include_trades)
    except _EXPECTED as exc:
        return _failure(exc)


@mcp.tool(title="Compare strategies")
def compare_strategies(
    symbols: List[str],
    names: Optional[List[str]] = None,
    family: Optional[str] = None,
    start: str = "2015-01-01",
    end: str = "2030-01-01",
    interval: str = "1d",
    rank_by: str = "fitness",
    starting_cash: float = 100_000.0,
    commission_bps: float = 1.0,
    slippage_bps: float = 5.0,
    workers: int = 4,
    limit: int = 15,
    offline: bool = False,
) -> Dict[str, Any]:
    """Backtest many strategies over one universe and rank them.

    Default ranking is evotrader's composite fitness: Sharpe plus excess
    return over buy-and-hold, charged for drawdown, turnover and trade counts
    too small to mean anything. Ranking by ``total_return`` instead mostly
    surfaces whichever strategy took the most risk in this particular window.

    Args:
        symbols: Tickers to trade.
        names: Strategies to compare; defaults to the whole library except
            the fixed archetypes.
        family: Restrict to one family — mean-reversion, trend, breakout,
            regime or archetype.
        rank_by: "fitness", or any metric name such as "sharpe".
        limit: How many ranked rows to return.
    """
    try:
        chosen = list(names) if names else strategies.names(family)
        if not names and not family:
            chosen = [n for n in chosen if not n.startswith("archetype:")]
        if not chosen:
            return {"error": "no strategies matched"}
        genomes = [strategies.build(n) for n in chosen]
        dataset = load_dataset(_spec(symbols, start, end, interval, offline))
        rows = compare(genomes, dataset, _costs(starting_cash, commission_bps,
                                                slippage_bps),
                       rank_by=rank_by, workers=workers)
        start_date, end_date = dataset.dates
        return {
            "symbols": list(dataset.spec.symbols),
            "interval": interval,
            "period": {"start": start_date, "end": end_date, "bars": dataset.bars},
            "ranked_by": rank_by,
            "tested": len(rows),
            "benchmark_return": (rows[0].get("metrics") or {}).get("benchmark_return")
                                if rows else None,
            "results": [_leaderboard_row(r) for r in rows[:max(1, limit)]],
        }
    except _EXPECTED as exc:
        return _failure(exc)


def _leaderboard_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """One compact ranking row — the full metric block is rarely worth it."""
    if "error" in row:
        return {"strategy": row.get("strategy"), "error": row["error"]}
    m = row.get("metrics") or {}
    return {
        "strategy": row.get("strategy"),
        "fitness": row.get("fitness"),
        "total_return": m.get("total_return"),
        "excess_return": m.get("excess_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "trades": m.get("trades"),
        "win_rate": m.get("win_rate"),
        "turnover": m.get("turnover"),
    }


@mcp.tool(title="Walk-forward validation")
def walk_forward_test(
    symbols: List[str],
    strategy: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    entry_rules: Optional[List[str]] = None,
    exit_rules: Optional[List[str]] = None,
    risk: Optional[Dict[str, Any]] = None,
    start: str = "2010-01-01",
    end: str = "2030-01-01",
    interval: str = "1d",
    folds: int = 3,
    test_frac: float = 0.25,
    starting_cash: float = 100_000.0,
    commission_bps: float = 1.0,
    slippage_bps: float = 5.0,
    offline: bool = False,
) -> Dict[str, Any]:
    """Run one fixed strategy across anchored folds to see if it travels.

    Each fold trains on all history before its test window, so no fold sees
    its own future. Because nothing is fitted here, a gap between in-sample
    and out-of-sample folds measures REGIME DEPENDENCE, not overfitting — the
    same rules simply worked in one period and not another. Use ``optimize``
    when you want to measure the cost of a parameter search.
    """
    try:
        genome = make_genome(strategy, params=params, entries=entry_rules,
                             exits=exit_rules, risk=risk)
        return walk_forward(genome, _spec(symbols, start, end, interval, offline),
                            _costs(starting_cash, commission_bps, slippage_bps),
                            folds=folds, test_frac=test_frac)
    except _EXPECTED as exc:
        return _failure(exc)


@mcp.tool(title="Optimize parameters")
def optimize_strategy(
    symbols: List[str],
    strategy: str,
    grid: Dict[str, List[Any]],
    start: str = "2010-01-01",
    end: str = "2030-01-01",
    interval: str = "1d",
    test_frac: float = 0.25,
    rank_by: str = "fitness",
    top: int = 5,
    starting_cash: float = 100_000.0,
    commission_bps: float = 1.0,
    slippage_bps: float = 5.0,
    workers: int = 4,
    offline: bool = False,
) -> Dict[str, Any]:
    """Grid-search a strategy on a training window, then score the winners on
    bars the search never saw.

    This is where overfitting is actually measurable. The best in-sample
    combination is almost always better in-sample than it will ever be again;
    the ``test`` column says by how much, and ``degradation`` summarises it.
    A result that looks superb in training and ordinary out of sample is the
    normal outcome, not a bug.

    Args:
        grid: Parameter values to try, e.g. {"oversold": [25, 30, 35]}.
            Use describe_strategy to see what a strategy takes.
        test_frac: Share of the window held back from the search.
        top: How many of the best in-sample combinations to report.
    """
    try:
        return optimize(strategy, grid, _spec(symbols, start, end, interval, offline),
                        _costs(starting_cash, commission_bps, slippage_bps),
                        test_frac=test_frac, rank_by=rank_by, top=top,
                        workers=workers)
    except _EXPECTED as exc:
        return _failure(exc)


@mcp.tool(title="List strategies")
def list_strategies(family: Optional[str] = None) -> Dict[str, Any]:
    """Named strategies available to backtest, grouped by family."""
    chosen = strategies.names(family)
    return {
        "families": strategies.families(),
        "count": len(chosen),
        "strategies": [{"name": n,
                        "family": strategies.SPECS[n].family,
                        "thesis": strategies.SPECS[n].thesis,
                        "params": dict(strategies.SPECS[n].params)}
                       for n in chosen],
    }


@mcp.tool(title="Describe a strategy")
def describe_strategy(name: str) -> Dict[str, Any]:
    """The rules, parameters and risk limits behind one named strategy."""
    try:
        return strategies.describe(name)
    except strategies.StrategyError as exc:
        return _failure(exc)


@mcp.tool(title="List rule features")
def list_features() -> Dict[str, Any]:
    """The vocabulary entry and exit rules may use.

    Rules are boolean expressions over these names, with the usual
    comparisons, ``and``/``or``/``not``, arithmetic, and the listed functions.
    There is no eval anywhere — a rule cannot reach outside this set.
    """
    return {
        "market_features": {n: FEATURE_DOCS.get(n, "") for n in MARKET_FEATURES},
        "portfolio_features": {n: FEATURE_DOCS.get(n, "") for n in PORTFOLIO_FEATURES},
        "functions": sorted(FUNCTIONS),
        "intervals": list(INTERVALS),
        "examples": [
            "rsi14 < 30 and close > sma200",
            "cross_above(macd, macd_signal) and volume_ratio > 1.5",
            "close > ema26 + 2 * atr14",
            "position_return > 0.18 or bars_held > 40",
        ],
    }


@mcp.tool(title="Validate rules")
def validate_strategy(
    entry_rules: Optional[List[str]] = None,
    exit_rules: Optional[List[str]] = None,
    strategy: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    risk: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check that rules parse and reference only real features, without
    loading any data. Cheaper than discovering a typo mid-backtest."""
    try:
        genome = make_genome(strategy, params=params, entries=entry_rules,
                             exits=exit_rules, risk=risk)
    except _EXPECTED as exc:
        return {"valid": False, **_failure(exc)}
    return {
        "valid": True,
        "name": genome.name,
        "entry_rules": [r.when for r in genome.entry_rules],
        "exit_rules": [r.when for r in genome.exit_rules],
        "risk": genome.risk.to_dict(),
    }


@mcp.tool(title="Data cache status")
def data_cache(clear: bool = False) -> Dict[str, Any]:
    """Which prepared windows are held in memory; optionally drop them."""
    if clear:
        clear_cache()
        return {"cleared": True, **cache_info()}
    return cache_info()


# ─── Screening ────────────────────────────────────────────────────────────────

@mcp.tool(title="List screen presets")
def list_presets() -> Dict[str, Any]:
    """Named screens available as a starting point, with their filters."""
    return {
        name: {
            "market": screen.market,
            "sorted_by": screen.sort_by,
            "limit": screen.limit,
            "filters": [f"{f.column} {f.operation} {f.value}" for f in screen.filters],
        }
        for name, screen in PRESETS.items()
    }


@mcp.tool(title="List screener columns")
def list_columns() -> Dict[str, Any]:
    """The column aliases, filter operations and markets a screen can use.

    Unlisted TradingView column names are passed through unchanged, so this is
    a convenience vocabulary rather than the full set.
    """
    return {"columns": COLUMNS, "operations": list(OPERATIONS),
            "markets": list(MARKETS)}


@mcp.tool(title="Screen for symbols")
def screen_symbols(
    preset_name: Optional[str] = None,
    filters: Optional[List[str]] = None,
    market: str = "america",
    sort_by: Optional[str] = None,
    limit: int = 25,
    backtest_start: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Find symbols matching a screen, for use as an evolution universe.

    Args:
        preset_name: A named screen from ``list_presets`` to start from.
        filters: Predicates like ``"mcap > 10e9"`` or ``"rsi < 35"``, added to
            the preset's own. Columns come from ``list_columns``.
        market: Which market to scan (default ``america``).
        sort_by: Column to rank by; defaults to the preset's.
        limit: How many symbols to return.
        backtest_start: If given, the intended backtest start date — the
            result gains a bias warning when the screen post-dates it.
        refresh: Bypass the 15-minute cache.
    """
    try:
        screen = _build(preset_name, filters, market, sort_by, limit, "custom")
        return _result(run_screen(screen, refresh=refresh), backtest_start)
    except ScreenerError as exc:
        return {"error": str(exc)}


@mcp.tool(title="Quote symbols")
def quote(symbols: List[str], market: str = "america") -> Dict[str, Any]:
    """Current price, change and indicator values for specific tickers.

    Symbols absent from the chosen market come back under ``missing`` rather
    than being dropped — usually a wrong ``market`` (crypto lives under
    ``crypto``, named by base currency: ``BTC``, not ``BTC-USD``).
    """
    try:
        requested = [s.strip().upper() for s in symbols if s.strip()]
        snapshot = run_screen(quote_screen(requested, market=market))
        result = _result(snapshot)
        key = "base" if market == "crypto" else "name"
        found = {str(r.get(key) or r.get("symbol", "")).upper()
                 for r in snapshot.rows}
        wanted = ([t[:-4] if t.endswith("-USD") else t for t in requested]
                  if market == "crypto" else requested)
        missing = [s for s, w in zip(requested, wanted) if w not in found]
        if missing:
            result["missing"] = missing
        return result
    except ScreenerError as exc:
        return {"error": str(exc)}


@mcp.tool(title="Save a universe snapshot")
def save_universe(
    name: str,
    preset_name: Optional[str] = None,
    filters: Optional[List[str]] = None,
    market: str = "america",
    sort_by: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Run a screen and write a dated snapshot to disk.

    Snapshots accumulate into a point-in-time record of what matched when,
    which is the only honest way to build a universe history from an endpoint
    that reports the present.
    """
    try:
        screen = _build(preset_name, filters, market, sort_by, limit, name)
        snapshot = run_screen(replace(screen, name=name))
        path = snapshot.save()
        return {"saved": path, **_result(snapshot)}
    except ScreenerError as exc:
        return {"error": str(exc)}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
