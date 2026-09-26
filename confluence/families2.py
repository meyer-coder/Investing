"""Production run 2: ~20,000 strategies on the Topstep / FundedNext futures universe.

Families are grouped by the confluence they are built around — the 19
categories this run was asked to cover — and each family combines that
anchor with at least one other kind of confluence (structure, trend,
volume, candles ...).  The generator crosses every family with

    underlying x timeframe (1m-4h) x session x entry x stop x target x extra filter

and deals underlyings round-robin, so every family is tested on every market.
"""
from __future__ import annotations

import hashlib
import random
from typing import List, Optional, Sequence

from . import components2  # noqa: F401  (registers the new legs)
from .bars import SESSION_ORDER
from .components import LEGS
from .families import ENTRIES, FAMILY_BY_NUM, STOPS, TARGETS, Family, Strategy, _name
from .futures import UNDERLYING_ORDER

CATEGORIES = ["Fibonacci", "Breakout", "Reversal", "Elliott Wave", "FVG", "Candlestick", "Harmonic",
              "Support & Resistance", "Dynamic S&R", "Trend Lines", "Gann", "Momentum", "Oscillators",
              "Divergence", "Volume", "Supply & Demand", "Market Structure", "BOS", "CHoCH"]
GROUPS2 = CATEGORIES + ["Control"]

TIMEFRAMES2 = [1, 2, 3, 5, 10, 15, 30, 60, 120, 240]
TF_WEIGHT2 = {1: 0.05, 2: 0.06, 3: 0.07, 5: 0.14, 10: 0.12, 15: 0.16, 30: 0.14, 60: 0.12, 120: 0.08, 240: 0.06}

TX = ("atr_hot", "rsi_room", "adx_up", "vol_confirm", "not_extended", "strong_close")
RX = ("atr_calm", "rsi_os_zone", "vol_spike", "strong_close", "vol_confirm")
BX = ("atr_hot", "vol_confirm", "adx_up", "strong_close")

_F = []


def fam(cat: str, name: str, legs, extras, thesis: str):
    _F.append((cat, name, tuple(legs), tuple(extras), thesis))


# Fibonacci
fam("Fibonacci", "Fib 61.8 Engulf in Uptrend", ["ms_up", "fib618", "engulf"], TX, "Deep 61.8–78.6% pullbacks inside a bullish structure, confirmed by an engulfing candle.")
fam("Fibonacci", "Golden Pocket RSI Divergence", ["fibgp", "rsi_div"], RX, "Price reaches the 50–61.8% pocket while RSI stops confirming the push.")
fam("Fibonacci", "Fib 38.2 Trend Continuation", ["ema_stack", "fib382", "prev_high"], TX, "Shallow pullbacks in strong stacked-EMA trends resume quickly.")
fam("Fibonacci", "Golden Pocket Pin at 200EMA Side", ["ema200", "fibgp", "pin"], TX, "Golden-pocket rejection wick with the 200 EMA below.")
fam("Fibonacci", "Fib 61.8 Stochastic Turn", ["fib618", "stoch_cross"], RX, "Deep retracement plus stochastic turning up from oversold.")
# Breakout
fam("Breakout", "Range Box Break with Volume", ["htf", "box_break", "vol_confirm"], BX, "A tight box breaks in the higher-timeframe direction on rising tick volume.")
fam("Breakout", "Volatility Breakout in Structure", ["ms_up", "vol_breakout"], BX, "A 1-ATR expansion bar in the direction of market structure.")
fam("Breakout", "Donchian Break OBV ADX", ["obv_up", "adx", "donchian_break"], BX, "20-bar breakout backed by trend strength and on-balance volume.")
fam("Breakout", "Squeeze Box Break", ["squeeze", "box_break"], BX, "Volatility compression released through a tight range box.")
fam("Breakout", "Falling Trendline Break Momentum", ["mom_up", "tl_break"], BX, "A falling trend line breaks while 20-bar momentum is already positive.")
# Reversal
fam("Reversal", "Key Reversal at Swing Support", ["sr_retest", "key_rev"], RX, "An outside key-reversal bar off a prior swing low.")
fam("Reversal", "Climax Reversal Oversold", ["rsi_os_zone", "climax_rev"], RX, "A 2-ATR selling climax that closes strong while RSI is oversold.")
fam("Reversal", "Turtle Soup Volume Spike", ["turtle", "vol_spike", "prev_high"], RX, "False break of the 20-bar low on a volume spike.")
fam("Reversal", "Bollinger Exhaustion Oversold", ["bb_touch", "exhaustion", "rsi_os_zone"], RX, "Four bars down into the lower band, then the first bullish close.")
fam("Reversal", "Liquidity Sweep Key Reversal", ["pdl_sweep", "key_rev"], RX, "Yesterday's low is swept and reclaimed with a key-reversal bar.")
# Elliott
fam("Elliott Wave", "Elliott Wave-3 Breakout", ["ew3"], BX, "Buy the break of the wave-1 high after a valid wave 2.")
fam("Elliott Wave", "Elliott Wave-3 with HTF Trend", ["htf", "ew3"], BX, "Wave-3 breakouts only when the higher timeframe agrees.")
fam("Elliott Wave", "Elliott Wave-2 Pocket Engulf", ["ew2", "engulf"], TX, "Wave-2 golden-pocket pullback after an impulse that broke structure, with an engulfing candle.")
fam("Elliott Wave", "Elliott ABC End 200EMA", ["ema200", "ewabc", "prev_high"], RX, "An equal-legs ABC correction completes above the 200 EMA.")
# FVG
fam("FVG", "FVG Retest in Bullish Structure", ["ms_up", "fvg", "prev_high"], TX, "Imbalances left by a bullish structure get defended.")
fam("FVG", "Inverse FVG Retest", ["ifvg", "prev_high"], TX, "A bearish gap that price closed through flips into support.")
fam("FVG", "FVG in the Golden Pocket", ["fvg", "fibgp"], TX, "A fair-value gap that sits inside the 50–61.8% pocket.")
fam("FVG", "Inverse FVG in Structure", ["ms_up", "ifvg"], TX, "Inverse-FVG retests only in a bullish structure.")
# Candlestick
fam("Candlestick", "Hammer at Demand", ["sd_zone", "hammer"], RX, "A hammer on the first return to a demand zone.")
fam("Candlestick", "Morning Star at Swing Support", ["sr_retest", "morning_star"], RX, "Three-bar morning star off a prior swing low.")
fam("Candlestick", "Engulfing at 200EMA", ["ema200_touch", "engulf"], TX, "Engulfing candle on a 200 EMA retest.")
fam("Candlestick", "Three Soldiers OBV", ["obv_up", "soldiers"], BX, "Three white soldiers with on-balance volume rising.")
fam("Candlestick", "Harami Oversold in Structure", ["ms_up", "harami", "rsi_os_zone"], RX, "Bullish harami at oversold RSI inside a bullish structure.")
fam("Candlestick", "Tweezer Bottom at VWAP", ["vwapv_retest", "tweezer"], TX, "Tweezer bottom on a tick-volume VWAP retest.")
fam("Candlestick", "Doji at Extreme Follow-through", ["doji_ext", "prev_high"], RX, "A doji at a 10-bar low followed by a bar through its high.")
# Harmonic
fam("Harmonic", "Gartley PRZ Rejection", ["gartley"], RX, "Bullish Gartley completes and D is rejected on the first touch.")
fam("Harmonic", "Bat PRZ Rejection", ["bat"], RX, "Bat pattern D at the 0.886 retracement, first-touch rejection.")
fam("Harmonic", "Butterfly PRZ Rejection", ["butterfly"], RX, "Butterfly D at the 1.272 extension, first-touch rejection.")
fam("Harmonic", "Crab PRZ Rejection", ["crab"], RX, "Crab D at the 1.618 extension, first-touch rejection.")
fam("Harmonic", "AB=CD above 200EMA", ["abcd", "ema200"], RX, "Equal-legs AB=CD pullback that completes above the 200 EMA.")
# Support & resistance
fam("Support & Resistance", "Swing Support Engulf", ["sr_retest", "engulf"], RX, "Prior swing low holds as support with an engulfing candle.")
fam("Support & Resistance", "S/R Flip with Momentum", ["sr_flip", "mom_up", "prev_high"], TX, "Broken swing high retested as support with momentum positive.")
fam("Support & Resistance", "Round Number at Swing Support", ["round", "sr_retest"], RX, "A round number that lines up with a prior swing low.")
fam("Support & Resistance", "Daily Pivot Pin", ["pivot", "pin"], RX, "Floor-pivot S1 rejected by a pin bar.")
# Dynamic S&R
fam("Dynamic S&R", "200EMA Touch in Structure", ["ema200_touch", "ms_up", "prev_high"], TX, "200 EMA retest inside a bullish structure.")
fam("Dynamic S&R", "Tick-Volume VWAP Retest OBV", ["vwapv_retest", "obv_up", "prev_high"], TX, "VWAP (tick-volume weighted) retest with OBV rising.")
fam("Dynamic S&R", "BB Mid Pullback ADX", ["adx", "bbmid_touch", "prev_high"], TX, "Trend pullbacks to the Bollinger mid-band.")
fam("Dynamic S&R", "20EMA Pullback on Dry Volume", ["ema_stack", "pb_ema20", "vol_dryup"], TX, "Quiet-volume pullback to the 20 EMA in a stacked trend.")
# Trend lines
fam("Trend Lines", "Trendline Bounce Pin", ["tl_bounce", "pin"], TX, "Pin-bar rejection off a rising trend line.")
fam("Trend Lines", "Trendline Bounce in Structure", ["ms_up", "tl_bounce"], TX, "Trend-line bounces only in a bullish structure.")
fam("Trend Lines", "Trendline Break with Volume", ["tl_break", "vol_confirm"], BX, "A falling trend line breaks on above-average tick volume.")
fam("Trend Lines", "Trendline Break OBV", ["tl_break", "obv_up"], BX, "Trend-line break confirmed by rising on-balance volume.")
# Gann
fam("Gann", "Gann 1x1 in Structure", ["ms_up", "gann1x1"], TX, "The 1x1 angle from the last swing low holds inside a bullish structure.")
fam("Gann", "Gann 2x1 Support Follow-through", ["gann2x1", "prev_high"], TX, "Steep 2x1 angle holds and the next bar follows through.")
fam("Gann", "Gann 1x1 Dry Volume", ["gann1x1", "vol_dryup"], TX, "Quiet pullback onto the 1x1 angle.")
fam("Gann", "Gann 2x1 with HTF", ["htf", "gann2x1"], TX, "2x1 angle support with the higher timeframe trending.")
# Momentum
fam("Momentum", "ROC Zero Cross in Structure", ["ms_up", "roc_cross"], TX, "Rate of change turns positive inside a bullish structure.")
fam("Momentum", "MACD Histogram Turn above 200EMA", ["ema200", "macd_hist_turn"], TX, "MACD histogram turns up from below zero above the 200 EMA.")
fam("Momentum", "DI Cross with Volume", ["di_cross", "vol_confirm"], BX, "+DI crosses -DI on above-average volume.")
fam("Momentum", "Momentum BB Mid Pullback", ["mom_up", "bbmid_touch"], TX, "Positive momentum with a pullback to the mid-band.")
# Oscillators
fam("Oscillators", "CCI -100 Cross above 200EMA", ["ema200", "cci_cross"], TX, "CCI leaves the oversold zone in an uptrend.")
fam("Oscillators", "Williams %R in Structure", ["ms_up", "willr_cross"], TX, "Williams %R turns up from -80 in a bullish structure.")
fam("Oscillators", "StochRSI above VWAP", ["vwap_side", "stochrsi"], TX, "Stochastic RSI turns up while price holds above VWAP.")
fam("Oscillators", "RSI 30 Cross at Swing Support", ["sr_retest", "rsi_os"], RX, "RSI leaves oversold on a prior swing low.")
# Divergence
fam("Divergence", "MACD Divergence at Lower Band", ["bb_touch", "macd_div"], RX, "MACD divergence on a lower Bollinger band tag.")
fam("Divergence", "Stochastic Divergence Oversold", ["stoch_div", "rsi_os_zone"], RX, "Stochastic divergence with RSI under 40.")
fam("Divergence", "Hidden Divergence in Structure", ["ms_up", "hidden_div"], TX, "Hidden bullish divergence: continuation in a bullish structure.")
fam("Divergence", "OBV Divergence", ["obv_div"], RX, "Price makes a lower low while on-balance volume makes a higher low.")
# Volume
fam("Volume", "Volume Climax Reversal", ["vol_climax"], RX, "Capitulation: a 3x-volume bar with a long lower wick.")
fam("Volume", "MFI Cross above 200EMA", ["ema200", "mfi_cross"], TX, "Money Flow Index leaves oversold in an uptrend.")
fam("Volume", "Volume Spike Donchian Break", ["donchian_break", "vol_spike"], BX, "20-bar breakout on 2x volume.")
fam("Volume", "Dry-Volume Pullback in Structure", ["ms_up", "vol_dryup", "prev_high"], TX, "Pullback on drying volume, then a bar through the prior high.")
# Supply & demand
fam("Supply & Demand", "Demand Zone in Structure", ["ms_up", "sd_zone"], TX, "First return to a demand zone inside a bullish structure.")
fam("Supply & Demand", "Demand Zone Follow-through", ["sd_zone", "prev_high"], RX, "Demand zone retest and a bar through the prior high.")
fam("Supply & Demand", "Order Block with Volume", ["ob", "vol_confirm"], TX, "Order-block retest on above-average volume.")
fam("Supply & Demand", "Demand Zone Oversold", ["sd_zone", "rsi_os_zone"], RX, "Demand zone reached with RSI under 40.")
# Market structure
fam("Market Structure", "HH/HL Pullback to 20EMA", ["ms_up", "pb_ema20", "prev_high"], TX, "Classic HH/HL trend pullback to the 20 EMA.")
fam("Market Structure", "Range Structure Band Fade", ["ms_range", "bb_touch", "pin"], RX, "In a mixed structure, fade the Bollinger band with a pin bar.")
fam("Market Structure", "Structure Inside-Bar Break", ["ms_up", "inside_break"], TX, "Inside-bar breaks in the direction of structure.")
fam("Market Structure", "Structure Swing Support", ["ms_up", "sr_retest"], TX, "Higher-low retests of a prior swing low.")
# BOS
fam("BOS", "BOS with HTF and Volume", ["htf", "bos", "vol_confirm"], BX, "Break of structure with the higher timeframe and volume behind it.")
fam("BOS", "BOS Retest Continuation", ["bos_retest", "prev_high"], TX, "After a break of structure, the broken level is retested and holds.")
fam("BOS", "BOS with OBV", ["obv_up", "bos"], BX, "Break of structure with on-balance volume rising.")
fam("BOS", "BOS with ADX", ["adx", "bos"], BX, "Break of structure in a trending (ADX > 20) market.")
# CHoCH
fam("CHoCH", "CHoCH Reversal", ["choch"], RX, "The first break of the last swing high after a bearish structure.")
fam("CHoCH", "CHoCH with Volume", ["choch", "vol_confirm"], RX, "Change of character on above-average volume.")
fam("CHoCH", "CHoCH with HTF", ["htf", "choch"], RX, "Change of character in the direction of the higher timeframe.")
fam("CHoCH", "CHoCH above 200EMA", ["ema200", "choch"], RX, "Change of character that happens above the 200 EMA.")

FAMILIES2: List[Family] = []
for k, (cat, name, legs, extras, thesis) in enumerate(_F, start=101):
    for code in legs + extras:
        if code not in LEGS:
            raise KeyError(f"family {name}: unknown leg {code}")
    FAMILIES2.append(Family(k, name, cat, thesis, legs, extras, tuple(SESSION_ORDER), tuple(TIMEFRAMES2), tuple(TARGETS)))
FAMILIES2.append(Family(300, "RANDOM control", "Control",
                        "Coin-flip entries with the same sessions, stops, targets and costs. The luck baseline.",
                        (), (), tuple(SESSION_ORDER), tuple(TIMEFRAMES2), tuple(TARGETS)))
for f in FAMILIES2:
    FAMILY_BY_NUM[f.num] = f


def fid2(f: Family) -> str:
    return "CTRL" if f.group == "Control" else f"{f.num - 100:02d}"


def generate2(per_family: int = 240, seed: int = 11, markets: Sequence[str] = tuple(UNDERLYING_ORDER),
              controls_per_cell: int = 8) -> List[Strategy]:
    out: List[Strategy] = []
    for fam_ in FAMILIES2:
        rng = random.Random(f"{seed}-{fam_.num}")
        seen = set()
        weights = [TF_WEIGHT2[t] for t in fam_.timeframes]
        extras: List[Optional[str]] = [None, None] + list(fam_.extras)
        control = fam_.group == "Control"
        quota = len(markets) * len(fam_.targets) * controls_per_cell if control else per_family
        k = attempts = 0
        while k < quota and attempts < quota * 200:
            attempts += 1
            market = markets[k % len(markets)]
            target = fam_.targets[(k // len(markets)) % len(fam_.targets)] if control else rng.choice(fam_.targets)
            tf = rng.choices(fam_.timeframes, weights)[0]
            session = rng.choice(fam_.sessions)
            entry = rng.choice(ENTRIES)
            stop = rng.choice(STOPS)
            extra = None if control else rng.choice(extras)
            key = (market, tf, session, entry, stop, target, extra)
            if key in seen:
                continue
            seen.add(key)
            k += 1
            legs = fam_.legs + ((extra,) if extra else ())
            sid = f"{fid2(fam_)}-{k:03d}" if not control else f"CTRL-{k:03d}"
            sd = int(hashlib.sha1(f"r2-{sid}".encode()).hexdigest()[:8], 16)
            out.append(Strategy(sid, _name(fam_, extra, market, tf, session, entry, stop, target),
                                fam_.num, market, tf, session, entry, stop, target, legs, extra, sd))
    return out
