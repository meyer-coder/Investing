#!/usr/bin/env python3
"""A minimal TradingView MCP server you run yourself.

Why run your own rather than use a hosted connector:
  * count goes to 5000 instead of 1000 (tvdatafeed's own ceiling)
  * it authenticates as YOU, so your TradingView plan's bar limit applies
    (anonymous access is capped at the free tier's 5,000 regardless of what
    you pay)
  * extended_session is on, so equities include pre- and post-market
  * large results are written to a CSV file and summarised, instead of being
    dumped into the reply where they overflow the response limit
  * it runs locally, so there is no remote host to return a 502

Setup:
    pip install mcp pandas
    pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git
    export TV_USERNAME=...     # optional but strongly recommended
    export TV_PASSWORD=...
    claude mcp add tradingview-local -- python3 /full/path/to/this/file.py

Bar limits are set by TradingView per plan, above whatever this server does:
Basic 5,000 / Essential 10,000 / Plus 10,000 / Premium 20,000 / Ultimate 40,000.
At 5m that is roughly 18 trading days of NQ on Basic, 72 on Premium. Deep
intraday history still belongs in a file — see docs/data-sources.md.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_BARS = 5000          # tvdatafeed's ceiling; TradingView's plan cap sits above it
INLINE_ROW_LIMIT = 400   # beyond this, write a file rather than flooding the reply

OUTDIR = Path(os.environ.get("TV_MCP_OUTDIR", Path.home() / ".tradingview-mcp" / "data"))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit("missing dependency: pip install mcp")

try:
    from tvDatafeed import TvDatafeed, Interval
except ImportError:
    sys.exit("missing dependency: pip install --upgrade --no-cache-dir "
             "git+https://github.com/rongardF/tvdatafeed.git")

INTERVALS = {
    "1m": Interval.in_1_minute,   "3m": Interval.in_3_minute,
    "5m": Interval.in_5_minute,   "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute, "45m": Interval.in_45_minute,
    "1h": Interval.in_1_hour,     "2h": Interval.in_2_hour,
    "4h": Interval.in_4_hour,     "1D": Interval.in_daily,
    "1W": Interval.in_weekly,     "1M": Interval.in_monthly,
}

mcp = FastMCP("tradingview-local")
_client: TvDatafeed | None = None


def client() -> TvDatafeed:
    """Log in once and reuse. Anonymous works but caps you at the free tier."""
    global _client
    if _client is None:
        user, pw = os.environ.get("TV_USERNAME"), os.environ.get("TV_PASSWORD")
        _client = TvDatafeed(username=user, password=pw) if user and pw else TvDatafeed()
    return _client


def split_symbol(symbol: str) -> tuple[str, str]:
    """'CME_MINI:NQ1!' -> ('NQ1!', 'CME_MINI'). A bare symbol defaults to NASDAQ."""
    if ":" in symbol:
        exchange, ticker = symbol.split(":", 1)
        return ticker.strip(), exchange.strip()
    return symbol.strip(), "NASDAQ"


@mcp.tool()
def bars(symbol: str, timeframe: str = "5m", count: int = 1000,
         extended_session: bool = True) -> str:
    """Historical OHLCV candles from TradingView.

    symbol: EXCHANGE:TICKER, e.g. CME_MINI:NQ1!, NASDAQ:AAPL, BINANCE:BTCUSDT
    timeframe: 1m 3m 5m 15m 30m 45m 1h 2h 4h 1D 1W 1M
    count: up to 5000. Your TradingView plan may cap it lower.
    extended_session: include pre/post-market for equities. No effect on futures.

    Coverage is count x timeframe, so 1000 5m bars of a 23-hour future is about
    4 trading days, while 1000 daily bars is about 4 years. Returns a CSV file
    path plus a summary when the result is large.
    """
    if timeframe not in INTERVALS:
        return f"error: unknown timeframe {timeframe!r}. use one of: {', '.join(INTERVALS)}"
    if count < 1:
        return "error: count must be at least 1"

    requested = count
    count = min(count, MAX_BARS)
    ticker, exchange = split_symbol(symbol)

    try:
        df = client().get_hist(symbol=ticker, exchange=exchange,
                               interval=INTERVALS[timeframe], n_bars=count,
                               extended_session=extended_session)
    except Exception as exc:
        return (f"error fetching {symbol}: {exc}\n"
                "if this persists, TradingView may have changed its feed — try "
                "reinstalling tvdatafeed from GitHub.")

    if df is None or df.empty:
        return (f"no data for {symbol} at {timeframe}. check the EXCHANGE:TICKER "
                "spelling — futures usually need a continuous suffix, e.g. NQ1!")

    df = df.sort_index()
    note = ""
    if requested > MAX_BARS:
        note = f"\nNOTE: asked for {requested}, capped at {MAX_BARS} (tvdatafeed's limit)."
    if len(df) < count * 0.9:
        note += (f"\nNOTE: asked for {count} bars, got {len(df)}. That is usually "
                 "your TradingView plan's bar limit, not an error. "
                 "Basic 5,000 / Essential 10,000 / Premium 20,000 / Ultimate 40,000.")

    head = (f"{symbol} {timeframe} — {len(df)} bars, "
            f"{df.index[0]} to {df.index[-1]} (exchange local time)")

    if len(df) <= INLINE_ROW_LIMIT:
        return head + note + "\n\n" + df.to_csv()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUTDIR / f"{exchange}_{ticker}_{timeframe}_{stamp}.csv".replace("!", "")
    df.to_csv(path)

    per_day = df.groupby(df.index.date).size()
    return (f"{head}{note}\n"
            f"written to: {path}\n"
            f"sessions: {len(per_day)}, bars/session median {per_day.median():.0f} "
            f"(min {per_day.min()}, max {per_day.max()})\n\n"
            f"first 5 and last 5 rows:\n{df.head().to_csv()}\n...\n{df.tail().to_csv()}")


@mcp.tool()
def search_symbol(query: str, exchange: str = "") -> str:
    """Find TradingView tickers by name or partial symbol."""
    try:
        results = client().search_symbol(query, exchange)
    except Exception as exc:
        return f"error searching for {query!r}: {exc}"
    if not results:
        return f"no matches for {query!r}"
    lines = [f"{r.get('exchange','?')}:{r.get('symbol','?'):<16} "
             f"{r.get('type','') or '':<10} {r.get('description','')}"
             for r in results[:25]]
    return f"{len(results)} matches for {query!r}:\n" + "\n".join(lines)


@mcp.tool()
def status() -> str:
    """Report whether the server is logged in, and its limits."""
    authed = bool(os.environ.get("TV_USERNAME") and os.environ.get("TV_PASSWORD"))
    return (f"tradingview-local\n"
            f"authenticated: {authed}"
            f"{'' if authed else '  <- anonymous: capped at the free tier (5,000 bars)'}\n"
            f"max bars per call: {MAX_BARS}\n"
            f"output directory: {OUTDIR}\n"
            f"coverage is count x timeframe: 1000 5m bars of a 23h future is "
            f"~4 trading days; 1000 daily bars is ~4 years.")


if __name__ == "__main__":
    mcp.run()
