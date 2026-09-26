"""The second confluence vocabulary: structure, patterns, oscillators and volume.

Registers more legs into ``components.LEGS`` (import this module to use them).
Each leg carries a ``cat`` — the confluence category it belongs to, matching
the list the second production run was asked to cover:

    Fibonacci · Breakout · Reversal · Elliott Wave · FVG · Candlestick ·
    Harmonic · Support & Resistance · Dynamic S&R · Trend Lines · Gann ·
    Momentum · Oscillators · Divergence · Volume · Supply & Demand ·
    Market Structure · BOS · CHoCH

Volume is Dukascopy tick volume (the number of price updates per minute),
the standard proxy when exchange volume is not available for the whole
history.  VWAP here is volume-weighted with that tick volume.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from . import indicators as ind
from . import structure as st
from .components import LEGS, Ctx, Leg, both, cross_above, cross_below, prev, recent

CATEGORY: Dict[str, str] = {}


def leg(code: str, kind: str, cat: str, label: str, text: str):
    def wrap(fn):
        LEGS[code] = Leg(code, kind, label, text, fn)
        CATEGORY[code] = cat
        return fn
    return wrap


# ------------------------------------------------------------------ shared structure

def piv(x: Ctx):
    def make():
        pp, pi, pt, pc = st.pivots(x.h, x.l, x.atr, st.PIVOT_ATR)
        lv = st.levels(x.f.n, pp, pi, pt, pc)
        return pp, pi, pt, pc, lv
    return x.get("pivots", make)


def vol(x: Ctx) -> np.ndarray:
    v = getattr(x.f, "v", None)
    return v if v is not None else np.ones(x.f.n)


def vavg(x: Ctx) -> np.ndarray:
    return x.get("vavg", lambda: ind.sma(vol(x), 20))


# ------------------------------------------------------------------ Market structure / BOS / CHoCH

@leg("ms_up", "bias", "Market Structure", "structure up", "market structure is bullish: the last swing high and swing low are both higher than the ones before (HH + HL)")
def _ms(x):
    ms = piv(x)[4][9]
    return ms > 0, ms < 0


@leg("ms_range", "bias", "Market Structure", "structure mixed", "market structure is mixed (neither HH+HL nor LH+LL): a range")
def _msr(x):
    return both(piv(x)[4][9] == 0)


@leg("bos", "trigger", "BOS", "BOS", "break of structure: close through the last confirmed swing high while structure is already bullish")
def _bos2(x):
    lv = piv(x)[4]
    sh1, sl1, ms = lv[0], lv[2], lv[9]
    return (cross_above(x.c, sh1) & (prev(ms) > 0)), (cross_below(x.c, sl1) & (prev(ms) < 0))


@leg("choch", "trigger", "CHoCH", "CHoCH", "change of character: close through the last confirmed swing high while structure was bearish")
def _choch(x):
    lv = piv(x)[4]
    sh1, sl1, ms = lv[0], lv[2], lv[9]
    return (cross_above(x.c, sh1) & (prev(ms) < 0)), (cross_below(x.c, sl1) & (prev(ms) > 0))


@leg("bos_retest", "location", "BOS", "BOS retest", "pullback to the broken swing high within 15 bars of a break of structure, holding above it")
def _bos_rt(x):
    b_up, b_dn = LEGS["bos"].fn(x)
    lv = piv(x)[4]
    sh1, sl1 = lv[0], lv[2]
    # level broken most recently (carry the level of the break forward)
    return (recent(b_up, 15) & ~b_up & (x.l <= prev(sh1) + 0.2 * x.atr) & (x.c > prev(sh1)),
            recent(b_dn, 15) & ~b_dn & (x.h >= prev(sl1) - 0.2 * x.atr) & (x.c < prev(sl1)))


# ------------------------------------------------------------------ Fibonacci

def _fib(x, lo, hi):
    pp, pi, pt, pc, lv = piv(x)
    return st.fib_zone(x.h, x.l, x.c, pp, pt, lv[8], lo, hi)


@leg("fib382", "location", "Fibonacci", "Fib 38.2–50", "pullback into the 38.2–50% retracement of the last completed swing, holding above 50%")
def _f382(x):
    return x.get("fib382", lambda: _fib(x, 0.382, 0.5))


@leg("fib618", "location", "Fibonacci", "Fib 61.8–78.6", "pullback into the 61.8–78.6% retracement of the last completed swing, holding above 78.6%")
def _f618(x):
    return x.get("fib618", lambda: _fib(x, 0.618, 0.786))


@leg("fibgp", "location", "Fibonacci", "golden pocket", "pullback into the golden pocket (50–61.8%) of the last completed swing, holding above 61.8%")
def _fgp(x):
    return x.get("fibgp", lambda: _fib(x, 0.5, 0.618))


# ------------------------------------------------------------------ Elliott

def _ew(x):
    def make():
        pp, pi, pt, pc, lv = piv(x)
        return st.elliott(x.h, x.l, x.c, x.atr, pp, pt, lv[8])
    return x.get("elliott", make)


@leg("ew3", "trigger", "Elliott Wave", "wave-3 break", "Elliott wave 3 starts: after wave 1 (2+ ATR) and a 38.2–88.6% wave 2 that held the wave-1 low, close above the wave-1 high")
def _ew3(x):
    e = _ew(x)
    return e[0], e[1]


@leg("ew2", "location", "Elliott Wave", "wave-2 pocket", "Elliott wave-2 buy: an impulse of 2.5+ ATR that took out the prior swing high, now retraced into 50–61.8%")
def _ew2(x):
    e = _ew(x)
    return e[2], e[3]


@leg("ewabc", "location", "Elliott Wave", "ABC end", "Elliott ABC correction complete: the C leg has matched the A leg (equal legs) and price closes back above it")
def _ewabc(x):
    e = _ew(x)
    return e[4], e[5]


# ------------------------------------------------------------------ Harmonics

def _harm(x, kind):
    def make():
        pp, pi, pt, pc, lv = piv(x)
        return st.harmonic(x.h, x.l, x.c, x.atr, pp, pt, lv[8], kind)
    return x.get(f"harm{kind}", make)


for _k, (_code, _name, _txt) in enumerate([
        ("gartley", "Gartley", "bullish Gartley: AB = 0.618 XA, BC 0.382–0.886 AB, price reaches D at the 0.786 XA retracement and closes back above it"),
        ("bat", "Bat", "bullish Bat: AB 0.382–0.5 XA, D at the 0.886 XA retracement, rejected on the first touch"),
        ("butterfly", "Butterfly", "bullish Butterfly: AB = 0.786 XA, D at the 1.272 XA extension below X, rejected on the first touch"),
        ("crab", "Crab", "bullish Crab: AB 0.382–0.618 XA, D at the 1.618 XA extension, rejected on the first touch"),
        ("abcd", "AB=CD", "bullish AB=CD: BC retraces 61.8–78.6% of AB and CD equals AB; first touch of D rejected")]):
    def _mk(k=_k):
        return lambda x: _harm(x, k)
    LEGS[_code] = Leg(_code, "location", _name, _txt, _mk())
    CATEGORY[_code] = "Harmonic"


# ------------------------------------------------------------------ Trend lines, Gann, S/R

def _tl(x):
    def make():
        pp, pi, pt, pc, lv = piv(x)
        return st.trendlines(x.h, x.l, x.c, x.atr, pp, pi, pt, pc, lv[8])
    return x.get("tl", make)


@leg("tl_bounce", "location", "Trend Lines", "trendline bounce", "bounce off the rising trend line drawn through the last two higher swing lows")
def _tlb(x):
    t = _tl(x)
    return t[0], t[1]


@leg("tl_break", "trigger", "Trend Lines", "trendline break", "close through the falling trend line drawn through the last two lower swing highs")
def _tlk(x):
    t = _tl(x)
    return t[2], t[3]


def _gn(x, mult):
    def make():
        pp, pi, pt, pc, lv = piv(x)
        return st.gann(x.h, x.l, x.c, x.atr, pp, pi, pt, pc, lv[8], mult)
    return x.get(f"gann{mult}", make)


@leg("gann1x1", "location", "Gann", "Gann 1x1", "touch of the Gann 1x1 angle from the last swing low (1 unit = 0.25 ATR per bar) and close above it")
def _g11(x):
    return _gn(x, 1.0)


@leg("gann2x1", "location", "Gann", "Gann 2x1", "touch of the steeper Gann 2x1 angle from the last swing low and close above it")
def _g21(x):
    return _gn(x, 2.0)


def _sr(x):
    def make():
        pp, pi, pt, pc, lv = piv(x)
        return st.sr(x.h, x.l, x.c, x.atr, pp, pt, pc, lv[8])
    return x.get("sr", make)


@leg("sr_retest", "location", "Support & Resistance", "swing S/R", "retest of one of the last four swing lows as support (within 0.25 ATR) and close above it")
def _srr(x):
    s = _sr(x)
    return s[0], s[1]


@leg("sr_flip", "location", "Support & Resistance", "S/R flip", "role reversal: the last swing high, once broken, is retested from above and holds as support")
def _srf(x):
    s = _sr(x)
    return s[2], s[3]


# ------------------------------------------------------------------ Dynamic S/R

@leg("ema200_touch", "location", "Dynamic S&R", "200EMA touch", "tagged the 200 EMA within the last 2 bars and closed above it")
def _e200(x):
    e = x.ema(200)
    return recent(x.l <= e, 2) & (x.c > e), recent(x.h >= e, 2) & (x.c < e)


@leg("bbmid_touch", "location", "Dynamic S&R", "BB mid touch", "pulled back to the Bollinger middle band (20 SMA) and closed above it")
def _bbm(x):
    m = ind.sma(x.c, 20)
    return recent(x.l <= m, 2) & (x.c > m), recent(x.h >= m, 2) & (x.c < m)


@leg("vwapv_retest", "location", "Dynamic S&R", "VWAP retest", "retest of the session VWAP (weighted by tick volume) and close above it")
def _vwv(x):
    v = x.get("vwapv", lambda: _vwap_volume(x))
    return recent(x.l <= v, 3) & (x.c > v), recent(x.h >= v, 3) & (x.c < v)


def _vwap_volume(x):
    f = x.f
    ck = f.clock
    m = ck.m
    vv = getattr(m, "v", None)
    if vv is None:
        return f.cache["vwap"]
    tp = (m.h + m.l + m.c) / 3.0
    w = np.maximum(vv, 1e-9)
    new_day = np.concatenate(([True], np.diff(ck.day) != 0))
    grp = np.cumsum(new_day) - 1

    def seg(a):
        cs = np.cumsum(a)
        base = np.concatenate(([0.0], cs))[np.flatnonzero(new_day)]
        return cs - base[grp]
    s0, s1 = seg(w), seg(w * tp)
    at = f.hi - 1
    return s1[at] / s0[at]


# ------------------------------------------------------------------ Supply & demand, FVG variants, breakout

@leg("sd_zone", "location", "Supply & Demand", "demand zone", "first return to a demand zone: a small base candle that price left with a 1.5 ATR displacement (valid 60 bars)")
def _sd(x):
    return x.get("sdz", lambda: st.supply_demand(x.o, x.h, x.l, x.c, x.atr, 60))


@leg("ifvg", "location", "FVG", "inverse FVG", "inverse FVG: a bearish fair-value gap that price closed through, retested from above as support")
def _ifvg(x):
    def make():
        h2, l2 = prev(x.h, 2), prev(x.l, 2)
        bear = (x.h < l2) & ((l2 - x.h) > 0.1 * x.atr)
        bull = (x.l > h2) & ((x.l - h2) > 0.1 * x.atr)
        from .components import ffill_age
        btop = prev(ffill_age(np.where(bear, l2, np.nan), 20))   # top of the bearish gap
        bbot = prev(ffill_age(np.where(bear, x.h, np.nan), 20))
        stop_ = prev(ffill_age(np.where(bull, x.l, np.nan), 20))
        sbot = prev(ffill_age(np.where(bull, h2, np.nan), 20))
        inv_up = recent(x.c > btop, 10) & (x.l <= btop) & (x.c > bbot) & (x.c > btop)
        inv_dn = recent(x.c < sbot, 10) & (x.h >= sbot) & (x.c < stop_) & (x.c < sbot)
        return inv_up, inv_dn
    return x.get("ifvg", make)


@leg("box_break", "trigger", "Breakout", "range-box break", "close above a tight 12-bar box (box height at most 2.5 ATR)")
def _box(x):
    hh = prev(ind.rolling_max(x.h, 12))
    ll = prev(ind.rolling_min(x.l, 12))
    tight = (hh - ll) <= 2.5 * x.atr
    return tight & (x.c > hh), tight & (x.c < ll)


@leg("vol_breakout", "trigger", "Breakout", "volatility breakout", "bar closes at least 1 ATR above the prior close (volatility expansion)")
def _vbo(x):
    return x.c - prev(x.c) >= x.atr, prev(x.c) - x.c >= x.atr


# ------------------------------------------------------------------ Reversal

@leg("key_rev", "trigger", "Reversal", "key reversal", "key reversal: a new low below the prior bar, then a close above the prior bar's high")
def _krev(x):
    return (x.l < prev(x.l)) & (x.c > prev(x.h)), (x.h > prev(x.h)) & (x.c < prev(x.l))


@leg("climax_rev", "trigger", "Reversal", "climax reversal", "selling climax: range above 2 ATR with the close in the top 40% of the bar")
def _crev(x):
    r = np.maximum(x.rng, 1e-12)
    big = x.rng > 2 * x.atr
    return big & ((x.c - x.l) >= 0.6 * r), big & ((x.h - x.c) >= 0.6 * r)


# ------------------------------------------------------------------ Candlesticks

def _body(x):
    return np.abs(x.c - x.o)


@leg("hammer", "trigger", "Candlestick", "hammer", "hammer after a 3-bar decline: lower wick at least 2x the body, upper wick under a quarter of the range")
def _hammer(x):
    r = np.maximum(x.rng, 1e-12)
    lw = np.minimum(x.o, x.c) - x.l
    uw = x.h - np.maximum(x.o, x.c)
    b = _body(x)
    dec, inc = x.c < prev(x.c, 3), x.c > prev(x.c, 3)
    return (lw >= 2 * b) & (uw <= 0.25 * r) & dec, (uw >= 2 * b) & (lw <= 0.25 * r) & inc


@leg("morning_star", "trigger", "Candlestick", "morning star", "morning star: a large bearish bar, a small-bodied bar, then a bullish bar closing above the first bar's midpoint")
def _mstar(x):
    o2, c2, o1, c1 = prev(x.o, 2), prev(x.c, 2), prev(x.o, 1), prev(x.c, 1)
    a = x.atr
    big_dn, big_up = (o2 - c2) >= 0.6 * a, (c2 - o2) >= 0.6 * a
    small = np.abs(c1 - o1) <= 0.3 * a
    return (big_dn & small & (x.c > x.o) & (x.c > (o2 + c2) / 2),
            big_up & small & (x.c < x.o) & (x.c < (o2 + c2) / 2))


@leg("harami", "trigger", "Candlestick", "harami", "bullish harami: a small bullish body inside the previous large bearish body")
def _harami(x):
    o1, c1 = prev(x.o), prev(x.c)
    big = np.abs(c1 - o1) >= 0.6 * x.atr
    inside = (np.maximum(x.o, x.c) <= np.maximum(o1, c1)) & (np.minimum(x.o, x.c) >= np.minimum(o1, c1))
    return big & (c1 < o1) & (x.c > x.o) & inside, big & (c1 > o1) & (x.c < x.o) & inside


@leg("tweezer", "trigger", "Candlestick", "tweezer bottom", "tweezer bottom: two lows within 0.05 ATR, bearish bar then bullish bar")
def _tweez(x):
    tol = 0.05 * x.atr
    return ((np.abs(x.l - prev(x.l)) <= tol) & (prev(x.c) < prev(x.o)) & (x.c > x.o),
            (np.abs(x.h - prev(x.h)) <= tol) & (prev(x.c) > prev(x.o)) & (x.c < x.o))


@leg("marubozu", "trigger", "Candlestick", "marubozu", "bullish marubozu: body at least 90% of a range of 1+ ATR")
def _maru(x):
    r = np.maximum(x.rng, 1e-12)
    full = (_body(x) >= 0.9 * r) & (x.rng >= x.atr)
    return full & (x.c > x.o), full & (x.c < x.o)


@leg("soldiers", "trigger", "Candlestick", "three soldiers", "three white soldiers: three bullish bars, each closing higher and in the top 30% of its range")
def _sold(x):
    r = np.maximum(x.rng, 1e-12)
    top = (x.c - x.l) >= 0.7 * r
    bot = (x.h - x.c) >= 0.7 * r
    bull = (x.c > x.o) & top
    bear = (x.c < x.o) & bot
    up = bull & (prev(bull.astype(float)) == 1) & (prev(bull.astype(float), 2) == 1) & (x.c > prev(x.c)) & (prev(x.c) > prev(x.c, 2))
    dn = bear & (prev(bear.astype(float)) == 1) & (prev(bear.astype(float), 2) == 1) & (x.c < prev(x.c)) & (prev(x.c) < prev(x.c, 2))
    return up, dn


@leg("doji_ext", "location", "Candlestick", "doji at extreme", "the previous bar was a doji (body under 10% of range) at a 10-bar low")
def _doji(x):
    r = np.maximum(x.rng, 1e-12)
    doji = _body(x) <= 0.1 * r
    lo = x.l <= ind.rolling_min(x.l, 10)
    hi = x.h >= ind.rolling_max(x.h, 10)
    return prev((doji & lo).astype(float)) == 1, prev((doji & hi).astype(float)) == 1


# ------------------------------------------------------------------ Momentum & oscillators

@leg("roc_cross", "trigger", "Momentum", "ROC cross", "10-bar rate of change crosses above zero")
def _roc(x):
    r = ind.returns(x.c, 10) if hasattr(ind, "returns") else x.c / prev(x.c, 10) - 1
    return cross_above(r, 0.0), cross_below(r, 0.0)


@leg("macd_hist_turn", "trigger", "Momentum", "MACD hist turn", "MACD histogram turns up while below zero")
def _mht(x):
    hst = x.macd[2]
    h1, h2 = prev(hst), prev(hst, 2)
    return (hst > h1) & (h1 <= h2) & (hst < 0), (hst < h1) & (h1 >= h2) & (hst > 0)


@leg("di_cross", "trigger", "Momentum", "+DI cross", "+DI crosses above -DI with ADX above 18")
def _dic(x):
    a, p, m = x.adx
    return cross_above(p, m) & (a > 18), cross_below(p, m) & (a > 18)


@leg("mom_up", "bias", "Momentum", "momentum up", "20-bar momentum positive and rising (close above the close 20 bars ago, and above 5 bars ago)")
def _mom(x):
    return (x.c > prev(x.c, 20)) & (x.c > prev(x.c, 5)), (x.c < prev(x.c, 20)) & (x.c < prev(x.c, 5))


def _cci(x):
    def make():
        tp = (x.h + x.l + x.c) / 3.0
        m = ind.sma(tp, 20)
        dev = ind.sma(np.abs(tp - np.nan_to_num(m)), 20)
        with np.errstate(divide="ignore", invalid="ignore"):
            return (tp - m) / (0.015 * dev)
    return x.get("cci", make)


@leg("cci_cross", "trigger", "Oscillators", "CCI -100 cross", "CCI(20) crosses back above -100")
def _ccic(x):
    c = _cci(x)
    return cross_above(c, -100.0), cross_below(c, 100.0)


@leg("willr_cross", "trigger", "Oscillators", "%R -80 cross", "Williams %R(14) crosses back above -80")
def _wr(x):
    hh, ll = ind.rolling_max(x.h, 14), ind.rolling_min(x.l, 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        w = -100 * (hh - x.c) / (hh - ll)
    return cross_above(w, -80.0), cross_below(w, -20.0)


@leg("stochrsi", "trigger", "Oscillators", "StochRSI cross", "Stochastic RSI (14) crosses up out of the bottom 20%")
def _srsi(x):
    r = x.rsi
    hh, ll = ind.rolling_max(np.nan_to_num(r, nan=50), 14), ind.rolling_min(np.nan_to_num(r, nan=50), 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(hh > ll, (r - ll) / (hh - ll), 0.5)
    return cross_above(k, 0.2), cross_below(k, 0.8)


@leg("rsi_os_zone", "filter", "Oscillators", "RSI < 40", "RSI(14) below 40 on the signal bar (oversold side)")
def _rsio(x):
    return x.rsi < 40, x.rsi > 60


@leg("mfi_cross", "trigger", "Volume", "MFI 20 cross", "Money Flow Index (14, tick volume) crosses back above 20")
def _mfi(x):
    def make():
        tp = (x.h + x.l + x.c) / 3.0
        mf = tp * vol(x)
        up = np.where(tp > prev(tp), mf, 0.0)
        dn = np.where(tp < prev(tp), mf, 0.0)
        su, sd = ind.sma(np.nan_to_num(up), 14), ind.sma(np.nan_to_num(dn), 14)
        with np.errstate(divide="ignore", invalid="ignore"):
            return 100 - 100 / (1 + su / np.maximum(sd, 1e-12))
    m = x.get("mfi", make)
    return cross_above(m, 20.0), cross_below(m, 80.0)


# ------------------------------------------------------------------ Divergence

def _div(x, key, osc, lo, hi, hidden=False):
    return x.get(key, lambda: st.divergence(x.l, x.h, osc, 20, 3, lo, hi, hidden))


@leg("macd_div", "trigger", "Divergence", "MACD divergence", "bullish MACD divergence: a lower low than 3-20 bars ago with a higher MACD low, MACD below zero")
def _mdiv(x):
    return _div(x, "mdiv", x.macd[0], 0.0, 0.0)


@leg("stoch_div", "trigger", "Divergence", "Stoch divergence", "bullish stochastic divergence: a lower low with a higher %K low from below 25")
def _sdiv(x):
    k, d = x.get("stoch", lambda: ind.stochastic(x.h, x.l, x.c))
    return _div(x, "sdiv", k, 25.0, 75.0)


@leg("hidden_div", "trigger", "Divergence", "hidden divergence", "hidden bullish divergence (trend continuation): a higher low with a lower RSI low, RSI below 45")
def _hdiv(x):
    return _div(x, "hdiv", x.rsi, 45.0, 55.0, True)


@leg("obv_div", "trigger", "Divergence", "OBV divergence", "bullish OBV divergence: a lower low while on-balance volume (tick volume) makes a higher low")
def _odiv(x):
    obv = x.get("obv", lambda: np.cumsum(np.sign(np.nan_to_num(x.c - prev(x.c))) * vol(x)))
    return x.get("odiv", lambda: st.divergence(x.l, x.h, obv, 20, 3, 1e18, -1e18, False))


# ------------------------------------------------------------------ Volume

@leg("vol_spike", "filter", "Volume", "volume spike", "signal-bar tick volume at least 2x its 20-bar average")
def _vsp(x):
    return both(vol(x) > 2.0 * vavg(x))


@leg("vol_confirm", "filter", "Volume", "volume confirm", "signal-bar tick volume at least 1.3x its 20-bar average")
def _vcf(x):
    return both(vol(x) > 1.3 * vavg(x))


@leg("vol_dryup", "location", "Volume", "volume dry-up", "pullback on drying volume: the last 3 bars all below 0.8x average tick volume")
def _vdu(x):
    low = (vol(x) < 0.8 * vavg(x)).astype(float)
    ok = (prev(low) == 1) & (prev(low, 2) == 1) & (prev(low, 3) == 1)
    return both(ok)


@leg("vol_climax", "trigger", "Volume", "volume climax", "volume climax reversal: tick volume above 3x average and a lower wick of at least half the range")
def _vcl(x):
    r = np.maximum(x.rng, 1e-12)
    spike = vol(x) > 3.0 * vavg(x)
    lw = np.minimum(x.o, x.c) - x.l
    uw = x.h - np.maximum(x.o, x.c)
    return spike & (lw >= 0.5 * r), spike & (uw >= 0.5 * r)


@leg("obv_up", "bias", "Volume", "OBV rising", "on-balance volume (tick volume) above its 20-bar EMA")
def _obv(x):
    obv = x.get("obv", lambda: np.cumsum(np.sign(np.nan_to_num(x.c - prev(x.c))) * vol(x)))
    e = x.get("obv_ema", lambda: ind.ema(obv, 20))
    return obv > e, obv < e


# Categories for the legs that already existed.
CATEGORY.update({
    "fvg": "FVG", "displacement": "FVG", "ob": "Supply & Demand",
    "donchian_break": "Breakout", "pdh_break": "Breakout", "or_break": "Breakout", "ib_break": "Breakout",
    "asia_break": "Breakout", "on_break": "Breakout", "squeeze": "Breakout", "nr7": "Breakout",
    "turtle": "Reversal", "exhaustion": "Reversal", "pdl_sweep": "Reversal", "asia_sweep": "Reversal",
    "london_sweep": "Reversal", "on_sweep": "Reversal", "ib_fade": "Reversal",
    "engulf": "Candlestick", "pin": "Candlestick", "inside_break": "Candlestick", "three_bar": "Candlestick",
    "pivot": "Support & Resistance", "round": "Support & Resistance", "pw_sweep": "Support & Resistance",
    "dbl": "Support & Resistance",
    "pb_ema20": "Dynamic S&R", "pb_ema50": "Dynamic S&R", "vwap_retest": "Dynamic S&R", "bb_touch": "Dynamic S&R",
    "kc_touch": "Dynamic S&R",
    "macd_cross": "Momentum", "ema_cross": "Momentum", "adx": "Momentum", "hull_turn": "Momentum",
    "st_flip": "Momentum", "macd0": "Momentum",
    "rsi_os": "Oscillators", "rsi_reset": "Oscillators", "stoch_cross": "Oscillators",
    "rsi_div": "Divergence", "fib": "Fibonacci",
    "range_spike": "Volume",
    "ema200": "Dynamic S&R", "ema_stack": "Dynamic S&R", "htf": "Market Structure", "daily": "Market Structure",
    "vwap_side": "Dynamic S&R", "supertrend": "Momentum", "range": "Market Structure",
    "atr_hot": "Breakout", "atr_calm": "Reversal", "rsi_room": "Oscillators", "adx_up": "Momentum",
    "strong_close": "Candlestick", "not_extended": "Dynamic S&R", "prev_high": "Candlestick",
})
