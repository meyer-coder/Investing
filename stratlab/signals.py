"""Signal families.  Each returns, for every bar, +1 (long), -1 (short) or 0,
known at the bar's close, and optionally a price level the family aims for
(used by a ``level`` target).  Directions and sessions are applied later by
the engine; these only say what the pattern is.
"""
from __future__ import annotations

import inspect
from typing import Callable, Dict, Optional, Tuple

import numpy as np

from . import indicators as ind
from .data import Bars

Signal = Tuple[np.ndarray, Optional[np.ndarray]]


def _cross_up(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a > b) & (ind.prior(a) <= ind.prior(b))


def _side(long_: np.ndarray, short: np.ndarray) -> np.ndarray:
    long_, short = np.nan_to_num(long_).astype(bool), np.nan_to_num(short).astype(bool)
    return np.where(long_ & ~short, 1, np.where(short & ~long_, -1, 0))


def volume_spike_breakout(B: Bars, vol_mult: float = 2.5, vol_n: int = 50, k: int = 10) -> Signal:
    avg = ind.prior(ind.sma(B.v, vol_n))
    spike = B.v >= vol_mult * avg
    hh, ll = ind.prior(ind.rolling_max(B.h, k)), ind.prior(ind.rolling_min(B.l, k))
    return _side(spike & (B.c > hh), spike & (B.c < ll)), None


def range_spike_breakout(B: Bars, mult: float = 2.0, n: int = 20, k: int = 10) -> Signal:
    tr = ind.true_range(B)
    spike = tr >= mult * ind.prior(ind.sma(tr, n))
    hh, ll = ind.prior(ind.rolling_max(B.h, k)), ind.prior(ind.rolling_min(B.l, k))
    return _side(spike & (B.c > hh), spike & (B.c < ll)), None


def donchian_break(B: Bars, n: int = 20) -> Signal:
    hh, ll = ind.prior(ind.rolling_max(B.h, n)), ind.prior(ind.rolling_min(B.l, n))
    return _side(_cross_up(B.c, hh), _cross_up(-B.c, -ll)), None


def ema_cross(B: Bars, fast: int = 9, slow: int = 21) -> Signal:
    f, s = ind.ema(B.c, fast), ind.ema(B.c, slow)
    return _side(_cross_up(f, s), _cross_up(s, f)), None


def ema_ribbon(B: Bars, fast: int = 8, mid: int = 21, slow: int = 55) -> Signal:
    f, m, s = ind.ema(B.c, fast), ind.ema(B.c, mid), ind.ema(B.c, slow)
    up, dn = (f > m) & (m > s), (f < m) & (m < s)
    return _side(up & ~ind.prior(up).astype(bool), dn & ~ind.prior(dn).astype(bool)), None


def macd_cross(B: Bars, fast: int = 12, slow: int = 26, signal: int = 9) -> Signal:
    macd = ind.ema(B.c, fast) - ind.ema(B.c, slow)
    sig = ind.ema(np.nan_to_num(macd), signal)
    return _side(_cross_up(macd, sig) & (macd < 0), _cross_up(sig, macd) & (macd > 0)), None


def zscore_reversion(B: Bars, n: int = 20, z: float = 2.0) -> Signal:
    mu, sd = ind.sma(B.c, n), ind.rolling_std(B.c, n)
    zz = np.where(sd > 0, (B.c - mu) / sd, 0.0)
    return _side(_cross_up(-zz, np.full_like(zz, z)), _cross_up(zz, np.full_like(zz, z))), mu


def bollinger_reclaim(B: Bars, n: int = 20, k: float = 2.0) -> Signal:
    mu, sd = ind.sma(B.c, n), ind.rolling_std(B.c, n)
    lo, hi = mu - k * sd, mu + k * sd
    was_below, was_above = ind.prior(B.c) < ind.prior(lo), ind.prior(B.c) > ind.prior(hi)
    return _side(was_below & (B.c > lo), was_above & (B.c < hi)), mu


def vwap_band_reversion(B: Bars, k: float = 2.0) -> Signal:
    vw, sd = ind.vwap(B)
    lo, hi = vw - k * sd, vw + k * sd
    return _side(_cross_up(-B.c, -lo) & (sd > 0), _cross_up(B.c, hi) & (sd > 0)), vw


def sweep_reclaim(B: Bars, k: int = 20) -> Signal:
    hh, ll = ind.prior(ind.rolling_max(B.h, k)), ind.prior(ind.rolling_min(B.l, k))
    return _side((B.l < ll) & (B.c > ll), (B.h > hh) & (B.c < hh)), None


def _first_break(B: Bars, hi: np.ndarray, lo: np.ndarray, after: int) -> np.ndarray:
    """+1/-1 at the first close beyond [lo, hi] each trading day, at or after tmin ``after``."""
    raw = _side((B.c > hi) & (B.tmin >= after), (B.c < lo) & (B.tmin >= after))
    out = np.zeros_like(raw)
    days = B.tday
    cut = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])
    for s, e in zip(cut, np.r_[cut[1:], len(days)]):
        k = np.flatnonzero(raw[s:e])
        if len(k):
            out[s + k[0]] = raw[s + k[0]]
    return out


def opening_range_breakout(B: Bars, minutes: int = 30) -> Signal:
    hi, lo, _, _ = ind.day_values(B, 930, 930 + minutes)
    return _first_break(B, hi, lo, 930 + minutes), None


def asian_range_break(B: Bars) -> Signal:
    hi, lo, _, _ = ind.day_values(B, 120, 360)              # 20:00-00:00
    return _first_break(B, hi, lo, 360), None


def round_number(B: Bars, grid: float = 10.0) -> Signal:
    up = (np.floor(B.o / grid) + 1) * grid                  # first round number above the open
    dn = (np.ceil(B.o / grid) - 1) * grid                   # first round number below the open
    return _side((B.l <= dn) & (B.c > dn), (B.h >= up) & (B.c < up)), None


def gap_fade(B: Bars, min_gap_atr: float = 0.5, days: int = 14) -> Signal:
    """At the close of the first 09:30 bar: if the day opened more than
    min_gap_atr x the average day range away from the previous 16:00 close,
    trade back toward that close (the ``level`` target)."""
    _, pc = ind.previous_rth(B)
    first = (B.tmin == 930)
    n = len(B.c)
    rth = (B.tmin >= 930) & (B.tmin + B.tf <= 1320)
    cut = np.flatnonzero(np.r_[True, B.tday[1:] != B.tday[:-1]])
    ranges = []                                             # (day's first row, end row, 09:30-16:00 range)
    for s, e in zip(cut, np.r_[cut[1:], n]):
        k = np.flatnonzero(rth[s:e]) + s
        ranges.append((s, e, B.h[k].max() - B.l[k].min() if len(k) else np.nan))
    rng = np.full(n, np.nan)
    for j, (s, e, _) in enumerate(ranges):
        prev = [r for _, _, r in ranges[max(0, j - days):j] if not np.isnan(r)]
        if len(prev) == days:
            rng[s:e] = np.mean(prev)
    gap = B.o - pc
    big = first & (np.abs(gap) > min_gap_atr * rng)
    return _side(big & (gap < 0), big & (gap > 0)), pc


def noise_breakout(B: Bars, lookback: int = 14) -> Signal:
    """Bot A's idea on any bars: a close outside the day's usual distance from
    its 09:30 open (the average for that time of day over the last
    ``lookback`` sessions), beyond the previous close too."""
    n = len(B.c)
    rth = (B.tmin >= 930) & (B.tmin + B.tf <= 1320)
    _, _, op, _ = ind.day_values(B, 930, 930 + B.tf)
    _, pc = ind.previous_rth(B)
    move = np.where(rth, np.abs(B.c / op - 1), np.nan)
    slot = (B.tmin - 930) // B.tf
    band = np.full(n, np.nan)
    hist: Dict[int, list] = {}
    cut = np.flatnonzero(np.r_[True, B.tday[1:] != B.tday[:-1]])
    for s, e in zip(cut, np.r_[cut[1:], n]):
        k = np.flatnonzero(rth[s:e]) + s
        for i in k:
            h = hist.get(int(slot[i]), [])
            if len(h) >= lookback:
                band[i] = np.mean(h[-lookback:])
        for i in k:
            if not np.isnan(move[i]):
                hist.setdefault(int(slot[i]), []).append(move[i])
    upper = np.maximum(op, pc) * (1 + band)
    lower = np.minimum(op, pc) * (1 - band)
    return _side(B.c > upper, B.c < lower), None


def random_control(B: Bars, rate: float = 0.02, seed: int = 0) -> Signal:
    """No information at all: a coin decides whether and which way to trade."""
    rng = np.random.default_rng(seed)
    fire = rng.random(len(B.c)) < rate
    side = np.where(rng.random(len(B.c)) < 0.5, 1, -1)
    return np.where(fire, side, 0), None


FAMILIES: Dict[str, Tuple[Callable[..., Signal], str]] = {
    "volume_spike_breakout": (volume_spike_breakout,
                              "a candle with volume {vol_mult}x its {vol_n}-candle average that closes beyond "
                              "the high (low) of the previous {k} candles"),
    "range_spike_breakout": (range_spike_breakout,
                             "a candle whose range is {mult}x the {n}-candle average and that closes beyond "
                             "the previous {k} candles"),
    "donchian_break": (donchian_break, "the first close beyond the highest high (lowest low) of {n} candles"),
    "ema_cross": (ema_cross, "the {fast} EMA crosses the {slow} EMA"),
    "ema_ribbon": (ema_ribbon, "the {fast}/{mid}/{slow} EMAs line up in order"),
    "macd_cross": (macd_cross, "MACD({fast},{slow},{signal}) crosses its signal line below (above) zero"),
    "zscore_reversion": (zscore_reversion, "the close moves {z} standard deviations from its {n}-candle "
                                           "average; fade it"),
    "bollinger_reclaim": (bollinger_reclaim, "a close back inside the {n}-candle, {k}-sigma Bollinger band "
                                             "after one outside it; fade the move"),
    "vwap_band_reversion": (vwap_band_reversion, "the close moves {k} sigma from the session VWAP; fade it"),
    "sweep_reclaim": (sweep_reclaim, "a candle takes out the {k}-candle high (low) and closes back inside; "
                                     "trade the reversal (liquidity sweep / Judas swing)"),
    "opening_range_breakout": (opening_range_breakout, "the first close beyond the first {minutes} minutes "
                                                       "of the 09:30 session"),
    "asian_range_break": (asian_range_break, "the first close beyond the 20:00-00:00 Asian range"),
    "round_number": (round_number, "a candle tags the next ${grid} round number and closes back; fade it"),
    "gap_fade": (gap_fade, "the 09:30 open gaps over {min_gap_atr}x the average day range from the previous "
                           "close; trade back toward that close"),
    "noise_breakout": (noise_breakout, "a close outside the usual distance from the 09:30 open for that time "
                                       "of day ({lookback} sessions) -- Bot A's idea"),
    "random_control": (random_control, "RANDOM CONTROL: a coin decides ({rate} of candles, seed {seed})"),
}


def compute(B: Bars, family: str, settings: dict) -> Signal:
    fn, _ = FAMILIES[family]
    return fn(B, **settings)


def settings_of(family: str, settings: dict) -> dict:
    """The family's settings with its defaults filled in."""
    fn, _ = FAMILIES[family]
    defaults = {k: v.default for k, v in inspect.signature(fn).parameters.items() if k != "B"}
    return {**defaults, **settings}


def describe(family: str, settings: dict) -> str:
    return FAMILIES[family][1].format(**settings_of(family, settings))
