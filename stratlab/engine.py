"""Run a strategy card on minute data.

Signals come from the card's candles and are known at a candle's close.
Orders and exits are worked on one-minute bars:

* market entry fills at the open of the minute after the signal candle;
  limit and stop entries fill on the first later minute that trades through
  the price, before the cancel time, the session's end and the flat time;
* an order that is already marketable when placed (the first minute opens
  past its price) fills at that open;
* otherwise fills are never better than the order's price: a limit entry, a
  target or a partial fills at its price even if the minute opens past it
  (minute data has gaps, and a real resting order mostly fills at its
  price); a stop -- entry or exit -- fills at the open when the minute gaps
  past it (worse);
* in every minute the stop is checked first, so a minute that touches both
  the stop and the target counts as the stop; after a limit or stop fill the
  rest of that minute is unknown, so only the stop is checked in it;
* a partial exit fills at its price, then the rest runs on;
* trailing stops move only after a minute is over, from its best price;
* out at the close of the last minute before the time stop or the flat time;
* one position at a time; a new signal counts only once the last trade (or
  unfilled order) is done;
* only usable days trade (data.from_rows); a session that starts before
  09:30 also needs that night's quotes to be live;
* no stop is closer than MIN_STOP_TICKS ticks of the real contract (a stop
  worked out as closer -- e.g. from a near-zero ATR on a quiet overnight
  candle -- is widened to it).

Costs: the market's CME contract commission plus a tick of slippage each way
(research/edges.py), charged on every trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from . import filters as flt
from . import indicators as ind
from . import signals as sig
from .data import DAY_START, Bars, Minutes, bars, market, minutes, parse_clock, trading_day_label
from .spec import SESSIONS, normalize


VERSION = 7                  # bump when a fix changes results; the log re-runs older results
MIN_STOP_TICKS = 4


@dataclass
class Trade:
    day: str
    side: int
    entry_time: int       # local minute of the fill
    exit_time: int        # local minute of the exit
    entry: float
    risk: float           # distance to the first stop, in price
    gross: float          # result as a share of the entry price, before costs
    r_gross: float        # result in R (multiples of the first risk), before costs
    r_cost: float         # costs in R
    r_net: float
    mae_r: float          # worst open loss in R (<= 0)
    why: str              # stop, trail, target, time, flat


def _window(session: str):
    a, b, _ = SESSIONS[session]
    lo, hi = parse_clock(a), parse_clock(b)
    return lo, (hi if hi > lo else hi + 1440)


def walk(M: Minutes, e: int, e_px: float, side: int, stop: float, target: Optional[float], x_end: int,
         fill_inside: bool, risk: float, trailing: dict, partial: dict, atr_val: float):
    """Manage one position from row e.  Returns (exit row, realized price move x fraction, worst price, why)."""
    x1 = int(np.searchsorted(M.L, x_end))
    if x1 <= e:
        return None
    O, H, Lw, C = M.o, M.h, M.l, M.c
    s = side
    if trailing["type"] == "none" and partial["type"] == "none":
        seg_h, seg_l, seg_o = H[e:x1], Lw[e:x1], O[e:x1]
        n = x1 - e
        hs = (seg_l <= stop) if s > 0 else (seg_h >= stop)
        s_at = int(np.argmax(hs)) if hs.any() else n
        t_at = n
        if target is not None:
            ht = (seg_h >= target) if s > 0 else (seg_l <= target)
            if fill_inside:
                ht[0] = False
            t_at = int(np.argmax(ht)) if ht.any() else n
        if s_at < n and s_at <= t_at:
            m, why = s_at, "stop"
            px = stop if m == 0 else (min(seg_o[m], stop) if s > 0 else max(seg_o[m], stop))
        elif t_at < n:
            m, why, px = t_at, "target", target
        else:
            m, why, px = n - 1, "time", C[x1 - 1]
        worst = seg_l[:m + 1].min() if s > 0 else seg_h[:m + 1].max()
        return e + m, s * (px - e_px), worst, why
    cur = stop
    best, worst = e_px, e_px
    left, realized = 1.0, 0.0
    p_on = partial["type"] == "take"
    p_lvl = e_px + s * partial.get("at_r", 0.0) * risk
    be_lvl = e_px + s * trailing.get("at_r", 0.0) * risk
    tr_from = e_px + s * trailing.get("after_r", 0.0) * risk
    tr_dist = trailing.get("mult", 0.0) * atr_val
    why = "time"
    r = e
    for r in range(e, x1):
        o, h, lo, c = O[r], H[r], Lw[r], C[r]
        first = r == e
        worst = min(worst, lo) if s > 0 else max(worst, h)
        if (s > 0 and lo <= cur) or (s < 0 and h >= cur):
            px = cur if first else (min(o, cur) if s > 0 else max(o, cur))
            realized += left * s * (px - e_px)
            left, why = 0.0, ("stop" if cur == stop else "trail")
            break
        if first and fill_inside:
            best = max(best, c) if s > 0 else min(best, c)
            continue
        if p_on and ((s > 0 and h >= p_lvl) or (s < 0 and lo <= p_lvl)):
            realized += partial["frac"] * s * (p_lvl - e_px)
            left -= partial["frac"]
            p_on = False
        if target is not None and ((s > 0 and h >= target) or (s < 0 and lo <= target)):
            realized += left * s * (target - e_px)
            left, why = 0.0, "target"
            break
        best = max(best, h) if s > 0 else min(best, lo)
        if trailing["type"] == "breakeven" and s * (best - be_lvl) >= 0:
            cur = max(cur, e_px) if s > 0 else min(cur, e_px)
        elif trailing["type"] == "atr" and s * (best - tr_from) >= 0:
            cur = max(cur, best - tr_dist) if s > 0 else min(cur, best + tr_dist)
    else:
        realized += left * s * (C[x1 - 1] - e_px)
        r = x1 - 1
    return r, realized, worst, why


def run(spec: dict, B: Optional[Bars] = None, M: Optional[Minutes] = None) -> List[Trade]:
    s = normalize(spec)
    m = market(s["market"])
    M = M if M is not None else minutes(s["market"])
    B = B if B is not None else bars(s["market"], s["tf"])
    tf = s["tf"]
    side, level = sig.compute(B, s["family"], s["settings"])
    n = len(side)
    ok_l, ok_s = np.ones(n, bool), np.ones(n, bool)
    for f in s["filters"]:
        a, b = flt.compute(B, f)
        ok_l &= np.nan_to_num(a).astype(bool)
        ok_s &= np.nan_to_num(b).astype(bool)
    if s["direction"] == "long":
        ok_s[:] = False
    elif s["direction"] == "short":
        ok_l[:] = False
    w0, w1 = _window(s["session"])
    close = B.tmin + tf
    in_win = (close > w0) & (close <= w1)
    days = np.unique(B.tday)
    overnight = w0 < 930                      # the session starts before 09:30: the night's quotes must be live
    night = M.night_ok or {}
    good = {int(d) for d in days if M.valid.get(int(d), False) and (not overnight or night.get(int(d), True))}
    valid = np.isin(B.tday, list(good))
    fire = np.where(side > 0, ok_l, np.where(side < 0, ok_s, False)) & in_win & valid
    cand = np.flatnonzero(fire & (side != 0))

    atrs: Dict[int, np.ndarray] = {}

    def atr_n(k: int) -> np.ndarray:
        if k not in atrs:
            atrs[k] = ind.atr(B, k)
        return atrs[k]

    tick = m.tick / m.price                       # one tick as a share of the price
    flat_t = parse_clock(s["flat"])
    e_spec, st, tg, tr, pa = s["entry"], s["stop"], s["target"], s["trailing"], s["partial"]
    busy = -1
    per_day: Dict[int, int] = {}
    out: List[Trade] = []
    for i in cand:
        sgn = int(side[i])
        t_close = int(B.start[i]) + tf
        td = int(B.tday[i])
        if t_close < busy or per_day.get(td, 0) >= s["max_trades_day"]:
            continue
        day0 = td * 1440 + DAY_START
        flat_at = day0 + flat_t
        r0 = int(B.row1[i])
        if r0 >= len(M.L) or M.L[r0] >= flat_at:
            continue
        # ---- entry
        fill_inside = e_spec["type"] != "market"
        if e_spec["type"] == "market":
            e, e_px = r0, float(M.o[r0])
        else:
            deadline = min(t_close + e_spec["cancel_bars"] * tf, day0 + w1, flat_at)
            rd = int(np.searchsorted(M.L, deadline))
            hi, lo = float(B.h[i]), float(B.l[i])
            if e_spec["type"] == "limit_pullback":
                lvl = hi - e_spec["frac"] * (hi - lo) if sgn > 0 else lo + e_spec["frac"] * (hi - lo)
                hit = (M.l[r0:rd] < lvl) if sgn > 0 else (M.h[r0:rd] > lvl)
            else:
                lvl = hi * (1 + e_spec["ticks"] * tick) if sgn > 0 else lo * (1 - e_spec["ticks"] * tick)
                hit = (M.h[r0:rd] >= lvl) if sgn > 0 else (M.l[r0:rd] <= lvl)
            if not hit.any():
                busy = deadline
                continue
            e = r0 + int(np.argmax(hit))
            o = float(M.o[e])
            through = (o < lvl if sgn > 0 else o > lvl) if e_spec["type"] == "limit_pullback" \
                else (o > lvl if sgn > 0 else o < lvl)
            if e == r0 and through:
                # the price was already past the order when it was placed: it fills at once, at the open
                e_px, fill_inside = o, False
            elif e_spec["type"] == "limit_pullback":
                e_px = lvl
            else:
                e_px = max(o, lvl) if sgn > 0 else min(o, lvl)
        # ---- stop, target
        if st["type"] == "atr":
            a = atr_n(st["n"])[i]
            if not np.isfinite(a) or a <= 0:
                continue
            stop = e_px - sgn * st["mult"] * a
        elif st["type"] == "signal_bar":
            stop = float(B.l[i]) * (1 - st["ticks"] * tick) if sgn > 0 else float(B.h[i]) * (1 + st["ticks"] * tick)
        else:
            stop = e_px * (1 - sgn * st["pct"] / 100)
        risk = sgn * (e_px - stop)
        if risk <= 0:
            continue
        floor = MIN_STOP_TICKS * tick * e_px
        if risk < floor:
            risk = floor
            stop = e_px - sgn * risk
        if tg["type"] == "r":
            target = e_px + sgn * tg["mult"] * risk
        elif tg["type"] == "atr":
            a = atr_n(tg["n"])[i]
            target = e_px + sgn * tg["mult"] * a if np.isfinite(a) else None
        elif tg["type"] == "level":
            target = None if level is None else float(level[i])
            if target is None or not np.isfinite(target) or sgn * (target - e_px) <= 0:
                continue
        else:
            target = None
        x_end = flat_at
        if s["time_stop_bars"]:
            x_end = min(x_end, int(M.L[e]) + s["time_stop_bars"] * tf)
        atr_val = float(atr_n(tr.get("n", 14))[i]) if tr["type"] == "atr" else 0.0
        res = walk(M, e, e_px, sgn, stop, target, x_end, fill_inside, risk, tr, pa, atr_val)
        if res is None:
            continue
        x, realized, worst_px, why = res
        if why == "time" and x_end == flat_at:
            why = "flat"
        r_gross = realized / risk
        r_cost = m.cost * e_px / risk
        out.append(Trade(trading_day_label(td), sgn, int(M.L[e]), int(M.L[x]), e_px, risk, realized / e_px,
                         r_gross, r_cost, r_gross - r_cost, min(0.0, sgn * (worst_px - e_px) / risk), why))
        per_day[td] = per_day.get(td, 0) + 1
        busy = int(M.L[x]) + 1
    return out
