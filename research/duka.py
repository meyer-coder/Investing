"""Years of one-minute Nasdaq-100 bars from Dukascopy's free chart service.

    python research/duka.py fetch 2013-01-01 2026-09-26                # the Nasdaq-100; resumable
    python research/duka.py fetch 2013-01-01 2026-09-26 XAU/USD        # any Dukascopy instrument
    python research/duka.py status XAU/USD

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
import urllib.parse
import urllib.request
from typing import List, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shortbot.data import NY, Session, clean_sessions, to_sessions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_ROOT = os.path.join(ROOT, "data", "cache", "duka")
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument={inst}&offer_side=B"
       "&interval=1MIN&splits=true&stocks=true&limit=30000&time_direction=N&timestamp={ms}&jsonp=cb")
PACE = 3.0
NASDAQ = "USATECH.IDX/USD"


def cache_dir(instrument: str = NASDAQ) -> str:
    name = "USATECH" if instrument == NASDAQ else instrument.replace("/", "_").replace(".", "_")
    return os.path.join(CACHE_ROOT, f"{name}_1m")


CACHE = cache_dir()


def _chunk(ms: int, instrument: str = NASDAQ) -> Optional[np.ndarray]:
    """Candles from ``ms`` on as rows (epoch seconds, o, h, l, c, v); None if refused."""
    url = URL.format(inst=urllib.parse.quote(instrument, safe=""), ms=ms)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Referer": "https://freeserv.dukascopy.com/"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode()
    rows = json.loads(text[text.index("(") + 1:text.rindex(")")])
    if not rows:
        return np.zeros((0, 6))
    a = np.asarray(rows, dtype=float)
    a[:, 0] = a[:, 0] // 1000
    return a


def _last_saved(instrument: str = NASDAQ) -> Optional[int]:
    d = cache_dir(instrument)
    if not os.path.isdir(d):
        return None
    ends = [int(f.split("_")[1].split(".")[0]) for f in os.listdir(d) if f.endswith(".npz")]
    return max(ends) if ends else None


def fetch(start: str, end: str, instrument: str = NASDAQ) -> None:
    folder = cache_dir(instrument)
    os.makedirs(folder, exist_ok=True)
    stop_s = int(dt.datetime.fromisoformat(end).replace(tzinfo=dt.timezone.utc).timestamp())
    last = _last_saved(instrument)
    t = (last + 60) if last else int(dt.datetime.fromisoformat(start)
                                      .replace(tzinfo=dt.timezone.utc).timestamp())
    failures = 0
    while t < stop_s:
        try:
            a = _chunk(t * 1000, instrument)
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
        np.savez_compressed(os.path.join(folder, f"{first}_{last}.npz"), a=a)
        print(f"{dt.datetime.utcfromtimestamp(first):%Y-%m-%d} .. {dt.datetime.utcfromtimestamp(last):%Y-%m-%d}"
              f"  {len(a):,} minutes", flush=True)
        t = last + 60
        time.sleep(PACE)


def load_rows(instrument: str = NASDAQ) -> np.ndarray:
    d = cache_dir(instrument)
    files = sorted(f for f in os.listdir(d) if f.endswith(".npz"))
    a = np.concatenate([np.load(os.path.join(d, f))["a"] for f in files])
    _, idx = np.unique(a[:, 0], return_index=True)
    return a[idx]


def sessions(bar_minutes: int = 5, start: str = "", end: str = "",
             dropped: Optional[list] = None, instrument: str = NASDAQ,
             session: tuple = (9 * 60 + 30, 16 * 60), max_jump_pct: Optional[float] = None) -> List[Session]:
    """Bars inside ``session`` (minutes since midnight New York; the regular
    09:30-16:00 session by default).  Half days and days with missing data are
    dropped (``dropped`` collects them).  ``max_jump_pct`` drops days with a
    bar-to-bar jump above that share of the price: needed for commodity CFDs,
    which roll between futures months; not for indices or currencies."""
    a = load_rows(instrument)
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
    length = (session[1] - session[0]) // bar_minutes
    out = to_sessions(rows, bar_minutes, start_min=session[0], end_min=session[1],
                      min_bars=int(0.97 * length))
    if start:
        out = [s for s in out if s.date >= start]
    if end:
        out = [s for s in out if s.date <= end]
    # index and currency CFDs have no contract rolls: no expiry weeks to drop and
    # no jump filter (one here removed real crash days such as 2025-04-09)
    return clean_sessions(out, False, dropped, max_jump_pct=max_jump_pct)


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "fetch":
        fetch(argv[1] if len(argv) > 1 else "2013-01-01", argv[2] if len(argv) > 2 else
              dt.date.today().isoformat(), argv[3] if len(argv) > 3 else NASDAQ)
    elif argv and argv[0] == "status":
        inst = argv[1] if len(argv) > 1 else NASDAQ
        last = _last_saved(inst)
        d = cache_dir(inst)
        n = len(os.listdir(d)) if os.path.isdir(d) else 0
        print(f"{inst}: {n} chunks cached" + (f", through {dt.datetime.utcfromtimestamp(last)} UTC" if last else ""))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
