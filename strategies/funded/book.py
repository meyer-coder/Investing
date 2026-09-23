"""Several same-day strategies in one FundedNext account.

    python strategies/funded/book.py [--out book.json]

The bred strategies are selective (in the market on 4 to 11% of sessions) and
each passes slowly on its own.  Here their day-by-day P&L is added up, each on
its own micro contract, and the sum is replayed as fresh Legacy challenges and
funded accounts.  A day's worst point is the sum of each strategy's worst,
as if every low came at the same moment: conservative.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from validate import ACCOUNTS, WINDOWS, market                              # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.prop import MICROS, TradePath, challenge_stats, funded_stats, trade_paths  # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402


def daily_pnl(genome: Genome, symbol: str, micro: str, contracts: int,
              day_stop: float) -> Dict[str, Tuple[float, float]]:
    """date -> (realized, worst) for one strategy's same-day trades."""
    u, f, bars = market(symbol, "globex")
    r = run_backtest(compile_genome(genome), u, f, starting_cash=25_000.0, commission_bps=0.2,
                     slippage_bps=1.0, record_thoughts=False, day_trade=True, carry=True,
                     day_stop=day_stop, day_stop_exit=False, exec_bars={symbol: bars})
    paths = trade_paths(r.journal.trades, bars, micro=MICROS[micro], contracts=contracts,
                        price_now=float(bars.close[-1]), slippage_bps=1.0)
    out: Dict[str, Tuple[float, float]] = {}
    for p in paths:
        d = bars.dates[p.entry_bar]
        a, w = out.get(d, (0.0, 0.0))
        out[d] = (a + p.realized, w + p.worst[0])
    return out


def combine(parts: List[Dict[str, Tuple[float, float]]], calendar: List[str]) -> List[TradePath]:
    paths = []
    for k, d in enumerate(calendar):
        hits = [p[d] for p in parts if d in p]
        if hits:
            realized = sum(h[0] for h in hits)
            worst = min(realized, sum(h[1] for h in hits))
            paths.append(TradePath(k, k, [k], [realized], [worst], realized))
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picked", default=str(HERE / "bred" / "candidates.json"))
    ap.add_argument("--out", default=str(ROOT / "profitable-strategies" / "funded" / "reports" / "book.json"))
    args = ap.parse_args(argv)
    cands = json.loads(Path(args.picked).read_text())["strategies"]
    parts = {c["key"]: daily_pnl(Genome.from_dict(c["genome"]), c["settings"]["symbol"],
                                 c["settings"]["micro"], c["settings"].get("contracts", 1),
                                 c["settings"]["day_stop"]) for c in cands}
    calendar = sorted(set(market("ES1!", "globex")[2].dates) | set(market("YM1!", "globex")[2].dates))
    rows = []
    for n in range(1, len(cands) + 1):
        for combo in itertools.combinations([c["key"] for c in cands], n):
            paths = combine([parts[k] for k in combo], calendar)
            row = {"book": list(combo), "windows": {}}
            for w, (a, b) in WINDOWS.items():
                idx = [i for i, d in enumerate(calendar) if a <= d <= b]
                starts = idx[::5]
                pnl = [p.realized for p in paths if idx and idx[0] <= p.entry_bar <= idx[-1]]
                row["windows"][w] = {"usd_per_session": round(sum(pnl) / max(len(idx), 1), 2),
                                     "days_traded": len(pnl), "worst_day": round(min(pnl), 0) if pnl else 0.0}
                for acct, (rules, funded_rules) in ACCOUNTS.items():
                    if acct == "100K":
                        continue
                    ch = challenge_stats(paths, starts, rules)
                    fu = funded_stats(paths, starts, funded_rules)
                    row["windows"][w][acct] = {"pass": round(ch.pass_rate, 3), "breach": round(ch.breach_rate, 3),
                                               "days_to_pass": ch.median_days_to_pass,
                                               "funded_breach_6m": round(fu.breach_126, 3)}
            rows.append(row)
            print(" + ".join(combo), "|", " | ".join(
                f"{w} ${row['windows'][w]['usd_per_session']:5.1f} 25K {row['windows'][w]['25K']['pass']:.2f}/"
                f"{row['windows'][w]['25K']['breach']:.2f} 50K {row['windows'][w]['50K']['pass']:.2f}/"
                f"{row['windows'][w]['50K']['breach']:.2f}" for w in ("oldest", "older", "train", "last_12m")),
                flush=True)
    Path(args.out).write_text(json.dumps({"windows": WINDOWS, "rows": rows}, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
