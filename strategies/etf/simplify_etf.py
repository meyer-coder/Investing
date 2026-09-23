"""Shrink an evolved ETF strategy to the rules that matter, every trade unchanged.

    from simplify_etf import slim            # slim(genome_dict, symbols) -> genome_dict

The NQ simplifier (strategies/nq2x/simplify.py) drops one clause, rule or risk
setting at a time and keeps the change only when the trade list is identical.
Here the trade list is every trade from 2012 to today on the strategy's own
funds, compared past the longest warm-up.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "nq2x"))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from simplify import simplify                                              # noqa: E402
from gauntlet import ACCOUNT, SLIP, market                                 # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

COMMON_START = "2012-03-01"      # past the 52-week warm-up from the 2011 start


class EtfJudge:
    def __init__(self, symbols: Sequence[str]) -> None:
        self.u, self.f = market(symbols)
        self.start = next(i for i, d in enumerate(self.u.calendar) if d >= COMMON_START)

    def signature(self, g: Genome) -> Tuple:
        r = run_backtest(compile_genome(g), self.u, self.f, starting_cash=ACCOUNT, commission_bps=0.0,
                         slippage_bps=SLIP, record_thoughts=False, start_bar=self.start)
        return tuple((t.symbol, t.entry_date, t.exit_date) for t in r.journal.trades)


def slim(item: dict, symbols: Sequence[str]) -> dict:
    return simplify(item, EtfJudge(symbols))
