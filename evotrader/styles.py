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

LEVERAGED_SWING = TradingStyle(
    name="leveraged_swing",
    summary="2x/3x ETFs on core names, held 1-7 days, sold for a 5-15% gain",
    mandate=_LEVERAGED_SWING_MANDATE,
    archetypes=_LEVERAGED_SWING_ARCHETYPES,
)

#: Every style a config can name.  Add a ``TradingStyle`` here to make it available.
STYLES: Dict[str, TradingStyle] = {LEVERAGED_SWING.name: LEVERAGED_SWING}


def get_style(name: str) -> Optional[TradingStyle]:
    """Look a style up by name.  ``""`` means no style; unknown names raise."""
    if not name:
        return None
    try:
        return STYLES[name]
    except KeyError:
        raise ValueError(f"unknown style {name!r}; available: "
                         f"{', '.join(sorted(STYLES))}") from None
