"""The breakout bot inside a funded account's loss limit.

    python strategies/sweeps/funded.py

The owner's accounts are a FundedNext 25K and a Topstep 100K; their rules are
written down once, in evotrader/accounts.py.  Every firm's limit trails the
best end-of-day balance, locks at the starting balance, and ends the account
the moment a floating loss touches it.  Beyond that:

* FundedNext Legacy 25K: a $1,000 limit, a $1,250 challenge target with no
  day more than 40% of the profit, no daily loss limit;
* Topstep 100K: a $3,000 limit, a $6,000 Combine target with the best day at
  most 55% of the profit, and a $2,000 daily loss limit that ends the day
  there (it is optional; the replay keeps it on);
* FundedNext Legacy 50K, for comparison: the smallest FundedNext account
  with a $2,000 limit ($3,000 target, 40%);
* the challenge gets a year; the funded account has no target, and the
  question is how often it is lost within three, six and twelve months.

What each account earns after fees and payouts, and the sizing that earns
the most without losing the account too often, is sweetspot.py.

At one MNQ the noise-area breakout's ordinary losing stretches reach $5,678,
so the limit is hit often.  What is tried:

* the stop: 0.10%, 0.15%, 0.20% or the bot's own 0.30% from the entry;
* the contract: one MNQ, or the same NQ signal traded in one MES or one MYM,
  entered and closed on the NQ trade's minutes, with a resting stop the same
  share from its own entry; they carry about half and a third of an MNQ's
  dollar swings;
* a day rule: none, done for the day after the first losing trade, or one
  trade a day;
* the pre-market break (bot B) and both bots together, at their own stops;
* sizing off the room left above the limit: each morning, trade the largest
  of 1 MYM, 1 MES and 1-5 MNQ whose bad day (its 99th-percentile daily loss
  in 2013-2019) is no more than a share of the room, and never less than
  1 MYM.

Costs per contract: $0.75 a side, a tick of slippage on market fills and two
on stop fills (prop.py).  Trades are priced at today's index levels.  Accounts
start every fifth session.  Choices are made on accounts started in
2013-2019 and shown on accounts started in 2020-2025; each needs a year of
data after its start.  Written to funded.json.

The owner's settings (profitable-strategies/futures/breakout-bot/README.md):
the 0.30% stop, no day rule, and sizing off the room, a quarter of it on the
25K and a third on the 100K.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import data                                                                  # noqa: E402
import sweeps                                                                # noqa: E402
import trend                                                                 # noqa: E402
from evotrader import accounts                                               # noqa: E402

OPEN, T = data.OPEN, data.T
SPLIT = "2020-01-01"
CONTRACTS = {"MNQ": ("NQ", 2.0, 0.25), "MES": ("ES", 5.0, 0.25), "MYM": ("YM", 0.5, 1.0)}
COMMISSION = 0.75
#: name: (maximum loss, challenge target, best day's largest share of the profit, daily loss limit or 0)
ACCOUNTS = {a.name: (a.max_loss, a.target, a.consistency, a.daily_loss) for a in accounts.ALL.values()}
HORIZON = 252
EVERY = 5
STOPS = (0.001, 0.0015, 0.002, 0.003)
DAY_RULES = ("none", "first loss", "one trade")
SHARES = (0.15, 0.25, 0.35, 0.5)
PM_BREAK = {"mode": "break", "kind": "PM", "until": "11:30", "hold": 5, "target": None}


def trades_a(D: dict, stop: float) -> list:
    """Bot A's trades: (NQ day, side, entry column, exit column, why, gross NQ return, stop share)."""
    log: list = []
    trend.noise_days(bot_rth(D), hard_stop=stop, log=log)
    return [(i, side, OPEN + a, OPEN + b, why, net + 1e-4, stop) for i, side, a, b, net, why in log]


def trades_b(D: dict) -> list:
    out = [(i, side, e, u, why, net + sweeps.COST, None) for i, side, net, _, why, e, u, _ in sweeps.run(D, **PM_BREAK)]
    return sorted(out, key=lambda x: (x[0], x[2]))


def bot_rth(D: dict) -> dict:
    return {"O": D["O"][:, OPEN:], "H": D["H"][:, OPEN:], "L": D["L"][:, OPEN:], "C": D["C"][:, OPEN:], "pc": D["pc"]}


def priced(trades: list, Ds: dict, contract: str, level: dict) -> list:
    """Each trade in one contract at today's level: (NQ day, dollars, worst open dollars).

    In MES or MYM the NQ signal is followed: in on the NQ entry's minute, out on its exit (a band exit at the
    same open, an NQ stop at that minute's close, the close), and a resting stop the same share from the
    contract's own entry (for bot A) takes it out first if it is touched."""
    inst, pv, tick = CONTRACTS[contract]
    Dn, Dx = Ds["NQ"], Ds[inst]
    xmap = {d: k for k, d in enumerate(Dx["dates"])}
    notional = level[inst] * pv
    out = []
    for i, side, a, b, why, gross, stop in trades:
        j = i if inst == "NQ" else xmap.get(Dn["dates"][i])
        if j is None:
            continue
        O, H, L, C = Dx["O"][j], Dx["H"][j], Dx["L"][j], Dx["C"][j]
        entry = O[a]
        ticks_out = 2 if why == "stop" else 1
        if inst == "NQ":
            ret = gross
        else:
            ticks_out = 1                                                     # a market order on the NQ signal
            px = C[T - 1] if why == "close" else (C[b] if why == "stop" else O[b])
            if stop:
                stop_px = entry * (1 - side * stop)
                end = b if why in ("close", "stop") else b - 1
                seg = (L[a:end + 1] <= stop_px) if side > 0 else (H[a:end + 1] >= stop_px)
                hit = np.flatnonzero(seg)
                if hit.size:
                    k = a + hit[0]
                    px = stop_px if k == a else (min(O[k], stop_px) if side > 0 else max(O[k], stop_px))
                    why, b, ticks_out = "stop", k, 2
            ret = side * (px / entry - 1.0)
        # the bars held whole: up to the exit bar for a close or a target, before it for a band exit (filled at
        # its open) or a stop (the fill is the worst of its bar: a stop hit on the entry bar leaves none)
        last = b if why in ("close", "target") else b - 1
        seg = slice(a, last + 1)
        worst = 0.0 if last < a else \
            (L[seg].min() / entry - 1.0) if side > 0 else (1.0 - H[seg].max() / entry)
        cost_in = COMMISSION + tick * pv
        cost_out = COMMISSION + tick * pv * ticks_out
        out.append((i, ret * notional - cost_in - cost_out, min(worst, ret) * notional - cost_in))
    return out


def by_day(rows: list, nd: int, rule: str):
    """Per NQ session: the day's dollars and its lowest point, one contract, trades taken in order."""
    pnl, low = np.zeros(nd), np.zeros(nd)
    count, lost = np.zeros(nd, int), np.zeros(nd, bool)
    for i, p, w in rows:
        if (rule == "one trade" and count[i]) or (rule == "first loss" and lost[i]):
            continue
        low[i] = min(low[i], pnl[i] + w)
        pnl[i] += p
        low[i] = min(low[i], pnl[i])
        count[i] += 1
        lost[i] |= p < 0
    return pnl, low


def replay(pnl, low, s: int, max_loss: float, target: float, consistency: float, daily_loss: float,
           horizon: int = HORIZON):
    """One account from session s: (0 breach / 1 pass / 2 still going, sessions, dollars)."""
    return replay_ladder([(pnl, low, 0.0)], s, max_loss, target, consistency, daily_loss, 0.0, horizon)


def replay_ladder(rungs: list, s: int, max_loss: float, target: float, consistency: float, daily_loss: float,
                  share: float, horizon: int = HORIZON):
    """As replay, the size chosen each morning from the room above the limit.

    A daily loss limit closes the day where the day's P&L first reaches it, so the day's low and its close
    are both the limit (the bars say how low a day went, not in what order, so a day that dipped through the
    limit and recovered is booked at the limit)."""
    bal = peak = best = 0.0
    floor = -max_loss
    for n in range(horizon):
        k = s + n
        room = bal - floor
        r = 0
        while r + 1 < len(rungs) and rungs[r + 1][2] <= share * room:
            r += 1
        p, lo = rungs[r][0][k], rungs[r][1][k]
        if daily_loss and lo <= -daily_loss:
            p = lo = -daily_loss
        if bal + lo <= floor:
            return 0, n + 1, floor
        bal += p
        best = max(best, p)
        if target and bal >= max(target, best / consistency):
            return 1, n + 1, bal
        peak = max(peak, bal)
        floor = min(0.0, max(floor, peak - max_loss))
    return 2, horizon, bal


def odds(results: list) -> dict:
    res = np.array([r[0] for r in results])
    days = np.array([r[1] for r in results])
    usd = np.array([r[2] for r in results])
    out = {"pass": round(float((res == 1).mean()), 3), "breach": round(float((res == 0).mean()), 3),
           "open": round(float((res == 2).mean()), 3)}
    if (res == 1).any():
        out["median_days_to_pass"] = float(np.median(days[res == 1]))
    out["breach_3m"] = round(float(((res == 0) & (days <= 63)).mean()), 3)
    out["breach_6m"] = round(float(((res == 0) & (days <= 126)).mean()), 3)
    out["usd_a_session"] = round(float(np.mean(usd / days)), 1)
    return out


def account_odds(run, starts: dict) -> dict:
    """run(s, max_loss, target, consistency, daily_loss) for every account, challenge and funded, on dev and
    test starts."""
    out = {}
    for name, (max_loss, target, consistency, daily_loss) in ACCOUNTS.items():
        out[name] = {}
        for part, ss in starts.items():
            out[name][part] = {"challenge": odds([run(s, max_loss, target, consistency, daily_loss) for s in ss]),
                               "funded": odds([run(s, max_loss, 0.0, consistency, daily_loss) for s in ss])}
    return out


def score(o: dict, account: str, part: str = "dev") -> float:
    return o[account][part]["challenge"]["pass"] - o[account][part]["challenge"]["breach"]


def day_stats(dates: np.ndarray, pnl: np.ndarray, low: np.ndarray) -> dict:
    eq = np.cumsum(pnl)
    dev = dates < SPLIT
    return {"usd_day": round(float(pnl.mean()), 1), "dev_usd_day": round(float(pnl[dev].mean()), 1),
            "test_usd_day": round(float(pnl[~dev].mean()), 1), "worst_day": round(float(low.min()), 0),
            "worst_stretch": round(float((eq - np.maximum.accumulate(np.r_[0.0, eq])[1:]).min()), 0),
            "sharpe": round(float(pnl.mean() / (pnl.std() + 1e-12) * np.sqrt(252)), 2)}


def main() -> int:
    Ds = {inst: data.load(inst) for inst in ("NQ", "ES", "YM")}
    level = {inst: float(D["C"][-1, -1]) for inst, D in Ds.items()}
    dates = np.array(Ds["NQ"]["dates"])
    nd = len(dates)
    ok = [s for s in range(0, nd - HORIZON, EVERY)]
    starts = {"dev": [s for s in ok if dates[s] < SPLIT], "test": [s for s in ok if dates[s] >= SPLIT]}
    print(f"{nd} NQ sessions; accounts started every {EVERY}th: {len(starts['dev'])} in 2013-2019, "
          f"{len(starts['test'])} in 2020-{dates[ok[-1]][:4]}; today's MNQ ${level['NQ'] * 2:,.0f}, "
          f"MES ${level['ES'] * 5:,.0f}, MYM ${level['YM'] * 0.5:,.0f} of index")
    out = {"accounts": {k: dict(zip(("max_loss", "target", "consistency", "daily_loss"), v))
                        for k, v in ACCOUNTS.items()}, "fixed": {}, "ladder": {}}
    days = {}
    configs = [("A", stop, c, rule) for stop, c, rule in itertools.product(STOPS, CONTRACTS, DAY_RULES)]
    configs += [("B", None, c, rule) for c, rule in itertools.product(CONTRACTS, DAY_RULES)]
    tr_a = {stop: trades_a(Ds["NQ"], stop) for stop in STOPS}
    tr_b = trades_b(Ds["NQ"])
    for bot, stop, c, rule in configs:
        rows = priced(tr_a[stop] if bot == "A" else tr_b, Ds, c, level)
        days[(bot, stop, c, rule)] = by_day(rows, nd, rule)
    for c, rule in itertools.product(CONTRACTS, DAY_RULES):              # both bots, A at 0.30%
        pa, la = days[("A", 0.003, c, rule)]
        pb, lb = days[("B", None, c, rule)]
        days[("A+B", 0.003, c, rule)] = (pa + pb, la + lb)
        configs.append(("A+B", 0.003, c, rule))

    def name(cfg):
        bot, stop, c, rule = cfg
        return f"bot {bot}" + (f", stop {stop:.2%}" if bot == "A" else "") + f", 1 {c}, day rule: {rule}"

    print("\nOne contract, fixed.  $ a session, then for each account: challenge pass / breach "
          "(accounts started 2013-2019 | 2020-2025), and funded accounts lost within a year")
    for cfg in configs:
        pnl, low = days[cfg]
        st = day_stats(dates, pnl, low)
        pl, ll = pnl.tolist(), low.tolist()                                    # lists index faster in the loop
        o = account_odds(lambda s, m, t, c, dl: replay(pl, ll, s, m, t, c, dl), starts)
        out["fixed"][name(cfg)] = {"days": st, "odds": o}
    ranked = {}
    for acc in ACCOUNTS:
        ranked[acc] = sorted(out["fixed"], key=lambda k: -score(out["fixed"][k]["odds"], acc))
        base = name(("A", 0.003, "MNQ", "none"))
        print(f"\n-- {acc}: the bot as built, then the eight best on 2013-2019 starts")
        for k in [base] + [k for k in ranked[acc] if k != base][:8]:
            x = out["fixed"][k]
            d, o = x["days"], x["odds"][acc]
            print(f"  {k:52s} ${d['usd_day']:+6.1f} (13-19 {d['dev_usd_day']:+5.1f}, 20-26 {d['test_usd_day']:+5.1f}) "
                  f"worst day {d['worst_day']:+6.0f} stretch {d['worst_stretch']:+7.0f} | challenge "
                  f"{o['dev']['challenge']['pass']:.0%}/{o['dev']['challenge']['breach']:.0%} | "
                  f"{o['test']['challenge']['pass']:.0%}/{o['test']['challenge']['breach']:.0%} "
                  f"({o['test']['challenge'].get('median_days_to_pass', float('nan')):.0f} sessions) | funded lost in a year "
                  f"{o['dev']['funded']['breach']:.0%} | {o['test']['funded']['breach']:.0%}, "
                  f"${o['test']['funded']['usd_a_session']:+.1f} a session", flush=True)

    print("\nSizing off the room above the limit (1 MYM, 1 MES, 1-5 MNQ; the largest whose bad day fits the share)")
    dev_days = dates < SPLIT
    for bot, stop, rule in (("A", s, r) for s, r in itertools.product(STOPS[1:], DAY_RULES[:2])):
        rungs = []
        for c, n in (("MYM", 1), ("MES", 1), ("MNQ", 1), ("MNQ", 2), ("MNQ", 3), ("MNQ", 4), ("MNQ", 5)):
            pnl, low = days[(bot, stop, c, rule)]
            bad = -float(np.quantile(np.minimum(low, pnl)[dev_days & (low < 0)], 0.01)) * n
            rungs.append(((pnl * n).tolist(), (low * n).tolist(), bad))
        rungs.sort(key=lambda x: x[2])
        for share in SHARES:
            key = f"bot A, stop {stop:.2%}, day rule: {rule}, bad day <= {share:.0%} of the room"
            o = account_odds(lambda s, m, t, c, dl: replay_ladder(rungs, s, m, t, c, dl, share), starts)
            out["ladder"][key] = {"odds": o, "bad_days": [round(r[2]) for r in rungs]}
    for acc in ACCOUNTS:
        best = sorted(out["ladder"], key=lambda k: -score(out["ladder"][k]["odds"], acc))[:6]
        print(f"\n-- {acc}: the six best on 2013-2019 starts")
        for k in best:
            o = out["ladder"][k]["odds"][acc]
            print(f"  {k:66s} challenge {o['dev']['challenge']['pass']:.0%}/{o['dev']['challenge']['breach']:.0%} | "
                  f"{o['test']['challenge']['pass']:.0%}/{o['test']['challenge']['breach']:.0%} "
                  f"({o['test']['challenge'].get('median_days_to_pass', float('nan')):.0f} sessions) | funded lost in a year "
                  f"{o['dev']['funded']['breach']:.0%} | {o['test']['funded']['breach']:.0%} (3 months "
                  f"{o['test']['funded']['breach_3m']:.0%}), ${o['test']['funded']['usd_a_session']:+.1f} a session", flush=True)
    (HERE / "funded.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
