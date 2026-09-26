"""Price structure from causal swing pivots, and the patterns built on it.

A swing pivot is a local high or low that price has since moved away from by
at least ``k`` ATR.  It is *confirmed* on the bar where that reversal happens,
and nothing below may use a pivot before its confirmation bar, so every
pattern is known only at the close of the bar where it would really have been
visible on a chart.

Patterns (long side; shorts mirror):

* market structure  higher highs and higher lows (HH/HL) = up, LH/LL = down
* BOS               close through the last swing high while structure is up
* CHoCH             close through the last swing high while structure is down
* Fibonacci         pullback into a retracement band of the last completed swing up
* Elliott           wave-3 start (break of wave-1 high after a 38.2–88.6% wave 2),
                    wave-2 buy (golden-pocket pullback after an impulse that broke
                    structure), ABC end (C leg equal to A leg)
* harmonics         Gartley, Bat, Butterfly, Crab and AB=CD: price reaches the
                    pattern's D level and closes back above it (first touch only)
* trend lines       bounce off the line through the last two rising swing lows;
                    break of the line through the last two falling swing highs
* Gann angles       touch of the 1x1 / 2x1 angle drawn from the last swing low, with
                    one "unit" = 0.25 ATR per bar (Gann's price/time scale has to be
                    chosen; this one keeps the angles comparable across markets)
* S/R               retest of a prior swing low as support; broken swing high
                    retested as support (role reversal)
* supply & demand   first return to a demand zone: a small base candle that price
                    left with a 1.5 ATR displacement
"""
from __future__ import annotations

import numpy as np
from numba import njit

PIVOT_ATR = 3.0
HARMONIC_PIVOT_ATR = 1.5


@njit(cache=True)
def pivots(h, l, atr, k):
    """Zigzag pivots.  Returns (price, bar, type(+1 high/-1 low), confirm_bar), count."""
    n = h.size
    # a pivot can be confirmed on every bar when ATR is tiny (flat holiday tape), so size for n
    pp = np.empty(n + 8)
    pi = np.empty(n + 8, np.int64)
    pt = np.empty(n + 8, np.int8)
    pc = np.empty(n + 8, np.int64)
    m = 0
    d = 0
    hi = -1e300
    hi_i = 0
    lo = 1e300
    lo_i = 0
    for i in range(n):
        a = atr[i]
        if not (a > 0):
            continue
        if h[i] > hi:
            hi = h[i]
            hi_i = i
        if l[i] < lo:
            lo = l[i]
            lo_i = i
        if d >= 0 and hi - l[i] >= k * a and hi_i < i + 1 and (d == 1 or hi_i > lo_i):
            pp[m] = hi
            pi[m] = hi_i
            pt[m] = 1
            pc[m] = i
            m += 1
            d = -1
            lo = l[i]
            lo_i = i
            continue
        if d <= 0 and h[i] - lo >= k * a and (d == -1 or lo_i > hi_i):
            pp[m] = lo
            pi[m] = lo_i
            pt[m] = -1
            pc[m] = i
            m += 1
            d = 1
            hi = h[i]
            hi_i = i
    return pp[:m].copy(), pi[:m].copy(), pt[:m].copy(), pc[:m].copy()


@njit(cache=True)
def _last(pp, pt, pc, upto, typ, skip):
    """Index into the pivot arrays of the (skip+1)-th most recent pivot of ``typ`` among the first ``upto``."""
    s = 0
    for j in range(upto - 1, -1, -1):
        if pt[j] == typ:
            if s == skip:
                return j
            s += 1
    return -1


@njit(cache=True)
def levels(n, pp, pi, pt, pc):
    """Per bar: last two swing highs / lows (price and bar) known at that bar's close, and structure state."""
    sh1 = np.full(n, np.nan)
    sh2 = np.full(n, np.nan)
    sl1 = np.full(n, np.nan)
    sl2 = np.full(n, np.nan)
    sh1i = np.full(n, -1, np.int64)
    sh2i = np.full(n, -1, np.int64)
    sl1i = np.full(n, -1, np.int64)
    sl2i = np.full(n, -1, np.int64)
    known = np.zeros(n, np.int64)
    ms = np.zeros(n)
    p = 0
    m = pp.size
    for i in range(n):
        while p < m and pc[p] <= i:
            p += 1
        known[i] = p
        a = _last(pp, pt, pc, p, 1, 0)
        b = _last(pp, pt, pc, p, 1, 1)
        c = _last(pp, pt, pc, p, -1, 0)
        d = _last(pp, pt, pc, p, -1, 1)
        if a >= 0:
            sh1[i] = pp[a]
            sh1i[i] = pi[a]
        if b >= 0:
            sh2[i] = pp[b]
            sh2i[i] = pi[b]
        if c >= 0:
            sl1[i] = pp[c]
            sl1i[i] = pi[c]
        if d >= 0:
            sl2[i] = pp[d]
            sl2i[i] = pi[d]
        if a >= 0 and b >= 0 and c >= 0 and d >= 0:
            if pp[a] > pp[b] and pp[c] > pp[d]:
                ms[i] = 1.0
            elif pp[a] < pp[b] and pp[c] < pp[d]:
                ms[i] = -1.0
    return sh1, sh2, sl1, sl2, sh1i, sh2i, sl1i, sl2i, known, ms


@njit(cache=True)
def fib_zone(h, l, c, pp, pt, known, lo_r, hi_r):
    """Pullback into [lo_r, hi_r] retracement of the last completed swing, closing back out of the deep edge."""
    n = c.size
    up = np.zeros(n, np.bool_)
    dn = np.zeros(n, np.bool_)
    for i in range(n):
        k = known[i]
        if k < 2:
            continue
        # last pivot is a high and the one before a low: swing up just completed
        if pt[k - 1] == 1 and pt[k - 2] == -1:
            H = pp[k - 1]
            L = pp[k - 2]
            leg = H - L
            if leg > 0:
                top = H - lo_r * leg
                deep = H - hi_r * leg
                if l[i] <= top and l[i] >= H - (hi_r + 0.1) * leg and c[i] > deep and l[i] > L:
                    up[i] = True
        if pt[k - 1] == -1 and pt[k - 2] == 1:
            L = pp[k - 1]
            H = pp[k - 2]
            leg = H - L
            if leg > 0:
                bot = L + lo_r * leg
                deep = L + hi_r * leg
                if h[i] >= bot and h[i] <= L + (hi_r + 0.1) * leg and c[i] < deep and h[i] < H:
                    dn[i] = True
    return up, dn


@njit(cache=True)
def elliott(h, l, c, atr, pp, pt, known):
    """(wave-3 long, wave-3 short, wave-2 long, wave-2 short, ABC-end long, ABC-end short)."""
    n = c.size
    w3u = np.zeros(n, np.bool_)
    w3d = np.zeros(n, np.bool_)
    w2u = np.zeros(n, np.bool_)
    w2d = np.zeros(n, np.bool_)
    abu = np.zeros(n, np.bool_)
    abd = np.zeros(n, np.bool_)
    for i in range(1, n):
        k = known[i]
        a = atr[i]
        if k < 4 or not (a > 0):
            continue
        # wave 3: L0 H1 L2 (L2 most recent), L2 > L0, retrace 0.382-0.886, close crosses above H1
        if pt[k - 1] == -1:
            L0 = pp[k - 3]
            H1 = pp[k - 2]
            L2 = pp[k - 1]
            w1 = H1 - L0
            if w1 >= 2.0 * a and L2 > L0:
                r = (H1 - L2) / w1
                if 0.382 <= r <= 0.886 and c[i] > H1 and c[i - 1] <= H1:
                    w3u[i] = True
        else:
            H0 = pp[k - 3]
            L1 = pp[k - 2]
            H2 = pp[k - 1]
            w1 = H0 - L1
            if w1 >= 2.0 * a and H2 < H0:
                r = (H2 - L1) / w1
                if 0.382 <= r <= 0.886 and c[i] < L1 and c[i - 1] >= L1:
                    w3d[i] = True
        # wave 2: impulse L0 -> H1 that took out the previous swing high, now in the 50-61.8% pocket
        if pt[k - 1] == 1 and k >= 3:
            H1 = pp[k - 1]
            L0 = pp[k - 2]
            Hp = pp[k - 3]
            w1 = H1 - L0
            if w1 >= 2.5 * a and H1 > Hp:
                if l[i] <= H1 - 0.5 * w1 and l[i] >= H1 - 0.7 * w1 and c[i] > H1 - 0.618 * w1:
                    w2u[i] = True
        if pt[k - 1] == -1 and k >= 3:
            L1 = pp[k - 1]
            H0 = pp[k - 2]
            Lp = pp[k - 3]
            w1 = H0 - L1
            if w1 >= 2.5 * a and L1 < Lp:
                if h[i] >= L1 + 0.5 * w1 and h[i] <= L1 + 0.7 * w1 and c[i] < L1 + 0.618 * w1:
                    w2d[i] = True
        # ABC: H0 A(low) B(high, below H0); C target = B - (H0 - A)
        if pt[k - 1] == 1:
            H0 = pp[k - 3]
            A = pp[k - 2]
            B = pp[k - 1]
            if B < H0 and B > A:
                C = B - (H0 - A)
                if l[i] <= C + 0.25 * a and c[i] > C and l[i] >= C - 0.75 * a:
                    abu[i] = True
        else:
            L0 = pp[k - 3]
            A = pp[k - 2]
            B = pp[k - 1]
            if B > L0 and B < A:
                C = B + (A - L0)
                if h[i] >= C - 0.25 * a and c[i] < C and h[i] <= C + 0.75 * a:
                    abd[i] = True
    return w3u, w3d, w2u, w2d, abu, abd


@njit(cache=True)
def harmonic(h, l, c, atr, pp, pt, known, kind):
    """kind: 0 Gartley, 1 Bat, 2 Butterfly, 3 Crab, 4 AB=CD.  First touch of D, close back through it."""
    n = c.size
    up = np.zeros(n, np.bool_)
    dn = np.zeros(n, np.bool_)
    used_u = -1
    used_d = -1
    for i in range(n):
        k = known[i]
        a = atr[i]
        if k < 4 or not (a > 0):
            continue
        X = pp[k - 4]
        A = pp[k - 3]
        B = pp[k - 2]
        C = pp[k - 1]
        bull = pt[k - 1] == 1          # X low, A high, B low, C high -> buy at D below
        xa = abs(A - X)
        ab = abs(A - B)
        bc = abs(C - B)
        if xa <= 0 or ab <= 0:
            continue
        r1 = ab / xa
        r2 = bc / ab
        D = np.nan
        if kind == 0 and 0.5 <= r1 <= 0.7 and 0.382 <= r2 <= 0.886:
            D = 0.786
        elif kind == 1 and 0.35 <= r1 <= 0.55 and 0.382 <= r2 <= 0.886:
            D = 0.886
        elif kind == 2 and 0.70 <= r1 <= 0.86 and 0.382 <= r2 <= 0.886:
            D = 1.272
        elif kind == 3 and (0.35 <= r1 <= 0.65 or 0.84 <= r1 <= 0.93) and 0.382 <= r2 <= 0.886:   # crab / deep crab
            D = 1.618
        elif kind == 4 and 0.618 <= r2 <= 0.786:
            D = -1.0
        if np.isnan(D):
            continue
        if bull:
            if not (X < A and B < A and B > X and C > B and C < A):
                if kind != 4 or not (C > B and C < A):
                    continue
            lvl = C - ab if kind == 4 else A - D * xa
            if used_u != k and l[i] <= lvl + 0.5 * a and l[i] >= lvl - 1.5 * a and c[i] > lvl:
                up[i] = True
                used_u = k
        else:
            if not (X > A and B > A and B < X and C < B and C > A):
                if kind != 4 or not (C < B and C > A):
                    continue
            lvl = C + ab if kind == 4 else A + D * xa
            if used_d != k and h[i] >= lvl - 0.5 * a and h[i] <= lvl + 1.5 * a and c[i] < lvl:
                dn[i] = True
                used_d = k
    return up, dn


@njit(cache=True)
def trendlines(h, l, c, atr, pp, pi, pt, pc, known):
    """(bounce long, bounce short, break long, break short) off lines through the last two swings of a side."""
    n = c.size
    bu = np.zeros(n, np.bool_)
    bd = np.zeros(n, np.bool_)
    ku = np.zeros(n, np.bool_)
    kd = np.zeros(n, np.bool_)
    for i in range(1, n):
        k = known[i]
        a = atr[i]
        if k < 3 or not (a > 0):
            continue
        j1 = _last(pp, pt, pc, k, -1, 0)
        j2 = _last(pp, pt, pc, k, -1, 1)
        if j1 >= 0 and j2 >= 0 and pp[j1] > pp[j2] and pi[j1] > pi[j2]:
            s = (pp[j1] - pp[j2]) / (pi[j1] - pi[j2])
            line = pp[j2] + s * (i - pi[j2])
            if l[i] <= line + 0.15 * a and c[i] > line and l[i] >= line - 0.5 * a:
                bu[i] = True
            prev = pp[j2] + s * (i - 1 - pi[j2])
            if c[i] < line - 0.1 * a and c[i - 1] >= prev:
                kd[i] = True           # rising support broken: short
        j1 = _last(pp, pt, pc, k, 1, 0)
        j2 = _last(pp, pt, pc, k, 1, 1)
        if j1 >= 0 and j2 >= 0 and pp[j1] < pp[j2] and pi[j1] > pi[j2]:
            s = (pp[j1] - pp[j2]) / (pi[j1] - pi[j2])
            line = pp[j2] + s * (i - pi[j2])
            if h[i] >= line - 0.15 * a and c[i] < line and h[i] <= line + 0.5 * a:
                bd[i] = True
            prev = pp[j2] + s * (i - 1 - pi[j2])
            if c[i] > line + 0.1 * a and c[i - 1] <= prev:
                ku[i] = True           # falling resistance broken: long
    return bu, bd, ku, kd


@njit(cache=True)
def gann(h, l, c, atr, pp, pi, pt, pc, known, mult):
    """Touch of the mult x (0.25 ATR per bar) angle from the last swing low (long) / high (short)."""
    n = c.size
    up = np.zeros(n, np.bool_)
    dn = np.zeros(n, np.bool_)
    for i in range(n):
        k = known[i]
        a = atr[i]
        if k < 1 or not (a > 0):
            continue
        j = _last(pp, pt, pc, k, -1, 0)
        if j >= 0 and 3 <= i - pi[j] <= 80:
            unit = 0.25 * atr[pi[j]] if atr[pi[j]] > 0 else 0.25 * a
            line = pp[j] + mult * unit * (i - pi[j])
            if l[i] <= line + 0.1 * a and c[i] > line and l[i] >= line - 0.5 * a:
                up[i] = True
        j = _last(pp, pt, pc, k, 1, 0)
        if j >= 0 and 3 <= i - pi[j] <= 80:
            unit = 0.25 * atr[pi[j]] if atr[pi[j]] > 0 else 0.25 * a
            line = pp[j] - mult * unit * (i - pi[j])
            if h[i] >= line - 0.1 * a and c[i] < line and h[i] <= line + 0.5 * a:
                dn[i] = True
    return up, dn


@njit(cache=True)
def sr(h, l, c, atr, pp, pt, pc, known):
    """(support retest long, resistance retest short, flip long, flip short)."""
    n = c.size
    su = np.zeros(n, np.bool_)
    sd = np.zeros(n, np.bool_)
    fu = np.zeros(n, np.bool_)
    fd = np.zeros(n, np.bool_)
    for i in range(1, n):
        k = known[i]
        a = atr[i]
        if k < 2 or not (a > 0):
            continue
        # any of the last 4 swing lows retested as support
        cnt = 0
        for j in range(k - 1, -1, -1):
            if pt[j] == -1:
                lv = pp[j]
                if lv < c[i] and abs(l[i] - lv) <= 0.25 * a and c[i] > lv:
                    su[i] = True
                cnt += 1
                if cnt >= 4:
                    break
        cnt = 0
        for j in range(k - 1, -1, -1):
            if pt[j] == 1:
                lv = pp[j]
                if lv > c[i] and abs(h[i] - lv) <= 0.25 * a and c[i] < lv:
                    sd[i] = True
                cnt += 1
                if cnt >= 4:
                    break
        # role reversal: last swing high that price has closed above, retested
        j = _last(pp, pt, pc, k, 1, 0)
        if j >= 0:
            lv = pp[j]
            if c[i] > lv and l[i] <= lv + 0.2 * a and l[i] >= lv - 0.5 * a and c[i - 1] > lv - 0.2 * a:
                fu[i] = True
        j = _last(pp, pt, pc, k, -1, 0)
        if j >= 0:
            lv = pp[j]
            if c[i] < lv and h[i] >= lv - 0.2 * a and h[i] <= lv + 0.5 * a and c[i - 1] < lv + 0.2 * a:
                fd[i] = True
    return su, sd, fu, fd


@njit(cache=True)
def supply_demand(o, h, l, c, atr, life):
    """First retest of a demand (supply) zone: a small base candle left by a 1.5 ATR displacement."""
    n = c.size
    up = np.zeros(n, np.bool_)
    dn = np.zeros(n, np.bool_)
    dz_lo = np.nan
    dz_hi = np.nan
    dz_t = -1
    sz_lo = np.nan
    sz_hi = np.nan
    sz_t = -1
    for i in range(4, n):
        a = atr[i]
        if not (a > 0):
            continue
        # zone detection: base at j = i-3..i-1 with range < 0.7 ATR, then close[i] beyond base by 1.5 ATR
        for j in range(i - 3, i):
            r = h[j] - l[j]
            if r < 0.7 * a:
                if c[i] - h[j] >= 1.5 * a:
                    dz_lo = l[j]
                    dz_hi = h[j]
                    dz_t = i
                    break
                if l[j] - c[i] >= 1.5 * a:
                    sz_lo = l[j]
                    sz_hi = h[j]
                    sz_t = i
                    break
        if dz_t >= 0 and i > dz_t and i - dz_t <= life:
            if l[i] <= dz_hi and c[i] > dz_lo:
                up[i] = True
                dz_t = -1              # first retest only
            elif c[i] < dz_lo:
                dz_t = -1              # zone broken
        if sz_t >= 0 and i > sz_t and i - sz_t <= life:
            if h[i] >= sz_lo and c[i] < sz_hi:
                dn[i] = True
                sz_t = -1
            elif c[i] > sz_hi:
                sz_t = -1
    return up, dn


@njit(cache=True)
def divergence(l, h, osc, lookback, gap, lo_th, hi_th, hidden):
    """Regular (or hidden) divergence between price extremes and an oscillator."""
    n = l.size
    bull = np.zeros(n, np.bool_)
    bear = np.zeros(n, np.bool_)
    for i in range(lookback, n):
        if np.isnan(osc[i]):
            continue
        jl = -1
        jh = -1
        for j in range(i - lookback, i - gap + 1):
            if jl < 0 or l[j] < l[jl]:
                jl = j
            if jh < 0 or h[j] > h[jh]:
                jh = j
        if np.isnan(osc[jl]) or np.isnan(osc[jh]):
            continue
        if not hidden:
            if l[i] < l[jl] and osc[i] > osc[jl] and osc[jl] < lo_th:
                bull[i] = True
            if h[i] > h[jh] and osc[i] < osc[jh] and osc[jh] > hi_th:
                bear[i] = True
        else:
            if l[i] > l[jl] and osc[i] < osc[jl] and osc[i] < lo_th:
                bull[i] = True
            if h[i] < h[jh] and osc[i] > osc[jh] and osc[i] > hi_th:
                bear[i] = True
    return bull, bear
