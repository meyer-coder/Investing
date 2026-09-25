"""Bar-by-bar backtest of the short strategy, then a Topstep Combine on top.

Fills are deliberately unflattering:

* entries are market sells at the next bar's open, one tick worse;
* stops fill one tick worse than the stop, or at the open if a bar gaps
  through it;
* targets are limit buys that fill only if price trades a tick *through*;
* when one bar touches both the stop and the target, the stop is assumed
  to have come first.

Each trade records its worst open loss (MAE), which is what Topstep's
real-time loss limits react to.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from .config import AccountRules, BotConfig, RiskParams
from .data import Session
from .strategy import DayState, Entry, ShortStrategy


@dataclass
class Trade:
    date: str
    setup: str
    entry_minute: int
    exit_minute: int
    entry: float
    exit: float
    contracts: int
    stop: float
    target: float
    pnl_usd: float           # after commission
    mae_usd: float           # worst open loss while in the trade (<= 0), after commission
    exit_reason: str
    reason: str

    @property
    def points(self) -> float:
        return self.entry - self.exit


def size_trade(e: Entry, r: RiskParams) -> int:
    """Contracts so that the stop risks about ``risk_per_trade_usd``; 0 = skip."""
    one_lot = e.stop_pts * r.point_value + r.commission_rt
    if one_lot > r.max_stop_risk_usd:
        return 0
    return int(max(1, min(r.max_contracts, math.floor(r.risk_per_trade_usd / one_lot))))


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def run_session(s: Session, strat: ShortStrategy, prof, r: RiskParams) -> List[Trade]:
    """All trades the bot would have taken in one session."""
    p = strat.p
    slip = r.slippage_ticks * r.tick_size
    day = DayState()
    trades: List[Trade] = []
    pos: Optional[dict] = None
    flat_at = strat.flatten_minute(s.date)

    for i in range(len(s)):
        m = int(s.minute[i])
        o, h, lo, c = (float(s.open[i]), float(s.high[i]), float(s.low[i]), float(s.close[i]))

        if pos is not None and i >= pos["i"]:
            exit_px, why = None, ""
            if m >= flat_at:
                exit_px, why = o + slip, "flatten"
            elif i > pos["i"] and o >= pos["stop"]:
                exit_px, why = o + slip, "stop (gap)"
            elif h >= pos["stop"]:
                exit_px, why = pos["stop"] + slip, "stop"
            elif lo <= pos["target"] - r.tick_size:
                exit_px, why = pos["target"], "target"
            elif m + s.bar_minutes - pos["minute"] >= p.max_hold_minutes:
                exit_px, why = c + slip, "time"
            elif i == len(s) - 1:
                exit_px, why = c + slip, "session end"
            # Worst price seen while short.  Exits at the open or at the stop
            # end the trade before the rest of the bar; otherwise assume the
            # bar's high came before its low.
            bar_worst = exit_px if why in ("flatten", "stop (gap)", "stop") else h
            worst = max(pos["worst"], bar_worst)
            pos["worst"] = worst
            if exit_px is not None:
                n = pos["n"]
                pnl = (pos["entry"] - exit_px) * r.point_value * n - r.commission_rt * n
                mae = min(0.0, (pos["entry"] - worst) * r.point_value * n) - r.commission_rt * n
                exit_min = m if why in ("flatten", "stop (gap)") else m + s.bar_minutes
                trades.append(Trade(s.date, pos["setup"], pos["minute"], exit_min, pos["entry"],
                                    exit_px, n, pos["stop"], pos["target"], round(pnl, 2),
                                    round(min(mae, pnl), 2), why, pos["reason"]))
                day.record_exit(pnl, exit_min)
                if day.pnl_usd <= -r.daily_loss_stop_usd or day.pnl_usd >= r.daily_profit_stop_usd:
                    day.done = True
                pos = None

        if pos is None and i + 1 < len(s):
            e = strat.decide(s, i, day, prof)
            if e is not None:
                n = size_trade(e, r)
                if n > 0:
                    entry = float(s.open[i + 1]) - slip
                    pos = {"i": i + 1, "minute": int(s.minute[i + 1]), "entry": entry, "n": n,
                           "stop": entry + e.stop_pts, "target": entry - e.target_pts,
                           "worst": entry, "setup": e.setup, "reason": e.reason}
                    day.in_position = True
                    day.setups_used[e.setup] = day.setups_used.get(e.setup, 0) + 1
    return trades


def run(sessions: Sequence[Session], cfg: BotConfig) -> List[Trade]:
    strat = ShortStrategy(cfg.strategy)
    need = strat.warmup_days()
    trades: List[Trade] = []
    for d in range(need, len(sessions)):
        if not strat.day_allowed(sessions[:d]):
            continue
        prof = strat.profile(sessions[d - cfg.strategy.profile_days:d])
        trades.extend(run_session(sessions[d], strat, prof, cfg.risk))
    return trades


# ------------------------------------------------------------ Topstep Combine

@dataclass
class Attempt:
    start: str
    outcome: str            # passed / failed / unfinished
    days: int
    profit: float
    best_day: float


def combine_attempt(trades_by_day: Dict[str, List[Trade]], dates: Sequence[str],
                    rules: AccountRules) -> Attempt:
    """Run one Combine from ``dates[0]`` until it passes, fails or runs out of data."""
    start = rules.start_balance
    balance = eod_high = start
    mll = start - rules.max_loss
    best_day = 0.0
    for n, d in enumerate(dates, 1):
        day_start = balance
        day_pnl = 0.0
        for t in trades_by_day.get(d, []):
            floor_mll = mll
            floor_dll = day_start - rules.daily_loss if rules.daily_loss > 0 else -math.inf
            worst = balance + t.mae_usd
            if worst <= max(floor_mll, floor_dll):
                if floor_dll > floor_mll:
                    balance = floor_dll            # DLL flattens you: day over, account alive
                    day_pnl = balance - day_start
                    break
                return Attempt(dates[0], "failed", n, balance + t.mae_usd - start, best_day)
            balance += t.pnl_usd
            day_pnl += t.pnl_usd
        best_day = max(best_day, day_pnl)
        eod_high = max(eod_high, balance)
        mll = min(eod_high - rules.max_loss, start)
        profit = balance - start
        target = max(rules.profit_target, best_day / rules.consistency if rules.consistency else 0)
        if profit >= target:
            return Attempt(dates[0], "passed", n, profit, best_day)
    return Attempt(dates[0], "unfinished", len(dates), balance - start, best_day)


def combine_attempts(trades: Sequence[Trade], dates: Sequence[str],
                     rules: AccountRules) -> List[Attempt]:
    """One Combine started on every date in the test window."""
    by_day: Dict[str, List[Trade]] = {}
    for t in trades:
        by_day.setdefault(t.date, []).append(t)
    return [combine_attempt(by_day, dates[k:], rules) for k in range(len(dates))]


# ------------------------------------------------------------------ summary

@dataclass
class Stats:
    trades: int = 0
    days: int = 0
    trades_per_day: float = 0.0
    net_usd: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_usd: float = 0.0
    worst_day_usd: float = 0.0
    best_day_usd: float = 0.0
    by_setup: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_exit: Dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def stats(trades: Sequence[Trade], days: int) -> Stats:
    st = Stats(trades=len(trades), days=days)
    if not trades:
        return st
    pnl = np.asarray([t.pnl_usd for t in trades])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    st.trades_per_day = len(trades) / max(days, 1)
    st.net_usd = float(pnl.sum())
    st.win_rate = float(len(wins) / len(pnl))
    st.avg_win = float(wins.mean()) if len(wins) else 0.0
    st.avg_loss = float(losses.mean()) if len(losses) else 0.0
    st.profit_factor = float(wins.sum() / -losses.sum()) if losses.sum() < 0 else float("inf")
    eq = np.cumsum(pnl)
    st.max_drawdown_usd = float((eq - np.maximum.accumulate(np.maximum(eq, 0))).min())
    daily: Dict[str, float] = {}
    for t in trades:
        daily[t.date] = daily.get(t.date, 0.0) + t.pnl_usd
    st.worst_day_usd = min(daily.values())
    st.best_day_usd = max(daily.values())
    for name in sorted({t.setup for t in trades}):
        sub = np.asarray([t.pnl_usd for t in trades if t.setup == name])
        st.by_setup[name] = {"trades": int(len(sub)), "net_usd": float(sub.sum()),
                             "win_rate": float((sub > 0).mean()), "avg_usd": float(sub.mean())}
    for t in trades:
        st.by_exit[t.exit_reason] = st.by_exit.get(t.exit_reason, 0) + 1
    return st


def describe(trades: Sequence[Trade], days: int, attempts: Sequence[Attempt], title: str) -> str:
    st = stats(trades, days)
    lines = [f"== {title}",
             f"   {st.trades} trades over {days} sessions ({st.trades_per_day:.2f}/day)   "
             f"net ${st.net_usd:+,.0f}   win {st.win_rate * 100:.0f}%   "
             f"avg win ${st.avg_win:,.0f} / avg loss ${st.avg_loss:,.0f}   "
             f"profit factor {st.profit_factor:.2f}",
             f"   max drawdown ${st.max_drawdown_usd:,.0f}   worst day ${st.worst_day_usd:+,.0f}   "
             f"best day ${st.best_day_usd:+,.0f}"]
    for name, v in st.by_setup.items():
        lines.append(f"   {name:<12} {v['trades']:>4} trades  net ${v['net_usd']:+8,.0f}  "
                     f"win {v['win_rate'] * 100:3.0f}%  avg ${v['avg_usd']:+.0f}")
    lines.append("   exits: " + ", ".join(f"{k} {v}" for k, v in sorted(st.by_exit.items())))
    if attempts:
        done = [a for a in attempts if a.outcome != "unfinished"]
        passed = [a for a in done if a.outcome == "passed"]
        failed = [a for a in done if a.outcome == "failed"]
        if done:
            med = float(np.median([a.days for a in passed])) if passed else float("nan")
            lines.append(f"   Topstep 50K Combine started on each day: {len(passed)} passed, "
                         f"{len(failed)} failed, {len(attempts) - len(done)} ran out of data"
                         f"  -> pass rate {len(passed) / len(done) * 100:.0f}% of finished attempts"
                         + (f", median {med:.0f} days to pass" if passed else ""))
        else:
            lines.append(f"   Topstep 50K Combine: none of {len(attempts)} attempts finished "
                         f"inside the data")
    return "\n".join(lines)
