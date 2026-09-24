"""Years of one-minute bars for US stocks, from Dukascopy's stock CFDs.

    python strategies/scalp/duka_stocks.py 2022-09-01 2026-09-23 AAPL NVDA ...   # fetch; resumable
    python strategies/scalp/duka_stocks.py --ask 2022-09-01 2026-09-23 AAPL ...   # the offer side
    python strategies/scalp/duka_stocks.py --10s 2025-09-24 2026-09-23 NVDA ...  # ten-second bars, both sides
    python strategies/scalp/duka_stocks.py --status

Yahoo keeps one-minute stock bars for 30 days only, so the scalpers in this
folder were found on one month.  Dukascopy's chart service serves its US
stock CFDs (<SYM>.US/USD), which follow the listed shares, a minute at a
time for years, up to 30,000 minutes a request (about three and a half months
of regular sessions).  Bid side, stamped in UTC; volume is Dukascopy's own tick
count, so nothing here uses it.  Bars from 13:00 to 21:30 UTC are kept, one
compressed array per stock in data/cache/duka/stocks/ (git-ignored).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "cache" / "duka" / "stocks"
STORE_ASK = ROOT / "data" / "cache" / "duka" / "stocks_ask"                 # the offer side, same layout
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument={sym}.US%2FUSD&offer_side={side}&interval={interval}"
       "&splits=true&stocks=true&limit=30000&time_direction=N&timestamp={ms}&jsonp=cb")
NY = ZoneInfo("America/New_York")


def _chunk(sym: str, ms: int, side: str = "B", interval: str = "1MIN") -> Optional[np.ndarray]:
    req = urllib.request.Request(URL.format(sym=sym, ms=ms, side=side, interval=interval), headers={"User-Agent": "Mozilla/5.0",
                                                                       "Referer": "https://freeserv.dukascopy.com/"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode()
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        print(f"{sym} {dt.datetime.utcfromtimestamp(ms / 1000):%Y-%m-%d}: {type(e).__name__}", flush=True)
        return None
    rows = [x for x in json.loads(text[text.index("(") + 1:text.rindex(")")]) if x]
    if not rows:
        return np.zeros((0, 5))
    return np.array([[x[0] / 1000.0, x[1], x[2], x[3], x[4]] for x in rows], dtype=float)


def fetch(sym: str, start: dt.date, end: dt.date, pace: float = 3.0, side: str = "B") -> int:
    """All minutes from `start` to `end`, appended to what is on disk (side "A" for the offer)."""
    store = STORE_ASK if side == "A" else STORE
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{sym}.npz"
    have = np.load(path)["a"] if path.exists() else np.zeros((0, 5))
    t = dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp()
    if len(have):
        t = max(t, have[-1, 0] + 60)
    stop = dt.datetime(end.year, end.month, end.day, 23, 59, tzinfo=dt.timezone.utc).timestamp()
    parts, got = [have], 0
    while t < stop:
        for attempt in range(6):
            a = _chunk(sym, int(t * 1000), side)
            if a is not None:
                break
            time.sleep(10 * (attempt + 1))
        else:
            print(f"{sym}: refused six times, stopping", flush=True)
            break
        time.sleep(pace)
        if not len(a):
            break
        a = a[a[:, 0] < stop]
        hm = (a[:, 0] % 86400) / 60.0
        parts.append(a[(hm >= 13 * 60) & (hm < 21 * 60 + 30)])
        got += len(a)
        if not len(a) or a[-1, 0] + 60 >= stop:
            break
        t = a[-1, 0] + 60
    allrows = np.concatenate(parts)
    if len(allrows):
        allrows = allrows[np.unique(allrows[:, 0], return_index=True)[1]]
    np.savez_compressed(path, a=allrows)
    return got


def load(sym: str, start: str = "2000-01-01", end: str = "2100-01-01") -> Dict[str, np.ndarray]:
    """Regular-session bars (09:30-15:59 New York) by date: rows of (epoch seconds, o, h, l, c)."""
    path = STORE / f"{sym}.npz"
    if not path.exists():
        return {}
    a = np.load(path)["a"]
    out: Dict[str, list] = {}
    for row in a:
        t = dt.datetime.fromtimestamp(row[0], tz=dt.timezone.utc).astimezone(NY)
        if not ((9, 30) <= (t.hour, t.minute) < (16, 0)):
            continue
        d = t.strftime("%Y-%m-%d")
        if start <= d <= end:
            out.setdefault(d, []).append(row)
    return {d: np.array(v) for d, v in out.items() if len(v) >= 370}


def fetch_seconds(sym: str, start: dt.date, end: dt.date, pace: float = 2.0) -> int:
    """Ten-second bars, bid and offer, 13:30-20:00 UTC, to data/cache/duka/stocks10s/<SYM>_<B|A>.npz."""
    store = STORE.parent / "stocks10s"
    store.mkdir(parents=True, exist_ok=True)
    got = 0
    for side in ("B", "A"):
        path = store / f"{sym}_{side}.npz"
        have = np.load(path)["a"] if path.exists() else np.zeros((0, 5))
        t = dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp()
        if len(have):
            t = max(t, have[-1, 0] + 10)
        stop = dt.datetime(end.year, end.month, end.day, 23, 59, tzinfo=dt.timezone.utc).timestamp()
        parts = [have]
        while t < stop:
            for attempt in range(6):
                a = _chunk(sym, int(t * 1000), side, "10SEC")
                if a is not None:
                    break
                time.sleep(10 * (attempt + 1))
            else:
                break
            time.sleep(pace)
            if not len(a):
                break
            a = a[a[:, 0] < stop]
            hm = (a[:, 0] % 86400) / 60.0
            parts.append(a[(hm >= 13 * 60 + 25) & (hm < 20 * 60 + 5)])
            got += len(a)
            if not len(a) or a[-1, 0] + 10 >= stop:
                break
            t = a[-1, 0] + 10
        rows = np.concatenate(parts)
        if len(rows):
            rows = rows[np.unique(rows[:, 0], return_index=True)[1]]
        np.savez_compressed(path, a=rows)
    return got


def status() -> str:
    files = sorted(STORE.glob("*.npz"))
    out = []
    for p in files:
        a = np.load(p)["a"]
        if len(a):
            out.append(f"{p.stem} {dt.datetime.utcfromtimestamp(a[0, 0]):%Y-%m-%d}..{dt.datetime.utcfromtimestamp(a[-1, 0]):%Y-%m-%d} ({len(a)})")
    return f"{len(files)} stocks: " + "; ".join(out)


if __name__ == "__main__":
    if "--status" in sys.argv:
        print(status())
    else:
        side = "A" if "--ask" in sys.argv else "B"
        args = [x for x in sys.argv[1:] if x not in ("--ask", "--10s")]
        a, b = (dt.date.fromisoformat(x) for x in args[:2])
        for sym in args[2:]:
            n = fetch_seconds(sym, a, b) if "--10s" in sys.argv else fetch(sym, a, b, side=side)
            print(f"{sym}: {n} minutes fetched", flush=True)
        print(status())
