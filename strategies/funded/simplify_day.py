"""Shrink an evolved same-day genome to the rules that actually matter.

    python strategies/funded/simplify_day.py IN.json OUT.json --symbol YM1! --day-stop 0.01

The NQ 2x simplifier (strategies/nq2x/simplify.py) removes one clause, rule
or risk setting at a time and keeps the change only when every trade is
unchanged.  Here "every trade" is every same-day trade from 2000 to 2026 on
the island's own index, with the island's daily stop and carried positions,
so the slim genome trades exactly the days the evolved one did.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "nq2x"))
sys.path.insert(0, str(HERE))
from simplify import COMMON_START, simplify                                # noqa: E402
from validate import market                                                # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402


class DayJudge:
    def __init__(self, symbol: str, day_stop: float, session: str = "globex") -> None:
        self.u, self.f, self.exec_bars = market(symbol, session)
        self.symbol, self.day_stop = symbol, day_stop

    def signature(self, g: Genome) -> Tuple:
        r = run_backtest(compile_genome(g), self.u, self.f, starting_cash=25_000.0, commission_bps=0.2,
                         slippage_bps=1.0, record_thoughts=False, start_bar=COMMON_START,
                         day_trade=True, carry=True, day_stop=self.day_stop, day_stop_exit=False,
                         exec_bars={self.symbol: self.exec_bars})
        return tuple((t.entry_date, t.exit_date) for t in r.journal.trades)


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--day-stop", type=float, required=True)
    ap.add_argument("--session", default="globex")
    args = ap.parse_args(argv)
    raw = json.loads(Path(args.src).read_text())
    items = raw["genomes"] if isinstance(raw, dict) else raw
    judge = DayJudge(args.symbol, args.day_stop, args.session)
    out = []
    for item in items:
        slim = simplify(item, judge)
        before = sum(len(r["when"]) for r in item["entry_rules"] + item["exit_rules"])
        after = sum(len(r["when"]) for r in slim["entry_rules"] + slim["exit_rules"])
        print(f"{item['name'][:50]:50} rule text {before:4d} -> {after:4d} chars, "
              f"{len(item['entry_rules'])}+{len(item['exit_rules'])} -> "
              f"{len(slim['entry_rules'])}+{len(slim['exit_rules'])} rules", flush=True)
        out.append(slim)
    Path(args.dst).write_text(json.dumps({"genomes": out}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
