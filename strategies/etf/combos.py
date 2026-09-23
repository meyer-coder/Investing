"""Two or three strategies sharing one $25,000 account, chosen so that one's
good months cover the other's quiet ones.

    python strategies/etf/combos.py [--min 120] [--exclude TSM] [--target 250]

The account is split: each strategy trades its own share and keeps its own
rules, so the book's day is the weighted sum of theirs.  Candidates are stored
strategies at --min dollars a session or more over the held-out six months
(rebuilt series, and real funds where the store has them), profitable over
2012-2018, never down more than 70%, and not on the excluded underlyings;
near-copies (daily returns correlated 0.97 or more over the six months) are
dropped.  Every pair and, from the best pairs, every third strategy is scored
on the six months at the size that makes --target dollars a session (the book
keeps the rest in cash): its worst calendar month first, then its worst
drawdown.  The best are then measured over 2019-2026 and 2012-2018 too.

The six months were never used to breed these strategies, but choosing the
combination on them makes the months in-sample for the choice.

Writes strategies/etf/combos.json.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pickle
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import ACCOUNT, SLIP, WINDOWS, backtest, load_store              # noqa: E402
from evotrader.genome import Genome                                            # noqa: E402

OUT = ROOT / "strategies" / "etf" / "combos.json"


def series(v: dict) -> Dict[str, float]:
    res = backtest(Genome.from_dict(v["genome"]), v["symbols"], SLIP)
    d, e = res.journal.equity_dates, np.asarray(res.journal.equity, dtype=float)
    return dict(zip(d[1:], e[1:] / e[:-1] - 1.0))


def month_key(d: str) -> str:
    return "2026-04" if d[:7] == "2026-03" else d[:7]


def stats(r: np.ndarray, dates: List[str], held_out: bool = False) -> dict:
    usd = r * ACCOUNT
    months: Dict[str, List[float]] = {}
    for d, x in zip(dates, usd):
        months.setdefault(month_key(d) if held_out else d[:7], []).append(x)
    mm = np.array([np.mean(v) for v in months.values()])
    eq = np.cumprod(1.0 + r)
    dd = float(np.min(eq / np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:] - 1.0))
    roll = np.convolve(usd, np.ones(21), mode="valid") / 21 if len(usd) >= 21 else np.array([usd.mean()])
    return {"usd_per_session": round(float(usd.mean()), 1), "worst_month": round(float(mm.min()), 1),
            "months_up": round(float((mm > 0).mean()), 3), "months": len(mm),
            "month_stretches_up": round(float((roll > 0).mean()), 3),
            "worst_month_stretch": round(float(roll.min()), 1), "max_drawdown": round(dd, 4),
            "worst_day": round(float(usd.min()), 0),
            **({"by_month": {k: round(float(np.mean(v)), 1) for k, v in months.items()}} if held_out else {})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=120.0)
    ap.add_argument("--exclude", default="TSM")
    ap.add_argument("--target", type=float, default=250.0)
    ap.add_argument("--keep", type=int, default=40)
    ap.add_argument("--floor", type=float, default=150.0, help="the worst month a combination should clear")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    bad = [x for x in args.exclude.split(",") if x]
    store = load_store()["strategies"]
    cands = []
    for key, v in store.items():
        if any(x in s for s in v["symbols"] for x in bad):
            continue
        w = v["windows"]
        real = v["verdict"].get("real_held_out_usd")
        if w["held_out"]["usd_per_session"] < args.min or (real is not None and real < 0.9 * args.min):
            continue
        if not v["verdict"].get("older_profitable"):
            continue
        if min((w.get(k) or {}).get("max_drawdown", 0.0) for k in ("older", "train", "held_out")) <= -0.70:
            continue
        cands.append((key, v))
    print(f"{len(cands)} candidates", flush=True)

    cache = ROOT / "runs" / "etf" / "combo_returns.pkl"
    known = pickle.loads(cache.read_bytes()) if cache.exists() else {}
    rets = {k: known[k] if k in known else series(v) for k, v in cands}
    cache.write_bytes(pickle.dumps({**known, **rets}))
    dates = sorted(set().union(*(set(r) for r in rets.values())))     # a strategy not yet trading is in cash
    dates = [d for d in dates if d >= WINDOWS["older"][0]]
    R = np.array([[rets[k].get(d, 0.0) for d in dates] for k, _ in cands])
    a, b = WINDOWS["held_out"]
    ho = np.array([a <= d <= b for d in dates])
    hd = [d for d in dates if a <= d <= b]

    # drop near-copies over the six months, keeping the better earner
    order = np.argsort(-R[:, ho].mean(axis=1))
    C = np.corrcoef(R[:, ho])
    keep: List[int] = []
    for i in order:
        if all(C[i, j] < 0.97 for j in keep):
            keep.append(int(i))
    R, cands = R[keep], [cands[i] for i in keep]
    print(f"{len(cands)} after dropping near-copies", flush=True)

    H = R[:, ho] * ACCOUNT
    mkeys = sorted({month_key(d) for d in hd})
    M = np.stack([H[:, [month_key(d) == m for d in hd]].mean(axis=1) for m in mkeys], axis=1)   # usd/session by month
    avg = H.mean(axis=1)

    def sized_worst(idx) -> tuple:
        m = M[list(idx)].mean(axis=0)
        f = min(1.0, args.target / m.mean()) if m.mean() > 0 else 1.0
        return f * m.min(), f

    scored = []
    n = len(cands)
    for i, j in itertools.combinations(range(n), 2):
        w, f = sized_worst((i, j))
        scored.append((w, (i, j)))
    scored.sort(reverse=True)
    pairs = [p for _, p in scored[:300]]
    for (i, j) in pairs[:60]:
        for k in range(n):
            if k in (i, j):
                continue
            w, f = sized_worst((i, j, k))
            scored.append((w, tuple(sorted((i, j, k)))))
    scored = sorted(set(scored), reverse=True)

    rows, seen = [], set()
    for w, idx in scored:
        if idx in seen:
            continue
        seen.add(idx)
        mix = R[list(idx)].mean(axis=0)
        m = M[list(idx)].mean(axis=0)
        f = min(1.0, args.target / m.mean()) if m.mean() > 0 else 1.0
        r = f * mix
        win = {name: stats(r[np.array([lo <= d <= hi for d in dates])], [d for d in dates if lo <= d <= hi],
                           held_out=(name == "held_out"))
               for name, (lo, hi) in WINDOWS.items() if name != "last_12m"}
        rows.append({"members": [{"key": cands[i][0], "name": cands[i][1]["genome"]["name"],
                                  "symbols": cands[i][1]["symbols"], "source": cands[i][1]["source"],
                                  "held_out_usd": round(float(avg[i]), 1),
                                  "real_held_out_usd": cands[i][1]["verdict"].get("real_held_out_usd")}
                                 for i in idx],
                     "fraction": round(f, 3), "each": round(f / len(idx), 3), "windows": win})
        if len(rows) >= args.keep:
            break
    rows.sort(key=lambda x: (x["windows"]["held_out"]["worst_month"] >= args.floor,
                             x["windows"]["held_out"]["max_drawdown"] > -0.20,
                             x["windows"]["train"]["months_up"], x["windows"]["held_out"]["worst_month"]),
              reverse=True)
    Path(args.out).write_text(json.dumps(rows, indent=1))
    for x in rows[:15]:
        h, t, o = (x["windows"][k] for k in ("held_out", "train", "older"))
        print(" + ".join(f"{','.join(m['symbols'])} {m['name'][:26]}" for m in x["members"]))
        print(f"   at {x['fraction']:.0%} ({x['each']:.0%} each): 6mo ${h['usd_per_session']:.0f} worst month "
              f"${h['worst_month']:.0f} 1mo-up {h['month_stretches_up']:.0%} dd {h['max_drawdown']:.0%} | "
              f"2019-26 ${t['usd_per_session']:.0f} months up {t['months_up']:.0%} dd {t['max_drawdown']:.0%} | "
              f"2012-18 ${o['usd_per_session']:.0f} up {o['months_up']:.0%} dd {o['max_drawdown']:.0%}")
        print("   " + " ".join(f"{k[5:]}:{v:.0f}" for k, v in h["by_month"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
