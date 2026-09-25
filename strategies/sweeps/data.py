"""NQ and ES one-minute bars from 07:00 to 16:00 New York, for the breakout and liquidity-sweep bot.

    from data import load                  # load("NQ") or load("ES") -> {dates, O, H, L, C (days x 540), ...}

Dukascopy's Nasdaq-100 and S&P 500 CFDs, which follow the index futures
minute for minute (the bid side, UTC stamps), as fetched by
strategies/quick/indexes.py (data/cache/duka/idx/<name>/, 2013 to August 2020
for the Nasdaq, 2013 on for the S&P) and strategies/mnq/duka.py
(data/cache/duka/months_wide/, the Nasdaq from September 2020).  Each file
holds 11:00-21:30 UTC, so 07:00-16:00 New York is always inside it.

Column 0 is 07:00, 150 is the 09:30 open, 539 is 15:59.  A day is kept when
it has 97% of its regular-session minutes and 80% of the pre-market ones;
missing minutes carry the last price forward; half days are dropped.  Each
day also carries the previous kept session's regular-hours high, low and
close.  Cached in data/cache/quick/sweep_<inst>.npz.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DUKA = ROOT / "data" / "cache" / "duka"
CACHE = ROOT / "data" / "cache" / "quick"
NY = ZoneInfo("America/New_York")
T, OPEN = 540, 150                       # minutes from 07:00; the 09:30 open's column


def _files(inst: str):
    if inst == "NQ":
        old = [p for p in sorted((DUKA / "idx" / "USATECH").glob("*.npz")) if p.stem < "2020-09"]
        return old + sorted((DUKA / "months_wide").glob("*.npz"))
    return sorted((DUKA / "idx" / {"ES": "USA500", "YM": "USA30", "RTY": "USSC2000"}[inst]).glob("*.npz"))


def load(inst: str = "NQ") -> dict:
    path = CACHE / f"sweep_{inst}.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files}
    a = np.concatenate([np.load(p)["a"] for p in _files(inst)])
    a = a[np.unique(a[:, 0], return_index=True)[1]]
    t = a[:, 0].astype(np.int64)
    day = t // 86400
    minute = (t % 86400) // 60
    days = np.unique(day)
    offset = {d: int(dt.datetime.fromtimestamp(int(d) * 86400 + 43200, tz=NY).utcoffset().total_seconds() // 60) for d in days}
    k = minute + np.array([offset[d] for d in day]) - 7 * 60
    wk = np.array([dt.date.fromordinal(dt.date(1970, 1, 1).toordinal() + int(d)).weekday() for d in days])
    weekday = dict(zip(days, wk))
    keep = (k >= 0) & (k < T) & np.array([weekday[d] < 5 for d in day])
    a, day, k = a[keep], day[keep], k[keep]
    out_dates, X = [], []
    starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    ends = np.r_[starts[1:], len(day)]
    for s, e in zip(starts, ends):
        kk = k[s:e]
        rth = np.sum(kk >= OPEN)
        pre = np.sum(kk < OPEN)
        if rth < 0.97 * (T - OPEN) or pre < 0.8 * OPEN:
            continue
        x = np.full((T, 4), np.nan)
        x[kk] = a[s:e, 1:5]
        first = np.flatnonzero(~np.isnan(x[:, 3]))[0]
        x[:first] = x[first, 0]
        for j in range(first + 1, T):
            if np.isnan(x[j, 3]):
                x[j] = x[j - 1, 3]
        if len(np.unique(x[-120:, 3])) < 20:                                  # a half day
            continue
        out_dates.append(dt.date.fromordinal(dt.date(1970, 1, 1).toordinal() + int(day[s])).isoformat())
        X.append(x)
    X = np.array(X)
    O, H, L, C = X[:, :, 0], X[:, :, 1], X[:, :, 2], X[:, :, 3]
    ph = np.r_[np.nan, H[:-1, OPEN:].max(axis=1)]
    pl = np.r_[np.nan, L[:-1, OPEN:].min(axis=1)]
    pc = np.r_[np.nan, C[:-1, -1]]
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, dates=np.array(out_dates), O=O, H=H, L=L, C=C, ph=ph, pl=pl, pc=pc)
    return load(inst)


if __name__ == "__main__":
    for inst in ("NQ", "ES"):
        D = load(inst)
        print(inst, len(D["dates"]), D["dates"][0], D["dates"][-1])
