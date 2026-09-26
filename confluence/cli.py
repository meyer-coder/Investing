"""Command line.

    python -m confluence.cli fetch                  # 8+ years of 1-minute bars for every market
    python -m confluence.cli crosscheck             # how well each feed tracks the real contract
    python -m confluence.cli macro                  # VIX, yields, dollar, S&P, CPI, FOMC and jobs days
    python -m confluence.cli run                    # generate, backtest, log, build the explorer
    python -m confluence.cli explorer               # rebuild the explorer / CSV from the last run
    python -m confluence.cli show 22-091            # one strategy's rules and numbers
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import pickle
import sys
import time
from typing import Optional, Sequence

RESULTS_PKL = os.path.join("runs", "results.pkl.gz")


def _dates(args) -> tuple:
    end = dt.date.fromisoformat(args.end) if args.end else _last_data_day()
    start = dt.date(end.year - args.years, end.month, end.day) + dt.timedelta(days=1)
    return start, end


def _last_data_day() -> dt.date:
    from .data import load_feed
    from .markets import FEEDS
    last = []
    for feed in FEEDS:
        try:
            m = load_feed(feed)
        except Exception:  # noqa: BLE001
            continue
        last.append(dt.datetime.fromtimestamp(int(m.t[-1]) * 60, dt.timezone.utc).date())
    return min(last) if last else dt.date.today() - dt.timedelta(days=1)


def cmd_fetch(args) -> int:
    from .data import build_feed
    from .markets import MARKETS
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today() - dt.timedelta(days=1)
    start = dt.date.fromisoformat(args.start)
    patch_from = dt.date.fromisoformat(args.patch_from) if args.patch_from else None
    wanted = {f.strip().upper() for f in args.feeds.split(",")} if args.feeds else None
    done = set()
    for m in MARKETS.values():
        if m.feed in done or (wanted and m.feed not in wanted and m.code not in wanted):
            continue
        done.add(m.feed)
        mins = build_feed(m.feed, m.duka, m.duka_scale, start, end, refresh=args.refresh,
                          duka_threads=args.duka_threads, patch_from=patch_from)
        a, b = mins.span()
        print(f"{m.feed:8s} {len(mins):>10,} bars  {a} .. {b} UTC  {mins.sources}")
    return 0


def cmd_crosscheck(args) -> int:
    from .data import crosscheck, load_feed
    from .markets import MARKETS
    out = {}
    for code, m in MARKETS.items():
        res = crosscheck(load_feed(m.feed), m.yahoo)
        res["feed"] = m.feed
        out[code] = res
        print(code, json.dumps(res))
    os.makedirs("results", exist_ok=True)
    path = os.path.join("results", "data_quality.json")
    if os.path.exists(path):            # keep checks made elsewhere (e.g. the TradingView spot check)
        with open(path) as fh:
            old = json.load(fh)
        out.update({k: v for k, v in old.items() if k.startswith("_")})
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    return 0


def cmd_macro(args) -> int:
    from .macro import DIMENSIONS, fetch_all
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today()
    m = fetch_all(dt.date.fromisoformat(args.start), end, refresh=args.refresh)
    for k, v in m["series"].items():
        ks = sorted(v)
        print(f"{k:6s} {len(v):>5} days  {ks[0]} .. {ks[-1]}")
    print(f"FOMC statement days: {len(m['fomc'])} · jobs-report days: {len(m['nfp'])} · "
          f"CPI months: {len(m['cpi'])} (last {max(m['cpi'])})")
    print("regimes: " + ", ".join(d.title for d in DIMENSIONS))
    return 0


def cmd_run(args) -> int:
    from .families import generate
    from .runner import run_all
    from .report import write_all
    start, end = _dates(args)
    strategies = generate(per_family=args.per_family, controls_per_cell=args.controls_per_cell)
    if args.markets:
        keep = {m.strip().upper() for m in args.markets.split(",")}
        strategies = [s for s in strategies if s.market.upper() in keep]
    if args.limit:
        strategies = strategies[:: max(1, len(strategies) // args.limit)][: args.limit]
    print(f"{len(strategies):,} strategies · test {start} .. {end} · {args.workers} workers", flush=True)
    t0 = time.time()
    results = run_all(strategies, start, end, workers=args.workers,
                      trades_dir=None if args.no_trades else os.path.join("runs", "trades"))
    elapsed = time.time() - t0
    meta = {"start": start.isoformat(), "end": end.isoformat(), "elapsed_s": round(elapsed, 1),
            "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "workers": args.workers,
            "per_family": args.per_family, "controls_per_cell": args.controls_per_cell}
    os.makedirs("runs", exist_ok=True)
    with gzip.open(RESULTS_PKL, "wb") as fh:
        pickle.dump({"meta": meta, "strategies": strategies, "results": results}, fh)
    print(f"backtested {len(results):,} strategies in {elapsed / 60:.1f} min -> {RESULTS_PKL}", flush=True)
    write_all(strategies, results, meta, out_dir=args.out)
    return 0


def cmd_explorer(args) -> int:
    from .report import write_all
    with gzip.open(RESULTS_PKL, "rb") as fh:
        blob = pickle.load(fh)
    write_all(blob["strategies"], blob["results"], blob["meta"], out_dir=args.out)
    return 0


def cmd_show(args) -> int:
    with gzip.open(RESULTS_PKL, "rb") as fh:
        blob = pickle.load(fh)
    s = next((x for x in blob["strategies"] if x.sid == args.sid), None)
    if s is None:
        print(f"unknown strategy {args.sid}", file=sys.stderr)
        return 1
    r = blob["results"][s.sid]
    print(f"{s.sid}  {s.name}\n  family: {s.fam.name} ({s.group})\n  thesis: {s.fam.thesis}")
    for rule in s.rules():
        print(f"  - {rule}")
    keys = ["trades", "per_week", "win", "avg_rr", "net_r", "gross_r", "total_r", "usd", "max_dd",
            "cost_r", "r12", "n12", "e3y", "n3y", "e6", "n6", "score", "t", "usd_day", "d_p10", "d_p90",
            "p_pass", "p_payout"]
    for k in keys:
        v = r.get(k)
        print(f"  {k:10s} {v:.4f}" if isinstance(v, float) else f"  {k:10s} {v}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="confluence", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download and splice 1-minute history")
    f.add_argument("--start", default="2018-01-01")
    f.add_argument("--end")
    f.add_argument("--refresh", action="store_true")
    f.add_argument("--feeds", help="only these feeds or markets, e.g. WTIUSD or USOIL,MNQ")
    f.add_argument("--patch-from", default="",
                   help="fill thin histdata days from Dukascopy only from this date on (default: all history)")
    f.add_argument("--duka-threads", type=int, default=6)
    f.set_defaults(func=cmd_fetch)
    c = sub.add_parser("crosscheck", help="compare each feed with the real contract on Yahoo")
    c.set_defaults(func=cmd_crosscheck)
    mc = sub.add_parser("macro", help="download macro data (VIX, yields, dollar, S&P, CPI, FOMC and jobs days)")
    mc.add_argument("--start", default="2017-01-01")
    mc.add_argument("--end")
    mc.add_argument("--refresh", action="store_true")
    mc.set_defaults(func=cmd_macro)
    r = sub.add_parser("run", help="generate every strategy, backtest, log, build the explorer")
    r.add_argument("--years", type=int, default=8)
    r.add_argument("--end", help="last day of the test (default: last day with data)")
    r.add_argument("--per-family", type=int, default=210)
    r.add_argument("--controls-per-cell", type=int, default=20)
    r.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    r.add_argument("--markets", help="comma separated subset, e.g. MNQ,MES")
    r.add_argument("--limit", type=int, help="run only N strategies (smoke test)")
    r.add_argument("--no-trades", action="store_true", help="do not save the per-trade logs")
    r.add_argument("--out", default="results")
    r.set_defaults(func=cmd_run)
    e = sub.add_parser("explorer", help="rebuild the explorer from the last run")
    e.add_argument("--out", default="results")
    e.set_defaults(func=cmd_explorer)
    s = sub.add_parser("show", help="print one strategy")
    s.add_argument("sid")
    s.set_defaults(func=cmd_show)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
