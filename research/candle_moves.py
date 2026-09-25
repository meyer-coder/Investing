"""Do big moves in Nasdaq futures keep going, or snap back?

Three questions, answered on real NQ futures bars (MNQ trades at the same
price; only the dollars per point differ):

1. How big is a normal 5-minute candle, and at what time of day do the
   biggest drops happen?
2. When price has moved several "normal candles" in 15 minutes, what happens
   over the next 15 / 30 / 60 minutes?  If it usually bounces, fade the move
   (buy selloffs, short rips).  If it usually continues, go with it.
3. When the day has already moved a large share of its normal daily range,
   does it keep going into the close or come back?

Everything is measured with past-only information: a candle is called "big"
by comparing it with the same time of day over *earlier* sessions, and every
simulated entry fills at the next bar's open (or at the touched level for the
day-level study), never at a price that was not yet known.

    python research/candle_moves.py            # uses cached bars if present
    python research/candle_moves.py --refresh  # re-download from Yahoo
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")
CACHE_DIR = os.environ.get("EVOTRADER_CACHE", os.path.join("data", "cache"))
_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
_UA = "Mozilla/5.0 (compatible; evotrader/0.1)"

POINT_VALUE = 2.0   # MNQ pays $2 per index point
COST_POINTS = 1.1   # ~$1.22 commission + 1 tick slippage each side, per round turn

RTH_OPEN = 9 * 60 + 30      # 09:30 New York
RTH_CLOSE = 16 * 60         # 16:00 New York


# --------------------------------------------------------------------------- data
# Bars come from shortbot.data, which drops the week of each quarterly expiry
# (Yahoo's continuous NQ=F mixes two contracts then), sessions with broken
# price jumps, today's unfinished session and off-grid live-quote rows.

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shortbot.data import Session, load_sessions  # noqa: E402


# ---------------------------------------------------------------- statistics

@dataclass
class Outcome:
    label: str
    n: int
    mean_pts: float
    median_pts: float
    win_rate: float
    t_stat: float
    net_usd: float          # mean per MNQ trade after costs

    def row(self) -> str:
        return (f"{self.label:<34} n={self.n:>4}  avg {self.mean_pts:+7.1f} pts  "
                f"median {self.median_pts:+7.1f}  win* {self.win_rate * 100:5.1f}%  "
                f"t {self.t_stat:+5.2f}  net ${self.net_usd:+7.2f}/MNQ")


def summarise(label: str, pts: List[float]) -> Outcome:
    a = np.asarray(pts, dtype=float)
    if a.size == 0:
        return Outcome(label, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    sd = float(np.std(a, ddof=1)) if a.size > 1 else 0.0
    t = float(np.mean(a) / (sd / math.sqrt(a.size))) if sd > 0 else 0.0
    return Outcome(label, int(a.size), float(np.mean(a)), float(np.median(a)),
                   float(np.mean(a - COST_POINTS > 0)), t,
                   (float(np.mean(a)) - COST_POINTS) * POINT_VALUE)


# ------------------------------------------------- 1. normal candle size by time

def expected_ranges(days: List[Session], lookback: int = 10, width: int = 2,
                    step: int = 5) -> List[np.ndarray]:
    """For each bar, the average candle range at that time of day over the
    previous ``lookback`` sessions (slots within +-``width`` bars of ``step``
    minutes pooled).  NaN until enough history exists.  Uses only earlier
    sessions."""
    out = []
    for i, s in enumerate(days):
        exp = np.full(len(s.minute), np.nan)
        prior = days[max(0, i - lookback):i]
        if len(prior) >= lookback:
            pool: Dict[int, List[float]] = {}
            for p in prior:
                for m, r in zip(p.minute, p.high - p.low):
                    pool.setdefault(int(m), []).append(float(r))
            for j, m in enumerate(s.minute):
                vals = [v for k in range(-width, width + 1)
                        for v in pool.get(int(m) + step * k, [])]
                if vals:
                    exp[j] = float(np.mean(vals))
        out.append(exp)
    return out


def candle_profile(days: List[Session]) -> List[Dict]:
    """Average 5-minute candle range and big-drop frequency per half hour."""
    buckets: Dict[int, Dict[str, List[float]]] = {}
    all_moves = np.concatenate([s.close - s.open for s in days])
    big_drop = float(np.percentile(all_moves, 2))       # the worst 2% of candles
    for s in days:
        for m, o, h, lo, c in zip(s.minute, s.open, s.high, s.low, s.close):
            b = buckets.setdefault(int(m) // 30 * 30, {"range": [], "drop": []})
            b["range"].append(h - lo)
            b["drop"].append(1.0 if c - o <= big_drop else 0.0)
    total_drops = sum(sum(b["drop"]) for b in buckets.values()) or 1.0
    rows = []
    for m in sorted(buckets):
        b = buckets[m]
        rows.append({"time": f"{m // 60:02d}:{m % 60:02d}",
                     "avg_range_pts": float(np.mean(b["range"])),
                     "big_drop_share": float(sum(b["drop"])) / total_drops,
                     "bars": len(b["range"])})
    return rows


# ------------------------------------------------ 2. 15-minute stretch events

def stretch_events(days: List[Session], exp: List[np.ndarray], *, look: int, k: float,
                   hold: int, direction: int, window: Optional[Tuple[int, int]] = None,
                   bracket: Optional[float] = None) -> List[Tuple[str, float]]:
    """Fade trades after a ``look``-bar move of at least ``k`` normal candles.

    direction=-1 finds selloffs (and buys them), +1 finds rips (and shorts
    them).  Entry at the next bar's open, exit at the close ``hold`` bars
    later or at the session's last bar.  With ``bracket`` set, a stop and a
    target are also placed ``bracket`` normal candles away from the entry;
    when one bar touches both, the stop is assumed to fill first.  Returns
    (date, fade points) pairs; a negative mean means the move tended to
    *continue*.
    """
    trades = []
    for s, e in zip(days, exp):
        n = len(s.minute)
        t = look - 1                       # the first full window ends on bar look-1
        while t < n - 1:
            ref = e[t]
            if s.minute[t] < RTH_OPEN or (window and not (window[0] <= s.minute[t] < window[1])):
                t += 1                     # no signal from a bar that began before 09:30
                continue
            if math.isnan(ref) or ref <= 0:
                t += 1
                continue
            move = s.close[t] - s.open[t - look + 1]
            if direction * move >= k * ref:
                entry = s.open[t + 1]
                exit_i = min(t + hold, n - 1)
                fade = (entry - s.close[exit_i]) * direction
                if bracket:
                    dist = bracket * ref
                    for j in range(t + 1, exit_i + 1):
                        adverse = (s.high[j] - entry) if direction > 0 else (entry - s.low[j])
                        favour = (entry - s.low[j]) if direction > 0 else (s.high[j] - entry)
                        if adverse >= dist:
                            fade, exit_i = -dist, j
                            break
                        if favour >= dist:
                            fade, exit_i = dist, j
                            break
                trades.append((s.date, float(fade)))
                t = exit_i              # one position at a time; the exit bar can signal again
                continue
            t += 1
    return trades


# ------------------------------------------ 3. day moved X of its normal range

def trend_labels(days: List[Session], lookback: int = 20) -> Dict[str, bool]:
    """date -> True when the previous close was above the average of the
    prior ``lookback`` closes (known before the session starts).  Sessions
    without enough history are left out."""
    closes = [float(s.close[-1]) for s in days]
    return {days[i].date: closes[i - 1] > float(np.mean(closes[i - 1 - lookback:i - 1]))
            for i in range(lookback + 1, len(days))}


def day_range_events(days: List[Session], frac: float, direction: int,
                     lookback: int = 14) -> List[Tuple[str, float]]:
    """Once price is ``frac`` x average daily range away from the day's open,
    fade it with a limit order at that level and hold to the session close.
    Returns (date, fade points)."""
    ranges = [float(s.high.max() - s.low.min()) for s in days]
    out = []
    for i in range(lookback, len(days)):
        s = days[i]
        adr = float(np.mean(ranges[i - lookback:i]))
        level = s.open[0] + direction * frac * adr
        for j in range(len(s.minute)):
            hit = s.high[j] >= level if direction > 0 else s.low[j] <= level
            if hit:
                # A bar can open beyond the level (a gap); a resting limit order
                # then fills at that open, which is better than the level.
                fill = s.open[j] if (direction > 0 and s.open[j] > level) or \
                    (direction < 0 and s.open[j] < level) else level
                out.append((s.date, float((fill - s.close[-1]) * direction)))
                break
    return out


# ----------------------------------------------------------------------- main

def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh", action="store_true", help="re-download bars")
    ap.add_argument("--json", default="", help="also write results to this JSON file")
    args = ap.parse_args(argv)

    result: Dict = {"symbol": "NQ=F", "point_value": POINT_VALUE,
                    "cost_points": COST_POINTS}

    # ---- 5-minute bars, regular trading hours
    dropped: list = []
    days5 = load_sessions("yahoo", refresh=args.refresh, dropped=dropped)
    result["five_min"] = {"sessions": len(days5), "first": days5[0].date, "last": days5[-1].date}
    print(f"\n5-minute bars: {len(days5)} regular sessions, {days5[0].date} .. {days5[-1].date}")

    prof = candle_profile(days5)
    result["profile"] = prof
    print("\n1) Normal 5-minute candle size, and where the biggest drops happen")
    print("   time    avg range      $/MNQ   share of the worst-2% drop candles")
    for r in prof:
        bar = "#" * int(round(r["big_drop_share"] * 100))
        print(f"   {r['time']}  {r['avg_range_pts']:7.1f} pts  ${r['avg_range_pts'] * POINT_VALUE:7.0f}"
              f"   {r['big_drop_share'] * 100:5.1f}%  {bar}")

    exp = expected_ranges(days5)
    dates = sorted({d.date for d in days5[10:]})
    mid = dates[len(dates) // 2]
    print(f"   (dropped {len(dropped)} sessions so far: contract-switch weeks, unfinished or broken days)")
    print("\n2) After a 15-minute move of k normal candles, FADE it (buy drops / short rips)")
    print("   win* = share of trades that made money after costs")
    print("   positive = the move snapped back, negative = it kept going; bracket = stop and")
    print("   target each 2 normal candles away (rows with fewer than 20 trades hidden)")
    stretch = []
    windows = {"all day": None, "first hour 09:30-10:30": (570, 630),
               "after 10:30": (630, 960)}
    for wname, win in windows.items():
        for k in (1.5, 2.0, 3.0):
            for hold, hold_name, br in ((3, "15m", None), (6, "30m", None), (12, "60m", None),
                                        (12, "60m 1:1 bracket", 2.0)):
                for direction, dname in ((-1, "buy selloff"), (+1, "short rip")):
                    tr = stretch_events(days5, exp, look=3, k=k, hold=hold,
                                        direction=direction, window=win, bracket=br)
                    pts = [p for _, p in tr]
                    o = summarise(f"{dname} k={k:g} {hold_name}", pts)
                    first = summarise("", [p for d, p in tr if d < mid])
                    second = summarise("", [p for d, p in tr if d >= mid])
                    stretch.append({"window": wname, "k": k, "hold": hold_name, "side": dname,
                                    **o.__dict__, "first_half_mean": first.mean_pts,
                                    "second_half_mean": second.mean_pts,
                                    "first_half_n": first.n, "second_half_n": second.n})
        print(f"\n   [{wname}]")
        for s in stretch:
            if s["window"] == wname and s["n"] >= 20:
                o = Outcome(**{k: s[k] for k in Outcome.__dataclass_fields__})
                print("   " + o.row() + f"  halves {s['first_half_mean']:+.1f} / {s['second_half_mean']:+.1f}")
    result["stretch"] = stretch

    # ---- hourly bars, two years: day-level stretch
    days60 = load_sessions("yahoo-hourly", refresh=args.refresh, dropped=dropped)
    result["dropped"] = dropped
    result["hourly"] = {"sessions": len(days60), "first": days60[0].date, "last": days60[-1].date}
    adr_pts = float(np.mean([s.high.max() - s.low.min() for s in days60[-20:]]))
    print(f"\n3) Hourly bars: {len(days60)} sessions {days60[0].date} .. {days60[-1].date}"
          f"   (last 20 days' average 9:00-16:00 range: {adr_pts:.0f} pts = ${adr_pts * POINT_VALUE:,.0f}/MNQ)")
    print("   Price is X of a normal day's range away from the 9:00 open: FADE it to the 16:00 close")
    daylevel = []
    half60 = days60[len(days60) // 2].date
    for frac in (0.5, 0.75, 1.0):
        for direction, dname in ((-1, "buy selloff"), (+1, "short rip")):
            tr = day_range_events(days60, frac, direction)
            o = summarise(f"{dname} at {frac:g} x day range", [p for _, p in tr])
            first = summarise("", [p for d, p in tr if d < half60])
            second = summarise("", [p for d, p in tr if d >= half60])
            daylevel.append({"frac": frac, "side": dname, **o.__dict__,
                             "first_half_mean": first.mean_pts, "second_half_mean": second.mean_pts})
            print("   " + o.row() + f"  halves {first.mean_pts:+.1f} / {second.mean_pts:+.1f}")
    result["day_level"] = daylevel
    result["recent_day_range_pts"] = adr_pts

    # ---- the same stretch idea on hourly candles over two years, split by
    # year and by trend, to see whether section 2 survives outside one summer
    exp60 = expected_ranges(days60, lookback=20, width=0, step=60)
    trend = trend_labels(days60)
    print("\n4) Two-year check on hourly candles: one hourly candle of k normal hourly candles, FADE it")
    print("   uptrend = previous close above its 20-day average (known before the open)")
    robust = []
    for k in (1.5, 2.0):
        for hold in (1, 2, 7):
            hold_name = "to close" if hold == 7 else f"{hold}h"
            for direction, dname in ((-1, "buy selloff"), (+1, "short rip")):
                tr = stretch_events(days60, exp60, look=1, k=k, hold=hold, direction=direction)
                groups = {"all": tr,
                          "2024": [x for x in tr if x[0] < "2025"],
                          "2025": [x for x in tr if "2025" <= x[0] < "2026"],
                          "2026": [x for x in tr if x[0] >= "2026"],
                          "uptrend": [x for x in tr if trend.get(x[0]) is True],
                          "downtrend": [x for x in tr if trend.get(x[0]) is False]}
                row = {"k": k, "hold": hold_name, "side": dname}
                for g, xs in groups.items():
                    o = summarise(g, [p for _, p in xs])
                    row[g] = {"n": o.n, "mean_pts": o.mean_pts, "win_rate": o.win_rate,
                              "t_stat": o.t_stat, "net_usd": o.net_usd}
                robust.append(row)
                parts = "  ".join(f"{g} {row[g]['mean_pts']:+6.1f} (n{row[g]['n']})"
                                  for g in groups if g != "all")
                a = row["all"]
                print(f"   {dname:<11} k={k:g} {hold_name:<8} all {a['mean_pts']:+6.1f} pts "
                      f"n={a['n']:>3} win* {a['win_rate'] * 100:4.1f}% t {a['t_stat']:+5.2f} | {parts}")
    result["hourly_robustness"] = robust

    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=1)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
