"""Which FundedNext Legacy account, and how many micros, for the day-trade strategies?

    python strategies/funded/account_sizes.py [--out account_sizes.json]

The top ten NQ strategies reworked as day trades (Globex session, the daily
stop capping each day and the position carried on), on one to three MNQ or
MES, and the day-trade MYM island's best agent on one to four MYM, replayed
as fresh Legacy 25K, 50K and 100K challenges and funded accounts, one
started every week of each window.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from validate import WINDOWS, market                                        # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.prop import (LEGACY_25K, LEGACY_25K_FUNDED, LEGACY_50K, LEGACY_50K_FUNDED,  # noqa: E402
                            LEGACY_100K, LEGACY_100K_FUNDED, LEGACY_FEES, MICROS,
                            challenge_stats, funded_stats, trade_paths)
from evotrader.runner import run_backtest                                   # noqa: E402

ACCOUNTS = {"25K": (LEGACY_25K, LEGACY_25K_FUNDED), "50K": (LEGACY_50K, LEGACY_50K_FUNDED),
            "100K": (LEGACY_100K, LEGACY_100K_FUNDED)}
DATA_SYMBOL = {"MNQ": "NQ1!", "MES": "ES1!", "MYM": "YM1!"}


def trades_for(genome: Genome, signal: str, micro: str, day_stop: float):
    """Day trades on the Globex session: signals from ``signal``, fills on the micro's own index."""
    u, f, _ = market(signal, "globex")
    _, _, exec_bars = market(DATA_SYMBOL[micro], "globex")
    if exec_bars.dates != u.bars[signal].dates:
        from day_trades import _on_dates
        exec_bars = _on_dates(exec_bars, u.bars[signal].dates)
        exec_bars.symbol = signal
    r = run_backtest(compile_genome(genome), u, f, starting_cash=25_000.0, commission_bps=0.2,
                     slippage_bps=1.0, record_thoughts=False, leverage=2.0, day_trade=True,
                     carry=True, day_stop=day_stop, day_stop_exit=False, exec_bars={signal: exec_bars})
    return r.journal.trades, exec_bars


def odds(trades, bars, micro: str, contracts: int) -> dict:
    m = MICROS[micro]
    price_now = float(bars.close[-1])
    paths = trade_paths(trades, bars, micro=m, contracts=contracts, price_now=price_now,
                        slippage_bps=1.0)
    out = {}
    for w, (a, b) in WINDOWS.items():
        starts = [i for i, d in enumerate(bars.dates) if a <= d <= b][::5]
        out[w] = {}
        for acct, (rules, funded_rules) in ACCOUNTS.items():
            ch = challenge_stats(paths, starts, rules)
            fu = funded_stats(paths, starts, funded_rules)
            out[w][acct] = {"pass": round(ch.pass_rate, 3), "breach": round(ch.breach_rate, 3),
                            "open": round(ch.still_open / ch.starts, 3) if ch.starts else 0.0,
                            "days_to_pass": ch.median_days_to_pass,
                            "funded_breach_6m": round(fu.breach_126, 3),
                            "funded_usd_per_session": round(fu.mean_pnl_per_day_funded, 2),
                            "fee_per_pass": round(LEGACY_FEES[acct] / ch.pass_rate, 0) if ch.pass_rate else None}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "profitable-strategies" / "funded" / "reports"
                                         / "account_sizes.json"))
    ap.add_argument("--mym", default=str(ROOT / "profitable-strategies" / "funded" / "reports"
                                         / "validation.json"))
    args = ap.parse_args(argv)
    top = sorted(json.loads((ROOT / "profitable-strategies" / "nq-2x" / "all.json").read_text())["genomes"],
                 key=lambda g: g["rank"])[:10]
    jobs = []
    for g in top:
        jobs.append((g["name"], g, "NQ1!", "MNQ", 0.008, (1, 2, 3)))
        jobs.append((g["name"], g, "NQ1!", "MES", 0.010, (1, 2, 3)))
    val = json.loads(Path(args.mym).read_text())["rows"] if Path(args.mym).exists() else []
    for row in [r for r in val if r["island"].startswith("MYM")][:1]:
        jobs.append((row["genome"]["name"], row["genome"], "YM1!", "MYM", row["day_stop"], (1, 2, 3, 4)))
    rows = []
    for name, g, signal, micro, stop, sizes in jobs:
        trades, bars = trades_for(Genome.from_dict(g), signal, micro, stop)
        for c in sizes:
            rows.append({"name": name, "signal": signal, "micro": micro, "contracts": c,
                         "day_stop": stop, "day_stop_usd": round(stop * float(bars.close[-1])
                                                                 * MICROS[micro].point_value * c, 0),
                         "windows": odds(trades, bars, micro, c)})
            t = rows[-1]["windows"]
            print(f"{name[:32]:32} {c} {micro} | " + " | ".join(
                f"{a} tr {t['train'][a]['pass']:.2f}/{t['train'][a]['breach']:.2f} old {t['older'][a]['pass']:.2f}/{t['older'][a]['breach']:.2f}"
                for a in ACCOUNTS), flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"windows": WINDOWS, "fees": LEGACY_FEES, "rows": rows}, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
