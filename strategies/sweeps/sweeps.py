"""Liquidity sweeps and level breakouts on NQ and ES, one-minute bars, 2013 to September 2026.

    python strategies/sweeps/sweeps.py

The levels each morning (data.py; column 150 is the 09:30 open):

* PD - yesterday's regular-session high and low;
* PM - the pre-market high and low, 07:00-09:29 New York;
* OR - the first fifteen minutes' high and low (traded from 09:45).

Two ways to trade a level, each once a level a day:

* sweep (fade): price trades through the level, then a one-minute bar closes
  back inside within `back` minutes: that is the sweep.  Enter against it at
  the next minute's open, the stop just past the sweep's extreme (plus 0.02%
  of the price), the target `target` times that risk (or the close);
* break (follow): a one-minute bar closes beyond the level and the next
  `hold` bars stay beyond it.  Enter with it at the next open, the stop on the
  level's other side (0.02% past it), the target as above.

The sweep is also tried the way ICT traders take it:

* +MSS: after price runs the level, wait (up to `back` minutes) for a close
  beyond the low (high) of the ten minutes before the run, a "market
  structure shift", and enter then, the stop past the run's extreme;
* +trend: fade a run of the highs only when yesterday closed below its 20-day
  average, a run of the lows only when above it;
* target "mid": the middle of the level pair (the other side's liquidity is
  often further than the day goes).

Entries between the level's first minute and `until` (11:30 or 15:00);
anything open is closed at 15:59.  Costs 1 bp of the price a round trip ($6
on an MNQ at today's level, above a tick of slippage plus commission), and 2 bp
as a check.

Every setting is run; each is judged on 2013-2019 and shown on 2020-2026,
where the choices are then checked.  Random sides on the same trades test
whether the direction is worth anything.  Written to
strategies/sweeps/sweeps.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data                                                                  # noqa: E402

OPEN, T = data.OPEN, data.T
SPLIT = "2020-01-01"
BUF = 0.0002
COST = 1e-4
UNTIL = {"11:30": 270, "15:00": 480}


def levels(D, i, kind):
    """(high level, low level, first minute to trade) for day i."""
    H, L = D["H"][i], D["L"][i]
    if kind == "PD":
        return D["ph"][i], D["pl"][i], OPEN
    if kind == "PM":
        return H[:OPEN].max(), L[:OPEN].min(), OPEN
    return H[OPEN:OPEN + 15].max(), L[OPEN:OPEN + 15].min(), OPEN + 15


def exit_trade(D, i, e, side, entry, stop, target):
    """From minute e: the stop, the target or the 15:59 close, whichever comes first.  Returns (exit price, minute, why)."""
    O, H, L, C = D["O"][i], D["H"][i], D["L"][i], D["C"][i]
    hs = np.flatnonzero((L[e:] <= stop) if side > 0 else (H[e:] >= stop))
    ht = np.flatnonzero((H[e:] >= target) if side > 0 else (L[e:] <= target)) if target is not None else np.array([], int)
    s = hs[0] if hs.size else T
    t = ht[0] if ht.size else T
    if s == T and t == T:
        return C[T - 1], T - 1, "close"
    if s <= t:                                                                # a stop and a target in one bar: the stop
        u = e + s
        px = stop if u == e else (min(O[u], stop) if side > 0 else max(O[u], stop))
        return px, u, "stop"
    return target, e + t, "target"                                            # a resting limit: filled at its price


def trend(D) -> np.ndarray:
    """+1 when the previous session closed above its 20-day average, -1 below, 0 before there are 20."""
    close = D["C"][:, -1]
    out = np.zeros(len(close))
    for i in range(21, len(close)):
        out[i] = 1.0 if close[i - 1] > close[i - 21:i - 1].mean() else -1.0
    return out


def run(D, mode, kind, until, back=5, hold=1, target=2.0, cost=COST, confirm=None, bias=False, look=10):
    """All trades of one setting: (day index, side, net return, R multiple, why, entry minute, exit minute, entry price)."""
    out = []
    O, H, L, C = D["O"], D["H"], D["L"], D["C"]
    last = UNTIL[until]
    days = np.array(D["dates"], dtype="datetime64[D]")
    tr = trend(D) if bias else None
    for i in range(1, len(D["dates"])):
        if kind == "PD" and days[i] - days[i - 1] > np.timedelta64(4, "D"):   # the session before is missing
            continue
        hi, lo, first = levels(D, i, kind)
        if np.isnan(hi) or np.isnan(lo) or hi <= lo:
            continue
        for lvl, up in ((hi, True), (lo, False)):
            h, l, c = H[i], L[i], C[i]
            through = np.flatnonzero((h[first:last] > lvl) if up else (l[first:last] < lvl))
            if not through.size:
                continue
            j = first + through[0]
            if mode == "sweep":
                side = -1 if up else 1
                if bias and tr[i] != side:
                    continue
                if confirm == "mss":                                          # a close past the swing before the run
                    swing = l[j - look:j].min() if up else h[j - look:j].max()
                    seg = np.flatnonzero((c[j:j + back + 1] < swing) if up else (c[j:j + back + 1] > swing))
                else:
                    seg = np.flatnonzero((c[j:j + back + 1] < lvl) if up else (c[j:j + back + 1] > lvl))
                if not seg.size:
                    continue
                m = j + seg[0]
                if m + 1 >= last:
                    continue
                extreme = h[j:m + 1].max() if up else l[j:m + 1].min()
                entry = O[i, m + 1]
                stop = extreme * (1 + BUF) if up else extreme * (1 - BUF)
            else:
                beyond = np.flatnonzero((c[j:last] > lvl) if up else (c[j:last] < lvl))
                if not beyond.size:
                    continue
                m = j + beyond[0]
                if m + hold >= last or not (np.all(c[m:m + hold + 1] > lvl) if up else np.all(c[m:m + hold + 1] < lvl)):
                    continue
                m += hold
                side = 1 if up else -1
                entry = O[i, m + 1]
                stop = lvl * (1 - BUF) if up else lvl * (1 + BUF)
            risk = side * (entry - stop)
            if risk <= 0:
                continue
            if target == "mid":
                tgt = (hi + lo) / 2
                if side * (tgt - entry) <= 0:
                    continue
            else:
                tgt = entry + side * target * risk if target else None
            px, u, why = exit_trade(D, i, m + 1, side, entry, stop, tgt)
            gross = side * (px / entry - 1.0)
            out.append((i, side, gross - cost, (side * (px - entry)) / risk, why, m + 1, int(u), float(entry)))
    return out


def stats(D, trades) -> dict:
    if not trades:
        return {"trades": 0}
    ds = np.array(D["dates"])
    r = np.array([t[2] for t in trades])
    rr = np.array([t[3] for t in trades])
    idx = np.array([t[0] for t in trades])
    dev, test = ds[idx] < SPLIT, ds[idx] >= SPLIT
    per_day = len(trades) / len(ds)

    def part(m):
        v = r[m]
        if v.size < 2:
            return {"trades": int(v.size)}
        return {"trades": int(v.size), "mean_bp": round(float(v.mean() * 1e4), 2), "t": round(float(v.mean() / v.std(ddof=1) * np.sqrt(v.size)), 2),
                "win": round(float((v > 0).mean()), 3), "pf": round(float(v[v > 0].sum() / max(-v[v <= 0].sum(), 1e-12)), 2),
                "mean_r": round(float(rr[m].mean()), 3)}
    years = {}
    for k, x in zip(ds[idx], r):
        years.setdefault(k[:4], []).append(x)
    return {"all": part(np.ones(len(r), bool)), "dev": part(dev), "test": part(test), "trades_per_day": round(per_day, 2),
            "years_bp": {y: round(float(np.mean(v) * 1e4), 1) for y, v in sorted(years.items())}}


KINDS, UNTILS = ("PD", "PM", "OR"), ("11:30", "15:00")


def grid():
    seen = set()
    sweeps = [itertools.product(KINDS, UNTILS, (1, 5, 15), (1.0, 2.0, 3.0, None), (None,), (False,)),
              itertools.product(KINDS, UNTILS, (5, 15), (2.0, "mid", None), (None,), (False, True)),
              itertools.product(KINDS, UNTILS, (15, 30), (2.0, "mid", None), ("mss",), (False, True))]
    for kind, until, back, target, confirm, bias in itertools.chain(*sweeps):
        s = {"mode": "sweep", "kind": kind, "until": until, "back": back, "target": target, "confirm": confirm, "bias": bias}
        if label(s) not in seen:
            seen.add(label(s))
            yield s
    for kind, until, hold, target in itertools.product(KINDS, UNTILS, (1, 5), (1.0, 2.0, 3.0, None)):
        yield {"mode": "break", "kind": kind, "until": until, "hold": hold, "target": target}


def label(s: dict) -> str:
    extra = f"back {s['back']}m" if s["mode"] == "sweep" else f"hold {s['hold']}m"
    tgt = "mid" if s["target"] == "mid" else (f"{s['target']:g}R" if s["target"] else "close")
    flags = (" +MSS" if s.get("confirm") else "") + (" +trend" if s.get("bias") else "")
    return f"{s['mode']:5s} {s['kind']} to {s['until']} {extra:9s} target {tgt}{flags}"


def family(s: dict) -> str:
    if s["mode"] == "break":
        return "break"
    return "sweep" + (" +MSS" if s.get("confirm") else "") + (" +trend" if s.get("bias") else "") + (" to mid" if s["target"] == "mid" else "")


def main() -> int:
    res = {}
    rng = np.random.default_rng(5)
    for inst in ("NQ", "ES"):
        D = data.load(inst)
        rows = []
        for s in grid():
            tr = run(D, **s)
            st = stats(D, tr)
            if st.get("all", {}).get("trades", 0) < 100 or "t" not in st["dev"] or "t" not in st["test"]:
                continue
            r = np.array([t[2] for t in tr])
            flips = rng.choice([-1.0, 1.0], size=(500, r.size))
            rnd = (flips * (r + COST)[None, :]).mean(axis=1) - COST
            st["p_vs_random_side"] = round(float((rnd >= r.mean()).mean()), 3)
            st["mean_bp_at_2bp"] = round(float((r.mean() - COST) * 1e4), 2)
            rows.append({"setting": s, "label": label(s), **st})
        rows.sort(key=lambda x: -x["dev"]["t"])
        test_pos = sum(x["test"]["mean_bp"] > 0 for x in rows)
        print(f"\n{inst}: {len(D['dates'])} sessions {D['dates'][0]} to {D['dates'][-1]}; {len(rows)} settings, "
              f"{test_pos} positive on 2020-2026; the ten best on 2013-2019 (t) and what they did after:")
        head = (f"  {'setting':62s} {'tr/day':>6} {'dev bp':>7} {'dev t':>6} {'test bp':>8} {'test t':>6} {'win':>5} {'mean R':>7} "
                f"{'at 2bp':>7} {'p side':>6}")

        def show(x):
            print(f"  {x['label']:62s} {x['trades_per_day']:6.2f} {x['dev']['mean_bp']:+7.2f} {x['dev']['t']:+6.2f} "
                  f"{x['test']['mean_bp']:+8.2f} {x['test']['t']:+6.2f} {x['test']['win']:5.0%} {x['test']['mean_r']:+7.3f} "
                  f"{x['mean_bp_at_2bp']:+7.2f} {x['p_vs_random_side']:6.3f}", flush=True)
        print(head)
        for x in rows[:10]:
            show(x)
        print("  the ten best sweeps on 2013-2019:")
        for x in [x for x in rows if x["setting"]["mode"] == "sweep"][:10]:
            show(x)
        for fam in sorted({family(x["setting"]) for x in rows}):
            sub = [x for x in rows if family(x["setting"]) == fam]
            print(f"  {fam:28s} {len(sub):3d} settings; positive on 2020-2026: {sum(x['test']['mean_bp'] > 0 for x in sub):3d}; "
                  f"the best ten on 2013-2019 made {np.mean([x['test']['mean_bp'] for x in sub[:10]]):+.2f} bp a trade after; "
                  f"all {np.mean([x['test']['mean_bp'] for x in sub]):+.2f} bp (2013-2019 {np.mean([x['dev']['mean_bp'] for x in sub]):+.2f})",
                  flush=True)
        res[inst] = rows
    (Path(__file__).resolve().parent / "sweeps.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
