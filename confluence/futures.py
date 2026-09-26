"""The futures universe of the second run: contracts, feeds, firms and plans.

Every strategy is defined on an *underlying* (NQ, ES, CL, 6E ...) and
backtested on the Dukascopy feed that tracks it (``data.build_duka_feed``).
Which contract you would actually trade — micro or mini, at which firm —
is decided later by the account optimiser (``accounts.py``), because it
depends on the account's contract limits and the risk you choose.

Permitted products, commissions and plan rules come from
``data/propfirms.json`` (researched from topstep.com and fundednext.com on
2026-09-26).  Two facts matter a lot:

* Topstep currently allows 0 contracts of SI, HG and PL (the micros SIL and
  MHG remain tradable), and is the only one of the two firms with rates (ZB),
  Nikkei (NKD), crypto (MET) and the micro FX contracts M6E / M6B.
* FundedNext does not publish per-contract fees; its one worked example (NQ
  $5.76 per round turn vs Topstep's $3.78) is used to scale Topstep's table
  by 1.52 as an estimate.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .markets import Market

PROPFIRMS_JSON = os.path.join("data", "propfirms.json")
FUNDEDNEXT_FEE_SCALE = 5.76 / 3.78


@dataclass(frozen=True)
class Contract:
    symbol: str
    point_value: float      # USD per 1.0 price move
    tick: float
    micro: bool


@dataclass(frozen=True)
class Underlying:
    code: str               # what the explorer shows
    name: str
    feed: str               # Dukascopy-built feed in data/cache/m1
    duka: str
    contracts: Tuple[Contract, ...]    # smallest first
    yahoo: str


C = Contract
UNDERLYINGS: Dict[str, Underlying] = {u.code: u for u in [
    Underlying("NQ", "Nasdaq-100", "F_NQ", "USATECHIDXUSD", (C("MNQ", 2.0, 0.25, True), C("NQ", 20.0, 0.25, False)), "NQ=F"),
    Underlying("ES", "S&P 500", "F_ES", "USA500IDXUSD", (C("MES", 5.0, 0.25, True), C("ES", 50.0, 0.25, False)), "ES=F"),
    Underlying("YM", "Dow Jones", "F_YM", "USA30IDXUSD", (C("MYM", 0.5, 1.0, True), C("YM", 5.0, 1.0, False)), "YM=F"),
    Underlying("RTY", "Russell 2000", "F_RTY", "USSC2000IDXUSD", (C("M2K", 5.0, 0.1, True), C("RTY", 50.0, 0.1, False)), "RTY=F"),
    Underlying("NKD", "Nikkei 225 (USD)", "F_NKD", "JPNIDXJPY", (C("NKD", 5.0, 5.0, False),), "NKD=F"),
    Underlying("CL", "WTI crude oil", "F_CL", "LIGHTCMDUSD", (C("MCL", 100.0, 0.01, True), C("QM", 500.0, 0.025, False), C("CL", 1000.0, 0.01, False)), "CL=F"),
    Underlying("NG", "Natural gas", "F_NG", "GASCMDUSD", (C("MNG", 1000.0, 0.001, True), C("QG", 2500.0, 0.005, False), C("NG", 10000.0, 0.001, False)), "NG=F"),
    Underlying("GC", "Gold", "F_GC", "XAUUSD", (C("MGC", 10.0, 0.1, True), C("GC", 100.0, 0.1, False)), "GC=F"),
    Underlying("SI", "Silver", "F_SI", "XAGUSD", (C("SIL", 1000.0, 0.005, True), C("SI", 5000.0, 0.005, False)), "SI=F"),
    Underlying("HG", "Copper", "F_HG", "COPPERCMDUSD", (C("MHG", 2500.0, 0.0005, True), C("HG", 25000.0, 0.0005, False)), "HG=F"),
    Underlying("6E", "Euro FX", "F_6E", "EURUSD", (C("M6E", 12500.0, 0.0001, True), C("6E", 125000.0, 0.00005, False)), "6E=F"),
    Underlying("6B", "British pound", "F_6B", "GBPUSD", (C("M6B", 6250.0, 0.0001, True), C("6B", 62500.0, 0.0001, False)), "6B=F"),
    Underlying("6J", "Japanese yen", "F_6J", "USDJPY", (C("6J", 12_500_000.0, 0.0000005, False),), "6J=F"),
    Underlying("6A", "Australian dollar", "F_6A", "AUDUSD", (C("M6A", 10000.0, 0.0001, True), C("6A", 100000.0, 0.00005, False)), "6A=F"),
    Underlying("6C", "Canadian dollar", "F_6C", "USDCAD", (C("6C", 100000.0, 0.00005, False),), "6C=F"),
    Underlying("6S", "Swiss franc", "F_6S", "USDCHF", (C("6S", 125000.0, 0.00005, False),), "6S=F"),
    Underlying("6N", "New Zealand dollar", "F_6N", "NZDUSD", (C("6N", 100000.0, 0.00005, False),), "6N=F"),
    Underlying("ZB", "30-year T-bond", "F_ZB", "USTBONDTRUSD", (C("ZB", 1000.0, 1.0 / 32.0, False),), "ZB=F"),
    Underlying("ZS", "Soybeans", "F_ZS", "SOYBEANCMDUSX", (C("ZS", 50.0, 0.25, False),), "ZS=F"),
    Underlying("ETH", "Ether (micro)", "F_ETH", "ETHUSD", (C("MET", 0.1, 0.5, True),), "ETH-USD"),
]}
UNDERLYING_ORDER = list(UNDERLYINGS)

# Dukascopy storage scale per instrument, and whether the quote is inverted
# (USD/JPY, USD/CAD, USD/CHF -> the CME contracts quote USD per JPY/CAD/CHF).
# Scales were checked against the Yahoo futures price level.
DUKA_SCALE: Dict[str, Tuple[float, bool]] = {
    "F_NQ": (1e3, False), "F_ES": (1e3, False), "F_YM": (1e3, False), "F_RTY": (1e3, False),
    "F_NKD": (1e3, False), "F_CL": (1e3, False), "F_NG": (1e4, False), "F_GC": (1e3, False),
    "F_SI": (1e3, False), "F_HG": (1e4, False), "F_6E": (1e5, False), "F_6B": (1e5, False),
    "F_6J": (1e3, True), "F_6A": (1e5, False), "F_6C": (1e5, True), "F_6S": (1e5, True),
    "F_6N": (1e5, False), "F_ZB": (1e3, False), "F_ZS": (1e3, False), "F_ETH": (10.0, False),
}


def load_propfirms(path: str = PROPFIRMS_JSON) -> dict:
    with open(path) as fh:
        return json.load(fh)


def firm_products(pf: dict) -> Dict[str, set]:
    """Tradable contract symbols per firm (volatility bans applied)."""
    out = {}
    for f in pf["firms"]:
        prods = set(f["permitted_products"])
        if f["firm"].startswith("Topstep"):
            prods -= {"SI", "HG", "PL"}        # currently set to 0 contracts
        out[f["firm"]] = prods
    return out


def commission(pf: dict, firm: str, symbol: str) -> float:
    """Round-turn fee per contract, USD."""
    top = next(f for f in pf["firms"] if f["firm"].startswith("Topstep"))["commissions"]
    base = top.get(symbol)
    if base is None:
        base = 1.22 if symbol.startswith("M") else 4.22
    if firm.startswith("Topstep"):
        return float(base)
    fn = next(f for f in pf["firms"] if not f["firm"].startswith("Topstep"))["commissions"]
    return float(fn.get(symbol, base * FUNDEDNEXT_FEE_SCALE))


def backtest_markets(pf: Optional[dict] = None) -> Dict[str, Market]:
    """Market entries the runner uses: costs in price units for the smallest contract."""
    pf = pf or load_propfirms()
    out = {}
    for u in UNDERLYINGS.values():
        c = u.contracts[0]
        cost = commission(pf, "Topstep", c.symbol) / c.point_value + 2 * c.tick
        out[u.code] = Market(u.code, u.name, "future", u.feed, u.duka, 0.0, c.tick, c.point_value, cost,
                             u.yahoo, "", "", f"{c.symbol}: ${commission(pf, 'Topstep', c.symbol):.2f} RT + 2 ticks")
    return out
