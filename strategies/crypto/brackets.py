"""Crypto with a fixed risk-to-reward bracket: risk 30% of the account to make 30% or 45%, at 1x, 2x and 3x.

    python strategies/crypto/brackets.py

The owner wants leveraged crypto with a risk-to-reward of 30:30 to 30:45.
study.py found that trend and breakout entries beat random timing on 29
coins, but its winners are rare and huge (the 50-day trend wins 1 trade in
5; winners average +485%, losers -5%).  This puts a bracket on the same
entries instead of the rules' own exits:

* entries: the 50-day trend (a close above the 50-day average, out of a
  position) and the 20-day breakout (a close above the highest close of the
  last 20 days), filled at the next day's open;
* exits: a stop 30% of the account below the fill and a target 30% or 45%
  above it, so at 2x the price stop is 15% and the targets 15% and 22.5%, at
  3x 10% and 10% or 15%; checked on each day's low and high (a day that
  reaches both is booked at the stop), otherwise held;
* the rules' own exits, unbracketed, at the same leverage, for comparison;
* leverage multiplies the price move (a futures or margin position, not a
  daily-reset fund); costs 10 bp a side times the leverage; a stop that gaps
  through fills at the open;
* random entries on the same coins with the same bracket and the same
  number of trades, 300 times: a bracket that makes money on random entries
  too is the market's drift, not the entry.

Per trade in account %: win rate, average, the share of coins where it made
money; and a book of the five study coins (AAVE, BNB, BTC, INJ, MSTR) with
$5,000 each, one position at a time per coin, compounding within the coin:
dollars a day on $25,000, the deepest fall, how many sleeves were wiped out
(down 90% or more).  2017-2020 and 2021-2026 shown apart.  Written to
brackets.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study as S                                                            # noqa: E402

RISK = 0.30
REWARDS = (0.30, 0.45)
LEVERAGE = (1.0, 2.0, 3.0)
SPLIT = "2021-01-01"
RANDOM = 200
SPAN = 400                                                                    # days a bracket may stay open
SLEEVE = 5_000.0


def entries(c: np.ndarray, kind: str) -> np.ndarray:
    """Days whose close gives an entry signal (the fill is the next open)."""
    pos = S.trend(c, 50) if kind == "trend 50" else S.breakout(c, 20, 10)
    prev = np.r_[0.0, pos[:-1]]
    return np.flatnonzero((pos == 1) & (prev == 0))


def rule_exit(c: np.ndarray, kind: str) -> np.ndarray:
    pos = S.trend(c, 50) if kind == "trend 50" else S.breakout(c, 20, 10)
    return pos


def bracket_trade(o, h, lo, i: int, lev: float, reward: float, cost: float):
    """Enter at the open of day i; exit at the account stop or target (a day reaching both is the stop; a stop
    gapped through fills at the open).  Still open after SPAN days: out at that day's open.  (exit day, account
    return), or None when the data ends first."""
    e = o[i]
    stop, target = e * (1 - RISK / lev), e * (1 + reward / lev)
    j = min(len(o), i + SPAN)
    hit_s, hit_t = lo[i:j] <= stop, h[i:j] >= target
    both = hit_s | hit_t
    if not both.any():
        if j == len(o):
            return None
        return j - 1, lev * (o[j - 1] / e - 1.0) - 2 * cost * lev
    k = int(np.argmax(both))
    t = i + k
    px = (o[t] if k > 0 and o[t] <= stop else stop) if hit_s[k] else target
    return t, lev * (px / e - 1.0) - 2 * cost * lev


def rule_trade(o, lo, pos, i: int, lev: float, cost: float):
    """Enter at the open of day i (signal on i-1); exit at the open after the rule's own exit signal.  A low
    that takes a leveraged position to zero on the way ends it at -100%."""
    for t in range(i, len(o) - 1):
        if pos[t] == 0:
            if lev * (lo[i:t + 2].min() / o[i] - 1.0) <= -1.0:
                return t + 1, -1.0
            return t + 1, max(lev * (o[t + 1] / o[i] - 1.0) - 2 * cost * lev, -1.0)
    return None


def coin(sym: str, kind: str, lev: float, reward, rng=None, n_random: int = 0) -> dict:
    """All trades on one coin, one at a time; reward None = the rule's own exit."""
    dates, o, h, lo, c = S.bars(sym)
    ds = np.array(dates)
    first = int(np.searchsorted(ds, S.START))
    cost = S.cost_bp(sym) * 1e-4
    sig = [i for i in entries(c, kind) if i >= first and i + 1 < len(o)]
    pos = rule_exit(c, kind)
    trades, busy = [], -1
    for i in sig:
        if i + 1 <= busy:
            continue
        res = bracket_trade(o, h, lo, i + 1, lev, reward, cost) if reward else rule_trade(o, lo, pos, i + 1, lev, cost)
        if res is None:
            break
        t_out, ret = res
        trades.append((dates[i + 1], dates[t_out], max(ret, -1.0), t_out - (i + 1)))
        busy = t_out
    out = {"trades": trades}
    if n_random and reward and trades:
        lo_i = max(first, 60)
        means = []
        for _ in range(n_random):
            rs, busy, k = [], -1, 0
            days = np.sort(rng.integers(lo_i, len(o) - 2, size=len(trades) * 3))
            for d in days:
                if k >= len(trades) or d <= busy:
                    continue
                res = bracket_trade(o, h, lo, int(d), lev, reward, cost)
                if res is None:
                    break
                rs.append(max(res[1], -1.0))
                busy, k = res[0], k + 1
            means.append(float(np.mean(rs)) if rs else 0.0)
        out["random_means"] = means
    return out


def stats(trades: list) -> dict:
    if not trades:
        return {"trades": 0}
    r = np.array([t[2] for t in trades])
    return {"trades": int(r.size), "win_rate": round(float((r > 0).mean()), 3), "mean_pct": round(float(r.mean() * 100), 2),
            "median_pct": round(float(np.median(r) * 100), 2), "avg_days": round(float(np.mean([t[3] for t in trades])), 1)}


def sleeve(trades: list) -> dict:
    """$5,000 compounding through the trades in order: where it ends, its deepest fall, and whether it was wiped out."""
    eq, peak, fall = SLEEVE, SLEEVE, 0.0
    for t in trades:
        eq *= 1 + t[2]
        peak = max(peak, eq)
        fall = min(fall, eq / peak - 1)
    return {"end": round(eq, 0), "deepest_fall_pct": round(fall * 100, 1), "wiped_out": bool(eq < SLEEVE * 0.1 or fall <= -0.9)}


def main() -> int:
    rng = np.random.default_rng(30)
    for sym in S.WIDE + ["MSTR"]:                                         # fetch, then drop bad first prints
        try:
            S.bars(sym)
        except Exception as e:
            print(f"  {sym}: {str(e)[:60]}")
            continue
        if S.clean_cache(sym):
            S.C._markets.clear()
    variants = [(kind, lev, rw) for kind in ("trend 50", "breakout 20/10") for lev in LEVERAGE for rw in REWARDS + (None,)]
    out = {}
    for kind, lev, rw in variants:
        name = f"{kind}, {lev:g}x, " + (f"risk 30% / reward {rw:.0%}" if rw else "the rule's own exit")
        allt, per_coin, rnd = [], {}, []
        for sym in S.WIDE:
            try:
                res = coin(sym, kind, lev, rw, rng, RANDOM if rw else 0)
            except Exception as e:                                            # a coin with too little history
                print(f"  {sym}: {str(e)[:60]}")
                continue
            allt += res["trades"]
            per_coin[sym] = stats(res["trades"])
            if "random_means" in res:
                rnd.append(np.array(res["random_means"]) * len(res["trades"]))
        a = [t for t in allt if t[0] < SPLIT]
        b = [t for t in allt if t[0] >= SPLIT]
        row = {"all": stats(allt), "2017-2020": stats(a), "2021-2026": stats(b),
               "coins_profitable": round(float(np.mean([v.get("mean_pct", 0) > 0 for v in per_coin.values()])), 3)}
        if rnd:
            rm = np.sum(rnd, axis=0) / max(len(allt), 1)
            real = np.mean([t[2] for t in allt])
            row["random_mean_pct"] = round(float(rm.mean() * 100), 2)
            row["edge_vs_random_pct"] = round(float((real - rm.mean()) * 100), 2)
            row["p_value_vs_random"] = round(float((rm >= real).mean()), 3)
        book = {}
        for sym in S.FIVE:
            try:
                tr = coin(sym, kind, lev, rw)["trades"]
            except Exception:
                continue
            book[sym] = {**sleeve(tr), "2021-2026": sleeve([t for t in tr if t[0] >= SPLIT])}
        row["five_sleeves"] = book
        out[name] = row
        s_all, s_a, s_b = row["all"], row["2017-2020"], row["2021-2026"]
        print(f"{name:52s} {s_all['trades']:5d} trades, win {s_all.get('win_rate', 0):.0%}, "
              f"avg {s_all.get('mean_pct', 0):+6.2f}% (17-20 {s_a.get('mean_pct', 0):+6.2f}%, 21-26 {s_b.get('mean_pct', 0):+6.2f}%), "
              f"coins up {row['coins_profitable']:.0%}"
              + (f"; random {row['random_mean_pct']:+.2f}%, edge {row['edge_vs_random_pct']:+.2f}% (p {row['p_value_vs_random']})"
                 if "random_mean_pct" in row else "")
              + "; five sleeves wiped out: " + str(sum(v["wiped_out"] for v in book.values())), flush=True)
    (HERE / "brackets.json").write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
