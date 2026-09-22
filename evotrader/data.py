"""Market data: fetching, on-disk caching, and train/validation windowing.

Daily OHLCV bars are pulled from Yahoo Finance's public chart endpoint (no key
required) and cached as CSV under ``data/cache``.  Continuous futures such as
``NQ1!`` come from TradingView instead, back-adjusted across rolls (see
``ratio_adjust``).  A deterministic synthetic generator is available so the
whole system can be exercised offline.
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
from datetime import datetime, time as dtime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

CACHE_DIR = os.environ.get("EVOTRADER_CACHE", os.path.join("data", "cache"))
_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
_UA = "Mozilla/5.0 (compatible; evotrader/0.1)"


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
    warnings: List[str] = field(default_factory=list)   # symbols that were dropped

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


def _cache_path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol.upper().replace('/', '_')}.csv")


def _write_cache(bars: Bars) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(bars.symbol)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for i, d in enumerate(bars.dates):
            w.writerow([d, bars.open[i], bars.high[i], bars.low[i],
                        bars.close[i], bars.volume[i]])
    os.replace(tmp, path)


def _meta_path(symbol: str) -> str:
    return _cache_path(symbol)[:-4] + ".meta.json"


def _read_meta(symbol: str) -> Dict[str, str]:
    path = _meta_path(symbol)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as fh:
            meta = json.load(fh)
        return meta if isinstance(meta, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_meta(symbol: str, **fields: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_meta_path(symbol), "w") as fh:
        json.dump({**_read_meta(symbol), **fields}, fh)


def _read_cache(symbol: str) -> Bars | None:
    path = _cache_path(symbol)
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
                retries: int = 3) -> Bars:
    """Download daily bars from Yahoo Finance's chart endpoint."""
    p1 = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86400
    url = (f"{_YAHOO.format(symbol=urllib.parse.quote(symbol))}"
           f"?period1={p1}&period2={p2}&interval=1d&events=div%2Csplit")
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
        dates.append(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
        o.append(float(row[0]) * ratio)
        h.append(float(row[1]) * ratio)
        l.append(float(row[2]) * ratio)
        c.append(close * ratio)
        v.append(float(row[4] or 0.0))
    if not dates:
        raise DataError(f"{symbol}: no usable bars in {start}..{end}")
    return Bars(symbol.upper(), dates, *[np.asarray(x, dtype=float) for x in (o, h, l, c, v)])


#: Exchange for each futures root a config may name as ``ROOT1!``; the loader
#: asks TradingView for ``EXCHANGE:ROOT1!``.  An exchange-qualified symbol
#: (``CME_MINI:NQ1!``) works too, it is just an awkward file name.
FUTURES_EXCHANGES: Dict[str, str] = {
    "NQ": "CME_MINI", "MNQ": "CME_MINI", "ES": "CME_MINI", "MES": "CME_MINI",
    "RTY": "CME_MINI", "M2K": "CME_MINI", "YM": "CBOT_MINI", "MYM": "CBOT_MINI",
    "CL": "NYMEX", "MCL": "NYMEX", "GC": "COMEX", "MGC": "COMEX",
}

#: CME equity-index futures settle their session at 17:00 New York; a daily bar
#: is complete only after that.
FUTURES_SESSION_END = dtime(17, 0)


def is_continuous_future(symbol: str) -> bool:
    """``NQ1!``, ``ES2!``, ``CME_MINI:NQ1!``: TradingView's continuous contracts."""
    s = symbol.upper()
    return len(s) > 2 and s.endswith("!") and s[-2].isdigit()


def tradingview_future(symbol: str) -> str:
    s = symbol.upper()
    if ":" in s:
        return s
    root = s[:-2]
    exchange = FUTURES_EXCHANGES.get(root)
    if exchange is None:
        raise DataError(f"{symbol}: unknown futures root {root!r}; name it with its "
                        f"exchange, for example CME_MINI:NQ1!")
    return f"{exchange}:{s}"


def ratio_adjust(plain: Bars, additive: Bars) -> Bars:
    """Continuous futures with the roll gaps removed as ratios, not points.

    TradingView back-adjusts by adding each roll's gap to every earlier price,
    so NQ in 2010 reads 5,600 instead of 1,900 and every early percentage move
    shrinks threefold.  Here each segment is scaled by the ratio the roll
    implies instead: the return across a roll is the new contract's own return,
    which is what a position that rolled actually earned, and returns inside a
    segment are untouched.  The quarterly gap (about 1% for NQ at 4-5% rates)
    is carry, not profit, and an unadjusted series books it as a phantom gain.
    """
    if list(plain.dates) != list(additive.dates):
        raise DataError(f"{plain.symbol}: plain and back-adjusted series disagree on dates")
    n = len(plain)
    diff = np.asarray(additive.close, dtype=float) - np.asarray(plain.close, dtype=float)
    factor = np.ones(n)
    running = 1.0
    for i in range(n - 1, 0, -1):
        gap = diff[i - 1] - diff[i]              # points added to bars before the roll
        base = float(plain.close[i - 1])
        if abs(gap) > 1e-6 and base > 0:
            running *= (base + gap) / base
        factor[i - 1] = running
    return Bars(plain.symbol, list(plain.dates), plain.open * factor, plain.high * factor,
                plain.low * factor, plain.close * factor,
                np.asarray(plain.volume, dtype=float).copy())


def _session_complete(date: str, now: datetime | None = None) -> bool:
    """Has the futures session labelled ``date`` settled yet?"""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/New_York")
    except Exception:  # pragma: no cover - no tz database: assume UTC-4
        from datetime import timedelta
        tz = timezone(timedelta(hours=-4))
    end = datetime.combine(datetime.strptime(date, "%Y-%m-%d").date(),
                           FUTURES_SESSION_END, tzinfo=tz)
    return (now or datetime.now(timezone.utc)) >= end


def fetch_tradingview_future(symbol: str, *, bars: int = 10_000,
                             timeout: float = 120.0, fetch=None) -> Bars:
    """Daily bars for a continuous future, ratio back-adjusted, by trading date."""
    from . import tvdata            # tvdata imports this module; import lazily
    fetch = fetch or tvdata.fetch_bars
    tv_symbol = tradingview_future(symbol)
    kwargs = dict(timeout=timeout, trading_dates=True, drop_forming=False)
    plain = fetch(tv_symbol, "1D", bars, **kwargs)
    additive = fetch(tv_symbol, "1D", bars, backadjust=True, **kwargs)
    shared = sorted(set(plain.dates) & set(additive.dates))
    if len(shared) < 50:
        raise DataError(f"{symbol}: TradingView returned too little history")
    plain, additive = _take_dates(plain, shared), _take_dates(additive, shared)
    out = ratio_adjust(plain, additive)
    if out.dates and not _session_complete(out.dates[-1]):
        out = out.index_slice(0, len(out) - 1)   # still trading: not a bar yet
    out.symbol = symbol.upper()
    return out


def _take_dates(bars: Bars, dates: Sequence[str]) -> Bars:
    pos = {d: i for i, d in enumerate(bars.dates)}
    take = np.asarray([pos[d] for d in dates], dtype=int)
    return Bars(bars.symbol, list(dates), bars.open[take], bars.high[take],
                bars.low[take], bars.close[take], bars.volume[take])


def synthetic_bars(symbol: str, n: int = 1500, *, seed: int | None = None,
                   drift: float = 0.0003, vol: float = 0.012,
                   start_price: float = 100.0) -> Bars:
    """Deterministic geometric-random-walk bars, for tests and offline runs."""
    # zlib.crc32, not hash(): str hashing is salted per process, which would
    # make "deterministic" offline data differ between runs.
    stable = zlib.crc32(symbol.upper().encode()) if seed is None else seed
    rng = np.random.default_rng(stable % (2 ** 32))
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
    day = np.datetime64("2015-01-01")
    dates = [str(day + np.timedelta64(int(i * 1.4), "D")) for i in range(n)]
    return Bars(symbol.upper(), dates, open_, high, low, close, volume)


def load_symbol(symbol: str, start: str, end: str, *, offline: bool = False,
                refresh: bool = False) -> Bars:
    """Cache-first symbol load; falls back to synthetic data when offline.

    The cache remembers the earliest date it was ever asked for.  A request
    that reaches further back than the cache was built for refetches from the
    earlier date instead of silently returning the truncated window, and a
    refresh re-downloads from the earliest date ever requested, so a refresh
    driven by a short-history config can never shrink the cache.
    """
    cached = _read_cache(symbol)
    known_from = _read_meta(symbol).get("fetched_start")
    covers = cached is not None and (
        (known_from is not None and known_from <= start) or cached.dates[0] <= start)
    if cached is not None and not refresh and (covers or offline):
        window = cached.slice(start, end)
        if len(window) > 50:
            return window
    if offline:
        return synthetic_bars(symbol).slice(start, end)
    fetch_from = min([start] + ([known_from] if known_from else [])
                     + ([cached.dates[0]] if cached is not None else []))
    if is_continuous_future(symbol):
        # The whole available history comes back either way; remember the
        # earliest date asked for so a later, earlier request is not a refetch.
        bars = fetch_tradingview_future(symbol)
        _write_cache(bars)
        _write_meta(symbol, fetched_start=min(fetch_from, bars.dates[0]),
                    fetched_end=bars.dates[-1], source="tradingview",
                    contract=tradingview_future(symbol),
                    adjustment="ratio back-adjusted at each roll")
        return bars.slice(start, end)
    bars = fetch_yahoo(symbol, fetch_from, end)
    _write_cache(bars)
    _write_meta(symbol, fetched_start=fetch_from, fetched_end=end)
    return bars.slice(start, end)


def load_universe(symbols: Sequence[str], start: str, end: str, *,
                  offline: bool = False, refresh: bool = False,
                  min_bars: int = 250) -> Universe:
    """Load several symbols and align them on the intersection of their dates."""
    loaded: Dict[str, Bars] = {}
    errors: List[str] = []
    for sym in symbols:
        try:
            bars = load_symbol(sym, start, end, offline=offline, refresh=refresh)
        except DataError as exc:
            errors.append(str(exc))
            continue
        if len(bars) >= min_bars:
            loaded[bars.symbol] = bars
        else:
            errors.append(f"{sym}: only {len(bars)} bars (need {min_bars})")
    if not loaded:
        raise DataError("no symbols loaded. " + "; ".join(errors))
    return align(loaded)


def align(loaded: Dict[str, Bars]) -> Universe:
    """Put several symbols on the intersection of their dates.

    Trading on a bar one symbol does not have is a quiet way to invent
    information, so the shared calendar is the only calendar.
    """
    if not loaded:
        raise DataError("nothing to align")
    common = set.intersection(*(set(b.dates) for b in loaded.values()))
    if not common:
        raise DataError("symbols share no common bars: "
                        + ", ".join(sorted(loaded)))
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


def date_cut(universe: Universe, test_start: str) -> int:
    """Index of the first bar on or after ``test_start`` (len when none is)."""
    for i, d in enumerate(universe.calendar):
        if d >= test_start:
            return i
    return len(universe)


def holdout_split(universe: Universe, test_frac: float = 0.2) -> Tuple[Universe, Universe]:
    """Single chronological train/test cut."""
    n = len(universe)
    cut = max(1, int(n * (1 - test_frac)))
    return universe.slice(0, cut), universe.slice(cut, n)
