"""Indicators on bars.  Every value at bar i uses bars up to and including i
(known at its close); the ``prior_*`` helpers use bars before i only."""
from __future__ import annotations

import numpy as np

from evotrader.indicators import atr as _atr, ema, rolling_std, sma  # noqa: F401

from .data import Bars


def rolling_max(x: np.ndarray, w: int) -> np.ndarray:
    """Max over the last w values, ending at each i (van Herk / Gil-Werman)."""
    x = np.asarray(x, float)
    n = len(x)
    out = np.full(n, np.nan)
    if w < 1 or n < w:
        return out
    pad = (-n) % w
    xp = np.concatenate([x, np.full(pad, -np.inf)]).reshape(-1, w)
    pre = np.maximum.accumulate(xp, axis=1).ravel()[:n]
    suf = np.maximum.accumulate(xp[:, ::-1], axis=1)[:, ::-1].ravel()[:n]
    i = np.arange(w - 1, n)
    out[w - 1:] = np.maximum(suf[i - w + 1], pre[i])
    return out


def rolling_min(x: np.ndarray, w: int) -> np.ndarray:
    return -rolling_max(-np.asarray(x, float), w)


def prior(x: np.ndarray) -> np.ndarray:
    """x shifted one bar later: the value as of the bar before."""
    return np.r_[np.nan, np.asarray(x, float)[:-1]]


def atr(B: Bars, n: int = 14) -> np.ndarray:
    return _atr(B.h, B.l, B.c, n)


def true_range(B: Bars) -> np.ndarray:
    pc = prior(B.c)
    tr = np.maximum(B.h - B.l, np.maximum(np.abs(B.h - pc), np.abs(B.l - pc)))
    tr[0] = B.h[0] - B.l[0]
    return tr


def anchors(B: Bars) -> np.ndarray:
    """VWAP anchor of each bar: 18:00 for the overnight, 09:30 for the day session."""
    return B.tday * 2 + (B.tmin >= 930)


def vwap(B: Bars):
    """Session VWAP and its volume-weighted standard deviation (typical price;
    the data's volume is the CFD's quote activity, a stand-in for real volume)."""
    tp = (B.h + B.l + B.c) / 3
    v = np.where(B.v > 0, B.v, 1e-12)
    a = anchors(B)
    cut = np.flatnonzero(np.r_[True, a[1:] != a[:-1]])
    seg = np.repeat(np.arange(len(cut)), np.diff(np.r_[cut, len(a)]))

    def cum(x):
        cs = np.cumsum(x)
        base = np.r_[0.0, cs[cut[1:] - 1]]
        return cs - base[seg]

    sv, spv, sp2v = cum(v), cum(tp * v), cum(tp * tp * v)
    vw = spv / sv
    sd = np.sqrt(np.maximum(sp2v / sv - vw * vw, 0.0))
    return vw, sd


def day_values(B: Bars, lo: int, hi: int):
    """For each bar, the high, low, open and close of its trading day's [lo, hi)
    tmin window -- available only once the window is over (NaN before)."""
    n = len(B.c)
    hi_a, lo_a, op_a, cl_a = (np.full(n, np.nan) for _ in range(4))
    inwin = (B.tmin >= lo) & (B.tmin + B.tf <= hi)
    days = B.tday
    cut = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])
    end = np.r_[cut[1:], n]
    for s, e in zip(cut, end):
        k = np.flatnonzero(inwin[s:e]) + s
        if len(k) == 0:
            continue
        after = np.arange(k[-1] + 1, e)
        if (B.tmin[k[-1]] + B.tf) < hi:                 # window not finished inside the data
            continue
        hi_a[after] = B.h[k].max()
        lo_a[after] = B.l[k].min()
        op_a[after] = B.o[k[0]]
        cl_a[after] = B.c[k[-1]]
    return hi_a, lo_a, op_a, cl_a


def previous_rth(B: Bars):
    """For each bar, the previous trading day's 09:30-16:00 open and close."""
    n = len(B.c)
    po, pc = np.full(n, np.nan), np.full(n, np.nan)
    rth = (B.tmin >= 930) & (B.tmin + B.tf <= 1320)
    days = B.tday
    cut = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])
    end = np.r_[cut[1:], n]
    last = (np.nan, np.nan)
    for s, e in zip(cut, end):
        po[s:e], pc[s:e] = last
        k = np.flatnonzero(rth[s:e]) + s
        if len(k):
            last = (B.o[k[0]], B.c[k[-1]])
    return po, pc
