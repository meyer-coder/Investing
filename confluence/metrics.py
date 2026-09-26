"""Turning a trade list into the numbers in the explorer.

All results are in R: +1R is a winner that made what the trade risked.  "$ at
$250 risk" simply multiplies by 250, i.e. assumes every trade is sized to
lose $250 at its stop (fractional contracts / lots allowed).

Recency weighting (the ranking score)
-------------------------------------
The whole 8 years is tested, but the ranking leans on the recent past:

    score = 0.25 * E(8y) + 0.35 * E(3y) + 0.40 * E(6m)

where E(window) is the net R per trade in that window, shrunk toward zero by
its sample size: ``total_R / (trades + 30)``.  The last 6 months carry a
little more weight than the last 3 years, and both carry more than the full
8 years.  Shrinkage keeps a strategy with three lucky trades from topping
the table.  The same weights drive the prop-firm Monte Carlo, which samples
recent days more often than old ones.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from numba import njit

RISK_USD = 250.0
WEIGHTS = {"8y": 0.25, "3y": 0.35, "6m": 0.40}
SHRINK = 30.0

# Prop-firm evaluation model (a typical 50K futures combine).
EVAL_TARGET = 3000.0
EVAL_MLL = 2000.0          # trailing on end-of-day balance, stops trailing at the start balance
EVAL_DAYS = 60
PAYOUT_WIN_DAYS = 5        # winning days of at least PAYOUT_WIN_USD
PAYOUT_WIN_USD = 150.0
PAYOUT_MIN_PROFIT = 1000.0
FUNDED_DAYS = 60
MC_SIMS = 2000
MC_BLOCK = 5


def day_to_date(day: int) -> dt.date:
    return dt.date(1970, 1, 1) + dt.timedelta(days=int(day))


@dataclass
class Calendar:
    """Trading days of the feed within the test, and the window boundaries."""

    days: np.ndarray           # trading-day ids, ascending
    start: int                 # first day of the 8-year test
    d3y: int
    d12m: int
    d6m: int
    end: int
    month_ends: np.ndarray     # day id of the last trading day of each month
    month_labels: List[str]

    @classmethod
    def build(cls, all_days: np.ndarray, start: dt.date, end: dt.date) -> "Calendar":
        ep = dt.date(1970, 1, 1)
        s = (start - ep).days
        e = (end - ep).days
        days = np.unique(all_days)
        days = days[(days >= s) & (days <= e)]
        def back(years=0, months=0):
            y, m = end.year - years, end.month - months
            while m <= 0:
                m += 12
                y -= 1
            return (dt.date(y, m, min(end.day, 28)) - ep).days + 1
        dates = [day_to_date(d) for d in days]
        keys = np.array([d.year * 12 + d.month for d in dates])
        last = np.flatnonzero(np.append(np.diff(keys) != 0, True))
        return cls(days, s, back(years=3), back(years=1), back(months=6), e,
                   days[last], [dates[i].strftime("%Y-%m") for i in last])

    def n_days(self, since: int) -> int:
        return int(np.sum(self.days >= since))

    def weeks(self, since: int) -> float:
        return max((self.end - since + 1) / 7.0, 1e-9)


def score_of(total: float, n: int, r3: float, n3: int, r6: float, n6: int) -> float:
    """Recency-weighted, sample-size-shrunk expectancy (see module docstring)."""
    return (WEIGHTS["8y"] * total / (n + SHRINK) + WEIGHTS["3y"] * r3 / (n3 + SHRINK)
            + WEIGHTS["6m"] * r6 / (n6 + SHRINK))


def _window(net, mask):
    n = int(mask.sum())
    tot = float(net[mask].sum()) if n else 0.0
    return n, tot


def max_drawdown(cum: np.ndarray) -> float:
    if cum.size == 0:
        return 0.0
    peak = np.maximum.accumulate(np.concatenate(([0.0], cum)))[1:]
    return float(np.max(peak - cum))


def evaluate(trades: Dict[str, np.ndarray], cal: Calendar, seed: int = 0) -> dict:
    """Every statistic the explorer shows for one strategy."""
    gross = trades["gross"]
    cost = trades["cost"]
    net = gross - cost
    day = trades["day"]
    n = int(net.size)
    out: dict = {"trades": n}
    weeks = cal.weeks(cal.start)
    out["per_week"] = n / weeks
    if n == 0:
        out.update(win=np.nan, avg_rr=np.nan, net_r=np.nan, gross_r=np.nan, total_r=0.0,
                   usd=0.0, max_dd=0.0, cost_r=np.nan, pf=np.nan, t=0.0,
                   n12=0, r12=0.0, n3y=0, r3y=0.0, e3y=np.nan, n6=0, r6=0.0, e6=np.nan,
                   score=0.0, usd_day=0.0, d_p10=0.0, d_p90=0.0, green_days=np.nan,
                   p_pass=0.0, p_payout=0.0, pass_days=np.nan, streak=0, best=np.nan, worst=np.nan,
                   usd_day_3y=0.0, usd_day_6m=0.0, active_days=0, gsd=0.0)
        return out
    wins = net > 0
    out["win"] = float(wins.mean())
    aw = float(net[wins].mean()) if wins.any() else np.nan
    al = float(-net[~wins].mean()) if (~wins).any() else np.nan
    out["avg_rr"] = aw / al if (al and al > 0 and not np.isnan(aw)) else np.nan
    out["net_r"] = float(net.mean())
    out["gross_r"] = float(gross.mean())
    out["total_r"] = float(net.sum())
    out["usd"] = out["total_r"] * RISK_USD
    cum = np.cumsum(net)
    out["max_dd"] = max_drawdown(cum)
    out["cost_r"] = float(cost.mean())
    pos, neg = float(net[wins].sum()), float(-net[~wins].sum())
    out["pf"] = pos / neg if neg > 0 else np.nan
    sd = float(net.std(ddof=1)) if n > 1 else 0.0
    out["t"] = float(net.mean() / sd * np.sqrt(n)) if sd > 0 else 0.0
    out["gsd"] = float(gross.std(ddof=1)) if n > 1 else 0.0
    out["best"], out["worst"] = float(net.max()), float(net.min())
    # losing streak
    streak = run = 0
    for w in wins:
        run = 0 if w else run + 1
        streak = max(streak, run)
    out["streak"] = streak
    # windows
    n12, r12 = _window(net, day >= cal.d12m)
    n3, r3 = _window(net, day >= cal.d3y)
    n6, r6 = _window(net, day >= cal.d6m)
    out.update(n12=n12, r12=r12, n3y=n3, r3y=r3, e3y=r3 / n3 if n3 else np.nan,
               n6=n6, r6=r6, e6=r6 / n6 if n6 else np.nan)
    out["score"] = score_of(out["total_r"], n, r3, n3, r6, n6)
    # daily P&L at $250 risk
    ud, inv = np.unique(day, return_inverse=True)
    dpl = np.bincount(inv, weights=net) * RISK_USD
    out["active_days"] = int(ud.size)
    out["usd_day"] = float(dpl.sum() / max(cal.n_days(cal.start), 1))
    out["usd_day_3y"] = float(dpl[ud >= cal.d3y].sum() / max(cal.n_days(cal.d3y), 1))
    out["usd_day_6m"] = float(dpl[ud >= cal.d6m].sum() / max(cal.n_days(cal.d6m), 1))
    q = np.percentile(dpl, [5, 10, 25, 50, 75, 90, 95])
    out["d_p10"], out["d_p90"] = float(q[1]), float(q[5])
    out["d_q"] = [float(x) for x in q]
    out["d_min"], out["d_max"] = float(dpl.min()), float(dpl.max())
    out["green_days"] = float((dpl > 0).mean())
    # full calendar of daily P&L (zeros on days without a trade) for the prop sim
    full = np.zeros(cal.days.size)
    pos_ = np.searchsorted(cal.days, ud)
    ok = (pos_ < cal.days.size)
    ok[ok] = cal.days[pos_[ok]] == ud[ok]
    np.add.at(full, pos_[ok], dpl[ok])
    w = np.full(cal.days.size, WEIGHTS["8y"] / cal.days.size)
    in3, in6 = cal.days >= cal.d3y, cal.days >= cal.d6m
    w[in3] += WEIGHTS["3y"] / max(in3.sum(), 1)
    w[in6] += WEIGHTS["6m"] / max(in6.sum(), 1)
    p_pass, p_pay, med = prop_mc(full, np.cumsum(w) / w.sum(), MC_SIMS, seed)
    out["p_pass"], out["p_payout"], out["pass_days"] = p_pass, p_pay, med
    return out


def profile(trades: Dict[str, np.ndarray], cal: Calendar) -> dict:
    """The heavier per-strategy detail shown when a row is clicked."""
    net = trades["gross"] - trades["cost"]
    day = trades["day"]
    # monthly equity (cumulative net R at each month end)
    idx = np.searchsorted(day, cal.month_ends, side="right")
    cum = np.concatenate(([0.0], np.cumsum(net)))
    eq = [round(float(cum[i]), 2) for i in idx]
    years: Dict[str, List[float]] = {}
    ylab = np.array([day_to_date(d).year for d in day]) if day.size else np.array([], int)
    for y in range(day_to_date(cal.start).year, day_to_date(cal.end).year + 1):
        m = ylab == y
        years[str(y)] = [int(m.sum()), round(float(net[m].sum()), 2)]
    exits = np.bincount(trades["reason"].astype(int), minlength=4).tolist() if day.size else [0, 0, 0, 0]
    last = []
    for k in range(max(0, day.size - 8), day.size):
        last.append([day_to_date(day[k]).isoformat(), int(trades["dir"][k]), round(float(net[k]), 2),
                     int(trades["reason"][k])])
    longs = trades["dir"] > 0
    side = [int(longs.sum()), round(float(net[longs].sum()), 2),
            int((~longs).sum()), round(float(net[~longs].sum()), 2)]
    return {"eq": eq, "years": years, "exits": exits, "last": last, "side": side}


@njit(cache=True)
def prop_mc(daily, wcum, sims, seed):
    """Monte-Carlo a 50K-style evaluation then a funded account.

    Days are drawn in blocks of MC_BLOCK consecutive trading days, with block
    starts sampled by recency weight.  Returns (P(pass), P(pass and reach
    first payout), median trading days to pass).
    """
    np.random.seed(seed)
    n = daily.size
    passed = 0
    paid = 0
    days_to_pass = np.full(sims, np.nan)
    for s in range(sims):
        # ---------------- evaluation
        bal = 0.0
        peak = 0.0
        status = 0
        t = 0
        pos = n
        while t < EVAL_DAYS:
            if pos >= n or (t % MC_BLOCK) == 0:
                u = np.random.random()
                pos = np.searchsorted(wcum, u)
                if pos > n - MC_BLOCK:
                    pos = n - MC_BLOCK
            bal += daily[pos]
            pos += 1
            t += 1
            if bal >= EVAL_TARGET:
                status = 1
                break
            floor = min(peak - EVAL_MLL, 0.0)
            if bal <= floor:
                status = -1
                break
            if bal > peak:
                peak = bal
        if status != 1:
            continue
        passed += 1
        days_to_pass[s] = t
        # ---------------- funded account, first payout
        bal = 0.0
        peak = 0.0
        good = 0
        t = 0
        pos = n
        while t < FUNDED_DAYS:
            if pos >= n or (t % MC_BLOCK) == 0:
                u = np.random.random()
                pos = np.searchsorted(wcum, u)
                if pos > n - MC_BLOCK:
                    pos = n - MC_BLOCK
            d = daily[pos]
            bal += d
            pos += 1
            t += 1
            if d >= PAYOUT_WIN_USD:
                good += 1
            floor = min(peak - EVAL_MLL, 0.0)
            if bal <= floor:
                break
            if bal > peak:
                peak = bal
            if good >= PAYOUT_WIN_DAYS and bal >= PAYOUT_MIN_PROFIT:
                paid += 1
                break
    med = np.nanmedian(days_to_pass) if passed > 0 else np.nan
    return passed / sims, paid / sims, med
