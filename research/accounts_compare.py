"""The FundedNext Legacy 25K against the Topstep 100K, running Bot A (the
noise-area breakout, research/noise_breakout.py) at 1-4 MNQ.

For every fifth session a fresh run starts and lives two years: challenge,
funded account, and a new challenge after every loss, with every fee counted
(shortbot.backtest.cycle).  Trades are priced at today's NQ level.  The
account rules are in shortbot/config.py (ACCOUNTS).

    python research/accounts_compare.py
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duka import sessions as duka_sessions  # noqa: E402
from noise_breakout import MNQ_NOTIONAL, day_arrays, run  # noqa: E402
from shortbot import backtest as bt  # noqa: E402
from shortbot.config import ACCOUNTS  # noqa: E402

HORIZON = 504            # two years of sessions
EVERY = 5


def as_trades(noise_trades, contracts: int) -> Dict[str, List[bt.Trade]]:
    by_day: Dict[str, List[bt.Trade]] = {}
    for t in noise_trades:
        usd = MNQ_NOTIONAL * contracts
        by_day.setdefault(t.day, []).append(bt.Trade(
            t.day, "noise", t.entry_min, t.exit_min, 0.0, 0.0, contracts, 0.0, 0.0,
            round(t.ret * usd, 2), round(t.worst * usd, 2), t.why, "", t.side))
    return by_day


def main() -> None:
    ss = duka_sessions(1)
    D = day_arrays(ss)
    trades = run(D)
    dates = [str(d) for d in D["dates"][14:]]
    print(f"Bot A: {len(trades):,} trades, {dates[0]} .. {dates[-1]}; runs start every {EVERY}th session "
          f"and live {HORIZON} sessions (two years)\n")
    halves = (("2013-2019 starts", lambda d: d <= "2019-12-31"), ("2020-2024 starts", lambda d: "2020" <= d <= "2024-09-30"))
    for key in ("fn-legacy-25k", "100k"):
        rules = ACCOUNTS[key]
        print(f"== {rules.name}: ${rules.max_loss:,.0f} max loss, ${rules.profit_target:,.0f} target, "
              f"{'no daily limit' if not rules.daily_loss else f'${rules.daily_loss:,.0f} daily limit'}, "
              f"{int(rules.payout_split * 100)}% split, payouts up to ${rules.payout_cap:,.0f}")
        for n in (1, 2, 3, 4):
            by_day = as_trades(trades, n)
            cells = []
            for label, keep in halves:
                starts = [k for k in range(0, len(dates) - HORIZON, EVERY) if keep(dates[k])]
                att = [bt.combine_attempt(by_day, dates[k:k + HORIZON], rules) for k in starts]
                done = [a for a in att if a.outcome != "unfinished"]
                passed = sum(a.outcome == "passed" for a in done)
                fund = [bt.funded_attempt(by_day, dates[k:k + HORIZON], rules) for k in starts]
                lost3 = np.mean([f.outcome == "blown" and f.days <= 63 for f in fund])
                lost12 = np.mean([f.outcome == "blown" and f.days <= 252 for f in fund])
                nets = np.array([bt.cycle(by_day, dates[k:k + HORIZON], rules).net / 2 for k in starts])
                cells.append(f"pass {passed / max(len(done), 1) * 100:3.0f}% | funded lost <3mo "
                             f"{lost3 * 100:3.0f}% <1y {lost12 * 100:3.0f}% | net/yr median "
                             f"${np.median(nets):+6,.0f} (below 0: {np.mean(nets < 0) * 100:3.0f}%)")
            print(f"   {n} MNQ   {cells[0]}")
            print(f"           {cells[1]}")
        print()


if __name__ == "__main__":
    main()
