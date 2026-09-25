"""Can the Three MNQ Setups be refined into something that works?  An honest
search on 13 years of one-minute Nasdaq-100 bars (Dukascopy, research/duka.py).

The protocol is fixed before looking at any result:

1. search    2013-2019: every variant below is scored; a variant survives with
             at least 100 trades, a positive mean and t >= 2.0;
2. confirm   2020-2022: survivors must be positive again and beat at least
             90% of random-entry bots with the same bracket, window, trade
             count and long/short mix;
3. final     2023-2026: looked at once, for the confirmed variants only.

Variants: each setup alone (A, B, C from the document, plus their mirror
images A', B', C'), and the document's three together; with and without the
volume conditions (the data's volume is a tick count, not exchange volume);
all day (09:45-15:30) or mornings only (09:45-12:00); and 16 exits -- the
document's bracket scaled to today's price (0.10% stop, 0.15% target),
stops of 1, 1.5 or 2 x ATR with targets of 1, 1.5, 2 or 3 x the stop, or the
same stops with no target, held to 15:55.

Every trade: entry at the next minute's open after the 5-minute candle
closes, stop and target resting from the fill (a target fills when touched, a
stop at the stop or at the open if the price gaps through it), out by 15:55,
one trade at a time, at most 6 a day, 1 bp of the price per round trip in
costs.  Results are in basis points of the price per trade, and in dollars
per trade for 2 MNQ at today's level.

    python research/refine_setups.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duka import sessions as duka_sessions  # noqa: E402
from shortbot.data import NY  # noqa: E402
from three_setups import annotate, candles_from_sessions, parts  # noqa: E402

COST = 1e-4
USD_PER_BP_2MNQ = 30_478 * 2.0 * 2 / 10_000          # $ per basis point for 2 MNQ at today's price
FLAT_MIN = 15 * 60 + 55
PERIODS = {"search": ("2013-01-01", "2019-12-31"), "confirm": ("2020-01-01", "2022-12-31"),
           "final": ("2023-01-01", "2099-12-31")}


# ------------------------------------------------------------------ the setups

def signals_for_day(day_cs: List[dict], setup: str, use_volume: bool, window_end: int) -> List[Tuple[int, int]]:
    """(candle index, side) for every candle that sets ``setup`` up.  The
    document's conditions; primed setups are exact mirror images."""
    out, used = [], -1
    for t in range(6, len(day_cs)):
        c = day_cs[t]
        end = c["end_min"]
        if not (9 * 60 + 45 <= end <= window_end):
            continue
        rng, body, up, pos = parts(c)
        low_wick = min(c["o"], c["c"]) - c["l"]
        atr = c["atr"]
        avg6 = float(np.mean([x["v"] for x in day_cs[t - 6:t]]))
        vol_ok = (lambda k: c["v"] >= k * avg6) if use_volume else (lambda k: True)
        side = 0
        if setup == "A":                                   # rejection at the recent top -> short
            top12 = max(x["h"] for x in day_cs[max(0, t - 12):t])
            prior = any(parts(x)[2] >= 0.5 * parts(x)[0] and abs(x["h"] - c["h"]) <= 0.6 * atr
                        for i, x in enumerate(day_cs[t - 6:t], t - 6) if i > used)
            if up >= 0.5 * rng and pos <= 1 / 3 and rng >= 0.6 * atr and c["h"] >= top12 - 0.6 * atr \
                    and prior and vol_ok(1.3):
                side = -1
        elif setup == "A'":                                # rejection at the recent bottom -> long
            bot12 = min(x["l"] for x in day_cs[max(0, t - 12):t])
            prior = any((min(x["o"], x["c"]) - x["l"]) >= 0.5 * parts(x)[0] and abs(x["l"] - c["l"]) <= 0.6 * atr
                        for i, x in enumerate(day_cs[t - 6:t], t - 6) if i > used)
            if low_wick >= 0.5 * rng and pos >= 2 / 3 and rng >= 0.6 * atr and c["l"] <= bot12 + 0.6 * atr \
                    and prior and vol_ok(1.3):
                side = 1
        elif setup == "B" and t >= 15:                     # support swept, reclaimed, strong green -> long
            support = min(x["l"] for x in day_cs[t - 15:t - 3])
            swept = any(x["l"] < support and x["c"] > support for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used)
            if swept and c["c"] > c["o"] and body >= 0.6 * rng and pos >= 0.8 and rng >= atr \
                    and c["c"] > c["vwap"] and vol_ok(1.0):
                side = 1
        elif setup == "B'" and t >= 15:                    # resistance swept, lost, strong red -> short
            resist = max(x["h"] for x in day_cs[t - 15:t - 3])
            swept = any(x["h"] > resist and x["c"] < resist for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used)
            if swept and c["c"] < c["o"] and body >= 0.6 * rng and pos <= 0.2 and rng >= atr \
                    and c["c"] < c["vwap"] and vol_ok(1.0):
                side = -1
        elif setup == "C" and t >= 4:                      # new session high made and lost -> short
            level = max(x["h"] for x in day_cs[:t - 3])
            broke = any(x["h"] > level for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used)
            if broke and c["h"] >= level and c["c"] < level and pos <= 0.35 and up >= 0.3 * rng:
                side = -1
        elif setup == "C'" and t >= 4:                     # new session low made and reclaimed -> long
            level = min(x["l"] for x in day_cs[:t - 3])
            broke = any(x["l"] < level for i, x in enumerate(day_cs[t - 3:t], t - 3) if i > used)
            if broke and c["l"] <= level and c["c"] > level and pos >= 0.65 and low_wick >= 0.3 * rng:
                side = 1
        if side:
            out.append((t, side))
            used = t
    return out


# --------------------------------------------------------------------- exits

EXITS: List[Tuple[str, str, float, Optional[float]]] = [("doc 0.10%/0.15%", "pct", 0.0010, 0.0015)]
for s in (1.0, 1.5, 2.0):
    for m in (1.0, 1.5, 2.0, 3.0):
        EXITS.append((f"{s:g} ATR stop, {m:g}R target", "atr", s, m))
    EXITS.append((f"{s:g} ATR stop, to the close", "atr", s, None))


@dataclass
class Outcome:
    exit_min: int
    ret: float        # net of costs, fraction of the entry price


def outcome(mins: np.ndarray, o, h, lo, c, start: int, side: int, atr: float,
            kind: str, a: float, b: Optional[float]) -> Optional[Outcome]:
    """Trade from the minute bar at index ``start`` (entry at its open)."""
    if start >= len(mins) or mins[start] >= FLAT_MIN:
        return None
    entry = o[start]
    if kind == "pct":
        stop_d, tgt_d = entry * a, entry * b
    else:
        stop_d = a * atr
        tgt_d = None if b is None else b * stop_d
    stop = entry - side * stop_d
    target = None if tgt_d is None else entry + side * tgt_d
    for k in range(start, len(mins)):
        if mins[k] >= FLAT_MIN:
            return Outcome(int(mins[k]), side * (o[k] / entry - 1) - COST)
        if (side > 0 and lo[k] <= stop) or (side < 0 and h[k] >= stop):
            px = stop if k == start else (min(o[k], stop) if side > 0 else max(o[k], stop))
            return Outcome(int(mins[k]) + 1, side * (px / entry - 1) - COST)
        if target is not None and ((side > 0 and h[k] >= target) or (side < 0 and lo[k] <= target)):
            return Outcome(int(mins[k]) + 1, side * (target / entry - 1) - COST)
    return Outcome(int(mins[-1]) + 1, side * (c[-1] / entry - 1) - COST)


# ------------------------------------------------------------------ the book

def book(day_trades: List[Tuple[int, int, Outcome]]) -> List[Tuple[int, float]]:
    """One at a time, at most 6 a day, day stop at -$600 on 2 MNQ at today's price
    (about -98 bp): (side, ret) of the trades actually taken."""
    taken, free_at, day_bp = [], 0, 0.0
    for entry_min, side, out in day_trades:
        if entry_min < free_at or len(taken) >= 6 or day_bp <= -600 / USD_PER_BP_2MNQ:
            continue
        taken.append((side, out.ret))
        day_bp += out.ret * 1e4
        free_at = out.exit_min
    return taken


def stats(rets: List[float]) -> Tuple[int, float, float]:
    a = np.asarray(rets) * 1e4
    if len(a) < 2:
        return len(a), float(a.mean()) if len(a) else 0.0, 0.0
    return len(a), float(a.mean()), float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a))))


def main() -> None:
    s5 = duka_sessions(5)
    s1 = {s.date: s for s in duka_sessions(1)}
    s5 = [s for s in s5 if s.date in s1]
    cs = candles_from_sessions(s5)
    annotate(cs)
    by_day: Dict[str, List[dict]] = {s.date: [] for s in s5}
    for c in cs:
        t0 = dt.datetime.fromtimestamp(c["start"], NY)
        c["end_min"] = t0.hour * 60 + t0.minute + 5          # minutes since midnight, New York
        by_day[str(c["day"])].append(c)
    days = sorted(by_day)
    print(f"{len(days)} sessions, {days[0]} .. {days[-1]}; "
          f"search {sum(d <= PERIODS['search'][1] for d in days)}, "
          f"confirm {sum(PERIODS['confirm'][0] <= d <= PERIODS['confirm'][1] for d in days)}, "
          f"final {sum(d >= PERIODS['final'][0] for d in days)}")

    minute_arrays = {d: (s1[d].minute, s1[d].open, s1[d].high, s1[d].low, s1[d].close) for d in days}

    signal_cache: Dict[tuple, list] = {}
    outcome_cache: Dict[tuple, Optional[Outcome]] = {}

    def trades_for(setups, use_volume, window_end, exit_def, which_days):
        """Per day, the trades a variant takes: list of (day, side, ret)."""
        out = []
        for d in which_days:
            day_cs = by_day[d]
            mins, o, h, lo, c = minute_arrays[d]
            cands = []
            for st in setups:
                key = (d, st, use_volume, window_end)
                if key not in signal_cache:
                    signal_cache[key] = signals_for_day(day_cs, st, use_volume, window_end)
                for t, side in signal_cache[key]:
                    okey = (d, t, side, exit_def[0])
                    if okey not in outcome_cache:
                        start = int(np.searchsorted(mins, day_cs[t]["end_min"]))
                        outcome_cache[okey] = outcome(mins, o, h, lo, c, start, side, day_cs[t]["atr"],
                                                      *exit_def[1:])
                    oc = outcome_cache[okey]
                    if oc is not None:
                        cands.append((day_cs[t]["end_min"], side, oc))
            cands.sort(key=lambda x: x[0])
            out.extend((d, side, r) for side, r in book(cands))
        return out

    def in_period(name):
        lo_, hi_ = PERIODS[name]
        return [d for d in days if lo_ <= d <= hi_]

    variants = []
    for setups in (("A",), ("A'",), ("B",), ("B'",), ("C",), ("C'",), ("A", "B", "C")):
        for use_volume in (True, False):
            if not use_volume and setups in (("C",), ("C'",)):
                continue                                    # C has no volume condition
            for window_end, wname in ((15 * 60 + 30, "all day"), (12 * 60, "mornings")):
                for ex in EXITS:
                    variants.append((setups, use_volume, window_end, wname, ex))
    print(f"{len(variants)} variants\n")

    # 1. search
    search_days = in_period("search")
    scored = []
    for v in variants:
        tr = trades_for(v[0], v[1], v[2], v[4], search_days)
        n, mean, t = stats([r for _, _, r in tr])
        scored.append((v, n, mean, t))
    passed = [x for x in scored if x[1] >= 100 and x[2] > 0 and x[3] >= 2.0]
    print(f"1) search 2013-2019: {len(passed)} of {len(scored)} variants have 100+ trades, a positive "
          f"mean and t >= 2.0 (about {0.023 * len(scored):.0f} would by luck alone)")
    orig = [x for x in scored if x[0][0] == ("A", "B", "C") and x[0][1] and x[0][3] == "all day"
            and x[0][4][0].startswith("doc")][0]
    print(f"   the document's own rules (A+B+C, volume, all day, its bracket): n={orig[1]}, "
          f"{orig[2]:+.2f} bp a trade (${orig[2] * USD_PER_BP_2MNQ:+.0f} on 2 MNQ), t={orig[3]:+.1f}; "
          f"gross of costs {orig[2] + 1:+.2f} bp")
    positive = sum(1 for x in scored if x[1] >= 100 and x[2] > 0)
    print(f"   {positive} of {len(scored)} variants with 100+ trades had a positive mean after costs; "
          f"the ten strongest, pass or not (costs are 1 bp; add it back for the gross):")
    for v, n, mean, t in sorted([x for x in scored if x[1] >= 100], key=lambda x: -x[3])[:10]:
        print(f"   {'+'.join(v[0]):<6} vol={'on ' if v[1] else 'off'} {v[3]:<8} {v[4][0]:<26} "
              f"n={n:>5} {mean:+6.2f} bp (gross {mean + 1:+.2f}) t={t:+.1f}")
    print("   passing variants:")
    for v, n, mean, t in sorted(passed, key=lambda x: -x[3])[:15]:
        print(f"   {'+'.join(v[0]):<6} vol={'on ' if v[1] else 'off'} {v[3]:<8} {v[4][0]:<26} "
              f"n={n:>5} {mean:+6.2f} bp (${mean * USD_PER_BP_2MNQ:+5.0f}) t={t:+.1f}")

    # 2. confirm
    confirm_days = in_period("confirm")
    print("\n2) confirm 2020-2022 (positive, and beats >= 90% of 200 random-entry bots):")
    confirmed = []
    for v, n0, m0, t0 in passed:
        tr = trades_for(v[0], v[1], v[2], v[4], confirm_days)
        n, mean, t = stats([r for _, _, r in tr])
        if n < 30 or mean <= 0:
            print(f"   {'+'.join(v[0]):<6} {v[3]:<8} {v[4][0]:<26} n={n:>4} {mean:+6.2f} bp  -> out")
            continue
        pct = random_rank(v, tr, confirm_days, by_day, minute_arrays, mean)
        verdict = "CONFIRMED" if pct >= 90 else "out"
        print(f"   {'+'.join(v[0]):<6} {v[3]:<8} {v[4][0]:<26} n={n:>4} {mean:+6.2f} bp t={t:+.1f} "
              f"beats {pct:.0f}% of random -> {verdict}")
        if pct >= 90:
            confirmed.append(v)

    # 3. final
    final_days = in_period("final")
    print(f"\n3) final look, 2023-2026, confirmed variants only ({len(confirmed)}):")
    for v in confirmed:
        tr = trades_for(v[0], v[1], v[2], v[4], final_days)
        n, mean, t = stats([r for _, _, r in tr])
        pct = random_rank(v, tr, final_days, by_day, minute_arrays, mean) if n >= 10 else float("nan")
        print(f"   {'+'.join(v[0]):<6} vol={'on ' if v[1] else 'off'} {v[3]:<8} {v[4][0]:<26} n={n:>4} "
              f"{mean:+6.2f} bp (${mean * USD_PER_BP_2MNQ:+.0f} a trade on 2 MNQ, "
              f"${mean * USD_PER_BP_2MNQ * n / max(len(final_days), 1):+.0f} a day) t={t:+.1f} "
              f"beats {pct:.0f}% of random")


def random_rank(v, real_trades, which_days, by_day, minute_arrays, real_mean, runs: int = 200) -> float:
    """Share of random-entry bots (same exit, window, count and long/short mix)
    whose mean trade is below the variant's."""
    setups, use_volume, window_end, _, ex = v
    n_real = len(real_trades)
    long_share = float(np.mean([s > 0 for _, s, _ in real_trades])) if real_trades else 0.5
    slots = [(d, t) for d in which_days for t, c in enumerate(by_day[d])
             if t >= 6 and 9 * 60 + 45 <= c["end_min"] <= window_end]
    means = []
    rng = np.random.default_rng(7)
    for _ in range(runs):
        picks = rng.choice(len(slots), size=min(len(slots), int(n_real * 1.6)), replace=False)
        cands_by_day: Dict[str, list] = {}
        for p in sorted(picks):
            d, t = slots[p]
            side = 1 if rng.random() < long_share else -1
            mins, o, h, lo, c = minute_arrays[d]
            start = int(np.searchsorted(mins, by_day[d][t]["end_min"]))
            oc = outcome(mins, o, h, lo, c, start, side, by_day[d][t]["atr"], *ex[1:])
            if oc is not None:
                cands_by_day.setdefault(d, []).append((by_day[d][t]["end_min"], side, oc))
        rets = []
        for d, cands in cands_by_day.items():
            rets.extend(r for _, r in book(sorted(cands, key=lambda x: x[0])))
        rets = rets[:n_real] if len(rets) > n_real else rets
        means.append(np.mean(rets) * 1e4 if rets else 0.0)
    return float(np.mean(np.asarray(means) < real_mean) * 100)


if __name__ == "__main__":
    main()
