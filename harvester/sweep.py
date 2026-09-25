"""Sweep the feed: every symbol, every timeframe, as deep as it will go.

This is the difference between a request and a harvest.  ``fetch`` answers a
question you asked; a sweep walks a whole universe without being asked again,
takes the maximum depth the feed will serve for each series, merges it into
the store, and keeps going when one symbol fails.

Depth comes from two directions and it is worth being clear about which:
one pull exhausts everything TradingView will serve *backwards* for a series,
and that limit is fixed.  Running the sweep again tomorrow adds what has
happened since.  So a ten-year 1-minute store is built by sweeping on a
schedule for a long time, not by one clever request.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .data import Bars, DataError
from .tvcache import CACHE_DIR, cached_bars, read_cache
from .tvdata import MAX_BARS, interval_seconds, normalise_timeframe

# Coarse to fine.  A sweep does the cheap, deep timeframes first so that an
# interrupted run still leaves every symbol with usable daily history.
LADDER: Tuple[str, ...] = ("1W", "1D", "240", "60", "30", "15", "5", "1")

LEDGER_NAME = "sweep.json"


@dataclass
class Result:
    """What one (symbol, timeframe) pull did."""

    symbol: str
    timeframe: str
    bars: int = 0
    added: int = 0
    start: str = ""
    end: str = ""
    seconds: float = 0.0
    error: str = ""
    skipped: bool = False

    @property
    def ok(self) -> bool:
        return not self.error


@dataclass
class Plan:
    """The jobs a sweep will run, and the ones it is skipping as fresh."""

    jobs: List[Tuple[str, str]] = field(default_factory=list)
    fresh: List[Tuple[str, str]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.jobs)


def ledger_path(directory: str = "") -> str:
    return os.path.join(directory or CACHE_DIR, LEDGER_NAME)


def load_ledger(directory: str = "") -> Dict[str, Dict[str, object]]:
    """What previous sweeps recorded, keyed ``SYMBOL|timeframe``.

    A corrupt or half-written ledger costs a re-pull, never the run: the store
    itself is the record, and this only decides what to skip.
    """
    path = ledger_path(directory)
    try:
        with open(path) as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    series = loaded.get("series") if isinstance(loaded, dict) else None
    return series if isinstance(series, dict) else {}


def save_ledger(series: Dict[str, Dict[str, object]], directory: str = "") -> str:
    path = ledger_path(directory)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"updated": time.time(), "series": series}, fh, indent=1,
                  sort_keys=True)
    os.replace(tmp, path)
    return path


def key(symbol: str, timeframe: str) -> str:
    return f"{symbol.upper()}|{normalise_timeframe(timeframe)}"


def stale_after(timeframe: str, floor: float = 3600.0) -> float:
    """How old a series may get before a sweep pulls it again.

    One bar's worth of time, floored: re-pulling a 1-minute series every
    minute would spend the whole sweep on one symbol, and a daily series has
    nothing new to give until tomorrow.
    """
    return max(float(interval_seconds(timeframe)), floor)


def plan(symbols: Sequence[str], timeframes: Sequence[str],
         ledger: Optional[Dict[str, Dict[str, object]]] = None, *,
         redo: bool = False, retry_failed: bool = True,
         floor: float = 3600.0, now: Optional[float] = None) -> Plan:
    """Which pulls this sweep needs to make.

    Symbol-major, so an interrupted run leaves whole symbols finished rather
    than every symbol half-done.
    """
    ledger = ledger or {}
    stamp = time.time() if now is None else now
    out = Plan()
    for symbol in symbols:
        for timeframe in timeframes:
            tf = normalise_timeframe(timeframe)
            job = (symbol.upper(), tf)
            record = ledger.get(key(symbol, tf)) or {}
            if redo or not record:
                out.jobs.append(job)
                continue
            if record.get("error") and retry_failed:
                out.jobs.append(job)
                continue
            age = stamp - float(record.get("at") or 0.0)
            if age >= stale_after(tf, floor):
                out.jobs.append(job)
            else:
                out.fresh.append(job)
    return out


def pull(symbol: str, timeframe: str, *, bars: int = MAX_BARS,
         timeout: float = 300.0, fetch=None) -> Result:
    """One series, as deep as the feed goes, merged into the store.

    Never raises: a sweep that dies on the first delisted ticker is not a
    sweep.  The failure is recorded on the result and the caller moves on.
    """
    started = time.monotonic()
    before = read_cache(symbol, timeframe)
    held = len(before) if before is not None else 0
    try:
        kwargs = {"force": True, "timeout": timeout}
        if fetch is not None:
            kwargs["fetch"] = fetch
        series = cached_bars(symbol, timeframe, bars, **kwargs)
    except (DataError, OSError, ValueError) as exc:
        return Result(symbol, timeframe, bars=held, seconds=time.monotonic() - started,
                      error=str(exc)[:200])
    return Result(symbol, timeframe, bars=len(series), added=len(series) - held,
                  start=series.dates[0] if len(series) else "",
                  end=series.dates[-1] if len(series) else "",
                  seconds=time.monotonic() - started)


def run(symbols: Sequence[str], timeframes: Sequence[str] = LADDER, *,
        bars: int = MAX_BARS, timeout: float = 300.0, pause: float = 0.4,
        redo: bool = False, floor: float = 3600.0, directory: str = "",
        progress: Optional[Callable[[Result, int, int], None]] = None,
        puller: Callable[..., Result] = pull) -> List[Result]:
    """Sweep a universe, writing the ledger as it goes.

    The ledger is saved after every pull, not at the end, because a sweep of a
    few hundred symbols runs for hours and the useful thing after a crash is
    knowing exactly where it stopped.
    """
    ledger = load_ledger(directory)
    todo = plan(symbols, timeframes, ledger, redo=redo, floor=floor)
    total = len(todo.jobs)
    results: List[Result] = []
    for index, (symbol, timeframe) in enumerate(todo.jobs, start=1):
        result = puller(symbol, timeframe, bars=bars, timeout=timeout)
        results.append(result)
        ledger[key(symbol, timeframe)] = {
            "at": time.time(), "bars": result.bars, "added": result.added,
            "start": result.start, "end": result.end,
            "seconds": round(result.seconds, 2), "error": result.error,
        }
        save_ledger(ledger, directory)
        if progress is not None:
            progress(result, index, total)
        if pause > 0 and index < total:
            time.sleep(pause)
    return results


def summarise(results: Sequence[Result]) -> Dict[str, object]:
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    return {
        "series": len(results),
        "ok": len(ok),
        "failed": len(failed),
        "bars": sum(r.bars for r in ok),
        "added": sum(r.added for r in ok),
        "seconds": round(sum(r.seconds for r in results), 1),
        "failures": [(r.symbol, r.timeframe, r.error) for r in failed],
    }


def describe(summary: Dict[str, object]) -> str:
    lines = [
        f"{summary['ok']}/{summary['series']} series pulled, "
        f"{int(summary['bars']):,} bars held, {int(summary['added']):+,} new, "
        f"in {_clock(float(summary['seconds']))}",
    ]
    failures = list(summary.get("failures") or [])
    if failures:
        lines.append(f"{len(failures)} failed:")
        for symbol, timeframe, error in failures[:15]:
            lines.append(f"  {symbol:<20} {timeframe:<4} {error[:70]}")
        if len(failures) > 15:
            lines.append(f"  ... and {len(failures) - 15} more")
    return "\n".join(lines)


def _clock(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"
