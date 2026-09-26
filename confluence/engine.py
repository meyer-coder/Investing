"""The backtest engine: signals on timeframe bars, fills on 1-minute bars.

Decisions are made on a bar's close.  From there everything — the entry
order, the stop, the target, the trailing stop, the session exit — is walked
through the underlying 1-minute bars, so a 60-minute strategy knows whether
its stop or its target was touched first inside the hour.  When both fall in
the same minute the stop is assumed to have filled first.

Fill rules
  market   next bar's first 1-minute open
  stop     1 tick through the signal bar's extreme; gaps fill at the open
  limit    signal bar midpoint; gaps fill at the open (better price)
  stop-out at the stop, or the open if the minute gapped through it
  target   at the target, or the open if the minute gapped through it
  session  at the open of the first minute at/after the session exit; if the
           data jumps straight into the next trading day (early close,
           missing minutes) at the entry day's last close — never across a gap

Costs are charged per round trip as ``cost_rt / risk`` in R, where risk is
the entry-to-stop distance.  Each trade also records its maximum adverse
excursion (MAE, in R, <= 0): the worst price reached before the exit, which
the prop-account simulation needs because firms check the max loss on open
P&L.  Stops are floored at 0.3 ATR so a razor-thin
"signal bar" stop cannot produce a tiny risk and an absurd R multiple.
"""
from __future__ import annotations

import numpy as np
from numba import njit

ENTRY_CODE = {"market": 0, "stop": 1, "limit": 2}
STOP_CODE = {"ATR 1.0": (0, 1.0), "ATR 1.5": (0, 1.5), "swing": (1, 0.0), "signal bar": (2, 0.0)}
TARGET_CODE = {"1R": (1.0, 0), "1.5R": (1.5, 0), "2R": (2.0, 0), "3R": (3.0, 0),
               "trail": (0.0, 1), "session": (0.0, 0)}
REASONS = ["stop", "target", "trail", "time"]
MIN_RISK_ATR = 0.3


@njit(cache=True)
def run(sig_l, sig_s,
        tf_h, tf_l, tf_hi, tf_tdm_close, tf_day, atr, swing_lo, swing_hi,
        m_t, m_o, m_h, m_l, m_c, m_tdm, m_day, m_bar,
        entry_type, stop_type, stop_k, target_r, trail,
        win_start, win_end, exit_tdm, cost_rt, tick, start_bar, max_per_day, cap):
    n = sig_l.size
    nm = m_t.size
    e_min = np.empty(cap, np.int64)
    x_min = np.empty(cap, np.int64)
    e_day = np.empty(cap, np.int32)
    dirs = np.empty(cap, np.int8)
    gross = np.empty(cap, np.float64)
    cost = np.empty(cap, np.float64)
    reason = np.empty(cap, np.int8)
    mae = np.empty(cap, np.float64)
    nt = 0
    cur_day = -1
    day_count = 0
    i = start_bar
    while i < n - 1 and nt < cap:
        L = sig_l[i]
        S = sig_s[i]
        if L == S:                      # nothing, or a conflict
            i += 1
            continue
        tc = tf_tdm_close[i]
        if tc < win_start or tc > win_end:
            i += 1
            continue
        d = tf_day[i]
        if d == cur_day and day_count >= max_per_day:
            i += 1
            continue
        a = atr[i]
        if not (a > 0):
            i += 1
            continue
        dirn = 1 if L else -1
        j0 = tf_hi[i]
        if j0 >= nm:
            break
        # ---------------------------------------------------------- entry
        fill = -1
        entry = 0.0
        if entry_type == 0:
            if m_day[j0] == d and m_tdm[j0] < exit_tdm:
                fill = j0
                entry = m_o[j0]
            nxt = i + 1
        else:
            if entry_type == 1:
                px = tf_h[i] + tick if dirn > 0 else tf_l[i] - tick
            else:
                px = 0.5 * (tf_h[i] + tf_l[i])
            last_bar = i + 3
            if last_bar > n - 1:
                last_bar = n - 1
            jend = tf_hi[last_bar]
            for j in range(j0, jend):
                if m_day[j] != d or m_tdm[j] >= exit_tdm:
                    break
                if entry_type == 1:
                    if dirn > 0 and m_h[j] >= px:
                        fill = j
                        entry = m_o[j] if m_o[j] > px else px
                        break
                    if dirn < 0 and m_l[j] <= px:
                        fill = j
                        entry = m_o[j] if m_o[j] < px else px
                        break
                else:
                    if dirn > 0 and m_l[j] <= px:
                        fill = j
                        entry = m_o[j] if m_o[j] < px else px
                        break
                    if dirn < 0 and m_h[j] >= px:
                        fill = j
                        entry = m_o[j] if m_o[j] > px else px
                        break
            nxt = last_bar
            if nxt <= i:
                nxt = i + 1
        if fill < 0:
            i = nxt
            continue
        # ---------------------------------------------------------- stop / target
        if stop_type == 0:
            stop = entry - dirn * stop_k * a
        elif stop_type == 1:
            stop = swing_lo[i] - 0.1 * a if dirn > 0 else swing_hi[i] + 0.1 * a
        else:
            stop = tf_l[i] - 0.1 * a if dirn > 0 else tf_h[i] + 0.1 * a
        risk = (entry - stop) * dirn
        if not (risk >= MIN_RISK_ATR * a):
            risk = MIN_RISK_ATR * a
            stop = entry - dirn * risk
        tgt = entry + dirn * target_r * risk if target_r > 0 else np.nan
        cur_stop = stop
        best = entry
        worst = entry
        trailing = False
        why = 3
        k = fill
        xp = m_c[nm - 1]
        while k < nm:
            if m_day[k] != d:
                # The data skipped past the session exit into another trading day
                # (early close, holiday, missing minutes).  Flat at the entry day's
                # last price: an intraday strategy never carries the overnight gap.
                k -= 1
                xp = m_c[k]
                why = 3
                break
            if m_tdm[k] >= exit_tdm:
                xp = m_o[k]
                why = 3
                if (xp - worst) * dirn < 0:
                    worst = xp
                break
            same = k == fill and entry_type != 0      # price path before the fill is unknown
            if dirn > 0:
                if m_l[k] <= cur_stop:
                    xp = cur_stop if (same or m_o[k] > cur_stop) else m_o[k]
                    why = 2 if trailing else 0
                    if xp < worst:
                        worst = xp
                    break
                if m_l[k] < worst:
                    worst = m_l[k]
                if target_r > 0 and not same and m_h[k] >= tgt:
                    xp = tgt if m_o[k] < tgt else m_o[k]
                    why = 1
                    break
                if m_h[k] > best:
                    best = m_h[k]
            else:
                if m_h[k] >= cur_stop:
                    xp = cur_stop if (same or m_o[k] < cur_stop) else m_o[k]
                    why = 2 if trailing else 0
                    if xp > worst:
                        worst = xp
                    break
                if m_h[k] > worst:
                    worst = m_h[k]
                if target_r > 0 and not same and m_l[k] <= tgt:
                    xp = tgt if m_o[k] > tgt else m_o[k]
                    why = 1
                    break
                if m_l[k] < best:
                    best = m_l[k]
            if trail == 1:
                b = m_bar[k]
                if k == tf_hi[b] - 1 and (best - entry) * dirn >= risk and atr[b] > 0:
                    ns = best - dirn * 2.0 * atr[b]
                    if (ns - cur_stop) * dirn > 0:
                        cur_stop = ns
                        trailing = True
            k += 1
        if k >= nm:
            k = nm - 1
        e_min[nt] = m_t[fill]
        x_min[nt] = m_t[k]
        e_day[nt] = d
        dirs[nt] = dirn
        gross[nt] = (xp - entry) * dirn / risk
        cost[nt] = cost_rt / risk
        reason[nt] = why
        mae[nt] = min((worst - entry) * dirn / risk, 0.0)
        nt += 1
        if d != cur_day:
            cur_day = d
            day_count = 0
        day_count += 1
        b = m_bar[k]
        i = b if b > i else i + 1
    return (e_min[:nt], x_min[:nt], e_day[:nt], dirs[:nt], gross[:nt], cost[:nt], reason[:nt], mae[:nt])
