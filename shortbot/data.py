"""Intraday bars grouped into New York trading sessions.

Backtests read Yahoo Finance's NQ=F (the same price as MNQ) or any CSV of
timestamp,open,high,low,close,volume.  The live bot builds the same
``Session`` objects from TopstepX bars, so the strategy never knows which
source it is looking at.
"""
from __future__ import annotations

import csv
import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")
CACHE_DIR = os.environ.get("EVOTRADER_CACHE", os.path.join("data", "cache"))
_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
_UA = "Mozilla/5.0 (compatible; evotrader/0.1)"

RTH_OPEN = 9 * 60 + 30
RTH_CLOSE = 16 * 60

Row = Tuple[int, float, float, float, float, float]   # epoch s, o, h, l, c, v


@dataclass
class Session:
    """One day's bars in time order.  ``minute`` is each bar's start time in
    minutes since midnight, New York."""

    date: str
    bar_minutes: int
    minute: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    def __len__(self) -> int:
        return len(self.minute)


def fetch_yahoo(symbol: str = "NQ=F", interval: str = "5m", rng: str = "60d",
                refresh: bool = False) -> List[Row]:
    """OHLCV rows from Yahoo's public chart endpoint, cached as CSV."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{symbol.replace('=', '_')}_{interval}_{rng}_ohlcv.csv")
    if os.path.exists(path) and not refresh:
        return load_csv(path)
    req = urllib.request.Request(_YAHOO.format(symbol=symbol, interval=interval, rng=rng),
                                 headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        chart = json.load(resp)["chart"]
    if not chart.get("result"):
        raise RuntimeError(f"Yahoo returned no data for {symbol}: {chart.get('error')}")
    res = chart["result"][0]
    q = res["indicators"]["quote"][0]
    rows = [(int(t), o, h, lo, c, float(v or 0.0)) for t, o, h, lo, c, v in
            zip(res["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"])
            if None not in (o, h, lo, c)]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    return rows


def load_csv(path: str) -> List[Row]:
    """Read timestamp,open,high,low,close[,volume].  The timestamp may be epoch
    seconds or an ISO-8601 string (naive strings are taken as UTC)."""
    rows: List[Row] = []
    with open(path, newline="") as f:
        for r in csv.reader(f):
            if not r or not r[0] or r[0].lower().startswith(("time", "date", "ts")):
                continue
            rows.append((_epoch(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]),
                         float(r[5]) if len(r) > 5 and r[5] != "" else 0.0))
    return rows


def _epoch(s: str) -> int:
    try:
        return int(float(s))
    except ValueError:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())


def to_sessions(rows: Iterable[Row], bar_minutes: int, start_min: int = RTH_OPEN,
                end_min: int = RTH_CLOSE, min_bars: int = 0) -> List[Session]:
    """Group bars into weekday sessions covering [start_min, end_min) New York."""
    by_day: Dict[str, List[Tuple]] = {}
    for t, o, h, lo, c, v in rows:
        dt = datetime.fromtimestamp(t, timezone.utc).astimezone(NY)
        m = dt.hour * 60 + dt.minute
        if start_min <= m < end_min and dt.weekday() < 5:
            by_day.setdefault(dt.strftime("%Y-%m-%d"), []).append((m, o, h, lo, c, v))
    out = []
    for day in sorted(by_day):
        uniq = {b[0]: b for b in by_day[day]}           # last write wins on duplicates
        a = np.asarray([uniq[m] for m in sorted(uniq)], dtype=float)
        if len(a) < max(min_bars, 1):
            continue
        out.append(Session(day, bar_minutes, a[:, 0].astype(int), a[:, 1], a[:, 2],
                           a[:, 3], a[:, 4], a[:, 5]))
    return out


def full_day_bars(bar_minutes: int, start_min: int = RTH_OPEN, end_min: int = RTH_CLOSE) -> int:
    return (end_min - start_min) // bar_minutes


def load_sessions(source: str, bar_minutes: int = 5, refresh: bool = False) -> List[Session]:
    """``yahoo`` (60 days of 5-minute bars), ``yahoo-hourly`` (two years of
    60-minute bars, 09:00-16:00) or a path to a CSV."""
    if source == "yahoo":
        rows = fetch_yahoo("NQ=F", "5m", "60d", refresh)
        return to_sessions(rows, 5, min_bars=int(0.8 * full_day_bars(5)))
    if source == "yahoo-hourly":
        rows = fetch_yahoo("NQ=F", "60m", "730d", refresh)
        return to_sessions(rows, 60, start_min=9 * 60, min_bars=6)
    rows = load_csv(source)
    return to_sessions(rows, bar_minutes, min_bars=int(0.8 * full_day_bars(bar_minutes)))


def session_from_bars(date: str, bar_minutes: int,
                      bars: Sequence[Tuple[int, float, float, float, float, float]]) -> Session:
    """Build a Session from (minute, o, h, l, c, v) tuples -- used by the live bot."""
    a = np.asarray(sorted(bars), dtype=float).reshape(-1, 6)
    return Session(date, bar_minutes, a[:, 0].astype(int), a[:, 1], a[:, 2], a[:, 3],
                   a[:, 4], a[:, 5])
