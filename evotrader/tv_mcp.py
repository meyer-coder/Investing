"""MCP server: backtesting strategies on TradingView data.

TradingView is where the chart is; this is where the test runs.  Bars come from
TradingView's own feed (:mod:`evotrader.tvdata`), the simulation is this
package's engine — decisions on a bar's close, fills at the **next** bar's
open, commission and slippage charged both ways — and the report comes back in
the shape a Strategy Tester report has: net profit against buy-and-hold, max
drawdown, profit factor, Sharpe, the trade list.

    evotrader tv-mcp                      # stdio, for Claude Code

Strategies are written in this package's rule language, not Pine::

    entry_rules: [{"when": "rsi14 < 30 and close > sma200", "weight": 0.25}]
    exit_rules:  [{"when": "rsi14 > 60"}, {"when": "position_return < -0.08"}]

`strategy_language` returns the whole vocabulary.  Rules are parsed, never
evaluated as code, so a malformed rule is a clear error rather than a surprise.

Three things this server will keep saying, because they are what separate a
backtest from a result: a window you chose after seeing the chart is in-sample,
`walk_forward` is the cheapest honest check available here, and fills assume
you could transact at the next open at the modelled slippage.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import data as marketdata
from . import tvcache
from . import tvdata
from .config import EvolutionConfig
from .data import Universe, walk_forward_splits
from .features import FeatureSet, build_features
from .fitness import FitnessConfig, Metrics, compute_metrics, fitness_score
from .genome import Genome, GenomeError, compile_genome
from .mcp_rpc import (MCPServer, Registry, ToolError, ToolResult, choice_arg,
                      float_arg, int_arg, list_arg, required_str, serve, str_arg)
from .prompts import genome_schema_text, rule_reference
from .runner import buy_and_hold, run_backtest
from .store import Store

SERVER_NAME = "tradingview-backtest"

INSTRUCTIONS = """\
Backtests strategies on TradingView data.

`search_symbols` resolves a ticker to TradingView's exchange-qualified form
(AAPL -> NASDAQ:AAPL). `get_bars` shows what the feed returns. `backtest` runs
a strategy and reports it the way a Strategy Tester does; `compare_strategies`
runs several on identical bars; `walk_forward` re-tests on windows the strategy
was not chosen on. `strategy_language` is the rule vocabulary — read it before
writing rules.

Bars are read from the local store first (`evotrader tv-fetch` fills it). A
symbol that is not in the store yet is pulled live, which takes seconds per
symbol and can exceed a client's tool timeout — warm new symbols with
`tv-fetch` before backtesting a basket of them.

Say these plainly when reporting a result, because they are what separates a
backtest from evidence: a window picked after looking at the chart is
in-sample, the engine fills at the next bar's open with commission and
slippage charged, and a strategy that trades a handful of times has told you
almost nothing whatever its return says.
"""

_SYMBOLS_PROPERTY = {
    "type": ["array", "string"], "items": {"type": "string"},
    "description": "TradingView symbols, e.g. [\"NASDAQ:AAPL\", \"AMEX:SPY\"]",
}
_TIMEFRAME_PROPERTY = {
    "type": "string",
    "description": "1, 5, 15, 60, 240, 1D, 1W, 1M (also 1h/4h/1d aliases). Default 1D",
}
_BARS_PROPERTY = {
    "type": "integer",
    "description": "how many recent bars to test on (default 2000)",
}
_SOURCE_PROPERTY = {
    "type": "string", "enum": ["tradingview", "yahoo", "synthetic"],
    "description": "bar source. tradingview (default) matches the chart; yahoo "
                   "is daily, dividend-adjusted; synthetic is offline test data",
}
_ENTRY_PROPERTY = {
    "type": "array",
    "items": {"type": ["object", "string"]},
    "description": "entry rules: [{\"when\": \"<rule>\", \"weight\": 0.25}], "
                   "weight being the target position size as a share of equity",
}
_EXIT_PROPERTY = {
    "type": "array",
    "items": {"type": ["object", "string"]},
    "description": "exit rules: [{\"when\": \"<rule>\"}]; any match closes the position",
}
_RISK_PROPERTY = {
    "type": "object",
    "description": "max_position_pct, max_positions, max_gross_exposure, "
                   "stop_loss_pct, take_profit_pct, trailing_stop_pct, "
                   "max_hold_bars, min_hold_bars, cooldown_bars",
}

TV_TOOLS = Registry()
tool = TV_TOOLS.tool


# ------------------------------------------------------------------- the view

class Backtester:
    """Holds the bar cache, so comparing ten strategies fetches data once."""

    def __init__(self, *, source: str = "tradingview", session_token: str = "",
                 db_path: str = "", refresh: bool = True):
        self.default_source = source
        self.refresh = refresh
        self.session_token = session_token or os.environ.get("TRADINGVIEW_SESSION", "")
        self.db_path = db_path or os.environ.get("EVOTRADER_DB") or EvolutionConfig().db_path
        self._bars: Dict[Tuple[str, ...], Universe] = {}
        # Keyed by id(), so the universe is kept alive alongside its features:
        # a collected universe could otherwise have its id reused by another.
        self._features: Dict[int, Tuple[Universe, FeatureSet]] = {}
        self._store: Optional[Store] = None

    # ----------------------------------------------------------------- data
    def universe(self, symbols: Sequence[str], timeframe: str, bars: int,
                 source: str) -> Universe:
        key = (source, timeframe, str(bars)) + tuple(sorted(symbols))
        cached = self._bars.get(key)
        if cached is not None:
            return cached
        if source == "tradingview":
            universe = tvdata.load_universe(
                symbols, timeframe, bars, session_token=self.session_token,
                min_bars=min(250, max(50, bars // 4)),
                fetch=self._cached_fetch)
        else:
            if tvdata.normalise_timeframe(timeframe) != "1D":
                raise ToolError(f"the {source} source serves daily bars only; "
                                f"use timeframe 1D or source tradingview")
            plain = [s.split(":")[-1].upper() for s in symbols]
            if source == "synthetic":
                # Offline bars have their own calendar; take it whole and trim.
                start, end = "1900-01-01", "2999-12-31"
            else:
                # Calendar days for N sessions, with room for weekends and holidays.
                start = (date.today() - timedelta(days=int(bars * 1.5) + 30)).isoformat()
                end = date.today().isoformat()
            universe = marketdata.load_universe(
                plain, start, end, offline=(source == "synthetic"),
                min_bars=min(250, max(50, bars // 4)))
            if len(universe) > bars:
                universe = universe.slice(len(universe) - bars, len(universe))
        if len(universe) < 60:
            raise ToolError(f"only {len(universe)} shared bars for "
                            f"{', '.join(symbols)} — ask for more bars, or drop "
                            f"the symbol with the shortest history")
        self._bars[key] = universe
        return universe

    def _cached_fetch(self, symbol: str, timeframe: str, bars: int, **kwargs):
        """Fetch through the local store, so history outlives the feed's window."""
        return tvcache.cached_bars(symbol, timeframe, bars,
                                   refresh=self.refresh, **kwargs)

    def features(self, universe: Universe) -> FeatureSet:
        key = id(universe)
        if key not in self._features:
            self._features[key] = (universe, build_features(universe))
        return self._features[key][1]

    def store(self) -> Store:
        if self._store is None:
            if not os.path.exists(self.db_path):
                raise ToolError(f"no evotrader database at {self.db_path!r}; "
                                f"pass db=<path> or run `evotrader run` first")
            self._store = Store(self.db_path)
        return self._store

    def close(self) -> None:
        if self._store is not None:
            try:
                self._store.close()
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass
            self._store = None


# ------------------------------------------------------------------ strategy

def _strategy_from(args: Dict[str, Any], *, name_default: str = "strategy") -> Genome:
    """Turn tool arguments into a compiled-checked genome."""
    entries = args.get("entry_rules") or []
    exits = args.get("exit_rules") or []
    if isinstance(entries, str):
        entries = [entries]
    if isinstance(exits, str):
        exits = [exits]
    if not entries:
        raise ToolError("entry_rules is required: when should this strategy buy?")
    if not exits:
        raise ToolError("exit_rules is required: a strategy that never sells "
                        "is a buy-and-hold with extra steps")
    genome = Genome.from_dict({
        "name": str_arg(args, "name") or name_default,
        "thesis": str_arg(args, "thesis"),
        "entry_rules": entries,
        "exit_rules": exits,
        "risk": args.get("risk") or {},
    })
    try:
        compile_genome(genome)
    except GenomeError as exc:
        raise ToolError(f"{exc}. Call strategy_language for the vocabulary.") from exc
    return genome


def _run(view: Backtester, genome: Genome, universe: Universe, timeframe: str, *,
         starting_cash: float, commission_bps: float, slippage_bps: float,
         fitness: Optional[FitnessConfig] = None) -> Dict[str, Any]:
    """One backtest, reported the way a Strategy Tester reports one."""
    features = view.features(universe)
    compiled = compile_genome(genome)
    result = run_backtest(compiled, universe, features,
                          starting_cash=starting_cash,
                          commission_bps=commission_bps, slippage_bps=slippage_bps)
    benchmark = buy_and_hold(universe, features, starting_cash=starting_cash)
    per_year = tvdata.bars_per_year(timeframe)
    metrics = compute_metrics(result.journal.equity, result.journal.trades,
                              benchmark=benchmark, turnover=result.turnover,
                              exposure=result.exposure, bars_per_year=per_year)
    first, last = universe.date_range()
    return {
        "name": genome.name, "metrics": metrics,
        "fitness": fitness_score(metrics, fitness or FitnessConfig()),
        "journal": result.journal, "bars": len(universe),
        "start": first, "end": last, "symbols": universe.symbols,
        "timeframe": tvdata.normalise_timeframe(timeframe),
    }


def _report_lines(run: Dict[str, Any]) -> List[str]:
    m: Metrics = run["metrics"]
    excess = m.total_return - m.benchmark_return
    bh_cagr = ((1 + m.benchmark_return) ** (1 / max(m.years, 1e-9)) - 1
               if m.benchmark_return > -1 else -1.0)
    return [
        f"{run['name']} — {', '.join(run['symbols'])} · {run['timeframe']} · "
        f"{run['start']}..{run['end']} ({run['bars']} bars)",
        f"  net profit       {m.total_return * 100:+8.1f}%   "
        f"buy & hold {m.benchmark_return * 100:+7.1f}%   "
        f"excess {excess * 100:+.1f}%",
        f"  annualised       {m.cagr * 100:+8.1f}%   (bh {bh_cagr * 100:+.1f}%)",
        f"  max drawdown     {m.max_drawdown * 100:+8.1f}%   "
        f"volatility {m.volatility * 100:.1f}%",
        f"  profit factor    {_num(m.profit_factor):>8}   "
        f"sharpe {m.sharpe:.2f}   sortino {m.sortino:.2f}   calmar {m.calmar:.2f}",
        f"  trades           {m.trades:>8}   win {m.win_rate * 100:.0f}%   "
        f"avg hold {m.avg_bars_held:.0f} bars   avg trade {m.avg_trade_return * 100:+.2f}%",
        f"  exposure         {m.exposure * 100:>7.0f}%   "
        f"turnover {m.turnover:.1f}x/yr   fitness {run['fitness']:+.3f}",
    ]


def _num(value: float) -> str:
    if value is None or math.isinf(value) or math.isnan(value):
        return "inf" if value == float("inf") else "-"
    return f"{value:.2f}"


def _caveats(m: Metrics, trades_needed: int = 10) -> List[str]:
    out = []
    if m.trades < trades_needed:
        out.append(f"  only {m.trades} trades — too few to distinguish skill from luck")
    if m.exposure < 0.05 and m.trades:
        out.append("  the strategy is in the market almost never; the return is "
                   "mostly cash")
    if m.max_drawdown < -0.35:
        out.append(f"  a {abs(m.max_drawdown) * 100:.0f}% drawdown is the part of "
                   f"this result you would have had to sit through")
    if m.total_return < m.benchmark_return:
        out.append("  buy-and-hold beat it over this window")
    return out


def _common(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "starting_cash": float_arg(args, "starting_cash", 100_000.0, lo=100.0,
                                   hi=1e12),
        "commission_bps": float_arg(args, "commission_bps", 1.0, hi=500.0),
        "slippage_bps": float_arg(args, "slippage_bps", 5.0, hi=500.0),
    }


def _fmt_num(value: Any, places: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:,.{places}f}"
    return str(value)


def _symbols(args: Dict[str, Any], key: str = "symbols") -> List[str]:
    symbols = [str(s).strip().upper() for s in list_arg(args, key) if str(s).strip()]
    if not symbols:
        raise ToolError("symbols is required, e.g. [\"NASDAQ:AAPL\"]")
    if len(symbols) > 20:
        raise ToolError("at most 20 symbols per backtest")
    return symbols


def _trade_lines(run: Dict[str, Any], limit: int) -> List[str]:
    trades = run["journal"].trades[:limit] if run.get("journal") else []
    if not trades:
        return []
    return [f"\n  first {len(trades)} trades"] + [f"    {t.summary()}" for t in trades]


# --------------------------------------------------------------------- tools

@tool("search_symbols", "Search symbols",
      "Resolve a ticker or company name to the exchange-qualified symbols "
      "TradingView uses, e.g. AAPL -> NASDAQ:AAPL. Start here when unsure what "
      "to pass as a symbol.",
      {"query": {"type": "string", "description": "ticker or name, e.g. AAPL or Apple"},
       "exchange": {"type": "string", "description": "restrict to one exchange, e.g. NASDAQ"},
       "limit": {"type": "integer", "description": "rows to return (default 10)"}},
      required=["query"])
def _search_symbols(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    query = required_str(args, "query")
    limit = int_arg(args, "limit", 10, hi=50)
    try:
        matches = tvdata.search_symbols(query, exchange=str_arg(args, "exchange"),
                                        limit=limit)
    except tvdata.TradingViewError as exc:
        raise ToolError(str(exc)) from exc
    if not matches:
        return f"TradingView knows no symbol matching {query!r}", {"matches": []}
    lines = [f"{len(matches)} matches for {query!r}"]
    for m in matches:
        lines.append(f"  {m['symbol']:<24} {m['type']:<8} {m['currency']:<4} "
                     f"{m['description'][:44]}")
    return "\n".join(lines), {"matches": matches}


@tool("get_bars", "Get bars",
      "Fetch recent OHLCV for one symbol and show what the feed actually "
      "returned — range, bar count and the last few bars. Worth calling once "
      "before trusting a backtest on a symbol you have not used here.",
      {"symbol": {"type": "string", "description": "e.g. NASDAQ:AAPL"},
       "timeframe": _TIMEFRAME_PROPERTY, "bars": _BARS_PROPERTY,
       "source": _SOURCE_PROPERTY,
       "show": {"type": "integer", "description": "how many recent bars to print (default 5)"}},
      required=["symbol"])
def _get_bars(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbol = required_str(args, "symbol")
    timeframe = str_arg(args, "timeframe", "1D") or "1D"
    count = int_arg(args, "bars", 300, lo=10, hi=20_000)
    source = choice_arg(args, "source", [view.default_source] + [
        s for s in ("tradingview", "yahoo", "synthetic") if s != view.default_source])
    universe = view.universe([symbol], timeframe, count, source)
    bars = universe.bars[universe.symbols[0]]
    show = int_arg(args, "show", 5, lo=0, hi=50)
    first, last = universe.date_range()
    lines = [f"{universe.symbols[0]} · {tvdata.normalise_timeframe(timeframe)} · "
             f"{len(bars)} bars · {first}..{last} · source {source}"]
    for i in range(max(0, len(bars) - show), len(bars)):
        lines.append(f"  {bars.dates[i]}  O {bars.open[i]:>10.2f}  H {bars.high[i]:>10.2f}"
                     f"  L {bars.low[i]:>10.2f}  C {bars.close[i]:>10.2f}"
                     f"  V {bars.volume[i]:>14,.0f}")
    return "\n".join(lines), {
        "symbol": universe.symbols[0], "source": source,
        "timeframe": tvdata.normalise_timeframe(timeframe),
        "bars": len(bars), "start": first, "end": last,
        "last": [{"date": bars.dates[i], "open": float(bars.open[i]),
                  "high": float(bars.high[i]), "low": float(bars.low[i]),
                  "close": float(bars.close[i]), "volume": float(bars.volume[i])}
                 for i in range(max(0, len(bars) - show), len(bars))],
    }


@tool("backtest", "Backtest a strategy",
      "Run one strategy over TradingView bars and report it the way a Strategy "
      "Tester does: net profit against buy-and-hold, drawdown, profit factor, "
      "Sharpe, the trade list. Decisions are taken on a bar's close and filled "
      "at the next bar's open, with commission and slippage charged both ways.",
      {"symbols": _SYMBOLS_PROPERTY,
       "entry_rules": _ENTRY_PROPERTY, "exit_rules": _EXIT_PROPERTY,
       "risk": _RISK_PROPERTY,
       "name": {"type": "string", "description": "what to call this strategy"},
       "thesis": {"type": "string", "description": "the belief it trades on, for the report"},
       "timeframe": _TIMEFRAME_PROPERTY, "bars": _BARS_PROPERTY,
       "source": _SOURCE_PROPERTY,
       "starting_cash": {"type": "number", "description": "default 100000"},
       "commission_bps": {"type": "number", "description": "per side, default 1"},
       "slippage_bps": {"type": "number", "description": "per side, default 5"},
       "trades": {"type": "integer", "description": "sample trades to show (default 10)"}},
      required=["symbols", "entry_rules", "exit_rules"])
def _backtest(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbols = _symbols(args)
    timeframe = str_arg(args, "timeframe", "1D") or "1D"
    count = int_arg(args, "bars", 2000, lo=100, hi=20_000)
    source = choice_arg(args, "source", [view.default_source] + [
        s for s in ("tradingview", "yahoo", "synthetic") if s != view.default_source])
    genome = _strategy_from(args)
    universe = view.universe(symbols, timeframe, count, source)
    run = _run(view, genome, universe, timeframe, **_common(args))

    lines = _report_lines(run)
    lines += _trade_lines(run, int_arg(args, "trades", 10, lo=0, hi=100))
    caveats = _caveats(run["metrics"])
    if caveats:
        lines.append("\n  worth noting")
        lines += caveats
    lines.append("\n  this window was chosen, not drawn at random — run "
                 "`walk_forward` before treating it as evidence")
    return "\n".join(lines), {
        "name": run["name"], "symbols": run["symbols"], "source": source,
        "timeframe": run["timeframe"], "bars": run["bars"],
        "start": run["start"], "end": run["end"],
        "metrics": run["metrics"].to_dict(), "fitness": run["fitness"],
        "strategy": genome.to_dict(),
        "trades": [t.to_dict() for t in run["journal"].trades],
        "rule_hits": run["journal"].rule_hits,
        "rejected_entries": run["journal"].rejected_entries,
        "caveats": [c.strip() for c in caveats],
    }


@tool("compare_strategies", "Compare strategies",
      "Run several strategies over identical bars and rank them side by side. "
      "The bars are fetched once, so the comparison is like-for-like.",
      {"symbols": _SYMBOLS_PROPERTY,
       "strategies": {"type": "array", "items": {"type": "object"},
                      "description": "[{name, entry_rules, exit_rules, risk?}, ...], "
                                     "2 to 8 of them"},
       "timeframe": _TIMEFRAME_PROPERTY, "bars": _BARS_PROPERTY,
       "source": _SOURCE_PROPERTY,
       "starting_cash": {"type": "number"}, "commission_bps": {"type": "number"},
       "slippage_bps": {"type": "number"}},
      required=["symbols", "strategies"])
def _compare_strategies(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbols = _symbols(args)
    specs = list_arg(args, "strategies")
    if len(specs) < 2:
        raise ToolError("give at least two strategies to compare")
    if len(specs) > 8:
        raise ToolError("at most eight strategies per comparison")
    timeframe = str_arg(args, "timeframe", "1D") or "1D"
    count = int_arg(args, "bars", 2000, lo=100, hi=20_000)
    source = choice_arg(args, "source", [view.default_source] + [
        s for s in ("tradingview", "yahoo", "synthetic") if s != view.default_source])
    universe = view.universe(symbols, timeframe, count, source)
    common = _common(args)

    runs = []
    for i, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ToolError("each strategy must be an object with entry_rules "
                            "and exit_rules")
        genome = _strategy_from(spec, name_default=f"strategy {i + 1}")
        runs.append(_run(view, genome, universe, timeframe, **common))
    runs.sort(key=lambda r: r["metrics"].total_return, reverse=True)

    bh = runs[0]["metrics"].benchmark_return
    lines = [f"{len(runs)} strategies · {', '.join(universe.symbols)} · "
             f"{runs[0]['timeframe']} · {runs[0]['start']}..{runs[0]['end']} "
             f"({runs[0]['bars']} bars)",
             f"  buy & hold over the same window: {bh * 100:+.1f}%", "",
             "   net profit |  max dd |   pf |  sharpe | trades | win | strategy"]
    for r in runs:
        m = r["metrics"]
        lines.append(f"  {m.total_return * 100:+9.1f}% | {m.max_drawdown * 100:+6.1f}% | "
                     f"{_num(m.profit_factor):>4} | {m.sharpe:+7.2f} | "
                     f"{m.trades:>6} | {m.win_rate * 100:>2.0f}% | {r['name'][:32]}")
    beat = [r["name"] for r in runs if r["metrics"].total_return > bh]
    lines.append(f"\n  beat buy-and-hold: {', '.join(beat) if beat else 'none of them'}")
    lines.append("  ranking several strategies on one window is itself a way to "
                 "overfit — the winner here is a candidate, not a conclusion")
    return "\n".join(lines), {
        "symbols": universe.symbols, "timeframe": runs[0]["timeframe"],
        "start": runs[0]["start"], "end": runs[0]["end"], "bars": runs[0]["bars"],
        "benchmark_return": round(bh, 6),
        "results": [{"name": r["name"], "metrics": r["metrics"].to_dict(),
                     "fitness": r["fitness"]} for r in runs],
    }


@tool("walk_forward", "Walk-forward test",
      "Re-test a strategy on windows it was not chosen on. Each fold reports "
      "the earlier (in-sample) window against the later (out-of-sample) one, "
      "so you can see whether the result survives moving forward in time. This "
      "is the cheapest honest check this server offers.",
      {"symbols": _SYMBOLS_PROPERTY,
       "entry_rules": _ENTRY_PROPERTY, "exit_rules": _EXIT_PROPERTY,
       "risk": _RISK_PROPERTY, "name": {"type": "string"},
       "timeframe": _TIMEFRAME_PROPERTY, "bars": _BARS_PROPERTY,
       "source": _SOURCE_PROPERTY,
       "folds": {"type": "integer", "description": "how many folds (default 3)"},
       "starting_cash": {"type": "number"}, "commission_bps": {"type": "number"},
       "slippage_bps": {"type": "number"}},
      required=["symbols", "entry_rules", "exit_rules"])
def _walk_forward(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbols = _symbols(args)
    timeframe = str_arg(args, "timeframe", "1D") or "1D"
    count = int_arg(args, "bars", 2000, lo=300, hi=20_000)
    source = choice_arg(args, "source", [view.default_source] + [
        s for s in ("tradingview", "yahoo", "synthetic") if s != view.default_source])
    folds = int_arg(args, "folds", 3, lo=1, hi=10)
    genome = _strategy_from(args)
    universe = view.universe(symbols, timeframe, count, source)
    common = _common(args)

    splits = walk_forward_splits(universe, folds=folds)
    rows, oos_returns = [], []
    for split in splits:
        in_sample = _run(view, genome, split.train, timeframe, **common)
        out_sample = _run(view, genome, split.test, timeframe, **common)
        oos_returns.append(out_sample["metrics"].total_return
                           - out_sample["metrics"].benchmark_return)
        rows.append({"fold": split.name,
                     "in_sample": in_sample, "out_of_sample": out_sample})

    lines = [f"{genome.name} — walk-forward over {', '.join(universe.symbols)} · "
             f"{rows[0]['in_sample']['timeframe']} · {len(universe)} bars",
             "  fold  | window                   | net profit | vs b&h | trades | sharpe"]
    for row in rows:
        for label, key in (("in ", "in_sample"), ("out", "out_of_sample")):
            r = row[key]
            m = r["metrics"]
            lines.append(f"  {row['fold']:<5} | {label} {r['start']}..{r['end']} | "
                         f"{m.total_return * 100:+9.1f}% | "
                         f"{(m.total_return - m.benchmark_return) * 100:+5.1f}% | "
                         f"{m.trades:>6} | {m.sharpe:+.2f}")
    positive = sum(1 for x in oos_returns if x > 0)
    mean_excess = sum(oos_returns) / len(oos_returns)
    lines.append(f"\n  out-of-sample excess over buy-and-hold: {mean_excess * 100:+.1f}% "
                 f"mean, positive in {positive} of {len(oos_returns)} folds")
    if positive == len(oos_returns) and mean_excess > 0:
        lines.append("  it held up on every fold — weak evidence, but the right "
                     "kind of weak evidence")
    elif positive == 0:
        lines.append("  it did not beat buy-and-hold out of sample on any fold; "
                     "the in-sample result was the window, not the strategy")
    else:
        lines.append("  mixed across folds — consistent with noise; more symbols "
                     "or a longer history would say more than more tuning")
    return "\n".join(lines), {
        "name": genome.name, "symbols": universe.symbols,
        "folds": [{"fold": row["fold"],
                   "in_sample": {"start": row["in_sample"]["start"],
                                 "end": row["in_sample"]["end"],
                                 "metrics": row["in_sample"]["metrics"].to_dict()},
                   "out_of_sample": {"start": row["out_of_sample"]["start"],
                                     "end": row["out_of_sample"]["end"],
                                     "metrics": row["out_of_sample"]["metrics"].to_dict()}}
                  for row in rows],
        "mean_out_of_sample_excess": mean_excess,
        "folds_positive": positive, "folds_total": len(oos_returns),
    }


@tool("backtest_evolved_agent", "Backtest an evolved agent",
      "Take an agent from an evotrader training run by id and test it on "
      "TradingView data — different symbols, a different timeframe, or dates "
      "it never evolved on. The bridge between what evolution found and what "
      "the chart says.",
      {"genome_id": {"type": "string", "description": "genome id from a training run"},
       "symbols": _SYMBOLS_PROPERTY, "timeframe": _TIMEFRAME_PROPERTY,
       "bars": _BARS_PROPERTY, "source": _SOURCE_PROPERTY,
       "db": {"type": "string", "description": "SQLite path (default $EVOTRADER_DB)"},
       "trades": {"type": "integer", "description": "sample trades to show (default 10)"},
       "starting_cash": {"type": "number"}, "commission_bps": {"type": "number"},
       "slippage_bps": {"type": "number"}},
      required=["genome_id", "symbols"])
def _backtest_evolved_agent(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    genome_id = required_str(args, "genome_id")
    symbols = _symbols(args)
    timeframe = str_arg(args, "timeframe", "1D") or "1D"
    count = int_arg(args, "bars", 2000, lo=100, hi=20_000)
    source = choice_arg(args, "source", [view.default_source] + [
        s for s in ("tradingview", "yahoo", "synthetic") if s != view.default_source])
    if str_arg(args, "db"):
        view.db_path = str_arg(args, "db")
        view.close()
    genome = view.store().get_genome(genome_id)
    if genome is None:
        raise ToolError(f"unknown genome {genome_id!r} in {view.db_path}")
    universe = view.universe(symbols, timeframe, count, source)
    run = _run(view, genome, universe, timeframe, **_common(args))

    lines = [genome.describe(), ""] + _report_lines(run)
    lines += _trade_lines(run, int_arg(args, "trades", 10, lo=0, hi=100))
    caveats = _caveats(run["metrics"])
    if caveats:
        lines.append("\n  worth noting")
        lines += caveats
    lines.append(f"\n  this agent was evolved on its own symbols and window; "
                 f"scoring it here on {', '.join(universe.symbols)} is a test it "
                 f"has not been fitted to, which is the point")
    return "\n".join(lines), {
        "genome_id": genome_id, "name": genome.name,
        "generation": genome.generation, "origin": genome.origin,
        "symbols": run["symbols"], "timeframe": run["timeframe"],
        "start": run["start"], "end": run["end"], "bars": run["bars"],
        "metrics": run["metrics"].to_dict(), "fitness": run["fitness"],
        "strategy": genome.to_dict(),
        "trades": [t.to_dict() for t in run["journal"].trades],
        "caveats": [c.strip() for c in caveats],
    }


@tool("quote", "Quote",
      "Last price, the day's change and volume for one or more symbols. A "
      "snapshot, not history — `get_bars` is what a backtest runs on.",
      {"symbols": _SYMBOLS_PROPERTY,
       "fields": {"type": "array", "items": {"type": "string"},
                  "description": "close, change, volume, market_cap, rsi, "
                                 "sma50, sma200, perf_ytd, sector, ..."}},
      required=["symbols"])
def _quote(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbols = _symbols(args)
    try:
        rows = tvdata.quotes(symbols, fields=list_arg(args, "fields"))
    except tvdata.TradingViewError as exc:
        raise ToolError(str(exc)) from exc
    if not rows:
        return f"no data for {', '.join(symbols)}", {"quotes": []}
    lines = []
    for r in rows:
        change = r.get("change")
        lines.append(f"  {r['symbol']:<16} {_fmt_num(r.get('close')):>10}  "
                     f"{('%+.2f%%' % change) if isinstance(change, (int, float)) else '    -':>8}  "
                     f"vol {_fmt_num(r.get('volume'), 0):>14}  "
                     f"{str(r.get('description') or '')[:34]}")
    return "\n".join(lines), {"quotes": rows}


@tool("technicals", "Technical snapshot",
      "TradingView's own indicator values for one symbol — RSI, MACD, the "
      "moving averages, ATR, performance — as the chart shows them. Useful for "
      "checking a rule against what TradingView displays; the backtest computes "
      "its own indicators from bars and does not read these.",
      {"symbol": {"type": "string", "description": "e.g. NASDAQ:AAPL"}},
      required=["symbol"])
def _technicals(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    symbol = required_str(args, "symbol")
    try:
        row = tvdata.technicals(symbol)
    except tvdata.TradingViewError as exc:
        raise ToolError(str(exc)) from exc
    order = [("close", "close"), ("change", "change %"), ("rsi", "RSI(14)"),
             ("macd", "MACD"), ("macd_signal", "MACD signal"),
             ("sma20", "SMA20"), ("sma50", "SMA50"), ("sma200", "SMA200"),
             ("atr", "ATR"), ("volatility", "volatility %"),
             ("perf_week", "week %"), ("perf_month", "month %"),
             ("perf_ytd", "YTD %")]
    lines = [f"{row['symbol']}"]
    for key, label in order:
        if row.get(key) is not None:
            lines.append(f"  {label:<14} {_fmt_num(row[key])}")
    close, sma200 = row.get("close"), row.get("sma200")
    if isinstance(close, (int, float)) and isinstance(sma200, (int, float)):
        lines.append(f"  {'vs SMA200':<14} "
                     f"{'above' if close > sma200 else 'below'} "
                     f"({(close / sma200 - 1) * 100:+.1f}%)")
    return "\n".join(lines), {"technicals": row}


@tool("screener", "Screen the market",
      "Find symbols matching conditions — the way to turn a strategy into a "
      "list worth testing it on. Filters are {field, op, value} over close, "
      "change, volume, relative_volume, market_cap, pe, rsi, macd, sma20/50/200, "
      "atr, volatility, perf_week/month/ytd, gap, sector. Results are common "
      "stock only unless you say otherwise, so no preferred shares or second "
      "listings.",
      {"filters": {"type": "array", "items": {"type": "object"},
                   "description": "[{\"field\": \"rsi\", \"op\": \"less\", "
                                  "\"value\": 35}, ...]; op is greater, less, "
                                  "egreater, eless, equal, nequal, in_range"},
       "fields": {"type": "array", "items": {"type": "string"},
                  "description": "columns to return"},
       "sort_by": {"type": "string", "description": "field to sort on (default market_cap)"},
       "ascending": {"type": "boolean", "description": "smallest first (default false)"},
       "limit": {"type": "integer", "description": "rows (default 25, max 100)"},
       "market": {"type": "string", "description": "america (default), crypto, forex, ..."},
       "include_all_share_classes": {"type": "boolean",
                                     "description": "keep preferred shares and "
                                                    "second listings (default false)"}},
      required=["filters"])
def _screener(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    filters = list_arg(args, "filters")
    if not filters:
        raise ToolError("give at least one filter, e.g. "
                        "[{\"field\": \"rsi\", \"op\": \"less\", \"value\": 35}]")
    if not all(isinstance(f, dict) for f in filters):
        raise ToolError("each filter must be an object with field, op and value")
    try:
        rows = tvdata.screen(
            filters, fields=list_arg(args, "fields"),
            sort_by=str_arg(args, "sort_by", "market_cap") or "market_cap",
            descending=not bool(args.get("ascending")),
            limit=int_arg(args, "limit", 25, hi=100),
            market=str_arg(args, "market", "america") or "america",
            common_stock_only=not bool(args.get("include_all_share_classes")))
    except tvdata.TradingViewError as exc:
        raise ToolError(str(exc)) from exc
    if not rows:
        return "nothing matched those filters", {"matches": []}
    described = ", ".join(f"{f.get('field')} {f.get('op')} {f.get('value')}"
                          for f in filters)
    lines = [f"{len(rows)} matches — {described}"]
    for r in rows:
        bits = [f"  {r['symbol']:<16}"]
        for key in ("close", "change", "rsi"):
            if r.get(key) is not None:
                bits.append(f"{key} {_fmt_num(r[key]):>9}")
        bits.append(str(r.get("description") or "")[:30])
        lines.append("  ".join(bits))
    lines.append("\n  a screen is a list of candidates, not signals — "
                 "`backtest` them before believing any of it")
    return "\n".join(lines), {"matches": rows, "filters": filters}


@tool("strategy_language", "Strategy language",
      "The rule vocabulary: every market and portfolio feature a rule may "
      "reference, the functions it may call, and the risk fields. Read this "
      "before writing entry or exit rules.")
def _strategy_language(view: Backtester, args: Dict[str, Any]) -> ToolResult:
    from .dsl import FUNCTION_DOCS
    from .features import FEATURE_DOCS, MARKET_FEATURES, PORTFOLIO_FEATURES

    return rule_reference() + "\n" + genome_schema_text(), {
        "market_features": {n: FEATURE_DOCS.get(n, "") for n in MARKET_FEATURES},
        "portfolio_features": {n: FEATURE_DOCS.get(n, "") for n in PORTFOLIO_FEATURES},
        "functions": dict(FUNCTION_DOCS),
    }


# ------------------------------------------------------------------ resources

def _resources(view: Backtester) -> List[Dict[str, Any]]:
    return [{"uri": "evotrader://strategy-language",
             "name": "strategy language",
             "description": "features, functions and the strategy shape",
             "mimeType": "text/plain"},
            {"uri": "tradingview://timeframes",
             "name": "timeframes",
             "description": "supported resolutions and their annualisation factors",
             "mimeType": "text/plain"}]


def _read_resource(view: Backtester, uri: str) -> Dict[str, Any]:
    if uri == "evotrader://strategy-language":
        return {"uri": uri, "mimeType": "text/plain",
                "text": rule_reference() + "\n" + genome_schema_text()}
    if uri == "tradingview://timeframes":
        rows = "\n".join(f"  {tf:<4} {per:>10,.0f} bars/year"
                         for tf, per in tvdata.TIMEFRAMES.items())
        return {"uri": uri, "mimeType": "text/plain",
                "text": "TradingView resolutions accepted by this server:\n" + rows}
    raise ToolError(f"unknown resource {uri!r}")


def build_server(*, source: str = "tradingview", db_path: str = "",
                 session_token: str = "", refresh: bool = True) -> MCPServer:
    view = Backtester(source=source, db_path=db_path, session_token=session_token,
                      refresh=refresh)
    return MCPServer(view, TV_TOOLS, name=SERVER_NAME,
                     title="TradingView backtesting", instructions=INSTRUCTIONS,
                     resources=_resources, read_resource=_read_resource)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tradingview-backtest",
        description="Backtest strategies on TradingView data, over MCP on stdio.")
    parser.add_argument("--source", choices=["tradingview", "yahoo", "synthetic"],
                        default="tradingview", help="default bar source")
    parser.add_argument("--db", dest="db_path", default="",
                        help="evotrader SQLite path, for backtest_evolved_agent")
    args = parser.parse_args(argv)
    print(f"{SERVER_NAME} on stdio (bars from {args.source})", file=sys.stderr)
    try:
        return serve(build_server(source=args.source, db_path=args.db_path))
    except KeyboardInterrupt:  # pragma: no cover - interactive
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
