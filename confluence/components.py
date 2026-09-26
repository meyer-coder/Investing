"""The confluence vocabulary: every leg a strategy can be built from.

A strategy is a conjunction of legs.  Each leg is one of four kinds:

* **bias** — which side of the market we want to be on (trend, regime, VWAP side)
* **location** — where price is: a level, a zone, a sweep, a breakout
* **trigger** — the bar that says "now": engulfing, pin bar, break of structure
* **filter** — optional extra confirmation: volatility, room to run, candle strength

Every leg returns a ``(long, short)`` pair of boolean arrays evaluated on the
bar's close, with no look-ahead: levels are only used once their window has
closed (see ``bars.py``) and every indicator is causal.

``LEGS[code].text`` is the plain-English rule shown in the explorer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

import numpy as np
from numba import njit

from . import indicators as ind
from .bars import ROUND_STEP, Frame, _tdm, add_levels, higher_tf_trend

Pair = Tuple[np.ndarray, np.ndarray]
WARMUP_BARS = 300


@dataclass(frozen=True)
class Leg:
    code: str
    kind: str          # bias | location | trigger | filter
    label: str         # short name used in strategy names
    text: str          # the long-side rule in plain English (short side mirrors it)
    fn: Callable


LEGS: Dict[str, Leg] = {}


def leg(code: str, kind: str, label: str, text: str):
    def wrap(fn):
        LEGS[code] = Leg(code, kind, label, text, fn)
        return fn
    return wrap


# ------------------------------------------------------------------ context

class Ctx:
    """A frame plus memoised indicators, so 200 strategies share the work."""

    def __init__(self, frame: Frame):
        self.f = frame
        self.memo: Dict[str, object] = {}
        if "pdh" not in frame.cache:
            add_levels(frame)
        self.o, self.h, self.l, self.c = frame.o, frame.h, frame.l, frame.c

    def get(self, key: str, make: Callable):
        if key not in self.memo:
            self.memo[key] = make()
        return self.memo[key]

    # common series
    def ema(self, n):
        return self.get(f"ema{n}", lambda: ind.ema(self.c, n))

    @property
    def atr(self):
        return self.get("atr", lambda: ind.atr(self.h, self.l, self.c, 14))

    @property
    def rsi(self):
        return self.get("rsi", lambda: ind.rsi(self.c, 14))

    @property
    def adx(self):
        return self.get("adx", lambda: ind.adx(self.h, self.l, self.c, 14))

    @property
    def macd(self):
        return self.get("macd", lambda: ind.macd(self.c))

    @property
    def rng(self):
        return self.get("rng", lambda: self.h - self.l)

    def lvl(self, name):
        return self.f.cache[name]

    def leg(self, code: str) -> Pair:
        key = f"leg:{code}"
        if key not in self.memo:
            lo, sh = LEGS[code].fn(self)
            lo = np.asarray(lo, dtype=bool).copy()
            sh = np.asarray(sh, dtype=bool).copy()
            lo[:WARMUP_BARS] = False
            sh[:WARMUP_BARS] = False
            self.memo[key] = (lo, sh)
        return self.memo[key]


# ------------------------------------------------------------------ helpers

def prev(x, k=1):
    return ind.shift(np.asarray(x, dtype=float), k)


def recent(mask, k):
    """True if ``mask`` held on any of the last ``k`` bars, this one included."""
    m = np.asarray(mask, dtype=np.int64)
    cs = np.cumsum(m)
    out = cs.copy()
    out[k:] = cs[k:] - cs[:-k]
    return out > 0


def cross_above(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float) if np.ndim(b) else np.full(a.size, float(b))
    return (a > b) & (prev(a) <= prev(b))


def cross_below(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float) if np.ndim(b) else np.full(a.size, float(b))
    return (a < b) & (prev(a) >= prev(b))


def both(mask) -> Pair:
    m = np.asarray(mask, dtype=bool)
    return m, m


@njit(cache=True)
def ffill_age(v, max_age):
    """Carry the last non-NaN value forward for at most ``max_age`` bars."""
    out = np.full(v.size, np.nan)
    last = np.nan
    age = 10 ** 9
    for i in range(v.size):
        if not np.isnan(v[i]):
            last = v[i]
            age = 0
        else:
            age += 1
        if age <= max_age:
            out[i] = last
    return out


@njit(cache=True)
def _rsi_divergence(l, h, r, lookback, gap):
    n = l.size
    bull = np.zeros(n, dtype=np.bool_)
    bear = np.zeros(n, dtype=np.bool_)
    for i in range(lookback, n):
        jl = -1
        jh = -1
        for j in range(i - lookback, i - gap + 1):
            if jl < 0 or l[j] < l[jl]:
                jl = j
            if jh < 0 or h[j] > h[jh]:
                jh = j
        if np.isnan(r[i]) or np.isnan(r[jl]) or np.isnan(r[jh]):
            continue
        if l[i] < l[jl] and r[i] > r[jl] + 3.0 and r[jl] < 35.0:
            bull[i] = True
        if h[i] > h[jh] and r[i] < r[jh] - 3.0 and r[jh] > 65.0:
            bear[i] = True
    return bull, bear


# ------------------------------------------------------------------ bias legs

@leg("ema200", "bias", "200EMA", "close is above the 200-bar EMA")
def _ema200(x: Ctx) -> Pair:
    e = x.ema(200)
    return x.c > e, x.c < e


@leg("ema_stack", "bias", "EMA stack", "EMA 20 > EMA 50 > EMA 200 (stacked uptrend)")
def _ema_stack(x: Ctx) -> Pair:
    a, b, c = x.ema(20), x.ema(50), x.ema(200)
    return (a > b) & (b > c), (a < b) & (b < c)


@leg("htf", "bias", "HTF trend", "higher-timeframe trend is up: last closed HTF bar (1h for <=15m charts, 4h above) closed above its rising 50 EMA")
def _htf(x: Ctx) -> Pair:
    htf = 60 if x.f.tf <= 15 else 240
    s = x.get(f"htf{htf}", lambda: higher_tf_trend(x.f.clock, x.f, htf))
    return s > 0, s < 0


@leg("daily", "bias", "daily bias", "daily bias is up: yesterday closed above the daily 20 EMA")
def _daily(x: Ctx) -> Pair:
    s = x.lvl("daily_bias")
    return s > 0, s < 0


@leg("vwap_side", "bias", "VWAP side", "close is above session VWAP")
def _vwap_side(x: Ctx) -> Pair:
    v = x.lvl("vwap")
    return x.c > v, x.c < v


@leg("supertrend", "bias", "Supertrend", "Supertrend (10, 3) is long")
def _supertrend(x: Ctx) -> Pair:
    s = x.get("st", lambda: ind.supertrend(x.h, x.l, x.c, ind.atr(x.h, x.l, x.c, 10), 3.0))
    return s > 0, s < 0


@leg("adx", "bias", "ADX>20", "ADX(14) above 20 with +DI above -DI (trending up)")
def _adx(x: Ctx) -> Pair:
    a, p, m = x.adx
    return (a > 20) & (p > m), (a > 20) & (m > p)


@leg("range", "bias", "ranging", "ranging regime: ADX(14) below 20")
def _range(x: Ctx) -> Pair:
    return both(x.adx[0] < 20)


@leg("midnight", "bias", "midnight open", "price is above the 00:00 ET (midnight) open")
def _midnight(x: Ctx) -> Pair:
    m = x.lvl("midnight")
    return x.c > m, x.c < m


@leg("hull", "bias", "Hull slope", "Hull MA(21) is rising")
def _hull(x: Ctx) -> Pair:
    hm = x.get("hma", lambda: ind.hma(x.c, 21))
    return hm > prev(hm), hm < prev(hm)


@leg("macd0", "bias", "MACD>0", "MACD line is above zero")
def _macd0(x: Ctx) -> Pair:
    m = x.macd[0]
    return m > 0, m < 0


@leg("day_open", "bias", "above day open", "price is above today's 18:00 ET open")
def _day_open(x: Ctx) -> Pair:
    d = x.lvl("day_open")
    return x.c > d, x.c < d


@leg("ny_open_side", "bias", "above NY open", "price is above the 09:30 ET open")
def _ny_open_side(x: Ctx) -> Pair:
    d = x.lvl("ny_open")
    return x.c > d, x.c < d


# ------------------------------------------------------------------ location legs

@leg("pb_ema20", "location", "20EMA pullback", "pulled back to tag the 20 EMA within the last 3 bars and closed back above it")
def _pb20(x: Ctx) -> Pair:
    e = x.ema(20)
    return recent(x.l <= e, 3) & (x.c > e), recent(x.h >= e, 3) & (x.c < e)


@leg("pb_ema50", "location", "50EMA pullback", "pulled back to tag the 50 EMA within the last 3 bars and closed back above it")
def _pb50(x: Ctx) -> Pair:
    e = x.ema(50)
    return recent(x.l <= e, 3) & (x.c > e), recent(x.h >= e, 3) & (x.c < e)


@leg("vwap_retest", "location", "VWAP retest", "tagged VWAP within the last 3 bars and closed back above it")
def _vwap_retest(x: Ctx) -> Pair:
    v = x.lvl("vwap")
    return recent(x.l <= v, 3) & (x.c > v), recent(x.h >= v, 3) & (x.c < v)


@leg("vwap_2sd", "location", "VWAP -2σ", "stretched to the -2σ VWAP band within the last 3 bars and closed back inside it")
def _vwap_2sd(x: Ctx) -> Pair:
    v, s = x.lvl("vwap"), x.lvl("vwap_sd")
    lo, hi = v - 2 * s, v + 2 * s
    return recent(x.l <= lo, 3) & (x.c > lo), recent(x.h >= hi, 3) & (x.c < hi)


@leg("vwap_1sd", "location", "VWAP -1σ", "retested the -1σ VWAP band and closed between it and VWAP")
def _vwap_1sd(x: Ctx) -> Pair:
    v, s = x.lvl("vwap"), x.lvl("vwap_sd")
    lo, hi = v - s, v + s
    return (recent(x.l <= lo, 2) & (x.c > lo) & (x.c < v),
            recent(x.h >= hi, 2) & (x.c < hi) & (x.c > v))


def _sweep(x: Ctx, lo_level, hi_level, k=3) -> Pair:
    return (recent(x.l < lo_level, k) & (x.c > lo_level),
            recent(x.h > hi_level, k) & (x.c < hi_level))


@leg("pdl_sweep", "location", "PDL sweep", "swept below the prior-day low within the last 3 bars and closed back above it")
def _pdl_sweep(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("pdl"), x.lvl("pdh"))


@leg("pdh_break", "location", "PDH break", "first close above the prior-day high")
def _pdh_break(x: Ctx) -> Pair:
    return cross_above(x.c, x.lvl("pdh")), cross_below(x.c, x.lvl("pdl"))


@leg("asia_sweep", "location", "Asia sweep", "swept below the Asia-session low (19:00-00:00 ET) and closed back above it")
def _asia_sweep(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("asia_l"), x.lvl("asia_h"))


@leg("asia_break", "location", "Asia break", "first close above the Asia-session high")
def _asia_break(x: Ctx) -> Pair:
    return cross_above(x.c, x.lvl("asia_h")), cross_below(x.c, x.lvl("asia_l"))


@leg("london_sweep", "location", "London sweep", "swept below the London-session low (02:00-05:00 ET) and closed back above it")
def _london_sweep(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("london_l"), x.lvl("london_h"))


@leg("on_sweep", "location", "overnight sweep", "swept below the overnight low (18:00-09:30 ET) and closed back above it")
def _on_sweep(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("on_l"), x.lvl("on_h"))


@leg("on_break", "location", "overnight break", "first close above the overnight high")
def _on_break(x: Ctx) -> Pair:
    return cross_above(x.c, x.lvl("on_h")), cross_below(x.c, x.lvl("on_l"))


@leg("or_break", "location", "ORB", "first close above the 30-minute opening range high (09:30-10:00 ET)")
def _or_break(x: Ctx) -> Pair:
    return cross_above(x.c, x.lvl("or_h")), cross_below(x.c, x.lvl("or_l"))


@leg("or_retest", "location", "ORB retest", "broke the opening range high within the last 12 bars, then retested it and held")
def _or_retest(x: Ctx) -> Pair:
    hi, lo = x.lvl("or_h"), x.lvl("or_l")
    up = recent(cross_above(x.c, hi), 12) & ~cross_above(x.c, hi) & recent(x.l <= hi, 2) & (x.c > hi)
    dn = recent(cross_below(x.c, lo), 12) & ~cross_below(x.c, lo) & recent(x.h >= lo, 2) & (x.c < lo)
    return up, dn


@leg("ib_break", "location", "IB break", "first close above the initial-balance high (09:30-10:30 ET)")
def _ib_break(x: Ctx) -> Pair:
    return cross_above(x.c, x.lvl("ib_h")), cross_below(x.c, x.lvl("ib_l"))


@leg("ib_fade", "location", "IB fade", "failed break below the initial-balance low: closed back inside within 3 bars")
def _ib_fade(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("ib_l"), x.lvl("ib_h"))


@leg("fvg", "location", "FVG retest", "retraced into a bullish fair-value gap formed within the last 10 bars and held its lower edge")
def _fvg(x: Ctx) -> Pair:
    def make():
        h2, l2 = prev(x.h, 2), prev(x.l, 2)
        big = 0.1 * x.atr
        bull = (x.l > h2) & ((x.l - h2) > big)
        bear = (x.h < l2) & ((l2 - x.h) > big)
        btop = prev(ffill_age(np.where(bull, x.l, np.nan), 10))
        bbot = prev(ffill_age(np.where(bull, h2, np.nan), 10))
        stop_ = prev(ffill_age(np.where(bear, x.h, np.nan), 10))
        sbot = prev(ffill_age(np.where(bear, l2, np.nan), 10))
        return ((x.l <= btop) & (x.c > bbot), (x.h >= stop_) & (x.c < sbot))
    return x.get("fvg", make)


@leg("ob", "location", "order block", "retested a bullish order block (the last down candle before a displacement up) within 30 bars")
def _ob(x: Ctx) -> Pair:
    def make():
        rng = x.rng
        disp_up = (rng > 1.5 * x.atr) & (x.c > prev(x.h))
        disp_dn = (rng > 1.5 * x.atr) & (x.c < prev(x.l))
        prev_bear = prev(x.c) < prev(x.o)
        prev_bull = prev(x.c) > prev(x.o)
        bz_top = prev(ffill_age(np.where(disp_up & prev_bear, prev(x.h), np.nan), 30))
        bz_bot = prev(ffill_age(np.where(disp_up & prev_bear, prev(x.l), np.nan), 30))
        sz_bot = prev(ffill_age(np.where(disp_dn & prev_bull, prev(x.l), np.nan), 30))
        sz_top = prev(ffill_age(np.where(disp_dn & prev_bull, prev(x.h), np.nan), 30))
        return ((x.l <= bz_top) & (x.c > bz_bot), (x.h >= sz_bot) & (x.c < sz_top))
    return x.get("ob", make)


@leg("bb_touch", "location", "BB touch", "tagged the lower Bollinger band (20, 2) and closed back inside")
def _bb(x: Ctx) -> Pair:
    mid = ind.sma(x.c, 20)
    sd = x.get("sd20", lambda: ind.rolling_std(x.c, 20))
    lo, hi = mid - 2 * sd, mid + 2 * sd
    return recent(x.l <= lo, 2) & (x.c > lo), recent(x.h >= hi, 2) & (x.c < hi)


@leg("kc_touch", "location", "Keltner touch", "tagged the lower Keltner channel (EMA20 - 2 ATR) and closed back inside")
def _kc(x: Ctx) -> Pair:
    e = x.ema(20)
    lo, hi = e - 2 * x.atr, e + 2 * x.atr
    return recent(x.l <= lo, 2) & (x.c > lo), recent(x.h >= hi, 2) & (x.c < hi)


@leg("turtle", "location", "turtle soup", "false break of the prior 20-bar low: traded below it and closed back above")
def _turtle(x: Ctx) -> Pair:
    ll = prev(ind.rolling_min(x.l, 20))
    hh = prev(ind.rolling_max(x.h, 20))
    return (x.l < ll) & (x.c > ll), (x.h > hh) & (x.c < hh)


@leg("donchian_break", "location", "Donchian break", "first close above the prior 20-bar high")
def _donchian(x: Ctx) -> Pair:
    hh = prev(ind.rolling_max(x.h, 20))
    ll = prev(ind.rolling_min(x.l, 20))
    return cross_above(x.c, hh), cross_below(x.c, ll)


@leg("pivot", "location", "S1/R1 pivot", "bounced off the daily S1 pivot (floor pivots from yesterday)")
def _pivot(x: Ctx) -> Pair:
    s1, r1 = x.lvl("s1"), x.lvl("r1")
    return recent(x.l <= s1, 2) & (x.c > s1), recent(x.h >= r1, 2) & (x.c < r1)


@leg("pw_sweep", "location", "prior-week sweep", "swept below the prior-week low and closed back above it")
def _pw_sweep(x: Ctx) -> Pair:
    return _sweep(x, x.lvl("pwl"), x.lvl("pwh"))


@leg("fib", "location", "Fib 50-61.8", "pulled back into the 50-61.8% retracement of today's up-leg (day range > 2 ATR) and held")
def _fib(x: Ctx) -> Pair:
    hi, lo, op = x.lvl("day_hi"), x.lvl("day_lo"), x.lvl("day_open")
    r = hi - lo
    big = r > 2 * x.atr
    up = big & (x.c > op) & (x.l <= hi - 0.5 * r) & (x.l >= hi - 0.786 * r) & (x.c > hi - 0.618 * r)
    dn = big & (x.c < op) & (x.h >= lo + 0.5 * r) & (x.h <= lo + 0.786 * r) & (x.c < lo + 0.618 * r)
    return up, dn


@leg("round", "location", "round number", "dipped through a round number (e.g. NQ 100s, EURUSD 50 pips) and closed back above it")
def _round(x: Ctx) -> Pair:
    step = ROUND_STEP.get(x.f.feed, 1.0)
    below = np.floor(x.c / step) * step
    above = np.ceil(x.c / step) * step
    return (x.l <= below) & (x.c > below), (x.h >= above) & (x.c < above)


@leg("dbl", "location", "double bottom", "double bottom: retested the low of 5-20 bars ago within 0.25 ATR and closed above it")
def _dbl(x: Ctx) -> Pair:
    ll = prev(ind.rolling_min(x.l, 16), 5)
    hh = prev(ind.rolling_max(x.h, 16), 5)
    tol = 0.25 * x.atr
    return ((np.abs(x.l - ll) <= tol) & (x.c > ll)), ((np.abs(x.h - hh) <= tol) & (x.c < hh))


@leg("gap", "location", "gap fill", "NY opened more than 0.15% below yesterday's close and price has not yet filled the gap")
def _gap(x: Ctx) -> Pair:
    ny, pdc = x.lvl("ny_open"), x.lvl("pdc")
    g = (ny - pdc) / pdc
    return (g < -0.0015) & (x.c < pdc), (g > 0.0015) & (x.c > pdc)


@leg("squeeze", "location", "squeeze release", "Bollinger bands were inside the Keltner channel for 6 of the last 10 bars and just expanded out")
def _squeeze(x: Ctx) -> Pair:
    mid = ind.sma(x.c, 20)
    sd = x.get("sd20", lambda: ind.rolling_std(x.c, 20))
    e = x.ema(20)
    on = (mid + 2 * sd < e + 1.5 * x.atr) & (mid - 2 * sd > e - 1.5 * x.atr)
    cnt = np.convolve(on.astype(float), np.ones(10), mode="full")[: on.size]
    return both((prev(cnt) >= 6) & ~on)


@leg("nr7", "location", "NR7", "the previous bar was the narrowest of the last 7 (compression)")
def _nr7(x: Ctx) -> Pair:
    r = x.rng
    return both(prev(r) <= prev(ind.rolling_min(r, 7)))


@leg("sb_window", "location", "Silver Bullet hour", "bar closes inside an ICT Silver Bullet hour (10:00-11:00 or 14:00-15:00 ET)")
def _sb(x: Ctx) -> Pair:
    t = x.f.tdm_close
    return both(((t > _tdm(10)) & (t <= _tdm(11))) | ((t > _tdm(14)) & (t <= _tdm(15))))


@leg("ny_first30", "location", "NY first 30m", "bar closes in the first 30 minutes of the NY cash session")
def _ny30(x: Ctx) -> Pair:
    t = x.f.tdm_close
    return both((t > _tdm(9, 30)) & (t <= _tdm(10)))


@leg("po3", "location", "power of 3", "London swept the Asia low (manipulation) and NY trades back above the midnight open (distribution)")
def _po3(x: Ctx) -> Pair:
    al, ah = x.lvl("asia_l"), x.lvl("asia_h")
    ll, lh = x.lvl("london_l"), x.lvl("london_h")
    m = x.lvl("midnight")
    ny = x.f.tdm_open >= _tdm(9, 30)
    return ny & (ll < al) & (x.c > m), ny & (lh > ah) & (x.c < m)


# ------------------------------------------------------------------ triggers

@leg("engulf", "trigger", "engulfing", "bullish engulfing candle")
def _engulf(x: Ctx) -> Pair:
    o1, c1 = prev(x.o), prev(x.c)
    up = (c1 < o1) & (x.c > x.o) & (x.c >= o1) & (x.o <= c1)
    dn = (c1 > o1) & (x.c < x.o) & (x.c <= o1) & (x.o >= c1)
    return up, dn


@leg("pin", "trigger", "pin bar", "pin bar: lower wick at least 2x the body and half the range, small upper wick")
def _pin(x: Ctx) -> Pair:
    body = np.abs(x.c - x.o)
    r = np.maximum(x.rng, 1e-12)
    lw = np.minimum(x.o, x.c) - x.l
    uw = x.h - np.maximum(x.o, x.c)
    return ((lw >= 2 * body) & (lw >= 0.5 * r) & (uw <= 0.3 * r),
            (uw >= 2 * body) & (uw >= 0.5 * r) & (lw <= 0.3 * r))


@leg("bos", "trigger", "BOS", "break of structure: close above the highest high of the prior 5 bars")
def _bos(x: Ctx) -> Pair:
    return x.c > prev(ind.rolling_max(x.h, 5)), x.c < prev(ind.rolling_min(x.l, 5))


@leg("ema_cross", "trigger", "9/21 cross", "EMA 9 crosses above EMA 21")
def _ema_cross(x: Ctx) -> Pair:
    a, b = x.ema(9), x.ema(21)
    return cross_above(a, b), cross_below(a, b)


@leg("rsi_reset", "trigger", "RSI reset", "RSI(14) crosses back above 40 (momentum resumes after a reset)")
def _rsi_reset(x: Ctx) -> Pair:
    return cross_above(x.rsi, 40.0), cross_below(x.rsi, 60.0)


@leg("rsi_os", "trigger", "RSI 30 cross", "RSI(14) crosses back above 30 out of oversold")
def _rsi_os(x: Ctx) -> Pair:
    return cross_above(x.rsi, 30.0), cross_below(x.rsi, 70.0)


@leg("macd_cross", "trigger", "MACD cross", "MACD line crosses above its signal line")
def _macd_cross(x: Ctx) -> Pair:
    m, s, _ = x.macd
    return cross_above(m, s), cross_below(m, s)


@leg("inside_break", "trigger", "inside-bar break", "the previous bar was an inside bar and this bar closes above its high")
def _inside(x: Ctx) -> Pair:
    h1, l1, h2, l2 = prev(x.h), prev(x.l), prev(x.h, 2), prev(x.l, 2)
    inside = (h1 < h2) & (l1 > l2)
    return inside & (x.c > h1), inside & (x.c < l1)


@leg("displacement", "trigger", "displacement", "displacement candle: range > 1.5 ATR, bullish, closing in its top quarter")
def _disp(x: Ctx) -> Pair:
    r = x.rng
    big = r > 1.5 * x.atr
    return (big & (x.c > x.o) & (x.c - x.l >= 0.75 * r),
            big & (x.c < x.o) & (x.h - x.c >= 0.75 * r))


@leg("prev_high", "trigger", "close > prior high", "bullish bar closing above the prior bar's high")
def _prev_high(x: Ctx) -> Pair:
    return (x.c > prev(x.h)) & (x.c > x.o), (x.c < prev(x.l)) & (x.c < x.o)


@leg("stoch_cross", "trigger", "Stoch cross", "Stochastic %K crosses above %D below 30")
def _stoch(x: Ctx) -> Pair:
    k, d = x.get("stoch", lambda: ind.stochastic(x.h, x.l, x.c))
    return cross_above(k, d) & (k < 30), cross_below(k, d) & (k > 70)


@leg("ha_flip", "trigger", "HA flip", "Heikin-Ashi candle turns bullish after two bearish ones")
def _ha(x: Ctx) -> Pair:
    ho, hc = x.get("ha", lambda: ind.heikin_ashi(x.o, x.h, x.l, x.c))
    bull = hc > ho
    b1, b2 = prev(bull.astype(float)), prev(bull.astype(float), 2)
    return bull & (b1 == 0) & (b2 == 0), ~bull & (b1 == 1) & (b2 == 1)


@leg("three_bar", "trigger", "3-bar push", "three consecutive bullish bars, each closing higher")
def _three(x: Ctx) -> Pair:
    c1, c2, c3 = prev(x.c), prev(x.c, 2), prev(x.c, 3)
    o1, o2 = prev(x.o), prev(x.o, 2)
    up = (x.c > c1) & (c1 > c2) & (c2 > c3) & (x.c > x.o) & (c1 > o1) & (c2 > o2)
    dn = (x.c < c1) & (c1 < c2) & (c2 < c3) & (x.c < x.o) & (c1 < o1) & (c2 < o2)
    return up, dn


@leg("hull_turn", "trigger", "Hull turn", "Hull MA(21) turns up")
def _hull_turn(x: Ctx) -> Pair:
    hm = x.get("hma", lambda: ind.hma(x.c, 21))
    h1, h2 = prev(hm), prev(hm, 2)
    return (hm > h1) & (h1 <= h2), (hm < h1) & (h1 >= h2)


@leg("st_flip", "trigger", "Supertrend flip", "Supertrend (10, 3) flips to long")
def _st_flip(x: Ctx) -> Pair:
    s = x.get("st", lambda: ind.supertrend(x.h, x.l, x.c, ind.atr(x.h, x.l, x.c, 10), 3.0))
    s1 = prev(s)
    return (s > 0) & (s1 < 0), (s < 0) & (s1 > 0)


@leg("rsi_div", "trigger", "RSI divergence", "bullish RSI divergence: a lower low than 3-20 bars ago while RSI(14) makes a higher low from below 35")
def _rsi_div(x: Ctx) -> Pair:
    return x.get("rsidiv", lambda: _rsi_divergence(x.l, x.h, x.rsi, 20, 3))


@leg("exhaustion", "trigger", "exhaustion flip", "four bearish bars in a row, then a bullish close")
def _exh(x: Ctx) -> Pair:
    bear = (x.c < x.o).astype(float)
    bull = (x.c > x.o).astype(float)
    b4 = sum(prev(bear, k) for k in range(1, 5))
    u4 = sum(prev(bull, k) for k in range(1, 5))
    return (b4 == 4) & (x.c > x.o), (u4 == 4) & (x.c < x.o)


# ------------------------------------------------------------------ filters

@leg("atr_hot", "filter", "ATR expanding", "ATR(14) above its 100-bar average (volatility expanding)")
def _atr_hot(x: Ctx) -> Pair:
    return both(x.atr > ind.sma(np.nan_to_num(x.atr), 100))


@leg("atr_calm", "filter", "ATR calm", "ATR(14) below its 100-bar average (quiet tape)")
def _atr_calm(x: Ctx) -> Pair:
    return both(x.atr < ind.sma(np.nan_to_num(x.atr), 100))


@leg("rsi_room", "filter", "RSI room", "RSI(14) below 65 (room to run)")
def _rsi_room(x: Ctx) -> Pair:
    return x.rsi < 65, x.rsi > 35


@leg("adx_up", "filter", "ADX rising", "ADX(14) higher than 3 bars ago (trend strengthening)")
def _adx_up(x: Ctx) -> Pair:
    a = x.adx[0]
    return both(a > prev(a, 3))


@leg("strong_close", "filter", "strong close", "signal bar closes in the top 30% of its range")
def _strong(x: Ctx) -> Pair:
    r = np.maximum(x.rng, 1e-12)
    return (x.c - x.l) >= 0.7 * r, (x.h - x.c) >= 0.7 * r


@leg("range_spike", "filter", "range spike", "signal bar range is 1.3x the 20-bar average range (activity proxy for volume)")
def _range_spike(x: Ctx) -> Pair:
    return both(x.rng > 1.3 * ind.sma(x.rng, 20))


@leg("not_extended", "filter", "not extended", "close within 1.5 ATR of the 20 EMA (not chasing)")
def _not_ext(x: Ctx) -> Pair:
    return both(np.abs(x.c - x.ema(20)) < 1.5 * x.atr)


def leg_text(code: str, side: str = "long") -> str:
    return LEGS[code].text
