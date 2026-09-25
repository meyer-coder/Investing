"""What "everything" means: the symbol lists a full sweep walks.

The built-in lists are the liquid instruments worth having deep history for.
They are a starting point, not a limit — ``--universe FILE`` takes any list of
exchange-qualified symbols, and ``--top N`` builds one from TradingView's own
screener.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence, Tuple

from .tvdata import COMMON_STOCK_FILTERS, SCAN_FIELDS, TradingViewError, _scan

# Index and sector ETFs: the cheapest broad coverage of the US market.
ETFS = [
    "AMEX:SPY", "NASDAQ:QQQ", "AMEX:IWM", "AMEX:DIA", "AMEX:MDY", "AMEX:RSP",
    "AMEX:XLF", "AMEX:XLE", "AMEX:XLK", "AMEX:XLV", "AMEX:XLI", "AMEX:XLY",
    "AMEX:XLP", "AMEX:XLU", "AMEX:XLB", "AMEX:XLRE", "AMEX:XLC",
    "AMEX:GLD", "AMEX:SLV", "AMEX:USO", "AMEX:UNG", "NASDAQ:TLT", "AMEX:HYG",
    "AMEX:LQD", "AMEX:EEM", "AMEX:EFA", "CBOE:ARKK", "NASDAQ:SMH", "CBOE:VXX",
]

# Continuous front-month futures.  Deep intraday history for these comes from
# the contract archive, not from the continuous symbol.
FUTURES = [
    "CME_MINI:NQ1!", "CME_MINI:ES1!", "CME_MINI:RTY1!", "CBOT_MINI:YM1!",
    "NYMEX:CL1!", "NYMEX:NG1!", "COMEX:GC1!", "COMEX:SI1!", "COMEX:HG1!",
    "CBOT:ZB1!", "CBOT:ZN1!", "CBOT:ZC1!", "CBOT:ZS1!", "CBOT:ZW1!",
    "CME:6E1!", "CME:6J1!", "CME:6B1!",
]

# (exchange, root) pairs the archive builder can walk back through expired
# quarterly contracts.  Only the index futures roll on the H/M/U/Z calendar
# the archive assumes, so only they are listed.
FUTURES_ROOTS: List[Tuple[str, str]] = [
    ("CME_MINI", "NQ"), ("CME_MINI", "ES"), ("CME_MINI", "RTY"),
    ("CBOT_MINI", "YM"),
]

FX = [
    "FX:EURUSD", "FX:GBPUSD", "FX:USDJPY", "FX:AUDUSD", "FX:USDCAD",
    "FX:USDCHF", "FX:NZDUSD", "FX:EURJPY", "FX:GBPJPY",
]

CRYPTO = [
    "BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT",
    "BINANCE:BNBUSDT", "BINANCE:XRPUSDT", "COINBASE:BTCUSD", "COINBASE:ETHUSD",
]

INDICES = ["SP:SPX", "NASDAQ:NDX", "TVC:DJI", "TVC:VIX", "TVC:DXY", "TVC:US10Y"]

# The mega-caps carry most of the index, so they are worth having even when a
# screener pull is not run.
MEGACAPS = [
    "NASDAQ:AAPL", "NASDAQ:MSFT", "NASDAQ:NVDA", "NASDAQ:AMZN", "NASDAQ:GOOGL",
    "NASDAQ:META", "NASDAQ:TSLA", "NASDAQ:AVGO", "NYSE:BRK.B", "NYSE:JPM",
    "NYSE:V", "NYSE:UNH", "NYSE:XOM", "NYSE:JNJ", "NASDAQ:WMT", "NYSE:PG",
    "NYSE:MA", "NASDAQ:COST", "NASDAQ:AMD", "NASDAQ:NFLX",
]

GROUPS: Dict[str, List[str]] = {
    "etfs": ETFS, "futures": FUTURES, "fx": FX, "crypto": CRYPTO,
    "indices": INDICES, "megacaps": MEGACAPS,
}

DEFAULT_GROUPS = ("etfs", "futures", "indices", "megacaps", "fx", "crypto")


def group(names: Sequence[str]) -> List[str]:
    """Symbols for named groups, in order, without duplicates."""
    out: List[str] = []
    for name in names:
        key = name.strip().lower()
        if key == "all":
            for g in DEFAULT_GROUPS:
                out.extend(GROUPS[g])
            continue
        if key not in GROUPS:
            raise TradingViewError(
                f"unknown group {name!r}; available: {', '.join(sorted(GROUPS))}, all")
        out.extend(GROUPS[key])
    return dedupe(out)


def dedupe(symbols: Sequence[str]) -> List[str]:
    """Upper-case, de-duplicated, original order kept."""
    seen, out = set(), []
    for s in symbols:
        key = s.strip().upper()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def read_file(path: str) -> List[str]:
    """One exchange-qualified symbol per line; ``#`` comments allowed."""
    if not os.path.exists(path):
        raise TradingViewError(f"no such universe file: {path}")
    with open(path) as fh:
        lines = [line.split("#", 1)[0].strip() for line in fh]
    symbols = dedupe([l for l in lines if l])
    if not symbols:
        raise TradingViewError(f"{path} lists no symbols")
    return symbols


def write_file(path: str, symbols: Sequence[str]) -> str:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as fh:
        for s in symbols:
            fh.write(s + "\n")
    return path


def from_screener(top: int = 500, *, market: str = "america",
                  sort_by: str = "market_cap", min_volume: int = 0,
                  timeout: float = 25.0) -> List[str]:
    """The top ``top`` common stocks by ``sort_by``, straight from the screener.

    The scanner serves at most 100 rows per request, so this pages through in
    hundreds rather than asking for a number it will silently truncate.
    """
    if sort_by not in SCAN_FIELDS:
        raise TradingViewError(f"cannot sort by {sort_by!r}; "
                               f"available: {', '.join(sorted(SCAN_FIELDS))}")
    filters: List[Dict[str, Any]] = list(COMMON_STOCK_FILTERS)
    if min_volume > 0:
        filters.append({"left": "volume", "operation": "greater",
                        "right": int(min_volume)})
    wanted = max(1, int(top))
    symbols: List[str] = []
    for start in range(0, wanted, 100):
        rows = _scan({
            "filter": filters,
            "options": {"lang": "en"},
            "symbols": {"query": {"types": []}, "tickers": []},
            "columns": [SCAN_FIELDS["name"], SCAN_FIELDS[sort_by]],
            "sort": {"sortBy": SCAN_FIELDS[sort_by], "sortOrder": "desc"},
            "range": [start, min(start + 100, wanted)],
        }, market=market, timeout=timeout)
        if not rows:
            break                      # the market has no more to give
        symbols.extend(str(r.get("s", "")) for r in rows)
    return dedupe(symbols)[:wanted]
