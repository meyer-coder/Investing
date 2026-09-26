"""How many edges as good as Bot A would one Topstep 100K need to pay $50-60 a day?

Only one edge survived research/edges.py, so the others are stand-ins: Bot A's
own daily dollars at 1 MNQ, shifted in time by an equal share of the history
for each extra edge.  Every stand-in has Bot A's exact size of wins and losses
but falls on different days, as an unrelated edge would.  This is an estimate
of what is needed, not a strategy.

For N stand-ins, each is traded at the same size (fractions of an MNQ allowed,
to show the trend).  The largest size at which at least 80% of one-year funded
runs survive is kept (Topstep 100K, keeping $3,000 after each payout; starts
every 10 sessions over 2013-2026).

    python research/edges_needed.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portfolio as P  # noqa: E402
from shortbot import backtest as bt  # noqa: E402
from shortbot.config import ACCOUNTS  # noqa: E402


def main() -> None:
    rows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "edges.json")))
    loaded: dict = {}
    usd, worst = P.daily_series(P.pick(rows)[0], loaded)
    dates = sorted({str(d) for D in loaded.values() for d in D["dates"]})
    x = np.array([usd.get(d, 0.0) for d in dates])
    w = np.array([worst.get(d, 0.0) for d in dates])
    rules = replace(ACCOUNTS["100k"], payout_keep=3_000.0)
    starts = list(range(0, len(dates) - P.HORIZON, 10))
    print(f"Bot A at 1 MNQ: ${x.mean():.1f} a day, Sharpe {x.mean() / x.std() * np.sqrt(252):.2f}\n")
    print("edges | book Sharpe | MNQ each | book a day | paid to you a day | survive a year")
    for n in (1, 2, 3, 4, 6, 8, 12):
        shifts = [int(i * len(x) / n) for i in range(n)]
        X = sum(np.roll(x, s) for s in shifts)
        W = sum(np.roll(w, s) for s in shifts)
        best = None
        for scale in np.arange(0.1, 1.51, 0.1):
            by_day = {d: [bt.Trade(d, "book", 0, 0, 0, 0, 1, 0, 0, round(scale * X[i], 2),
                                   round(min(scale * W[i], scale * X[i], 0.0), 2), "", "")]
                      for i, d in enumerate(dates)}
            runs = [bt.funded_attempt(by_day, dates[k:k + P.HORIZON], rules) for k in starts]
            alive = np.mean([r.outcome != "blown" for r in runs])
            if alive >= 0.80:
                best = (scale, alive, np.mean([r.paid_to_trader for r in runs]) / P.HORIZON)
        sharpe = X.mean() / X.std() * np.sqrt(252)
        if best is None:
            print(f"{n:5d} | {sharpe:11.2f} | no size keeps 80% alive")
            continue
        scale, alive, paid = best
        print(f"{n:5d} | {sharpe:11.2f} | {scale:8.1f} | ${scale * X.mean():9.0f} | ${paid:16.0f} | "
              f"{alive * 100:13.0f}%")


if __name__ == "__main__":
    main()
