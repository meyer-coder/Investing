"""Three more ideas, tested with the protocol of research/edges.py.

Rules, fixed before any result was seen.  Times are New York time; "NY PM"
is 13:30-16:00.  Fills use one-minute bars; signals use the idea's own bars.
Everything is flat by 15:55 (Topstep closes positions at 16:10).

1. Gold (XAU/USD as MGC), round-number reaction, 15-minute bars, NY PM.
   A round number is a multiple of $10 (version a) or $50 (version b).
   A 15-minute bar that trades up to the first round number above its open
   and closes back below it is a rejection: short at the next bar's open.
   The mirror (down to the first round number below the open, close back
   above) buys.  A bar that does both is skipped.  Signal bars are the ones
   closing 13:45-15:30; the first signal of the day is the only trade.
   Stop one tick ($0.10) beyond the signal bar's extreme; target 1R or 2R;
   otherwise out at 15:55.  Four versions: $10 or $50 x 1R or 2R.

2. Crude (WTI, LIGHT.CMD/USD as MCL), z-score reversion, 15-minute bars,
   all sessions.  A trading day runs 18:00-15:55 (Topstep's hours); the
   z-score is (close - mean of the last N closes) / their standard
   deviation, over that day's bars only, so the contract-roll gaps at the
   18:00 reopen never enter it.  z <= -T buys at the next bar's open, z >= T
   sells short; one position at a time.  Out at the next bar's open after a
   close back across the mean, at a stop 2 standard deviations (at the
   signal) beyond the entry, or at 15:55.  Signals on bars closing up to
   15:30.  Four versions: N = 20 or 40 bars x T = 2.0 or 2.5.  Days missing
   over 10% of their minutes, or with a one-minute jump over 2% (broken
   data), are skipped.

3. Euro (EUR/USD as M6E), EMA crossover, 3-minute bars, NY PM.  EMAs of the
   3-minute closes, run over all hours.  A cross is the fast EMA moving from
   one side of the slow to the other at a bar close, on bars closing
   13:33-15:30; the trade is in the cross's direction at the next bar's
   open.  Version "reverse": each later cross reverses the position.
   Version "first": only the day's first cross is traded, out at the next
   opposite cross.  Out at 15:55 regardless; no stop.  Four versions: 9/21
   or 20/50 x reverse or first.

Sessions (gold and euro) must have at least 90% of their minutes.

Costs: the micro contract's $1.22 commission plus a tick of slippage each
way, as in research/edges.py.  Also shown for the full-size contract (GC,
CL, 6E) at an assumed $4 commission and a tick each way, which is cheaper
as a share of the price.

Protocol: search on data up to 2019 (100+ trades, a positive mean after
micro costs, t >= 2); confirm on 2020-2022 (positive, and the long/short
calls beat 90% of 2,000 random sign flips); one final look at 2023-2026.

    python research/three_ideas.py
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edges as E  # noqa: E402
from duka import load_rows  # noqa: E402
from judas import day_label, local_minutes  # noqa: E402

PM0, FLAT, LAST_SIGNAL = 13 * 60 + 30, 15 * 60 + 55, 15 * 60 + 30
COVER = 0.90
FULL = {"XAU/USD": (100.0, 0.1), "LIGHT.CMD/USD": (1_000.0, 0.01), "EUR/USD": (125_000.0, 0.00005)}


def full_cost(m: E.Market) -> float:
    mult, tick = FULL[m.key]
    return (4.0 + 2 * tick * mult) / (m.price * mult)


def bars(a: np.ndarray, L: np.ndarray, k: int) -> Dict[str, np.ndarray]:
    """k-minute bars on the New York clock; ``row`` is each bar's first one-minute row."""
    key = L // k
    cut = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    last = np.r_[cut[1:], len(a)] - 1
    return {"start": key[cut] * k, "row": cut, "o": a[cut, 1], "h": np.maximum.reduceat(a[:, 2], cut),
            "l": np.minimum.reduceat(a[:, 3], cut), "c": a[last, 4]}


def hold(a, L, e: int, side: int, stop: Optional[float], target: Optional[float],
         x_end: int) -> Optional[Tuple[int, float, float]]:
    """In at the open of one-minute row e; out at the stop, the target, or the
    close of the last minute before New York minute ``x_end``.  A minute that
    touches both counts as the stop.  Returns (exit row, gross, worst)."""
    O, H, Lo, C = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
    x1 = int(np.searchsorted(L, x_end))
    if x1 <= e:
        return None
    entry, n = O[e], x1 - e
    seg_h, seg_l, seg_o = H[e:x1], Lo[e:x1], O[e:x1]
    s_at = t_at = n
    if stop is not None:
        hit = (seg_h >= stop) if side < 0 else (seg_l <= stop)
        s_at = int(np.argmax(hit)) if hit.any() else n
    if target is not None:
        hit = (seg_l <= target) if side < 0 else (seg_h >= target)
        t_at = int(np.argmax(hit)) if hit.any() else n
    if s_at < n and s_at <= t_at:
        m, px = s_at, stop
        if m > 0:
            px = max(seg_o[m], stop) if side < 0 else min(seg_o[m], stop)
    elif t_at < n:
        m, px = t_at, target
        if m > 0:
            px = min(seg_o[m], target) if side < 0 else max(seg_o[m], target)
    else:
        m, px = n - 1, C[x1 - 1]
    worst_px = seg_h[:m + 1].max() if side < 0 else seg_l[:m + 1].min()
    gross = side * (px / entry - 1)
    return e + m, gross, min(0.0, side * (worst_px / entry - 1), gross)


def covered(L: np.ndarray, t0: int, t1: int) -> bool:
    i0, i1 = np.searchsorted(L, [t0, t1])
    return (i1 - i0) >= COVER * (t1 - t0)


# ------------------------------------------------------------- 1. gold

def day_slices(day_of: np.ndarray):
    """(day, first, end) for each run of equal values in a sorted array."""
    cut = np.flatnonzero(np.r_[True, day_of[1:] != day_of[:-1]])
    ends = np.r_[cut[1:], len(day_of)]
    return zip(day_of[cut], cut, ends)


def round_numbers(a, L, grid: float, r_mult: float) -> Tuple[List[E.Trade], int]:
    b = bars(a, L, 15)
    tick = 0.1
    out, days = [], 0
    for day, s0, s1 in day_slices(b["start"] // 1440):
        if not covered(L, day * 1440 + PM0, day * 1440 + 16 * 60):
            continue
        days += 1
        for i in range(s0, s1):
            mod = b["start"][i] % 1440
            if mod < PM0 or mod + 15 > LAST_SIGNAL:
                continue
            o, h, lo, c = b["o"][i], b["h"][i], b["l"][i], b["c"][i]
            up = (np.floor(o / grid) + 1) * grid                 # first round number above the open
            dn = (np.ceil(o / grid) - 1) * grid                  # first round number below the open
            short = h >= up and c < up
            long_ = lo <= dn and c > dn
            if short == long_:
                continue
            side = -1 if short else 1
            e = int(np.searchsorted(L, b["start"][i] + 15))
            if e >= len(L) or L[e] // 1440 != day or L[e] % 1440 > LAST_SIGNAL:
                break
            entry = a[e, 1]
            stop = h + tick if side < 0 else lo - tick
            risk = side * (entry - stop)
            if risk <= 0:
                break
            res = hold(a, L, e, side, stop, entry + side * r_mult * risk, day * 1440 + FLAT)
            if res:
                x, g, w = res
                out.append(E.Trade(day_label(day), side, int(L[e] % 1440), int(L[x] % 1440), g, w))
            break
    return out, days


# ------------------------------------------------------------ 2. crude

def zscore(a, L, n: int, thr: float) -> Tuple[List[E.Trade], int]:
    b = bars(a, L, 15)
    jump = np.r_[0.0, np.abs(a[1:, 1] / a[:-1, 4] - 1)]
    out, days = [], 0
    for td, s0, s1 in day_slices((b["start"] - 18 * 60) // 1440):   # a trading day starts at 18:00
        t0, t1 = td * 1440 + 18 * 60, (td + 1) * 1440 + FLAT
        last_close = (td + 1) * 1440 + LAST_SIGNAL
        i0, i1 = np.searchsorted(L, [t0, t1])
        if (i1 - i0) < COVER * (t1 - t0) or jump[i0 + 1:i1].max(initial=0.0) > 0.02:
            continue
        days += 1
        starts, rows, c = b["start"][s0:s1], b["row"][s0:s1], b["c"][s0:s1]
        keep = starts < t1
        starts, rows, c = starts[keep], rows[keep], c[keep]
        k = n - 1
        while k < len(c) - 1 and starts[k] + 15 <= last_close:
            w = c[k - n + 1:k + 1]
            mu, sd = w.mean(), w.std()
            if sd == 0 or abs(c[k] - mu) < thr * sd:
                k += 1
                continue
            side = -1 if c[k] > mu else 1
            e = int(rows[k + 1])
            stop = a[e, 1] - side * 2 * sd
            x_end = t1
            for j in range(k + 1, len(c)):                       # first later close back across the mean
                if side * (c[j] - c[j - n + 1:j + 1].mean()) >= 0:
                    x_end = min(t1, starts[j] + 15)
                    break
            res = hold(a, L, e, side, stop, None, x_end)
            if res is None:
                break
            x, g, wst = res
            out.append(E.Trade(day_label(td + 1), side, int(L[e] % 1440), int(L[x] % 1440), g, wst))
            k = max(int(np.searchsorted(starts + 15, L[x], side="right")), k + 1)
    return out, days


# ------------------------------------------------------------- 3. euro

def ema(x: np.ndarray, n: int) -> np.ndarray:
    alpha, out = 2.0 / (n + 1), np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + alpha * (x[i] - out[i - 1])
    return out


def ema_cross(a, L, fast: int, slow: int, reverse: bool) -> Tuple[List[E.Trade], int]:
    b = bars(a, L, 3)
    sign = np.sign(ema(b["c"], fast) - ema(b["c"], slow))
    out, days = [], 0
    for day, s0, s1 in day_slices(b["start"] // 1440):
        if not covered(L, day * 1440 + PM0, day * 1440 + 16 * 60):
            continue
        days += 1
        flat_at = day * 1440 + FLAT
        # crosses at the close of bars closing 13:33-15:30, entered at the next bar's open
        entries = []
        for i in range(max(s0, 1), s1 - 1):
            close = b["start"][i] % 1440 + 3
            if PM0 < close <= LAST_SIGNAL and sign[i] != 0 and sign[i - 1] != 0 and sign[i] != sign[i - 1]:
                entries.append((i, int(b["row"][i + 1]), int(sign[i])))
        if not entries:
            continue
        if reverse:
            legs = [(e, side, flat_at if nxt is None else int(L[nxt[1]]))
                    for (_, e, side), nxt in zip(entries, entries[1:] + [None])]
        else:
            i0, e, side = entries[0]
            x_end = flat_at
            for i in range(i0 + 1, s1):                           # the next opposite cross, any time
                if b["start"][i] + 3 >= flat_at:
                    break
                if sign[i] == -side and sign[i - 1] == side:
                    x_end = b["start"][i] + 3
                    break
            legs = [(e, side, x_end)]
        for e, side, x_end in legs:
            res = hold(a, L, e, side, None, None, x_end)
            if res:
                x, g, w = res
                out.append(E.Trade(day_label(day), side, int(L[e] % 1440), int(L[x] % 1440), g, w))
    return out, days


IDEAS: List[Tuple[str, str, List[Tuple[str, Callable]]]] = [
    ("XAU/USD", "Gold round-number reaction, 15m, NY PM", [
        ("$10 levels, 1R", lambda a, L: round_numbers(a, L, 10.0, 1.0)),
        ("$10 levels, 2R", lambda a, L: round_numbers(a, L, 10.0, 2.0)),
        ("$50 levels, 1R", lambda a, L: round_numbers(a, L, 50.0, 1.0)),
        ("$50 levels, 2R", lambda a, L: round_numbers(a, L, 50.0, 2.0)),
    ]),
    ("LIGHT.CMD/USD", "Crude z-score reversion, 15m, all sessions", [
        ("20 bars, z 2.0", lambda a, L: zscore(a, L, 20, 2.0)),
        ("20 bars, z 2.5", lambda a, L: zscore(a, L, 20, 2.5)),
        ("40 bars, z 2.0", lambda a, L: zscore(a, L, 40, 2.0)),
        ("40 bars, z 2.5", lambda a, L: zscore(a, L, 40, 2.5)),
    ]),
    ("EUR/USD", "Euro EMA crossover, 3m, NY PM", [
        ("9/21, reverse", lambda a, L: ema_cross(a, L, 9, 21, True)),
        ("9/21, first cross", lambda a, L: ema_cross(a, L, 9, 21, False)),
        ("20/50, reverse", lambda a, L: ema_cross(a, L, 20, 50, True)),
        ("20/50, first cross", lambda a, L: ema_cross(a, L, 20, 50, False)),
    ]),
]
PERIODS = (("search", "0000", E.SEARCH_END), ("confirm", "2020-01-01", E.CONFIRM_END),
           ("final", "2023-01-01", "9999"))


def main() -> None:
    n_all = n_pass = n_conf = 0
    for key, title, versions in IDEAS:
        m = E.BY_KEY[key]
        a = load_rows(key)
        L = local_minutes(a)
        cf = full_cost(m)
        print(f"\n######## {title}: {m.contract} (1 contract = ${m.notional:,.0f}); costs {m.cost * 1e4:.2f} bp "
              f"a round trip on the micro, {cf * 1e4:.2f} bp on the full-size contract")
        for name, fn in versions:
            tr, _ = fn(a, L)
            n_all += 1
            sc = {p: E.score(tr, m.cost, lo, hi) for p, lo, hi in PERIODS}
            passed = sc["search"]["n"] >= 100 and sc["search"]["mean_bp"] > 0 and sc["search"]["t"] >= 2.0
            confirmed = passed and sc["confirm"]["mean_bp"] > 0 and sc["confirm"]["flip_pct"] >= 90
            n_pass += passed
            n_conf += confirmed
            print(f"== {name}: {len(tr)} trades")
            for p, lo, hi in PERIODS:
                x = sc[p]
                g = np.array([t.gross for t in tr if lo <= t.day <= hi])
                days = len({t.day for t in tr if lo <= t.day <= hi})
                win = np.mean(g - m.cost > 0) * 100 if len(g) else 0.0
                full = (g.mean() - cf) * 1e4 if len(g) else 0.0
                usd = x["mean_bp"] / 1e4 * m.notional * x["n"]
                print(f"   {p:<8} n={x['n']:>5} win {win:3.0f}% gross {g.mean() * 1e4 if len(g) else 0:+6.2f} bp | "
                      f"net {x['mean_bp']:+6.2f} bp t={x['t']:+5.1f} flips {x['flip_pct']:3.0f}% | "
                      f"full-size net {full:+6.2f} bp | ${usd:+8,.0f} in all on 1 micro, {days} days with a trade")
            print("   " + ("CONFIRMED" if confirmed else "passed the search, failed to confirm" if passed
                           else "failed the search"))
    print(f"\n{n_all} versions: {n_pass} passed the search (about {0.023 * n_all:.1f} would by luck), "
          f"{n_conf} confirmed on 2020-2022.")


if __name__ == "__main__":
    main()
