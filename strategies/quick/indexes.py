"""One-minute bars for the other US index CFDs on Dukascopy: S&P 500, Russell 2000, Dow.

    python strategies/quick/indexes.py 2020-09-01 2026-09-23 USA500 USSC2000 USA30   # fetch; resumable
    from indexes import load                                                        # {dates, O, H, L, C, pc}

Same service and layout as strategies/mnq/duka.py (the Nasdaq-100): a month
per file, 11:00-21:30 UTC, in data/cache/duka/idx/<name>/ (git-ignored).
`load(name)` lines the regular sessions up 09:30-15:59 New York like
index.load(), dropping half days.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "cache" / "duka" / "idx"
CACHE = ROOT / "data" / "cache" / "quick"
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument={inst}&offer_side=B"
       "&interval=1MIN&splits=true&stocks=true&limit=30000&time_direction=N&timestamp={ms}&jsonp=cb")
INSTRUMENTS = {"USA500": "USA500.IDX%2FUSD", "USSC2000": "USSC2000.IDX%2FUSD", "USA30": "USA30.IDX%2FUSD",
               "WTI": "LIGHT.CMD%2FUSD", "GOLD": "XAU%2FUSD", "TBOND": "USTBOND.TR%2FUSD", "EURUSD": "EUR%2FUSD"}
# the day each market trades most, New York time: stock indexes 09:30-16:00; crude oil, gold and bonds their
# pit hours; the euro London's afternoon and New York's morning
SESSIONS = {"WTI": ((9, 0), (14, 30)), "GOLD": ((8, 20), (13, 30)), "TBOND": ((8, 20), (15, 0)), "EURUSD": ((8, 0), (16, 0))}
NY = ZoneInfo("America/New_York")
WINDOW = (11 * 60, 21 * 60 + 30)
T = 390


def _chunk(inst: str, ms: int):
    req = urllib.request.Request(URL.format(inst=INSTRUMENTS.get(inst, inst), ms=ms), headers={"User-Agent": "Mozilla/5.0",
                                                                        "Referer": "https://freeserv.dukascopy.com/"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            text = r.read().decode()
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        print(f"{inst} {dt.datetime.utcfromtimestamp(ms / 1000):%Y-%m-%d}: {type(e).__name__}", flush=True)
        return None
    rows = [x for x in json.loads(text[text.index("(") + 1:text.rindex(")")]) if x]
    return np.array([[x[0] / 1000.0, x[1], x[2], x[3], x[4]] for x in rows]) if rows else np.zeros((0, 5))


def fetch(inst: str, start: dt.date, end: dt.date, pace: float = 2.0) -> int:
    folder = STORE / inst
    folder.mkdir(parents=True, exist_ok=True)
    got = 0
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        path = folder / f"{y:04d}-{m:02d}.npz"
        nxt = (y + (m == 12), 1 if m == 12 else m + 1)
        month_end = dt.datetime(*nxt, 1, tzinfo=dt.timezone.utc).timestamp()
        if not path.exists() or (y, m) == (end.year, end.month):
            t = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp()
            parts = []
            while t < month_end:
                for attempt in range(6):
                    a = _chunk(inst, int(t * 1000))
                    if a is not None:
                        break
                    time.sleep(10 * (attempt + 1))
                else:
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
            np.savez_compressed(path, a=a[(hm >= WINDOW[0]) & (hm < WINDOW[1])])
            got += 1
        y, m = nxt
    return got


def load(inst: str) -> dict:
    """{dates, O, H, L, C (days x minutes), pc}: the market's session (SESSIONS, else 09:30-16:00 New York) on days
    with at least 97% of its minutes, half days dropped."""
    path = CACHE / f"idx_{inst}.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files}
    rows = np.concatenate([np.load(p)["a"] for p in sorted((STORE / inst).glob("*.npz"))])
    rows = rows[np.unique(rows[:, 0], return_index=True)[1]]
    (h0, m0), (h1, m1) = SESSIONS.get(inst, ((9, 30), (16, 0)))
    n_min = (h1 * 60 + m1) - (h0 * 60 + m0)
    by = {}
    for r in rows:
        t = dt.datetime.fromtimestamp(r[0], tz=dt.timezone.utc).astimezone(NY)
        k = (t.hour - h0) * 60 + t.minute - m0
        if 0 <= k < n_min and t.weekday() < 5:
            by.setdefault(t.strftime("%Y-%m-%d"), []).append((k, r[1], r[2], r[3], r[4]))
    dates, X = [], []
    for d in sorted(by):
        v = by[d]
        if len(v) < 0.97 * n_min:
            continue
        a = np.full((n_min, 4), np.nan)
        for k, o, h, l, c in v:
            a[k] = (o, h, l, c)
        for j in range(n_min):
            if np.isnan(a[j, 3]):
                a[j] = a[j - 1, 3] if j else a[np.flatnonzero(~np.isnan(a[:, 3]))[0], 0]
        if len(np.unique(a[-120:, 3])) < 20:                                  # a half day: the last two hours sit still
            continue
        dates.append(d)
        X.append(a)
    X = np.array(X)
    pc = np.concatenate([[np.nan], X[:-1, -1, 3]])
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, dates=np.array(dates), O=X[:, :, 0], H=X[:, :, 1], L=X[:, :, 2], C=X[:, :, 3], pc=pc)
    return load(inst)


if __name__ == "__main__":
    a, b = (dt.date.fromisoformat(x) for x in sys.argv[1:3])
    for inst in sys.argv[3:]:
        print(f"{inst}: {fetch(inst, a, b)} months fetched", flush=True)
