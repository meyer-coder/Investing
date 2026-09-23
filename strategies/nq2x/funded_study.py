"""Can the NQ 2x strategies survive a FundedNext 25K account?

    python strategies/nq2x/funded_study.py [--out funded_study.json] [--file all.json]

For every strategy, micro contract and stop setting: one cost-free backtest
on the contract's own index (back-adjusted continuous future, daily bars),
its trades priced at one micro contract at today's index level, then replayed
as a fresh Legacy 25K challenge and a fresh funded account from a start every
week (see evotrader/prop.py for the rules).  Start windows:

  older   2010-01 .. 2018-06   never used by the breeding
  train   2019-01 .. 2025-09   the breeding's window
  recent  2025-09 .. 2026-09   the last twelve months (the last six held out)
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from evotrader.data import load_universe                                   # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.prop import MICROS, challenge_stats, funded_stats, trade_paths   # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

STOPS = (None, 0.003, 0.005, 0.0075, 0.01, 0.015, 0.02)      # None = the strategy's own stop, on the close
WINDOWS = {"older": ("2010-01-01", "2018-06-30"), "train": ("2019-01-01", "2025-09-19"),
           "recent": ("2025-09-22", "2026-09-22")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(HERE.parents[1] / "profitable-strategies" / "nq-2x" / "all.json"))
    ap.add_argument("--out")
    ap.add_argument("--micros", default="MNQ,MES,MYM,M2K")
    ap.add_argument("--every", type=int, default=5, help="a new account every N trading days")
    args = ap.parse_args(argv)
    items = json.loads(Path(args.file).read_text())["genomes"]
    data = {}
    for m in args.micros.split(","):
        micro = MICROS[m]
        u = load_universe([micro.data_symbol], "2009-01-01", "2026-09-22")
        data[m] = (micro, u, build_features(u))
    results = []
    for item in items:
        base = Genome.from_dict(item)
        for m, (micro, u, f) in data.items():
            bars = u.bars[micro.data_symbol]
            price_now = float(bars.close[-1])
            for stop in STOPS:
                g = copy.deepcopy(base)
                intrabar = stop is not None
                if intrabar:
                    g.risk.stop_loss_pct = stop
                r = run_backtest(compile_genome(g), u, f, starting_cash=100_000.0, commission_bps=0.0,
                                 slippage_bps=0.0, record_thoughts=False, intrabar_stops=intrabar)
                paths = trade_paths(r.journal.trades, bars, micro=micro, contracts=1, price_now=price_now)
                row = {"name": base.name, "rank": item.get("rank"), "micro": m,
                       "stop": "own, on the close" if stop is None else f"{stop * 100:.2f}% resting",
                       "stop_usd": (None if stop is None else round(stop * price_now * micro.point_value, 0)),
                       "own_stop_usd": round(base.risk.stop_loss_pct * price_now * micro.point_value, 0),
                       "notional": round(price_now * micro.point_value, 0), "windows": {}}
                for w, (a, b) in WINDOWS.items():
                    starts = [i for i, d in enumerate(bars.dates) if a <= d <= b][::args.every]
                    if not starts:
                        continue
                    ch = challenge_stats(paths, starts)
                    fu = funded_stats(paths, starts)
                    row["windows"][w] = {
                        "starts": ch.starts, "pass": ch.pass_rate, "breach": ch.breach_rate,
                        "open": ch.still_open / ch.starts, "days_to_pass": ch.median_days_to_pass,
                        "funded_breach_3m": fu.breach_63, "funded_breach_6m": fu.breach_126,
                        "funded_breach_12m": fu.breach_252, "funded_usd_per_session": fu.mean_pnl_per_day_funded}
                results.append(row)
            tr = next(x for x in results[::-1] if x["micro"] == m and x["stop"] == "own, on the close")["windows"]["train"]
            print(f"{item.get('rank', 0):2d} {base.name[:34]:34} {m}: own stop train pass {tr['pass'] * 100:3.0f}% "
                  f"breach {tr['breach'] * 100:3.0f}%", flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
