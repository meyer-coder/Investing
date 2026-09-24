"""The wide set of funds each of the top five is run on: synthetic 2x funds on 146 large US stocks and
synthetic 3x funds on 30 index, sector and country ETFs, daily bars from 1998.

    python strategies/top5/universe.py          # fetch the underlyings and write the synthetic series

The top five were bred on 2x single-stock funds (MUU, AMDL) and 3x sector and
index funds (SOXL, TQQQ, TECL), which have a handful of years of history
each.  To see whether a rule's edge is its own or the history of one stock,
the same rule is run on the same kind of fund on many other underlyings: a
daily-reset 2x series for each stock and a 3x series for each ETF, built the
way strategies/etf/synth.py builds MU.2X (k times the underlying's move from
the previous close, less the fund's fee and financing).  They are written to
the data cache as <SYMBOL>.2X and <SYMBOL>.3X.

Survivorship: these are today's large caps, and stocks that later collapsed
or were taken over are missing, which flatters anything that buys.  The random
entries in rigor.py share that bias, so the comparison between the rule and
random timing is the fair test; the raw dollars are not.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
import synth                                                                 # noqa: E402
from evotrader.data import DataError, _read_cache, _write_cache, _write_meta, load_symbol   # noqa: E402

START, END = "1998-01-01", "2026-09-22"
# short rates before synth.py's table starts
synth.RATES.update({1998: 4.8, 1999: 4.6, 2000: 5.8, 2001: 3.4, 2002: 1.6, 2003: 1.0, 2004: 1.4})

STOCKS = (
    # technology and semiconductors
    "AAPL MSFT NVDA AMD INTC CSCO ORCL IBM QCOM TXN ADBE AMAT MU LRCX KLAC ADI MCHP NTAP HPQ AMZN NFLX EBAY INTU "
    "CTSH ACN ADP GOOGL CRM AVGO MRVL TER SWKS STX WDC JNPR AKAM FFIV CDNS SNPS ADSK "
    # financials
    "JPM BAC C WFC GS MS AXP USB PNC BK SCHW MET AIG TRV ALL CB MMC BLK SPGI MCO "
    # health care
    "JNJ PFE MRK ABT LLY BMY AMGN GILD UNH CVS MDT TMO DHR BDX SYK BIIB REGN VRTX ISRG ZBH "
    # consumer
    "KO PEP PG WMT HD LOW MCD SBUX NKE COST TGT DIS CMCSA CL KMB MO YUM TJX BKNG ORLY "
    # industrials
    "GE BA CAT DE HON MMM UPS UNP LMT RTX GD NOC EMR ETN ITW FDX CSX NSC WM "
    # energy and materials
    "XOM CVX COP SLB OXY EOG HAL DVN FCX NEM APD ECL NUE SHW MLM VMC "
    # utilities, telecoms, real estate
    "NEE DUK SO D AEP EXC T VZ AMT SPG PLD").split()
ETFS = ("SPY QQQ DIA IWM MDY XLK XLF XLE XLV XLI XLY XLP XLU XLB SMH IBB EEM EFA EWJ EWZ FXI IYR IYT SOXX GLD TLT "
        "EWG EWU EWT EWY").split()


def name(sym: str, k: float) -> str:
    return f"{sym}.{k:g}X"


def members(kind: str = "all"):
    """(synthetic name, underlying, leverage) for the stocks at 2x, the ETFs at 3x, or both."""
    out = []
    if kind in ("all", "stocks"):
        out += [(name(s, 2.0), s, 2.0) for s in STOCKS]
    if kind in ("all", "etfs"):
        out += [(name(s, 3.0), s, 3.0) for s in ETFS]
    return out


def build() -> int:
    made = 0
    for syn, under, k in members():
        have = _read_cache(syn)
        if have is not None and have.dates[-1] >= "2026-09-21" and have.dates[0] <= "2006-01-03":
            continue
        try:
            u = load_symbol(under, START, END)
        except DataError as e:
            print(f"{under}: {e}", flush=True)
            continue
        b = synth.synth(u, k, syn)
        _write_cache(b)
        _write_meta(syn, fetched_start="1990-01-01", fetched_end=b.dates[-1], source=f"synthetic {k:g}x daily reset of {under}")
        made += 1
        print(f"{syn:9s} {b.dates[0]} to {b.dates[-1]} ({len(b)} bars)", flush=True)
    return made


if __name__ == "__main__":
    print(f"{build()} synthetic series written")
