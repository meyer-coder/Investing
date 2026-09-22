"""The bar every NQ 2x strategy has to clear, and the numbers it is judged on.

    python strategies/nq2x/gauntlet.py CANDIDATES.json [--out results.json] [--account 25000]

Each genome is run on NQ1! (ratio back-adjusted continuous E-mini) at 2x the
account in notional, 0.2 bp commission + 1 bp slippage a side, fills at the
next open, over four windows:

  train     2019-01-02 .. 2026-03-20   the only window the evolution selected on
  held-out  2026-03-23 .. 2026-09-22   the last six months, never used for selection
  older     2010-01-04 .. 2018-12-31   nine older years, also never used for selection
  stress    the train and held-out windows again at three times the costs

"Profitable" means: a positive return with a profit factor above 1 on the
held-out six months (at least 5 trades) and on the training window (at least
30 trades).  The older-history and stress results are reported as tiers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evotrader.data import date_cut, load_universe                      # noqa: E402
from evotrader.features import build_features                           # noqa: E402
from evotrader.fitness import compute_metrics                           # noqa: E402
from evotrader.genome import Genome, compile_genome                     # noqa: E402
from evotrader.runner import buy_and_hold, run_backtest                 # noqa: E402

SYMBOL = "NQ1!"
TRAIN = ("2019-01-01", "2026-03-20")
HELD_OUT_START = "2026-03-23"
END = "2026-09-22"
OLDER = ("2010-01-01", "2018-12-31")
LEVERAGE = 2.0
COMMISSION, SLIPPAGE = 0.2, 1.0


class Windows:
    """Data and features for each window, built once and shared by every genome."""

    def __init__(self) -> None:
        self.train = load_universe([SYMBOL], *TRAIN)
        self.recent = load_universe([SYMBOL], TRAIN[0], END)
        self.cut = date_cut(self.recent, HELD_OUT_START)
        self.older = load_universe([SYMBOL], *OLDER)
        self.f_train = build_features(self.train)
        self.f_recent = build_features(self.recent)
        self.f_older = build_features(self.older)


def _stats(result, universe, features, start_bar, account: float) -> Dict[str, Any]:
    j = result.journal
    bench = buy_and_hold(universe, features, starting_cash=account, start=result.start_bar)
    m = compute_metrics(j.equity, j.trades, benchmark=bench, turnover=result.turnover,
                        exposure=result.exposure)
    e = np.asarray(j.equity, dtype=float)
    r = e[1:] / e[:-1] - 1 if e.size > 2 else np.zeros(1)
    in_market = float(np.mean(np.abs(r) > 1e-12)) if r.size else 0.0
    return {
        "start": j.equity_dates[0] if j.equity_dates else "", "end": j.equity_dates[-1] if j.equity_dates else "",
        "return": m.total_return, "benchmark": m.benchmark_return, "sharpe": m.sharpe,
        "max_drawdown": m.max_drawdown, "trades": m.trades, "win_rate": m.win_rate,
        "profit_factor": m.profit_factor if np.isfinite(m.profit_factor) else 99.0,
        "avg_trade": m.avg_trade_return, "avg_hold": m.avg_bars_held, "exposure": m.exposure,
        "worst_day": m.worst_day, "best_day": float(r.max()) if r.size else 0.0,
        "mean_day": float(r.mean()) if r.size else 0.0,
        "usd_per_session": float(r.mean()) * account if r.size else 0.0,
        "usd_worst_day": float(r.min()) * account if r.size else 0.0,
        "usd_best_day": float(r.max()) * account if r.size else 0.0,
        "p10_day": float(np.percentile(r, 10)) if r.size else 0.0,
        "p90_day": float(np.percentile(r, 90)) if r.size else 0.0,
        "sessions_in_market": in_market,
        "sessions_below_2pct": float(np.mean(r < -0.02)) if r.size else 0.0,
        "sessions_below_4pct": float(np.mean(r < -0.04)) if r.size else 0.0,
        "trade_list": [{"entry": t.entry_date, "exit": t.exit_date, "ret": t.ret, "bars": t.bars_held,
                        "why_out": t.exit_reason} for t in j.trades][-40:],
    }


def run_one(genome: Genome, w: Windows, *, account: float = 25_000.0,
            cost_mult: float = 1.0) -> Dict[str, Any]:
    compiled = compile_genome(genome)
    kw = dict(starting_cash=account, commission_bps=COMMISSION * cost_mult,
              slippage_bps=SLIPPAGE * cost_mult, record_thoughts=False, leverage=LEVERAGE)
    tr = run_backtest(compiled, w.train, w.f_train, **kw)
    start = max(w.cut, w.f_recent.warmup_for(compiled.feature_names()))
    ho = run_backtest(compiled, w.recent, w.f_recent, start_bar=start, **kw)
    out = {"train": _stats(tr, w.train, w.f_train, None, account),
           "held_out": _stats(ho, w.recent, w.f_recent, start, account)}
    if cost_mult == 1.0:
        old = run_backtest(compiled, w.older, w.f_older, **kw)
        out["older"] = _stats(old, w.older, w.f_older, None, account)
        # the last twelve months: six in-sample, six held out
        yr = run_backtest(compiled, w.recent, w.f_recent,
                          start_bar=max(date_cut(w.recent, "2025-09-22"),
                                        w.f_recent.warmup_for(compiled.feature_names())), **kw)
        out["last_12m"] = _stats(yr, w.recent, w.f_recent, None, account)
    return out


def passes(res: Dict[str, Any]) -> Dict[str, bool]:
    ho, tr = res["held_out"], res["train"]
    ok = (ho["return"] > 0 and ho["profit_factor"] > 1.0 and ho["trades"] >= 5
          and tr["return"] > 0 and tr["profit_factor"] > 1.0 and tr["trades"] >= 30)
    older = res.get("older")
    stress = res.get("stress", {})
    return {
        "profitable": ok,
        "older_profitable": bool(older and older["return"] > 0 and older["profit_factor"] > 1.0),
        "survives_3x_costs": bool(stress and stress["held_out"]["return"] > 0
                                  and stress["train"]["return"] > 0),
        "hits_85_per_session": ho["usd_per_session"] >= 85.0,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--out")
    ap.add_argument("--account", type=float, default=25_000.0)
    args = ap.parse_args(argv)
    raw = json.loads(Path(args.file).read_text())
    items = raw["genomes"] if isinstance(raw, dict) else raw
    w = Windows()
    results: List[Dict[str, Any]] = []
    for item in items:
        g = Genome.from_dict(item)
        res = run_one(g, w, account=args.account)
        res["stress"] = run_one(g, w, account=args.account, cost_mult=3.0)
        res["verdict"] = passes(res)
        res["genome"] = g.to_dict()
        results.append(res)
        ho, tr, old = res["held_out"], res["train"], res["older"]
        flag = "PASS" if res["verdict"]["profitable"] else "fail"
        print(f"{flag}  {g.name[:44]:44} held-out {ho['return']*100:+6.1f}% n{ho['trades']:3d} pf {ho['profit_factor']:5.2f} "
              f"${ho['usd_per_session']:+6.0f}/session worst ${ho['usd_worst_day']:+6.0f} | train {tr['return']*100:+7.1f}% "
              f"n{tr['trades']:4d} pf {tr['profit_factor']:4.2f} mdd {tr['max_drawdown']*100:5.1f}% | older "
              f"{old['return']*100:+7.1f}% pf {old['profit_factor']:4.2f} | 3x costs "
              f"{'ok' if res['verdict']['survives_3x_costs'] else 'NO'}")
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1, default=float))
    n = sum(r["verdict"]["profitable"] for r in results)
    print(f"{n} of {len(results)} pass; "
          f"{sum(r['verdict']['hits_85_per_session'] for r in results)} average $85+ per held-out session")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
