"""Command line.

    python -m confluence.cli fetch                  # 8+ years of 1-minute bars for every market
    python -m confluence.cli crosscheck             # how well each feed tracks the real contract
    python -m confluence.cli macro                  # VIX, yields, dollar, S&P, CPI, FOMC and jobs days
    python -m confluence.cli run                    # generate, backtest, log, build the explorer
    python -m confluence.cli explorer               # rebuild the explorer / CSV from the last run
    python -m confluence.cli show 22-091            # one strategy's rules and numbers

Second run — the Topstep / FundedNext futures universe:

    python -m confluence.cli futures-fetch          # 22 Dukascopy feeds with tick volume
    python -m confluence.cli futures-crosscheck     # each feed against the real future on Yahoo
    python -m confluence.cli futures-run            # ~20,000 strategies, 19 confluence categories
    python -m confluence.cli futures-accounts       # best prop account, size and risk for each
    python -m confluence.cli futures-explorer       # results/futures/explorer.html and logs
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
RUN2_DIR = os.path.join("runs", "futures")
RUN2_PKL = os.path.join(RUN2_DIR, "results.pkl.gz")
ACCOUNTS_PKL = os.path.join(RUN2_DIR, "accounts.pkl.gz")


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


# ------------------------------------------------------------------ second run: futures

def universe2(accounts=None):
    from .accounts import PLANS
    from .bars import PROP_SESSIONS
    from .components2 import CATEGORY
    from .families2 import FAMILIES2, GROUPS2
    from .futures import backtest_markets
    from .report import Universe
    plans = {p.key: {"label": p.label, "firm": p.firm, "name": p.name, "size": p.size, "price": p.price,
                     "monthly": p.monthly, "activation": p.activation, "target": p.target, "mll": p.mll,
                     "cap": p.cap, "fcaps": list(p.f_caps), "dll": p.dll, "cons": p.cons,
                     "paycap": p.pay_cap, "split": p.split} for p in PLANS}
    return Universe("run2", "Futures confluence run (Topstep / FundedNext)", list(GROUPS2), list(FAMILIES2),
                    backtest_markets(), dict(PROP_SESSIONS), os.path.join(RUN2_DIR, "trades"), accounts, plans,
                    dict(CATEGORY))


def cmd_futures_fetch(args) -> int:
    from .data import build_duka_feed
    from .futures import DUKA_SCALE, UNDERLYINGS
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today() - dt.timedelta(days=1)
    wanted = {f.strip().upper() for f in args.feeds.split(",")} if args.feeds else None
    for u in UNDERLYINGS.values():
        if wanted and u.code not in wanted and u.feed not in wanted:
            continue
        scale, inv = DUKA_SCALE[u.feed]
        m = build_duka_feed(u.feed, u.duka, scale, dt.date.fromisoformat(args.start), end, invert=inv,
                            threads=args.threads, cme_week=u.code in ("BTC", "ETH"))
        print(f"{u.code:4s} {u.feed:6s} {len(m):>10,} minutes  {m.sources}")
    return 0


def _last_day(feeds) -> dt.date:
    from .data import load_feed
    last = [dt.datetime.fromtimestamp(int(load_feed(f).t[-1]) * 60, dt.timezone.utc).date() for f in feeds]
    return min(last)


def cmd_futures_run(args) -> int:
    from .families2 import generate2
    from .runner import run_all
    u = universe2()
    feeds = sorted({m.feed for m in u.markets.values()})
    end = dt.date.fromisoformat(args.end) if args.end else _last_day(feeds)
    start = dt.date(end.year - args.years, end.month, end.day) + dt.timedelta(days=1)
    strategies = generate2(per_family=args.per_family, controls_per_cell=args.controls_per_cell)
    if args.markets:
        keep = {m.strip().upper() for m in args.markets.split(",")}
        strategies = [s for s in strategies if s.market.upper() in keep]
    if args.limit:
        strategies = strategies[:: max(1, len(strategies) // args.limit)][: args.limit]
    print(f"{len(strategies):,} strategies · test {start} .. {end} · {args.workers} workers", flush=True)
    t0 = time.time()
    results = run_all(strategies, start, end, workers=args.workers, trades_dir=u.trades_dir,
                      markets=u.markets, sessions=u.sessions, min_risk_cost=args.min_risk_cost)
    elapsed = time.time() - t0
    if args.merge and os.path.exists(RUN2_PKL):
        # add these markets to an earlier partial run (feeds that finished downloading later)
        with gzip.open(RUN2_PKL, "rb") as fh:
            old = pickle.load(fh)
        if old["meta"]["end"] != end.isoformat():
            raise SystemExit(f"--merge: earlier run ends {old['meta']['end']}, this one {end}")
        done = {s.sid for s in strategies}
        strategies = [s for s in old["strategies"] if s.sid not in done] + strategies
        results = {**{k: v for k, v in old["results"].items() if k not in done}, **results}
        elapsed += old["meta"].get("elapsed_s", 0.0)
    meta = {"start": start.isoformat(), "end": end.isoformat(), "elapsed_s": round(elapsed, 1),
            "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "workers": args.workers,
            "per_family": args.per_family, "controls_per_cell": args.controls_per_cell,
            "min_risk_cost": args.min_risk_cost}
    os.makedirs(RUN2_DIR, exist_ok=True)
    with gzip.open(RUN2_PKL, "wb") as fh:
        pickle.dump({"meta": meta, "strategies": strategies, "results": results}, fh)
    print(f"backtested {len(results):,} strategies in {elapsed / 60:.1f} min -> {RUN2_PKL}", flush=True)
    return 0


def cmd_futures_accounts(args) -> int:
    from .accounts import optimise_all
    with gzip.open(RUN2_PKL, "rb") as fh:
        blob = pickle.load(fh)
    u = universe2()
    t0 = time.time()
    acc = optimise_all(blob["strategies"], u.markets, u.trades_dir, workers=args.workers)
    with gzip.open(ACCOUNTS_PKL, "wb") as fh:
        pickle.dump(acc, fh)
    print(f"accounts for {len(acc):,} strategies in {(time.time() - t0) / 60:.1f} min -> {ACCOUNTS_PKL}", flush=True)
    return 0


def cmd_futures_crosscheck(args) -> int:
    from .data import crosscheck, load_feed
    u = universe2()
    out = {}
    for code, m in u.markets.items():
        try:
            res = crosscheck(load_feed(m.feed), m.yahoo)
        except Exception as exc:  # noqa: BLE001 - one missing feed should not stop the others
            res = {"error": str(exc)[:200]}
        res["feed"] = m.feed
        out[code] = res
        print(code, json.dumps(res), flush=True)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "data_quality.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return 0


def cmd_futures_trades(args) -> int:
    """Every trade of the given strategies as CSV (New York times, prices), for replay tools like FX Replay."""
    import csv
    from .runner import trade_list
    with gzip.open(RUN2_PKL, "rb") as fh:
        blob = pickle.load(fh)
    meta, by_id = blob["meta"], {s.sid: s for s in blob["strategies"]}
    u = universe2()
    os.makedirs(args.out, exist_ok=True)
    for sid in args.sids:
        s = by_id.get(sid)
        if s is None:
            print(f"unknown strategy {sid}", file=sys.stderr)
            return 1
        rows = trade_list(s, dt.date.fromisoformat(meta["start"]), dt.date.fromisoformat(meta["end"]), u.markets,
                          u.sessions, meta.get("min_risk_cost", 0.0), args.risk)
        path = os.path.join(args.out, f"{sid}_trades.csv")
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"{sid}: {len(rows)} trades, {sum(r['net_r'] for r in rows):+.1f}R -> {path}")
    return 0


def cmd_fxr_script(args) -> int:
    """FX Replay (FXR Script) indicator for a strategy: marks setups, simulates its trades, tallies R."""
    from .fxr import render
    with gzip.open(RUN2_PKL, "rb") as fh:
        results = pickle.load(fh)["results"]
    os.makedirs(args.out, exist_ok=True)
    for sid in args.sids:
        r = results.get(sid)
        js = render(sid, {"trades": r["trades"], "win": r["win"], "net_r": r["net_r"]} if r else None)
        path = os.path.join(args.out, f"{sid}.fxr.js")
        with open(path, "w") as fh:
            fh.write(js)
        print(f"{sid} -> {path}")
    return 0


def cmd_futures_explorer(args) -> int:
    from .report import write_all
    with gzip.open(RUN2_PKL, "rb") as fh:
        blob = pickle.load(fh)
    acc = {}
    if os.path.exists(ACCOUNTS_PKL):
        with gzip.open(ACCOUNTS_PKL, "rb") as fh:
            acc = pickle.load(fh)
    meta = dict(blob["meta"])
    write_all(blob["strategies"], blob["results"], meta, out_dir=args.out, u=universe2(acc))
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
    ff = sub.add_parser("futures-fetch", help="second run: Dukascopy 1-minute feeds for the 20 futures underlyings")
    ff.add_argument("--start", default="2018-01-01")
    ff.add_argument("--end")
    ff.add_argument("--feeds", help="only these underlyings or feeds, e.g. NQ,CL")
    ff.add_argument("--threads", type=int, default=7)
    ff.set_defaults(func=cmd_futures_fetch)
    fr = sub.add_parser("futures-run", help="second run: generate and backtest ~20,000 strategies")
    fr.add_argument("--years", type=int, default=8)
    fr.add_argument("--end")
    fr.add_argument("--per-family", type=int, default=240)
    fr.add_argument("--controls-per-cell", type=int, default=8)
    fr.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    fr.add_argument("--markets", help="comma separated underlyings, e.g. NQ,ES")
    fr.add_argument("--limit", type=int)
    fr.add_argument("--merge", action="store_true", help="add these markets to the saved run instead of replacing it")
    fr.add_argument("--min-risk-cost", type=float, default=4.0,
                    help="stops at least this many round-trip costs wide (costs <= 1/x R); 0 = only the 0.3 ATR floor")
    fr.set_defaults(func=cmd_futures_run)
    fa = sub.add_parser("futures-accounts", help="second run: best prop account / size / risk per strategy")
    fa.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
    fa.set_defaults(func=cmd_futures_accounts)
    fc = sub.add_parser("futures-crosscheck", help="second run: each feed against the real future on Yahoo")
    fc.add_argument("--out", default=os.path.join("results", "futures"))
    fc.set_defaults(func=cmd_futures_crosscheck)
    ft = sub.add_parser("futures-trades", help="second run: every trade of some strategies as CSV, for replay tools")
    ft.add_argument("sids", nargs="+")
    ft.add_argument("--risk", type=float, default=500.0, help="dollars risked per trade for the $ column")
    ft.add_argument("--out", default=os.path.join("results", "futures", "replay"))
    ft.set_defaults(func=cmd_futures_trades)
    fx = sub.add_parser("fxr-script", help="FX Replay (FXR Script) indicator for 36-221 / 21-155")
    fx.add_argument("sids", nargs="+")
    fx.add_argument("--out", default=os.path.join("results", "futures", "replay", "fxr"))
    fx.set_defaults(func=cmd_fxr_script)
    fe = sub.add_parser("futures-explorer", help="second run: explorer, CSV and logs")
    fe.add_argument("--out", default=os.path.join("results", "futures"))
    fe.set_defaults(func=cmd_futures_explorer)
    s = sub.add_parser("show", help="print one strategy")
    s.add_argument("sid")
    s.set_defaults(func=cmd_show)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
