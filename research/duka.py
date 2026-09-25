"""Years of one-minute Nasdaq-100 bars from Dukascopy's free chart service.

    python research/duka.py fetch 2013-01-01 2026-09-26   # resumable; about 240 requests, paced
    python research/duka.py status

The instrument is Dukascopy's Nasdaq-100 CFD (USATECH.IDX/USD, bid side),
which follows the NQ future minute for minute but is not the future: the
price level differs by the futures basis, there are no contract rolls, and
"volume" is Dukascopy's own tick count, not exchange volume.  Each request
returns up to 30,000 one-minute candles; they are cached under
data/cache/duka/USATECH_1m/ (git-ignored).

``sessions()`` turns them into regular-session (09:30-16:00 New York)
``shortbot.data.Session`` objects, at 1 or 5 minutes a bar.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import List, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shortbot.data import NY, Session, clean_sessions, to_sessions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "cache", "duka", "USATECH_1m")
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument=USATECH.IDX%2FUSD&offer_side=B"
       "&interval=1MIN&splits=true&stocks=true&limit=30000&time_direction=N&timestamp={ms}&jsonp=cb")
PACE = 3.0


def _chunk(ms: int) -> Optional[np.ndarray]:
    """Candles from ``ms`` on as rows (epoch seconds, o, h, l, c, v); None if refused."""
    req = urllib.request.Request(URL.format(ms=ms), headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://freeserv.dukascopy.com/"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode()
    rows = json.loads(text[text.index("(") + 1:text.rindex(")")])
    if not rows:
        return np.zeros((0, 6))
    a = np.asarray(rows, dtype=float)
    a[:, 0] = a[:, 0] // 1000
    return a


def _last_saved() -> Optional[int]:
    if not os.path.isdir(CACHE):
        return None
    ends = [int(f.split("_")[1].split(".")[0]) for f in os.listdir(CACHE) if f.endswith(".npz")]
    return max(ends) if ends else None


def fetch(start: str, end: str) -> None:
    os.makedirs(CACHE, exist_ok=True)
    stop_s = int(dt.datetime.fromisoformat(end).replace(tzinfo=dt.timezone.utc).timestamp())
    last = _last_saved()
    t = (last + 60) if last else int(dt.datetime.fromisoformat(start)
                                      .replace(tzinfo=dt.timezone.utc).timestamp())
    failures = 0
    while t < stop_s:
        try:
            a = _chunk(t * 1000)
        except urllib.error.HTTPError as e:
            failures += 1
            wait = 60 if e.code == 429 else 20
            print(f"{dt.datetime.utcfromtimestamp(t):%Y-%m-%d}: HTTP {e.code}; waiting {wait}s", flush=True)
            if failures > 20:
                raise SystemExit("too many failures; run again later to resume")
            time.sleep(wait)
            continue
        except (urllib.error.URLError, OSError, ValueError) as e:
            failures += 1
            print(f"{dt.datetime.utcfromtimestamp(t):%Y-%m-%d}: {type(e).__name__}; retrying", flush=True)
            if failures > 20:
                raise SystemExit("too many failures; run again later to resume")
            time.sleep(20)
            continue
        failures = 0
        if len(a) == 0:
            print("no more data", flush=True)
            break
        first, last = int(a[0, 0]), int(a[-1, 0])
        np.savez_compressed(os.path.join(CACHE, f"{first}_{last}.npz"), a=a)
        print(f"{dt.datetime.utcfromtimestamp(first):%Y-%m-%d} .. {dt.datetime.utcfromtimestamp(last):%Y-%m-%d}"
              f"  {len(a):,} minutes", flush=True)
        t = last + 60
        time.sleep(PACE)


def load_rows() -> np.ndarray:
    files = sorted(f for f in os.listdir(CACHE) if f.endswith(".npz"))
    a = np.concatenate([np.load(os.path.join(CACHE, f))["a"] for f in files])
    _, idx = np.unique(a[:, 0], return_index=True)
    return a[idx]


def sessions(bar_minutes: int = 5, start: str = "", end: str = "",
             dropped: Optional[list] = None) -> List[Session]:
    """Regular-session bars (09:30-16:00 New York).  Half days and days with
    missing or broken data are dropped (``dropped`` collects them)."""
    a = load_rows()
    step = 60 * bar_minutes
    if bar_minutes > 1:                                  # aggregate minutes into bars on the grid
        key = (a[:, 0] // step) * step
        cut = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
        ends = np.r_[cut[1:], len(a)]
        rows = [(int(key[s]), a[s, 1], a[s:e, 2].max(), a[s:e, 3].min(), a[e - 1, 4], a[s:e, 5].sum())
                for s, e in zip(cut, ends)]
    else:
        rows = [tuple(r) for r in a]
        rows = [(int(r[0]),) + tuple(float(x) for x in r[1:]) for r in rows]
    out = to_sessions(rows, bar_minutes, min_bars=int(0.97 * (390 // bar_minutes)))
    if start:
        out = [s for s in out if s.date >= start]
    if end:
        out = [s for s in out if s.date <= end]
    return clean_sessions(out, False, dropped)            # a CFD has no contract rolls


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "fetch":
        fetch(argv[1] if len(argv) > 1 else "2013-01-01", argv[2] if len(argv) > 2 else
              dt.date.today().isoformat())
    elif argv and argv[0] == "status":
        last = _last_saved()
        n = len(os.listdir(CACHE)) if os.path.isdir(CACHE) else 0
        print(f"{n} chunks cached" + (f", through {dt.datetime.utcfromtimestamp(last)} UTC" if last else ""))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
