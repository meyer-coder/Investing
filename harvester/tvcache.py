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

# HARVEST_CACHE is this tool's name for it; EVOTRADER_TV_CACHE is honoured so a
# store already filled by evotrader is picked up rather than re-downloaded.
CACHE_DIR = (os.environ.get("HARVEST_CACHE")
             or os.environ.get("EVOTRADER_TV_CACHE")
             or os.path.join("data", "cache", "tv"))


def cache_path(symbol: str, timeframe: str) -> str:
    """Where a series lives.  ``.npz`` is the store; ``.csv`` is interchange."""
    return _path(symbol, timeframe, ".npz")


def csv_path(symbol: str, timeframe: str) -> str:
    return _path(symbol, timeframe, ".csv")


def _path(symbol: str, timeframe: str, suffix: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", symbol.upper())
    return os.path.join(CACHE_DIR, f"{safe}__{normalise_timeframe(timeframe)}{suffix}")


def read_cache(symbol: str, timeframe: str) -> Optional[Bars]:
    """Read the store, preferring the binary form.

    Text costs about 6 seconds per million bars to parse and the binary form
    about 0.2 — which stops mattering at a few thousand bars and decides
    everything at ten years of one-minute data.
    """
    npz = cache_path(symbol, timeframe)
    if os.path.exists(npz):
        return _read_npz(npz, symbol.upper())
    return _read_path(csv_path(symbol, timeframe), symbol.upper())


def _read_npz(path: str, symbol: str) -> Optional[Bars]:
    try:
        with np.load(path, allow_pickle=False) as z:
            return Bars(symbol, [str(d) for d in z["dates"]], z["open"],
                        z["high"], z["low"], z["close"], z["volume"])
    except (OSError, ValueError, KeyError):
        return None


def _read_path(path: str, symbol: str) -> Optional[Bars]:
    if not os.path.exists(path):
        return None
    dates: List[str] = []
    cols: List[List[float]] = [[], [], [], [], []]
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        names = {(n or "").strip().lower(): n for n in (reader.fieldnames or [])}
        # Another tool's export will not use these exact headers.
        date_key = next((names[k] for k in ("date", "datetime", "time",
                                            "timestamp", "date_time")
                         if k in names), None)
        keys = {k: names.get(k) for k in ("open", "high", "low", "close", "volume")}
        if date_key is None or not all(keys[k] for k in ("open", "high", "low", "close")):
            return None
        for row in reader:
            try:
                values = [float(row[keys[k]]) for k in ("open", "high", "low", "close")]
                volume = float(row[keys["volume"]]) if keys["volume"] else 0.0
            except (TypeError, ValueError, KeyError):
                continue
            dates.append(str(row[date_key]).strip())
            for col, value in zip(cols, values + [volume]):
                col.append(value)
    if not dates:
        return None
    return Bars(symbol, dates, *[np.asarray(c, dtype=float) for c in cols])


def write_cache(bars: Bars, timeframe: str) -> str:
    path = cache_path(bars.symbol, timeframe)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp.npz"
    np.savez(tmp, dates=np.asarray(bars.dates), open=bars.open, high=bars.high,
             low=bars.low, close=bars.close, volume=bars.volume)
    os.replace(tmp, path)
    return path


def export_csv(symbol: str, timeframe: str, path: str = "") -> str:
    """Write a series out as CSV, for anything that does not read .npz."""
    bars = read_cache(symbol, timeframe)
    if bars is None:
        raise DataError(f"nothing stored for {symbol} at {timeframe}")
    target = path or csv_path(symbol, timeframe)
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        for i, stamp in enumerate(bars.dates):
            writer.writerow([stamp, bars.open[i], bars.high[i], bars.low[i],
                             bars.close[i], bars.volume[i]])
    return target


def import_csv(path: str, symbol: str, timeframe: str, *,
               merge: bool = True) -> Bars:
    """Load bars from anywhere into the store.

    Columns are matched by header name, so a CSV from another tool works as
    long as it has a date/time column and OHLC; volume may be missing.
    """
    bars = _read_path(path, symbol.upper())
    if bars is None:
        raise DataError(f"no usable rows in {path}")
    merged = merge_series(read_cache(symbol, timeframe), bars) if merge else bars
    merged = Bars(symbol.upper(), merged.dates, merged.open, merged.high,
                  merged.low, merged.close, merged.volume)
    write_cache(merged, timeframe)
    return merged


def merge_series(old: Optional[Bars], new: Optional[Bars]) -> Bars:
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
        merged = merge_series(stored, fetched)
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
        if "__" not in name or not name.endswith((".npz", ".csv")):
            continue
        label, timeframe = name[:-4].rsplit("__", 1)
        path = os.path.join(CACHE_DIR, name)
        # Read the file itself: the name is sanitised, so it cannot be turned
        # back into a symbol reliably.
        stored = _read_npz(path, label) if name.endswith(".npz") \
            else _read_path(path, label)
        if stored is None:
            continue
        out.append({"symbol": label, "timeframe": timeframe,
                    "bars": len(stored), "start": stored.dates[0],
                    "end": stored.dates[-1], "path": path})
    return out
