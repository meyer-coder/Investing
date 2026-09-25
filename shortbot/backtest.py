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
    side: int = -1           # +1 long, -1 short

    @property
    def points(self) -> float:
        return self.side * (self.exit - self.entry)


def size_trade(e: Entry, r: RiskParams) -> int:
    """Contracts so that the stop risks about ``risk_per_trade_usd``; 0 = skip."""
    one_lot = e.stop_pts * r.point_value + r.commission_rt
    if one_lot > r.max_stop_risk_usd:
        return 0
    return int(max(1, min(r.max_contracts, math.floor(r.risk_per_trade_usd / one_lot))))


def stop_price(entry: float, side: int, stop_pts: float, tick: float) -> float:
    """Stop ``stop_pts`` against the trade, rounded to a tick away from the entry
    (the live bot rounds the same way)."""
    raw = entry - side * stop_pts
    return (math.floor(raw / tick + 1e-9) if side > 0 else math.ceil(raw / tick - 1e-9)) * tick


def target_price(entry: float, side: int, target_pts: float, tick: float) -> float:
    """Target ``target_pts`` in the trade's favour, rounded to the nearest tick."""
    return round((entry + side * target_pts) / tick) * tick


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def run_session(s: Session, strat: ShortStrategy, prof, r: RiskParams,
                max_contracts: Optional[int] = None) -> List[Trade]:
    """All trades the bot would have taken in one session."""
    p = strat.p
    slip = r.slippage_ticks * r.tick_size
    day = DayState()
    trades: List[Trade] = []
    pos: Optional[dict] = None

    for i in range(len(s)):
        m = int(s.minute[i])
        o, h, lo, c = (float(s.open[i]), float(s.high[i]), float(s.low[i]), float(s.close[i]))

        if pos is not None and i >= pos["i"]:
            sd, stop, target = pos["side"], pos["stop"], pos["target"]   # sd: +1 long, -1 short
            flat_at = pos["flat_at"]
            adverse, favour = (lo, h) if sd > 0 else (h, lo)
            exit_px, why = None, ""
            if m >= flat_at:
                exit_px, why = o - sd * slip, "flatten"
            elif i > pos["i"] and sd * (o - stop) <= 0:
                exit_px, why = o - sd * slip, "stop (gap)"
            elif sd * (adverse - stop) <= 0:
                exit_px, why = stop - sd * slip, "stop"
            elif sd * (favour - target) >= r.tick_size:
                exit_px, why = target, "target"
            elif m + s.bar_minutes > flat_at:
                # the flatten time falls inside this bar: out at its close, the
                # last price before the deadline (coarse bars, e.g. hourly)
                exit_px, why = c - sd * slip, "flatten"
            elif m + s.bar_minutes - pos["minute"] >= p.max_hold_minutes:
                exit_px, why = c - sd * slip, "time"
            elif i == len(s) - 1:
                exit_px, why = c - sd * slip, "session end"
            # Worst price seen in the trade.  Exits at the open or at the stop
            # end the trade before the rest of the bar; otherwise assume the
            # bar went against the position before it went for it.
            at_open = why == "stop (gap)" or (why == "flatten" and m >= flat_at)
            bar_worst = exit_px if at_open or why == "stop" else adverse
            if sd * (bar_worst - pos["worst"]) < 0:
                pos["worst"] = bar_worst
            if exit_px is not None:
                n, entry = pos["n"], pos["entry"]
                pnl = sd * (exit_px - entry) * r.point_value * n - r.commission_rt * n
                mae = min(0.0, sd * (pos["worst"] - entry) * r.point_value * n) - r.commission_rt * n
                exit_min = m if at_open else m + s.bar_minutes
                trades.append(Trade(s.date, pos["setup"], pos["minute"], exit_min, entry,
                                    exit_px, n, stop, target, round(pnl, 2),
                                    round(min(mae, pnl), 2), why, pos["reason"], sd))
                day.record_exit(pnl, exit_min)
                if day.pnl_usd <= -r.daily_loss_stop_usd or day.pnl_usd >= r.daily_profit_stop_usd:
                    day.done = True
                pos = None

        # a new entry needs the next bar to follow on directly (no gap in the data)
        if pos is None and i + 1 < len(s) and int(s.minute[i + 1]) == m + s.bar_minutes:
            e = strat.decide(s, i, day, prof)
            if e is not None:
                n = size_trade(e, r)
                if max_contracts is not None:
                    n = min(n, max_contracts)
                if n > 0:
                    sd = e.side
                    entry = float(s.open[i + 1]) + sd * slip
                    start = int(s.minute[i + 1])
                    pos = {"i": i + 1, "minute": start, "entry": entry, "n": n, "side": sd,
                           "stop": stop_price(entry, sd, e.stop_pts, r.tick_size),
                           "target": target_price(entry, sd, e.target_pts, r.tick_size),
                           "flat_at": strat.deadline(s.date, start), "worst": entry,
                           "setup": e.setup, "reason": e.reason}
                    day.in_position = True
                    day.setups_used[e.setup] = day.setups_used.get(e.setup, 0) + 1
    return trades


def run(sessions: Sequence[Session], cfg: BotConfig,
        strat: Optional[ShortStrategy] = None) -> List[Trade]:
    strat = strat or ShortStrategy(cfg.strategy)
    need = strat.warmup_days()
    trades: List[Trade] = []
    for d in range(need, len(sessions)):
        if not strat.day_allowed(sessions[:d]):
            continue
        prof = strat.profile(sessions[d - cfg.strategy.profile_days:d])
        trades.extend(run_session(sessions[d], strat, prof, cfg.risk, cfg.account.max_contracts))
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
                # Topstep liquidates at the limit; report that, not the trade's worst tick
                return Attempt(dates[0], "failed", n, floor_mll - start, best_day)
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


# ------------------------------------------------- Express Funded + the whole cycle

@dataclass
class Funded:
    start: str
    outcome: str                  # blown / running (data ended)
    days: int
    payouts: int
    paid_to_trader: float         # after the profit split
    first_payout_day: Optional[int]


def funded_attempt(trades_by_day: Dict[str, List[Trade]], dates: Sequence[str],
                   rules: AccountRules) -> Funded:
    """An Express Funded Account from ``dates[0]``: balance starts at $0, the max
    loss starts at -max_loss, trails the end-of-day high and locks at $0; after
    the first payout it sits at $0 for good.  A payout (half the balance, up to
    the cap) is requested as soon as there are enough winning days."""
    bal = eod_high = 0.0
    mll = -rules.max_loss
    wins = payouts = 0
    paid = since_last = 0.0
    first: Optional[int] = None
    for n, d in enumerate(dates, 1):
        day_start, day_pnl = bal, 0.0
        for t in trades_by_day.get(d, []):
            floor_dll = day_start - rules.daily_loss if rules.daily_loss > 0 else -math.inf
            if bal + t.mae_usd <= max(mll, floor_dll):
                if floor_dll > mll:
                    bal = floor_dll
                    day_pnl = bal - day_start
                    break
                return Funded(dates[0], "blown", n, payouts, paid, first)
            bal += t.pnl_usd
            day_pnl += t.pnl_usd
        since_last += day_pnl
        wins += 1 if day_pnl >= rules.winning_day else 0
        if payouts == 0:
            eod_high = max(eod_high, bal)
            mll = min(eod_high - rules.max_loss, 0.0)
        if wins >= rules.winning_days and since_last >= rules.min_cycle_profit and \
                (payouts == 0 or since_last > 0):
            amount = min(0.5 * bal, rules.payout_cap)
            if amount >= rules.min_payout:
                bal -= amount
                paid += amount * rules.payout_split
                payouts += 1
                wins, since_last, mll = 0, 0.0, 0.0
                first = first or n
    return Funded(dates[0], "running", len(dates), payouts, paid, first)


@dataclass
class Cycle:
    """Following the plan from one start date to the end of the data: buy a
    Combine, reset until it passes, trade the funded account until it is
    blown, buy again."""
    start: str
    days: int
    combines_passed: int
    combine_fails: int
    payouts: int
    paid_to_trader: float
    fees: float
    story: List[str] = field(default_factory=list)

    @property
    def net(self) -> float:
        return self.paid_to_trader - self.fees


def cycle(trades_by_day: Dict[str, List[Trade]], dates: Sequence[str],
          rules: AccountRules) -> Cycle:
    """Billing follows Topstep's Standard path: buying a Combine starts a
    30-day subscription (~21 trading days); each rebill charges the monthly
    fee and adds a reset credit; after a failure a reset uses a credit or
    costs the reset fee, and restarts the 30-day clock; passing ends the
    subscription and costs the activation fee when the funded account opens."""
    k = passed = fails = payouts = 0
    paid = fees = 0.0
    days_per_month = 21
    story: List[str] = []
    monthly = rules.billing == "monthly"
    while k < len(dates):
        fees += rules.monthly_fee                            # buy a Combine (or a challenge)
        credits = 0
        while k < len(dates):                               # attempts until it passes
            a = combine_attempt(trades_by_day, dates[k:], rules)
            story.append(f"{dates[k]}  Combine {a.outcome} after {a.days} trading days "
                         f"({a.profit:+,.0f})")
            rebills = (a.days - 1) // days_per_month if monthly else 0   # running at day 22, 43, ...
            fees += rebills * rules.monthly_fee
            credits += rebills
            k += a.days
            if a.outcome != "failed":
                break
            fails += 1
            if k >= len(dates):
                break                                       # data ends: no reset bought
            if credits:
                credits -= 1
            else:
                fees += rules.reset_fee
        if a.outcome != "passed":
            break
        passed += 1
        if k >= len(dates):
            break                                           # passed on the last day of data
        fees += rules.activation_fee
        f = funded_attempt(trades_by_day, dates[k:], rules)   # funded phase
        story.append(f"{dates[k]}  Express Funded {f.outcome} after {f.days} trading days: "
                     f"{f.payouts} payout(s), ${f.paid_to_trader:,.0f} to you")
        k += f.days
        payouts += f.payouts
        paid += f.paid_to_trader
    fees += rules.api_fee * math.ceil(len(dates) / days_per_month)
    return Cycle(dates[0], len(dates), passed, fails, payouts, paid, fees, story)


def cycles(trades: Sequence[Trade], dates: Sequence[str], rules: AccountRules,
           starts: Optional[int] = None) -> List[Cycle]:
    """The whole plan started on each of the first ``starts`` dates (default:
    the first half, so every run has at least half the data ahead of it)."""
    by_day: Dict[str, List[Trade]] = {}
    for t in trades:
        by_day.setdefault(t.date, []).append(t)
    n = starts if starts is not None else len(dates) // 2
    return [cycle(by_day, dates[k:], rules) for k in range(n)]


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


def describe(trades: Sequence[Trade], days: int, attempts: Sequence[Attempt], title: str,
             account: str = "Topstep 50K Combine") -> str:
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
            lines.append(f"   {account} started on each day: {len(passed)} passed, "
                         f"{len(failed)} failed, {len(attempts) - len(done)} ran out of data"
                         f" -> {len(passed) / len(done) * 100:.0f}% of the finished ones passed"
                         + (f", median {med:.0f} days to pass" if passed else "")
                         + " (overlapping start days: a handful of independent episodes)")
        else:
            lines.append(f"   {account}: none of {len(attempts)} attempts finished "
                         f"inside the data")
    return "\n".join(lines)
