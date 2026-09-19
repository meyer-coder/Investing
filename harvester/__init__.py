"""Market-data harvester: TradingView candles, kept on disk, deepened over time.

    from harvester import tvdata, tvcache, tvarchive

    tvdata.fetch_bars("NASDAQ:AAPL", "1D", 5000)       # one pull
    tvcache.cached_bars("NASDAQ:AAPL", "1D", 5000)     # pull + store + merge
    tvarchive.build("CME_MINI", "NQ", "5", since_year=2015)   # deep futures
"""
from .data import Bars, DataError, Universe
from .tvarchive import build as build_archive
from .tvcache import cached_bars, export_csv, import_csv
from .tvdata import fetch_bars, quotes, screen, search_symbols, technicals

__version__ = "0.1.0"
__all__ = ["Bars", "Universe", "DataError", "fetch_bars", "search_symbols",
           "quotes", "screen", "technicals", "cached_bars", "import_csv",
           "export_csv", "build_archive"]
