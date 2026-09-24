"""Regular-session one-minute Nasdaq-100 bars from every source the repo has.

    sessions("duka")      # Dukascopy's Nasdaq-100 CFD, September 2020 on (duka.py fetches it)
    sessions("islands")   # expired NQ contracts from TradingView, a week before each expiry, 2016-2026
    sessions("yahoo")     # NQ=F from Yahoo, the last 30 days (strategies/soxl/minute.py archives it)

Each returns {New York date: Day}, only sessions with at least 380 of the 390
bars from 09:30 to 15:59.  Stamps are UTC.  Prices are index points: the CFD
sits a basis below the future (about 300 points in September 2026) but moves
with it minute for minute (5-minute returns correlate 0.99 on the days both
cover), and a one-point move is $2 on one MNQ contract either way.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
sys.path.append(str(ROOT / "strategies" / "soxl"))       # minute.py; appended so no module there shadows one here
sys.path.append(str(ROOT / "strategies" / "scalp"))      # nq_events.py


@dataclass
class Day:
    date: str
    stamps: List[str]
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray

    def __len__(self) -> int:
        return len(self.stamps)


def _from_rows(date: str, rows) -> Day:
    rows = sorted(rows)
    cols = list(zip(*rows))
    return Day(date, list(cols[0]), *(np.asarray(cols[k], dtype=float) for k in (1, 2, 3, 4)))


def sessions(source: str = "duka", start: str = "2000-01-01", end: str = "2100-01-01") -> Dict[str, Day]:
    if source == "duka":
        import duka
        raw = duka.load(start, end)
        out = {}
        for d, rows in sorted(raw.items()):
            day = _from_rows(d, rows)
            # a half day (the eve of July 4th, the day after Thanksgiving, Christmas Eve) keeps a
            # quote after the 13:00 close but hardly moves: drop sessions whose last two hours sit still
            if len(np.unique(day.c[-120:])) >= 40:
                out[d] = day
        return out
    if source == "islands":
        import nq_events
        out = {}
        for d, b in nq_events.sessions().items():
            if start <= d <= end:
                out[d] = Day(d, list(b.dates), np.asarray(b.open, float), np.asarray(b.high, float),
                             np.asarray(b.low, float), np.asarray(b.close, float))
        return out
    if source == "yahoo":
        import minute
        rows = minute.read("NQ=F")
        by: Dict[str, list] = {}
        for t, (o, h, l, c, v) in rows.items():
            by.setdefault(minute.session_of(t), []).append((t, o, h, l, c))
        return {d: _from_rows(d, r) for d, r in sorted(by.items()) if len(r) >= 380 and start <= d <= end}
    raise ValueError(source)
