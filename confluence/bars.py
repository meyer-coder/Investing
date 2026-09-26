"""From 1-minute history to the bars, clocks and levels a strategy sees.

Everything intraday is keyed to the New York clock, because that is how the
sessions (Asia, London, NY am/pm) and the CME trading day are defined:

* a **trading day** runs 18:00 ET -> 17:00 ET and is named after the date it
  ends on (Sunday evening belongs to Monday), exactly like CME Globex;
* ``tdm`` ("trading-day minute") is minutes since 18:00 ET, 0..1439, which
  makes every session a contiguous interval.

Levels such as the Asia range or the opening range only exist once their
window has closed.  A bar may use a level only if the bar *opened* after the
window ended, so no bar ever sees a level that its own prices helped form.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from .data import Minutes

# Session entry windows and exit times, in trading-day minutes (0 = 18:00 ET).
def _tdm(hh: int, mm: int = 0) -> int:
    return ((hh * 60 + mm) - 18 * 60) % 1440


SESSIONS: Dict[str, Tuple[int, int, int]] = {
    #            entries from, entries until, flat at
    "Asia":    (_tdm(19), _tdm(0), _tdm(3)),
    "London":  (_tdm(2), _tdm(6), _tdm(9, 25)),
    "NY am":   (_tdm(9, 30), _tdm(11, 30), _tdm(12, 30)),
    "NY pm":   (_tdm(13), _tdm(15, 30), _tdm(16)),
    "Ldn+NY":  (_tdm(2), _tdm(11, 30), _tdm(16)),
    "all":     (_tdm(18, 5), _tdm(15, 30), _tdm(16, 50)),
}
SESSION_ORDER = list(SESSIONS)

# Prop-firm futures accounts (Topstep, FundedNext) must be flat by 3:10 PM CT
# (4:10 PM ET), so the second run's "all" session goes flat at 4:05 PM ET.
PROP_SESSIONS: Dict[str, Tuple[int, int, int]] = dict(SESSIONS, all=(_tdm(18, 5), _tdm(15, 30), _tdm(16, 5)))

# Level windows (trading-day minutes), available from the window's end.
ASIA = (_tdm(19), _tdm(0))
LONDON = (_tdm(2), _tdm(5))
OVERNIGHT = (0, _tdm(9, 30))
OR30 = (_tdm(9, 30), _tdm(10))
IB = (_tdm(9, 30), _tdm(10, 30))
MIDNIGHT = _tdm(0)
NY_OPEN = _tdm(9, 30)

# Round-number grid per feed, for the "round number" confluence.
ROUND_STEP = {"NSXUSD": 100.0, "SPXUSD": 25.0, "WTIUSD": 1.0, "EURUSD": 0.005,
              "GBPUSD": 0.005, "USDJPY": 0.5, "XAUUSD": 10.0, "GRXEUR": 100.0,
              # second run (futures universe; 6J / 6C / 6S are quoted as USD per unit)
              "F_NQ": 100.0, "F_ES": 25.0, "F_YM": 250.0, "F_RTY": 25.0, "F_NKD": 500.0,
              "F_CL": 1.0, "F_NG": 0.1, "F_GC": 10.0, "F_SI": 0.5, "F_HG": 0.05,
              "F_6E": 0.005, "F_6B": 0.005, "F_6J": 0.00005, "F_6A": 0.005, "F_6C": 0.005,
              "F_6S": 0.005, "F_6N": 0.005, "F_ZB": 1.0, "F_ZS": 10.0, "F_ETH": 100.0}


@dataclass
class MinuteClock:
    """1-minute data plus its New York clock, shared by every timeframe."""

    m: Minutes
    tdm: np.ndarray       # int16 minutes since 18:00 ET
    day: np.ndarray       # int32 trading-day id (days since epoch)
    week: np.ndarray      # int32 trading-week id

    @property
    def n(self) -> int:
        return len(self.m)


def minute_clock(m: Minutes) -> MinuteClock:
    import pandas as pd

    idx = pd.DatetimeIndex(m.t.astype("datetime64[m]")).tz_localize("UTC").tz_convert("America/New_York")
    local = (idx.tz_localize(None).to_numpy().astype("datetime64[m]").astype(np.int64))
    shifted = local + 6 * 60                   # 18:00 ET -> midnight of the trading day
    day = (shifted // 1440).astype(np.int32)
    tdm = (shifted % 1440).astype(np.int16)
    week = ((day.astype(np.int64) + 3) // 7).astype(np.int32)   # epoch day 0 was a Thursday
    return MinuteClock(m, tdm, day, week)


@dataclass
class Frame:
    """One feed at one timeframe: bars, their clocks, levels and indicators."""

    feed: str
    tf: int
    t: np.ndarray            # bar open, UTC minutes
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    lo: np.ndarray           # first 1-minute index of the bar
    hi: np.ndarray           # one past the last 1-minute index
    tdm_open: np.ndarray     # trading-day minute at the bar's open
    tdm_close: np.ndarray    # trading-day minute at the bar's close (open + tf)
    day: np.ndarray
    clock: MinuteClock
    m1_bar: np.ndarray       # 1-minute index -> bar index
    v: Optional[np.ndarray] = None   # bar tick volume (None when the feed has no volume)
    cache: Dict[str, np.ndarray] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.t.size)


def resample(clock: MinuteClock, tf: int) -> Frame:
    """Bars of ``tf`` minutes aligned to the trading day (18:00 ET), so no bar
    ever straddles two sessions — 120 and 240-minute bars included."""
    m = clock.m
    tdm = clock.tdm.astype(np.int64)
    vol = getattr(m, "v", None)
    if tf == 1:
        lo = np.arange(m.t.size, dtype=np.int64)
        hi = lo + 1
        t, o, h, l, c = m.t, m.o, m.h, m.l, m.c
        v = vol
        tdm_open = tdm.copy()
    else:
        bucket = clock.day.astype(np.int64) * 1440 + (tdm // tf) * tf
        lo = np.flatnonzero(np.concatenate(([True], np.diff(bucket) != 0))).astype(np.int64)
        hi = np.append(lo[1:], m.t.size).astype(np.int64)
        tdm_open = (tdm[lo] // tf) * tf
        t = m.t[lo] - (tdm[lo] - tdm_open)
        o = m.o[lo]
        c = m.c[hi - 1]
        h = np.maximum.reduceat(m.h, lo)
        l = np.minimum.reduceat(m.l, lo)
        v = np.add.reduceat(vol, lo) if vol is not None else None
    tdm_close = np.minimum(tdm_open + tf, 1440).astype(np.int16)
    m1_bar = np.repeat(np.arange(lo.size, dtype=np.int32), (hi - lo).astype(np.int64))
    return Frame(m.feed, tf, t, o, h, l, c, lo, hi, tdm_open.astype(np.int16), tdm_close,
                 clock.day[lo], clock, m1_bar, v)


# ------------------------------------------------------------------ levels

def _window_extremes(clock: MinuteClock, start: int, end: int):
    """Per trading day: (days, high, low, first open) of 1-minute bars with tdm in [start, end)."""
    mask = (clock.tdm >= start) & (clock.tdm < end)
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        e = np.empty(0)
        return e.astype(np.int32), e, e, e
    d = clock.day[idx]
    cut = np.flatnonzero(np.concatenate(([True], np.diff(d) != 0)))
    hi = np.maximum.reduceat(clock.m.h[idx], cut)
    lo = np.minimum.reduceat(clock.m.l[idx], cut)
    first = clock.m.o[idx[cut]]
    return d[cut], hi, lo, first


def _map_daily(frame: Frame, days: np.ndarray, values: np.ndarray, available_from: int) -> np.ndarray:
    """Spread a per-day value onto bars of that day that opened after it was known."""
    out = np.full(frame.n, np.nan)
    if days.size == 0:
        return out
    pos = np.searchsorted(days, frame.day)
    pos_c = np.minimum(pos, days.size - 1)
    hit = (days[pos_c] == frame.day) & (frame.tdm_open >= available_from)
    out[hit] = values[pos_c[hit]]
    return out


def _map_prior(frame: Frame, days: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Value from the most recent *previous* trading day that has data."""
    out = np.full(frame.n, np.nan)
    if days.size == 0:
        return out
    pos = np.searchsorted(days, frame.day) - 1       # strictly earlier day
    ok = pos >= 0
    out[ok] = values[pos[ok]]
    return out


def add_levels(frame: Frame) -> None:
    """Compute every session / daily level once per frame (cached)."""
    ck = frame.clock
    cache = frame.cache
    # Whole trading day.
    d, dh, dl, dopen = _window_extremes(ck, 0, 1440)
    last = np.flatnonzero(np.append(np.diff(ck.day) != 0, True))
    dclose = ck.m.c[last]
    cache["pdh"] = _map_prior(frame, d, dh)
    cache["pdl"] = _map_prior(frame, d, dl)
    cache["pdc"] = _map_prior(frame, d, dclose)
    cache["day_open"] = _map_daily(frame, d, dopen, 0)
    pivot = (dh + dl + dclose) / 3.0
    cache["pivot"] = _map_prior(frame, d, pivot)
    cache["r1"] = _map_prior(frame, d, 2 * pivot - dl)
    cache["s1"] = _map_prior(frame, d, 2 * pivot - dh)
    # Daily EMA20 of closes, known at the prior close.
    from .indicators import ema
    dema = ema(dclose, 20)
    cache["daily_bias"] = _map_prior(frame, d, np.sign(dclose - dema))
    # Prior trading week.
    wk_of_day = ((d.astype(np.int64) + 3) // 7)
    wcut = np.flatnonzero(np.concatenate(([True], np.diff(wk_of_day) != 0)))
    wh = np.maximum.reduceat(dh, wcut)
    wl = np.minimum.reduceat(dl, wcut)
    wids = wk_of_day[wcut]
    fweek = (frame.day.astype(np.int64) + 3) // 7
    pos = np.searchsorted(wids, fweek) - 1
    ok = pos >= 0
    cache["pwh"] = np.where(ok, wh[np.maximum(pos, 0)], np.nan)
    cache["pwl"] = np.where(ok, wl[np.maximum(pos, 0)], np.nan)
    # Session windows.
    for name, (a, b) in {"asia": ASIA, "london": LONDON, "on": OVERNIGHT, "or": OR30, "ib": IB}.items():
        wd, wh_, wl_, _ = _window_extremes(ck, a, b)
        cache[f"{name}_h"] = _map_daily(frame, wd, wh_, b)
        cache[f"{name}_l"] = _map_daily(frame, wd, wl_, b)
    # Day's extreme during London (for power-of-three), known after London.
    for name, at in {"midnight": MIDNIGHT, "ny_open": NY_OPEN}.items():
        wd, _, _, first = _window_extremes(ck, at, at + 30)
        cache[name] = _map_daily(frame, wd, first, at)
    # Running high/low of the trading day so far, up to and including this bar.
    cache["day_hi"], cache["day_lo"] = _running_day_extremes(frame)
    # Volume-free VWAP (see vwap_proxy).
    vw, sd = vwap_proxy(frame)
    cache["vwap"], cache["vwap_sd"] = vw, sd


def _running_day_extremes(frame: Frame):
    hi = frame.h.copy()
    lo = frame.l.copy()
    new_day = np.concatenate(([True], np.diff(frame.day) != 0))
    starts = np.flatnonzero(new_day)
    ends = np.append(starts[1:], frame.n)
    for s, e in zip(starts, ends):
        hi[s:e] = np.maximum.accumulate(hi[s:e])
        lo[s:e] = np.minimum.accumulate(lo[s:e])
    return hi, lo


def vwap_proxy(frame: Frame):
    """Session VWAP anchored at 18:00 ET, with ±σ bands.

    The 8-year CFD / FX feeds carry no usable volume, so each minute is
    weighted by its range (high - low) instead.  Intraday volume and range are
    strongly correlated, so this tracks a true VWAP far better than an
    unweighted average; it is still a proxy and is labelled as one.
    """
    ck = frame.clock
    m = ck.m
    rng = m.h - m.l
    floor = np.median(rng[rng > 0]) * 0.1 if np.any(rng > 0) else 1e-9
    w = np.maximum(rng, floor)
    tp = (m.h + m.l + m.c) / 3.0
    new_day = np.concatenate(([True], np.diff(ck.day) != 0))
    grp = np.cumsum(new_day) - 1
    def seg_cumsum(x):
        cs = np.cumsum(x)
        base = np.concatenate(([0.0], cs))[np.flatnonzero(new_day)]
        return cs - base[grp]
    s0 = seg_cumsum(w)
    s1 = seg_cumsum(w * tp)
    s2 = seg_cumsum(w * tp * tp)
    at = frame.hi - 1
    vw = s1[at] / s0[at]
    var = np.maximum(s2[at] / s0[at] - vw * vw, 0.0)
    return vw, np.sqrt(var)


def higher_tf_trend(clock: MinuteClock, frame: Frame, htf: int, length: int = 50) -> np.ndarray:
    """+1 / -1 / 0: last *completed* higher-timeframe close vs its rising / falling EMA."""
    from .indicators import ema

    big = resample(clock, htf)
    e = ema(big.c, length)
    slope = np.concatenate(([np.nan] * 3, e[3:] - e[:-3]))
    state = np.where((big.c > e) & (slope > 0), 1.0, np.where((big.c < e) & (slope < 0), -1.0, 0.0))
    state[np.isnan(e) | np.isnan(slope)] = 0.0
    big_close = big.t + htf
    pos = np.searchsorted(big_close, frame.t + frame.tf, side="right") - 1
    out = np.zeros(frame.n)
    ok = pos >= 0
    out[ok] = state[pos[ok]]
    return out
