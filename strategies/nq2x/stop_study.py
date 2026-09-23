"""What a tighter stop does to the NQ 2x strategies.

    python strategies/nq2x/stop_study.py [--out results.json]

Every published strategy is re-run with its stop loss replaced by a resting
stop order a fixed number of NQ points below the entry (converted to a share
of price at NQ 31,000, today's level), filled inside the bar the way a real
stop order fills.  Also shown: each strategy's own stop as published
(checked on the close) and the same stop as a resting order.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from evotrader.genome import Genome, compile_genome                      # noqa: E402
from evotrader.runner import run_backtest                                 # noqa: E402
from gauntlet import COMMISSION, LEVERAGE, SLIPPAGE, Windows              # noqa: E402

NQ_NOW = 31_000.0
POINTS = (9, 15, 25, 50, 100, 150, 250, 400)
ACCOUNT = 25_000.0


def window_stats(genome: Genome, w: Windows, *, intrabar: bool) -> dict:
    c = compile_genome(genome)
    kw = dict(starting_cash=ACCOUNT, commission_bps=COMMISSION, slippage_bps=SLIPPAGE,
              record_thoughts=False, leverage=LEVERAGE, intrabar_stops=intrabar)
    out = {}
    for name, u, f, start in (("held_out", w.recent, w.f_recent,
                               max(w.cut, w.f_recent.warmup_for(c.feature_names()))),
                              ("train", w.train, w.f_train, None),
                              ("older", w.older, w.f_older, None)):
        r = run_backtest(c, u, f, start_bar=start, **kw)
        j = r.journal
        e = np.asarray(j.equity, dtype=float)
        rets = e[1:] / e[:-1] - 1 if e.size > 2 else np.zeros(1)
        trades = j.trades
        wins = sum(t.pnl for t in trades if t.pnl > 0)
        losses = -sum(t.pnl for t in trades if t.pnl <= 0)
        stopped = [t for t in trades if "stop" in t.exit_reason]
        out[name] = {
            "return": float(e[-1] / e[0] - 1) if e.size > 1 else 0.0,
            "trades": len(trades),
            "win_rate": (sum(t.pnl > 0 for t in trades) / len(trades)) if trades else 0.0,
            "profit_factor": (wins / losses) if losses > 0 else (99.0 if wins > 0 else 0.0),
            "usd_per_session": float(rets.mean()) * ACCOUNT,
            "stopped_share": len(stopped) / len(trades) if trades else 0.0,
            "stopped_same_day": (sum(t.bars_held == 0 for t in stopped) / len(trades)) if trades else 0.0,
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(HERE.parents[1] / "profitable-strategies" / "nq-2x" / "all.json"))
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    items = json.loads(Path(args.file).read_text())["genomes"]
    w = Windows()
    results = []
    for item in items:
        base = Genome.from_dict(item)
        row = {"name": base.name, "rank": item.get("rank"), "own_stop_pct": base.risk.stop_loss_pct,
               "variants": {}}
        row["variants"]["own stop, on the close"] = window_stats(base, w, intrabar=False)
        if base.risk.stop_loss_pct:
            row["variants"]["own stop, resting"] = window_stats(base, w, intrabar=True)
        for pts in POINTS:
            g = copy.deepcopy(base)
            g.risk.stop_loss_pct = pts / NQ_NOW
            row["variants"][f"{pts} pts, resting"] = window_stats(g, w, intrabar=True)
        results.append(row)
        own = row["variants"]["own stop, on the close"]["held_out"]
        nine = row["variants"]["9 pts, resting"]["held_out"]
        print(f"{item.get('rank', 0):2d} {base.name[:36]:36} own stop {own['return'] * 100:+6.1f}% "
              f"${own['usd_per_session']:+5.0f} | 9 pts {nine['return'] * 100:+6.1f}% "
              f"${nine['usd_per_session']:+5.0f}, stopped {nine['stopped_share'] * 100:3.0f}% "
              f"({nine['stopped_same_day'] * 100:3.0f}% on the entry day)", flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
