"""Command line for the harvester.

    harvest all --group all
    harvest all --top 500 --loop
    harvest archive --root NQ --timeframe 5 --since 2015
    harvest fetch --symbols NASDAQ:AAPL,AMEX:SPY --timeframes 60,1D
    harvest depth --symbol NASDAQ:AAPL
    harvest status
    harvest export --symbol CME_MINI:NQ#ARCHIVE --timeframe 5 --file nq.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
import time
from typing import Optional, Sequence

from . import sweep, tvarchive, tvcache, tvdata, universe


def _universe(args: argparse.Namespace) -> list:
    """Whichever universe the flags describe, de-duplicated and ordered."""
    picked = []
    if args.symbols:
        picked.extend(s.strip() for s in args.symbols.split(",") if s.strip())
    if args.universe:
        picked.extend(universe.read_file(args.universe))
    if args.top:
        picked.extend(universe.from_screener(args.top, sort_by=args.sort_by))
    if args.group:
        picked.extend(universe.group(
            [g for g in args.group.split(",") if g.strip()]))
    if not picked:
        picked = universe.group(["all"])
    return universe.dedupe(picked)


def cmd_all(args: argparse.Namespace) -> int:
    """Sweep a whole universe as deep as the feed goes, repeatedly if asked."""
    try:
        symbols = _universe(args)
    except tvdata.TradingViewError as exc:
        print(f"cannot build the universe: {exc}", file=sys.stderr)
        return 1
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()] \
        if args.timeframes else list(sweep.LADDER)
    if args.list:
        for s in symbols:
            print(s)
        print(f"\n{len(symbols)} symbols x {len(timeframes)} timeframes "
              f"= {len(symbols) * len(timeframes)} series", file=sys.stderr)
        return 0
    if args.save_universe:
        print(f"wrote {universe.write_file(args.save_universe, symbols)}")

    started = time.monotonic()
    passes = 0
    failures = 0
    while True:
        passes += 1
        todo = sweep.plan(symbols, timeframes, sweep.load_ledger(),
                          redo=args.redo, floor=args.floor * 3600.0)
        head = (f"pass {passes}: {len(todo.jobs)} series to pull"
                if args.loop else
                f"{len(symbols)} symbols x {len(timeframes)} timeframes "
                f"-> {len(todo.jobs)} to pull")
        if todo.fresh:
            head += f", {len(todo.fresh)} already fresh"
        print(head, flush=True)

        clock = [time.monotonic()]

        def progress(result: sweep.Result, index: int, total: int) -> None:
            elapsed = time.monotonic() - clock[0]
            eta = (elapsed / index) * (total - index) if index else 0.0
            state = (f"{result.bars:>8,} bars {result.start[:10]}..{result.end[:10]} "
                     f"{result.added:>+7,}") if result.ok else f"FAILED {result.error[:60]}"
            print(f"  [{index:>4}/{total}] {result.symbol:<20} {result.timeframe:<4} "
                  f"{state}  eta {sweep._clock(eta)}", flush=True)

        results = sweep.run(symbols, timeframes, timeout=args.timeout,
                            pause=args.pause, redo=args.redo,
                            floor=args.floor * 3600.0, progress=progress)
        summary = sweep.summarise(results)
        failures += int(summary["failed"])
        print()
        print(sweep.describe(summary), flush=True)

        if args.with_archives:
            _archives(args)

        rows = tvcache.cache_summary()
        print(f"\n  store now holds {sum(int(r['bars']) for r in rows):,} bars "
              f"across {len(rows)} series at {tvcache.CACHE_DIR}", flush=True)

        if not args.loop:
            break
        if args.passes and passes >= args.passes:
            break
        wake = datetime.now(timezone.utc) + timedelta(seconds=args.every * 3600.0)
        print(f"\nsleeping until {wake:%Y-%m-%d %H:%M} UTC "
              f"(pass {passes + 1} in {args.every}h)", flush=True)
        time.sleep(args.every * 3600.0)

    print(f"\ntotal wall clock {sweep._clock(time.monotonic() - started)}")
    return 1 if failures and not tvcache.cache_summary() else 0


def _archives(args: argparse.Namespace) -> None:
    """Deep futures history for the roots that roll on the quarterly calendar."""
    print("\nbuilding futures archives from expired contracts")
    for exchange, root in universe.FUTURES_ROOTS:
        for timeframe in [t.strip() for t in args.archive_timeframes.split(",")
                          if t.strip()]:
            try:
                report = tvarchive.build(exchange, root, timeframe,
                                         since_year=args.since, bars=args.bars,
                                         pause=args.pause)
                print("  " + tvarchive.describe(report).replace("\n", "\n  "),
                      flush=True)
            except Exception as exc:  # noqa: BLE001 - one root must not stop the rest
                print(f"  {exchange}:{root} {timeframe}: {str(exc)[:70]}",
                      file=sys.stderr, flush=True)


def cmd_archive(args: argparse.Namespace) -> int:
    def progress(symbol: str, bars: int) -> None:
        print(f"  {symbol:<24} {bars:>7,} bars")

    print(f"pulling {args.root} quarterly contracts back to {args.since} "
          f"at {args.timeframe}")
    try:
        report = tvarchive.build(args.exchange, args.root, args.timeframe,
                                 since_year=args.since, bars=args.bars,
                                 back_adjust=not args.raw_prices,
                                 pause=args.pause, progress=progress)
    except tvdata.TradingViewError as exc:
        print(f"archive failed: {exc}", file=sys.stderr)
        return 1
    print()
    print(tvarchive.describe(report))
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]
    print("  symbol           | tf   |   bars | from             | to               | added")
    failures = 0
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                before = tvcache.read_cache(symbol, timeframe)
                bars = tvcache.cached_bars(symbol, timeframe, args.bars,
                                           force=True, timeout=args.timeout)
            except Exception as exc:  # noqa: BLE001 - one symbol must not stop the run
                print(f"  {symbol:<16} | {timeframe:<4} | {str(exc)[:52]}")
                failures += 1
                continue
            added = len(bars) - (len(before) if before is not None else 0)
            print(f"  {symbol:<16} | {timeframe:<4} | {len(bars):>6,} | "
                  f"{bars.dates[0]:<16} | {bars.dates[-1]:<16} | {added:>+6,}")
    rows = tvcache.cache_summary()
    print(f"\n  store holds {sum(int(r['bars']) for r in rows):,} bars "
          f"across {len(rows)} series")
    return 1 if failures and not rows else 0


def cmd_depth(args: argparse.Namespace) -> int:
    print(f"{args.symbol} — how much history one request returns\n")
    print("  tf   |   bars | from             | to               | span")
    for timeframe in [t.strip() for t in args.timeframes.split(",") if t.strip()]:
        try:
            bars = tvdata.fetch_bars(args.symbol, timeframe, args.bars,
                                     timeout=args.timeout)
        except tvdata.TradingViewError as exc:
            print(f"  {timeframe:<4} | {str(exc)[:60]}")
            continue
        first, last = bars.dates[0], bars.dates[-1]
        days = (datetime.strptime(last[:10], "%Y-%m-%d")
                - datetime.strptime(first[:10], "%Y-%m-%d")).days
        span = (f"{days / 365.25:.1f} years" if days > 400 else
                f"{days / 30.4:.1f} months" if days > 60 else f"{days} days")
        print(f"  {timeframe:<4} | {len(bars):>6,} | {first:<16} | {last:<16} | {span}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    rows = tvcache.cache_summary()
    if not rows:
        print(f"nothing stored yet in {tvcache.CACHE_DIR}")
        return 0
    print("  series                        | tf   |    bars | from             | to")
    for row in rows:
        print(f"  {str(row['symbol'])[:29]:<29} | {str(row['timeframe']):<4} | "
              f"{int(row['bars']):>7,} | {str(row['start']):<16} | {row['end']}")
    print(f"\n  {sum(int(r['bars']) for r in rows):,} bars in {len(rows)} series "
          f"at {tvcache.CACHE_DIR}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        path = tvcache.export_csv(args.symbol, args.timeframe, args.file or "")
    except Exception as exc:  # noqa: BLE001
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    try:
        bars = tvcache.import_csv(args.file, args.symbol, args.timeframe,
                                  merge=not args.replace)
    except Exception as exc:  # noqa: BLE001
        print(f"import failed: {exc}", file=sys.stderr)
        return 1
    print(f"{args.symbol} {args.timeframe}: {len(bars):,} bars "
          f"{bars.dates[0]}..{bars.dates[-1]}")
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    from getpass import getpass

    if args.forget:
        path = args.path or tvdata.credentials_path()
        print(f"removed {path}" if tvdata.forget_credentials(path)
              else f"nothing stored at {path}")
        return 0
    print("Paste the cookies from a browser logged in to TradingView:")
    print("  DevTools -> Application -> Cookies -> https://www.tradingview.com")
    print("Input is hidden and only written to the credentials file.\n")
    sessionid = getpass("sessionid: ").strip()
    if not sessionid:
        print("nothing entered", file=sys.stderr)
        return 1
    sign = getpass("sessionid_sign (enter if you have none): ").strip()
    try:
        tvdata.resolve_auth_token(sessionid, sign=sign)
    except tvdata.TradingViewError as exc:
        print(f"\nnot saved: {exc}", file=sys.stderr)
        return 1
    print(f"\nsigned in. stored at "
          f"{tvdata.save_credentials(sessionid, sign=sign, path=args.path or '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harvest",
        description="Pull TradingView candles and keep them on disk.")
    sub = p.add_subparsers(dest="command", required=True)

    al = sub.add_parser("all", help="sweep a whole universe as deep as it goes")
    al.add_argument("--group", help="etfs,futures,fx,crypto,indices,megacaps,all")
    al.add_argument("--universe", help="file of exchange-qualified symbols")
    al.add_argument("--top", type=int, help="top N stocks from the screener")
    al.add_argument("--sort-by", default="market_cap",
                    help="screener ranking: market_cap, volume, ...")
    al.add_argument("--symbols", help="extra symbols, comma separated")
    al.add_argument("--timeframes", help=f"default {','.join(sweep.LADDER)}")
    al.add_argument("--timeout", type=float, default=300.0,
                    help="seconds per series; raise it for deeper pulls")
    al.add_argument("--pause", type=float, default=0.4)
    al.add_argument("--floor", type=float, default=1.0,
                    help="hours before a series is pulled again")
    al.add_argument("--redo", action="store_true", help="ignore the ledger")
    al.add_argument("--loop", action="store_true", help="keep sweeping forever")
    al.add_argument("--every", type=float, default=6.0, help="hours between passes")
    al.add_argument("--passes", type=int, help="stop after this many passes")
    al.add_argument("--with-archives", action="store_true",
                    help="also rebuild the futures contract archives")
    al.add_argument("--archive-timeframes", default="1D,60")
    al.add_argument("--since", type=int, default=2015)
    al.add_argument("--bars", type=int, default=20000)
    al.add_argument("--list", action="store_true", help="print the universe and stop")
    al.add_argument("--save-universe", help="write the resolved universe to a file")
    al.set_defaults(func=cmd_all)

    a = sub.add_parser("archive", help="deep futures history from expired contracts")
    a.add_argument("--exchange", default="CME_MINI")
    a.add_argument("--root", default="NQ", help="NQ, ES, RTY, YM, CL, GC, ...")
    a.add_argument("--timeframe", default="5")
    a.add_argument("--since", type=int, default=2015)
    a.add_argument("--bars", type=int, default=20000)
    a.add_argument("--raw-prices", action="store_true",
                   help="leave the roll jumps in rather than back-adjusting")
    a.add_argument("--pause", type=float, default=0.5)
    a.set_defaults(func=cmd_archive)

    f = sub.add_parser("fetch", help="pull symbols into the store, merging")
    f.add_argument("--symbols", required=True)
    f.add_argument("--timeframes", default="1D")
    f.add_argument("--bars", type=int, default=20000)
    f.add_argument("--timeout", type=float, default=40.0)
    f.set_defaults(func=cmd_fetch)

    d = sub.add_parser("depth", help="how much history one request returns")
    d.add_argument("--symbol", default="NASDAQ:AAPL")
    d.add_argument("--timeframes", default="1,5,15,60,240,1D,1W")
    d.add_argument("--bars", type=int, default=20000)
    d.add_argument("--timeout", type=float, default=40.0)
    d.set_defaults(func=cmd_depth)

    s = sub.add_parser("status", help="what the store holds")
    s.set_defaults(func=cmd_status)

    e = sub.add_parser("export", help="write a stored series out as CSV")
    e.add_argument("--symbol", required=True)
    e.add_argument("--timeframe", required=True)
    e.add_argument("--file")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import", help="load a CSV from anywhere into the store")
    i.add_argument("--file", required=True)
    i.add_argument("--symbol", required=True)
    i.add_argument("--timeframe", required=True)
    i.add_argument("--replace", action="store_true")
    i.set_defaults(func=cmd_import)

    l = sub.add_parser("login", help="store a TradingView session for deeper history")
    l.add_argument("--path")
    l.add_argument("--forget", action="store_true")
    l.set_defaults(func=cmd_login)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
