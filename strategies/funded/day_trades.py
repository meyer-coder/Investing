"""The top NQ strategies as FundedNext day trades.

    python strategies/funded/day_trades.py [--top 10] [--out day_trades.json]

FundedNext Futures closes every position at 15:10 Chicago time and allows no
overnight or weekend holds, so a strategy that holds for days cannot run there
as written.  Each strategy here keeps its own entries and exits, but the
position is held only inside a session and bought back at the next session's
open for as long as the strategy would still hold it (``carry`` in
evotrader/runner.py), with a resting stop under each day's entry.  The stop
either ends the strategy's position ("ends") or only caps that day's loss and
the position is bought back at the next open ("caps").

Two sessions:

  globex  bought at the 18:00 New York Globex open, sold at the 16:00 settlement
  cash    bought at the 09:30 stock-market open, sold at the 16:00 close
          (the index fund's open, high and low applied to the future's close)

Two contracts: one MNQ, or one MES traded on the same NQ signal.  Every trade
is priced at today's contract size and replayed as fresh Legacy 25K
challenges and funded accounts (evotrader/prop.py), a new one every week.
The published multi-day version is the baseline.

Windows:  older 2010-2018 (never bred on), train 2019-01 .. 2026-03-20,
held-out 2026-03-23 .. 2026-09-22, and the last twelve months.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from evotrader.data import Bars, Universe, cash_session_bars, load_symbol, load_universe  # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.prop import MICROS, challenge_stats, funded_stats, trade_paths   # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

START, END = "2008-01-01", "2026-09-22"
WINDOWS = {"older": ("2010-01-01", "2018-12-31"), "train": ("2019-01-01", "2026-03-20"),
           "held_out": ("2026-03-23", "2026-09-22"), "last_12m": ("2025-09-22", "2026-09-22")}
DAY_STOPS = (0.0, 0.004, 0.006, 0.008, 0.010, 0.0125, 0.015, 0.02)
COMMISSION_BPS, SLIPPAGE_BPS = 0.2, 1.0          # the gauntlet's costs; the replay swaps in per-contract costs

_DATA: Dict[str, object] = {}


def _on_dates(bars: Bars, dates: List[str]) -> Bars:
    """``bars`` re-indexed onto ``dates``; a date it lacks becomes a flat bar at the last close."""
    at = {d: i for i, d in enumerate(bars.dates)}
    o, h, lo, c, v = (np.empty(len(dates)) for _ in range(5))
    last = float(bars.close[0])
    for k, d in enumerate(dates):
        i = at.get(d)
        if i is None:
            o[k] = h[k] = lo[k] = c[k] = last
            v[k] = 0.0
            continue
        o[k], h[k], lo[k], c[k], v[k] = (float(bars.open[i]), float(bars.high[i]), float(bars.low[i]),
                                         float(bars.close[i]), float(bars.volume[i]))
        last = c[k]
    return Bars(bars.symbol, list(dates), o, h, lo, c, v)


def load() -> Dict[str, object]:
    u = load_universe(["NQ1!"], START, END)
    nq = u.bars["NQ1!"]
    es = _on_dates(load_symbol("ES1!", START, END), nq.dates)
    qqq = load_symbol("QQQ", START, END)
    spy = load_symbol("SPY", START, END)
    execs = {
        ("MNQ", "globex"): nq,
        ("MNQ", "cash"): cash_session_bars(nq, qqq),
        ("MES", "globex"): Bars("NQ1!", es.dates, es.open, es.high, es.low, es.close, es.volume),
        ("MES", "cash"): Bars("NQ1!", *(lambda b: (b.dates, b.open, b.high, b.low, b.close, b.volume))(
            cash_session_bars(es, spy))),
    }
    return {"universe": u, "features": build_features(u), "execs": execs}


def _init() -> None:
    _DATA.update(load())


def daily(paths, n: int):
    """Each bar's P&L and its worst point against the prior close, from trade paths."""
    pnl = np.zeros(n)
    low = np.zeros(n)
    held = np.zeros(n, dtype=bool)
    for p in paths:
        prev = 0.0
        for b, e, w in zip(p.days, p.eod, p.worst):
            pnl[b] += e - prev
            low[b] = min(low[b], w - prev)
            held[b] = True
            prev = e
        if p.exit_bar != p.entry_bar:                      # a multi-day trade's exit, at the open
            pnl[p.exit_bar] += p.realized - prev
            low[p.exit_bar] = min(low[p.exit_bar], p.realized - prev)
    return pnl, low, held


def window_stats(paths, dates: List[str], pnl, low, held, a: str, b: str, every: int = 5,
                 rules=None, funded_rules=None) -> dict:
    idx = [i for i, d in enumerate(dates) if a <= d <= b]
    if not idx:
        return {}
    lo_i, hi_i = idx[0], idx[-1] + 1
    x = pnl[lo_i:hi_i]
    h = held[lo_i:hi_i]
    cum = np.cumsum(x)
    dd = float(np.min(cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:])) if len(cum) else 0.0
    traded = x[h]
    starts = idx[::every]
    ch = challenge_stats(paths, starts, rules) if rules else challenge_stats(paths, starts)
    fu = funded_stats(paths, starts, funded_rules) if funded_rules else funded_stats(paths, starts)
    return {
        "sessions": len(idx), "days_in_market": int(h.sum()),
        "usd_total": round(float(x.sum()), 0), "usd_per_session": round(float(x.mean()), 2),
        "win_days": round(float((traded > 0).mean()), 3) if len(traded) else 0.0,
        "worst_day": round(float(x.min()), 0), "worst_intraday": round(float(low[lo_i:hi_i].min()), 0),
        "best_day": round(float(x.max()), 0), "max_drawdown": round(dd, 0),
        "days_over_500_loss": int((x <= -500).sum()), "days_over_1000_loss": int((x <= -1000).sum()),
        "pass": round(ch.pass_rate, 3), "breach": round(ch.breach_rate, 3),
        "open": round(ch.still_open / ch.starts, 3) if ch.starts else 0.0,
        "days_to_pass": ch.median_days_to_pass,
        "funded_breach_6m": round(fu.breach_126, 3), "funded_breach_12m": round(fu.breach_252, 3),
    }


def run_job(job: dict) -> dict:
    u: Universe = _DATA["universe"]            # type: ignore[assignment]
    f = _DATA["features"]
    micro = MICROS[job["micro"]]
    exec_bars = _DATA["execs"][(job["micro"], job["session"])]   # type: ignore[index]
    g = Genome.from_dict(job["genome"])
    kw = dict(starting_cash=25_000.0, commission_bps=COMMISSION_BPS, slippage_bps=SLIPPAGE_BPS,
              record_thoughts=False, leverage=2.0, exec_bars={"NQ1!": exec_bars})
    if job["mode"] == "published":
        r = run_backtest(compile_genome(g), u, f, **kw)
    else:
        r = run_backtest(compile_genome(g), u, f, day_trade=True, carry=True,
                         day_stop=job["day_stop"], day_stop_exit=job["stop_style"] == "ends", **kw)
    price_now = float(exec_bars.close[-1])
    paths = trade_paths(r.journal.trades, exec_bars, micro=micro, contracts=1,
                        price_now=price_now, slippage_bps=SLIPPAGE_BPS)
    pnl, low, held = daily(paths, len(exec_bars))
    out = {k: job[k] for k in ("rank", "name", "mode", "session", "micro", "day_stop", "stop_style")}
    out["notional"] = round(price_now * micro.point_value, 0)
    out["day_stop_usd"] = round(job["day_stop"] * price_now * micro.point_value, 0) if job["day_stop"] else None
    out["windows"] = {w: window_stats(paths, exec_bars.dates, pnl, low, held, a, b)
                      for w, (a, b) in WINDOWS.items()}
    return out


def jobs_for(items: List[dict]) -> List[dict]:
    jobs = []
    for item in items:
        base = {"rank": item.get("rank"), "name": item["name"], "genome": item}
        for micro in ("MNQ", "MES"):
            jobs.append({**base, "mode": "published", "session": "globex", "micro": micro,
                         "day_stop": 0.0, "stop_style": ""})
            for session in ("globex", "cash"):
                for stop in DAY_STOPS:
                    # "ends": the day stop ends the strategy's position; "caps": it only
                    # caps that day, and the position is bought back at the next open
                    for style in (("ends",) if stop == 0 else ("ends", "caps")):
                        jobs.append({**base, "mode": "day", "session": session, "micro": micro,
                                     "day_stop": stop, "stop_style": style})
    return jobs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "profitable-strategies" / "nq-2x" / "all.json"))
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "profitable-strategies" / "funded" / "reports"
                                         / "day_trades.json"))
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args(argv)
    items = json.loads(Path(args.file).read_text())["genomes"]
    items = sorted(items, key=lambda g: g.get("rank", 99))[: args.top]
    jobs = jobs_for(items)
    print(f"{len(items)} strategies, {len(jobs)} runs", flush=True)
    if args.workers > 1:
        with ProcessPoolExecutor(args.workers, initializer=_init) as ex:
            rows = list(ex.map(run_job, jobs, chunksize=4))
    else:
        _init()
        rows = [run_job(j) for j in jobs]
    Path(args.out).write_text(json.dumps({"windows": WINDOWS, "day_stops": DAY_STOPS,
                                          "rows": rows}, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
