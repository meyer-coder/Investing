"""Where is the edge in five-to-ten-minute Nasdaq-100 futures trades?

    python strategies/mnq/edges.py islands        # expired NQ contracts, 2016-2026 (199 sessions)
    python strategies/mnq/edges.py duka 2024-01-01   # Dukascopy's Nasdaq-100, Sep 2020 on; dev before 2024, test after

For every regular-session minute and every candidate setup, the net result
of entering at the next minute's open and leaving at the open h minutes
later (h = 5, 7 or 10), long or short, less a round-trip cost.  Results are
in basis points of the index so that years at very different index levels
compare, and the cost is today's: 1.25 points on an index near 29,000
(0.43 bp), what one MNQ contract pays in commission and a tick of slippage
each way.  Entries only from 09:31 to 15:45 New York; every exit is inside
the same session, so nothing is ever held past the close.

Setups are judged on the early years (dev) and checked on the later ones
(test); a setup is worth a bot only if it holds in both, on most years, and
its mirror image does not do the same.
"""
from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import data                                                                  # noqa: E402

COST_BP = 1.25 / 29_000 * 1e4
HOLDS = (5, 7, 10)


def features(day: data.Day, prev: data.Day = None) -> Dict[str, np.ndarray]:
    o, h, l, c = day.o, day.h, day.l, day.c
    n = len(c)
    mins = np.array([(int(t[11:13]) * 60 + int(t[14:16])) for t in day.stamps])
    mso = mins - mins[0]                                   # minutes since the first bar (09:30)
    r1 = np.concatenate([[np.nan], c[1:] / c[:-1] - 1.0])
    r1[0] = c[0] / o[0] - 1.0                              # the first bar's own move, not the overnight gap
    if prev is not None:
        sd_prev = float(np.nanstd(prev.c[1:] / prev.c[:-1] - 1.0))
    else:
        sd_prev = float(np.nanstd(r1[1:]))
    # the typical one-minute move: yesterday's for the first half hour, then a rolling 30 minutes
    sd = np.full(n, sd_prev)
    for i in range(30, n):
        sd[i] = np.nanstd(r1[i - 29:i + 1])
    def ret(k):
        out = np.full(n, np.nan)
        out[k:] = c[k:] / c[:-k] - 1.0
        return out
    tp = (h + l + c) / 3.0
    twap = np.cumsum(tp) / np.arange(1, n + 1)
    hod = np.maximum.accumulate(h)
    lod = np.minimum.accumulate(l)
    prev_hod = np.concatenate([[np.nan], hod[:-1]])
    prev_lod = np.concatenate([[np.nan], lod[:-1]])
    day_ret = c / prev.c[-1] - 1.0 if prev is not None else np.full(n, np.nan)
    f = {"mso": mso.astype(float), "c": c, "r1": r1, "r5": ret(5), "r15": ret(15), "r30": ret(30), "day_ret": day_ret,
         "sd": sd, "ret_open": c / o[0] - 1.0, "twap_dist": c / twap - 1.0,
         "new_high": (c > prev_hod).astype(float), "new_low": (c < prev_lod).astype(float),
         "gap": np.full(n, (o[0] / prev.c[-1] - 1.0) if prev is not None else np.nan),
         "prev_high": np.full(n, prev.h.max() if prev is not None else np.nan),
         "prev_low": np.full(n, prev.l.min() if prev is not None else np.nan)}
    for k in (5, 15, 30):
        orh, orl = h[:k].max(), l[:k].min()
        f[f"orh{k}"] = np.where(mso >= k, orh, np.nan)
        f[f"orl{k}"] = np.where(mso >= k, orl, np.nan)
    below = (f["twap_dist"] < 0).astype(float)
    f["cross_up"] = np.concatenate([[0.0], ((below[:-1] == 1) & (below[1:] == 0)).astype(float)])
    f["cross_dn"] = np.concatenate([[0.0], ((below[:-1] == 0) & (below[1:] == 1)).astype(float)])
    return f


def first_true(mask: np.ndarray) -> np.ndarray:
    out = np.zeros_like(mask, dtype=bool)
    idx = np.flatnonzero(mask)
    if len(idx):
        out[idx[0]] = True
    return out


def setups(f: Dict[str, np.ndarray]) -> Dict[str, Tuple[np.ndarray, int]]:
    """Condition at a minute's close -> (mask, +1 long / -1 short).  Every
    setup comes with its mirror, so a one-sided drift shows up as such."""
    mso, sd = f["mso"], f["sd"]
    z1 = f["r1"] / sd
    z5 = f["r5"] / (sd * np.sqrt(5))
    z15 = f["r15"] / (sd * np.sqrt(15))
    zopen = f["ret_open"] / (sd * np.sqrt(np.maximum(mso, 1)))
    c = f["c"]
    windows = {"09:31-10:00": (1, 30), "10:00-11:30": (30, 120), "11:30-14:30": (120, 300), "14:30-15:45": (300, 375)}
    out: Dict[str, Tuple[np.ndarray, int]] = {}

    def add(name, mask, side):
        out[name] = (np.nan_to_num(mask.astype(float)).astype(bool), side)

    for (wn, (a, b)), k in itertools.product(windows.items(), (2.0, 3.0, 4.0)):
        w = (mso >= a) & (mso <= b)
        add(f"1m jump z>{k} {wn}: go with it", w & (z1 > k), 1)
        add(f"1m drop z<-{k} {wn}: go with it", w & (z1 < -k), -1)
        add(f"1m jump z>{k} {wn}: fade it", w & (z1 > k), -1)
        add(f"1m drop z<-{k} {wn}: fade it", w & (z1 < -k), 1)
    for (wn, (a, b)), k in itertools.product(windows.items(), (1.5, 2.5)):
        w = (mso >= a) & (mso <= b)
        add(f"5m run up z>{k} {wn}: go with it", w & (z5 > k), 1)
        add(f"5m run down z<-{k} {wn}: go with it", w & (z5 < -k), -1)
        add(f"5m run up z>{k} {wn}: fade it", w & (z5 > k), -1)
        add(f"5m run down z<-{k} {wn}: fade it", w & (z5 < -k), 1)
        add(f"15m run up z>{k} {wn}: go with it", w & (z15 > k), 1)
        add(f"15m run down z<-{k} {wn}: go with it", w & (z15 < -k), -1)
        add(f"15m run up z>{k} {wn}: fade it", w & (z15 > k), -1)
        add(f"15m run down z<-{k} {wn}: fade it", w & (z15 < -k), 1)
    for at, k in itertools.product((5, 10, 15, 30), (1.0, 2.0)):
        w = mso == at
        add(f"open drive up z>{k} at +{at}m: go with it", w & (zopen > k), 1)
        add(f"open drive down z<-{k} at +{at}m: go with it", w & (zopen < -k), -1)
        add(f"open drive up z>{k} at +{at}m: fade it", w & (zopen > k), -1)
        add(f"open drive down z<-{k} at +{at}m: fade it", w & (zopen < -k), 1)
    for k in (5, 15, 30):
        up = first_true((c > f[f"orh{k}"]) & (mso <= 240))
        dn = first_true((c < f[f"orl{k}"]) & (mso <= 240))
        add(f"{k}m opening range break up: go with it", up, 1)
        add(f"{k}m opening range break down: go with it", dn, -1)
        add(f"{k}m opening range break up: fade it", up, -1)
        add(f"{k}m opening range break down: fade it", dn, 1)
    for wn, (a, b) in windows.items():
        w = (mso >= max(a, 30)) & (mso <= b)
        add(f"new high of day {wn}: go with it", w & (f["new_high"] > 0), 1)
        add(f"new low of day {wn}: go with it", w & (f["new_low"] > 0), -1)
        add(f"new high of day {wn}: fade it", w & (f["new_high"] > 0), -1)
        add(f"new low of day {wn}: fade it", w & (f["new_low"] > 0), 1)
        w = (mso >= a) & (mso <= b)
        add(f"crosses above session average {wn}: go with it", w & (f["cross_up"] > 0), 1)
        add(f"crosses below session average {wn}: go with it", w & (f["cross_dn"] > 0), -1)
        add(f"crosses above session average {wn}: fade it", w & (f["cross_up"] > 0), -1)
        add(f"crosses below session average {wn}: fade it", w & (f["cross_dn"] > 0), 1)
    for k in (0.003, 0.006):
        g = f["gap"]
        w = mso == 0
        add(f"gap up >{k:.1%} at 09:30: go with it", w & (g > k), 1)
        add(f"gap down >{k:.1%} at 09:30: go with it", w & (g < -k), -1)
        add(f"gap up >{k:.1%} at 09:30: fade it", w & (g > k), -1)
        add(f"gap down >{k:.1%} at 09:30: fade it", w & (g < -k), 1)
    up = first_true((c > f["prev_high"]) & (mso >= 1) & (mso <= 360))
    dn = first_true((c < f["prev_low"]) & (mso >= 1) & (mso <= 360))
    add("breaks yesterday's high: go with it", up, 1)
    add("breaks yesterday's low: go with it", dn, -1)
    add("breaks yesterday's high: fade it", up, -1)
    add("breaks yesterday's low: fade it", dn, 1)
    for at, k in itertools.product((330, 345, 360, 365, 370, 375), (0.0025, 0.005, 0.01)):
        w = mso == at
        add(f"day up >{k:.2%} at +{at}m: go with it", w & (f["day_ret"] > k), 1)
        add(f"day down >{k:.2%} at +{at}m: go with it", w & (f["day_ret"] < -k), -1)
        add(f"day up >{k:.2%} at +{at}m: fade it", w & (f["day_ret"] > k), -1)
        add(f"day down >{k:.2%} at +{at}m: fade it", w & (f["day_ret"] < -k), 1)
        add(f"open-to-now up >{k:.2%} at +{at}m: go with it", w & (f["ret_open"] > k), 1)
        add(f"open-to-now down >{k:.2%} at +{at}m: go with it", w & (f["ret_open"] < -k), -1)
    for at in (0, 5, 15, 30, 60, 150, 270, 330, 360, 370):
        w = mso == at
        add(f"every day at +{at}m: long", w, 1)
        add(f"every day at +{at}m: short", w, -1)
    return out


def _accumulate(job) -> Dict[str, dict]:
    """Net bp of every setup over the given sessions (prev: the session before the first)."""
    keys, days = job
    acc: Dict[str, dict] = {}
    for j, d in enumerate(keys):
        if j == 0:
            continue                                   # the first session only serves as the previous one
        day = days[d]
        prev = days[keys[j - 1]]
        if (np.datetime64(d) - np.datetime64(prev.date)).astype(int) > 4:
            prev = None                                # a gap between two islands: no previous session
        f = features(day, prev)
        o = day.o
        n = len(o)
        mso = f["mso"]
        for name, (mask, side) in setups(f).items():
            idx = np.flatnonzero(mask & (mso <= 375))
            for hold in HOLDS:
                ok = idx[idx + 1 + hold < n]
                if not len(ok):
                    continue
                net = side * (o[ok + 1 + hold] / o[ok + 1] - 1.0) * 1e4 - COST_BP
                acc.setdefault(f"{name} | {hold}m", {}).setdefault(d, []).extend(net.tolist())
    return acc


def study(days: Dict[str, data.Day], split: str, workers: int = 4) -> Dict[str, dict]:
    """Every setup's trades by session, in parallel by year, then dev (before
    `split`) against test, year by year."""
    import multiprocessing as mp
    keys = sorted(days)
    years = sorted({d[:4] for d in keys})
    jobs = []
    for y in years:
        ks = [d for d in keys if d[:4] == y]
        before = [d for d in keys if d < ks[0]]
        ks = before[-1:] + ks
        jobs.append((ks, {d: days[d] for d in ks}))
    with mp.get_context("fork").Pool(workers) as pool:
        parts = pool.map(_accumulate, jobs)
    acc: Dict[str, Dict[str, list]] = {}
    for part in parts:
        for k, by_day in part.items():
            acc.setdefault(k, {}).update(by_day)
    ndev = sum(1 for d in keys[1:] if d < split)
    ntest = len(keys) - 1 - ndev
    rows = {}
    for key, by_day in acc.items():
        a = np.array([x for d, v in by_day.items() if d < split for x in v])
        b = np.array([x for d, v in by_day.items() if d >= split for x in v])
        if len(a) < 30 or len(b) < 15:
            continue
        yrs: Dict[str, list] = {}
        for d, v in by_day.items():
            yrs.setdefault(d[:4], []).extend(v)
        ym = {y: float(np.mean(v)) for y, v in yrs.items()}
        rows[key] = {"dev_bp": round(float(a.mean()), 2), "dev_n": len(a), "dev_per_day": round(len(a) / ndev, 2),
                     "dev_t": round(float(a.mean() / (a.std(ddof=1) / np.sqrt(len(a)))), 2),
                     "dev_win": round(float((a > 0).mean()), 3),
                     "test_bp": round(float(b.mean()), 2), "test_n": len(b),
                     "test_t": round(float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b)))), 2),
                     "years_up": f"{sum(v > 0 for v in ym.values())}/{len(ym)}",
                     "years": {y: round(v, 2) for y, v in sorted(ym.items())}}
    return rows


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else "islands"
    split = sys.argv[2] if len(sys.argv) > 2 else "2021-01-01"
    days = data.sessions(source)
    rows = study(days, split)
    ranked = sorted(rows.items(), key=lambda kv: -kv[1]["dev_t"])
    print(f"{source}: {len(days)} sessions {min(days)} to {max(days)}; dev before {split}; cost {COST_BP:.2f} bp")
    for k, v in ranked[:40]:
        print(f"  {k[:62]:62s} dev {v['dev_bp']:+6.2f}bp t{v['dev_t']:+5.1f} x{v['dev_per_day']:5.2f}/d win {v['dev_win']:.0%} "
              f"| test {v['test_bp']:+6.2f}bp t{v['test_t']:+5.1f} n{v['test_n']:5d} | yrs up {v['years_up']}")
    out = ROOT / "strategies" / "mnq" / f"edges_{source}.json"
    out.write_text(json.dumps({"source": source, "sessions": len(days), "split": split, "cost_bp": COST_BP,
                               "setups": dict(ranked)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
