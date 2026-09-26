"""Scoring a card's trades on three periods fixed in advance.

    search   2013-2019   where ideas are allowed to be chosen
    confirm  2020-2022   must still be positive and beat random sign flips
    final    2023-2026   looked at once, never used to choose

A card passes the search with 100+ trades, a positive mean net R, t >= 2
and -- when the batch has random controls -- a better net R a trade than at
least 95% of them.  It is confirmed if on 2020-2022 it stays positive, its
long/short calls beat at least 90% of 2,000 random sign flips of the same
trades, and it beats at least 90% of the controls again.

Random controls matter because backtests carry biases that have nothing to
do with the signal (a stop-first rule on minutes that touch both the stop
and the target, fills around data gaps, drift): the controls share the
card's market, candles, session and exits, so they carry the same biases.
With many cards tested, about 2.3% pass the t >= 2 bar by luck alone -- the
log keeps that count honest.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

import numpy as np

from .data import minutes, trading_day_label
from .engine import Trade

PERIODS = (("search", "0000", "2019-12-31"), ("confirm", "2020-01-01", "2022-12-31"),
           ("final", "2023-01-01", "9999"))
RISK_USD = 250.0


@lru_cache(maxsize=None)
def _weeks(market_name: str, lo: str, hi: str) -> float:
    M = minutes(market_name)
    days = [trading_day_label(d) for d, ok in M.valid.items() if ok]
    return max(1.0, sum(lo <= d <= hi for d in days) / 5.0)


def stats(trades: List[Trade], market_name: str, lo: str, hi: str) -> Dict[str, float]:
    ts = [t for t in trades if lo <= t.day <= hi]
    n = len(ts)
    out = {"n": n, "per_week": n / _weeks(market_name, lo, hi)}
    if n < 2:
        return {**out, "win": 0.0, "avg_rr": 0.0, "net_r": 0.0, "gross_r": 0.0, "total_r": 0.0,
                "usd": 0.0, "max_dd_r": 0.0, "cost_r": 0.0, "t": 0.0, "flips": 0.0}
    net = np.array([t.r_net for t in ts])
    gross = np.array([t.r_gross for t in ts])
    cost = np.array([t.r_cost for t in ts])
    wins, losses = net[net > 0], net[net <= 0]
    eq = np.cumsum(net)
    dd = float(np.max(np.maximum.accumulate(np.r_[0.0, eq])[1:] - eq)) if n else 0.0
    sd = net.std(ddof=1)
    rng = np.random.default_rng(7)
    flip_means = (rng.choice([-1.0, 1.0], size=(2000, n)) * np.abs(gross)).mean(axis=1) - cost.mean()
    return {**out,
            "win": float(np.mean(net > 0) * 100),
            "avg_rr": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) and losses.mean() < 0 else 0.0,
            "net_r": float(net.mean()), "gross_r": float(gross.mean()), "total_r": float(net.sum()),
            "usd": float(net.sum() * RISK_USD), "max_dd_r": dd, "cost_r": float(cost.mean()),
            "t": float(net.mean() / (sd / np.sqrt(n))) if sd > 0 else 0.0,
            "flips": float(np.mean(flip_means < net.mean()) * 100)}


def evaluate(trades: List[Trade], market_name: str) -> Dict[str, Dict[str, float]]:
    return {p: stats(trades, market_name, lo, hi) for p, lo, hi in PERIODS}


def verdict(res: Dict[str, Dict[str, float]], beats: Optional[Dict[str, float]] = None) -> str:
    """``beats``: share (%) of the random controls each period's net R a trade beats."""
    s, c = res["search"], res["confirm"]
    if not (s["n"] >= 100 and s["net_r"] > 0 and s["t"] >= 2.0):
        return "failed search"
    if beats is not None and beats["search"] < 95:
        return "failed search (not above random)"
    if not (c["net_r"] > 0 and c["flips"] >= 90):
        return "failed confirm"
    if beats is not None and beats["confirm"] < 90:
        return "failed confirm (not above random)"
    return "CONFIRMED"
