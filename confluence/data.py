"""1-minute price history: download, splice, cache, cross-check.

Sources, in the order they are used:

* **histdata.com** — free 1-minute bars back to 2000 for FX, metals, oil and the
  major index CFDs.  One zip per symbol per year (per month for the current
  year).  This is the 8-year backbone: ~2 s per file instead of the ~1 file/s
  Dukascopy's per-day feed manages.
* **Dukascopy** datafeed — per-day 1-minute candle files.  Used to extend each
  feed from histdata's last published bar up to today; the splice is levelled
  on the overlap so the join cannot show up as a gap.
* **Yahoo Finance** — real futures (NQ=F, ES=F, CL=F, GC=F ...) at 5 minutes
  for the last 60 days.  Used to measure how closely each CFD proxy tracks
  the contract you would actually trade.
* **massive.com** (formerly Polygon.io) — used when ``MASSIVE_API_KEY`` or
  ``POLYGON_API_KEY`` is set; ``fetch_massive`` pulls minute aggregates for
  the ticker in ``Market.massive``.
* **TradingView** — the MCP TradingView server serves roughly the last month
  of 5-minute futures bars (e.g. CME_MINI:MNQ1!).  It is too short for an
  8-year test and is used for the same proxy cross-check.

Timestamps are stored as int64 minutes since the Unix epoch, UTC.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import lzma
import os
import re
import struct
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

CACHE = os.environ.get("CONFLUENCE_CACHE", os.path.join("data", "cache"))
RAW = os.path.join(CACHE, "raw")
M1 = os.path.join(CACHE, "m1")
_UA = "Mozilla/5.0 (X11; Linux x86_64) confluence/0.1"


class DataError(RuntimeError):
    pass


@dataclass
class Minutes:
    """1-minute OHLC for one feed, ascending, UTC epoch minutes."""

    feed: str
    t: np.ndarray        # int64 minutes since epoch, UTC
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    sources: Dict[str, str]

    def __len__(self) -> int:
        return int(self.t.size)

    def span(self) -> Tuple[str, str]:
        f = lambda m: dt.datetime.fromtimestamp(int(m) * 60, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
        return (f(self.t[0]), f(self.t[-1])) if len(self) else ("", "")


# ------------------------------------------------------------------ helpers

def _log(msg: str) -> None:
    print(f"[data {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _http(url: str, *, data: Optional[bytes] = None, headers: Optional[dict] = None,
          timeout: int = 60, retries: int = 5) -> bytes:
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - network errors of every flavour
            last = exc
            if getattr(exc, "code", None) == 404:
                break
            time.sleep(min(2 ** attempt, 20))
    raise DataError(f"{url}: {last}")


# ------------------------------------------------------------------ histdata

_HD_PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{period}"


def histdata_zip(feed: str, year: int, month: Optional[int] = None, *, refresh: bool = False) -> Optional[bytes]:
    """One histdata zip (a year, or a month for the current year), cached raw."""
    os.makedirs(os.path.join(RAW, "histdata"), exist_ok=True)
    tag = f"{year}" if month is None else f"{year}{month:02d}"
    path = os.path.join(RAW, "histdata", f"{feed}_{tag}.zip")
    if os.path.exists(path) and not refresh:
        with open(path, "rb") as fh:
            return fh.read()
    period = f"{year}" if month is None else f"{year}/{month}"
    page_url = _HD_PAGE.format(pair=feed.lower(), period=period)
    page = _http(page_url, timeout=30).decode("utf-8", "replace")
    form = dict(re.findall(r'<input type="hidden" name="(\w+)" id="\w+" value="([^"]*)"', page))
    if "tk" not in form:
        return None
    body = urllib.parse.urlencode(form).encode()
    blob = _http("https://www.histdata.com/get.php", data=body,
                 headers={"Referer": page_url, "Content-Type": "application/x-www-form-urlencoded"})
    if blob[:2] != b"PK":
        return None
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(blob)
    os.replace(tmp, path)
    return blob


def parse_histdata(blob: bytes) -> Tuple[np.ndarray, ...]:
    """``YYYYMMDD HHMMSS;open;high;low;close;volume`` in EST -> UTC arrays."""
    import pandas as pd

    z = zipfile.ZipFile(io.BytesIO(blob))
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    df = pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None,
                     names=["ts", "o", "h", "l", "c", "v"], dtype={"ts": str})
    # histdata documents its stamps as fixed EST, but they are New York wall
    # clock time *with* daylight saving: aligning minute returns against
    # Dukascopy's UTC feed gives correlation 1.0 at UTC-4 in July and at UTC-5
    # in January, and ~0 at the other offset.  The hour repeated at the
    # November fall-back is ambiguous and dropped.
    stamp = pd.DatetimeIndex(pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S"))
    local = stamp.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
    ok = np.asarray(~local.isna())
    minutes = (local[ok].tz_convert("UTC").tz_localize(None)
               .to_numpy().astype("datetime64[m]").astype(np.int64))
    return (minutes, df["o"].to_numpy(float)[ok], df["h"].to_numpy(float)[ok],
            df["l"].to_numpy(float)[ok], df["c"].to_numpy(float)[ok])


# ------------------------------------------------------------------ Dukascopy

_DUKA = "https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"


_tls = threading.local()


def _duka_get(url: str, retries: int = 5) -> bytes:
    """GET over a per-thread keep-alive session.

    Through the egress proxy a fresh TLS connection costs ~15 s, a reused one
    ~0.2 s, so connection reuse is the difference between minutes and hours.
    """
    try:
        import requests
    except ImportError:          # pragma: no cover - requests ships almost everywhere
        return _http(url, timeout=45)
    last: Optional[Exception] = None
    for attempt in range(retries):
        sess = getattr(_tls, "session", None)
        if sess is None:
            sess = _tls.session = requests.Session()
            sess.headers["User-Agent"] = _UA
        try:
            r = sess.get(url, timeout=60)
            if r.status_code == 404:
                raise DataError(f"{url}: 404")
            r.raise_for_status()
            return r.content
        except DataError:
            raise
        except Exception as exc:  # noqa: BLE001
            last = exc
            _tls.session = None
            time.sleep(min(2 ** attempt, 20))
    raise DataError(f"{url}: {last}")


def dukascopy_day(sym: str, day: dt.date, scale: float) -> Tuple[np.ndarray, ...]:
    """One UTC day of Dukascopy 1-minute bid candles (empty arrays if closed)."""
    os.makedirs(os.path.join(RAW, "dukascopy"), exist_ok=True)
    path = os.path.join(RAW, "dukascopy", f"{sym}_{day.isoformat()}.bi5")
    if os.path.exists(path):
        with open(path, "rb") as fh:
            raw = fh.read()
    else:
        raw = _duka_get(_DUKA.format(sym=sym, y=day.year, m=day.month - 1, d=day.day))
        if day < dt.datetime.now(dt.timezone.utc).date():   # never cache a partial day
            with open(path, "wb") as fh:
                fh.write(raw)
    empty = tuple(np.empty(0) for _ in range(5))
    if not raw:
        return empty
    data = lzma.decompress(raw)
    n = len(data) // 24
    if n == 0:
        return empty
    rec = np.frombuffer(data[:n * 24], dtype=np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"),
                                                      ("l", ">i4"), ("h", ">i4"), ("v", ">f4")]))
    keep = rec["v"] > 0          # closed-market minutes are flat zero-volume candles
    rec = rec[keep]
    base = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp()) // 60
    t = base + rec["t"].astype(np.int64) // 60
    return (t, rec["o"] / scale, rec["h"] / scale, rec["l"] / scale, rec["c"] / scale)


# ------------------------------------------------------------------ Yahoo

def fetch_yahoo(symbol: str, interval: str = "5m", range_: str = "60d") -> Tuple[np.ndarray, np.ndarray]:
    """Real-instrument closes from Yahoo's chart endpoint: (utc minutes, close)."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?range={range_}&interval={interval}")
    payload = json.loads(_http(url, timeout=30))
    res = (payload.get("chart", {}).get("result") or [None])[0]
    if not res:
        raise DataError(f"yahoo {symbol}: empty")
    ts = np.asarray(res.get("timestamp") or [], dtype=np.int64)
    close = np.asarray([np.nan if x is None else x for x in res["indicators"]["quote"][0]["close"]], float)
    ok = ~np.isnan(close)
    return ts[ok] // 60, close[ok]


# ------------------------------------------------------------------ massive.com

def massive_key() -> Optional[str]:
    return os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")


def fetch_massive(ticker: str, start: str, end: str, *, multiplier: int = 1,
                  timespan: str = "minute") -> Tuple[np.ndarray, ...]:
    """Minute aggregates from massive.com (Polygon's API, renamed).

    Needs ``MASSIVE_API_KEY`` (or ``POLYGON_API_KEY``).  Follows ``next_url``
    pagination.  Returns (utc minutes, open, high, low, close).
    """
    key = massive_key()
    if not key:
        raise DataError("massive.com: set MASSIVE_API_KEY to use this source")
    url = (f"https://api.massive.com/v2/aggs/ticker/{urllib.parse.quote(ticker)}/range/"
           f"{multiplier}/{timespan}/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    cols: List[List[float]] = [[], [], [], [], []]
    while url:
        payload = json.loads(_http(url, timeout=60))
        for bar in payload.get("results") or []:
            for col, k in zip(cols, ("t", "o", "h", "l", "c")):
                col.append(bar[k])
        nxt = payload.get("next_url")
        url = f"{nxt}&apiKey={key}" if nxt else None
    t = np.asarray(cols[0], dtype=np.int64) // 60_000
    return (t, *[np.asarray(c, float) for c in cols[1:]])


# ------------------------------------------------------------------ building a feed

def _concat(parts: Iterable[Tuple[np.ndarray, ...]]) -> Tuple[np.ndarray, ...]:
    parts = [p for p in parts if p[0].size]
    if not parts:
        raise DataError("no bars")
    cols = [np.concatenate([p[i] for p in parts]) for i in range(5)]
    order = np.argsort(cols[0], kind="stable")
    cols = [c[order] for c in cols]
    keep = np.concatenate(([True], np.diff(cols[0]) > 0))   # drop duplicate minutes
    return tuple(c[keep] for c in cols)


def build_feed(feed: str, duka: str, duka_scale: float, start: dt.date, end: dt.date,
               *, refresh: bool = False, duka_threads: int = 3,
               patch_from: Optional[dt.date] = None) -> Minutes:
    """Splice histdata history with Dukascopy and cache the result.

    Dukascopy fills (a) days histdata is missing or thin on, from
    ``patch_from`` onward (default: everything), and (b) the tail from
    histdata's last bar up to ``end``.  Dukascopy throttles hard, so keep
    ``duka_threads`` low; downloaded days are cached, so an interrupted
    fetch resumes where it stopped.
    """
    parts: List[Tuple[np.ndarray, ...]] = []
    sources: Dict[str, str] = {}
    this_year = end.year
    for year in range(start.year, this_year + 1):
        if year < this_year:
            blob = histdata_zip(feed, year, refresh=refresh)
            if blob is None:
                _log(f"{feed} {year}: histdata has no yearly file, trying months")
                months = range(1, 13)
            else:
                parts.append(parse_histdata(blob))
                continue
        else:
            months = range(1, end.month + 1)
        for month in months:
            try:
                blob = histdata_zip(feed, year, month, refresh=refresh or (year == this_year and month == end.month))
            except DataError as exc:
                _log(f"{feed} {year}-{month:02d}: {exc}")
                blob = None
            if blob is not None:
                parts.append(parse_histdata(blob))
    t, o, h, l, c = _concat(parts)
    hd_last = int(t[-1])
    sources["histdata"] = f"{_fmt(t[0])} .. {_fmt(hd_last)}"
    _log(f"{feed}: histdata {len(t):,} bars {sources['histdata']}")

    # Level check: histdata occasionally files the wrong instrument under a symbol
    # (its GRXEUR "DAX" for mid-2020..2023 is the Euro Stoxx 50 at ~3,500 while the
    # DAX traded ~13,000).  Compare each month with Dukascopy on a sample day and
    # drop months that disagree by more than 1%; the thin-day patch below then
    # refills them from Dukascopy.
    bad = mismatched_months(t, c, duka, duka_scale, threads=duka_threads)
    if bad:
        keep = ~np.isin(_month_key(t), np.asarray(bad))
        _log(f"{feed}: {len(bad)} histdata months disagree with Dukascopy by >1% "
             f"({', '.join(_fmt_month(b) for b in bad[:6])}{' ...' if len(bad) > 6 else ''}); replacing them")
        t, o, h, l, c = t[keep], o[keep], h[keep], l[keep], c[keep]
        sources["histdata_rejected_months"] = [_fmt_month(b) for b in bad]

    # Day-level guard for the edges of a mislabelled stretch (e.g. 2023-12-01 in GRXEUR).
    jumps = level_outlier_days(t, c)
    if jumps.size:
        keep = ~np.isin(t // 1440, jumps)
        _log(f"{feed}: {jumps.size} day(s) with a >25% level jump vs the surrounding days; replacing them")
        t, o, h, l, c = t[keep], o[keep], h[keep], l[keep], c[keep]
        sources["histdata_rejected_days"] = [str(np.datetime64(int(d), "D")) for d in jumps]

    # Fill thin or missing days from Dukascopy (same underlying prices; histdata wins ties).
    thin = [d for d in thin_days(t, start) if patch_from is None or d >= patch_from]
    if thin:
        _log(f"{feed}: {len(thin)} thin/missing days in histdata, patching from Dukascopy")
        got = _duka_many(duka, thin, duka_scale, threads=duka_threads)
        patch = [g for g in got if g is not None and g[0].size]
        if patch:
            before = t.size
            t, o, h, l, c = _concat([(t, o, h, l, c)] + patch)
            sources["dukascopy_patch"] = (f"{len(thin)} thin days since {thin[0]}, "
                                          f"+{t.size - before:,} minutes")
            _log(f"{feed}: patched +{t.size - before:,} minutes")

    # Extend with Dukascopy from a few days before histdata's last bar (overlap for levelling).
    last_day = dt.datetime.fromtimestamp(hd_last * 60, dt.timezone.utc).date()
    days = [last_day - dt.timedelta(days=4) + dt.timedelta(days=i)
            for i in range((end - last_day).days + 5)]
    days = [d for d in days if d.weekday() != 5 and d <= end]
    if days and last_day < end:
        with ThreadPoolExecutor(duka_threads) as ex:
            got = list(ex.map(lambda d: _safe_duka(duka, d, duka_scale), days))
        tail = _concat([g for g in got if g is not None and g[0].size] or [tuple(np.empty(0) for _ in range(5))]) \
            if any(g is not None and g[0].size for g in got) else None
        if tail is not None:
            tt = tail[0]
            common, ia, ib = np.intersect1d(t, tt, return_indices=True)
            if common.size > 200:
                offset = float(np.median(c[ia] - tail[4][ib]))
                corr = float(np.corrcoef(np.diff(c[ia]), np.diff(tail[4][ib]))[0, 1])
            else:
                offset, corr = 0.0, float("nan")
            new = tt > hd_last
            if new.any():
                ext = tuple(x[new] for x in tail)
                ext = (ext[0], ext[1] + offset, ext[2] + offset, ext[3] + offset, ext[4] + offset)
                t, o, h, l, c = _concat([(t, o, h, l, c), ext])
                sources["dukascopy"] = (f"{_fmt(ext[0][0])} .. {_fmt(ext[0][-1])} "
                                        f"(levelled {offset:+.5g} on {common.size} overlapping minutes, "
                                        f"1-min return corr {corr:.3f})")
                _log(f"{feed}: dukascopy tail {int(new.sum()):,} bars, {sources['dukascopy']}")
    os.makedirs(M1, exist_ok=True)
    np.savez(os.path.join(M1, f"{feed}.npz"), t=t, o=o, h=h, l=l, c=c,
             sources=json.dumps(sources))
    return Minutes(feed, t, o, h, l, c, sources)


def _month_key(t: np.ndarray) -> np.ndarray:
    d = (t // 1440).astype("datetime64[D]")
    return d.astype("datetime64[M]").astype(np.int64)


def _fmt_month(key: int) -> str:
    return str(np.datetime64(int(key), "M"))


def mismatched_months(t: np.ndarray, c: np.ndarray, duka: str, scale: float, *,
                      tol: float = 0.01, threads: int = 6) -> List[int]:
    """Months whose histdata closes differ from Dukascopy's by more than ``tol``.

    One sample UTC weekday per month (the middle one with at least 300
    minutes) is compared on overlapping minutes.  Months Dukascopy cannot
    serve are kept.
    """
    day = t // 1440
    uniq, cnt = np.unique(day, return_counts=True)
    months = _month_key(uniq * 1440)
    samples = []
    for mk in np.unique(months):
        cand = uniq[(months == mk) & (cnt >= 300)]
        cand = [d for d in cand if (dt.date(1970, 1, 1) + dt.timedelta(days=int(d))).weekday() < 5]
        if cand:
            samples.append((int(mk), int(cand[len(cand) // 2])))
    ep = dt.date(1970, 1, 1)

    def check(item):
        mk, d = item
        got = _safe_duka(duka, ep + dt.timedelta(days=d), scale)
        if got is None or got[0].size < 60:
            return None
        common, ia, ib = np.intersect1d(t, got[0], return_indices=True)
        if common.size < 60:
            return None
        ratio = float(np.median(c[ia] / got[4][ib]))
        return mk if abs(ratio - 1.0) > tol else None

    with ThreadPoolExecutor(threads) as ex:
        return [m for m in ex.map(check, samples) if m is not None]


def level_outlier_days(t: np.ndarray, c: np.ndarray, *, tol: float = 0.25, half: int = 5) -> np.ndarray:
    """UTC days whose median close is more than ``tol`` (log) away from the
    median of the ``half`` days either side.  Real markets do not do that
    (the March 2020 crash days stay within ~10%); a wrong instrument does."""
    day = t // 1440
    uniq, start = np.unique(day, return_index=True)
    meds = np.array([np.median(c[a:b]) for a, b in zip(start, np.append(start[1:], c.size))])
    out = []
    for i in range(uniq.size):
        nb = np.r_[meds[max(0, i - half):i], meds[i + 1:i + 1 + half]]
        if nb.size and abs(np.log(meds[i] / np.median(nb))) > tol:
            out.append(uniq[i])
    return np.asarray(out, dtype=np.int64)


def thin_days(t: np.ndarray, start: dt.date, *, frac: float = 0.85,
              ref_from: dt.date = dt.date(2024, 1, 1)) -> List[dt.date]:
    """UTC weekdays with fewer than ``frac`` of a normal day's minutes.

    "Normal" is the median minutes per UTC weekday since ``ref_from``, when
    the histdata files are complete.  Christmas and New Year are skipped.
    """
    day = t // 1440
    uniq, cnt = np.unique(day, return_counts=True)
    ep = dt.date(1970, 1, 1)
    ref = cnt[uniq >= (ref_from - ep).days]
    ref = ref[[(ep + dt.timedelta(days=int(d))).weekday() < 5 for d in uniq[uniq >= (ref_from - ep).days]]]
    if ref.size == 0:
        return []
    need = frac * float(np.median(ref))
    have = dict(zip(uniq.tolist(), cnt.tolist()))
    out = []
    d = max(start, ep + dt.timedelta(days=int(uniq[0])))
    last = ep + dt.timedelta(days=int(uniq[-1]))
    while d <= last:
        if d.weekday() < 5 and (d.month, d.day) not in ((12, 25), (1, 1)):
            if have.get((d - ep).days, 0) < need:
                out.append(d)
        d += dt.timedelta(days=1)
    return out


def _duka_many(sym: str, days: List[dt.date], scale: float, threads: int = 24):
    done = [0]

    def one(d):
        r = _safe_duka(sym, d, scale)
        done[0] += 1
        if done[0] % 50 == 0:
            _log(f"dukascopy {sym}: {done[0]}/{len(days)} days")
        return r

    with ThreadPoolExecutor(threads) as ex:
        return list(ex.map(one, days))


def _safe_duka(sym: str, day: dt.date, scale: float):
    try:
        return dukascopy_day(sym, day, scale)
    except DataError as exc:
        _log(f"dukascopy {sym} {day}: {exc}")
        return None


def _fmt(minute: int) -> str:
    return dt.datetime.fromtimestamp(int(minute) * 60, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def load_feed(feed: str) -> Minutes:
    path = os.path.join(M1, f"{feed}.npz")
    if not os.path.exists(path):
        raise DataError(f"{feed}: not cached — run `python -m confluence.cli fetch` first")
    z = np.load(path)
    return Minutes(feed, z["t"], z["o"], z["h"], z["l"], z["c"], json.loads(str(z["sources"])))


# ------------------------------------------------------------------ proxy cross-check

def crosscheck(feed: Minutes, yahoo_symbol: str) -> Dict[str, object]:
    """How closely does the feed track the real instrument?  5-minute returns
    over Yahoo's last 60 days: correlation and the typical return gap."""
    try:
        yt, yc = fetch_yahoo(yahoo_symbol, "5m", "60d")
    except DataError as exc:
        return {"yahoo": yahoo_symbol, "error": str(exc)}
    # Feed closes on the same 5-minute grid (bar close = last minute in the bucket).
    bucket = feed.t // 5 * 5
    last = np.flatnonzero(np.diff(np.append(bucket, -1)) != 0)
    ft, fc = bucket[last], feed.c[last]
    # Yahoo stamps a 5m bar at its open; compare like with like.
    common, ia, ib = np.intersect1d(ft, yt, return_indices=True)
    if common.size < 500:
        return {"yahoo": yahoo_symbol, "overlap_bars": int(common.size), "error": "too little overlap"}
    fa, ya = fc[ia], yc[ib]
    gaps = np.diff(common) == 5
    fr, yr = np.diff(np.log(fa))[gaps], np.diff(np.log(ya))[gaps]
    return {
        "yahoo": yahoo_symbol,
        "overlap_bars": int(common.size),
        "from": _fmt(common[0]), "to": _fmt(common[-1]),
        "ret_corr_5m": round(float(np.corrcoef(fr, yr)[0, 1]), 4),
        "median_abs_ret_gap_bp": round(float(np.median(np.abs(fr - yr))) * 1e4, 3),
        "median_level_ratio": round(float(np.median(ya / fa)), 5),
    }
