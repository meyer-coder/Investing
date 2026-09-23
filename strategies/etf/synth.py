"""Synthetic daily-reset leveraged funds, for history before a fund existed.

    python strategies/etf/synth.py

A 2x fund resets its leverage every close, so inside a day it moves exactly k
times its underlying's move from the previous close.  From the underlying's
daily bars:

    close_t = close_{t-1} x (1 + k x r_t - drag)
    open_t  = close_{t-1} x (1 + k x (U_open_t / U_close_{t-1} - 1))
    high/low the same from the underlying's high and low (swapped for k < 0)

``drag`` charges the fund's fee and the cost of financing the extra exposure:
1% a year plus, per unit of leverage above one, that year's short rate plus
3% (swap spread).  Checked against the real funds, that leaves the synthetic
series slightly ahead in strong years, never behind.  Each series is
written to the data cache as <UNDERLYING>.<k>X (NVDA.2X) and is checked here
against the real fund over the real fund's life.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evotrader.data import Bars, _write_cache, _write_meta, load_symbol   # noqa: E402

#: synthetic series -> (underlying, leverage, the real funds it stands for)
SYNTH = {
    "NVDA.2X": ("NVDA", 2.0, ("NVDL", "NVDU", "NVDX")), "NVDA.-1X": ("NVDA", -1.0, ("NVDD",)),
    "NVDA.-2X": ("NVDA", -2.0, ("NVDQ",)),
    "AMD.2X": ("AMD", 2.0, ("AMDL", "AMUU")), "AVGO.2X": ("AVGO", 2.0, ("AVGX", "AVL", "AVGU")),
    "TSM.2X": ("TSM", 2.0, ("TSMX", "TSMU")), "MU.2X": ("MU", 2.0, ("MUU",)),
    "MU.-1X": ("MU", -1.0, ("MUD",)), "SMCI.2X": ("SMCI", 2.0, ("SMCX", "SMCL")),
    "PLTR.2X": ("PLTR", 2.0, ("PLTU", "PTIR")), "MSFT.2X": ("MSFT", 2.0, ("MSFU",)),
    "AAPL.2X": ("AAPL", 2.0, ("AAPU",)), "GOOGL.2X": ("GOOGL", 2.0, ("GGLL",)),
    "META.2X": ("META", 2.0, ("METU",)), "AMZN.2X": ("AMZN", 2.0, ("AMZU",)),
    "TSLA.2X": ("TSLA", 2.0, ("TSLL",)), "ORCL.2X": ("ORCL", 2.0, ("ORCX",)),
    "FTEC.2X": ("FTEC", 2.0, ()), "FTEC.3X": ("FTEC", 3.0, ()),
    "SMH.2X": ("SMH", 2.0, ("USD",)), "SMH.3X": ("SMH", 3.0, ("SOXL",)),
}


#: average short rate by year, for the cost of financing leverage
RATES = {2005: 3.2, 2006: 4.9, 2007: 4.5, 2008: 1.4, 2009: 0.15, 2010: 0.14, 2011: 0.05, 2012: 0.09,
         2013: 0.06, 2014: 0.03, 2015: 0.05, 2016: 0.32, 2017: 0.93, 2018: 1.94, 2019: 2.06,
         2020: 0.36, 2021: 0.05, 2022: 2.02, 2023: 5.03, 2024: 5.14, 2025: 4.25, 2026: 3.9}


def synth(u: Bars, k: float, name: str) -> Bars:
    extra = max(abs(k) - 1.0, 0.0)
    drags = [(0.01 + extra * (RATES.get(int(d[:4]), 3.9) / 100 + 0.03)) / 252.0 for d in u.dates]
    n = len(u)
    c = np.empty(n); o = np.empty(n); h = np.empty(n); lo = np.empty(n)
    c[0] = o[0] = h[0] = lo[0] = 100.0
    for t in range(1, n):
        prev_u, prev = float(u.close[t - 1]), c[t - 1]
        move = lambda px: max(prev * (1.0 + k * (float(px) / prev_u - 1.0)), prev * 0.01)
        c[t] = max(prev * (1.0 + k * (float(u.close[t]) / prev_u - 1.0) - drags[t]), prev * 0.01)
        o[t] = move(u.open[t])
        a, b = move(u.high[t]), move(u.low[t])
        h[t] = max(a, b, o[t], c[t]); lo[t] = min(a, b, o[t], c[t])
    vol = np.asarray(u.volume, dtype=float)
    return Bars(name, list(u.dates), o, h, lo, c, vol)


def build(start: str = "2005-01-01", end: str = "2026-09-22") -> None:
    for name, (under, k, real) in SYNTH.items():
        u = load_symbol(under, start, end)
        b = synth(u, k, name)
        _write_cache(b)
        _write_meta(name, fetched_start="1990-01-01", fetched_end=b.dates[-1],
                    source=f"synthetic {k:g}x daily reset of {under}")
        for r in real:
            try:
                rb = load_symbol(r, start, end)
            except Exception:
                continue
            common = sorted(set(rb.dates) & set(b.dates))[1:]
            ia = {d: i for i, d in enumerate(b.dates)}; ib = {d: i for i, d in enumerate(rb.dates)}
            ra = np.array([b.close[ia[d]] / b.close[ia[d] - 1] - 1 for d in common])
            rr = np.array([rb.close[ib[d]] / rb.close[ib[d] - 1] - 1 for d in common])
            corr = float(np.corrcoef(ra, rr)[0, 1])
            cum_a, cum_r = float(np.prod(1 + ra) - 1), float(np.prod(1 + rr) - 1)
            print(f"{name:9} vs {r:5} {common[0]}..{common[-1]} daily corr {corr:.4f} "
                  f"total {cum_a:+.0%} synthetic vs {cum_r:+.0%} real", flush=True)


if __name__ == "__main__":
    build()
