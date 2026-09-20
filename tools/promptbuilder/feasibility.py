"""Can this grid actually be tested to the required trade count?

Two questions, both answered before a single bar is fetched:

1. *Sample size.*  A variation that needs 400 trades and fires twice a month
   needs sixteen years of history.  Selective variations are the ones that look
   best and the ones least able to support the claim, so this is checked per
   variation rather than for the strategy as a whole.
2. *Multiple comparisons.*  Rank 500-800 variations by return and the winner is
   a near-certainty even when every one of them is worthless.  These are the
   numbers that say how good the best one has to be before it means anything.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict, List

from .grid import Grid
from .spec import Spec

TRADING_DAYS_PER_YEAR = 252.0


@dataclass
class Statistics:
    n_tests: int
    expected_max_t: float
    bonferroni_alpha: float
    bonferroni_z: float
    fdr_note: str


def statistics_for(n_tests: int, alpha: float = 0.05) -> Statistics:
    n = max(1, n_tests)
    # E[max of n standard normals] ~ sqrt(2 ln n); the value a no-edge search
    # is expected to produce by luck alone.
    expected_max = math.sqrt(2.0 * math.log(n)) if n > 1 else 0.0
    bonf_alpha = alpha / n
    bonf_z = NormalDist().inv_cdf(1.0 - bonf_alpha / 2.0)
    return Statistics(
        n_tests=n, expected_max_t=expected_max, bonferroni_alpha=bonf_alpha,
        bonferroni_z=bonf_z,
        fdr_note=("Bonferroni at this width is severe; Benjamini-Hochberg FDR at q=0.10 "
                  "is the usual practical choice, and a Deflated Sharpe Ratio or White's "
                  "Reality Check is better still because it accounts for the variations "
                  "being correlated rather than independent"),
    )


@dataclass
class FeasibilityReport:
    n_total: int
    n_feasible: int
    n_infeasible: int
    history_days: int
    history_years: float
    min_trades: int
    worst_required_days: int
    median_required_days: int
    days_needed_for_all: int
    years_needed_for_all: float
    tightest: List[Dict[str, object]]
    stats: Statistics

    @property
    def all_feasible(self) -> bool:
        return self.n_infeasible == 0


def assess(spec: Spec, grid: Grid) -> FeasibilityReport:
    required = sorted(v.required_days for v in grid.variations)
    worst = required[-1] if required else 0
    median = required[len(required) // 2] if required else 0
    tightest = [
        {"choices": v.choices, "trades_per_day": round(v.trades_per_day, 4),
         "attainable_trades": v.attainable_trades, "required_days": v.required_days}
        for v in sorted(grid.variations, key=lambda v: v.attainable_trades)[:5]
    ]
    return FeasibilityReport(
        n_total=len(grid.variations), n_feasible=len(grid.feasible),
        n_infeasible=len(grid.infeasible), history_days=spec.history_days,
        history_years=spec.history_days / TRADING_DAYS_PER_YEAR,
        min_trades=spec.min_trades, worst_required_days=worst,
        median_required_days=median, days_needed_for_all=worst,
        years_needed_for_all=worst / TRADING_DAYS_PER_YEAR,
        tightest=tightest, stats=statistics_for(len(grid.variations)),
    )
