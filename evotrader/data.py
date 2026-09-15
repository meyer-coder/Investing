"""Market data: fetching, on-disk caching, and train/validation windowing.

Daily OHLCV bars are pulled from Yahoo Finance's public chart endpoint (no key
required) and cached as CSV under ``data/cache``.  A deterministic synthetic
generator is available so the whole system can be exercised offline.
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

CACHE_DIR = os.environ.get("EVOTRADER_CACHE", os.path.join("data", "cache"))
_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_UA = "Mozilla/5.0 (compatible; evotrader/0.1)"

#: Bars per year for each supported interval, used to annualise Sharpe, CAGR
#: and turnover.  A US regular session is 6.5 hours, so an hourly series has
#: 6.5 bars per trading day.
BARS_PER_YEAR: Dict[str, float] = {
    "1d": 252.0,
    "1h": 252.0 * 6.5,
    "30m": 252.0 * 13.0,
    "15m": 252.0 * 26.0,
    "5m": 252.0 * 78.0,
}

#: How far back Yahoo serves each interval.  Intraday history is capped, and
#: asking for more silently returns an empty series, so requests are clamped.
_MAX_LOOKBACK_DAYS: Dict[str, Optional[int]] = {
    "1d": None, "1h": 730, "30m": 60, "15m": 60, "5m": 60,
}

INTERVALS = tuple(BARS_PER_YEAR)


def bars_per_year(interval: str = "1d") -> float:
    """Annualisation factor for an interval; unknown intervals fall back to daily."""
    return BARS_PER_YEAR.get(interval, 252.0)


def _check_interval(interval: str) -> str:
    if interval not in BARS_PER_YEAR:
        raise DataError(
            f"unsupported interval {interval!r}; choose from {', '.join(INTERVALS)}")
    return interval


class DataError(RuntimeError):
    pass


@dataclass
class Bars:
    """OHLCV series for a single symbol, ascending by date."""

    symbol: str
    dates: List[str]
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    def __len__(self) -> int:
        return len(self.dates)

    def slice(self, start: str | None = None, end: str | None = None) -> "Bars":
        lo = 0
        hi = len(self.dates)
        if start:
            while lo < hi and self.dates[lo] < start:
                lo += 1
        if end:
            while hi > lo and self.dates[hi - 1] > end:
                hi -= 1
        return Bars(
            self.symbol, self.dates[lo:hi], self.open[lo:hi], self.high[lo:hi],
            self.low[lo:hi], self.close[lo:hi], self.volume[lo:hi],
        )

    def index_slice(self, lo: int, hi: int) -> "Bars":
        return Bars(
            self.symbol, self.dates[lo:hi], self.open[lo:hi], self.high[lo:hi],
            self.low[lo:hi], self.close[lo:hi], self.volume[lo:hi],
        )


@dataclass
class Universe:
    """A set of symbols aligned onto a single shared calendar."""

    bars: Dict[str, Bars]
    calendar: List[str] = field(default_factory=list)

    @property
    def symbols(self) -> List[str]:
        return sorted(self.bars)

    def __len__(self) -> int:
        return len(self.calendar)

    def slice(self, lo: int, hi: int) -> "Universe":
        return Universe({s: b.index_slice(lo, hi) for s, b in self.bars.items()},
                        self.calendar[lo:hi])

    def date_range(self) -> Tuple[str, str]:
        if not self.calendar:
            return ("", "")
        return (self.calendar[0], self.calendar[-1])


def _coverage_path() -> str:
    return os.path.join(CACHE_DIR, "_coverage.json")


def _coverage_key(symbol: str, interval: str) -> str:
    return f"{symbol.upper()}@{interval}"


def _read_coverage() -> Dict[str, List[str]]:
    """What date range each cached series was actually fetched for.

    Without this the cache cannot tell "we have no bars before 2018 because
    none were requested" from "...because none exist", and a backtest asking
    for a longer window silently gets the shorter cached one.
    """
    try:
        with open(_coverage_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _record_coverage(symbol: str, interval: str, start: str, end: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    coverage = _read_coverage()
    key = _coverage_key(symbol, interval)
    have = coverage.get(key)
    if have:
        start, end = min(start, have[0]), max(end, have[1])
    coverage[key] = [start, end]
    tmp = _coverage_path() + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(coverage, fh, indent=0, sort_keys=True)
        os.replace(tmp, _coverage_path())
    except OSError:
        pass


def _covers(symbol: str, interval: str, start: str, end: str) -> Optional[Tuple[str, str]]:
    """Return the recorded range when it spans the request, else None."""
    have = _read_coverage().get(_coverage_key(symbol, interval))
    if have and have[0] <= start and have[1] >= end:
        return have[0], have[1]
    return None


def _cache_path(symbol: str, interval: str = "1d") -> str:
    stem = symbol.upper().replace("/", "_")
    suffix = "" if interval == "1d" else f"@{interval}"
    return os.path.join(CACHE_DIR, f"{stem}{suffix}.csv")


def _write_cache(bars: Bars, interval: str = "1d") -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(bars.symbol, interval)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for i, d in enumerate(bars.dates):
            w.writerow([d, bars.open[i], bars.high[i], bars.low[i],
                        bars.close[i], bars.volume[i]])
    os.replace(tmp, path)


def _read_cache(symbol: str, interval: str = "1d") -> Bars | None:
    path = _cache_path(symbol, interval)
    if not os.path.exists(path):
        return None
    dates: List[str] = []
    cols: List[List[float]] = [[], [], [], [], []]
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                vals = [float(row[k]) for k in ("open", "high", "low", "close", "volume")]
            except (TypeError, ValueError):
                continue
            dates.append(row["date"])
            for c, v in zip(cols, vals):
                c.append(v)
    if not dates:
        return None
    return Bars(symbol.upper(), dates, *[np.asarray(c, dtype=float) for c in cols])


def fetch_yahoo(symbol: str, start: str, end: str, *, timeout: int = 30,
                retries: int = 3, interval: str = "1d") -> Bars:
    """Download bars from Yahoo Finance's chart endpoint.

    Intraday intervals are served only for a trailing window (730 days for
    hourly, 60 for finer), so ``start`` is clamped rather than allowed to
    return an empty series.
    """
    _check_interval(interval)
    p1 = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86400
    limit = _MAX_LOOKBACK_DAYS.get(interval)
    if limit is not None:
        earliest = int(time.time()) - limit * 86400
        p1 = max(p1, earliest)
        if p2 <= p1:
            raise DataError(
                f"{symbol}: {interval} bars are only served for the last {limit} days, "
                f"which does not overlap {start}..{end}")
    url = (f"{_YAHOO.format(symbol=urllib.parse.quote(symbol))}"
           f"?period1={p1}&period2={p2}&interval={interval}&events=div%2Csplit")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2 ** attempt)
    else:
        raise DataError(f"could not fetch {symbol}: {last}")

    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise DataError(f"{symbol}: {chart['error']}")
    result = (chart.get("result") or [None])[0]
    if not result:
        raise DataError(f"{symbol}: empty response")
    stamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")

    stamp_fmt = "%Y-%m-%d" if interval == "1d" else "%Y-%m-%d %H:%M"
    dates, o, h, l, c, v = [], [], [], [], [], []
    for i, ts in enumerate(stamps):
        row = [quote.get(k, [None] * len(stamps))[i] for k in ("open", "high", "low", "close", "volume")]
        if any(x is None for x in row[:4]):
            continue
        close = float(row[3])
        # Scale OHLC by the adjusted-close ratio so splits/dividends do not show
        # up as phantom gaps a strategy could "trade".
        ratio = 1.0
        if adj and adj[i] is not None and close:
            ratio = float(adj[i]) / close
        dates.append(datetime.fromtimestamp(ts, tz=timezone.utc).strftime(stamp_fmt))
        o.append(float(row[0]) * ratio)
        h.append(float(row[1]) * ratio)
        l.append(float(row[2]) * ratio)
        c.append(close * ratio)
        v.append(float(row[4] or 0.0))
    if not dates:
        raise DataError(f"{symbol}: no usable {interval} bars in {start}..{end}")
    return Bars(symbol.upper(), dates, *[np.asarray(x, dtype=float) for x in (o, h, l, c, v)])


def synthetic_bars(symbol: str, n: int = 1500, *, seed: int | None = None,
                   drift: float = 0.0003, vol: float = 0.012,
                   start_price: float = 100.0, interval: str = "1d") -> Bars:
    """Deterministic geometric-random-walk bars, for tests and offline runs.

    ``interval`` only shapes the timestamps — offline bars are synthetic at
    any resolution — so an offline intraday run produces a coherent calendar.
    """
    # crc32, not hash(): Python salts string hashes per process, so hash()
    # made "deterministic" offline data differ on every run.
    if seed is None:
        seed = zlib.crc32(symbol.upper().encode())
    rng = np.random.default_rng(seed % (2 ** 32))
    shocks = rng.normal(drift, vol, n)
    # A slow regime cycle keeps synthetic data from being trivially trending.
    cycle = 0.0006 * np.sin(np.linspace(0, 6 * np.pi, n))
    close = start_price * np.cumprod(1.0 + shocks + cycle)
    intraday = np.abs(rng.normal(0, vol / 2, n))
    high = close * (1 + intraday)
    low = close * (1 - intraday)
    open_ = np.concatenate(([start_price], close[:-1])) * (1 + rng.normal(0, vol / 4, n))
    high = np.maximum.reduce([high, close, open_])
    low = np.minimum.reduce([low, close, open_])
    volume = rng.lognormal(15, 0.3, n)
    if interval == "1d":
        day = np.datetime64("2015-01-01")
        dates = [str(day + np.timedelta64(int(i * 1.4), "D")) for i in range(n)]
    else:
        minutes = {"1h": 60, "30m": 30, "15m": 15, "5m": 5}.get(interval, 60)
        origin = np.datetime64("2015-01-01T14:30")
        dates = [str(origin + np.timedelta64(i * minutes, "m")).replace("T", " ")
                 for i in range(n)]
    return Bars(symbol.upper(), dates, open_, high, low, close, volume)


def load_symbol(symbol: str, start: str, end: str, *, offline: bool = False,
                refresh: bool = False, interval: str = "1d") -> Bars:
    """Cache-first symbol load; falls back to synthetic data when offline.

    The cache is only trusted when it was fetched over a range covering the
    request.  Otherwise the window is re-fetched over the union of the two
    ranges, so coverage grows instead of oscillating between windows.
    """
    _check_interval(interval)
    want_start, want_end = start, end
    if not refresh:
        cached = _read_cache(symbol, interval)
        if cached is not None:
            recorded = _covers(symbol, interval, start, end)
            # Legacy caches predate coverage records; trust them only when the
            # bars themselves reach back at least as far as the request.
            if recorded is None and _read_coverage().get(
                    _coverage_key(symbol, interval)) is None:
                recorded = (cached.dates[0], cached.dates[-1]) \
                    if cached.dates and cached.dates[0] <= start else None
            if recorded is not None:
                window = cached.slice(start, end)
                if len(window) > 50:
                    return window
            have = _read_coverage().get(_coverage_key(symbol, interval))
            if have:
                want_start = min(want_start, have[0])
                want_end = max(want_end, have[1])
    if offline:
        return synthetic_bars(symbol, interval=interval).slice(start, end)
    bars = fetch_yahoo(symbol, want_start, want_end, interval=interval)
    _write_cache(bars, interval)
    _record_coverage(symbol, interval, want_start, want_end)
    return bars.slice(start, end)


def load_universe(symbols: Sequence[str], start: str, end: str, *,
                  offline: bool = False, refresh: bool = False,
                  min_bars: int = 250, interval: str = "1d") -> Universe:
    """Load several symbols and align them on the intersection of their dates."""
    _check_interval(interval)
    loaded: Dict[str, Bars] = {}
    errors: List[str] = []
    for sym in symbols:
        try:
            bars = load_symbol(sym, start, end, offline=offline, refresh=refresh,
                               interval=interval)
        except DataError as exc:
            errors.append(str(exc))
            continue
        if len(bars) >= min_bars:
            loaded[bars.symbol] = bars
        else:
            errors.append(f"{sym}: only {len(bars)} bars (need {min_bars})")
    if not loaded:
        raise DataError("no symbols loaded. " + "; ".join(errors))
    common = set.intersection(*(set(b.dates) for b in loaded.values()))
    calendar = sorted(common)
    aligned: Dict[str, Bars] = {}
    for sym, bars in loaded.items():
        idx = [i for i, d in enumerate(bars.dates) if d in common]
        take = np.asarray(idx, dtype=int)
        aligned[sym] = Bars(sym, [bars.dates[i] for i in idx], bars.open[take],
                            bars.high[take], bars.low[take], bars.close[take],
                            bars.volume[take])
    return Universe(aligned, calendar)


@dataclass
class Split:
    """One walk-forward fold: an in-sample window plus its out-of-sample tail."""

    name: str
    train: Universe
    test: Universe


def walk_forward_splits(universe: Universe, folds: int = 3,
                        test_frac: float = 0.25) -> List[Split]:
    """Anchored walk-forward folds; each fold trains on all history before its
    test window, so no fold ever sees its own future."""
    n = len(universe)
    if n < 300 or folds < 1:
        cut = max(1, int(n * (1 - test_frac)))
        return [Split("full", universe.slice(0, cut), universe.slice(cut, n))]
    test_len = max(60, int(n * test_frac / folds))
    splits: List[Split] = []
    for k in range(folds):
        test_end = n - (folds - 1 - k) * test_len
        test_start = test_end - test_len
        if test_start < 250:
            continue
        splits.append(Split(f"fold{k + 1}", universe.slice(0, test_start),
                            universe.slice(test_start, test_end)))
    return splits or [Split("full", universe.slice(0, int(n * 0.75)),
                            universe.slice(int(n * 0.75), n))]


def holdout_split(universe: Universe, test_frac: float = 0.2) -> Tuple[Universe, Universe]:
    """Single chronological train/test cut."""
    n = len(universe)
    cut = max(1, int(n * (1 - test_frac)))
    return universe.slice(0, cut), universe.slice(cut, n)
