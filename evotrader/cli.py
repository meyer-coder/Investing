"""Command line interface.

    evotrader run --population 100 --generations 1000
    evotrader resume run-20260101-120000-ab12
    evotrader report --html reports/run.html
    evotrader inspect <genome-id>
    evotrader screen --preset liquid-large-cap --save
    evotrader simulate --strategy rsi_pullback --symbols SPY,QQQ
    evotrader compare --symbols SPY,QQQ,IWM --family trend
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from typing import List, Optional, Sequence

from .config import DEFAULT_SYMBOLS, EvolutionConfig
from .data import load_universe
from .evolution import Evolution, score_genome
from .features import build_features
from .fitness import FitnessConfig
from .llm import PRICING, Claude
from .report import html_report, lineage, markdown_report, print_report
from .screener import (UNIVERSE_DIR, Filter, PRESETS, Screen, ScreenerError,
                       preset, run_screen, yahoo_symbols)
from . import strategies as strategy_lib
from .backtest_api import (Costs, DataSpec, compare as compare_strategies,
                           load_dataset, make_genome, optimize,
                           run as run_backtest_api, walk_forward)
from .data import DataError, INTERVALS
from .store import Store


def _add_run_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="JSON config file; flags below override it")
    p.add_argument("--symbols", help="comma separated tickers "
                                     f"(default: {','.join(DEFAULT_SYMBOLS)})")
    p.add_argument("--start", help="first date, YYYY-MM-DD")
    p.add_argument("--end", help="last date, YYYY-MM-DD")
    p.add_argument("--population", type=int, help="agents per generation")
    p.add_argument("--generations", type=int, help="number of generations to run")
    p.add_argument("--elites", type=int, help="survivors carried over and bred from")
    p.add_argument("--survivor-reports", type=int,
                   help="how many top agents Claude reads in detail")
    p.add_argument("--breeder", choices=["hybrid", "llm", "mutation"],
                   help="who writes the offspring")
    p.add_argument("--llm-share", type=float,
                   help="fraction of each generation written by Claude (hybrid)")
    p.add_argument("--llm-every", type=int, help="call Claude every N generations")
    p.add_argument("--model", help="Claude model id for breeding")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--budget", type=float, dest="budget_usd",
                   help="stop calling Claude after this many USD")
    p.add_argument("--seed", type=int, help="RNG seed (0 = nondeterministic)")
    p.add_argument("--workers", type=int, help="backtest processes (0 = auto)")
    p.add_argument("--offline", action="store_true",
                   help="use synthetic data instead of fetching prices")
    p.add_argument("--refresh-data", action="store_true", help="re-download price data")
    p.add_argument("--db", dest="db_path", help="SQLite path (default runs/evotrader.sqlite)")
    p.add_argument("--test-frac", type=float, help="held-out tail fraction")
    p.add_argument("--note", help="free text stored with the run")
    p.add_argument("--quiet", action="store_true")


def _config_from_args(args: argparse.Namespace) -> EvolutionConfig:
    cfg = EvolutionConfig.load(args.config) if getattr(args, "config", None) else EvolutionConfig()
    for name in ("start", "end", "population", "generations", "elites", "breeder",
                 "llm_share", "llm_every", "model", "effort", "budget_usd", "seed",
                 "workers", "db_path", "test_frac", "note", "survivor_reports"):
        value = getattr(args, name, None)
        if value is not None:
            setattr(cfg, name, value)
    if getattr(args, "symbols", None):
        cfg.symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if getattr(args, "offline", False):
        cfg.offline = True
    if getattr(args, "refresh_data", False):
        cfg.refresh_data = True
    if getattr(args, "quiet", False):
        cfg.verbose = False
    return cfg


def _estimate(cfg: EvolutionConfig) -> str:
    """A blunt up-front estimate, because 1000 generations is not free."""
    calls = cfg.generations // max(cfg.llm_every, 1) if cfg.breeder != "mutation" else 0
    price_in, price_out = PRICING.get(cfg.model, (5.0, 25.0))
    # Measured shape of one breeding call: a long briefing in, a batch of
    # genomes out.  Roughly 12k input tokens and 6k output tokens.
    per_call = (12_000 * price_in + 6_000 * price_out) / 1_000_000
    backtests = cfg.population * cfg.generations
    return (f"plan: {backtests:,} backtests, {calls:,} breeding calls "
            f"(~${calls * per_call:,.2f} at {cfg.model} list prices"
            f"{f', capped at ${cfg.budget_usd:.2f}' if cfg.budget_usd else ''})")


def cmd_run(args: argparse.Namespace) -> int:
    cfg = _config_from_args(args)
    cfg.validate()
    print(_estimate(cfg))
    if args.dry_run:
        print(json.dumps(cfg.to_dict(), indent=2))
        return 0
    evolution = Evolution(cfg)
    evolution.run()
    print_report(evolution.store, evolution.run_id, limit=10)
    print(f"resume with: evotrader resume {evolution.run_id} --db {cfg.db_path}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    store = Store(args.db_path or EvolutionConfig().db_path)
    stored = store.run_config(args.run_id)
    if stored is None:
        print(f"unknown run {args.run_id!r}", file=sys.stderr)
        return 1
    cfg = EvolutionConfig.from_dict(stored)
    for name in ("generations", "breeder", "llm_share", "llm_every", "model",
                 "budget_usd", "workers"):
        value = getattr(args, name, None)
        if value is not None:
            setattr(cfg, name, value)
    if getattr(args, "quiet", False):
        cfg.verbose = False
    evolution = Evolution(cfg, store=store)
    evolution.resume(args.run_id)
    evolution.run(args.generations)
    print_report(store, args.run_id, limit=10)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    store = Store(args.db_path or EvolutionConfig().db_path)
    run_id = args.run_id or (store.list_runs(1)[0]["id"] if store.list_runs(1) else None)
    if not run_id:
        print("no runs found", file=sys.stderr)
        return 1
    print_report(store, run_id, limit=args.limit)
    if args.html:
        os.makedirs(os.path.dirname(os.path.abspath(args.html)), exist_ok=True)
        with open(args.html, "w") as fh:
            fh.write(html_report(store, run_id, limit=args.limit))
        print(f"wrote {args.html}")
    if args.markdown:
        os.makedirs(os.path.dirname(os.path.abspath(args.markdown)), exist_ok=True)
        with open(args.markdown, "w") as fh:
            fh.write(markdown_report(store, run_id, limit=args.limit))
        print(f"wrote {args.markdown}")
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    store = Store(args.db_path or EvolutionConfig().db_path)
    rows = store.list_runs(args.limit)
    if not rows:
        print("no runs yet")
        return 0
    for row in rows:
        cfg = json.loads(row["config"])
        print(f"{row['id']}  {row['status']:<11} gens={row['generations'] or 0:<5} "
              f"pop={cfg['population']:<4} breeder={cfg['breeder']:<8} {row['note'][:40]}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    store = Store(args.db_path or EvolutionConfig().db_path)
    genome = store.get_genome(args.genome_id)
    if genome is None:
        print(f"unknown genome {args.genome_id!r}", file=sys.stderr)
        return 1
    print(genome.describe())
    if genome.rationale:
        print(f"\nrationale: {genome.rationale}")
    rows = store.conn.execute(
        "SELECT * FROM evaluations WHERE genome_id=?", (args.genome_id,)).fetchall()
    for row in rows:
        print(f"\ngeneration {row['generation']}: score {row['score']:+.3f}")
        print("  " + json.dumps(json.loads(row["metrics"]), indent=2).replace("\n", "\n  "))
    trades = store.conn.execute(
        "SELECT * FROM trades WHERE genome_id=? ORDER BY seq LIMIT ?",
        (args.genome_id, args.trades)).fetchall()
    if trades:
        print(f"\nfirst {len(trades)} trades")
        for t in trades:
            print(f"  {t['symbol']:<5} {t['entry_date']} -> {t['exit_date']} "
                  f"({t['bars_held']:>3}b) {t['ret'] * 100:+6.1f}%  in: {t['entry_reason']}"
                  f"  out: {t['exit_reason']}")
    chain = lineage(store, args.genome_id)
    if len(chain) > 1:
        print("\nancestry (newest first)")
        for g in chain:
            print(f"  gen {g.generation:>4} {g.origin:<9} {g.name[:40]:<40} {g.id}")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    """Re-run one stored genome over an arbitrary window."""
    store = Store(args.db_path or EvolutionConfig().db_path)
    genome = store.get_genome(args.genome_id)
    if genome is None:
        print(f"unknown genome {args.genome_id!r}", file=sys.stderr)
        return 1
    stored = store.run_config(
        store.conn.execute("SELECT run_id FROM genomes WHERE id=?",
                           (args.genome_id,)).fetchone()["run_id"]) or {}
    cfg = EvolutionConfig.from_dict(stored)
    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else cfg.symbols
    universe = load_universe(symbols, args.start or cfg.start, args.end or cfg.end,
                             offline=cfg.offline)
    features = build_features(universe)
    from .evolution import Context
    from .runner import buy_and_hold
    ctx = Context(train=universe, train_features=features,
                  train_benchmark=buy_and_hold(universe, features,
                                               starting_cash=cfg.starting_cash),
                  test=None, test_features=None, test_benchmark=None,
                  starting_cash=cfg.starting_cash, commission_bps=cfg.commission_bps,
                  slippage_bps=cfg.slippage_bps, fitness=cfg.fitness)
    outcome = score_genome(genome, ctx)
    if outcome.error:
        print(f"error: {outcome.error}", file=sys.stderr)
        return 1
    print(genome.describe())
    print(f"\nscore {outcome.score:+.3f} | {outcome.metrics.summary()}")
    print(json.dumps(outcome.metrics.to_dict(), indent=2))
    if outcome.journal and args.trades:
        print(f"\nfirst {args.trades} trades")
        for t in outcome.journal.trades[:args.trades]:
            print("  " + t.summary())
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    symbols = [s.strip().upper() for s in (args.symbols or ",".join(DEFAULT_SYMBOLS)).split(",")]
    universe = load_universe(symbols, args.start, args.end, refresh=True)
    a, b = universe.date_range()
    print(f"cached {len(universe.symbols)} symbols, {len(universe)} shared bars, {a}..{b}")
    return 0



def cmd_screen(args: argparse.Namespace) -> int:
    """Pick a symbol universe with a TradingView screen."""
    try:
        if args.preset:
            screen = preset(args.preset)
        else:
            screen = Screen(name=args.name, market=args.market)
        if args.filter:
            screen = replace(screen, name=args.name if not args.preset else screen.name,
                             filters=list(screen.filters) +
                                     [Filter.parse(f) for f in args.filter])
        if args.limit:
            screen = replace(screen, limit=args.limit)
        if args.sort:
            screen = replace(screen, sort_by=args.sort)
        snapshot = run_screen(screen, refresh=args.refresh)
    except ScreenerError as exc:
        print(f"screen failed: {exc}", file=sys.stderr)
        return 1

    symbols = yahoo_symbols(snapshot)
    if not symbols:
        print("no symbols matched — loosen the filters")
        return 1

    display = [c for c in snapshot.columns if c not in ("name", "description")][:5]
    print(f"{snapshot.screen}  ({snapshot.market}, {snapshot.total_matches} matches, "
          f"showing {len(symbols)}, captured {snapshot.captured_at[:10]})\n")
    header = f"{'symbol':<12}" + "".join(f"{c:>14}" for c in display)
    print(header)
    print("-" * len(header))
    for symbol, row in zip(symbols, snapshot.rows):
        cells = "".join(f"{_cell(row.get(c)):>14}" for c in display)
        print(f"{symbol:<12}{cells}")

    print(f"\nsymbols: {','.join(symbols)}")
    if args.save:
        path = snapshot.save()
        print(f"saved:   {path}")
    if args.config:
        _write_universe_config(args.config, symbols, snapshot)
        print(f"config:  {args.config}")
    return 0


def _cell(value) -> str:
    """Render one screener value narrow enough for a terminal column."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        for scale, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
            if abs(value) >= scale:
                return f"{value / scale:.1f}{suffix}"
        return f"{value:,.2f}"
    return str(value)[:13]


def _write_universe_config(path: str, symbols: List[str], snapshot) -> None:
    """Write a run config using the screened symbols, keeping other settings."""
    config = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    config["symbols"] = symbols
    config["note"] = (f"universe from TradingView screen '{snapshot.screen}' "
                      f"captured {snapshot.captured_at[:10]}")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)



def _parse_params(items: Optional[Sequence[str]]) -> dict:
    """Turn ``--param oversold=25`` flags into a parameter mapping."""
    out = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"expected key=value, got {item!r}")
        key, _, raw = item.partition("=")
        try:
            out[key.strip()] = float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)
        except ValueError:
            out[key.strip()] = raw.strip()
    return out


def _parse_grid(items: Optional[Sequence[str]]) -> dict:
    """Turn ``--grid oversold=25,30,35`` flags into a search grid."""
    grid = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"expected key=v1,v2,..., got {item!r}")
        key, _, raw = item.partition("=")
        values = []
        for piece in raw.split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                values.append(float(piece) if ("." in piece or "e" in piece.lower())
                              else int(piece))
            except ValueError:
                values.append(piece)
        if not values:
            raise ValueError(f"no values given for {key!r}")
        grid[key.strip()] = values
    return grid


def _sim_spec(args: argparse.Namespace) -> DataSpec:
    symbols = [s.strip().upper() for s in
               (args.symbols or ",".join(DEFAULT_SYMBOLS)).split(",") if s.strip()]
    return DataSpec.of(symbols, args.start, args.end, interval=args.interval,
                       offline=args.offline)


def _sim_costs(args: argparse.Namespace) -> Costs:
    return Costs(starting_cash=args.cash, commission_bps=args.commission,
                 slippage_bps=args.slippage)


def cmd_strategies(args: argparse.Namespace) -> int:
    """List the strategy library."""
    names = strategy_lib.names(args.family)
    if not names:
        print(f"no strategies in family {args.family!r}; "
              f"try {', '.join(strategy_lib.families())}", file=sys.stderr)
        return 1
    width = max(len(n) for n in names)
    family = None
    for name in sorted(names, key=lambda n: (strategy_lib.SPECS[n].family, n)):
        spec = strategy_lib.SPECS[name]
        if spec.family != family:
            family = spec.family
            print(f"\n{family}")
        params = ", ".join(f"{k}={v}" for k, v in sorted(spec.params.items()))
        print(f"  {name:<{width}}  {spec.thesis}")
        if params:
            print(f"  {'':<{width}}  params: {params}")
    print(f"\n{len(names)} strategies. Backtest one with: "
          f"evotrader simulate --strategy <name>")
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Backtest a library strategy, or rules given on the command line."""
    if args.grid and not args.strategy:
        print("--grid needs --strategy", file=sys.stderr)
        return 1
    try:
        grid = _parse_grid(args.grid)
        genome = make_genome(args.strategy, params=_parse_params(args.param),
                             entries=args.entry, exits=args.exit)
        dataset = load_dataset(_sim_spec(args))
        costs = _sim_costs(args)
        report = (optimize(args.strategy, grid, dataset.spec, costs,
                           workers=args.workers, top=args.top) if grid else None)
    except (ValueError, DataError, strategy_lib.StrategyError) as exc:
        print(f"simulate failed: {exc}", file=sys.stderr)
        return 1

    if report is not None:
        print(f"{args.strategy}: {report['combinations_tested']} combinations, "
              f"chosen on {report['train_window'][0]}..{report['train_window'][1]}, "
              f"scored on {report['test_window'][0]}..{report['test_window'][1]}\n")
        header = f"{'parameters':<38}{'train':>10}{'held out':>10}{'vs b&h':>10}"
        print(header)
        print("-" * len(header))
        for entry in report["results"]:
            params = ", ".join(f"{k}={v}" for k, v in sorted(entry["params"].items()))
            train, test = entry["train"], entry.get("test", {})
            print(f"{params:<38}{_pct(train['total_return']):>10}"
                  f"{_pct(test.get('total_return')):>10}"
                  f"{_pct(test.get('benchmark_return')):>10}")
        d = report["degradation"]
        print(f"\n  retained {_num(d.get('return_retained'))} of the in-sample "
              f"return out of sample — {d['verdict']}")
        print(f"  {report['note']}")
        return 0

    if args.walk_forward:
        report = walk_forward(genome, dataset.spec, costs, folds=args.folds)
        print(f"{genome.name}  walk-forward over {len(report['folds'])} anchored folds")
        for fold in report["folds"]:
            if "skipped" in fold:
                print(f"  {fold['fold']:<7} skipped ({fold['skipped']})")
                continue
            train, test = fold["train"], fold["test"]
            print(f"  {fold['fold']:<7} train {_pct(train['total_return'])} "
                  f"(bh {_pct(train['benchmark_return'])})   "
                  f"test {_pct(test['total_return'])} "
                  f"(bh {_pct(test['benchmark_return'])})  {test['trades']} trades")
        print(f"\n  {report['consistency']['verdict']}")
        print(f"  {report['note']}")
        return 0

    row = run_backtest_api(genome, dataset, costs, include_trades=args.trades > 0,
                           max_trades=args.trades)
    if "error" in row:
        print(f"simulate failed: {row['error']}", file=sys.stderr)
        return 1
    _print_result(row)
    for trade in row.get("trades", []):
        print("  " + ", ".join(f"{k}={v}" for k, v in list(trade.items())[:6]))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Rank the strategy library over one universe."""
    try:
        names = ([n.strip() for n in args.names.split(",")] if args.names
                 else strategy_lib.names(args.family))
        if not args.names and not args.family:
            names = [n for n in names if not n.startswith("archetype:")]
        genomes = [strategy_lib.build(n) for n in names]
        dataset = load_dataset(_sim_spec(args))
    except (ValueError, DataError, strategy_lib.StrategyError) as exc:
        print(f"compare failed: {exc}", file=sys.stderr)
        return 1

    rows = compare_strategies(genomes, dataset, _sim_costs(args),
                              rank_by=args.rank_by, workers=args.workers)
    start, end = dataset.dates
    print(f"{len(rows)} strategies over {', '.join(dataset.spec.symbols)}  "
          f"{start}..{end} ({dataset.bars} {dataset.spec.interval} bars), "
          f"ranked by {args.rank_by}\n")
    header = f"{'strategy':<22}{'fitness':>9}{'return':>9}{'vs b&h':>9}{'sharpe':>8}{'maxdd':>8}{'trades':>8}"
    print(header)
    print("-" * len(header))
    for row in rows[:args.limit]:
        if "error" in row:
            print(f"{row['strategy']:<22}  {row['error'][:50]}")
            continue
        m = row["metrics"]
        print(f"{row['strategy']:<22}{_num(row['fitness']):>9}"
              f"{_pct(m['total_return']):>9}{_pct(m['excess_return']):>9}"
              f"{_num(m['sharpe']):>8}{_pct(m['max_drawdown']):>8}{m['trades']:>8}")
    benchmark = (rows[0].get("metrics") or {}).get("benchmark_return") if rows else None
    if benchmark is not None:
        print(f"\nbuy-and-hold over the same window: {_pct(benchmark)}")
    return 0


def _pct(value: Optional[float]) -> str:
    return "-" if value is None else f"{value * 100:+.1f}%"


def _num(value: Optional[float], places: int = 2) -> str:
    """Metrics are None when they are not finite — an unbeaten strategy has an
    infinite profit factor, and that must not crash the report."""
    return "n/a" if value is None else f"{value:.{places}f}"


def _print_result(row: dict) -> None:
    m = row["metrics"]
    period = row["period"]
    print(f"{row['strategy']}  {', '.join(row['symbols'])}  "
          f"{period['start']}..{period['end']}  "
          f"({period['bars']} {row['interval']} bars, {period['years']}y)\n")
    print(f"  return          {_pct(m['total_return'])}   "
          f"(buy-and-hold {_pct(m['benchmark_return'])}, "
          f"excess {_pct(m['excess_return'])})")
    print(f"  cagr            {_pct(m['cagr'])}")
    print(f"  sharpe          {_num(m['sharpe'])}   sortino {_num(m['sortino'])}")
    print(f"  max drawdown    {_pct(m['max_drawdown'])}   calmar {_num(m['calmar'])}")
    print(f"  trades          {m['trades']}   win {_pct(m['win_rate'])[1:]}   "
          f"profit factor {_num(m['profit_factor'])}")
    print(f"  turnover        {_num(m['turnover'], 1)}x/yr   exposure "
          f"{_pct(m['exposure'])[1:]}")
    print(f"  costs paid      {row['costs_paid']:,.0f}   "
          f"final equity {row['final_equity']:,.0f}")
    print(f"  fitness         {_num(row['fitness'], 3)}")


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check the environment: data access, credentials, dependencies."""
    print(f"python            {sys.version.split()[0]}")
    try:
        import numpy
        print(f"numpy             {numpy.__version__}")
    except ImportError:
        print("numpy             MISSING (pip install numpy)")
    try:
        import anthropic
        print(f"anthropic sdk     {anthropic.__version__}")
    except ImportError:
        print("anthropic sdk     not installed — breeding falls back to mutation only")
    claude = Claude()
    print(f"claude            {'ready (' + claude.model + ')' if claude.available else claude.unavailable_reason}")
    try:
        universe = load_universe(["SPY"], "2024-01-01", "2024-12-31")
        print(f"market data       ok ({len(universe)} SPY bars in 2024)")
    except Exception as exc:  # noqa: BLE001 - this is the diagnostic
        print(f"market data       unavailable: {exc}\n"
              f"                  use --offline to run on synthetic prices")
    try:
        snapshot = run_screen(preset("liquid-large-cap"))
        print(f"tradingview       ok ({snapshot.total_matches} large caps match)")
    except Exception as exc:  # noqa: BLE001 - this is the diagnostic
        print(f"tradingview       unavailable: {exc}\n"
              f"                  screening is optional; runs use --symbols instead")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evotrader",
        description="Evolve paper-trading agents; Claude breeds each generation "
                    "from the last one's winners.")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="start a new evolution run")
    _add_run_flags(run)
    run.add_argument("--dry-run", action="store_true",
                     help="print the resolved config and cost estimate, then stop")
    run.set_defaults(func=cmd_run)

    res = sub.add_parser("resume", help="continue a run from its last checkpoint")
    res.add_argument("run_id")
    res.add_argument("--generations", type=int, help="how many more generations")
    res.add_argument("--breeder", choices=["hybrid", "llm", "mutation"])
    res.add_argument("--llm-share", type=float)
    res.add_argument("--llm-every", type=int)
    res.add_argument("--model")
    res.add_argument("--budget", type=float, dest="budget_usd")
    res.add_argument("--workers", type=int)
    res.add_argument("--db", dest="db_path")
    res.add_argument("--quiet", action="store_true")
    res.set_defaults(func=cmd_resume)

    rep = sub.add_parser("report", help="summarise a run")
    rep.add_argument("run_id", nargs="?", help="defaults to the most recent run")
    rep.add_argument("--db", dest="db_path")
    rep.add_argument("--limit", type=int, default=10)
    rep.add_argument("--html", help="also write a standalone HTML report here")
    rep.add_argument("--markdown", help="also write a Markdown report here")
    rep.set_defaults(func=cmd_report)

    runs = sub.add_parser("runs", help="list runs in the database")
    runs.add_argument("--db", dest="db_path")
    runs.add_argument("--limit", type=int, default=20)
    runs.set_defaults(func=cmd_runs)

    ins = sub.add_parser("inspect", help="show one genome, its results and ancestry")
    ins.add_argument("genome_id")
    ins.add_argument("--db", dest="db_path")
    ins.add_argument("--trades", type=int, default=20)
    ins.set_defaults(func=cmd_inspect)

    bt = sub.add_parser("backtest", help="re-run a stored genome over any window")
    bt.add_argument("genome_id")
    bt.add_argument("--db", dest="db_path")
    bt.add_argument("--symbols")
    bt.add_argument("--start")
    bt.add_argument("--end")
    bt.add_argument("--trades", type=int, default=10)
    bt.set_defaults(func=cmd_backtest)

    fetch = sub.add_parser("fetch", help="download and cache price data")
    fetch.add_argument("--symbols")
    fetch.add_argument("--start", default="2005-01-01")
    fetch.add_argument("--end", default="2030-01-01")
    fetch.set_defaults(func=cmd_fetch)

    scr = sub.add_parser("screen", help="choose a symbol universe from a TradingView screen")
    scr.add_argument("--preset", choices=sorted(PRESETS),
                     help="start from a named screen")
    scr.add_argument("--filter", action="append", metavar="EXPR",
                     help="add a predicate, e.g. 'mcap > 10e9' (repeatable)")
    scr.add_argument("--market", default="america")
    scr.add_argument("--name", default="custom", help="name for the saved snapshot")
    scr.add_argument("--sort", help="column to rank by")
    scr.add_argument("--limit", type=int, help="how many symbols to keep")
    scr.add_argument("--refresh", action="store_true", help="ignore the cache")
    scr.add_argument("--save", action="store_true",
                     help=f"write a dated snapshot under {UNIVERSE_DIR}")
    scr.add_argument("--config", metavar="PATH",
                     help="write/update a run config with these symbols")
    scr.set_defaults(func=cmd_screen)

    def _add_sim_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--symbols", help="comma separated tickers")
        p.add_argument("--start", default="2015-01-01")
        p.add_argument("--end", default="2030-01-01")
        p.add_argument("--interval", default="1d", choices=list(INTERVALS))
        p.add_argument("--cash", type=float, default=100_000.0)
        p.add_argument("--commission", type=float, default=1.0,
                       help="basis points per side")
        p.add_argument("--slippage", type=float, default=5.0,
                       help="basis points per side")
        p.add_argument("--offline", action="store_true",
                       help="synthetic prices, no network")

    strat = sub.add_parser("strategies", help="list the strategy library")
    strat.add_argument("--family")
    strat.set_defaults(func=cmd_strategies)

    sim = sub.add_parser("simulate", help="backtest a named strategy or ad-hoc rules")
    sim.add_argument("--strategy", help="name from `evotrader strategies`")
    sim.add_argument("--param", action="append", metavar="K=V",
                     help="override a strategy parameter (repeatable)")
    sim.add_argument("--entry", action="append", metavar="RULE",
                     help="entry rule, instead of a named strategy (repeatable)")
    sim.add_argument("--exit", action="append", metavar="RULE",
                     help="exit rule (repeatable)")
    sim.add_argument("--trades", type=int, default=0, help="show N trades")
    sim.add_argument("--walk-forward", action="store_true",
                     help="anchored folds instead of one window")
    sim.add_argument("--folds", type=int, default=3)
    sim.add_argument("--grid", action="append", metavar="K=V1,V2",
                     help="search these parameter values, scoring the winners "
                          "on a held-out window (repeatable)")
    sim.add_argument("--top", type=int, default=5,
                     help="how many of the best combinations to show")
    sim.add_argument("--workers", type=int, default=4)
    _add_sim_flags(sim)
    sim.set_defaults(func=cmd_simulate)

    cmp_ = sub.add_parser("compare", help="rank strategies over one universe")
    cmp_.add_argument("--names", help="comma separated strategy names")
    cmp_.add_argument("--family")
    cmp_.add_argument("--rank-by", dest="rank_by", default="fitness")
    cmp_.add_argument("--limit", type=int, default=20)
    cmp_.add_argument("--workers", type=int, default=4)
    _add_sim_flags(cmp_)
    cmp_.set_defaults(func=cmd_compare)

    doc = sub.add_parser("doctor", help="check data access, credentials and deps")
    doc.set_defaults(func=cmd_doctor)
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
