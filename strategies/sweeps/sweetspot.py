"""Where the breakout bot earns the most on each funded account without losing it too often.

    python strategies/sweeps/sweetspot.py

funded.py found two ends: one MNQ from the first day earns, but the account
is often lost within weeks; sizing off a quarter or a third of the room
above the limit keeps the account, but earns slowly.  This script walks the
whole range in between and prices it in the dollars that reach the owner:
payouts after the firm's split, minus the fee for every challenge bought.

The bot is bot A (the noise-area breakout with its 0.30% stop), NQ's signal
traded in 1 MYM, 1 MES or 1-10 MNQ (never more micros than the firm allows).
Each morning the size is the largest whose bad day (its 1-in-100 daily loss
in 2013-2019) is at most a share of the room above the limit, and never less
than 1 MYM.  A small share is safe and slow; a share above 1 lets one bad day
take the account.  The challenge and the funded account get their own share:
a lost challenge costs a fee, a lost funded account costs its payouts.

A room guard can sit on top: flatten and stop for the day once the day's
loss (open trades included) reaches a set share of the morning's room, so no
single day can take the account.  It is tried off, at half the room and at
80% of it.  The day's lowest point on one-minute bars (each bar's worst
price) says whether it was reached, and the day is booked at the guard, as a
resting stop would fill.

An account whose room has fallen below one MYM stop (0.30% of an MYM plus a
round trip's costs, about $80) is counted as lost: it cannot take a normal
trade any more.  Without this a guarded account never dies; it shrinks by
halves toward nothing.

The rules are evotrader/accounts.py.  Payouts: once the funded account has
the firm's winning days since its last payout, the profit above a cushion of
room is withdrawn, up to the firm's share of the profit and its cap; the
limit locks at the start after the first payout, as both firms do.  The
cushion is one loss limit (the room a fresh account has) or two (the size
can grow, but more is at stake).  Money left in the account at the end is
not counted.

Three replays from every fifth session:

* the challenge alone, for a year: passed, lost, or still going;
* a funded account alone, for a year: lost within three months or a year,
  and paid out;
* two years as they would be lived: a challenge, the funded account once it
  passes, and a new challenge (and its fee) after every loss.  Net is the
  owner's share of the payouts minus every fee, shown a year.  Two years,
  because a slow challenge leaves a one-year window almost no funded time.
  Starts need two years of data after them: 2013-2019 and 2020 to
  September 2024 (the last 2018-2019 starts run into 2020-2021).

The sweet spot, set before looking at 2020-2025: of the settings whose
funded account was lost within three months at most 5% of the time and
within a year at most 20% on 2013-2019 starts, the one with the highest
average net a year on those starts.  Written to sweetspot.json.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import funded                                                                # noqa: E402
from evotrader import accounts                                               # noqa: E402
from evotrader.accounts import Account                                       # noqa: E402

STOP = 0.003
HORIZON = 252
CAREER = 504                                                                  # two years
EVERY = 5
SHARES = (0.15, 0.25, 0.35, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
GUARDS = (0.0, 0.5, 0.8)                                                      # 0 = no room guard
CUSHIONS = (1.0, 2.0)                                                         # room kept after a payout, in limits
MAX_MNQ = 10
RISK_3M, RISK_1Y = 0.05, 0.20
FIXED = ("1 MES", "1 MNQ", "2 MNQ", "3 MNQ", "5 MNQ")                         # sizes held from the first day


def ladder(days: dict, dev: np.ndarray, max_micros: int) -> list:
    """The sizes, smallest bad day first: (name, $ a session, lowest point a session, bad day)."""
    out = []
    for c, n in [("MYM", 1), ("MES", 1)] + [("MNQ", k) for k in range(1, MAX_MNQ + 1)]:
        if n > max_micros:
            continue
        pnl, low = days[c]
        bad = -float(np.quantile(np.minimum(low, pnl)[dev & (low < 0)], 0.01)) * n
        out.append((f"{n} {c}", pnl * n, low * n, bad))
    return sorted(out, key=lambda x: x[3])


def simulate(rungs: list, acc: Account, starts, mode: str, share_c: float = 0.0, share_f: float = 0.0,
             fixed: Optional[int] = None, guard: float = 0.0, min_room: float = 0.0, cushion: float = 1.0,
             horizon: int = HORIZON) -> dict:
    """One account from every start, all at once.  mode: "challenge" (until passed or lost), "funded" (until
    lost) or "career" (challenges and funded accounts, a new challenge after every loss).  guard: the day stops
    once its loss reaches this share of the morning's room (0 = never).  min_room: an account with less room
    than this in the morning is lost.  cushion: a payout leaves this many loss limits of room."""
    P = np.array([r[1] for r in rungs])
    L = np.array([r[2] for r in rungs])
    bad = np.array([r[3] for r in rungs])
    starts = np.asarray(starts)
    S, ml = len(starts), acc.max_loss
    cap = acc.payout_cap or np.inf
    phase = np.full(S, 1 if mode == "funded" else 0)                         # 0 challenge, 1 funded
    bal, peak, best = np.zeros(S), np.zeros(S), np.zeros(S)
    floor = np.full(S, -ml)
    wins, in_ch = np.zeros(S, int), np.zeros(S, int)
    alive = np.ones(S, bool)
    event, when = np.full(S, 2), np.full(S, horizon)                         # 0 lost, 1 passed, 2 still going
    paid, take = np.zeros(S), np.zeros(S)
    fees = np.full(S, 0.0 if mode == "funded" else acc.challenge_fee)
    bought = np.full(S, 0 if mode == "funded" else 1)
    passes, lost_ch, lost_f = np.zeros(S, int), np.zeros(S, int), np.zeros(S, int)
    for n in range(horizon):
        k = starts + n
        if fixed is None:
            share = np.where(phase == 0, share_c, share_f)
            r = np.clip(np.searchsorted(bad, share * (bal - floor), side="right") - 1, 0, len(bad) - 1)
        else:
            r = np.full(S, fixed)
        p, lo = P[r, k], L[r, k]
        stop_at = np.full(S, np.inf)                                          # the day ends at the daily limit
        if acc.daily_loss:                                                    # or at the room guard
            stop_at = np.minimum(stop_at, acc.daily_loss)
        if guard:
            stop_at = np.minimum(stop_at, guard * (bal - floor))
        hit = lo <= -stop_at
        p = np.where(hit, -stop_at, p)
        lo = np.where(hit, -stop_at, lo)
        gone = alive & ((bal + lo <= floor) | (bal - floor < min_room))
        ok = alive & ~gone
        bal = np.where(ok, bal + p, bal)
        ch, fu = ok & (phase == 0), ok & (phase == 1)
        best = np.where(ch, np.maximum(best, p), best)
        passed = ch & (bal >= np.maximum(acc.target, best / acc.consistency))
        wins = np.where(fu & (p >= acc.payout_day_min), wins + 1, wins)
        peak = np.where(ok, np.maximum(peak, bal), peak)
        floor = np.where(ok, np.minimum(acc.lock_at, np.maximum(floor, peak - ml)), floor)
        # a payout: the profit above `cushion` limits of room over the lock level, up to the firm's share and cap
        # and at least its minimum; the floor locks for good
        keep = acc.lock_at + cushion * ml
        due = fu & (wins >= acc.payout_days) & (bal > keep)
        w = np.where(due, np.minimum(np.minimum(acc.payout_share * bal, bal - keep), cap), 0.0)
        due &= w >= max(acc.payout_min, 1e-9)
        w = np.where(due, w, 0.0)
        free = np.clip(acc.split_first - paid, 0.0, w) if acc.split_first else 0.0
        take += np.where(due, free + acc.split * (w - free), 0.0)
        paid += w
        bal -= w
        floor = np.where(due, acc.lock_at, floor)
        wins = np.where(due, 0, wins)
        in_ch = np.where(ch & ~passed, in_ch + 1, in_ch)
        if acc.monthly:                                                       # the challenge is billed monthly
            fees += np.where(ch & ~passed & (in_ch % accounts.SESSIONS_A_MONTH == 0), acc.challenge_fee, 0.0)
        if mode == "career":
            passes += passed
            lost_ch += gone & (phase == 0)
            lost_f += gone & (phase == 1)
            fees += np.where(passed, acc.activation_fee, 0.0) + np.where(gone, acc.challenge_fee, 0.0)
            bought += gone
            reset = gone | passed
            phase = np.where(passed, 1, np.where(gone, 0, phase))
            bal = np.where(reset, 0.0, bal)
            peak = np.where(reset, 0.0, peak)
            floor = np.where(reset, -ml, floor)
            best = np.where(reset, 0.0, best)
            wins = np.where(reset, 0, wins)
            in_ch = np.where(reset, 0, in_ch)
        else:
            end = gone | passed
            event = np.where(gone, 0, np.where(passed, 1, event))
            when = np.where(end, n + 1, when)
            alive &= ~end
    return {"event": event, "when": when, "take": take, "fees": fees, "net": take - fees, "bought": bought,
            "passes": passes, "lost_challenges": lost_ch, "lost_funded": lost_f, "left": bal}


def challenge_stats(res: dict) -> dict:
    e, w = res["event"], res["when"]
    return {"pass": round(float((e == 1).mean()), 3), "lost": round(float((e == 0).mean()), 3),
            "median_sessions_to_pass": float(np.median(w[e == 1])) if (e == 1).any() else None}


def funded_stats(res: dict) -> dict:
    e, w = res["event"], res["when"]
    return {"lost_3m": round(float(((e == 0) & (w <= 63)).mean()), 3), "lost_1y": round(float((e == 0).mean()), 3),
            "paid_a_year": round(float(res["take"].mean()), 0)}


def career_stats(res: dict, years: float = CAREER / 252) -> dict:
    """Two years lived, a year at a time: net, paid and fees a year; below zero is the two years' net."""
    net = res["net"]
    return {"net_a_year": round(float(net.mean() / years), 0), "net_median": round(float(np.median(net) / years), 0),
            "net_worst": round(float(net.min() / years), 0), "net_below_zero": round(float((net < 0).mean()), 3),
            "paid": round(float(res["take"].mean() / years), 0), "fees": round(float(res["fees"].mean() / years), 0),
            "challenges_bought": round(float(res["bought"].mean() / years), 2),
            "funded_lost": round(float(res["lost_funded"].mean() / years), 2)}


def study(acc: Account, days: dict, dates: np.ndarray, starts: dict, careers: dict, min_room: float) -> dict:
    dev_days = dates < funded.SPLIT
    rungs = ladder(days, dev_days, acc.max_micros)
    names = [r[0] for r in rungs]
    kw = {"min_room": min_room}
    out = {"rules": dataclasses.asdict(acc), "sizes": [{"size": r[0], "bad_day": round(r[3])} for r in rungs],
           "challenge": {}, "funded": {}, "career": {}, "fixed": {}}
    for part, ss in starts.items():
        cs = careers[part]
        for g in GUARDS:
            for s in SHARES:
                out["challenge"].setdefault(f"{s}|{g}", {})[part] = challenge_stats(
                    simulate(rungs, acc, ss, "challenge", s, s, guard=g, **kw))
                for c in CUSHIONS:
                    out["funded"].setdefault(f"{s}|{g}|{c}", {})[part] = funded_stats(
                        simulate(rungs, acc, ss, "funded", s, s, guard=g, cushion=c, **kw))
                    for sf in SHARES:
                        out["career"].setdefault(f"{s}/{sf}|{g}|{c}", {})[part] = career_stats(
                            simulate(rungs, acc, cs, "career", s, sf, guard=g, cushion=c, horizon=CAREER, **kw))
        for f in FIXED:
            if f not in names:
                continue
            i = names.index(f)
            out["fixed"].setdefault(f, {})[part] = {
                "challenge": challenge_stats(simulate(rungs, acc, ss, "challenge", fixed=i, **kw)),
                "funded": funded_stats(simulate(rungs, acc, ss, "funded", fixed=i, **kw)),
                "career": career_stats(simulate(rungs, acc, cs, "career", fixed=i, horizon=CAREER, **kw))}
    fund = lambda sf, g, c: out["funded"][f"{sf}|{g}|{c}"]["dev"]                   # noqa: E731
    safe = [(sf, g, c) for g in GUARDS for c in CUSHIONS for sf in SHARES
            if fund(sf, g, c)["lost_3m"] <= RISK_3M and fund(sf, g, c)["lost_1y"] <= RISK_1Y]
    net = lambda sc, sf, g, c: out["career"][f"{sc}/{sf}|{g}|{c}"]["dev"]["net_a_year"]  # noqa: E731
    cands = [(sc,) + x for sc in SHARES for x in safe]
    out["sweet_spot"] = list(max(cands, key=lambda x: net(*x))) if cands else None
    out["most_net"] = list(max(((sc, sf, g, c) for sc in SHARES for sf in SHARES for g in GUARDS for c in CUSHIONS),
                               key=lambda x: net(*x)))
    # the funded account's own frontier: for each share, the best guard and cushion by payouts on 2013-2019
    out["frontier"] = []
    for sf in SHARES:
        g, c = max(((g, c) for g in GUARDS for c in CUSHIONS), key=lambda x: fund(sf, *x)["paid_a_year"]
                   - 1e6 * (fund(sf, *x)["lost_1y"] > RISK_1Y))
        out["frontier"].append({"share": sf, "guard": g, "cushion": c,
                                "dev": out["funded"][f"{sf}|{g}|{c}"]["dev"], "test": out["funded"][f"{sf}|{g}|{c}"]["test"]})
    if out["sweet_spot"]:
        sc, sf, _, _ = out["sweet_spot"]
        out["table"] = [{"size": r[0], "bad_day": round(r[3]), "room_in_challenge": round(r[3] / sc),
                         "room_funded": round(r[3] / sf)} for r in rungs]
    return out


def _pct(x: float) -> str:
    return f"{x:4.0%}"


def report(acc: Account, o: dict) -> None:
    print(f"\n==== {acc.name}: ${acc.max_loss:,.0f} limit, ${acc.target:,.0f} target, "
          f"{'$%0.0f daily limit, ' % acc.daily_loss if acc.daily_loss else ''}{acc.max_micros} micros at most")
    print("  sizes and their bad days: " + ", ".join(f"{s['size']} ${s['bad_day']:,}" for s in o["sizes"]))
    print("  CHALLENGE  share|guard: passed/lost (median sessions to pass)   13-19 | 20-25")
    for key in (f"{s}|{g}" for g in GUARDS for s in SHARES):
        d, t = o["challenge"][key]["dev"], o["challenge"][key]["test"]
        print(f"    {key:9s} {_pct(d['pass'])}/{_pct(d['lost'])} ({d['median_sessions_to_pass'] or 0:4.0f}) | "
              f"{_pct(t['pass'])}/{_pct(t['lost'])} ({t['median_sessions_to_pass'] or 0:4.0f})")
    print("  FUNDED  share (best guard, cushion): lost within 3 months / a year, owner's payouts a year   13-19 | 20-25")
    for row in o["frontier"]:
        d, t = row["dev"], row["test"]
        print(f"    {row['share']:4.2f} (guard {row['guard']}, keep {row['cushion']:.0f} limit): {_pct(d['lost_3m'])}/"
              f"{_pct(d['lost_1y'])} ${d['paid_a_year']:6,.0f} | {_pct(t['lost_3m'])}/{_pct(t['lost_1y'])} "
              f"${t['paid_a_year']:6,.0f}")
    for name, x in o["fixed"].items():
        d, t = x["dev"]["funded"], x["test"]["funded"]
        print(f"    {name} held:                  {_pct(d['lost_3m'])}/{_pct(d['lost_1y'])} ${d['paid_a_year']:6,.0f} | "
              f"{_pct(t['lost_3m'])}/{_pct(t['lost_1y'])} ${t['paid_a_year']:6,.0f}")
    print("  TWO YEARS LIVED, a year at a time: net after fees (median, share of starts below zero, challenges a year)"
          "   13-19 | 20-24")
    for label, key in (("sweet spot", o["sweet_spot"]), ("most net", o["most_net"])):
        if not key:
            print(f"    {label}: nothing within the risk limits")
            continue
        sc, sf, g, c = key
        x = o["career"][f"{sc}/{sf}|{g}|{c}"]
        d, t = x["dev"], x["test"]
        print(f"    {label:10s} challenge {sc}, funded {sf}, guard {g}, keep {c:.0f} limit: ${d['net_a_year']:+7,.0f} "
              f"(median {d['net_median']:+,.0f}, {d['net_below_zero']:.0%}, {d['challenges_bought']:.1f}) | "
              f"${t['net_a_year']:+7,.0f} (median {t['net_median']:+,.0f}, {t['net_below_zero']:.0%}, "
              f"{t['challenges_bought']:.1f}; worst {t['net_worst']:+,.0f})")
    for name, x in o["fixed"].items():
        d, t = x["dev"]["career"], x["test"]["career"]
        print(f"    {name} held: ${d['net_a_year']:+7,.0f} (median {d['net_median']:+,.0f}, {d['net_below_zero']:.0%}, "
              f"{d['challenges_bought']:.1f}) | ${t['net_a_year']:+7,.0f} (median {t['net_median']:+,.0f}, "
              f"{t['net_below_zero']:.0%}, {t['challenges_bought']:.1f})")


def main() -> int:
    Ds = {inst: funded.data.load(inst) for inst in ("NQ", "ES", "YM")}
    level = {inst: float(D["C"][-1, -1]) for inst, D in Ds.items()}
    dates = np.array(Ds["NQ"]["dates"])
    nd = len(dates)
    trades = funded.trades_a(Ds["NQ"], STOP)
    days = {c: funded.by_day(funded.priced(trades, Ds, c, level), nd, "none") for c in funded.CONTRACTS}
    ok = np.arange(0, nd - HORIZON, EVERY)
    starts = {"dev": ok[dates[ok] < funded.SPLIT], "test": ok[dates[ok] >= funded.SPLIT]}
    ok2 = np.arange(0, nd - CAREER, EVERY)
    careers = {"dev": ok2[dates[ok2] < funded.SPLIT], "test": ok2[dates[ok2] >= funded.SPLIT]}
    # one MYM stop: 0.30% of an MYM plus commission both ways, a tick in and two out
    min_room = STOP * level["YM"] * 0.5 + 2 * funded.COMMISSION + 3 * 1.0 * 0.5
    print(f"{nd} NQ sessions to {dates[-1]}; {len(starts['dev'])} starts in 2013-2019, {len(starts['test'])} in "
          f"2020-{dates[ok[-1]][:4]} ({len(careers['test'])} with two years after them, to {dates[ok2[-1]]}); "
          f"bot A, 0.30% stop; MNQ ${level['NQ'] * 2:,.0f}, MES ${level['ES'] * 5:,.0f}, MYM ${level['YM'] * 0.5:,.0f} "
          f"of index; an account with less than ${min_room:.0f} of room is lost")
    out = {"data_to": str(dates[-1]), "risk_limits": {"lost_3m": RISK_3M, "lost_1y": RISK_1Y}, "min_room": min_room,
           "accounts": {}}
    for acc in accounts.ALL.values():
        o = study(acc, days, dates, starts, careers, min_room)
        report(acc, o)
        out["accounts"][acc.name] = o
    (HERE / "sweetspot.json").write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
