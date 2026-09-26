"""Minute data and bars on the New York clock.

Time is New York wall-clock minutes since 1970-01-01 ("local minutes").  A
trading day starts at 18:00 New York time, as CME futures do, and is labelled
with the date it ends on.  ``tmin`` is minutes since that 18:00: 09:30 is 930,
15:55 is 1315.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "research"))
sys.path.insert(0, ROOT)
from duka import load_rows  # noqa: E402
from edges import BY_KEY, Market  # noqa: E402
from shortbot.data import NY  # noqa: E402

DAY_START = 18 * 60          # a trading day starts at 18:00 New York time
RTH = (930, 1320)            # 09:30-16:00 as tmin
STALE_JUMP = 0.001           # a 09:30 open more than 10 bp from the 09:29 close: stale overnight quotes
FROZEN = 10                  # this many minutes in a row without any price change in 09:30-16:00: stale data

# names as TradingView shows them -> Dukascopy instrument
MARKETS: Dict[str, str] = {
    "NAS100": "USATECH.IDX/USD", "US500": "USA500.IDX/USD", "US30": "USA30.IDX/USD",
    "US2000": "USSC2000.IDX/USD", "XAUUSD": "XAU/USD", "USOIL": "LIGHT.CMD/USD",
    "NATGAS": "GAS.CMD/USD", "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD", "USTBOND": "USTBOND.TR/USD",
}


def market(name: str) -> Market:
    """The CME contract a market is traded as (costs, tick, contract value)."""
    return BY_KEY[MARKETS[name]]


def day_label(day: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=int(day))).isoformat()


def trading_day_label(tday: int) -> str:
    """A trading day that starts at 18:00 on day ``tday`` ends on day ``tday + 1``."""
    return day_label(tday + 1)


def local_minutes(t: np.ndarray) -> np.ndarray:
    """New York wall-clock minutes for epoch seconds ``t``."""
    t = t.astype(np.int64)
    hours = np.unique(t // 3600)
    off = {h: int(datetime.fromtimestamp(h * 3600, timezone.utc).astimezone(NY).utcoffset().total_seconds())
           for h in hours}
    offs = np.array([off[h] for h in t // 3600], dtype=np.int64)
    return (t + offs) // 60


@dataclass
class Minutes:
    L: np.ndarray            # local minute of each row
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    tday: np.ndarray         # trading day of each row
    tmin: np.ndarray         # minutes since the trading day's 18:00
    valid: Dict[int, bool]   # trading day -> usable (a full 09:30-16:00 session, no broken jumps)
    night_ok: Dict[int, bool] = None   # trading day -> its 18:00-09:30 quotes are live (no frozen stretch)


@dataclass
class Bars:
    tf: int
    start: np.ndarray        # local minute the bar starts
    row0: np.ndarray         # first minute row of the bar
    row1: np.ndarray         # one past its last minute row
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    v: np.ndarray
    tday: np.ndarray
    tmin: np.ndarray         # tmin of the bar's start; it closes at tmin + tf


def from_rows(a: np.ndarray, rolls: bool = False) -> Minutes:
    """Minutes from Dukascopy rows (epoch s, o, h, l, c, v).

    ``rolls``: the market rolls between futures months (crude, gas).  The
    market is shut from 17:00 to 18:00, so any gap at the 18:00 reopen is a
    roll (or a weekend) and is removed by scaling all earlier prices -- the
    usual back-adjustment -- so indicators never see it.  Days with a
    one-minute jump over 2% inside them are marked unusable (broken data).

    Every market: a day whose 09:30 open is more than 10 bp from the 09:29
    close is marked unusable.  Futures trade straight through 09:30, so such
    a jump means the CFD's overnight quotes were stale (Dukascopy's Nasdaq-100
    in 2013-2014 held still overnight and jumped at the cash open); a stop set
    overnight would be "gapped" by a move that never happened in the futures.
    Likewise a day with 10 or more minutes in a row of a frozen price inside
    09:30-16:00 (stale quotes; futures never stand still that long).
    ``night_ok`` records the same check for 18:00-09:30; strategies that
    trade before 09:30 need it too.
    """
    a = a[np.argsort(a[:, 0], kind="stable")]
    L = local_minutes(a[:, 0])
    o, h, l, c, v = (a[:, k].astype(float).copy() for k in range(1, 6))
    tday = (L - DAY_START) // 1440
    tmin = (L - DAY_START) % 1440
    first = np.flatnonzero(np.r_[True, tday[1:] != tday[:-1]])
    if rolls and len(first) > 1:
        # each row is scaled by the product of every day-start gap after it
        step = np.ones(len(L))
        step[first[1:] - 1] = o[first[1:]] / c[first[1:] - 1]
        ratio = np.cumprod(step[::-1])[::-1]
        for x in (o, h, l, c):
            x *= ratio
    valid: Dict[int, bool] = {}
    night: Dict[int, bool] = {}
    # length of the run of frozen minutes (no range, no change) ending at each row
    frozen = (h == l) & np.r_[False, o[1:] == c[:-1]]
    last_break = np.maximum.accumulate(np.where(~frozen, np.arange(len(L)), -1))
    run = np.arange(len(L)) - last_break
    jump = np.r_[0.0, np.abs(o[1:] / c[:-1] - 1)]
    jump[first] = 0.0
    ends = np.r_[first[1:], len(L)]
    for s, e in zip(first, ends):
        tm = tmin[s:e]
        rth = np.count_nonzero((tm >= RTH[0]) & (tm < RTH[1]))
        ok = rth >= 0.9 * (RTH[1] - RTH[0])
        if ok and rolls and jump[s:e].max() > 0.02:
            ok = False
        in_rth = (tm >= RTH[0]) & (tm < RTH[1])
        if ok and run[s:e][in_rth].max(initial=0) >= FROZEN:
            ok = False
        k = s + int(np.searchsorted(tm, RTH[0]))
        if ok and k < e and tm[k - s] == RTH[0] and k > s and tm[k - s - 1] == RTH[0] - 1 \
                and jump[k] > STALE_JUMP:
            ok = False
        valid[int(tday[s])] = bool(ok)
        night[int(tday[s])] = bool(run[s:e][tm < RTH[0]].max(initial=0) < FROZEN)
    return Minutes(L, o, h, l, c, v, tday, tmin, valid, night)


@lru_cache(maxsize=4)
def minutes(name: str) -> Minutes:
    m = market(name)
    return from_rows(load_rows(m.key), rolls=m.rolls)


def make_bars(M: Minutes, tf: int) -> Bars:
    """tf-minute bars on the New York clock (tf divides 18:00, so bars line up with the trading day)."""
    if tf == 1:
        idx = np.arange(len(M.L))
        return Bars(1, M.L, idx, idx + 1, M.o, M.h, M.l, M.c, M.v, M.tday, M.tmin)
    key = M.L // tf
    cut = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    end = np.r_[cut[1:], len(M.L)]
    return Bars(tf, key[cut] * tf, cut, end, M.o[cut], np.maximum.reduceat(M.h, cut),
                np.minimum.reduceat(M.l, cut), M.c[end - 1], np.add.reduceat(M.v, cut),
                M.tday[cut], M.tmin[cut])


_BARS: Dict[tuple, Bars] = {}


def bars(name: str, tf: int) -> Bars:
    if (name, tf) not in _BARS:
        _BARS[(name, tf)] = make_bars(minutes(name), tf)
    return _BARS[(name, tf)]


def parse_clock(s: str) -> int:
    """'15:55' -> tmin."""
    hh, mm = s.split(":")
    return (int(hh) * 60 + int(mm) - DAY_START) % 1440
