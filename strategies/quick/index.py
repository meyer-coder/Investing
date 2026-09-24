"""Quick intraday trades on the Nasdaq-100 (QQQ, TQQQ or MNQ), flat every close.

    python strategies/quick/index.py

Six years of one-minute Nasdaq-100 bars (Dukascopy CFD, Sep 2020 to Sep 2026,
strategies/mnq/data.py), lined up 09:30-15:59 New York.  Each rule decides on
a bar's close, fills at the next bar's open, may carry a stop checked on each
bar's high and low (the stop price fills; a gap through it fills at the open),
and is flat at the 15:59 close.  Results are per-day returns on the traded
notional, net of a round-trip cost; dollars on $25,000:

* QQQ at L times buying power: 25,000 x L x (index return - 1 bp);
* TQQQ at L times: 25,000 x L x 3 x (index return - 1 bp), the fund's three-times
  daily leverage applied to the day's moves (3 bp a round trip; SQQQ for shorts);
* MNQ: $2 a point a contract, 1.25 points a round trip.

The rules are the published intraday patterns: the noise-area breakout
(Zarattini and Aziz, 2023), the first half hour predicting the last
(Gao, Han, Li and Zhou, 2018), opening-range breakouts with the first bar's
direction (Zarattini, Barbon and Aziz, 2024, on stocks), the opening drive,
gap fades and morning overreactions.  Dev is Sep 2020 to Dec 2023, test Jan
2024 to Sep 2026.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
NY = ZoneInfo("America/New_York")
CACHE = ROOT / "data" / "cache" / "quick"
SPLIT = "2024-01-01"
ACCOUNT = 25_000.0
T = 390


def load() -> dict:
    """{dates, O, H, L, C (days x 390), pc (previous close)}, cached."""
    path = CACHE / "index.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        return {k: z[k] for k in z.files}
    import data
    s = data.sessions("duka")
    dates = sorted(s)
    X = np.full((len(dates), T, 4), np.nan)
    for i, d in enumerate(dates):
        day = s[d]
        y, m, dd = map(int, d.split("-"))
        open_utc = dt.datetime(y, m, dd, 9, 30, tzinfo=NY).astimezone(dt.timezone.utc)
        base = open_utc.hour * 60 + open_utc.minute
        idx = np.array([int(x[11:13]) * 60 + int(x[14:16]) - base for x in day.stamps])
        ok = (idx >= 0) & (idx < T)
        X[i, idx[ok], 0], X[i, idx[ok], 1], X[i, idx[ok], 2], X[i, idx[ok], 3] = day.o[ok], day.h[ok], day.l[ok], day.c[ok]
        for j in range(1, T):                                                # forward-fill a missing minute with the last close
            if np.isnan(X[i, j, 3]):
                X[i, j] = X[i, j - 1, 3]
        if np.isnan(X[i, 0, 3]):
            X[i, 0] = X[i, np.flatnonzero(~np.isnan(X[i, :, 3]))[0], 0]
    pc = np.concatenate([[np.nan], X[:-1, -1, 3]])
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, dates=np.array(dates), O=X[:, :, 0], H=X[:, :, 1], L=X[:, :, 2], C=X[:, :, 3], pc=pc)
    return load()


# ---------------------------------------------------------------- the trade engine

def trade_day(o, h, l, c, entries, stop_fn=None, exit_fn=None, cost=1e-4):
    """One position at a time.  entries(t) -> +1/-1/0 at bar t's close; stop_fn(side, t_in, t) -> stop price
    or None; exit_fn(side, t) -> True to exit at the next open.  Returns (net return, trades)."""
    pos, px_in, t_in, total, n = 0, 0.0, 0, 0.0, 0
    t = 0
    while t < T - 1:
        if pos == 0:
            side = entries(t)
            if side:
                pos, px_in, t_in = side, o[t + 1], t + 1
                n += 1
                t += 1
                continue
            t += 1
            continue
        # in a position during bar t: the stop first
        stop = stop_fn(pos, t_in, t) if stop_fn else None
        if stop is not None and ((pos > 0 and l[t] <= stop) or (pos < 0 and h[t] >= stop)):
            fill = min(o[t], stop) if pos > 0 else max(o[t], stop)
            total += pos * (fill / px_in - 1.0) - cost
            pos = 0
            t += 1
            continue
        if exit_fn and exit_fn(pos, t):
            total += pos * (o[t + 1] / px_in - 1.0) - cost
            pos = 0
            t += 1
            continue
        t += 1
    if pos:
        total += pos * (c[T - 1] / px_in - 1.0) - cost
    return total, n


# ---------------------------------------------------------------- the rules

def noise_area(D: dict, lookback: int = 14, every: int = 30, vwap_stop: bool = True, band_mult: float = 1.0):
    """Zarattini-Aziz: trade breaks of the band the index usually moves within by this minute."""
    O, H, L, C, pc = D["O"], D["H"], D["L"], D["C"], D["pc"]
    move = np.abs(C / O[:, :1] - 1.0)                                          # |move from the open| each minute
    out = np.full(len(O), np.nan)
    ntr = np.zeros(len(O))
    for i in range(lookback + 1, len(O)):
        sig = band_mult * move[i - lookback:i].mean(axis=0)
        o, h, l, c = O[i], H[i], L[i], C[i]
        up = max(o[0], pc[i]) * (1 + sig)
        dn = min(o[0], pc[i]) * (1 - sig)
        typ = (h + l + c) / 3
        vwap = np.cumsum(typ) / np.arange(1, T + 1)
        checks = set(range(every - 1, T - 1, every))

        def entries(t):
            if t not in checks:
                return 0
            return 1 if c[t] > up[t] else (-1 if c[t] < dn[t] else 0)

        def exit_fn(side, t):
            if t not in checks:
                return False
            if side > 0:
                return c[t] < (max(up[t], vwap[t]) if vwap_stop else up[t])
            return c[t] > (min(dn[t], vwap[t]) if vwap_stop else dn[t])

        out[i], ntr[i] = trade_day(o, h, l, c, entries, None, exit_fn)
    return out, ntr


def first_last_half_hour(D: dict, use_12th: bool = False, min_move: float = 0.0):
    """Gao et al.: the return from the previous close to 10:00 sets the side for 15:30-16:00."""
    O, C, pc = D["O"], D["C"], D["pc"]
    r1 = C[:, 29] / pc - 1.0
    r12 = C[:, 359] / C[:, 329] - 1.0
    sig = np.sign(r1) if not use_12th else np.sign(np.sign(r1) + np.sign(r12))
    sig = np.where(np.abs(r1) >= min_move, sig, 0)
    ret = sig * (C[:, T - 1] / O[:, 360] - 1.0) - np.where(sig != 0, 1e-4, 0.0)
    return np.where(np.isnan(pc), np.nan, ret), (sig != 0).astype(float)


def orb(D: dict, minutes: int = 5, with_first_bar: bool = True, stop_atr: Optional[float] = None, last_entry: int = 330):
    """Opening range breakout: the first break of the first `minutes` range after it closes, stop at the other
    side (or a share of the 14-day daily range), out at the close; optionally only in the first bar's direction."""
    O, H, L, C = D["O"], D["H"], D["L"], D["C"]
    rng = (H.max(axis=1) - L.min(axis=1)) / O[:, 0]
    out = np.full(len(O), np.nan)
    ntr = np.zeros(len(O))
    for i in range(15, len(O)):
        o, h, l, c = O[i], H[i], L[i], C[i]
        hi, lo = h[:minutes].max(), l[:minutes].min()
        first = np.sign(c[minutes - 1] - o[0])
        atr = rng[i - 14:i].mean() * o[0]
        state = {"done": False}

        def entries(t):
            if state["done"] or t < minutes or t > last_entry:
                return 0
            side = 1 if c[t] > hi else (-1 if c[t] < lo else 0)
            if side and with_first_bar and side != first:
                return 0
            if side:
                state["done"] = True
            return side

        def stop_fn(side, t_in, t):
            if stop_atr is not None:
                return o[t_in] - side * stop_atr * atr
            return lo if side > 0 else hi

        out[i], ntr[i] = trade_day(o, h, l, c, entries, stop_fn)
    return out, ntr


def opening_drive(D: dict, minutes: int = 30, min_move: float = 0.0, stop_mult: Optional[float] = None):
    """Go with the move from the open to 10:00 (or 09:45), hold to the close; optional stop at the open's price."""
    O, H, L, C = D["O"], D["H"], D["L"], D["C"]
    out = np.full(len(O), np.nan)
    ntr = np.zeros(len(O))
    for i in range(1, len(O)):
        o, h, l, c = O[i], H[i], L[i], C[i]
        mv = c[minutes - 1] / o[0] - 1.0
        side = int(np.sign(mv)) if abs(mv) >= min_move else 0

        def entries(t):
            return side if t == minutes - 1 else 0

        stop_fn = (lambda s, t_in, t: o[0] if stop_mult == 0 else o[t_in] * (1 - s * stop_mult)) if stop_mult is not None else None
        out[i], ntr[i] = trade_day(o, h, l, c, entries, stop_fn)
    return out, ntr


def gap_trade(D: dict, min_gap: float = 0.005, fade: bool = True, until: int = T - 1):
    """Fade (or follow) the overnight gap from the open, out at `until` (bar index) or when the gap has filled."""
    O, H, L, C, pc = D["O"], D["H"], D["L"], D["C"], D["pc"]
    out = np.full(len(O), np.nan)
    ntr = np.zeros(len(O))
    for i in range(1, len(O)):
        o, h, l, c = O[i], H[i], L[i], C[i]
        g = o[0] / pc[i] - 1.0
        if np.isnan(g) or abs(g) < min_gap:
            out[i] = 0.0
            continue
        side = -int(np.sign(g)) if fade else int(np.sign(g))
        px = o[0]
        if fade:
            tgt = pc[i]
            hit = np.flatnonzero((h >= tgt) if side > 0 else (l <= tgt))     # a long waits for the high to reach the old close
            hit = hit[hit <= until]
            px_out = tgt if len(hit) else c[until]
        else:
            px_out = c[until]
        out[i] = side * (px_out / px - 1.0) - 1e-4
        ntr[i] = 1
    return out, ntr


def overreaction(D: dict, at: int = 90, k: float = 2.0, lookback: int = 20, fade: bool = True):
    """At `at` minutes after the open, if the move from the open is beyond k of its usual size at that minute,
    fade (or follow) it to the close."""
    O, C = D["O"], D["C"]
    mv = C[:, at] / O[:, 0] - 1.0
    out = np.full(len(O), np.nan)
    ntr = np.zeros(len(O))
    for i in range(lookback, len(O)):
        s = np.std(mv[i - lookback:i])
        if abs(mv[i]) > k * s:
            side = -np.sign(mv[i]) if fade else np.sign(mv[i])
            out[i] = side * (C[i, T - 1] / O[i, at + 1] - 1.0) - 1e-4
            ntr[i] = 1
        else:
            out[i] = 0.0
    return out, ntr


# ---------------------------------------------------------------- reporting

def summarize(dates, ret, ntr, label=""):
    ok = ~np.isnan(ret)
    ds, r, n = np.array(dates)[ok], ret[ok], ntr[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    years = {}
    for y in sorted({x[:4] for x in ds}):
        m = np.array([x[:4] == y for x in ds])
        years[y] = round(float(r[m].mean() * 1e4), 2)
    tq = 3 * r                                                               # TQQQ: three times the move and 3 bp a round trip
    row = {"dev_bp": round(float(r[dev].mean() * 1e4), 2), "test_bp": round(float(r[test].mean() * 1e4), 2),
           "test_up": round(float((r[test] > 0).mean()), 3), "trades_per_day": round(float(n.mean()), 2),
           "years_bp": years,
           "qqq_4x_test_usd": round(float(r[test].mean() * ACCOUNT * 4), 0),
           "tqqq_4x_test_usd": round(float(tq[test].mean() * ACCOUNT * 4), 0),
           "tqqq_4x_worst_day": round(float(tq.min() * ACCOUNT * 4), 0),
           "sharpe_test": round(float(r[test].mean() / (r[test].std() + 1e-12) * np.sqrt(252)), 2),
           "sharpe_dev": round(float(r[dev].mean() / (r[dev].std() + 1e-12) * np.sqrt(252)), 2)}
    if label:
        print(f"  {label:58s} dev {row['dev_bp']:+6.2f} / test {row['test_bp']:+6.2f} bp a day | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} "
              f"| QQQ 4x ${row['qqq_4x_test_usd']:+5.0f} TQQQ 4x ${row['tqqq_4x_test_usd']:+5.0f} | "
              + " ".join(f"{y[2:]}:{v:+.1f}" for y, v in years.items()), flush=True)
    return row


_D: dict = {}


def _job(item):
    label, fn, a = item
    r, n = globals()[fn](_D, *a)
    return label, r, n


def main() -> int:
    import multiprocessing as mp
    D = load()
    _D.update(D)
    dates = list(D["dates"])
    print(f"{len(dates)} sessions {dates[0]} to {dates[-1]}; bp a day on the traded notional after costs")
    jobs = []
    for lb, every, vw, bm in itertools.product((10, 14, 20), (30, 15), (True, False), (1.0, 1.5)):
        jobs.append((f"noise area lb{lb} every {every}m {'vwap stop' if vw else 'band stop'} x{bm}", "noise_area", (lb, every, vw, bm)))
    for u12, mm in itertools.product((False, True), (0.0, 0.0025, 0.005)):
        jobs.append((f"first half hour -> last{' +12th' if u12 else ''} min {mm:.2%}", "first_last_half_hour", (u12, mm)))
    for mins, wf, sa in itertools.product((5, 15, 30), (True, False), (None, 0.1, 0.25)):
        jobs.append((f"ORB {mins}m {'first-bar side' if wf else 'either side'} stop {sa if sa else 'range'}", "orb", (mins, wf, sa)))
    for mins, mm, sm in itertools.product((15, 30, 60), (0.0, 0.003, 0.006), (None, 0.0)):
        jobs.append((f"opening drive {mins}m min {mm:.1%} {'stop at open' if sm == 0 else 'no stop'}", "opening_drive", (mins, mm, sm)))
    for g, fade in itertools.product((0.003, 0.006, 0.01), (True, False)):
        jobs.append((f"gap {'fade to fill' if fade else 'follow'} >{g:.1%}", "gap_trade", (g, fade)))
    for at, k, fade in itertools.product((30, 60, 120), (1.5, 2.0, 2.5), (True, False)):
        jobs.append((f"{'fade' if fade else 'follow'} the move at +{at}m beyond {k} sd to the close", "overreaction", (at, k, 20, fade)))
    with mp.get_context("fork").Pool(4) as pool:
        out = pool.map(_job, jobs)
    res = {}
    for label, r, n in out:
        res[label] = summarize(dates, r, n, label)
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_bp"], kv[1]["test_bp"]))
    print("\nbest by the weaker of dev and test:")
    for k_, v in ranked[:15]:
        print(f"  {k_:58s} dev {v['dev_bp']:+6.2f} test {v['test_bp']:+6.2f} bp | Sharpe {v['sharpe_dev']:+.2f}/{v['sharpe_test']:+.2f} | "
              f"TQQQ 4x ${v['tqqq_4x_test_usd']:+.0f} a day, worst day ${v['tqqq_4x_worst_day']:+.0f}")
    (ROOT / "strategies" / "quick" / "index.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
