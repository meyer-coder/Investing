"""Technical indicators, compiled with numba.

All functions take and return 1-D float64 arrays of the same length, NaN
where the indicator is not yet defined.  They run over up to ~3 million bars
(8 years of 1-minute data), so the recursive ones are plain loops under
``@njit`` rather than Python.
"""
from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def ema(x, n):
    out = np.full(x.size, np.nan)
    if x.size < n:
        return out
    a = 2.0 / (n + 1.0)
    acc = 0.0
    for i in range(n):
        acc += x[i]
    acc /= n
    out[n - 1] = acc
    for i in range(n, x.size):
        acc = a * x[i] + (1.0 - a) * acc
        out[i] = acc
    return out


@njit(cache=True)
def rma(x, n):
    """Wilder's smoothing (alpha = 1/n), seeded with a simple mean."""
    out = np.full(x.size, np.nan)
    if x.size < n:
        return out
    acc = 0.0
    for i in range(n):
        acc += x[i]
    acc /= n
    out[n - 1] = acc
    for i in range(n, x.size):
        acc = (acc * (n - 1) + x[i]) / n
        out[i] = acc
    return out


@njit(cache=True)
def sma(x, n):
    out = np.full(x.size, np.nan)
    s = 0.0
    for i in range(x.size):
        s += x[i]
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


@njit(cache=True)
def wma(x, n):
    out = np.full(x.size, np.nan)
    denom = n * (n + 1) / 2.0
    for i in range(n - 1, x.size):
        s = 0.0
        for k in range(n):
            s += x[i - k] * (n - k)
        out[i] = s / denom
    return out


def hma(x, n):
    half = wma(x, max(n // 2, 1))
    full = wma(x, n)
    raw = 2.0 * half - full
    raw = np.where(np.isnan(raw), 0.0, raw)
    out = wma(raw, max(int(np.sqrt(n)), 1))
    out[: n + int(np.sqrt(n))] = np.nan
    return out


@njit(cache=True)
def true_range(h, l, c):
    tr = np.empty(c.size)
    tr[0] = h[0] - l[0]
    for i in range(1, c.size):
        a = h[i] - l[i]
        b = abs(h[i] - c[i - 1])
        d = abs(l[i] - c[i - 1])
        tr[i] = max(a, max(b, d))
    return tr


def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)


@njit(cache=True)
def rsi(c, n):
    out = np.full(c.size, np.nan)
    if c.size <= n:
        return out
    g = 0.0
    lo = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]
        if d > 0:
            g += d
        else:
            lo -= d
    g /= n
    lo /= n
    out[n] = 100.0 if lo == 0 else 100.0 - 100.0 / (1.0 + g / lo)
    for i in range(n + 1, c.size):
        d = c[i] - c[i - 1]
        up = d if d > 0 else 0.0
        dn = -d if d < 0 else 0.0
        g = (g * (n - 1) + up) / n
        lo = (lo * (n - 1) + dn) / n
        out[i] = 100.0 if lo == 0 else 100.0 - 100.0 / (1.0 + g / lo)
    return out


@njit(cache=True)
def _dm(h, l):
    n = h.size
    p = np.zeros(n)
    m = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        if up > dn and up > 0:
            p[i] = up
        if dn > up and dn > 0:
            m[i] = dn
    return p, m


def adx(h, l, c, n=14):
    """Return (adx, +DI, -DI)."""
    tr = rma(true_range(h, l, c), n)
    p, m = _dm(h, l)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100.0 * rma(p, n) / tr
        mdi = 100.0 * rma(m, n) / tr
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    dx = np.where(np.isnan(dx), 0.0, dx)
    a = rma(dx, n)
    a[: 2 * n] = np.nan
    return a, pdi, mdi


def macd(c, fast=12, slow=26, signal=9):
    line = ema(c, fast) - ema(c, slow)
    sig = np.full(c.size, np.nan)
    valid = np.flatnonzero(~np.isnan(line))
    if valid.size:
        sig[valid[0]:] = ema(line[valid[0]:], signal)
    return line, sig, line - sig


@njit(cache=True)
def rolling_std(x, n):
    out = np.full(x.size, np.nan)
    s = 0.0
    s2 = 0.0
    for i in range(x.size):
        s += x[i]
        s2 += x[i] * x[i]
        if i >= n:
            s -= x[i - n]
            s2 -= x[i - n] * x[i - n]
        if i >= n - 1:
            v = (s2 - s * s / n) / (n - 1)
            out[i] = np.sqrt(v) if v > 0 else 0.0
    return out


@njit(cache=True)
def rolling_max(x, n):
    out = np.full(x.size, np.nan)
    for i in range(n - 1, x.size):
        m = x[i]
        for k in range(1, n):
            if x[i - k] > m:
                m = x[i - k]
        out[i] = m
    return out


@njit(cache=True)
def rolling_min(x, n):
    out = np.full(x.size, np.nan)
    for i in range(n - 1, x.size):
        m = x[i]
        for k in range(1, n):
            if x[i - k] < m:
                m = x[i - k]
        out[i] = m
    return out


def stochastic(h, l, c, n=14, d=3):
    hh = rolling_max(h, n)
    ll = rolling_min(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(hh > ll, 100.0 * (c - ll) / (hh - ll), 50.0)
    k = sma(np.where(np.isnan(k), 50.0, k), d)
    return k, sma(np.where(np.isnan(k), 50.0, k), d)


@njit(cache=True)
def supertrend(h, l, c, atr_, mult):
    """Direction +1 / -1 of the classic Supertrend."""
    n = c.size
    d = np.zeros(n)
    up = np.nan
    dn = np.nan
    trend = 1.0
    for i in range(n):
        if np.isnan(atr_[i]):
            continue
        mid = (h[i] + l[i]) / 2.0
        bu = mid - mult * atr_[i]
        bd = mid + mult * atr_[i]
        if np.isnan(up):
            up, dn = bu, bd
        else:
            up = max(bu, up) if c[i - 1] > up else bu
            dn = min(bd, dn) if c[i - 1] < dn else bd
        if trend < 0 and c[i] > dn:
            trend = 1.0
        elif trend > 0 and c[i] < up:
            trend = -1.0
        d[i] = trend
    return d


@njit(cache=True)
def heikin_ashi(o, h, l, c):
    n = c.size
    ho = np.empty(n)
    hc = (o + h + l + c) / 4.0
    ho[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2.0
    return ho, hc


def shift(x, k=1, fill=np.nan):
    out = np.empty_like(x, dtype=float)
    if k > 0:
        out[:k] = fill
        out[k:] = x[:-k]
    else:
        out[:] = x
    return out
