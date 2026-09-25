"""Hunting intraday edges across the CME markets Topstep allows, with a fixed
protocol, so that what survives can be stacked on one account.

Markets (Dukascopy one-minute CFDs, research/duka.py) and the micro contract
each is priced as, at the 2026-09-25 close:

    Nasdaq-100 (MNQ), S&P 500 (MES), Dow (MYM), Russell 2000 (M2K),
    gold (MGC), crude (MCL), natural gas (MNG), euro (M6E), pound (M6B),
    yen (micro JPY/USD), Australian dollar (M6A), Canadian dollar
    (micro CAD/USD), US T-bond (ZB, full size)

Sessions (New York time, fixed from each market's structure, not tuned):
indices 09:30-16:00; crude and gas 09:00-16:00; gold, bond and currencies
08:30-16:00.  Everything is flat by 15:55.

Four families, four variants each (16 per market):

* noise    the noise-area breakout (Bot A): a band from how far the price
           usually is from the session open at each minute (14 sessions);
           a check's close outside it enters at the next open; out when a
           check's close is back inside or across the session's average
           price, at a resting stop, or at 15:55.  Checks every 30 or 60
           minutes; stop 0.25 or 0.5 x the average daily range.
* orb      opening-range breakout: the range of the first 15, 30 or 60
           minutes; the first one-minute close beyond it before 12:00
           enters, held to 15:55; stop at the other side of the range or at
           its middle (the 15- and 60-minute ranges with the far stop, the
           30-minute range with both, and the 60-minute with the middle).
* momentum the first half hour predicts the last: the return from the
           previous close (or from the session open) to 30 minutes in; the
           same side is taken from 15:30 to 15:55.  Two variants, plus the
           same pair with the signal from the session open to noon.
* gap      the move from the previous close to the session open, when bigger
           than half the average daily range: followed or faded, out after
           60 minutes or at 15:55, with a stop at half the average daily range.

Protocol, fixed before any result: search on data up to 2019 (a variant
survives with 100+ trades, a positive mean and t >= 2.0); confirm on
2020-2022 (positive, and its direction calls beat at least 90% of 2,000
random sign flips of the same trades); one final look at 2023-2026.
Costs: the micro contract's commission ($1.22) plus a tick of slippage on
each side, as a share of today's contract value.

    python research/edges.py            # every market with cached data
    python research/edges.py XAU/USD    # one market
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duka import NASDAQ, cache_dir, sessions as duka_sessions  # noqa: E402

FLAT = 15 * 60 + 55
SEARCH_END, CONFIRM_END = "2019-12-31", "2022-12-31"


@dataclass(frozen=True)
class Market:
    key: str               # Dukascopy instrument
    contract: str          # the CME contract it is traded as
    session_start: int     # minutes since midnight, New York
    price: float           # contract's underlying price at the 2026-09-25 close
    multiplier: float      # $ per point of that price
    tick: float            # tick size in points
    invert: bool = False   # Dukascopy quotes USD/JPY and USD/CAD; the futures are JPY/USD and CAD/USD
    rolls: bool = False    # commodity CFDs roll between futures months
    commission: float = 1.22

    @property
    def notional(self) -> float:
        return self.price * self.multiplier

    @property
    def cost(self) -> float:
        """Round-trip cost as a share of the contract's value."""
        return (self.commission + 2 * self.tick * self.multiplier) / self.notional


MARKETS = [
    Market(NASDAQ, "MNQ", 570, 30_921.75, 2.0, 0.25),
    Market("USA500.IDX/USD", "MES", 570, 7_805.75, 5.0, 0.25),
    Market("USA30.IDX/USD", "MYM", 570, 52_180.0, 0.5, 1.0),
    Market("USSC2000.IDX/USD", "M2K", 570, 2_859.90, 5.0, 0.1),
    Market("XAU/USD", "MGC", 510, 4_320.5, 10.0, 0.1),
    Market("LIGHT.CMD/USD", "MCL", 540, 92.44, 100.0, 0.01, rolls=True),
    Market("GAS.CMD/USD", "MNG", 540, 3.251, 1_000.0, 0.001, rolls=True),
    Market("EUR/USD", "M6E", 510, 1.14285, 12_500.0, 0.0001),
    Market("GBP/USD", "M6B", 510, 1.3251, 6_250.0, 0.0001),
    Market("USD/JPY", "MJY", 510, 0.006398, 1_250_000.0, 0.000001, invert=True),
    Market("AUD/USD", "M6A", 510, 0.70165, 10_000.0, 0.0001),
    Market("USD/CAD", "MCD", 510, 0.70975, 10_000.0, 0.0001, invert=True),
    Market("USTBOND.TR/USD", "ZB", 510, 104.6875, 1_000.0, 1 / 32, commission=3.78),
]
BY_KEY = {m.key: m for m in MARKETS}


@dataclass
class Trade:
    day: str
    side: int
    entry: int          # minute index in the session
    exit: int
    gross: float        # side x (exit / entry - 1)
    worst: float        # worst open gross return during the trade (<= 0)


# ------------------------------------------------------------------- data

def load(m: Market) -> Dict[str, np.ndarray]:
    """days x minutes arrays for the session, missing minutes carried forward."""
    ss = duka_sessions(1, instrument=m.key, session=(m.session_start, 16 * 60),
                       max_jump_pct=0.02 if m.rolls else None)
    T = 16 * 60 - m.session_start
    n = len(ss)
    O, H, L, C = (np.full((n, T), np.nan) for _ in range(4))
    for d, s in enumerate(ss):
        k = (s.minute - m.session_start).astype(int)
        ok = (k >= 0) & (k < T)
        o, h, lo, c = s.open[ok], s.high[ok], s.low[ok], s.close[ok]
        if m.invert:
            o, h, lo, c = 1 / o, 1 / lo, 1 / h, 1 / c
        O[d, k[ok]], H[d, k[ok]], L[d, k[ok]], C[d, k[ok]] = o, h, lo, c
        for j in range(T):
            if np.isnan(C[d, j]):
                prev = C[d, j - 1] if j else O[d, np.flatnonzero(~np.isnan(O[d]))[0]]
                O[d, j] = H[d, j] = L[d, j] = C[d, j] = prev
    dates = np.array([s.date for s in ss])
    pc = np.r_[np.nan, C[:-1, -1]]
    rng = (H.max(axis=1) - L.min(axis=1)) / O[:, 0]
    adr = np.full(n, np.nan)                               # average daily range, prior 14 sessions
    for d in range(14, n):
        adr[d] = rng[d - 14:d].mean()
    return {"dates": dates, "O": O, "H": H, "L": L, "C": C, "pc": pc, "adr": adr, "T": T,
            "start": m.session_start}


def minute_of(D, clock: int) -> int:
    """Session index of a New York clock minute."""
    return clock - D["start"]


# ----------------------------------------------------------------- exits

def run_to(D, d: int, side: int, k0: int, stop_level: Optional[float], k_end: int,
           price: Optional[float] = None) -> Tuple[int, float, float]:
    """Hold from the open of minute k0 (or ``price``) until the stop or the
    open of minute ``k_end``; returns (exit minute, gross, worst)."""
    O, H, L = D["O"][d], D["H"][d], D["L"][d]
    entry = O[k0] if price is None else price
    seg_lo, seg_hi = L[k0:k_end], H[k0:k_end]
    if stop_level is not None:
        hit = (seg_lo <= stop_level) if side > 0 else (seg_hi >= stop_level)
        j = int(np.argmax(hit)) if hit.any() else -1
        if j >= 0:
            k = k0 + j
            px = stop_level if k == k0 else (min(O[k], stop_level) if side > 0 else max(O[k], stop_level))
            worst_seg = seg_lo[:j + 1].min() if side > 0 else seg_hi[:j + 1].max()
            worst = min(0.0, side * (worst_seg / entry - 1), side * (px / entry - 1))
            return k, side * (px / entry - 1), worst
    exit_px = O[k_end] if k_end < D["T"] else D["C"][d, -1]
    worst_px = seg_lo.min() if side > 0 else seg_hi.max()
    return k_end, side * (exit_px / entry - 1), min(0.0, side * (worst_px / entry - 1))


# -------------------------------------------------------------- families

def noise(D, every: int, stop_mult: float) -> List[Trade]:
    O, H, L, C, pc, T = D["O"], D["H"], D["L"], D["C"], D["pc"], D["T"]
    dist = np.abs(C / O[:, :1] - 1.0)
    flat_k = minute_of(D, FLAT)
    checks = [k for k in range(every - 1, flat_k - 1, every)]
    out = []
    for d in range(14, len(D["dates"])):
        if np.isnan(pc[d]) or np.isnan(D["adr"][d]):
            continue
        sig = dist[d - 14:d].mean(axis=0)
        up = max(O[d, 0], pc[d]) * (1 + sig)
        dn = min(O[d, 0], pc[d]) * (1 - sig)
        vwap = np.cumsum((H[d] + L[d] + C[d]) / 3) / np.arange(1, T + 1)
        stop_frac = stop_mult * D["adr"][d]
        k = 0
        ci = 0
        while ci < len(checks):
            t = checks[ci]
            if t < k:
                ci += 1
                continue
            c = C[d, t]
            side = 1 if c > up[t] else (-1 if c < dn[t] else 0)
            if not side:
                ci += 1
                continue
            k0 = t + 1
            entry = O[d, k0]
            stop = entry * (1 - side * stop_frac)
            # hold to the first later check whose close is back inside / across VWAP, or the stop
            exit_k = flat_k
            for t2 in checks[ci + 1:]:
                c2 = C[d, t2]
                if (side > 0 and c2 < max(up[t2], vwap[t2])) or (side < 0 and c2 > min(dn[t2], vwap[t2])):
                    exit_k = t2 + 1
                    break
            kx, g, w = run_to(D, d, side, k0, stop, exit_k)
            out.append(Trade(str(D["dates"][d]), side, k0, kx, g, w))
            k = kx
            ci += 1
            while ci < len(checks) and checks[ci] < kx:      # re-entry waits for a later check
                ci += 1
            if kx == exit_k and exit_k != flat_k:
                ci += 1                                     # the exit check itself does not re-enter
    return out


def orb(D, minutes: int, stop_at: str) -> List[Trade]:
    H, L, C = D["H"], D["L"], D["C"]
    flat_k, last_k = minute_of(D, FLAT), minute_of(D, 12 * 60)
    out = []
    for d in range(14, len(D["dates"])):
        hi, lo = H[d, :minutes].max(), L[d, :minutes].min()
        seg = C[d, minutes:last_k]
        brk = (seg > hi) | (seg < lo)
        if not brk.any():
            continue
        t = minutes + int(np.argmax(brk))
        side = 1 if C[d, t] > hi else -1
        stop = (lo if side > 0 else hi) if stop_at == "far" else (hi + lo) / 2
        kx, g, w = run_to(D, d, side, t + 1, stop, flat_k)
        out.append(Trade(str(D["dates"][d]), side, t + 1, kx, g, w))
    return out


def momentum(D, from_close: bool, signal_end: int) -> List[Trade]:
    O, C, pc = D["O"], D["C"], D["pc"]
    k_sig, k_in, flat_k = minute_of(D, signal_end), minute_of(D, 15 * 60 + 30), minute_of(D, FLAT)
    out = []
    for d in range(14, len(D["dates"])):
        base = pc[d] if from_close else O[d, 0]
        if np.isnan(base):
            continue
        r = C[d, k_sig - 1] / base - 1
        if r == 0:
            continue
        side = 1 if r > 0 else -1
        kx, g, w = run_to(D, d, side, k_in, None, flat_k)
        out.append(Trade(str(D["dates"][d]), side, k_in, kx, g, w))
    return out


def gap(D, follow: bool, hold_to_close: bool) -> List[Trade]:
    O, pc, adr = D["O"], D["pc"], D["adr"]
    flat_k = minute_of(D, FLAT)
    out = []
    for d in range(14, len(D["dates"])):
        if np.isnan(pc[d]) or np.isnan(adr[d]):
            continue
        g0 = O[d, 0] / pc[d] - 1
        if abs(g0) < 0.5 * adr[d]:
            continue
        side = (1 if g0 > 0 else -1) * (1 if follow else -1)
        entry = O[d, 1]
        stop = entry * (1 - side * 0.5 * adr[d])
        kx, g, w = run_to(D, d, side, 1, stop, flat_k if hold_to_close else 61)
        out.append(Trade(str(D["dates"][d]), side, 1, kx, g, w))
    return out


VARIANTS: List[Tuple[str, Callable]] = [
    ("noise 30m, stop 0.25 ADR", lambda D: noise(D, 30, 0.25)),
    ("noise 30m, stop 0.5 ADR", lambda D: noise(D, 30, 0.5)),
    ("noise 60m, stop 0.25 ADR", lambda D: noise(D, 60, 0.25)),
    ("noise 60m, stop 0.5 ADR", lambda D: noise(D, 60, 0.5)),
    ("orb 15m, far stop", lambda D: orb(D, 15, "far")),
    ("orb 30m, far stop", lambda D: orb(D, 30, "far")),
    ("orb 30m, mid stop", lambda D: orb(D, 30, "mid")),
    ("orb 60m, far stop", lambda D: orb(D, 60, "far")),
    ("orb 60m, mid stop", lambda D: orb(D, 60, "mid")),
    ("momentum close->30m", lambda D: momentum(D, True, D["start"] + 30)),
    ("momentum open->30m", lambda D: momentum(D, False, D["start"] + 30)),
    ("momentum close->noon", lambda D: momentum(D, True, 12 * 60)),
    ("gap follow, 60m", lambda D: gap(D, True, False)),
    ("gap follow, to close", lambda D: gap(D, True, True)),
    ("gap fade, 60m", lambda D: gap(D, False, False)),
    ("gap fade, to close", lambda D: gap(D, False, True)),
]


# ----------------------------------------------------------------- scoring

def score(trades: List[Trade], cost: float, lo: str, hi: str) -> Dict[str, float]:
    g = np.array([t.gross for t in trades if lo <= t.day <= hi])
    if len(g) < 2:
        return {"n": int(len(g)), "mean_bp": 0.0, "t": 0.0, "flip_pct": 0.0}
    net = g - cost
    t = float(net.mean() / (net.std(ddof=1) / np.sqrt(len(net))))
    rng = np.random.default_rng(11)
    flips = (rng.choice([-1.0, 1.0], size=(2000, len(g))) * np.abs(g)).mean(axis=1) - cost
    return {"n": int(len(g)), "mean_bp": float(net.mean() * 1e4), "t": t,
            "flip_pct": float(np.mean(flips < net.mean()) * 100)}


def evaluate(m: Market) -> List[dict]:
    D = load(m)
    rows = []
    for name, fn in VARIANTS:
        tr = fn(D)
        s = score(tr, m.cost, "0000", SEARCH_END)
        c = score(tr, m.cost, "2020-01-01", CONFIRM_END)
        f = score(tr, m.cost, "2023-01-01", "9999")
        passed_search = s["n"] >= 100 and s["mean_bp"] > 0 and s["t"] >= 2.0
        confirmed = passed_search and c["mean_bp"] > 0 and c["flip_pct"] >= 90
        rows.append({"market": m.key, "contract": m.contract, "variant": name, "cost_bp": m.cost * 1e4,
                     "sessions": int(len(D["dates"])), "first": str(D["dates"][0]),
                     "search": s, "confirm": c, "final": f,
                     "passed_search": passed_search, "confirmed": confirmed})
    return rows


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    markets = [BY_KEY[a] for a in argv] if argv else [m for m in MARKETS if os.path.isdir(cache_dir(m.key))]
    all_rows = []
    for m in markets:
        rows = evaluate(m)
        all_rows.extend(rows)
        print(f"\n== {m.contract} ({m.key}), {rows[0]['sessions']} sessions from {rows[0]['first']}, "
              f"cost {m.cost * 1e4:.2f} bp a round trip")
        for r in rows:
            s, c, f = r["search"], r["confirm"], r["final"]
            tag = "CONFIRMED" if r["confirmed"] else ("search ok" if r["passed_search"] else "")
            print(f"   {r['variant']:<26} search n={s['n']:>4} {s['mean_bp']:+6.2f}bp t={s['t']:+5.1f} | "
                  f"confirm n={c['n']:>4} {c['mean_bp']:+6.2f}bp flips {c['flip_pct']:3.0f}% | "
                  f"final n={f['n']:>4} {f['mean_bp']:+6.2f}bp t={f['t']:+5.1f}  {tag}")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edges.json")
    old = json.load(open(path)) if os.path.exists(path) else []
    keep = [r for r in old if r["market"] not in {m.key for m in markets}]
    json.dump(keep + all_rows, open(path, "w"), indent=1)
    n_pass = sum(r["passed_search"] for r in all_rows)
    n_conf = sum(r["confirmed"] for r in all_rows)
    print(f"\n{len(all_rows)} variants: {n_pass} passed the search (about {0.023 * len(all_rows):.0f} "
          f"would by luck), {n_conf} confirmed on 2020-2022.  Saved to {path}")


if __name__ == "__main__":
    main()
