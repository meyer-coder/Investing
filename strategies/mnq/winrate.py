"""Raising the win rate at levels with filters, measured against break-even.

    python strategies/mnq/winrate.py

Every first touch of a QQQ dollar strike, mapped onto Dukascopy's Nasdaq-100
minutes (as in strikes.py), is one event.  For each, the features known at
the touch (calm or wild day, minute of the day, how fast price came, how far
it had already run, whether the touch bar was rejected, whether it is a
monthly options expiry) and the result of fading it (and of going with it)
under several stop/target pairs, entering at the next minute's open, or, for
the confirmation entry, at the open after a rejection bar.

What counts is not the win rate but the win rate above break-even, which for
a stop S and target T in basis points with cost c is (S + c) / (S + T).  A
filter is worth keeping only if it lifts that margin in 2020-2023 and in
2024-2026.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import data                                                                  # noqa: E402

LEVEL, COST_PTS = 29_000.0, 1.25
COST_BP = COST_PTS / LEVEL * 1e4
SPLIT = "2024-01-01"
QQQ = json.loads((ROOT / "data" / "cache" / "qqq_daily_close.json").read_text())
GEOMS = [(5, 5), (5, 10), (5, 15), (10, 10), (10, 20), (10, 30)]


def outcome(o, h, l, k, side, stop_bp, target_bp, n):
    """(+1 target, -1 stop, 0 time) and net bp from entering at o[k]."""
    entry = o[k]
    stop = entry * (1 - side * stop_bp / 1e4)
    target = entry * (1 + side * target_bp / 1e4)
    for m in range(k, n):
        if m >= 385 or m == n - 1:
            return 0, side * (o[m] / entry - 1) * 1e4 - COST_BP
        adverse, favour = (l[m], h[m]) if side > 0 else (h[m], l[m])
        if side * (adverse - stop) <= 0:
            px = o[m] if side * (o[m] - stop) < 0 else stop
            return -1, side * (px / entry - 1) * 1e4 - COST_BP
        if side * (favour - target) >= 0:
            px = o[m] if side * (o[m] - target) > 0 else target
            return 1, side * (px / entry - 1) * 1e4 - COST_BP
    return 0, 0.0


def third_friday(d: dt.date) -> bool:
    return d.weekday() == 4 and 15 <= d.day <= 21


def events(days: Dict[str, data.Day]) -> List[dict]:
    keys = sorted(days)
    out = []
    ranges = []                                               # recent full-day ranges, for the calm/wild split
    for j in range(1, len(keys)):
        d, p = keys[j], keys[j - 1]
        day, prev = days[d], days[p]
        ranges.append((prev.h.max() - prev.l.min()) / prev.c[-1])
        if p not in QQQ or len(ranges) < 21:
            continue
        typical = float(np.median(ranges[-21:-1]))
        o, h, l, c = day.o, day.h, day.l, day.c
        n = len(o)
        ratio = prev.c[-1] / QQQ[p]
        q = QQQ[p]
        strikes = np.arange(np.ceil(q * 0.985), np.floor(q * 1.015) + 1)
        r1 = np.concatenate([[0.0], c[1:] / c[:-1] - 1])
        sd = max(float(np.std(prev.c[1:] / prev.c[:-1] - 1)), 1e-6)
        for s in strikes:
            lvl = s * ratio
            for i in range(5, min(n - 3, 361)):
                if not (l[i] <= lvl <= h[i]):
                    continue
                prev_c = c[i - 1]
                if prev_c == lvl:
                    break
                came = 1 if prev_c < lvl else -1               # +1: came up to it
                fade = -came
                day_range_so_far = (h[:i + 1].max() - l[:i + 1].min()) / c[i]
                rec = {"day": d, "strike_kind": "10" if s % 10 == 0 else ("5" if s % 5 == 0 else "1"),
                       "mso": i, "opex": third_friday(dt.date.fromisoformat(d)),
                       # a day's range grows about with the square root of time: calm = under 60% of the typical pace
                       "calm": day_range_so_far < 0.6 * typical * np.sqrt(max(i, 1) / 390),
                       "speed": abs(c[i - 1] / c[max(i - 6, 0)] - 1) / (sd * np.sqrt(5)),
                       "extension": abs(c[i] / o[0] - 1) / (sd * np.sqrt(max(i, 1))),
                       "rejected": (came > 0 and c[i] <= lvl - 0.0002 * lvl) or (came < 0 and c[i] >= lvl + 0.0002 * lvl)}
                for (sb, tb) in GEOMS:
                    w, bp = outcome(o, h, l, i + 1, fade, sb, tb, n)
                    rec[f"fade {sb}/{tb}"] = (w, bp)
                    w, bp = outcome(o, h, l, i + 1, -fade, sb, tb, n)
                    rec[f"with {sb}/{tb}"] = (w, bp)
                    if rec["rejected"]:
                        w, bp = outcome(o, h, l, i + 2, fade, sb, tb, n)
                        rec[f"fade after rejection {sb}/{tb}"] = (w, bp)
                out.append(rec)
                break
    return out


def score(evs: List[dict], key: str, sb: float, tb: float) -> dict:
    rows = [e for e in evs if key in e]
    if len(rows) < 30:
        return {}
    res = {}
    for part, sel in (("dev", [e for e in rows if e["day"] < SPLIT]), ("test", [e for e in rows if e["day"] >= SPLIT])):
        if len(sel) < 15:
            return {}
        w = np.array([e[key][0] for e in sel])
        bp = np.array([e[key][1] for e in sel])
        be = (sb + COST_BP) / (sb + tb)
        wins = (w == 1).mean()
        res[part] = {"n": len(sel), "win": round(float(wins), 3), "breakeven": round(be, 3),
                     "margin": round(float(wins - be), 3), "pts": round(float(bp.mean() * LEVEL / 1e4), 2),
                     "t": round(float(bp.mean() / (bp.std(ddof=1) / np.sqrt(len(bp)))), 2)}
    return res


def main() -> int:
    days = data.sessions("duka")
    evs = events(days)
    print(f"{len(evs)} first touches of QQQ dollar strikes over {len(days)} sessions")
    filters = {
        "all": lambda e: True,
        "calm day so far": lambda e: e["calm"],
        "wild day so far": lambda e: not e["calm"],
        "after 14:00": lambda e: e["mso"] >= 270,
        "before 11:00": lambda e: e["mso"] < 90,
        "monthly expiry Friday": lambda e: e["opex"],
        "fast approach (5m move > 2 typical)": lambda e: e["speed"] > 2,
        "slow approach (5m move < 1 typical)": lambda e: e["speed"] < 1,
        "extended day (> 2 typical from the open)": lambda e: e["extension"] > 2,
        "round strike (5 or 10)": lambda e: e["strike_kind"] in ("5", "10"),
        "calm + after 14:00": lambda e: e["calm"] and e["mso"] >= 270,
        "calm + slow approach": lambda e: e["calm"] and e["speed"] < 1,
        "extended + fast approach": lambda e: e["extension"] > 2 and e["speed"] > 2,
    }
    table = {}
    for (fname, f), (sb, tb), how in itertools.product(filters.items(), GEOMS, ("fade", "with", "fade after rejection")):
        sel = [e for e in evs if f(e)]
        s = score(sel, f"{how} {sb}/{tb}", sb, tb)
        if s:
            table[f"{how} {sb}/{tb} | {fname}"] = s
    ranked = sorted(table.items(), key=lambda kv: -min(kv[1]["dev"]["margin"], kv[1]["test"]["margin"]))
    print("win rate above break-even (margin), 2020-2023 | 2024-2026; points a trade at 29,000 after costs")
    for k, v in ranked[:30]:
        a, b = v["dev"], v["test"]
        print(f"  {k[:74]:74s} n {a['n']:5d}/{b['n']:5d} win {a['win']:.0%}/{b['win']:.0%} be {a['breakeven']:.0%} "
              f"margin {a['margin']:+.1%}/{b['margin']:+.1%} | {a['pts']:+6.2f}/{b['pts']:+6.2f} pts t {a['t']:+.1f}/{b['t']:+.1f}")
    (ROOT / "strategies" / "mnq" / "winrate.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
