"""A local store of TradingView candles that deepens every time you fetch.

TradingView serves a rolling window — about five to six thousand bars per
timeframe, whatever the timeframe — so one request gives decades of daily bars
but only months of 5-minute ones.  The window moves forward; the history does
not come back.  Fetch weekly and merge, though, and the 5-minute record grows
past anything a single request will ever return.

    bars = cached_bars("NASDAQ:AAPL", "5", 20000)     # cache + a fresh pull

Bars are keyed by timestamp, so re-fetching overlapping windows is free of
duplicates, and a bar TradingView later revises replaces the one on disk.  The
files are CSV under ``data/cache/tv`` — greppable, diffable, and readable by
anything.
"""
from __future__ import annotations

import csv
import os
import re
import time
from typing import Dict, List, Optional, Sequence

import numpy as np

from .data import Bars, DataError
from .tvdata import fetch_bars, interval_seconds, normalise_timeframe

CACHE_DIR = os.environ.get("EVOTRADER_TV_CACHE",
                           os.path.join("data", "cache", "tv"))


def cache_path(symbol: str, timeframe: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", symbol.upper())
    return os.path.join(CACHE_DIR, f"{safe}__{normalise_timeframe(timeframe)}.csv")


def read_cache(symbol: str, timeframe: str) -> Optional[Bars]:
    return _read_path(cache_path(symbol, timeframe), symbol.upper())


def _read_path(path: str, symbol: str) -> Optional[Bars]:
    if not os.path.exists(path):
        return None
    dates: List[str] = []
    cols: List[List[float]] = [[], [], [], [], []]
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                values = [float(row[k]) for k in
                          ("open", "high", "low", "close", "volume")]
            except (TypeError, ValueError, KeyError):
                continue
            dates.append(row["date"])
            for col, value in zip(cols, values):
                col.append(value)
    if not dates:
        return None
    return Bars(symbol, dates, *[np.asarray(c, dtype=float) for c in cols])


def write_cache(bars: Bars, timeframe: str) -> str:
    path = cache_path(bars.symbol, timeframe)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for i, stamp in enumerate(bars.dates):
            writer.writerow([stamp, bars.open[i], bars.high[i], bars.low[i],
                             bars.close[i], bars.volume[i]])
    os.replace(tmp, path)
    return path


def merge(old: Optional[Bars], new: Optional[Bars]) -> Bars:
    """Union two series by timestamp; the newer fetch wins any overlap."""
    if old is None and new is None:
        raise DataError("nothing to merge")
    if old is None:
        return new
    if new is None:
        return old
    rows: Dict[str, Sequence[float]] = {}
    for bars in (old, new):                      # new second, so it overwrites
        for i, stamp in enumerate(bars.dates):
            rows[stamp] = (bars.open[i], bars.high[i], bars.low[i],
                           bars.close[i], bars.volume[i])
    dates = sorted(rows)
    cols = list(zip(*(rows[d] for d in dates)))
    return Bars(new.symbol, dates, *[np.asarray(c, dtype=float) for c in cols])


def cached_bars(symbol: str, timeframe: str = "1D", bars: int = 2000, *,
                refresh: bool = True, force: bool = False,
                session_token: str = "", timeout: float = 30.0,
                fetch=fetch_bars) -> Bars:
    """Return the deepest history available: what is on disk, plus a fresh pull.

    A failed fetch is not fatal when the cache already holds enough bars — the
    point of the cache is that history survives the feed being unavailable.

    Reads are cache-first: a series pulled moments ago is not pulled again
    unless ``force`` says so, because a cold fetch costs seconds and callers
    like an MCP client give up long before a dozen of them finish.
    """
    stored = read_cache(symbol, timeframe)
    if refresh and not force and stored is not None \
            and _checked_recently(symbol, timeframe):
        # A pull that cannot return anything new is a pull worth skipping: it
        # costs seconds, and a client's tool timeout is not generous.
        refresh = False
    fetched, error = None, ""
    if refresh:
        try:
            fetched = fetch(symbol, timeframe, bars, session_token=session_token,
                            timeout=timeout)
        except DataError as exc:
            error = str(exc)
            if stored is None:
                raise
    if fetched is not None:
        merged = merge(stored, fetched)
        if stored is None or len(merged) != len(stored):
            write_cache(merged, timeframe)
        else:
            _mark_checked(symbol, timeframe)
    else:
        merged = stored
    window = merged if len(merged) <= bars else Bars(
        merged.symbol, merged.dates[-bars:], merged.open[-bars:],
        merged.high[-bars:], merged.low[-bars:], merged.close[-bars:],
        merged.volume[-bars:])
    window.warnings = [error] if error else []
    return window


def _checked_recently(symbol: str, timeframe: str) -> bool:
    """Was this series refreshed within half a bar's worth of time?

    The file's own mtime is the record, which keeps weekends honest: nothing
    new arrives on a Sunday, and a daily series should not be re-pulled for
    every backtest because Friday's bar looks two days old.
    """
    path = cache_path(symbol, timeframe)
    if not os.path.exists(path):
        return False
    return time.time() - os.path.getmtime(path) < interval_seconds(timeframe) * 0.5


def _mark_checked(symbol: str, timeframe: str) -> None:
    path = cache_path(symbol, timeframe)
    if os.path.exists(path):
        os.utime(path, None)


def cache_summary() -> List[Dict[str, object]]:
    """What the cache holds, for reporting how deep the record has grown."""
    if not os.path.isdir(CACHE_DIR):
        return []
    out: List[Dict[str, object]] = []
    for name in sorted(os.listdir(CACHE_DIR)):
        if not name.endswith(".csv") or "__" not in name:
            continue
        label, timeframe = name[:-4].rsplit("__", 1)
        path = os.path.join(CACHE_DIR, name)
        # Read the file itself: the name is sanitised, so it cannot be turned
        # back into a symbol reliably.
        stored = _read_path(path, label)
        if stored is None:
            continue
        out.append({"symbol": label, "timeframe": timeframe,
                    "bars": len(stored), "start": stored.dates[0],
                    "end": stored.dates[-1], "path": path})
    return out
