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
STYLES: Dict[str, TradingStyle] = {
    LEVERAGED_SWING.name: LEVERAGED_SWING,
    QUICK_LEVERAGED.name: QUICK_LEVERAGED,
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
