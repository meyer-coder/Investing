"""Trading styles: a mandate for the breeder plus seed archetypes.

A style is how you tell the evolutionary loop *whose* trading it should
resemble.  It has two halves, and neither one touches the engine:

* ``mandate`` — plain-English guidance appended to every breeding briefing,
  so Claude breeds toward a particular way of trading rather than toward
  whatever one backtest window happens to reward.
* ``archetypes`` — hand-written genomes in that style, placed at the front of
  generation 0 so the population starts with the behaviour instead of having
  to stumble onto it.

The fitness weights that make a style score well live in the run config
(see ``configs/leveraged_swing.json``), because they are the part worth
arguing about per run.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

#: Same shape as ``population.ARCHETYPES``: (name, thesis, entries, exits, risk).
Archetype = Tuple[str, str, List[str], List[str], Dict[str, float]]


@dataclass(frozen=True)
class TradingStyle:
    name: str
    summary: str                                   # one line, shown at startup
    mandate: str                                   # appended to every breeding prompt
    archetypes: List[Archetype] = field(default_factory=list)
    # When set, every agent trades exactly this share of buying power (1.0 =
    # all of it, which on a 2x account is twice equity).  Breeding can still
    # change what an agent trades and when, never how big.
    fixed_size: Optional[float] = None


# --------------------------------------------------------------- leveraged swing
#
# Modelled on a real account's recent trading: 2x/3x ETFs on large, well-known
# names, held one to seven days, sold for a modest gain.  The numbers in the
# mandate are that account's actual closed trades, which is the point — the
# breeder is shown the behaviour to reproduce, not a description of it.

_LEVERAGED_SWING_MANDATE = """\
=== STYLE MANDATE: leveraged core names, small wins ===
The trader this population is bred for buys 2x and 3x leveraged ETFs on large,
well-known names (the Nasdaq-100, semiconductors, mega-cap tech) and sells
quickly for a modest gain. Their actual recent record is the target behaviour:
  - round trips of +19% in 1 day, +12% in 4 days, +12% in 7 days and +2% in
    3 days; six of seven closes were winners and the one loss was under 1%
  - positions of 10-15% of the account, six to eight open at once
  - entries on a one-day dip inside an uptrend, or after a strong close;
    limit orders a little below the last price are common
  - exits by taking the gain, not by waiting for a signal; a name is often
    re-entered a day or two after it was sold
  - losers are cut slowly, around -10%, rather than on the first red day

Breed for that:
  - holds of 1 to 7 bars: max_hold_bars is the norm, not the exception
  - take-profit targets of +5% to +15% on the leveraged product
  - a high win rate and a steady equity curve over one big win
  - position sizes of 0.10-0.15 of equity and 5-8 concurrent positions
Do not breed buy-and-hold. An agent that sits in a 3x fund through a bull run
is beta, not this style, and the hold-time penalty in the fitness function
charges for it. The instruments are leveraged; the portfolio is not (gross
exposure stays at or below 100%).
"""

_LEVERAGED_SWING_ARCHETYPES: List[Archetype] = [
    ("Leveraged Dip Buyer",
     "Buy a leveraged core name on a one-day dip while its trend holds; "
     "take the first 10% and leave.",
     ["ret1 < -0.03 and close > sma20 and mkt_above_sma200 == 1"],
     ["position_return > 0.10", "bars_held >= 5"],
     {"max_position_pct": 0.15, "max_positions": 6, "max_gross_exposure": 0.9,
      "stop_loss_pct": 0.10, "max_hold_bars": 7, "cooldown_bars": 1}),
    ("Overnight Momentum",
     "A leveraged name that closes strong on heavy volume tends to follow "
     "through for a day or two; ride that and get out.",
     ["ret1 > 0.04 and volume_ratio > 1.2 and close > sma50"],
     ["ret1 < -0.02", "bars_held >= 3"],
     {"max_position_pct": 0.12, "max_positions": 6, "stop_loss_pct": 0.08,
      "take_profit_pct": 0.08, "max_hold_bars": 4}),
    ("RSI Snapback",
     "Short-term oversold inside an uptrend snaps back within days on a "
     "leveraged product; sell the snap, not the trend.",
     ["rsi7 < 30 and close > sma50"],
     ["rsi7 > 60", "position_return > 0.12", "bars_held >= 7"],
     {"max_position_pct": 0.15, "max_positions": 5, "stop_loss_pct": 0.10,
      "max_hold_bars": 10, "cooldown_bars": 2}),
    ("Small Win Scalper",
     "Many small wins: buy any red day inside a rising 20-day trend and sell "
     "into the first strong green close.",
     ["ret1 < -0.015 and dist_sma20 > -0.05 and sma20 > sma50"],
     ["position_return > 0.05", "ret1 > 0.03", "bars_held >= 4"],
     {"max_position_pct": 0.12, "max_positions": 8, "stop_loss_pct": 0.08,
      "max_hold_bars": 5}),
]

# --------------------------------------------------------------- quick leveraged
#
# Funded-account trading: one to three sessions per trade, in leveraged funds
# that exist in both directions on the same underlying.  In a long-only engine,
# buying the inverse fund *is* the short trade.

_QUICK_LEVERAGED_MANDATE = """\
=== STYLE MANDATE: quick trades in leveraged long and short funds ===
This population trades for funded accounts, where a trade lasts one to three
sessions and the aim is a steady stream of small realised gains. The universe
is leveraged funds in both directions on the same underlyings (TQQQ and SQQQ
on the Nasdaq-100, MUU and MUD on Micron, RIOX on Riot, SOXL and SOXS on
semiconductors). Buying the inverse fund IS the short trade, so a rule that
buys a dip in TQQQ also buys a dip in SQQQ: write rules that make sense in
both directions, or gate them on the symbol's own short-term trend.

Target behaviour:
  - hold 1 to 3 bars: decide on the close, fill at the next open, be flat
    again within three sessions. max_hold_bars of 1-3 is the norm
  - take-profit targets of +3% to +8% on the leveraged product; stops of 4-8%
  - position sizes of 0.10-0.25 of equity, 2-5 positions open at once
  - trade often: a rule that fires a few times a year is useless here
  - prefer fast features (ret1, ret5, rsi7, sma10, sma20, bb_pct, volume_ratio,
    atr_pct, vol_ratio_20_60); a 200-bar mean is not available on the newer
    single-stock funds and is too slow to matter for a two-day trade
Avoid: trend-following holds, anything that needs weeks to play out, and
rules that only work in one direction of the market. An agent that sits in a
3x fund is beta, not this style; the hold-time penalty charges for it. The
portfolio stays unlevered (gross exposure at or below 100%).

Recency: most of the fitness score (70%) is earned on the last six months of
the window. What works now outranks what worked in 2018; a losing year long ago
is background, not a veto. Funded accounts cap the downside at the account,
so consistency of small wins and a survivable worst day matter more than
surviving a recession.
"""

_QUICK_LEVERAGED_ARCHETYPES: List[Archetype] = [
    ("One-Day Dip",
     "A 4% down day in a leveraged fund still above its 20-day mean is usually "
     "bought back within two sessions.",
     ["ret1 < -0.04 and close > sma20"],
     ["position_return > 0.04", "bars_held >= 2"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.06,
      "take_profit_pct": 0.05, "max_hold_bars": 2, "cooldown_bars": 1}),
    ("Gap Continuation",
     "A strong close on heavy volume tends to follow through at the next open; "
     "take that and leave.",
     ["ret1 > 0.05 and volume_ratio > 1.3 and close > sma10"],
     ["bars_held >= 1"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.05,
      "take_profit_pct": 0.06, "max_hold_bars": 2}),
    ("RSI7 Snap",
     "Deeply oversold on a 7-bar RSI snaps back within three sessions.",
     ["rsi7 < 25"],
     ["rsi7 > 50", "bars_held >= 3"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.07,
      "max_hold_bars": 3, "cooldown_bars": 1}),
    ("Band Snap",
     "A close below the lower Bollinger band while volatility is expanding "
     "mean-reverts fast.",
     ["bb_pct < 0.0 and vol_ratio_20_60 > 1.1"],
     ["bb_pct > 0.5", "bars_held >= 3"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.07,
      "max_hold_bars": 3}),
    ("Two Red Days",
     "Two consecutive down days inside a rising 50-day trend: buy the second, "
     "sell the first green close.",
     ["ret1 < 0 and prev(ret1) < 0 and close > sma50"],
     ["ret1 > 0.02", "bars_held >= 3"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.06,
      "max_hold_bars": 3}),
    ("Squeeze Pop",
     "Volatility contraction followed by a close above the upper band; ride the "
     "release for two sessions.",
     ["vol_ratio_20_60 < 0.8 and cross_above(close, bb_upper)"],
     ["bars_held >= 2", "ret1 < -0.02"],
     {"max_position_pct": 0.20, "max_positions": 4, "stop_loss_pct": 0.06,
      "take_profit_pct": 0.08, "max_hold_bars": 3}),
]

QUICK_LEVERAGED = TradingStyle(
    name="quick_leveraged",
    summary="1-3 session trades in leveraged long and short funds on core names",
    mandate=_QUICK_LEVERAGED_MANDATE,
    archetypes=_QUICK_LEVERAGED_ARCHETYPES,
)

LEVERAGED_SWING = TradingStyle(
    name="leveraged_swing",
    summary="2x/3x ETFs on core names, held 1-7 days, sold for a 5-15% gain",
    mandate=_LEVERAGED_SWING_MANDATE,
    archetypes=_LEVERAGED_SWING_ARCHETYPES,
)

#: Every style a config can name.  Add a ``TradingStyle`` here to make it available.
# ------------------------------------------------------------- NQ E-mini at 2x
#
# One instrument, the Nasdaq-100 E-mini, traded long at twice the account in
# notional: a $25,000 account holds about $50,000 of NQ, 0.8 of a micro (MNQ)
# at NQ 31,000.  Thresholds are index-sized: NQ moves about a third as much as
# the 3x funds the other styles were written for.

_NQ_2X_MANDATE = """\
=== STYLE MANDATE: Nasdaq-100 E-mini, long only, 2x the account ===
The population trades one instrument, the NQ E-mini future (back-adjusted
continuous contract), long only, at twice the account in notional whenever it
is in a position. Size is fixed by the account: do not breed position sizes.
Breed what to trade and when:
  - the target is a high average profit per session over the most recent
    year, with holds of one to ten sessions; the trader does not want
    month-long holds
  - index-sized thresholds: NQ's typical day is +/-1%, a -1.2% day is a real
    flush, a 3% move is rare. A 0.6% to 1% gain is a good quick trade, and at
    2x it is 1.2% to 2% of the account
  - two families work on this index: buying short, sharp dips inside an
    uptrend (sold within one to three sessions), and staying long while the
    trend is intact and volatility is calm (out on the first sign of stress)
  - every session in the market at 2x can cost 4-8% of the account on a bad
    day: prefer exits that step aside when volatility expands
  - calendar features exist for daily bars: day_of_week (0 = Monday) and
    day_of_month; the turn of the month is a known index effect
"""

_NQ_2X_ARCHETYPES: List[Archetype] = [
    # --- dips inside an uptrend, out within a few sessions
    ("NQ Capitulation Close",
     "A 1.2% down day closing in the bottom quarter of its range is a flush that is usually bought within two sessions.",
     ["ret1 < -0.012 and (close - low) / (high - low + 0.0001) < 0.25"],
     ["position_return > 0.008", "bars_held >= 2"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 3}),
    ("NQ Prior-Low Break",
     "A close under yesterday's low while above the 50-day mean is a one-day shakeout inside a trend.",
     ["close < prev(low) and close > sma50"],
     ["position_return > 0.006", "bars_held >= 2"],
     {"stop_loss_pct": 0.025, "max_hold_bars": 3}),
    ("NQ Z-Score Dip",
     "Two standard deviations under the 20-day mean, above the 200-day: buy, sell back at the mean.",
     ["zscore20 < -1.5 and close > sma200"],
     ["zscore20 > 0", "bars_held >= 4"],
     {"stop_loss_pct": 0.04, "max_hold_bars": 5}),
    ("NQ RSI Washout",
     "A 7-day RSI under 25 is a washout; the index snaps back before RSI reaches 50.",
     ["rsi7 < 25"],
     ["rsi7 > 50", "bars_held >= 3"],
     {"stop_loss_pct": 0.04, "max_hold_bars": 4}),
    ("NQ Red Day Above the 200",
     "A 1% down day in a long-term uptrend: take 0.6% or two sessions.",
     ["ret1 < -0.01 and close > sma200"],
     ["position_return > 0.006", "bars_held >= 2"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 3}),
    ("NQ Volume Flush",
     "A 1.2% down day on 1.5x volume is forced selling, bought back within two sessions.",
     ["volume_ratio > 1.5 and ret1 < -0.012"],
     ["position_return > 0.008", "bars_held >= 2"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 3}),
    ("NQ Two Red Days",
     "A red day after a 0.9% red day with a 2.5% five-day loss, still above the 50-day: sell the first 0.7% up day.",
     ["ret1 < 0 and prev(ret1) < -0.009 and ret5 < -0.025 and close > sma50"],
     ["ret1 > 0.007", "bars_held >= 3"],
     {"stop_loss_pct": 0.02, "max_hold_bars": 3}),
    ("NQ Pullback in a Rising Market",
     "A 2% five-day pullback while the 20-day mean is still rising: buy, take 1% or four sessions.",
     ["ret5 < -0.02 and close > sma50 and sma20_slope > 0"],
     ["position_return > 0.01", "bars_held >= 4"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 5}),
    ("NQ Uptrend Dip Buyer",
     "RSI(7) under 45 above the 50-day: buy the soft patch, sell when RSI is back over 70.",
     ["rsi7 < 45 and close > sma50"],
     ["rsi7 > 70", "bars_held >= 5"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 6}),
    ("NQ Turn of the Month",
     "The last days of a month and the first of the next carry most of the index's drift.",
     ["day_of_month >= 27 and close > sma50"],
     ["bars_held >= 4"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 5}),
    # --- ride a calm uptrend, step aside on stress
    ("NQ Calm Uptrend",
     "Above the 50-day with 20-day volatility under 25%: stay long, out on a break of the 50-day or a volatility spike.",
     ["close > sma50 and vol20 < 0.25"],
     ["close < sma50", "vol20 > 0.3"],
     {"max_hold_bars": 10}),
    ("NQ MACD Uptrend",
     "MACD histogram positive above the 50-day: momentum intact; out when the histogram turns.",
     ["macd_hist > 0 and close > sma50"],
     ["macd_hist < 0"],
     {"max_hold_bars": 10}),
    ("NQ Trend with a Crash Exit",
     "Long above the 50-day unless the day fell 2%; a 2% day is the exit.",
     ["close > sma50 and ret1 > -0.02"],
     ["ret1 < -0.02", "close < sma50"],
     {"max_hold_bars": 10}),
    ("NQ EMA Trend",
     "12-day EMA over the 26-day and the close over the 20-day mean: trend; out under the 20-day.",
     ["ema12 > ema26 and close > sma20"],
     ["close < sma20"],
     {"max_hold_bars": 10}),
    ("NQ Squeeze Breakout",
     "Volatility contracted, then a close through the upper band: ride the release for up to a week.",
     ["vol_ratio_20_60 < 0.8 and cross_above(close, bb_upper)"],
     ["ret1 < -0.01", "bars_held >= 5"],
     {"stop_loss_pct": 0.03, "max_hold_bars": 5}),
    ("NQ Strong Close",
     "A 0.5% up day closing in the top fifth of its range above the 20-day: the next session tends to follow.",
     ["(close - low) / (high - low + 0.0001) > 0.8 and ret1 > 0.005 and close > sma20"],
     ["bars_held >= 2"],
     {"stop_loss_pct": 0.025, "max_hold_bars": 2}),
    ("NQ Near the High",
     "Within 2% of the 52-week high with a positive week: momentum; out under the 10-day mean.",
     ["pct_of_52w_high > 0.98 and ret5 > 0"],
     ["close < sma10", "bars_held >= 8"],
     {"max_hold_bars": 8}),
    # --- both at once
    ("NQ Trend or Dip",
     "Long in a rising trend, and also after a washout; out when both have failed.",
     ["close > sma20 and sma20_slope > 0", "rsi7 < 30"],
     ["close < sma20 and rsi7 > 30"],
     {"stop_loss_pct": 0.05, "max_hold_bars": 10}),
    ("NQ Inside Day in an Uptrend",
     "An inside day above the 50-day is a pause; the trend usually resumes.",
     ["high < prev(high) and low > prev(low) and close > sma50"],
     ["ret1 < -0.01", "bars_held >= 3"],
     {"stop_loss_pct": 0.02, "max_hold_bars": 3}),
    ("NQ Monday Dip",
     "A red Monday above the 50-day is bought for the rest of the week.",
     ["day_of_week == 0 and ret1 < 0 and close > sma50"],
     ["position_return > 0.008", "bars_held >= 3"],
     {"stop_loss_pct": 0.025, "max_hold_bars": 4}),
]

NQ_2X = TradingStyle(
    name="nq_2x",
    summary="NQ E-mini, long only, always 2x the account in notional, 1-10 session holds",
    mandate=_NQ_2X_MANDATE,
    archetypes=_NQ_2X_ARCHETYPES,
    fixed_size=1.0,
)

# ------------------------------------------------------------ leveraged ETFs, full size
#
# Tech, semiconductor and AI 2x/3x funds on a cash account: one position at a
# time with the whole account, held one day to a few weeks.  The target is
# dollars a session, so size is fixed and breeding decides what and when.

_ETF_FULL_MANDATE = """\
=== STYLE MANDATE: leveraged tech / semis / AI funds, one position, full size ===
The population trades 2x and 3x funds on semiconductors, graphics-card and AI
names and big tech (SOXL, TQQQ, TECL, 2x NVDA, AMD, AVGO, TSM, MU and the
like), long only, one position at a time with the whole cash account.
  - the target is a high average profit per session over the last year, with
    a drawdown the trader can live with and a high share of winning trades
  - these funds move 2-3x their stock: a 3x semis fund's normal day is +/-4%,
    a -8% day is a flush, a 10% bounce in three days is common
  - two families work: short, sharp dips bought inside an uptrend and sold
    into the bounce within one to five sessions, and riding a calm, intact
    uptrend with an exit on the first sign of stress
  - inverse funds (SOXS, SQQQ, TECS) are in some universes: they are the
    only way to be short, and only pay in falling markets
"""

_ETF_FULL_ARCHETYPES: List[Archetype] = [
    ("Uptrend Flush", "A hard down day inside an uptrend, sold into the bounce.",
     ["ret1 < -0.05 and close > sma50"], ["ret1 > 0.03", "bars_held >= 3"],
     {"stop_loss_pct": 0.10, "take_profit_pct": 0.08, "max_hold_bars": 4}),
    ("Oversold Above the 200", "RSI(7) washed out while the long trend holds.",
     ["rsi7 < 20 and close > sma200"], ["rsi7 > 60", "bars_held >= 5"],
     {"stop_loss_pct": 0.12, "max_hold_bars": 6}),
    ("Z-Dip", "Two sigma under the 20-day mean in a long uptrend.",
     ["zscore20 < -1.8 and close > sma200"], ["zscore20 > 0"],
     {"stop_loss_pct": 0.12, "max_hold_bars": 8}),
    ("Calm Trend", "Long while above both means and volatility is calm.",
     ["close > sma50 and sma50 > sma200 and vol20 < 0.6"], ["close < sma50", "vol20 > 0.9"],
     {"trailing_stop_pct": 0.15, "max_hold_bars": 20}),
    ("Volume Breakout", "A close over the upper band on heavy volume.",
     ["close > bb_upper and volume_ratio > 1.4 and close > sma50"], ["bars_held >= 3", "ret1 < -0.04"],
     {"stop_loss_pct": 0.08, "take_profit_pct": 0.12, "max_hold_bars": 5}),
    ("Momentum Pullback", "A strong month, a shallow pause.",
     ["ret20 > 0.15 and ret1 < -0.02 and dist_sma20 > 0"], ["ret5 < -0.08", "bars_held >= 5"],
     {"stop_loss_pct": 0.10, "max_hold_bars": 6}),
    ("Two Red Days", "Two down days in an uptrend, sold on the first green close.",
     ["ret1 < 0 and prev(ret1) < 0 and close > sma50"], ["ret1 > 0.02", "bars_held >= 3"],
     {"stop_loss_pct": 0.08, "max_hold_bars": 4}),
    ("Capitulation Close", "A big down day closing near its low on volume.",
     ["ret1 < -0.06 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3"],
     ["position_return > 0.05", "bars_held >= 2"], {"stop_loss_pct": 0.12, "max_hold_bars": 3}),
    ("Month Turn", "The turn of the month above the 50-day.",
     ["(day_of_month >= 27 or day_of_month <= 2) and close > sma50"], ["bars_held >= 4"],
     {"stop_loss_pct": 0.08, "max_hold_bars": 5}),
    ("MACD Turn", "MACD histogram turns up above the 200-day.",
     ["macd_hist > 0 and prev(macd_hist) <= 0 and close > sma200"], ["macd_hist < 0"],
     {"stop_loss_pct": 0.10, "max_hold_bars": 15}),
    ("Strong Close", "A big up day closing at the high: follow it one or two days.",
     ["ret1 > 0.04 and (close - low) / (high - low + 0.0001) > 0.8 and close > sma50"],
     ["bars_held >= 2"], {"stop_loss_pct": 0.07, "max_hold_bars": 2}),
    ("New High, Calm", "Near the 52-week high with volatility in check.",
     ["pct_of_52w_high > 0.97 and vol20 < 0.7"], ["pct_of_52w_high < 0.88"],
     {"trailing_stop_pct": 0.12, "max_hold_bars": 20}),
    ("Inside Day", "A quiet inside day above the 20-day.",
     ["high < prev(high) and low > prev(low) and close > sma20"], ["bars_held >= 2"],
     {"stop_loss_pct": 0.07, "max_hold_bars": 3}),
    ("Stretched Below the 20", "Far under the 20-day mean in a long uptrend.",
     ["dist_sma20 < -0.12 and close > sma200"], ["dist_sma20 > 0"],
     {"stop_loss_pct": 0.15, "max_hold_bars": 10}),
    ("Quiet Dip, Quick Target", "A small dip on a quiet day, a quick target.",
     ["ret1 < -0.02 and atr_pct < 0.05 and close > sma50"], ["bars_held >= 2"],
     {"stop_loss_pct": 0.05, "take_profit_pct": 0.04, "max_hold_bars": 2}),
]

ETF_FULL = TradingStyle(
    name="etf_full",
    summary="leveraged tech/semis/AI funds, long only, one position with the whole account",
    mandate=_ETF_FULL_MANDATE,
    archetypes=_ETF_FULL_ARCHETYPES,
    fixed_size=1.0,
)



STYLES: Dict[str, TradingStyle] = {
    LEVERAGED_SWING.name: LEVERAGED_SWING,
    QUICK_LEVERAGED.name: QUICK_LEVERAGED,
    NQ_2X.name: NQ_2X,
    ETF_FULL.name: ETF_FULL,
}


def get_style(name: str) -> Optional[TradingStyle]:
    """Look a style up by name.  ``""`` means no style; unknown names raise."""
    if not name:
        return None
    try:
        return STYLES[name]
    except KeyError:
        raise ValueError(f"unknown style {name!r}; available: "
                         f"{', '.join(sorted(STYLES))}") from None
