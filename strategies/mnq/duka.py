"""Years of one-minute Nasdaq-100 bars from Dukascopy's free archive.

    python strategies/mnq/duka.py 2020-09-01 2026-09-23     # six years, a month per request; resumable
    python strategies/mnq/duka.py --status                  # what is on disk

Dukascopy's chart service returns up to 30,000 one-minute candles a request
(about a month) for its Nasdaq-100 CFD (USATECH.IDX/USD), which follows the
index future minute for minute.  Requests are paced three seconds apart.
Each month's candles between 13:00 and 21:30 UTC (the New York session in
summer and winter time) land in data/cache/duka/ as a compressed array
(git-ignored); `load()` turns them into regular-session bars.  The per-day
archive files (`fetch_days`) are the same data, far slower to fetch.

The candles are the bid side, stamped in UTC.  Volume is Dukascopy's own
tick count, not exchange volume, so nothing here should lean on it.
"""
from __future__ import annotations

import datetime as dt
import lzma
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "duka" / "USATECHIDXUSD"
URL = "https://datafeed.dukascopy.com/datafeed/USATECHIDXUSD/{y:04d}/{m:02d}/{d:02d}/BID_candles_min_1.bi5"
NY = ZoneInfo("America/New_York")
SCALE = 1000.0
Row = Tuple[str, float, float, float, float, float]


JSON_URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument=USATECH.IDX%2FUSD&offer_side=B"
            "&interval=1MIN&splits=true&stocks=true&limit=30000&time_direction=N&timestamp={ms}&jsonp=cb")
MONTHS = ROOT / "data" / "cache" / "duka" / "months"


def _json_chunk(ms: int) -> Optional[np.ndarray]:
    """Candles from `ms` on: rows of (epoch seconds, open, high, low, close); None when refused."""
    req = urllib.request.Request(JSON_URL.format(ms=ms), headers={"User-Agent": "Mozilla/5.0",
                                                                  "Referer": "https://freeserv.dukascopy.com/"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode()
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        print(f"{dt.datetime.utcfromtimestamp(ms / 1000)}: {type(e).__name__}", flush=True)
        return None
    import json
    rows = [x for x in json.loads(text[text.index("(") + 1:text.rindex(")")]) if x]
    if not rows:
        return np.zeros((0, 5))
    a = np.array([[x[0] / 1000.0, x[1], x[2], x[3], x[4]] for x in rows], dtype=float)
    return a


def fetch(start: dt.date, end: dt.date, pace: float = 3.0) -> int:
    """Every month from `start` to `end` not yet on disk, one request each
    (a second one when a month has more candles than a request carries)."""
    MONTHS.mkdir(parents=True, exist_ok=True)
    got = 0
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        path = MONTHS / f"{y:04d}-{m:02d}.npz"
        nxt = (y + (m == 12), 1 if m == 12 else m + 1)
        month_end = dt.datetime(*nxt, 1, tzinfo=dt.timezone.utc).timestamp()
        if not path.exists() or (y, m) == (end.year, end.month):
            t = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp()
            parts = []
            while t < month_end:
                for attempt in range(6):
                    a = _json_chunk(int(t * 1000))
                    if a is not None:
                        break
                    time.sleep(10 * (attempt + 1))
                else:
                    print(f"{y}-{m:02d}: refused six times, stopping", flush=True)
                    return got
                time.sleep(pace)
                if not len(a):
                    break
                a = a[a[:, 0] < month_end]
                parts.append(a)
                if not len(a) or a[-1, 0] + 60 >= month_end:
                    break
                t = a[-1, 0] + 60
            a = np.concatenate(parts) if parts else np.zeros((0, 5))
            hm = (a[:, 0] % 86400) / 60.0
            keep = (hm >= 13 * 60) & (hm < 21 * 60 + 30)
            np.savez_compressed(path, a=a[keep].astype(np.float64))
            got += 1
            print(f"{y}-{m:02d}: {int(keep.sum())} candles in the session window", flush=True)
        y, m = nxt
    return got


def _path(day: dt.date) -> Path:
    return CACHE / f"{day.isoformat()}.bi5"


def _get(day: dt.date) -> Optional[bytes]:
    """One day's raw file: bytes, b"" for a day with no data, None when refused."""
    req = urllib.request.Request(URL.format(y=day.year, m=day.month - 1, d=day.day),
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return b""
        print(f"{day}: HTTP {e.code}", flush=True)
        return None
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        print(f"{day}: {type(e).__name__}", flush=True)
        return None


def fetch_days(start: dt.date, end: dt.date, pace: float = 5.0) -> int:
    """The per-day archive files, every weekday from `end` back to `start`
    not yet on disk (slow: the archive throttles hard)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    day, got, refused = end, 0, 0
    while day >= start:
        if day.weekday() < 5 and not _path(day).exists():
            for attempt in range(8):
                raw = _get(day)
                if raw is not None:
                    _path(day).write_bytes(raw)
                    got += 1
                    refused = 0
                    pace = max(3.0, pace - 0.05)
                    break
                refused += 1
                pace = min(12.0, pace + 0.5)
                time.sleep(10 * (attempt + 1))
            else:
                print(f"{day}: refused eight times, stopping", flush=True)
                return got
            if got % 25 == 0:
                print(f"{day}: {got} days fetched, pace {pace:.1f}s", flush=True)
            time.sleep(pace)
        day -= dt.timedelta(days=1)
    return got


def decode(day: dt.date) -> List[Row]:
    raw = _path(day).read_bytes()
    if not raw:
        return []
    data = lzma.decompress(raw)
    base = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc)
    out = []
    for i in range(len(data) // 24):
        t, o, c, lo, hi, v = struct.unpack(">iiiiif", data[i * 24:(i + 1) * 24])
        stamp = (base + dt.timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M")
        out.append((stamp, o / SCALE, hi / SCALE, lo / SCALE, c / SCALE, float(v)))
    return out


def load(start: str = "2000-01-01", end: str = "2100-01-01", rth: bool = True) -> Dict[str, List[Row]]:
    """Candles on disk by New York session date (the monthly arrays, else the
    per-day files).  With `rth`, only the 09:30-15:59 bars, and only sessions
    with at least 380 of them that moved."""
    out: Dict[str, List[Row]] = {}
    months = sorted(MONTHS.glob("*.npz"))
    if months:
        for p in months:
            if not (start[:7] <= p.stem <= end[:7]):
                continue
            for ts, o, h, l, c in np.load(p)["a"]:
                u = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
                t = u.astimezone(NY)
                if rth and not ((9, 30) <= (t.hour, t.minute) < (16, 0)):
                    continue
                d = t.strftime("%Y-%m-%d")
                if start <= d <= end:
                    out.setdefault(d, []).append((u.strftime("%Y-%m-%d %H:%M"), o, h, l, c, 0.0))
    else:
        for p in sorted(CACHE.glob("*.bi5")):
            if not (start <= p.stem <= end):
                continue
            for row in decode(dt.date.fromisoformat(p.stem)):
                t = dt.datetime.strptime(row[0], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).astimezone(NY)
                if rth and not ((9, 30) <= (t.hour, t.minute) < (16, 0)):
                    continue
                out.setdefault(t.strftime("%Y-%m-%d"), []).append(row)
    if rth:
        out = {d: rows for d, rows in out.items()
               if len(rows) >= 380 and np.ptp([r[4] for r in rows]) > 0}
    return out


def status() -> str:
    months = sorted(p.stem for p in MONTHS.glob("*.npz"))
    days = sorted(p.stem for p in CACHE.glob("*.bi5"))
    return (f"{len(months)} months on disk ({months[0] if months else '-'} to {months[-1] if months else '-'}); "
            f"{len(days)} per-day files")


if __name__ == "__main__":
    if "--status" in sys.argv:
        print(status())
    else:
        a, b = (dt.date.fromisoformat(x) for x in sys.argv[1:3])
        print(fetch(a, b), "days fetched;", status())
