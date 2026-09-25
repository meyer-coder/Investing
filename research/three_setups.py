"""Out-of-sample test of the 'Three MNQ Setups' (rejection short, failed
breakdown long, failed breakout short).

The setups were written down from one day's chart (2026-09-25) and checked
on six sessions of 1-minute data.  This replays the same rules -- ``signal``
below is copied unchanged from that document's setups.py, and a rebuild of it
reproduces the document's 7 trades exactly -- over every regular session in
Yahoo's 60 days of 5-minute MNQ bars, and ranks the result against random
entries that use the same 30/45-point bracket, timing and limits.

5-minute bars cannot say whether the stop or the target came first when one
bar touches both, so every result is given twice: ``stop first`` (the
pessimistic bound) and ``target first`` (the optimistic one).  The truth lies
between.

    python research/three_setups.py            # uses cached bars if present
    python research/three_setups.py --refresh
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shortbot.data import NY, clean_sessions, fetch_yahoo, to_sessions  # noqa: E402

POINT, TICK, COMM = 2.0, 0.25, 0.75          # $ a point per MNQ, the tick, commission a contract a side
SIZE, STOP, TARGET = 2, 30.0, 45.0
DAY_STOP, MAX_TRADES = 600.0, 6
FIRST_SIGNAL, LAST_SIGNAL = dt.time(9, 45), dt.time(15, 30)
FLAT = (15, 55)
RULES_DAY = "2026-09-25"                     # the day the thresholds were read from


def et(t: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(t, NY)


# ------------------------------------------------------------------ candles

def candles_from_sessions(sessions) -> List[dict]:
    """Regular-session 5-minute candles, oldest first, in the document's format."""
    out = []
    for s in sessions:
        day = dt.date.fromisoformat(s.date)
        for m, o, h, lo, c, v in zip(s.minute, s.open, s.high, s.low, s.close, s.volume):
            start = int(dt.datetime(day.year, day.month, day.day, int(m) // 60, int(m) % 60,
                                    tzinfo=NY).timestamp())
            out.append({"day": day, "start": start, "end": start + 300, "o": float(o), "h": float(h),
                        "l": float(lo), "c": float(c), "v": float(v)})
    return out


def annotate(cs: List[dict]) -> None:
    """ATR(14) over regular-session 5-minute candles (previous days included) and
    VWAP anchored at each session's 09:30 -- as in the document."""
    prev_close, trs = None, []
    pv = vol = 0.0
    day = None
    for c in cs:
        tr = c["h"] - c["l"] if prev_close is None else max(c["h"], prev_close) - min(c["l"], prev_close)
        trs.append(tr)
        c["atr"] = float(np.mean(trs[-14:]))
        prev_close = c["c"]
        if c["day"] != day:
            day, pv, vol = c["day"], 0.0, 0.0
        w = max(c["v"], 1.0)
        pv += (c["h"] + c["l"] + c["c"]) / 3 * w
        vol += w
        c["vwap"] = pv / vol


# ------------------------------------------------ the setups (from the document)

def parts(c: dict):
    rng = max(c["h"] - c["l"], 1e-9)
    return rng, abs(c["c"] - c["o"]), c["h"] - max(c["o"], c["c"]), (c["c"] - c["l"]) / rng


def signal(day_cs: List[dict], t: int, used: Optional[Dict[str, int]] = None) -> Optional[tuple]:
    used = used or {}
    c = day_cs[t]
    if not (FIRST_SIGNAL <= et(c["end"]).time() <= LAST_SIGNAL) or t < 6:
        return None
    rng, body, up, pos = parts(c)
    atr = c["atr"]
    avg6 = float(np.mean([x["v"] for x in day_cs[t - 6:t]]))
    # A. a second rejection at the recent top, on volume
    top12 = max(x["h"] for x in day_cs[max(0, t - 12):t])
    prior_reject = any(parts(x)[2] >= 0.5 * parts(x)[0] and abs(x["h"] - c["h"]) <= 0.6 * atr
                       for i, x in enumerate(day_cs[t - 6:t], t - 6) if i > used.get("A", -1))
    if (up >= 0.5 * rng and pos <= 1 / 3 and rng >= 0.6 * atr and c["h"] >= top12 - 0.6 * atr and prior_reject
            and c["v"] >= 1.3 * avg6):
        return "A", -1
    # B. support swept and reclaimed, then a strong candle up through VWAP
    if t >= 15:
        support = min(x["l"] for x in day_cs[t - 15:t - 3])
        swept = any(x["l"] < support and x["c"] > support
                    for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used.get("B", -1))
        if (swept and c["c"] > c["o"] and body >= 0.6 * rng and pos >= 0.8 and rng >= atr and c["c"] > c["vwap"]
                and c["v"] >= avg6):
            return "B", 1
    # C. a new session high made and lost
    if t >= 4:
        level = max(x["h"] for x in day_cs[:t - 3])
        broke = any(x["h"] > level for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used.get("C", -1))
        if broke and c["h"] >= level and c["c"] < level and pos <= 0.35 and up >= 0.3 * rng:
            return "C", -1
    return None


# ------------------------------------------------------------------ the replay

def replay_day(day_cs: List[dict], chooser, target_first: bool) -> List[dict]:
    """One session, booked as in the document but on 5-minute bars: entry at the
    next candle's open plus a tick, a 30-point stop and 45-point target from the
    fill, a tick of slippage on a stop, $0.75 a contract a side, one trade at a
    time, one trade per trigger, at most 6 trades, day stop -$600 with the open
    trade included (checked at each bar close), flat at 15:55.  ``chooser``
    returns (setup, side) or None for candle t."""
    trades, used, realized, busy_until, done = [], {}, 0.0, 0, False
    for t in range(len(day_cs)):
        if done or len(trades) >= MAX_TRADES or day_cs[t]["end"] < busy_until:
            continue
        sig = chooser(day_cs, t, used)
        if not sig:
            continue
        setup, side = sig
        seq = day_cs[t + 1:]
        if not seq:
            break
        used[setup] = t
        entry = seq[0]["o"] + side * TICK
        stop, target = entry - side * STOP, entry + side * TARGET
        exit_px = exit_t = why = None
        ambiguous = False
        for k, b in enumerate(seq):
            o, h, lo, c = b["o"], b["h"], b["l"], b["c"]
            if (et(b["start"]).hour, et(b["start"]).minute) >= FLAT:
                exit_px, why = o - side * TICK, "flat for the close"
            else:
                hit_stop = (side > 0 and lo <= stop) or (side < 0 and h >= stop)
                hit_target = (side > 0 and h >= target) or (side < 0 and lo <= target)
                gap_stop = k > 0 and ((side > 0 and o <= stop) or (side < 0 and o >= stop))
                ambiguous = hit_stop and hit_target and not gap_stop
                if hit_stop and (not hit_target or gap_stop or not target_first):
                    exit_px, why = (min(o, stop) if side > 0 else max(o, stop)) - side * TICK, "stop"
                elif hit_target:
                    exit_px, why = target, "target"
                elif realized + side * (c - entry) * POINT * SIZE <= -DAY_STOP:
                    exit_px, why, done = c - side * TICK, "day stop", True
            if exit_px is not None:
                exit_t = b["end"] if why not in ("flat for the close",) else b["start"]
                break
        if exit_px is None:
            break
        usd = side * (exit_px - entry) * POINT * SIZE - 2 * COMM * SIZE
        realized += usd
        trades.append({"day": str(day_cs[t]["day"]), "setup": setup, "side": side,
                       "entry_time": et(seq[0]["start"]).strftime("%H:%M"), "entry": entry,
                       "exit": exit_px, "why": why, "usd": round(usd, 2), "ambiguous": ambiguous})
        busy_until = exit_t
        if realized <= -DAY_STOP:
            done = True
    return trades


def run(cs: List[dict], chooser, target_first: bool) -> List[dict]:
    by_day: Dict[dt.date, List[dict]] = {}
    for c in cs:
        by_day.setdefault(c["day"], []).append(c)
    out = []
    for d in sorted(by_day):
        out.extend(replay_day(by_day[d], chooser, target_first))
    return out


class Random:
    """Random entries on the same candles: fires with probability ``rate`` on
    any candle inside the signal window, long with probability ``long_share``."""

    def __init__(self, rate: float, long_share: float, seed: int):
        self.rate, self.long_share = rate, long_share
        self.rng = np.random.default_rng(seed)

    def __call__(self, day_cs, t, used):
        c = day_cs[t]
        if not (FIRST_SIGNAL <= et(c["end"]).time() <= LAST_SIGNAL) or t < 6:
            return None
        if self.rng.random() > self.rate:
            return None
        return ("R", 1) if self.rng.random() < self.long_share else ("R", -1)


def summary(trades: List[dict]) -> str:
    if not trades:
        return "no trades"
    usd = np.array([t["usd"] for t in trades])
    return (f"{len(usd):>3} trades, won {int((usd > 0).sum()):>2} ({(usd > 0).mean() * 100:3.0f}%), "
            f"net ${usd.sum():+8,.0f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--runs", type=int, default=500)
    a = ap.parse_args(argv)

    dropped: list = []
    rows = [r for r in fetch_yahoo("MNQ=F", "5m", "60d", a.refresh) if r[0] % 300 == 0]
    sessions = clean_sessions(to_sessions(rows, 5, min_bars=62), True, dropped)
    now = dt.datetime.now(NY)
    if sessions and sessions[-1].date == now.strftime("%Y-%m-%d") and (now.hour, now.minute) < (16, 15):
        dropped.append((sessions[-1].date, "today's session is not finished"))
        sessions = sessions[:-1]
    cs = candles_from_sessions(sessions)
    annotate(cs)
    days = sorted({c["day"] for c in cs})
    print(f"MNQ=F 5-minute bars: {len(days)} regular sessions, {days[0]} .. {days[-1]}"
          f" (dropped {len(dropped)}: expiry week / unfinished / broken)")

    for target_first in (False, True):
        label = "target first (optimistic)" if target_first else "stop first (pessimistic)"
        trades = run(cs, signal, target_first)
        rules_day = [t for t in trades if t["day"] == RULES_DAY]
        other = [t for t in trades if t["day"] != RULES_DAY]
        print(f"\n== the three setups, {label}")
        print(f"   all sessions:                 {summary(trades)}")
        print(f"   the day the rules came from:  {summary(rules_day)}")
        print(f"   every other day:              {summary(other)}")
        for s in ("A", "B", "C"):
            print(f"     setup {s}: {summary([t for t in other if t['setup'] == s])}")
        amb = sum(t["ambiguous"] for t in trades)
        print(f"   trades where one bar touched both stop and target: {amb}")

        # random entries with the same bracket, count and long/short mix (other days only)
        other_cs = [c for c in cs if str(c["day"]) != RULES_DAY]
        long_share = float(np.mean([t["side"] > 0 for t in other])) if other else 0.5
        window = sum(1 for c in other_cs if FIRST_SIGNAL <= et(c["end"]).time() <= LAST_SIGNAL)
        rate = max(len(other), 1) / max(window, 1)
        for _ in range(5):
            n = len(run(other_cs, Random(rate, long_share, 10_000), target_first))
            rate = min(1.0, rate * max(len(other), 1) / max(n, 1))
        nets = np.array([sum(t["usd"] for t in run(other_cs, Random(rate, long_share, seed), target_first))
                         for seed in range(a.runs)])
        mine = sum(t["usd"] for t in other)
        print(f"   {a.runs} random-entry bots on the other days (same bracket, count, "
              f"{long_share * 100:.0f}% long): median ${np.median(nets):+,.0f}, "
              f"10th-90th ${np.percentile(nets, 10):+,.0f} .. ${np.percentile(nets, 90):+,.0f}"
              f" -> the setups beat {float(np.mean(nets < mine)) * 100:.0f}% of them")


if __name__ == "__main__":
    main()
