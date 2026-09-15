"""MCP server exposing evotrader's TradingView screener.

Five tools over the client in :mod:`evotrader.screener`, so an interactive
session and the evolution loop share one implementation and one cache.

The scanner reports current values only.  Every screen result carries the date
it was captured, and a universe used to backtest an earlier window carries an
explicit bias note — the tools surface it rather than leaving a caller to
rediscover it.

Run it with ``python -m evotrader.mcp_server`` (stdio transport).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence

from mcp.server.mcpserver import MCPServer

from .screener import (COLUMNS, MARKETS, OPERATIONS, PRESETS, Filter, Screen,
                       ScreenerError, preset, quote_screen, run_screen,
                       yahoo_symbols)

mcp = MCPServer(
    name="evotrader-tradingview",
    instructions="TradingView screening for symbol-universe selection. "
                 "Returns current cross-sectional values, never history — "
                 "backtest bars come from evotrader's own data layer.",
    version="0.1.0",
)


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
