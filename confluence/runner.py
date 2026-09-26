"""Run every strategy: build signals, backtest, score, log.

Work is grouped by price feed (MNQ and NAS100 share NSXUSD, so their
indicators are computed once) and then by timeframe, and the feeds are
spread over worker processes.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Sequence

import numpy as np

from . import indicators as ind
from .bars import SESSIONS, minute_clock, resample
from .components import Ctx
from .data import load_feed
from .engine import ENTRY_CODE, STOP_CODE, TARGET_CODE, run
from .families import Strategy
from .markets import MARKETS
from .metrics import Calendar, evaluate, profile

MAX_PER_DAY = 4


def _log(msg: str) -> None:
    print(f"[run {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def signals(ctx: Ctx, s: Strategy, sessions=None):
    n = ctx.f.n
    if s.fam.group == "Control":
        ws, we, _ = (sessions or SESSIONS)[s.session]
        p = min(s.tf / (max(we - ws, s.tf) * 2.0), 0.5)
        u = np.random.default_rng(s.seed).random(n)
        return u < p / 2, (u >= p / 2) & (u < p)
    L = np.ones(n, dtype=bool)
    S = np.ones(n, dtype=bool)
    for code in s.legs:
        lo, sh = ctx.leg(code)
        L &= lo
        S &= sh
    return L, S


def backtest_frame(ctx: Ctx, s: Strategy, start_bar: int, markets=None,
                   sessions=None) -> Dict[str, np.ndarray]:
    f = ctx.f
    m = f.clock.m
    mk = (markets or MARKETS)[s.market]
    L, S = signals(ctx, s, sessions)
    ws, we, ex = (sessions or SESSIONS)[s.session]
    st, k = STOP_CODE[s.stop]
    tr, trail = TARGET_CODE[s.target]
    swing_lo = ctx.get("swing_lo", lambda: ind.rolling_min(f.l, 5))
    swing_hi = ctx.get("swing_hi", lambda: ind.rolling_max(f.h, 5))
    n_days = int(np.unique(f.day[start_bar:]).size)
    cap = MAX_PER_DAY * n_days + 16
    e_min, x_min, e_day, dirs, gross, cost, reason = run(
        L, S, f.h, f.l, f.hi, f.tdm_close.astype(np.int64), f.day, ctx.atr, swing_lo, swing_hi,
        m.t, m.o, m.h, m.l, m.c, f.clock.tdm.astype(np.int64), f.clock.day, f.m1_bar,
        ENTRY_CODE[s.entry], st, k, tr, trail, ws, we, ex, mk.cost_rt, mk.tick,
        start_bar, MAX_PER_DAY, cap)
    return {"entry": e_min, "exit": x_min, "day": e_day, "dir": dirs, "gross": gross,
            "cost": cost, "reason": reason}


def run_feed(feed: str, strategies: List[Strategy], start: dt.date, end: dt.date,
             trades_dir: Optional[str], markets=None, sessions=None) -> List[dict]:
    t0 = time.time()
    mins = load_feed(feed)
    clock = minute_clock(mins)
    cal = Calendar.build(clock.day, start, end)
    if trades_dir:
        os.makedirs(trades_dir, exist_ok=True)
        np.savez(os.path.join(trades_dir, f"cal_{feed}.npz"), days=cal.days,
                 bounds=np.array([cal.start, cal.d3y, cal.d12m, cal.d6m, cal.end]))
    by_tf: Dict[int, List[Strategy]] = defaultdict(list)
    for s in strategies:
        by_tf[s.tf].append(s)
    rows: List[dict] = []
    for tf in sorted(by_tf):
        t1 = time.time()
        frame = resample(clock, tf)
        ctx = Ctx(frame)
        start_bar = int(np.searchsorted(frame.day, cal.start))
        packed = defaultdict(list)
        for s in by_tf[tf]:
            tr = backtest_frame(ctx, s, start_bar, markets, sessions)
            res = evaluate(tr, cal, seed=s.seed % (2 ** 31))
            res["profile"] = profile(tr, cal)
            res["sid"] = s.sid
            rows.append(res)
            if trades_dir:
                packed["sid"].append(np.full(tr["gross"].size, s.sid, dtype="U10"))
                for key, v in tr.items():
                    packed[key].append(v)
        if trades_dir and packed:
            os.makedirs(trades_dir, exist_ok=True)
            np.savez_compressed(os.path.join(trades_dir, f"{feed}_{tf}m.npz"),
                                **{k: np.concatenate(v) for k, v in packed.items()})
        _log(f"{feed} {tf:>2}m: {len(by_tf[tf]):>4} strategies, {frame.n:,} bars, "
             f"{time.time() - t1:5.1f}s")
        del ctx, frame
    _log(f"{feed}: done in {time.time() - t0:.0f}s")
    return rows


def run_all(strategies: Sequence[Strategy], start: dt.date, end: dt.date, *,
            workers: int = 4, trades_dir: Optional[str] = "runs/trades", markets=None,
            sessions=None) -> Dict[str, dict]:
    """Backtest every strategy.  ``markets`` / ``sessions`` default to the first run's."""
    mk = markets or MARKETS
    by_feed: Dict[str, List[Strategy]] = defaultdict(list)
    for s in strategies:
        by_feed[mk[s.market].feed].append(s)
    order = sorted(by_feed, key=lambda f: -len(by_feed[f]))   # biggest first
    results: Dict[str, dict] = {}
    if workers <= 1:
        for feed in order:
            for r in run_feed(feed, by_feed[feed], start, end, trades_dir, markets, sessions):
                results[r["sid"]] = r
        return results
    with ProcessPoolExecutor(workers) as ex:
        futs = {ex.submit(run_feed, feed, by_feed[feed], start, end, trades_dir, markets, sessions): feed
                for feed in order}
        for fut in as_completed(futs):
            for r in fut.result():
                results[r["sid"]] = r
    return results


def feed_calendar(feed: str, start: dt.date, end: dt.date) -> Calendar:
    return Calendar.build(minute_clock(load_feed(feed)).day, start, end)
