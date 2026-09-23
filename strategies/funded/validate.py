"""Check the day-trade islands' best agents on history they never saw.

    python strategies/funded/validate.py RUN_ID [RUN_ID ...] [--top 8] [--out validation.json]

Each island trained up to 2026-03-20 (from 2019 or from 2010) with the
FundedNext fitness on its own account size.
Its best distinct agents are re-run with the island's own settings (index,
micro contract, session, daily stop) from 1999 and judged on:

  oldest    2000-2009, never seen by any breeding here
  older     2010-2018, seen only by the islands trained from 2010
  train     2019-01 .. 2026-03-20, selected on by every island
  held_out  2026-03-23 .. 2026-09-22, never used for selection
  last_12m  2025-09-22 .. 2026-09-22
  stress    the train window again at three times the per-contract costs

Numbers are dollars on one micro contract at today's index level, and fresh
Legacy challenges and funded accounts of the island's size started every week
(evotrader/prop.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from day_trades import daily, window_stats                                  # noqa: E402
from evotrader.data import CASH_PROXIES, cash_session_bars, load_symbol, load_universe  # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.prop import (LEGACY_25K, LEGACY_25K_FUNDED, LEGACY_50K, LEGACY_50K_FUNDED,  # noqa: E402
                            LEGACY_100K, LEGACY_100K_FUNDED, MICROS, trade_paths)
from evotrader.runner import run_backtest                                   # noqa: E402
from evotrader.store import Store                                           # noqa: E402

ACCOUNTS = {"25K": (LEGACY_25K, LEGACY_25K_FUNDED), "50K": (LEGACY_50K, LEGACY_50K_FUNDED),
            "100K": (LEGACY_100K, LEGACY_100K_FUNDED)}

START, END = "1999-01-01", "2026-09-22"
WINDOWS = {"oldest": ("2000-01-01", "2009-12-31"), "older": ("2010-01-01", "2018-12-31"),
           "train": ("2019-01-01", "2026-03-20"), "held_out": ("2026-03-23", "2026-09-22"),
           "last_12m": ("2025-09-22", "2026-09-22")}

_cache: Dict[tuple, tuple] = {}


def market(symbol: str, session: str):
    key = (symbol, session)
    if key not in _cache:
        u = load_universe([symbol], START, END)
        bars = u.bars[symbol]
        exec_bars = bars
        if session == "cash":
            exec_bars = cash_session_bars(bars, load_symbol(CASH_PROXIES[symbol], START, END))
        _cache[key] = (u, build_features(u), exec_bars)
    return _cache[key]


def evaluate(genome: Genome, cfg: dict) -> dict:
    symbol = cfg["symbols"][0]
    micro = MICROS[cfg["prop_micro"]]
    u, f, exec_bars = market(symbol, cfg.get("session", "globex"))
    r = run_backtest(compile_genome(genome), u, f, starting_cash=cfg["starting_cash"],
                     commission_bps=cfg["commission_bps"], slippage_bps=cfg["slippage_bps"],
                     record_thoughts=False, leverage=cfg.get("leverage", 1.0),
                     intrabar_stops=cfg.get("intrabar_stops", False),
                     day_trade=cfg.get("day_trade", False), carry=cfg.get("carry", False),
                     day_stop=cfg.get("day_stop", 0.0), day_stop_exit=cfg.get("day_stop_exit", True),
                     exec_bars={symbol: exec_bars})
    price_now = float(exec_bars.close[-1])
    rules, funded_rules = ACCOUNTS[cfg.get("prop_account", "25K")]
    out = {"notional": round(price_now * micro.point_value, 0), "account": cfg.get("prop_account", "25K"),
           "windows": {}}
    for label, m in (("normal", micro), ("stress", replace(micro, commission=3 * micro.commission,
                                                            tick=3 * micro.tick))):
        paths = trade_paths(r.journal.trades, exec_bars, micro=m, contracts=1,
                            price_now=price_now, slippage_bps=cfg["slippage_bps"])
        pnl, low, held = daily(paths, len(exec_bars))
        if label == "normal":
            for w, (a, b) in WINDOWS.items():
                out["windows"][w] = window_stats(paths, exec_bars.dates, pnl, low, held, a, b,
                                                 rules=rules, funded_rules=funded_rules)
        else:
            a, b = WINDOWS["train"]
            out["windows"]["stress"] = window_stats(paths, exec_bars.dates, pnl, low, held, a, b,
                                                    rules=rules, funded_rules=funded_rules)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--db", default=str(ROOT / "runs" / "evotrader.sqlite"))
    ap.add_argument("--out", default=str(ROOT / "profitable-strategies" / "funded" / "reports"
                                         / "validation.json"))
    args = ap.parse_args(argv)
    store = Store(args.db)
    rows: List[dict] = []
    for run_id in args.runs:
        cfg = store.run_config(run_id)
        board = store.leaderboard(run_id, limit=args.top)
        for rank, e in enumerate(board, 1):
            g = store.get_genome(e["genome_id"])
            res = evaluate(g, cfg)
            rows.append({"run": run_id, "island": f"{cfg['prop_micro']} {cfg.get('session', 'globex')}",
                         "day_stop": cfg.get("day_stop", 0.0), "rank": rank, "train_score": e["score"],
                         "test_score": e.get("test_score"), "genome": g.to_dict(), **res})
            w = res["windows"]
            print(f"{run_id} #{rank} {g.name[:30]:30} {res['account']:>4} score {e['score']:+.3f} | "
                  + " | ".join(f"{k} ${w[k]['usd_per_session']:5.1f} {w[k]['pass']:.2f}/{w[k]['breach']:.2f}"
                               for k in ("oldest", "older", "train", "held_out", "stress") if w.get(k)),
                  flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"windows": WINDOWS, "rows": rows}, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
