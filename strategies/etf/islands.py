"""Island configs for the leveraged-ETF grind.

    python strategies/etf/islands.py WAVE      # writes configs/etf/<wave>_*.json, prints their paths

Every island: a $25,000 cash account, one position with the whole account
(style etf_full), trained 2011-2026-03-20 with the last six months held out,
0 commission and 8 bp slippage a side (tight for SOXL/TQQQ, fair for the
single-stock funds), mutation breeding.  The fitness rewards the average daily
return (dollars a session), Sharpe and win rate, charges drawdowns past 35%,
and weights the last year at half.  Single-stock funds trade on their
synthetic daily-reset series (strategies/etf/synth.py), which reach back to
2011; the real funds are checked in the gauntlet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

UNIVERSES = {
    "soxl": ["SOXL", "SOXS"], "soxl_long": ["SOXL"], "tqqq": ["TQQQ", "SQQQ"], "tqqq_long": ["TQQQ"],
    "tecl": ["TECL", "TECS"], "tecl_long": ["TECL"], "usd": ["USD"], "rom": ["ROM"], "qld": ["QLD"],
    "nvda": ["NVDA.2X"], "nvda_ls": ["NVDA.2X", "NVDA.-2X"], "amd": ["AMD.2X"], "avgo": ["AVGO.2X"],
    "tsm": ["TSM.2X"], "mu": ["MU.2X"], "smci": ["SMCI.2X"], "msft": ["MSFT.2X"], "aapl": ["AAPL.2X"],
    "googl": ["GOOGL.2X"], "meta": ["META.2X"], "amzn": ["AMZN.2X"], "tsla": ["TSLA.2X"],
    "orcl": ["ORCL.2X"], "ftec2": ["FTEC.2X"], "ftec3": ["FTEC.3X"],
    "semis": ["SOXL", "NVDA.2X", "AMD.2X", "AVGO.2X", "TSM.2X", "MU.2X"],
    "gpu": ["NVDA.2X", "AMD.2X"],
    "ai": ["NVDA.2X", "AVGO.2X", "TSM.2X", "MSFT.2X", "GOOGL.2X", "META.2X", "AMZN.2X"],
    "megacap": ["MSFT.2X", "AAPL.2X", "GOOGL.2X", "META.2X", "AMZN.2X"],
    "index3x": ["SOXL", "TQQQ", "TECL"], "index3x_ls": ["SOXL", "SOXS", "TQQQ", "SQQQ", "TECL", "TECS"],
    "memory": ["MU.2X", "SOXL"],
    "tsm_usd": ["TSM.2X", "USD"], "amd_tsm": ["AMD.2X", "TSM.2X"], "mu_tsm": ["MU.2X", "TSM.2X"],
    "amd_mu": ["AMD.2X", "MU.2X"], "avgo_tsm_nvda": ["AVGO.2X", "TSM.2X", "NVDA.2X"],
}

FITNESS = {
    "reliable": dict(sharpe_weight=1.0, excess_weight=0.0, return_weight=0.5, consistency_weight=3.0,
                     drawdown_limit=0.35, drawdown_penalty=2.0, turnover_limit=400.0, turnover_penalty=0.0,
                     min_trades=40, inactivity_penalty=1.5, max_trades=6000, overtrading_penalty=0.0,
                     ruin_threshold=-0.7, ruin_penalty=5.0, win_rate_weight=0.5, hold_limit_bars=0.0,
                     hold_penalty=0.0, recent_bars=252, recent_weight=0.3),
    "dollars": dict(sharpe_weight=1.0, excess_weight=0.0, return_weight=1.0, drawdown_limit=0.35,
                    drawdown_penalty=2.0, turnover_limit=400.0, turnover_penalty=0.0, min_trades=40,
                    inactivity_penalty=1.5, max_trades=6000, overtrading_penalty=0.0, ruin_threshold=-0.7,
                    ruin_penalty=5.0, win_rate_weight=0.5, hold_limit_bars=0.0, hold_penalty=0.0,
                    recent_bars=252, recent_weight=0.5),
    "steady": dict(sharpe_weight=1.5, excess_weight=0.0, return_weight=0.6, drawdown_limit=0.20,
                   drawdown_penalty=4.0, turnover_limit=400.0, turnover_penalty=0.0, min_trades=40,
                   inactivity_penalty=1.5, max_trades=6000, overtrading_penalty=0.0, ruin_threshold=-0.5,
                   ruin_penalty=5.0, win_rate_weight=2.0, hold_limit_bars=6.0, hold_penalty=0.5,
                   recent_bars=252, recent_weight=0.5),
    "trend": dict(sharpe_weight=1.0, excess_weight=0.0, return_weight=1.5, drawdown_limit=0.45,
                  drawdown_penalty=1.5, turnover_limit=400.0, turnover_penalty=0.0, min_trades=25,
                  inactivity_penalty=1.0, max_trades=6000, overtrading_penalty=0.0, ruin_threshold=-0.75,
                  ruin_penalty=5.0, win_rate_weight=0.3, hold_limit_bars=0.0, hold_penalty=0.0,
                  recent_bars=252, recent_weight=0.6),
}


def config(name: str, universe: str, fitness: str, seed: int, *, generations: int = 30,
           population: int = 60, seed_file: str = "") -> dict:
    return {
        "symbols": UNIVERSES[universe], "start": "2011-01-01", "end": "2026-09-22",
        "offline": False, "refresh_data": False, "test_frac": 0.0, "test_start": "2026-03-23",
        "leverage": 1.0, "population": population, "generations": generations, "elites": 5,
        "survivor_reports": 5, "seed": seed, "starting_cash": 25000.0, "commission_bps": 0.0,
        "slippage_bps": 8.0, "breeder": "mutation", "immigrant_rate": 0.1, "crossover_rate": 0.35,
        "style": "etf_full", "fitness": FITNESS[fitness], "seed_file": seed_file,
        "run_id": "", "db_path": "runs/etf.sqlite", "workers": 1, "checkpoint_every": 5,
        "validate_top": 5, "verbose": True,
        "note": f"ETF grind {name}: {universe} ({', '.join(UNIVERSES[universe])}), {fitness} fitness",
    }


def main(argv) -> int:
    wave = argv[0]
    plan = [x.split(":") for x in argv[1:]]          # universe:fitness[:seed]
    out = []
    for i, item in enumerate(plan):
        universe, fitness = item[0], item[1]
        seed = int(item[2]) if len(item) > 2 else 1000 + i
        name = f"{wave}_{universe}_{fitness}_{seed}"
        path = ROOT / "configs" / "etf" / f"{name}.json"
        path.write_text(json.dumps(config(name, universe, fitness, seed), indent=1))
        out.append(str(path.relative_to(ROOT)))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
