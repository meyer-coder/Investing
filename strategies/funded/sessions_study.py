"""Micro trading at the market open and the market close.

    python strategies/funded/sessions_study.py [--out sessions_study.json]

Three questions, all priced at one MNQ at today's index level:

1. Where does the Nasdaq-100 earn its return: overnight (the 16:00 close to
   the 09:30 open) or during the stock market's session (09:30 to 16:00)?
   QQQ daily bars since 2005; QLD and TQQQ for the leveraged funds.
2. Trades at the 09:30 open, decided with the overnight gap known and flat by
   the 16:00 close (FundedNext closes everything at 15:10 Chicago time): buy
   or short the open after a gap of a given size, with and without a trend
   filter and a resting stop.  The session is QQQ's own open, high, low and
   close, applied to the MNQ contract.
3. Trades into the close: the last hour (15:00 to 16:00 New York) in the
   direction of the day so far, from NQ hourly bars (TradingView serves them
   from January 2025 without a login, so this one is a thin sample).

Every same-day trade is replayed as fresh FundedNext Legacy 25K challenges
and funded accounts (evotrader/prop.py), one started every week.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from evotrader.prop import LEGACY_25K, MICROS, TradePath, challenge_stats, funded_stats  # noqa: E402

NY = ZoneInfo("America/New_York")
WINDOWS = {"older": ("2010-01-01", "2018-12-31"), "train": ("2019-01-01", "2026-03-20"),
           "held_out": ("2026-03-23", "2026-09-22")}
MNQ = MICROS["MNQ"]
NQ_NOW = 31_028.5                     # NQ settlement 2026-09-22
NOTIONAL = MNQ.point_value * NQ_NOW
COST_ENTRY = MNQ.commission + MNQ.point_value * MNQ.tick          # $0.75 + one tick
COST_EXIT = MNQ.commission + MNQ.point_value * MNQ.tick
COST_STOP = MNQ.commission + 2 * MNQ.point_value * MNQ.tick


def read_daily(symbol: str):
    rows = list(csv.DictReader(open(ROOT / "data" / "cache" / f"{symbol}.csv")))
    dates = [r["date"] for r in rows]
    cols = {k: np.array([float(r[k]) for r in rows]) for k in ("open", "high", "low", "close")}
    return dates, cols


# --------------------------------------------------------------------- 1. split

def session_split(symbol: str) -> dict:
    dates, c = read_daily(symbol)
    on = np.log(c["open"][1:] / c["close"][:-1])
    rth = np.log(c["close"][1:] / c["open"][1:])
    years = np.array([d[:4] for d in dates[1:]])
    out = {"from": dates[0], "to": dates[-1], "by_year": {}}
    for y in sorted(set(years)):
        m = years == y
        out["by_year"][y] = {"overnight": round(float(np.expm1(on[m].sum())), 4),
                             "regular_hours": round(float(np.expm1(rth[m].sum())), 4)}
    for label, a, b in (("2005-2018", "2005", "2018"), ("2019-2026", "2019", "2026"),
                        ("all", "0000", "9999")):
        m = (years >= a) & (years <= b)
        out[label] = {"overnight": round(float(np.expm1(on[m].sum())), 3),
                      "regular_hours": round(float(np.expm1(rth[m].sum())), 3),
                      "overnight_per_day_bp": round(float(on[m].mean() * 1e4), 2),
                      "regular_hours_per_day_bp": round(float(rth[m].mean() * 1e4), 2),
                      "overnight_up_days": round(float((on[m] > 0).mean()), 3),
                      "regular_hours_up_days": round(float((rth[m] > 0).mean()), 3)}
    return out


# ------------------------------------------------------------------ 2. the open

def same_day_path(bar: int, ret: float, adverse: float, stopped: bool) -> TradePath:
    """One same-day MNQ trade: ``ret`` its return, ``adverse`` its worst move (<= 0)."""
    exit_cost = COST_STOP if stopped else COST_EXIT
    realized = NOTIONAL * ret - COST_ENTRY - exit_cost
    worst = min(realized, NOTIONAL * adverse - COST_ENTRY)
    return TradePath(bar, bar, [bar], [realized], [worst], realized, stopped)


def open_trades(dates, c, side: int, gap_min: float, gap_max: float, stop: float,
                trend: str) -> List[TradePath]:
    """Buy (side 1) or short (side -1) the 09:30 open when the overnight gap is
    in [gap_min, gap_max); flat at the close or at a resting stop."""
    close, opn, high, low = c["close"], c["open"], c["high"], c["low"]
    sma200 = np.convolve(close, np.ones(200) / 200, mode="full")[: len(close)]
    paths = []
    for t in range(201, len(dates)):
        gap = opn[t] / close[t - 1] - 1
        if not gap_min <= gap < gap_max:
            continue
        if trend == "up" and not close[t - 1] > sma200[t - 1]:
            continue
        if trend == "down" and not close[t - 1] < sma200[t - 1]:
            continue
        if side > 0:
            adverse = low[t] / opn[t] - 1
            ret = close[t] / opn[t] - 1
        else:
            adverse = opn[t] / high[t] - 1
            ret = opn[t] / close[t] - 1
        stopped = stop > 0 and adverse <= -stop
        if stopped:
            ret, adverse = -stop, -stop
        paths.append(same_day_path(t, ret, adverse, stopped))
    return paths


def stats(paths: Sequence[TradePath], dates: List[str], a: str, b: str) -> dict:
    idx = [i for i, d in enumerate(dates) if a <= d <= b]
    if not idx:
        return {}
    lo, hi = idx[0], idx[-1]
    pnl = np.array([p.realized for p in paths if lo <= p.entry_bar <= hi])
    worst = np.array([p.worst[0] for p in paths if lo <= p.entry_bar <= hi])
    starts = idx[::5]
    ch = challenge_stats(paths, starts, LEGACY_25K)
    fu = funded_stats(paths, starts)
    cum = np.cumsum(pnl) if len(pnl) else np.zeros(1)
    return {
        "sessions": len(idx), "trades": int(len(pnl)),
        "win": round(float((pnl > 0).mean()), 3) if len(pnl) else 0.0,
        "usd_per_trade": round(float(pnl.mean()), 1) if len(pnl) else 0.0,
        "usd_per_session": round(float(pnl.sum() / len(idx)), 2),
        "worst_day": round(float(pnl.min()), 0) if len(pnl) else 0.0,
        "worst_intraday": round(float(worst.min()), 0) if len(worst) else 0.0,
        "max_drawdown": round(float(np.min(cum - np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:])), 0),
        "pass": round(ch.pass_rate, 3), "breach": round(ch.breach_rate, 3),
        "funded_breach_6m": round(fu.breach_126, 3),
    }


def open_grid() -> List[dict]:
    dates, c = read_daily("QQQ")
    rows = []
    grid = []
    for side in (1, -1):
        grid.append((side, "any", -1.0, 1.0))
        for x in (0.0025, 0.005, 0.0075, 0.01, 0.015):
            grid.append((side, f"gap down {x:.2%}+", -1.0, -x))
            grid.append((side, f"gap up {x:.2%}+", x, 1.0))
    for side, label, g0, g1 in grid:
        for trend in ("any", "up", "down"):
            for stop in (0.0, 0.004, 0.006, 0.01):
                paths = open_trades(dates, c, side, g0, g1, stop, trend)
                rows.append({"side": "long" if side > 0 else "short", "gap": label, "trend": trend,
                             "stop": stop, "stop_usd": round(stop * NOTIONAL, 0) if stop else None,
                             "windows": {w: stats(paths, dates, a, b) for w, (a, b) in WINDOWS.items()}})
    return rows


# ----------------------------------------------------------------- 3. the close

def hourly_nq() -> Tuple[List[datetime], Dict[str, np.ndarray]]:
    z = np.load(ROOT / "data" / "cache" / "tv" / "CME_MINI_NQ1___60.npz", allow_pickle=True)
    ts = [datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(NY)
          for s in z["dates"]]
    return ts, {k: np.asarray(z[k], dtype=float) for k in ("open", "high", "low", "close")}


def close_study(min_move: Sequence[float] = (0.0, 0.005, 0.01, 0.015), stop: float = 0.0) -> dict:
    """At 15:00 New York, trade the last hour in the direction of the session so far
    (from the 18:00 Globex open, so a contract roll never sits inside the measure)."""
    ts, h = hourly_nq()
    sessions: Dict[str, dict] = {}
    for i, t in enumerate(ts):
        day = (t.date() if t.hour < 18 else (t.date().fromordinal(t.date().toordinal() + 1)))
        key = day.isoformat()
        s = sessions.setdefault(key, {})
        if t.hour == 18:
            s["open"] = h["open"][i]
        if t.hour == 14:
            s["at_15"] = h["close"][i]                   # the 14:00-15:00 bar closes at 15:00
        if t.hour == 15:
            s["last"] = (h["open"][i], h["high"][i], h["low"][i], h["close"][i])
    out = {}
    days = sorted(k for k, s in sessions.items() if {"open", "at_15", "last"} <= s.keys())
    for m in min_move:
        pnl, worst = [], []
        for k in days:
            s = sessions[k]
            move = s["at_15"] / s["open"] - 1
            if abs(move) < m or move == 0:
                continue
            side = 1 if move > 0 else -1
            entry = s["at_15"]
            _, hi, lo, cl = s["last"]
            ret = side * (cl / entry - 1)
            adverse = (lo / entry - 1) if side > 0 else (entry / hi - 1)
            stopped = stop > 0 and adverse <= -stop
            if stopped:
                ret, adverse = -stop, -stop
            cost = COST_ENTRY + (COST_STOP if stopped else COST_EXIT)
            pnl.append(NOTIONAL * ret - cost)
            worst.append(min(pnl[-1], NOTIONAL * adverse - COST_ENTRY))
        pnl_a = np.array(pnl)
        out[f"move {m:.1%}+"] = {
            "days": len(days), "trades": len(pnl), "from": days[0], "to": days[-1],
            "win": round(float((pnl_a > 0).mean()), 3) if len(pnl) else 0.0,
            "usd_per_trade": round(float(pnl_a.mean()), 1) if len(pnl) else 0.0,
            "t_stat": round(float(pnl_a.mean() / (pnl_a.std(ddof=1) / np.sqrt(len(pnl_a)))), 2)
            if len(pnl) > 2 else 0.0,
            "worst_trade": round(float(min(worst)), 0) if worst else 0.0,
            "usd_total": round(float(pnl_a.sum()), 0)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "profitable-strategies" / "funded" / "reports"
                                         / "sessions_study.json"))
    args = ap.parse_args(argv)
    result = {
        "mnq_notional": round(NOTIONAL, 0),
        "split": {s: session_split(s) for s in ("QQQ", "QLD", "TQQQ")},
        "open": open_grid(),
        "close": {"no stop": close_study(), "stop 0.3%": close_study(stop=0.003)},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
