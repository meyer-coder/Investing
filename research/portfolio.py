"""Stack the edges that survived research/edges.py on one account.

1. From research/edges.json, the confirmed variants; of those, one per market
   and family -- the one with the best search-period t, so near-copies of
   one idea do not count as separate edges.
2. Each edge's daily dollars at one micro contract (today's contract value,
   costs included), and each trade's worst open loss.
3. Equal risk: contracts in proportion to 1 / the edge's daily swing on the
   data up to 2022.
4. The whole book is scaled for a Topstep 100K funded account (keeping
   $3,000 after each payout): the largest scale at which 80% of one-year
   funded runs started in 2020-2022 survive, rounded to whole contracts.
5. The result is judged on 2023-2026, which played no part in any choice.

A day's worst point is taken as the sum of every trade's worst point that
day, as if they all happened at once -- cautious.

    python research/portfolio.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from typing import Dict, List

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edges as E  # noqa: E402
from shortbot import backtest as bt  # noqa: E402
from shortbot.config import ACCOUNTS  # noqa: E402

FIT_END = E.CONFIRM_END
HORIZON = 252              # funded-account survival and pay: one year
PLAN = 504                 # the whole plan (challenge, funded, again): two years
EVERY = 5


def family(variant: str) -> str:
    return variant.split()[0]


def pick(rows: List[dict]) -> List[dict]:
    best: Dict[tuple, dict] = {}
    for r in rows:
        if not r["confirmed"]:
            continue
        k = (r["market"], family(r["variant"]))
        if k not in best or r["search"]["t"] > best[k]["search"]["t"]:
            best[k] = r
    return list(best.values())


def daily_series(r: dict, loaded: Dict[str, dict]):
    m = E.BY_KEY[r["market"]]
    if m.key not in loaded:
        loaded[m.key] = E.load(m)
    D = loaded[m.key]
    fn = dict(E.VARIANTS)[r["variant"]]
    usd, worst = {}, {}
    for t in fn(D):
        usd[t.day] = usd.get(t.day, 0.0) + (t.gross - m.cost) * m.notional
        worst[t.day] = worst.get(t.day, 0.0) + (t.worst - m.cost) * m.notional
    return usd, worst


def book_days(series, contracts, days):
    """Per day, one aggregated trade: (pnl, worst)."""
    out = {}
    for (usd, worst), n in zip(series, contracts):
        if n == 0:
            continue
        for d, v in usd.items():
            p, w = out.get(d, (0.0, 0.0))
            out[d] = (p + n * v, w + n * worst[d])
    return {d: [bt.Trade(d, "book", 0, 0, 0, 0, 1, 0, 0, round(p, 2), round(min(w, p, 0.0), 2), "", "")]
            for d, (p, w) in out.items() if d in days}


def survival(by_day, dates, rules, starts) -> float:
    alive = [bt.funded_attempt(by_day, dates[k:k + HORIZON], rules).outcome != "blown" for k in starts]
    return float(np.mean(alive)) if alive else 0.0


def main() -> None:
    rows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "edges.json")))
    chosen = pick(rows)
    if not chosen:
        print("no confirmed edges")
        return
    loaded: Dict[str, dict] = {}
    series = [daily_series(r, loaded) for r in chosen]
    dates = sorted({str(d) for D in loaded.values() for d in D["dates"]})
    # common calendar: days every chosen market traded
    common = set(dates)
    for D in loaded.values():
        common &= {str(d) for d in D["dates"]}
    dates = sorted(common)
    fit = [d for d in dates if d <= FIT_END]
    vols = []
    for usd, _ in series:
        x = np.array([usd.get(d, 0.0) for d in fit])
        vols.append(x.std(ddof=1))
    print(f"{len(chosen)} edges, one per market and family:")
    for r, v in zip(chosen, vols):
        f = r["final"]
        print(f"   {r['contract']:<4} {r['variant']:<26} daily swing at 1 contract ${v:6.0f}; "
              f"final 2023-26 {f['mean_bp']:+.2f} bp a trade, t={f['t']:+.1f}")
    X = np.array([[s[0].get(d, 0.0) for d in dates] for s in series])
    if len(series) > 1:
        corr = np.corrcoef(X[:, [i for i, d in enumerate(dates) if d <= FIT_END]])
        off = corr[np.triu_indices(len(series), 1)]
        print(f"   daily correlation between edges (to 2022): mean {off.mean():+.2f}, max {off.max():+.2f}")

    w = np.array([1.0 / v for v in vols])
    w = w / w.max()                                         # the steadiest edge gets 1 unit
    rules = replace(ACCOUNTS["100k"], payout_keep=3_000.0)
    fit_starts = [k for k in range(0, len(dates) - HORIZON, EVERY) if "2020" <= dates[k] <= FIT_END]
    best = None
    for scale in np.arange(1, 41):
        contracts = [int(round(scale * x)) for x in w]
        if not any(contracts):
            continue
        by_day = book_days(series, contracts, set(dates))
        s = survival(by_day, dates, rules, fit_starts)
        if s >= 0.80:
            best = (scale, contracts, s)
    note = "80%+ survive a year on 2020-2022 starts"
    if best is None:                                        # even the smallest book is too big
        contracts = [max(0, int(round(x))) for x in w]
        by_day = book_days(series, contracts, set(dates))
        best = (1, contracts, survival(by_day, dates, rules, fit_starts))
        note = "the smallest book; no size reaches 80% survival on 2020-2022 starts"
    scale, contracts, s = best
    print(f"\nSized for a Topstep 100K funded account ({note}; {s * 100:.0f}% survive):")
    for r, n in zip(chosen, contracts):
        print(f"   {n:>3} x {r['contract']:<4} {r['variant']}")
    by_day = book_days(series, contracts, set(dates))
    for label, lo, hi in (("up to 2019", "0000", E.SEARCH_END), ("2020-2022", "2020-01-01", FIT_END),
                          ("2023-2026 (unseen)", "2023-01-01", "9999")):
        ds = [d for d in dates if lo <= d <= hi]
        pnl = np.array([by_day[d][0].pnl_usd if d in by_day else 0.0 for d in ds])
        sharpe = pnl.mean() / pnl.std(ddof=1) * np.sqrt(252) if pnl.std() > 0 else 0.0
        starts = [k for k in range(len(dates) - HORIZON) if lo <= dates[k] <= hi][::EVERY]
        surv = survival(by_day, dates, rules, starts) if starts else float("nan")
        funded = [bt.funded_attempt(by_day, dates[k:k + HORIZON], rules) for k in starts]
        paid = np.mean([f.paid_to_trader for f in funded]) / HORIZON if funded else float("nan")
        cyc = [bt.cycle(by_day, dates[k:k + PLAN], rules) for k in starts if k + PLAN <= len(dates)]
        net = np.median([c.net for c in cyc]) / PLAN if cyc else float("nan")
        print(f"   {label:<19} book ${pnl.mean():+6.1f}/day, Sharpe {sharpe:4.2f}, worst day ${pnl.min():+,.0f} | "
              f"funded a year: {surv * 100:3.0f}% survive, ${paid:+.0f}/day paid | two-year plan: median "
              f"${net:+.0f}/day after fees")


if __name__ == "__main__":
    main()
