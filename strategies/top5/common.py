"""Shared pieces for the top-five study: one backtest call and one set of statistics for every strategy.

Every daily strategy runs through evotrader's engine (evotrader/runner.py): the
rules are read on a bar's close and the order fills at the next open, with the
slippage charged on both sides, stops, targets and holding limits as each
genome sets them.  Dollars a day are the mean daily return of the account
times $25,000, the footing the strategy lists use.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evotrader.data import load_universe                                   # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

ACCOUNT = 25_000.0
END = "2026-09-22"
EXCLUDE = ("TSM", "TSMX")                   # never TSMX or TSM, at the user's request

_markets: Dict[Tuple[str, ...], tuple] = {}


def market(symbols: Sequence[str], data_start: str = "1995-01-01"):
    key = tuple(symbols) + (data_start,)
    if key not in _markets:
        u = load_universe(list(symbols), data_start, END, min_bars=100)
        _markets[key] = (u, build_features(u))
    return _markets[key]


def first_on_or_after(dates: List[str], d: str) -> int:
    for i, x in enumerate(dates):
        if x >= d:
            return i
    return len(dates)


def backtest(genome, symbols: Sequence[str], *, start: str, slippage: float, commission: float = 0.0,
             leverage: float = 1.0, data_start: str = "1995-01-01", **kw):
    g = genome if isinstance(genome, Genome) else Genome.from_dict(genome)
    u, f = market(symbols, data_start)
    compiled = compile_genome(g)
    s = max(first_on_or_after(u.calendar, start), f.warmup_for(compiled.feature_names()))
    return run_backtest(compiled, u, f, starting_cash=ACCOUNT, commission_bps=commission, slippage_bps=slippage,
                        record_thoughts=False, start_bar=s, leverage=leverage, **kw)


def daily_returns(result, a: str = "0000", b: str = "9999") -> Tuple[List[str], np.ndarray]:
    j = result.journal
    dates, eq = j.equity_dates, np.asarray(j.equity, dtype=float)
    idx = [i for i, d in enumerate(dates) if a <= d <= b]
    if len(idx) < 2:
        return [], np.zeros(0)
    lo = max(idx[0] - 1, 0)
    e = eq[lo: idx[-1] + 1]
    return dates[lo + 1: idx[-1] + 1], e[1:] / e[:-1] - 1.0


def day_stats(r: np.ndarray) -> Dict[str, float]:
    """Dollars a day on $25,000 (mean daily return x $25,000), Sharpe, worst day and the worst losing stretch
    of that fixed-dollar account."""
    if r.size < 5:
        return {}
    usd = r * ACCOUNT
    eq = np.cumsum(usd)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    sd = float(np.std(r, ddof=1))
    return {"sessions": int(r.size), "usd_per_day": round(float(usd.mean()), 1),
            "sharpe": round(float(r.mean() / sd * math.sqrt(252)), 2) if sd > 0 else 0.0,
            "worst_day": round(float(usd.min()), 0), "worst_stretch": round(dd, 0),
            "days_in_market": round(float(np.mean(np.abs(r) > 1e-12)), 3)}


def trade_stats(rets: np.ndarray) -> Dict[str, float]:
    """Per-trade statistics on each trade's return on the capital it used."""
    n = int(rets.size)
    if n == 0:
        return {"trades": 0}
    wins, losses = rets[rets > 0], rets[rets <= 0]
    gl = -losses.sum()
    sd = float(rets.std(ddof=1)) if n > 1 else 0.0
    return {"trades": n, "mean_bp": round(float(rets.mean() * 1e4), 1), "median_bp": round(float(np.median(rets) * 1e4), 1),
            "win_rate": round(float(wins.size / n), 3), "avg_win_pct": round(float(wins.mean() * 100), 2) if wins.size else 0.0,
            "avg_loss_pct": round(float(losses.mean() * 100), 2) if losses.size else 0.0,
            "profit_factor": round(float(wins.sum() / gl), 2) if gl > 1e-12 else 99.0,
            "t_stat": round(float(rets.mean() / (sd / math.sqrt(n))), 2) if sd > 0 else 0.0}


def excluded(symbols: Sequence[str]) -> bool:
    return any(s.upper().split(".")[0] in EXCLUDE for s in symbols)
