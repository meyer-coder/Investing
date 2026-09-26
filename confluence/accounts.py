"""Which prop account to trade a strategy on, at what size — and what it's worth.

For every strategy the backtest leaves a list of trades in R plus the stop
distance of each trade (``risk_pts = cost_rt / cost_R``).  That is enough to
re-price every trade for any contract at any size:

    units   = round(risk_usd / (risk_pts * point_value_of_the_smallest_contract))
    dollars = gross_R * risk_pts * point_value * units
              - sum over contracts (commission + 2 ticks of slippage)

``units`` counts the smallest contract the firm allows on that underlying
(MNQ for NQ at both firms, 6E at FundedNext because it bans M6E).  Ten
micros are bought as one mini when the mini is allowed, which is cheaper.
Sizes are capped by the plan's contract limit (in mini-equivalents, 10
micros = 1 mini), by Topstep's per-product limits (CL/GC 3/6/9, SIL/MHG
2/4/6 ...) and, in a Topstep Express Funded Account, by its scaling plan.
A trade whose stop is so wide that even one contract risks more than 1.5x
the chosen risk is skipped.

Every plan that is on sale today at the two firms is simulated
(``PLANS``):

* Topstep Trading Combine 50K / 100K / 150K, then the Express Funded
  Account (Standard payout path) — monthly fee until passed, $149 activation.
* FundedNext Rapid Pro, Rapid Daily, Legacy and Flex, each in three sizes —
  one-time fee.

The simulation (``_simulate``) draws trading days from the strategy's own
daily P&L in 5-day blocks, sampling recent days more often (the same
0.25 / 0.35 / 0.40 weights as the ranking score), and runs

1. the evaluation, up to 120 trading days: end-of-day trailing max loss
   that locks at the start balance (+$100 at FundedNext), checked against
   the day's worst point including each open trade's adverse excursion; the consistency rule that raises the
   target (Topstep 55%, Legacy/Flex 40%); minimum trading days; the Rapid
   Daily soft daily loss limit (stop trading for the day); and the
   inactivity rule (about 21 trading days without a trade ends the
   account);
2. the funded account, another 120 trading days, requesting a payout as
   soon as the plan allows and withdrawing what it allows (Topstep: 5
   winning days of $150+, 50% of the balance up to $2K/$3K/$5K; Rapid Pro:
   every 3 days with the 40% consistency rule; Rapid Daily: everything
   above the buffer once $500 above it; Legacy / Flex: 5 benchmark days
   and $500 profit, 50% of profit), paying the trader's split minus a 3.5%
   processing fee at FundedNext, until the account is breached, concluded
   (5 rewards on Rapid / Flex) or the 120 days run out.

The value of an attempt is what the trader is paid minus what the attempt
cost.  Each strategy is tried on every plan at every risk level in
``RISK_GRID`` (the same random days for every combination, so they are
compared like for like) and the one with the highest expected value wins.
Because an attempt can lose at most its fee while the payouts are capped
per request but not in count, a larger risk per trade often has the higher
expected value even when it busts more accounts — the chosen risk and its
bust rate are shown side by side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from numba import njit

from .futures import UNDERLYINGS, Contract, Underlying, commission, firm_products, load_propfirms

RISK_GRID = [100.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0, 750.0, 1000.0, 1500.0, 2000.0]
EVAL_DAYS = 120
FUNDED_DAYS = 120
BLOCK = 5
INACTIVE_DAYS = 21            # ~30 calendar days without a trade
TRADING_DAYS_PER_MONTH = 21   # Topstep rebills every 30 calendar days
SKIP_WIDE = 1.5               # skip a trade if one unit risks more than this x the target risk
WEIGHTS = (0.25, 0.35, 0.40)  # 8y, 3y, 6m — as in metrics.WEIGHTS

# Topstep per-product limits at 50K / 100K / 150K (contracts of that symbol).
TOPSTEP_PRODUCT_CAP = {"CL": (3, 6, 9), "QM": (3, 6, 9), "GC": (3, 6, 9), "MCL": (30, 60, 90),
                       "MGC": (30, 60, 90), "SIL": (2, 4, 6), "MHG": (2, 4, 6)}

# payout modes
PAY_TOPSTEP, PAY_RAPID_PRO, PAY_RAPID_DAILY, PAY_LEGACY, PAY_FLEX = range(5)


@dataclass(frozen=True)
class Plan:
    key: str                  # short id, e.g. "TS-50K"
    firm: str                 # "Topstep" | "FundedNext"
    name: str                 # "Trading Combine 50K"
    size: int
    price: float              # one-time fee, or the monthly fee when ``monthly``
    monthly: bool
    activation: float
    target: float
    mll: float
    lock: float               # the trailing max loss stops at start + lock
    cons: float               # consistency: best day <= cons x target (0 = none)
    min_days: int
    cap: int                  # evaluation contract limit, mini-equivalents
    dll: float                # soft daily loss limit (0 = none), evaluation and funded
    f_mll: float
    f_lock: float
    f_lock_paid: float        # floor after the first payout
    f_caps: Tuple[int, ...]   # funded contract limit per scaling tier
    f_tiers: Tuple[float, ...]  # balance thresholds between tiers (len = len(f_caps) - 1)
    pay_mode: int
    pay_thr: float            # winning / benchmark day threshold
    pay_cap: float
    pay_min: float
    pay_frac: float
    split: float
    fee: float                # payout processing fee
    max_pay: int              # 0 = unlimited

    @property
    def label(self) -> str:
        return f"{self.firm} {self.name}"


def _plans() -> List[Plan]:
    """The plans on sale on 2026-09-26 (numbers from data/propfirms.json)."""
    P = []
    ts = [(50_000, 49.0, 3000, 2000, 5, (2, 3, 5), (1500, 2000), 2000),
          (100_000, 99.0, 6000, 3000, 10, (3, 4, 5, 10), (1500, 2000, 3000), 3000),
          (150_000, 199.0, 9000, 4500, 15, (3, 4, 5, 10, 15), (1500, 2000, 3000, 4500), 5000)]
    for size, price, tgt, mll, cap, caps, tiers, pcap in ts:
        k = size // 1000
        P.append(Plan(f"TS-{k}K", "Topstep", f"Trading Combine {k}K", size, price, True, 149.0,
                      tgt, mll, 0.0, 0.55, 2, cap, 0.0, mll, 0.0, 0.0, caps, tiers,
                      PAY_TOPSTEP, 150.0, pcap, 125.0, 0.5, 0.9, 0.0, 0))
    rp = [(25_000, 79.99, 1500, 1000, 2, 800, 500), (50_000, 159.99, 3000, 2000, 4, 1200, 1000),
          (100_000, 279.99, 5000, 2500, 6, 2500, 1250)]
    for size, price, tgt, mll, cap, pcap, _ in rp:
        k = size // 1000
        P.append(Plan(f"FN-RP-{k}K", "FundedNext", f"Rapid Pro {k}K", size, price, False, 0.0,
                      tgt, mll, 100.0, 0.0, 1, cap, 0.0, mll, 100.0, 100.0, (cap,), (),
                      PAY_RAPID_PRO, 0.0, pcap, 250.0, 1.0, 0.9, 0.035, 5))
    rd = [(25_000, 79.99), (50_000, 169.99), (100_000, 279.99)]
    for (size, price), (_, _, tgt, mll, cap, pcap, dll) in zip(rd, rp):
        k = size // 1000
        P.append(Plan(f"FN-RD-{k}K", "FundedNext", f"Rapid Daily {k}K", size, price, False, 0.0,
                      tgt, mll, 100.0, 0.0, 1, cap, dll, mll, 100.0, 100.0, (cap,), (),
                      PAY_RAPID_DAILY, 0.0, pcap, 250.0, 1.0, 0.9, 0.035, 5))
    lg = [(25_000, 79.99, 1250, 1000, 2, 3, 100.0, 3000), (50_000, 199.99, 3000, 2000, 3, 5, 200.0, 6000),
          (100_000, 239.99, 6000, 3000, 5, 7, 200.0, 6000)]
    for size, price, tgt, mll, cap, fcap, thr, pcap in lg:
        k = size // 1000
        P.append(Plan(f"FN-LG-{k}K", "FundedNext", f"Legacy {k}K", size, price, False, 0.0,
                      tgt, mll, 0.0, 0.40, 3, cap, 0.0, mll, 0.0, 0.0, (fcap,), (),
                      PAY_LEGACY, thr, pcap, 250.0, 0.5, 0.8, 0.035, 0))
    fx = [(50_000, 69.99, 2500, 1500, 3, 200.0, 1500), (100_000, 139.99, 5000, 2500, 5, 200.0, 2500),
          (150_000, 249.99, 8000, 4000, 8, 250.0, 4000)]
    for size, price, tgt, mll, cap, thr, pcap in fx:
        k = size // 1000
        P.append(Plan(f"FN-FX-{k}K", "FundedNext", f"Flex {k}K", size, price, False, 0.0,
                      tgt, mll, 100.0, 0.40, 3, cap, 0.0, mll, 100.0, 100.0, (cap,), (),
                      PAY_FLEX, thr, pcap, 250.0, 0.5, 0.95, 0.035, 5))
    return P


PLANS: List[Plan] = _plans()
PLAN_BY_KEY = {p.key: p for p in PLANS}


def check_plans(pf: dict) -> List[str]:
    """Differences between PLANS and data/propfirms.json (targets, max loss, caps, price)."""
    issues = []
    names = {"Topstep": "Trading Combine", "Rapid Pro": "Rapid Pro", "Rapid Daily": "Rapid Daily",
             "Legacy": "Legacy", "Flex": "Flex"}
    for p in PLANS:
        firm = next(f for f in pf["firms"] if f["firm"].startswith(p.firm))
        base = p.name.rsplit(" ", 1)[0]
        base = names.get(base, base)
        j = next((q for q in firm["plans"] if q["plan"] == base and q["size"] == p.size), None)
        if j is None:
            issues.append(f"{p.key}: not in propfirms.json")
            continue
        for a, b in (("profit_target", p.target), ("max_loss", p.mll), ("max_minis", p.cap),
                     ("price_usd", p.price)):
            if j.get(a) is not None and abs(float(j[a]) - b) > 1e-6:
                issues.append(f"{p.key}: {a} {j[a]} != {b}")
    return issues


# ---------------------------------------------------------------- sizing
@dataclass
class Sizing:
    """How one firm lets you trade one underlying."""
    firm: str
    unit: Contract                       # the smallest allowed contract
    ladder: List[Tuple[Contract, int, float]]   # (contract, units per contract, $ cost RT incl. slippage), largest first
    unit_weight: float                   # mini-equivalents per unit
    product_cap: Dict[int, float]        # plan size -> cap in units from per-product limits (Topstep)


def sizing_for(pf: dict, firm: str, u: Underlying) -> Optional[Sizing]:
    allowed = firm_products(pf)[next(f["firm"] for f in pf["firms"] if f["firm"].startswith(firm))]
    cs = [c for c in u.contracts if c.symbol in allowed]
    if not cs:
        return None
    unit = cs[0]
    ladder = []
    for c in reversed(cs):
        k = c.point_value / unit.point_value
        if abs(k - round(k)) > 1e-9:
            continue
        ladder.append((c, int(round(k)), commission(pf, firm, c.symbol) + 2 * c.tick * c.point_value))
    # mini-equivalents per unit: micros count 0.1; at Topstep SIL counts 0.2 and MET/MBT a full lot
    w = 0.1 if unit.micro else 1.0
    if firm == "Topstep" and unit.symbol == "SIL":
        w = 0.2
    if firm == "Topstep" and unit.symbol in ("MET", "MBT"):
        w = 1.0
    # only merge units into a bigger contract when that leaves the mini-equivalent count unchanged
    ladder = [(c, k, cr) for c, k, cr in ladder if k == 1 or abs(k * w - (0.1 if c.micro else 1.0)) < 1e-9]
    pcap: Dict[int, float] = {}
    if firm == "Topstep":
        for i, size in enumerate((50_000, 100_000, 150_000)):
            caps = []
            for c, k, _ in ladder:
                if c.symbol in TOPSTEP_PRODUCT_CAP:
                    caps.append(TOPSTEP_PRODUCT_CAP[c.symbol][i] * k)
            if caps:
                pcap[size] = float(max(caps))
    return Sizing(firm, unit, ladder, w, pcap)


def price_trades(gross: np.ndarray, risk_pts: np.ndarray, sz: Sizing, risk_usd: float,
                 cap_minis: float, size: int, mae: Optional[np.ndarray] = None
                 ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dollar P&L, units and worst open P&L (after costs) of every trade at ``risk_usd`` per trade."""
    rpu = risk_pts * sz.unit.point_value
    umax = math.floor(cap_minis / sz.unit_weight + 1e-9)
    if size in sz.product_cap:
        umax = min(umax, int(sz.product_cap[size]))
    with np.errstate(divide="ignore", invalid="ignore"):
        u = np.floor(risk_usd / rpu + 0.5)
    u = np.where(rpu <= SKIP_WIDE * risk_usd, np.maximum(u, 1.0), 0.0)
    u = np.where(np.isfinite(u), np.minimum(u, umax), 0.0)
    rem = u.copy()
    cost = np.zeros_like(u)
    for c, k, c_rt in sz.ladder:
        n = np.floor(rem / k)
        rem -= n * k
        cost += n * c_rt
    per_r = risk_pts * sz.unit.point_value * u
    pnl = gross * per_r - cost
    worst = (np.minimum(mae, 0.0) if mae is not None else np.zeros_like(gross)) * per_r - cost
    worst = np.minimum(worst, pnl)
    return np.where(u > 0, pnl, 0.0), u, np.where(u > 0, worst, 0.0)


@njit(cache=True)
def daily_arrays(day_idx, pnl, worst, n_days, dll):
    """Per calendar day: P&L (after a soft daily loss limit), worst point including open trades, trades.

    ``worst`` is each trade's worst open P&L (its MAE in dollars, costs included).  A soft daily loss
    limit is enforced on open P&L like the firms do: the position is flattened at the limit and the
    day ends there.
    """
    out = np.zeros(n_days)
    low = np.zeros(n_days)
    cnt = np.zeros(n_days, np.int32)
    stopped = -1
    for i in range(day_idx.size):
        d = day_idx[i]
        if d < 0:
            continue
        if d == stopped:
            continue
        cnt[d] += 1
        if dll > 0 and out[d] + worst[i] <= -dll:
            out[d] = min(out[d] + pnl[i], -dll)
            if out[d] < low[d]:
                low[d] = out[d]
            stopped = d
            continue
        if out[d] + worst[i] < low[d]:
            low[d] = out[d] + worst[i]
        out[d] += pnl[i]
        if out[d] < low[d]:
            low[d] = out[d]
    return out, low, cnt


def block_starts(n_days: int, days: np.ndarray, d3y: int, d6m: int, sims: int, n_blocks: int,
                 rng: np.random.Generator) -> np.ndarray:
    """Recency-weighted 5-day block starts, shape (sims, n_blocks)."""
    w = np.full(n_days, WEIGHTS[0] / n_days)
    in3, in6 = days >= d3y, days >= d6m
    w[in3] += WEIGHTS[1] / max(in3.sum(), 1)
    w[in6] += WEIGHTS[2] / max(in6.sum(), 1)
    w /= w.sum()
    s = rng.choice(n_days, size=(sims, n_blocks), p=w)
    return np.minimum(s, n_days - BLOCK).astype(np.int64)


@njit(cache=True)
def _simulate(e_pnl, e_low, e_cnt, f_pnl, f_low, f_cnt, f_tiers,
              e_starts, f_starts,
              target, mll, lock, cons, min_days, price, monthly, activation,
              f_mll, f_lock, f_lock_paid, pay_mode, pay_thr, pay_cap, pay_min, pay_frac,
              split, fee, max_pay, eval_days, funded_days, block, inactive, seq_start):
    """One plan at one size for every simulated attempt.

    Returns per attempt: outcome (1 pass, -1 breached, 0 ran out of time),
    days in the evaluation, cost, total paid to the trader, number of payouts,
    funded outcome (1 breached, 0 not).

    With ``seq_start >= 0`` there is no resampling: one attempt starts on that
    day and walks the real calendar forward, the funded account starting the
    day after the evaluation ends (the blind replay).
    """
    sims = e_starts.shape[0]
    nd = e_pnl.size
    outcome = np.zeros(sims, np.int8)
    edays = np.zeros(sims, np.int32)
    cost = np.zeros(sims)
    paid = np.zeros(sims)
    npay = np.zeros(sims, np.int32)
    fbust = np.zeros(sims, np.int8)
    for s in range(sims):
        # ------------------------------------------------ evaluation
        bal = 0.0
        peak = 0.0
        best = 0.0
        traded = 0
        idle = 0
        res = 0
        t = 0
        while t < eval_days:
            if seq_start >= 0:
                d = seq_start + t
                if d >= nd:
                    break
            else:
                d = e_starts[s, t // block] + (t % block)
            t += 1
            floor = min(peak - mll, lock)
            if e_cnt[d] > 0:
                traded += 1
                idle = 0
                if bal + e_low[d] <= floor:
                    res = -1
                    break
                bal += e_pnl[d]
                if e_pnl[d] > best:
                    best = e_pnl[d]
            else:
                idle += 1
                if idle >= inactive:
                    res = -1
                    break
            if bal > peak:
                peak = bal
            tgt = target
            if cons > 0 and best > cons * target:
                tgt = best / cons
            if bal >= tgt and traded >= min_days:
                res = 1
                break
        outcome[s] = res
        edays[s] = t
        if monthly:
            cost[s] = price * (1 + (t - 1) // 21)
        else:
            cost[s] = price
        if res != 1:
            continue
        cost[s] += activation
        # ------------------------------------------------ funded
        bal = 0.0
        peak = 0.0
        paid_once = False
        cyc_start = 0.0
        cyc_best = 0.0
        cyc_days = 0
        wins = 0
        idle = 0
        tier = 0
        t = 0
        while t < funded_days:
            if seq_start >= 0:
                d = seq_start + edays[s] + t
                if d >= nd:
                    break
            else:
                d = f_starts[s, t // block] + (t % block)
            t += 1
            floor = min(peak - f_mll, f_lock)
            if paid_once and floor < f_lock_paid:
                floor = f_lock_paid
            if f_cnt[tier, d] > 0:
                idle = 0
                pnl = f_pnl[tier, d]
                if bal + f_low[tier, d] <= floor:
                    fbust[s] = 1
                    break
                bal += pnl
                cyc_days += 1
                if pnl > cyc_best:
                    cyc_best = pnl
                if pay_thr > 0 and pnl >= pay_thr:
                    wins += 1
            else:
                idle += 1
                if idle >= inactive:
                    fbust[s] = 1
                    break
            if bal > peak:
                peak = bal
            # scaling tier for the next session
            tier = 0
            for k in range(f_tiers.size):
                if bal >= f_tiers[k]:
                    tier = k + 1
            # payout request
            amt = 0.0
            cyc = bal - cyc_start
            if pay_mode == 0:       # Topstep XFA standard
                if wins >= 5 and (not paid_once or cyc > 0):
                    amt = min(pay_frac * bal, pay_cap)
            elif pay_mode == 1:     # FundedNext Rapid Pro
                if cyc_days >= 3 and cyc >= 500.0 and cyc_best <= 0.4 * cyc:
                    amt = min(cyc, pay_cap, bal - max(floor, f_lock))
            elif pay_mode == 2:     # FundedNext Rapid Daily
                buf = f_mll + 100.0
                if bal - buf >= 500.0:
                    amt = min(bal - buf, pay_cap)
            else:                   # Legacy / Flex
                if wins >= 5 and cyc >= 500.0:
                    amt = min(pay_frac * bal, pay_cap)
            if amt >= pay_min:
                bal -= amt
                paid[s] += amt * split * (1.0 - fee)
                npay[s] += 1
                paid_once = True
                cyc_start = bal
                cyc_best = 0.0
                cyc_days = 0
                wins = 0
                if max_pay > 0 and npay[s] >= max_pay:
                    break
    return outcome, edays, cost, paid, npay, fbust


@dataclass
class Result:
    plan: str
    risk: float
    sims: int
    p_pass: float
    p_bust: float        # breached in the evaluation
    p_payout: float      # at least one payout
    ev: float            # expected paid - cost per attempt
    cost: float
    paid: float          # expected paid per attempt
    paid_if: float       # expected paid given at least one payout
    pay_n: float         # payouts given funded
    days_pass: float     # median trading days to pass
    f_bust: float        # funded account breached, given passed
    units: float         # median units per trade
    skipped: float       # share of trades skipped (stop too wide)
    contracts: str = ""


def _summary(plan: Plan, risk: float, outs, units, skipped) -> Result:
    outcome, edays, cost, paid, npay, fbust = outs
    sims = outcome.size
    passed = outcome == 1
    got = npay > 0
    return Result(plan.key, risk, sims, float(passed.mean()), float((outcome == -1).mean()),
                  float(got.mean()), float((paid - cost).mean()), float(cost.mean()), float(paid.mean()),
                  float(paid[got].mean()) if got.any() else 0.0,
                  float(npay[passed].mean()) if passed.any() else 0.0,
                  float(np.median(edays[passed])) if passed.any() else float("nan"),
                  float(fbust[passed].mean()) if passed.any() else float("nan"),
                  float(units), float(skipped))


def describe_units(sz: Sizing, u: float) -> str:
    """'2 NQ + 3 MNQ' for a unit count."""
    u = int(round(u))
    if u <= 0:
        return "—"
    parts = []
    rem = u
    for c, k, _ in sz.ladder:
        n = rem // k
        rem -= n * k
        if n:
            parts.append(f"{n} {c.symbol}")
    return " + ".join(parts)


class Optimiser:
    """Prices one strategy's trades for every plan and risk level."""

    def __init__(self, pf: Optional[dict] = None, plans: Sequence[Plan] = PLANS,
                 risks: Sequence[float] = RISK_GRID):
        self.pf = pf or load_propfirms()
        self.plans = list(plans)
        self.risks = list(risks)
        self.sizing: Dict[Tuple[str, str], Optional[Sizing]] = {}
        for code, u in UNDERLYINGS.items():
            for firm in ("Topstep", "FundedNext"):
                self.sizing[(firm, code)] = sizing_for(self.pf, firm, u)

    def plans_for(self, underlying: str) -> List[Plan]:
        return [p for p in self.plans if self.sizing[(p.firm, underlying)] is not None]

    def run(self, underlying: str, gross: np.ndarray, risk_pts: np.ndarray, day_idx: np.ndarray,
            n_days: int, e_starts: np.ndarray, f_starts: np.ndarray,
            plans: Optional[Sequence[Plan]] = None, risks: Optional[Sequence[float]] = None,
            mae: Optional[np.ndarray] = None, seq_start: int = -1) -> List[Result]:
        eval_days, funded_days = (EVAL_DAYS, FUNDED_DAYS) if seq_start < 0 else (n_days, n_days)
        out: List[Result] = []
        cache: Dict[tuple, tuple] = {}
        risks = self.risks if risks is None else risks
        for plan in (self.plans_for(underlying) if plans is None else plans):
            sz = self.sizing[(plan.firm, underlying)]
            if sz is None:
                continue
            for r in risks:
                def arrays(cap):
                    key = (plan.firm, cap, r, plan.dll, plan.size)
                    if key not in cache:
                        pnl, u, worst = price_trades(gross, risk_pts, sz, r, cap, plan.size, mae)
                        took = u > 0
                        a = daily_arrays(np.where(took, day_idx, -1), pnl, worst, n_days, plan.dll)
                        med = float(np.median(u[took])) if took.any() else 0.0
                        cache[key] = (a, med, float(1.0 - took.mean()) if u.size else 0.0)
                    return cache[key]
                (ep, el, ec), med, skipped = arrays(plan.cap)
                fa = [arrays(c)[0] for c in plan.f_caps]
                fp = np.stack([a[0] for a in fa])
                fl = np.stack([a[1] for a in fa])
                fc = np.stack([a[2] for a in fa])
                outs = _simulate(ep, el, ec, fp, fl, fc, np.array(plan.f_tiers, dtype=np.float64),
                                 e_starts, f_starts, plan.target, plan.mll, plan.lock, plan.cons,
                                 plan.min_days, plan.price, plan.monthly, plan.activation,
                                 plan.f_mll, plan.f_lock, plan.f_lock_paid, plan.pay_mode, plan.pay_thr,
                                 plan.pay_cap, plan.pay_min, plan.pay_frac, plan.split, plan.fee,
                                 plan.max_pay, eval_days, funded_days, BLOCK, INACTIVE_DAYS, seq_start)
                res = _summary(plan, r, outs, med, skipped)
                res.contracts = describe_units(sz, med)
                out.append(res)
        return out


def best_of(results: Sequence[Result]) -> Optional[Result]:
    ok = [r for r in results if np.isfinite(r.ev)]
    return max(ok, key=lambda r: r.ev) if ok else None


# ---------------------------------------------------------------- the whole run
STAGE1_SIMS = 300          # every plan x every risk level
STAGE2_SIMS = 3000         # the best few combinations again, with fresh draws
STAGE2_TOP = 4
MIN_TRADES = 20
SAFE_BUST = 0.35           # the lower-risk alternative keeps the evaluation bust rate at or under this
BLIND_SIMS = 200           # the blind test's account search, on data up to six months ago


def _day_index(days: np.ndarray, trade_days: np.ndarray) -> np.ndarray:
    n = days.size
    di = np.searchsorted(days, trade_days)
    ok = di < n
    ok[ok] = days[di[ok]] == trade_days[ok]
    return np.where(ok, di, -1).astype(np.int64)


def optimise_feed(feed: str, items: Sequence[Tuple[str, str]], trades_dir: str, cost_rt: Dict[str, float],
                  seed: int = 7) -> Dict[str, dict]:
    """Optimise every (sid, underlying) of one feed; returns sid -> account summary."""
    import glob
    import os
    import time

    z = np.load(os.path.join(trades_dir, f"cal_{feed}.npz"))
    days, (start, d3y, d12m, d6m, end) = z["days"], z["bounds"]
    trades: Dict[str, Dict[str, np.ndarray]] = {}
    for path in sorted(glob.glob(os.path.join(trades_dir, f"{feed}_*m.npz"))):
        trades.update(_load_one(path))
    opt = Optimiser()
    n = days.size
    out: Dict[str, dict] = {}
    t0 = time.time()
    for k, (sid, und) in enumerate(items):
        t = trades.get(sid)
        if t is None or t["gross"].size < MIN_TRADES:
            continue
        risk_pts = cost_rt[und] / t["cost"]
        di = _day_index(days, t["day"].astype(np.int64))
        rng = np.random.default_rng([seed, k, n])
        e1 = block_starts(n, days, d3y, d6m, STAGE1_SIMS, EVAL_DAYS // BLOCK, rng)
        f1 = block_starts(n, days, d3y, d6m, STAGE1_SIMS, FUNDED_DAYS // BLOCK, rng)
        mae = t.get("mae")
        rs = opt.run(und, t["gross"], risk_pts, di, n, e1, f1, mae=mae)
        if not rs:
            continue
        top = sorted(rs, key=lambda r: -r.ev)[:STAGE2_TOP]
        e2 = block_starts(n, days, d3y, d6m, STAGE2_SIMS, EVAL_DAYS // BLOCK, rng)
        f2 = block_starts(n, days, d3y, d6m, STAGE2_SIMS, FUNDED_DAYS // BLOCK, rng)
        fine = []
        for r in top:
            fine += opt.run(und, t["gross"], risk_pts, di, n, e2, f2, plans=[PLAN_BY_KEY[r.plan]], risks=[r.risk],
                            mae=mae)
        best = best_of(fine)
        # a lower-risk alternative: the best EV among combinations that bust at most SAFE_BUST of evaluations
        safe = None
        cands = sorted((r for r in rs if r.p_bust <= SAFE_BUST and r.ev > 0), key=lambda r: -r.ev)[:2]
        if cands and not (best.p_bust <= SAFE_BUST):
            sf = []
            for r in cands:
                sf += opt.run(und, t["gross"], risk_pts, di, n, e2, f2, plans=[PLAN_BY_KEY[r.plan]], risks=[r.risk],
                              mae=mae)
            safe = best_of(sf)
        blind = _blind(opt, und, t, risk_pts, di, days, d6m, mae, rng)
        per_plan = {}
        for r in rs:
            if r.plan not in per_plan or r.ev > per_plan[r.plan].ev:
                per_plan[r.plan] = r
        curve = [r for r in rs if r.plan == best.plan]
        out[sid] = {"best": best.__dict__, "safe": safe.__dict__ if safe else None, "blind": blind,
                    "plans": [per_plan[p].__dict__ for p in per_plan],
                    "curve": [[r.risk, r.ev, r.p_pass, r.p_bust, r.p_payout] for r in curve]}
        if k and k % 500 == 0:
            print(f"[accounts] {feed}: {k}/{len(items)} ({time.time() - t0:.0f}s)", flush=True)
    print(f"[accounts] {feed}: {len(out)} strategies in {time.time() - t0:.0f}s", flush=True)
    return out


def _blind(opt: "Optimiser", und: str, t: dict, risk_pts: np.ndarray, di: np.ndarray, days: np.ndarray,
           d6m: int, mae, rng) -> Optional[dict]:
    """Blind test: choose plan and risk from data up to six months ago, then replay the last six months.

    The search is the same as the main one (every plan x every risk, recency weights measured from the
    cut-off) but sees only days before it.  The replay then starts an evaluation on the first day of
    the last six months and walks the real calendar forward, one attempt, no resampling.
    """
    n = days.size
    pos6 = int(np.searchsorted(days, d6m))
    pre = (di >= 0) & (di < pos6)
    if pos6 < 260 or n - pos6 < 20 or pre.sum() < MIN_TRADES:
        return None
    eb = block_starts(pos6, days[:pos6], d6m - 1096, d6m - 183, BLIND_SIMS, EVAL_DAYS // BLOCK, rng)
    fb = block_starts(pos6, days[:pos6], d6m - 1096, d6m - 183, BLIND_SIMS, FUNDED_DAYS // BLOCK, rng)
    rp = opt.run(und, t["gross"], risk_pts, np.where(pre, di, -1), n, eb, fb, mae=mae)
    bp = best_of(rp)
    if bp is None:
        return None
    r = opt.run(und, t["gross"], risk_pts, di, n, eb[:1], fb[:1], plans=[PLAN_BY_KEY[bp.plan]],
                risks=[bp.risk], mae=mae, seq_start=pos6)[0]
    outcome = 1 if r.p_pass > 0 else (-1 if r.p_bust > 0 else 0)
    return {"plan": bp.plan, "risk": bp.risk, "ev": bp.ev, "outcome": outcome, "days": r.days_pass,
            "paid": r.paid, "cost": r.cost, "net": r.paid - r.cost, "f_bust": r.f_bust}


def _load_one(path: str) -> Dict[str, Dict[str, np.ndarray]]:
    z = np.load(path)
    sid = z["sid"]
    order = np.argsort(sid, kind="stable")
    sid = sid[order]
    cut = np.flatnonzero(np.concatenate(([True], sid[1:] != sid[:-1]))) if sid.size else np.array([], int)
    ends = np.append(cut[1:], sid.size)
    cols = {k: z[k][order] for k in ("day", "gross", "cost", "mae") if k in z.files}
    return {str(sid[a]): {k: v[a:b] for k, v in cols.items()} for a, b in zip(cut, ends)}


def optimise_all(strategies, markets, trades_dir: str, workers: int = 4) -> Dict[str, dict]:
    """Best account for every strategy with at least MIN_TRADES trades, feeds spread over processes."""
    from collections import defaultdict
    from concurrent.futures import ProcessPoolExecutor, as_completed
    by_feed = defaultdict(list)
    for s in strategies:
        by_feed[markets[s.market].feed].append((s.sid, s.market))
    cost_rt = {k: m.cost_rt for k, m in markets.items()}
    out: Dict[str, dict] = {}
    if workers <= 1:
        for feed, items in by_feed.items():
            out.update(optimise_feed(feed, items, trades_dir, cost_rt))
        return out
    with ProcessPoolExecutor(workers) as ex:
        futs = [ex.submit(optimise_feed, feed, items, trades_dir, cost_rt) for feed, items in by_feed.items()]
        for f in as_completed(futs):
            out.update(f.result())
    return out
