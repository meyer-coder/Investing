"""The crypto trend book on a FundedNext Stellar 2-Step CFD account, 2021 on.

    python strategies/crypto/fundednext.py

The owner can trade crypto on FundedNext's CFD accounts.  From FundedNext's
own pages (checked 2026-09-25):

* the crypto CFDs: BTC, ETH, XRP, LTC, ADA, DOGE, XLM, LINK and XMR (the
  help centre lists the nine), all at 1:1 leverage, 0.04% commission;
* they trade Monday to Friday only; positions may be held overnight and over
  the weekend (a swap is charged, three times on Friday);
* Stellar 2-Step: 8% then 5% to pass, a daily loss limit of 5% of the
  initial balance (open trades included, reset each day), a static maximum
  loss of 10% of the initial balance, 5 trading days, 80% to the trader,
  first payout after 21 days and then every 14; at most $300,000 across all
  Stellar accounts.  Fees from a third-party review of FundedNext's page:
  $549.99 for $100K, $1,099.99 for $200K.

The book is study.py's rules on the nine coins, equal weight, with or without
holding nothing while Bitcoin is below its 200-day average.  Positions change
only when the fill day is a weekday; weekend signals wait for Monday's open.
Exposure is a share f of the initial balance (1:1, so f <= 1): at f = 0.3 a
$100K account holds at most $30,000 of crypto.  Costs: the 0.04% commission
plus an assumed 0.05% spread a side.  The swap is not published per symbol
on the pages read; the replay runs without it and again with 10% a year on
the crypto held, charged daily and three times on Fridays.

Each day's loss check uses every coin's low of the day at once (a cautious
bound).  Accounts start every fifth day; a year lived from each start:
challenge (both phases), funded account with payouts of everything above the
starting balance (80% to the owner), and a new challenge and fee after every
breach.  The book and f are chosen on starts in 2021-2023 and shown on starts
from 2024 (to September 2025, a year of data after each).  Written to
fundednext.json.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study as S                                                            # noqa: E402
import importlib.util                                                        # noqa: E402

# strategies/top5 (on the path through study.py) has its own book.py: load this folder's by its file
_spec = importlib.util.spec_from_file_location("crypto_book", HERE / "book.py")
BK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BK)

COINS = ["BTC-USD", "ETH-USD", "XRP-USD", "LTC-USD", "ADA-USD", "DOGE-USD", "XLM-USD", "LINK-USD", "XMR-USD"]
START, SPLIT = "2021-01-01", "2024-01-01"
FRACTIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0)
RULES = ("trend 20", "trend 50", "trend 100", "breakout 20/10", "breakout 55/20")
COST = 0.0004 + 0.0005
ACCOUNT, FEE = 100_000.0, 549.99
TARGETS, DAILY, MAX_LOSS, SPLIT_PCT = (0.08, 0.05), 0.05, 0.10, 0.80
FIRST_PAYOUT, EVERY_PAYOUT, HORIZON, STEP = 21, 14, 365, 5


def series(rule: str, regime: bool, swap: float):
    """The book's daily return and the day's worst point, at full exposure, on the calendar from START."""
    BK.COINS = COINS
    cal, syms, O, C = BK.panel()
    H, L = np.full_like(O, np.nan), np.full_like(O, np.nan)
    ix = {d: i for i, d in enumerate(cal)}
    for j, sym in enumerate(syms):
        dates, o, h, lo, c = S.bars(sym)
        for d, hh, ll in zip(dates, h, lo):
            if d in ix:
                H[ix[d], j], L[ix[d], j] = hh, ll
    P = BK.positions(C, BK.RULES[rule])
    n, k = O.shape
    weekday = np.array([dt.date.fromisoformat(d).weekday() < 5 for d in cal])
    live = ~np.isnan(C) & (np.cumsum(~np.isnan(C), axis=0) > 365)
    btc = syms.index("BTC-USD")
    if regime:
        b = C[:, btc]
        m = S.sma(np.nan_to_num(b, nan=np.nanmean(b)), 200)
        P = P * (~np.isnan(m) & (b > m))[:, None]
    r, low = np.zeros(n), np.zeros(n)
    w_prev = np.zeros(k)
    for t in range(1, n - 1):
        s = t - 1
        if weekday[t]:                                                          # a weekday open: the book may change
            m = live[s]
            w = np.where(m, 1.0 / max(m.sum(), 1), 0.0) * P[s] if m.any() else np.zeros(k)
        else:
            w = w_prev
        day = np.nan_to_num(O[t + 1] / O[t] - 1.0)
        worst = np.nan_to_num(np.minimum(L[t] / O[t] - 1.0, day))
        fee = COST * float(np.abs(w - w_prev).sum())
        carry = swap / 365 * float(w.sum()) * (3 if dt.date.fromisoformat(cal[t]).weekday() == 4 else
                                               (0 if not weekday[t] else 1))
        r[t] = float(w @ day) - fee - carry
        low[t] = float(w @ worst) - fee - carry
        w_prev = w
    keep = np.array(cal) >= START
    return list(np.array(cal)[keep]), r[keep], low[keep]


def life(r, low, s: int, f: float) -> dict:
    """A year from day s: challenge phases, funded payouts, a new challenge (and fee) after every breach."""
    phase, bal, day_n, since, paid, fees, bought, breaches, passes = 0, 0.0, 0, 0, 0.0, FEE, 1, 0, 0
    end = min(len(r), s + HORIZON)
    for t in range(s, end):
        pnl, worst = f * ACCOUNT * r[t], f * ACCOUNT * low[t]
        if worst <= -DAILY * ACCOUNT or bal + worst <= -MAX_LOSS * ACCOUNT:
            breaches += 1
            fees += FEE
            bought += 1
            phase, bal, day_n, since = 0, 0.0, 0, 0
            continue
        bal += pnl
        day_n += 1
        if phase < 2:
            if day_n >= 5 and bal >= TARGETS[phase] * ACCOUNT:
                phase, bal, day_n, since = phase + 1, 0.0, 0, 0
                passes += phase == 2
        else:
            since += 1
            due = since == FIRST_PAYOUT or (since > FIRST_PAYOUT and (since - FIRST_PAYOUT) % EVERY_PAYOUT == 0)
            if due and bal > 0:
                paid += SPLIT_PCT * bal
                bal = 0.0
    return {"net": paid - fees, "paid": paid, "fees": fees, "bought": bought, "breaches": breaches, "funded": passes}


def summarize(res: list) -> dict:
    net = np.array([x["net"] for x in res])
    return {"net_a_year": round(float(net.mean()), 0), "net_median": round(float(np.median(net)), 0),
            "below_zero": round(float((net < 0).mean()), 3), "challenges_bought": round(float(np.mean([x["bought"] for x in res])), 2),
            "reached_funded": round(float(np.mean([x["funded"] > 0 for x in res])), 3),
            "paid": round(float(np.mean([x["paid"] for x in res])), 0)}


def main() -> int:
    out = {}
    for rule, regime, swap in itertools.product(RULES, (False, True), (0.0, 0.10)):
        cal, r, low = series(rule, regime, swap)
        ds = np.array(cal)
        dev = [i for i in range(0, len(r) - HORIZON, STEP) if ds[i] < SPLIT]
        test = [i for i in range(0, len(r) - HORIZON, STEP) if ds[i] >= SPLIT]
        a, b = ds < SPLIT, ds >= SPLIT
        base = {"book_usd_per_day_100k_full": {"2021-2023": round(float(r[a].mean() * ACCOUNT), 1),
                                                 "2024-2026": round(float(r[b].mean() * ACCOUNT), 1)},
                "worst_day_pct": round(float(low.min() * 100), 1)}
        eq = np.cumprod(1 + r)
        base["deepest_fall_pct"] = round(float((eq / np.maximum.accumulate(eq) - 1).min() * 100), 1)
        for f in FRACTIONS:
            name = f"{rule}{', BTC above its 200-day' if regime else ''}, swap {swap:.0%}, exposure {f:.0%}"
            out[name] = {**base, "dev": summarize([life(r, low, s, f) for s in dev]),
                         "test": summarize([life(r, low, s, f) for s in test])}
            d, t = out[name]["dev"], out[name]["test"]
            print(f"{name:62s} dev net ${d['net_a_year']:+8,.0f} (med {d['net_median']:+,.0f}, <0 {d['below_zero']:.0%}, "
                  f"{d['challenges_bought']:.1f} ch, funded {d['reached_funded']:.0%}) | test ${t['net_a_year']:+8,.0f} "
                  f"(med {t['net_median']:+,.0f}, <0 {t['below_zero']:.0%}, {t['challenges_bought']:.1f} ch, funded {t['reached_funded']:.0%})",
                  flush=True)
    swap10 = {k: v for k, v in out.items() if "swap 10%" in k}
    pick = max(swap10, key=lambda k: swap10[k]["dev"]["net_median"])
    out["_picked_on_2021_2023"] = pick
    print(f"\npicked on 2021-2023 starts (median net a year, with the 10% swap): {pick}\n{json.dumps(out[pick], indent=1)}")
    (HERE / "fundednext.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
