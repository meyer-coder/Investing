"""The markets under test, their price feeds and their trading costs.

Futures (MNQ, MES) are backtested on the index CFD feed that tracks the same
underlying (NSXUSD / SPXUSD).  The CFD series is continuous — no roll gaps —
and trades the same Globex hours; what differs between MNQ and NAS100 is the
cost of trading it, which is what ``cost_rt`` captures.  ``crosscheck`` in
``data.py`` measures how closely each proxy tracks the real futures contract
on the bars Yahoo and TradingView still serve.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Market:
    code: str            # what the explorer shows
    name: str
    kind: str            # future | cfd | fx
    feed: str            # histdata.com symbol, the 8-year 1-minute backbone
    duka: str            # Dukascopy datafeed symbol, used to extend to today
    duka_scale: float    # Dukascopy stores prices as integers / scale
    tick: float
    point_value: float   # USD per 1.0 move for one contract / lot
    cost_rt: float       # all-in round trip cost in price units (see COSTS below)
    yahoo: str           # Yahoo symbol of the real instrument, for the cross-check
    tradingview: str     # TradingView symbol of the real instrument
    massive: str         # massive.com (ex-Polygon) ticker, used when a key is set
    cost_note: str


# Cost model, round trip, in price units:
#   futures: commission / point value + 2 ticks of slippage (market in, stop out)
#   CFD / FX: typical prop-firm / ECN spread + commission + a little slippage
MARKETS: Dict[str, Market] = {m.code: m for m in [
    Market("MNQ", "Micro E-mini Nasdaq-100 futures", "future", "NSXUSD", "USATECHIDXUSD",
           1000.0, 0.25, 2.0, 1.40 / 2.0 + 2 * 0.25, "NQ=F", "CME_MINI:MNQ1!", "I:NDX",
           "$1.40 RT commission + 2 ticks slippage = 1.20 pts"),
    Market("MES", "Micro E-mini S&P 500 futures (ES)", "future", "SPXUSD", "USA500IDXUSD",
           1000.0, 0.25, 5.0, 1.40 / 5.0 + 2 * 0.25, "ES=F", "CME_MINI:MES1!", "I:SPX",
           "$1.40 RT commission + 2 ticks slippage = 0.78 pts"),
    Market("NAS100", "Nasdaq-100 CFD", "cfd", "NSXUSD", "USATECHIDXUSD",
           1000.0, 0.1, 1.0, 1.80, "NQ=F", "CAPITALCOM:US100", "I:NDX",
           "1.5 pt spread + 0.3 pt slippage"),
    Market("USOIL", "WTI crude oil CFD", "cfd", "WTIUSD", "LIGHTCMDUSD",
           1000.0, 0.01, 1000.0, 0.04, "CL=F", "TVC:USOIL", "C:XTIUSD",
           "3 cent spread + 1 cent slippage"),
    Market("EURUSD", "Euro / US dollar", "fx", "EURUSD", "EURUSD",
           100000.0, 0.00001, 100000.0, 0.00012, "EURUSD=X", "FX:EURUSD", "C:EURUSD",
           "0.5 pip raw spread + $7/lot commission + 0.2 pip slippage = 1.2 pips"),
    Market("GBPUSD", "British pound / US dollar", "fx", "GBPUSD", "GBPUSD",
           100000.0, 0.00001, 100000.0, 0.00016, "GBPUSD=X", "FX:GBPUSD", "C:GBPUSD",
           "0.8 pip spread + $7/lot commission + 0.1 pip slippage = 1.6 pips"),
    Market("USDJPY", "US dollar / Japanese yen", "fx", "USDJPY", "USDJPY",
           1000.0, 0.001, 1000.0 / 150.0 * 100.0, 0.014, "JPY=X", "FX:USDJPY", "C:USDJPY",
           "0.6 pip spread + commission + slippage = 1.4 pips"),
    Market("XAUUSD", "Gold spot", "cfd", "XAUUSD", "XAUUSD",
           1000.0, 0.01, 100.0, 0.35, "GC=F", "OANDA:XAUUSD", "C:XAUUSD",
           "25 cent spread + 10 cent slippage"),
    Market("GER40", "DAX 40 CFD", "cfd", "GRXEUR", "DEUIDXEUR",
           1000.0, 0.1, 1.0, 1.60, "^GDAXI", "PEPPERSTONE:GER40", "I:DAX",
           "1.2 pt spread + 0.4 pt slippage"),
]}

MARKET_ORDER: List[str] = list(MARKETS)

# One price feed can serve several markets (MNQ and NAS100 share NSXUSD).
FEEDS: List[str] = sorted({m.feed for m in MARKETS.values()})
