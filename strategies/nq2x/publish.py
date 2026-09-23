"""Publish the final NQ 2x strategies: genomes, Pine, numbers, README data.

    python strategies/nq2x/publish.py SPEC.json OUT_DIR

SPEC is a JSON list, in rank order, of {"name", "slug", "family", "words",
"genome"}.  For each strategy this re-runs the gauntlet (the numbers in the
README come from here, not from a cache), adds calendar-year returns over
2010-2026 at 2x, writes the genome JSON and a Pine Script v6 strategy, and
compile-checks the Pine against TradingView's compiler.  results.json holds
everything the README is written from.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from evotrader.data import load_universe                                  # noqa: E402
from evotrader.features import build_features                             # noqa: E402
from evotrader.genome import Genome, compile_genome                       # noqa: E402
from evotrader.pine import compile_check, genome_to_pine                  # noqa: E402
from evotrader.runner import run_backtest                                 # noqa: E402
from gauntlet import COMMISSION, LEVERAGE, SLIPPAGE, Windows, passes, run_one   # noqa: E402


def by_year(genome: Genome, universe, features) -> list:
    r = run_backtest(compile_genome(genome), universe, features, starting_cash=25_000.0,
                     commission_bps=COMMISSION, slippage_bps=SLIPPAGE, record_thoughts=False,
                     leverage=LEVERAGE)
    j = r.journal
    last, order = {}, []
    for d, e in zip(j.equity_dates, j.equity):
        y = d[:4]
        if y not in last:
            order.append(y)
        last[y] = e
    rows, prev = [], j.equity[0] if j.equity else 25_000.0
    for y in order:
        trades = [t for t in j.trades if t.exit_date[:4] == y]
        rows.append({"year": y, "return": last[y] / prev - 1 if prev else 0.0, "trades": len(trades),
                     "win_rate": (sum(t.ret > 0 for t in trades) / len(trades)) if trades else 0.0})
        prev = last[y]
    return rows


def main(argv) -> int:
    spec = json.loads(Path(argv[0]).read_text())
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    w = Windows()
    full = load_universe(["NQ1!"], "2010-01-01", "2026-09-22")
    f_full = build_features(full)
    scored = []
    for item in spec:
        g = Genome.from_dict({**item["genome"], "name": item["name"], "thesis": item["words"]})
        g.risk.max_positions = 1                       # one instrument: identical behaviour
        g.risk.max_gross_exposure = 1.0
        compile_genome(g)
        res = run_one(g, w)
        res["stress"] = run_one(g, w, cost_mult=3.0)
        res["verdict"] = passes(res)
        res["by_year"] = by_year(g, full, f_full)
        scored.append((item, g, res))
    # most to least profitable over the held-out six months
    scored.sort(key=lambda x: -x[2]["held_out"]["return"])
    results = []
    for rank, (item, g, res) in enumerate(scored, 1):
        stem = f"{rank:02d}_{item['slug']}"
        body = g.to_dict()
        body.update({"rank": rank, "family": item["family"]})
        (out / f"{stem}.json").write_text(json.dumps({"genomes": [body]}, indent=1))
        pine = genome_to_pine(g, title=item["name"], source_note=(
            f"From evotrader, profitable-strategies/nq-2x/{stem}.json. NQ E-mini, long only, "
            f"twice the account in notional; bred over generations, judged on the last six months "
            f"held out (2026-03-23 to 2026-09-22)."))
        errors = compile_check(pine)
        if errors:
            raise SystemExit(f"{stem}.pine does not compile: {errors[:3]}")
        (out / f"{stem}.pine").write_text(pine)
        res.update({"rank": rank, "name": item["name"], "slug": item["slug"], "stem": stem,
                    "family": item["family"], "words": item["words"],
                    "origin": item.get("origin", ""), "genome": body})
        results.append(res)
        ho = res["held_out"]
        print(f"{rank:2d} {item['name'][:40]:40} held-out {ho['return']*100:+6.1f}% ${ho['usd_per_session']:+.0f}/session "
              f"| {'PASS' if res['verdict']['profitable'] else 'FAIL'} | pine ok")
    (out / "all.json").write_text(json.dumps({"genomes": [r["genome"] for r in results]}, indent=1))
    rep = out / "reports"
    rep.mkdir(exist_ok=True)
    (rep / "results.json").write_text(json.dumps(results, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
