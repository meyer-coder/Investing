"""Does sizing Bot A by the day's volatility raise what one Topstep 100K pays?

Six sizing rules, fixed before any result:

* fixed 1 MNQ, fixed 2 MNQ;
* volatility-scaled, base 1, 2 or 3: contracts = round(base x the median
  average daily range of the prior year / the average daily range of the
  prior 14 sessions), between 0 and 4 -- fewer contracts on wild days, more
  on calm ones (both known before the open);
* volatility-scaled base 2 with a daily guard: after the day's first losing
  trade, no more trades that day.

A rule is chosen on 2013-2022 starts (most paid a day with at least 80% of
one-year funded runs surviving) and judged on 2023-2026 starts.  Funded
account: Topstep 100K, keeping $3,000 after each payout (shortbot.config).

    python research/size_bot_a.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from typing import Callable, Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duka import sessions as duka_sessions  # noqa: E402
from noise_breakout import MNQ_NOTIONAL, day_arrays, run  # noqa: E402
from shortbot import backtest as bt  # noqa: E402
from shortbot.config import ACCOUNTS  # noqa: E402

YEAR, PLAN, EVERY = 252, 504, 5


def main() -> None:
    ss = duka_sessions(1)
    D = day_arrays(ss)
    trades = run(D)
    dates = [str(d) for d in D["dates"]]
    rng = (D["H"].max(axis=1) - D["L"].min(axis=1)) / D["O"][:, 0]
    adr = {dates[i]: rng[i - 14:i].mean() for i in range(14, len(dates))}
    ref = {dates[i]: np.median(rng[max(0, i - 252):i]) for i in range(14, len(dates))}

    def vol_scaled(base: float) -> Callable[[str], int]:
        return lambda d: int(np.clip(round(base * ref[d] / adr[d]), 0, 4))

    rules_sizes: Dict[str, Callable[[str], int]] = {
        "fixed 1 MNQ": lambda d: 1,
        "fixed 2 MNQ": lambda d: 2,
        "vol-scaled, base 1": vol_scaled(1),
        "vol-scaled, base 2": vol_scaled(2),
        "vol-scaled, base 3": vol_scaled(3),
        "vol-scaled base 2 + stop after a losing trade": vol_scaled(2),
    }
    by_day_trades: Dict[str, list] = {}
    for t in trades:
        by_day_trades.setdefault(t.day, []).append(t)
    days = [d for d in dates if d in adr]
    acct = replace(ACCOUNTS["100k"], payout_keep=3_000.0)

    def book(name: str) -> Dict[str, List[bt.Trade]]:
        size = rules_sizes[name]
        guard = "stop after" in name
        out: Dict[str, List[bt.Trade]] = {}
        for d, ts in by_day_trades.items():
            if d not in adr:
                continue
            n = size(d)
            if n == 0:
                continue
            for t in ts:
                usd = MNQ_NOTIONAL * n
                out.setdefault(d, []).append(bt.Trade(d, "A", t.entry_min, t.exit_min, 0, 0, n, 0, 0,
                                                      round(t.ret * usd, 2), round(t.worst * usd, 2), "", "", t.side))
                if guard and t.ret < 0:
                    break
        return out

    print("Bot A on a Topstep 100K funded account, keeping $3,000 after payouts.")
    print("Each cell: share of one-year funded runs that survive | paid to you a day | two-year plan median a day\n")
    periods = (("2013-2022 starts (choose)", "0000", "2022-12-31"), ("2023-2026 starts (judge)", "2023-01-01", "9999"))
    results = {}
    for name in rules_sizes:
        by_day = book(name)
        cells = []
        for label, lo, hi in periods:
            starts = [k for k in range(0, len(days) - YEAR, EVERY) if lo <= days[k] <= hi]
            f = [bt.funded_attempt(by_day, days[k:k + YEAR], acct) for k in starts]
            surv = np.mean([x.outcome != "blown" for x in f])
            paid = np.mean([x.paid_to_trader for x in f]) / YEAR
            plan_starts = [k for k in starts if k + PLAN <= len(days)]
            plan = np.median([bt.cycle(by_day, days[k:k + PLAN], acct).net for k in plan_starts]) / PLAN \
                if plan_starts else float("nan")
            cells.append((surv, paid, plan))
        results[name] = cells
        (s1, p1, q1), (s2, p2, q2) = cells
        avg_n = np.mean([len(v) and v[0].contracts for v in by_day.values()])
        print(f"   {name:<46} avg {avg_n:3.1f} MNQ | choose: {s1 * 100:3.0f}% ${p1:5.1f} ${q1:+6.1f} | "
              f"judge: {s2 * 100:3.0f}% ${p2:5.1f} ${q2:+6.1f}")
    ok = {k: v for k, v in results.items() if v[0][0] >= 0.80}
    if ok:
        pick = max(ok, key=lambda k: ok[k][0][1])
        s2, p2, q2 = results[pick][1]
        print(f"\nChosen on 2013-2022: {pick}.  On 2023-2026 it kept {s2 * 100:.0f}% of funded accounts a "
              f"year and paid ${p2:.1f} a day.")
    else:
        print("\nNo rule kept 80% of funded accounts alive on 2013-2022.")


if __name__ == "__main__":
    main()
