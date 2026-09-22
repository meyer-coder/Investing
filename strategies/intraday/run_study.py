"""First-pass study of intraday NQ candidates on the local TradingView store.

Usage: python strategies/intraday/run_study.py [5|15|60 ...]

Reads strategies/intraday/nq_candidates_<tf>m.json, runs every candidate on
the bars in data/cache/tv (fill it with `evotrader tv-fetch`), and prints the
Strategy Tester numbers plus a per-session P&L distribution in NQ points and
in dollars per MNQ contract ($2 a point).  Long-only, next-open fills,
commission and slippage as the candidates file says.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evotrader.tv_mcp import Backtester, _run, _strategy_from  # noqa: E402

ET = ZoneInfo("America/New_York")
MNQ_POINT = 2.0


def session_of(stamp: str) -> dt.date:
    naive = dt.datetime.strptime(stamp[:16], "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=dt.timezone.utc).astimezone(ET).date()


def study(tf: str, view: Backtester) -> None:
    spec = json.loads(Path(__file__).with_name(f"nq_candidates_{tf}m.json").read_text())
    symbol, costs = spec["symbol"], spec["costs"]
    universe = view.universe([symbol], tf, 20_000, "tradingview")
    first, last = universe.date_range()
    sessions = sorted({session_of(d) for d in universe.bars[symbol].dates})
    print(f"\n=== {symbol} {tf}m  {first} .. {last}  ({len(universe)} bars, "
          f"{len(sessions)} sessions)  costs {costs['commission_bps']}+{costs['slippage_bps']} bp/side")
    header = (f"{'strategy':38} {'trades':>6} {'win':>5} {'PF':>5} {'ret':>7} {'mdd':>6} "
              f"{'avg pts':>8} {'per session':>12} {'best':>7} {'worst':>7} {'p10':>6} {'p90':>6} {'active':>7}")
    print(header)
    rows = []
    for cand in spec["strategies"]:
        genome = _strategy_from(cand, name_default=cand["name"])
        run = _run(view, genome, universe, tf, starting_cash=25_000.0,
                   commission_bps=costs["commission_bps"], slippage_bps=costs["slippage_bps"])
        m = run["metrics"]
        by_day: dict = defaultdict(float)
        points = []
        for t in run["journal"].trades:
            pts = t.pnl / t.shares if t.shares else 0.0
            points.append(pts)
            by_day[session_of(t.exit_date)] += pts
        daily = np.array([by_day.get(s, 0.0) for s in sessions])
        active = float((daily != 0).mean()) if len(daily) else 0.0
        rows.append((cand["name"], m, points, daily, active))
    rows.sort(key=lambda r: -float(np.sum(r[3])))
    for name, m, points, daily, active in rows:
        avg_pts = float(np.mean(points)) if points else 0.0
        print(f"{name:38} {m.trades:6d} {m.win_rate*100:4.0f}% {m.profit_factor:5.2f} "
              f"{m.total_return*100:+6.1f}% {m.max_drawdown*100:5.1f}% "
              f"{avg_pts:+8.1f} {daily.mean():+8.1f} pts "
              f"{daily.max():+7.0f} {daily.min():+7.0f} {np.percentile(daily, 10):+6.0f} "
              f"{np.percentile(daily, 90):+6.0f} {active*100:6.0f}%")
    print(f"\n$ per session at 1 MNQ = points x {MNQ_POINT:.0f}; at 1 NQ = points x 20. "
          f"Per-session figures include flat sessions.")
    # by month, for a rough forward read
    print(f"\n{'strategy':38} " + " ".join(f"{'%s' % m:>14}" for m in sorted({s.strftime('%Y-%m') for s in sessions})))
    for name, m, points, daily, active in rows:
        cells = []
        for month in sorted({s.strftime('%Y-%m') for s in sessions}):
            mask = np.array([s.strftime('%Y-%m') == month for s in sessions])
            n = int((daily[mask] != 0).sum())
            cells.append(f"{daily[mask].sum():+7.0f} pts/{n:2d}d")
        print(f"{name:38} " + " ".join(f"{c:>14}" for c in cells))


def main(argv):
    tfs = argv or ["15", "5"]
    view = Backtester(source="tradingview", refresh=False)
    try:
        for tf in tfs:
            study(tf, view)
    finally:
        view.close()


if __name__ == "__main__":
    main(sys.argv[1:])
