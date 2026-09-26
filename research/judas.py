"""The Judas swing fade on the Nasdaq-100: one-minute bars, all three sessions.

A Judas swing is a false move at the start of a session: price runs past the
previous session's high or low, trips the stops there, then turns back.  The
fade trades the turn.

Rules, fixed before any result was seen.  Each session fades a sweep of the
session before it (New York time):

    session    entry window   range it fades                         flat by
    Asia       20:00-00:00    that day's New York session 09:30-16:00  02:00
    London     02:00-05:00    the Asian session before it 20:00-00:00  09:25
    New York   09:30-11:00    that morning's London session 02:00-05:00 15:55

1. Sweep: the first one-minute bar in the entry window whose high is above
   the range's high (or whose low is below its low).  Only a session's first
   sweep counts; a bar that sweeps both sides is skipped.
2. Reclaim: a one-minute close back inside the range, on the sweep bar or
   within the 15 minutes after it.  None: no trade that session.
3. Entry: the other way (short after a sweep of the high), at the next
   minute's open, which must still be inside the entry window.
4. Stop: one tick (0.25) beyond the furthest price between the sweep and the
   reclaim.  If the entry is already past it, no trade.
5. Target, two versions: the other side of the range, or twice the stop
   distance (2R).  A minute that touches both the stop and the target counts
   as the stop.  Neither by the flat time: out at the last minute's close.
6. At most one trade a session, so at most three a day.

A session is skipped when its range or its entry window is missing more than
10% of its minutes (Dukascopy has no Asian hours for most of 2015-2017).

Costs: one MNQ, the $1.22 commission plus one tick of slippage each way
(0.36 bp at today's price), as in research/edges.py; also shown with two
ticks each way, because the overnight sessions are thinner.

Eight versions: each session alone and all three together, for each target.

Protocol, the same as research/edges.py: search on data up to 2019 (100+
trades, a positive mean after costs, t >= 2); confirm on 2020-2022
(positive, and the long/short calls beat 90% of 2,000 random sign flips);
one final look at 2023-2026.

    python research/judas.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta, timezone, datetime
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edges as E  # noqa: E402
from duka import NASDAQ, load_rows  # noqa: E402
from shortbot.data import NY  # noqa: E402

TICK = 0.25
RECLAIM = 15
COVER = 0.90
MNQ = E.BY_KEY[NASDAQ]
COST_1 = MNQ.cost                                                    # 1 tick each way
COST_2 = (MNQ.commission + 4 * TICK * MNQ.multiplier) / MNQ.notional  # 2 ticks each way

# name, entry window, range window (with its day offset), flat time (with its day offset)
SESSIONS = [
    ("Asia", (20 * 60, 24 * 60), (9 * 60 + 30, 16 * 60), 0, 2 * 60, 1),
    ("London", (2 * 60, 5 * 60), (20 * 60, 24 * 60), -1, 9 * 60 + 25, 0),
    ("New York", (9 * 60 + 30, 11 * 60), (2 * 60, 5 * 60), 0, 15 * 60 + 55, 0),
]


def local_minutes(a: np.ndarray) -> np.ndarray:
    """New York wall-clock minutes since 1970-01-01 for each row."""
    t = a[:, 0].astype(np.int64)
    hours = np.unique(t // 3600)
    off = {h: int(datetime.fromtimestamp(h * 3600, timezone.utc).astimezone(NY).utcoffset().total_seconds())
           for h in hours}
    offs = np.array([off[h] for h in t // 3600])
    return (t + offs) // 60


def day_label(day: int) -> str:
    return (date(1970, 1, 1) + timedelta(days=int(day))).isoformat()


def trades_for(a: np.ndarray, L: np.ndarray, session, target: str) -> Tuple[List[E.Trade], List[float]]:
    """All trades of one session and target, and each trade's stop distance as a share of the price."""
    name, (ws, we), (rs, re_), ref_off, flat, flat_off = session
    O, H, Lo, C = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    out, stops = [], []
    for day in range(int(L[0] // 1440), int(L[-1] // 1440) + 1):
        w0, w1 = day * 1440 + ws, day * 1440 + we
        r0, r1 = (day + ref_off) * 1440 + rs, (day + ref_off) * 1440 + re_
        f = (day + flat_off) * 1440 + flat
        i0, i1 = np.searchsorted(L, [w0, w1])
        j0, j1 = np.searchsorted(L, [r0, r1])
        if (i1 - i0) < COVER * (we - ws) or (j1 - j0) < COVER * (re_ - rs):
            continue
        hi, lo = H[j0:j1].max(), Lo[j0:j1].min()
        up, dn = H[i0:i1] > hi, Lo[i0:i1] < lo
        any_ = up | dn
        if not any_.any():
            continue
        j = i0 + int(np.argmax(any_))
        if up[j - i0] and dn[j - i0]:
            continue
        side = -1 if up[j - i0] else 1
        k = j
        while k < i1 and L[k] <= L[j] + RECLAIM and not (lo < C[k] < hi):
            k += 1
        if k >= i1 or L[k] > L[j] + RECLAIM:
            continue
        e = k + 1
        if e >= len(L) or L[e] >= w1:
            continue
        entry = O[e]
        stop = H[j:k + 1].max() + TICK if side < 0 else Lo[j:k + 1].min() - TICK
        risk = side * (entry - stop)
        if risk <= 0:
            continue
        tgt = (lo if side < 0 else hi) if target == "range" else entry + side * 2 * risk
        if side * (tgt - entry) <= 0:
            continue
        x1 = int(np.searchsorted(L, f))
        if x1 <= e:
            continue
        seg_h, seg_l, seg_o = H[e:x1], Lo[e:x1], O[e:x1]
        hit_s = (seg_h >= stop) if side < 0 else (seg_l <= stop)
        hit_t = (seg_l <= tgt) if side < 0 else (seg_h >= tgt)
        s_at = int(np.argmax(hit_s)) if hit_s.any() else len(seg_h)
        t_at = int(np.argmax(hit_t)) if hit_t.any() else len(seg_h)
        if s_at <= t_at and s_at < len(seg_h):
            m, px = s_at, stop
            if m > 0:                                    # a gap through the stop fills at the open
                px = max(seg_o[m], stop) if side < 0 else min(seg_o[m], stop)
        elif t_at < len(seg_h):
            m, px = t_at, tgt
            if m > 0:
                px = min(seg_o[m], tgt) if side < 0 else max(seg_o[m], tgt)
        else:
            m, px = len(seg_h) - 1, C[x1 - 1]
        worst_px = seg_h[:m + 1].max() if side < 0 else seg_l[:m + 1].min()
        gross = side * (px / entry - 1)
        worst = min(0.0, side * (worst_px / entry - 1), gross)
        out.append(E.Trade(day_label(day), side, int(L[e] % 1440), int(L[e + m] % 1440), gross, worst))
        stops.append(risk / entry)
    return out, stops


def trading_days(L: np.ndarray, lo: str, hi: str) -> int:
    """Days with a New York session in the period (for dollars a day)."""
    days = np.unique(L[(L % 1440 >= 9 * 60 + 30) & (L % 1440 < 16 * 60)] // 1440)
    labels = [day_label(d) for d in days]
    return sum(lo <= s <= hi for s in labels)


def main() -> None:
    a = load_rows(NASDAQ)
    L = local_minutes(a)
    print(f"Nasdaq-100 one-minute CFD, {day_label(L[0] // 1440)} to {day_label(L[-1] // 1440)}; "
          f"1 MNQ = ${MNQ.notional:,.0f}; costs {COST_1 * 1e4:.2f} bp a round trip "
          f"({COST_2 * 1e4:.2f} bp with two ticks of slippage each way)\n")
    periods = (("search", "0000", E.SEARCH_END), ("confirm", "2020-01-01", E.CONFIRM_END),
               ("final", "2023-01-01", "9999"))
    ndays = {p: trading_days(L, lo, hi) for p, lo, hi in periods}
    cache: Dict[Tuple[str, str], Tuple[List[E.Trade], List[float]]] = {}
    for target in ("range", "2R"):
        for s in SESSIONS:
            cache[(s[0], target)] = trades_for(a, L, s, target)
    results = []
    for target in ("range", "2R"):
        label_t = "other side of the range" if target == "range" else "2R"
        for name in ("Asia", "London", "New York", "all sessions"):
            if name == "all sessions":
                tr = [t for s in SESSIONS for t in cache[(s[0], target)][0]]
                st = [x for s in SESSIONS for x in cache[(s[0], target)][1]]
            else:
                tr, st = cache[(name, target)]
            sc = {p: E.score(tr, COST_1, lo, hi) for p, lo, hi in periods}
            sc2 = {p: E.score(tr, COST_2, lo, hi) for p, lo, hi in periods}
            passed = sc["search"]["n"] >= 100 and sc["search"]["mean_bp"] > 0 and sc["search"]["t"] >= 2.0
            confirmed = passed and sc["confirm"]["mean_bp"] > 0 and sc["confirm"]["flip_pct"] >= 90
            results.append((name, target, passed, confirmed))
            print(f"== {name}, target {label_t}: {len(tr)} trades, median stop {np.median(st) * 1e4:.1f} bp "
                  f"({np.median(st) * MNQ.price:.1f} points, ${np.median(st) * MNQ.notional:.0f} on 1 MNQ at today's price)")
            for p, lo, hi in periods:
                x = sc[p]
                g = np.array([t.gross for t in tr if lo <= t.day <= hi])
                win = np.mean(g - COST_1 > 0) * 100 if len(g) else 0.0
                usd = x["mean_bp"] / 1e4 * MNQ.notional * x["n"] / max(1, ndays[p])
                usd2 = sc2[p]["mean_bp"] / 1e4 * MNQ.notional * x["n"] / max(1, ndays[p])
                print(f"   {p:<8} n={x['n']:>5} win {win:3.0f}% {x['mean_bp']:+6.2f} bp a trade t={x['t']:+5.1f} "
                      f"flips {x['flip_pct']:3.0f}% | ${usd:+6.1f} a day at 1 MNQ (two ticks: ${usd2:+6.1f})")
            print("   " + ("CONFIRMED" if confirmed else "passed the search, failed to confirm" if passed
                           else "failed the search"))
    n_pass = sum(r[2] for r in results)
    n_conf = sum(r[3] for r in results)
    print(f"\n{len(results)} versions: {n_pass} passed the search (about {0.023 * len(results):.1f} would by luck), "
          f"{n_conf} confirmed on 2020-2022.")


if __name__ == "__main__":
    main()
