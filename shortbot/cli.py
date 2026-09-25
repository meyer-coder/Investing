"""shortbot command line.

    python -m shortbot backtest                       # 60 days of 5-minute NQ
    python -m shortbot backtest --data yahoo-hourly   # two years, hourly (coarse)
    python -m shortbot backtest --data my_mnq_5m.csv --bar-minutes 5
    python -m shortbot sweep                          # tune on the first 60%, judge on the rest
    python -m shortbot vs-random --data yahoo-hourly  # is it better than coin flips?
    python -m shortbot init-config bot.json           # write the default settings to edit
    python -m shortbot live --config bot.json         # dry run: watch TopstepX, place nothing
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import replace
from typing import List, Optional, Sequence

from . import backtest as bt
from .config import TOPSTEP_ACCOUNTS, BotConfig
from .data import Session, load_sessions


def _config(path: Optional[str], account: Optional[str] = None) -> BotConfig:
    cfg = BotConfig.load(path) if path else BotConfig()
    if account:
        cfg.account = replace(TOPSTEP_ACCOUNTS[account])
    return cfg


def _only_setups(cfg: BotConfig, setups: Optional[str]) -> BotConfig:
    if not setups:
        return cfg
    names = {s.strip() for s in setups.split(",") if s.strip()}
    bad = names - {"momentum", "orb", "vwap_reject"}
    if bad:
        raise SystemExit(f"unknown setups: {sorted(bad)}")
    cfg.strategy = replace(cfg.strategy, momentum="momentum" in names, orb="orb" in names,
                           vwap_reject="vwap_reject" in names)
    return cfg


def _split(sessions: Sequence[Session], cfg: BotConfig, frac: float):
    """Tradable dates (after the warm-up) split into a tuning part and a later
    part that tuning never sees."""
    from .strategy import ShortStrategy
    dates = [s.date for s in sessions[ShortStrategy(cfg.strategy).warmup_days():]]
    cut = int(len(dates) * frac)
    return dates, dates[:cut], dates[cut:]


def _report(trades, dates, cfg, title) -> str:
    sub = [t for t in trades if t.date in set(dates)]
    return bt.describe(sub, len(dates), bt.combine_attempts(sub, dates, cfg.account), title,
                       cfg.account.name)


def _cycle_report(trades, dates, cfg) -> str:
    """The whole plan -- Combine, resets, funded account, payouts, fees -- from
    the first tradable day to the end of the data, plus the spread of results
    from other start days.  Those runs share most of their trades, so they
    are one history seen from different doors, not independent trials."""
    runs = bt.cycles(trades, dates, cfg.account)
    if not runs:
        return ""
    import numpy as np
    first = runs[0]
    lines = [f"   whole plan on {cfg.account.name} (buy, reset until it passes, trade the funded "
             f"account until it is blown, repeat):"]
    lines += [f"      {line}" for line in first.story]
    lines.append(f"      => {first.payouts} payout(s), ${first.paid_to_trader:,.0f} to you, "
                 f"${first.fees:,.0f} in fees (subscriptions, resets, activations, API): "
                 f"net ${first.net:+,.0f}")
    net = np.asarray([c.net for c in runs])
    lines.append(f"      starting on any of the first {len(runs)} days instead: net between "
                 f"${net.min():+,.0f} and ${net.max():+,.0f} (median ${np.median(net):+,.0f}); "
                 f"these runs overlap, so treat it as one history, not {len(runs)} trials")
    return "\n".join(lines)


def cmd_backtest(a) -> None:
    cfg = _only_setups(_config(a.config, a.account), a.setups)
    sessions = load_sessions(a.data, a.bar_minutes, a.refresh)
    trades = bt.run(sessions, cfg)
    dates, first, last = _split(sessions, cfg, 0.6)
    print(f"data: {a.data}  {sessions[0].date} .. {sessions[-1].date}  "
          f"({len(sessions)} sessions, the first {len(sessions) - len(dates)} only used as history)")
    print(_report(trades, dates, cfg, "all tradable sessions"))
    print(_cycle_report(trades, dates, cfg))
    print(_report(trades, first, cfg, f"first 60% ({first[0]} .. {first[-1]})"))
    print(_report(trades, last, cfg, f"last 40% ({last[0]} .. {last[-1]})"))
    if a.trades:
        print("\n   date        setup        in     out    entry      exit  lots   stop   target    "
              "pnl$   worst$  exit")
        for t in trades:
            print(f"   {t.date}  {t.setup:<11} {bt._hhmm(t.entry_minute)}  {bt._hhmm(t.exit_minute)}  "
                  f"{t.entry:9.2f} {t.exit:9.2f}  {t.contracts:>3}  {t.stop - t.entry:6.1f}  "
                  f"{t.entry - t.target:6.1f}  {t.pnl_usd:+7.0f}  {t.mae_usd:+7.0f}  {t.exit_reason}")
    if a.json:
        out = {"config": cfg.to_dict(), "data": a.data,
               "all": bt.stats(trades, len(dates)).to_dict(),
               "trades": [t.__dict__ for t in trades]}
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1, default=float)
        print(f"\nwrote {a.json}")


def cmd_sweep(a) -> None:
    """Small grid search.  Settings are chosen on the first 60% of sessions
    only; the last 40% shows whether the choice held up."""
    base = _only_setups(_config(a.config, a.account), a.setups)
    sessions = load_sessions(a.data, a.bar_minutes, a.refresh)
    dates, first, last = _split(sessions, base, 0.6)
    fs, ls = set(first), set(last)
    grid = {"mom_k": [1.25, 1.5, 2.0], "stop_units": [0.75, 1.0, 1.5],
            "target_units": [1.0, 1.5, 2.5], "max_hold_minutes": [60, 120]}
    rows = []
    for combo in itertools.product(*grid.values()):
        cfg = BotConfig.from_dict(base.to_dict())
        cfg.strategy = replace(cfg.strategy, **dict(zip(grid, combo)))
        trades = bt.run(sessions, cfg)
        tr_first = [t for t in trades if t.date in fs]
        tr_last = [t for t in trades if t.date in ls]
        rows.append((dict(zip(grid, combo)), bt.stats(tr_first, len(first)),
                     bt.stats(tr_last, len(last))))
    rows.sort(key=lambda r: r[1].net_usd if r[1].trades >= a.min_trades else -1e18, reverse=True)
    print(f"{len(rows)} settings tried on {first[0]}..{first[-1]}, "
          f"then judged on {last[0]}..{last[-1]}")
    print("   settings                                         | tuning: trades   net$   win  |"
          " unseen: trades   net$   win")
    for params, s1, s2 in rows[:a.top]:
        ptxt = " ".join(f"{k}={v}" for k, v in params.items())
        print(f"   {ptxt:<48} | {s1.trades:>6} {s1.net_usd:+8,.0f} {s1.win_rate * 100:4.0f}% |"
              f" {s2.trades:>6} {s2.net_usd:+8,.0f} {s2.win_rate * 100:4.0f}%")
    positive_unseen = sum(1 for _, _, s2 in rows if s2.net_usd > 0)
    print(f"\n   {positive_unseen} of {len(rows)} settings made money on the unseen part")


def cmd_vs_random(a) -> None:
    """Is the strategy better than luck?  Runs many coin-flip bots with the
    same stops, targets, sizing and limits, and ranks the strategy among them
    -- on trading P&L, and on the whole Topstep plan."""
    import numpy as np
    from .strategy import RandomStrategy, ShortStrategy
    cfg = _only_setups(_config(a.config, a.account), a.setups)
    sessions = load_sessions(a.data, a.bar_minutes, a.refresh)
    dates, _, _ = _split(sessions, cfg, 0.6)
    real = bt.run(sessions, cfg)
    real_pnl = sum(t.pnl_usd for t in real)
    real_net = bt.cycles(real, dates, cfg.account, starts=1)[0].net
    # match the trade count: tune the coin's per-bar rate until it trades about as often
    need = ShortStrategy(cfg.strategy).warmup_days()
    rate = max(len(real), 1) / max(1, sum(len(s) for s in sessions[need:]))
    for _ in range(5):
        n = len(bt.run(sessions, cfg, RandomStrategy(cfg.strategy, rate, 10_000)))
        rate = min(1.0, rate * max(len(real), 1) / max(n, 1))
    pnls, nets, counts = [], [], []
    for seed in range(a.runs):
        tr = bt.run(sessions, cfg, RandomStrategy(cfg.strategy, rate, seed))
        pnls.append(sum(t.pnl_usd for t in tr))
        nets.append(bt.cycles(tr, dates, cfg.account, starts=1)[0].net)
        counts.append(len(tr))
    pnls, nets = np.asarray(pnls), np.asarray(nets)
    print(f"{a.data}: {dates[0]} .. {dates[-1]}; strategy took {len(real)} trades, "
          f"the {a.runs} coin-flip bots took {np.median(counts):.0f} each (median)")
    for label, mine, dist in (("trading P&L", real_pnl, pnls),
                              (f"whole plan on {cfg.account.name}", real_net, nets)):
        print(f"   {label:<34} strategy ${mine:+9,.0f} | coin flips: median ${np.median(dist):+,.0f}, "
              f"10th-90th ${np.percentile(dist, 10):+,.0f} .. ${np.percentile(dist, 90):+,.0f}"
              f" | strategy beats {float(np.mean(dist < mine)) * 100:.0f}% of them")
    print("   Beating ~95% on trading P&L, in more than one period, is the bar for calling it an edge.")


def cmd_init_config(a) -> None:
    BotConfig().save(a.path)
    print(f"wrote {a.path}")


def cmd_live(a) -> None:
    from .live import run_live
    run_live(_config(a.config, a.account), live=a.live, account_id=a.account_id, log_path=a.log,
             allow_account_risk=a.allow_account_risk)


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(prog="shortbot", description="MNQ day-trading bot for Topstep")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def data_args(p):
        p.add_argument("--data", default="yahoo",
                       help="yahoo | yahoo-hourly | path to a CSV of timestamp,o,h,l,c,v")
        p.add_argument("--bar-minutes", type=int, default=5, help="bar size of a CSV file")
        p.add_argument("--config", help="JSON settings file (see init-config)")
        p.add_argument("--setups", help="comma list: momentum,orb,vwap_reject")
        p.add_argument("--account", choices=sorted(TOPSTEP_ACCOUNTS),
                       help="Topstep account size (overrides the config file's account)")
        p.add_argument("--refresh", action="store_true", help="re-download data")

    b = sub.add_parser("backtest", help="replay the bot over history")
    data_args(b)
    b.add_argument("--trades", action="store_true", help="list every trade")
    b.add_argument("--json", help="write stats and trades to this file")
    b.set_defaults(fn=cmd_backtest)

    s = sub.add_parser("sweep", help="try a grid of settings without peeking at the test part")
    data_args(s)
    s.add_argument("--top", type=int, default=10)
    s.add_argument("--min-trades", type=int, default=10)
    s.set_defaults(fn=cmd_sweep)

    v = sub.add_parser("vs-random", help="rank the strategy against coin-flip bots")
    data_args(v)
    v.add_argument("--runs", type=int, default=200)
    v.set_defaults(fn=cmd_vs_random)

    i = sub.add_parser("init-config", help="write the default settings file")
    i.add_argument("path")
    i.set_defaults(fn=cmd_init_config)

    lv = sub.add_parser("live", help="run against TopstepX (dry run unless --live)")
    lv.add_argument("--config", help="JSON settings file")
    lv.add_argument("--account", choices=sorted(TOPSTEP_ACCOUNTS),
                    help="Topstep account size the risk checks use")
    lv.add_argument("--live", action="store_true",
                    help="actually place orders (default: log what it would do)")
    lv.add_argument("--account-id", type=int, help="TopstepX account id to trade")
    lv.add_argument("--log", default="runs/shortbot-live.log")
    lv.add_argument("--allow-account-risk", action="store_true",
                    help="trade even if one losing trade could use up the account's whole max loss")
    lv.set_defaults(fn=cmd_live)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
