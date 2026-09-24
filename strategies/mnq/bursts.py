"""Ten-to-thirty-second bursts in the Nasdaq-100: do they carry on or snap back?

    python strategies/mnq/bursts.py            # the 10-second bars on disk (duka.py ... 10SEC)

Small, frequent gains: when the index moves fast over 10, 20 or 30 seconds,
does the next 10 seconds to 2 minutes follow it or give it back, by enough to
pay MNQ's cost?  Each 10-second bar from 08:00 to 15:55 New York is checked;
a burst is a move beyond a share of the price (0.05% to 0.3%) or beyond a
multiple of the typical 10-second move of the last half hour.  The trade goes
in at the NEXT 10-second bar's open (ten seconds late, on purpose: a bot is
faster, a person slower) and comes out at a later bar's open, going with the
burst or fading it, one position at a time.  Costs are counted three ways,
1.25, 2.5 and 5 index points a round trip, because a fast market fills worse.
Results are split by time of day (the 08:30 data releases, the 09:30 open,
the rest of the session) and first year against second.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import duka                                                                  # noqa: E402

LEVEL = 29_000.0
COSTS = (1.25, 2.5, 5.0)                   # index points a round trip
HOLDS = (1, 2, 3, 6, 12)                   # 10-second bars: 10 s to 2 minutes


def ny_minute(ts: np.ndarray) -> np.ndarray:
    import datetime as dt
    out = np.empty(len(ts))
    for k, t in enumerate(ts):
        u = dt.datetime.fromtimestamp(t, tz=dt.timezone.utc).astimezone(duka.NY)
        out[k] = u.hour * 60 + u.minute + u.second / 60.0
    return out


def zone(m: float) -> str:
    if 8 * 60 + 29 <= m < 8 * 60 + 36:
        return "08:29-08:35 releases"
    if 9 * 60 + 30 <= m < 9 * 60 + 36:
        return "09:30-09:35 open"
    if 9 * 60 + 36 <= m < 15 * 60 + 55:
        return "09:36-15:55 session"
    return "other"


def study(days: Dict[str, np.ndarray], split: str) -> Dict[str, dict]:
    acc: Dict[str, dict] = {}
    for d, a in days.items():
        ts, o, h, l, c = a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4]
        n = len(c)
        if n < 500:
            continue
        mins = ny_minute(ts)
        r1 = np.concatenate([[0.0], c[1:] / c[:-1] - 1.0])
        # the typical 10-second move over the last half hour (180 bars), from bars already closed
        sq = np.concatenate([[0.0], np.cumsum(r1 ** 2)])
        cnt = np.arange(n + 1)
        lo = np.maximum(np.arange(n) - 179, 0)
        sd = np.sqrt((sq[1:] - sq[lo]) / np.maximum(cnt[1:] - cnt[lo], 1))
        sd = np.maximum(sd, 1e-6)
        zones = np.array([zone(m) for m in mins])
        part = "dev" if d < split else "test"
        for k in (1, 2, 3):
            rk = np.full(n, np.nan)
            rk[k:] = c[k:] / c[:-k] - 1.0
            triggers = {}
            for th in (0.0005, 0.001, 0.002, 0.003):
                triggers[f"{k * 10}s move beyond {th:.2%}"] = np.abs(rk) > th
            for zz in (4.0, 6.0, 8.0):
                triggers[f"{k * 10}s move beyond {zz:g}x the typical"] = np.abs(rk) > zz * sd * np.sqrt(k)
            for name, mask in triggers.items():
                mask = np.nan_to_num(mask.astype(float)).astype(bool)
                idx = np.flatnonzero(mask[:n - 14])
                if not len(idx):
                    continue
                for hold in HOLDS:
                    # one position at a time: skip triggers while the last trade is still open
                    keep, busy = [], -1
                    for i in idx:
                        if i + 1 > busy:
                            keep.append(i)
                            busy = i + 1 + hold
                    keep = np.array(keep)
                    sign = np.sign(rk[keep])
                    move = (o[keep + 1 + hold] / o[keep + 1] - 1.0) * LEVEL      # points at today's level
                    for how, s in (("go with it", 1.0), ("fade it", -1.0)):
                        pts = s * sign * move
                        for zn in set(zones[keep]):
                            if zn == "other":
                                continue
                            sel = zones[keep] == zn
                            key = f"{name} | {how} | {hold * 10}s | {zn}"
                            r = acc.setdefault(key, {"dev": [], "test": [], "days": {}})
                            r[part].extend(pts[sel].tolist())
                            r["days"][d] = r["days"].get(d, 0) + int(sel.sum())
    ndays = {"dev": sum(1 for d in days if d < split), "test": sum(1 for d in days if d >= split)}
    rows = {}
    for key, r in acc.items():
        a, b = np.array(r["dev"]), np.array(r["test"])
        if len(a) < 40 or len(b) < 40:
            continue
        row = {"dev_n": len(a), "test_n": len(b), "per_day": round((len(a) + len(b)) / sum(ndays.values()), 2),
               "gross_dev": round(float(a.mean()), 2), "gross_test": round(float(b.mean()), 2),
               "win_dev_at_1.25": round(float((a > 1.25).mean()), 3)}
        for cost in COSTS:
            aa, bb = a - cost, b - cost
            row[f"net_{cost:g}"] = {"dev": round(float(aa.mean()), 2), "test": round(float(bb.mean()), 2),
                                    "dev_t": round(float(aa.mean() / (aa.std(ddof=1) / np.sqrt(len(aa)))), 2),
                                    "test_t": round(float(bb.mean() / (bb.std(ddof=1) / np.sqrt(len(bb)))), 2)}
        rows[key] = row
    return rows


def main() -> int:
    days = duka.load_seconds()
    keys = sorted(days)
    split = keys[len(keys) // 2]
    rows = study(days, split)
    ranked = sorted(rows.items(), key=lambda kv: -min(kv[1]["net_2.5"]["dev_t"], kv[1]["net_2.5"]["test_t"]))
    print(f"{len(days)} days of 10-second bars, {keys[0]} to {keys[-1]}; first half before {split}")
    print("points a trade per MNQ contract ($2 a point); net of 2.5 points unless noted")
    for k, v in ranked[:30]:
        n = v["net_2.5"]
        print(f"  {k[:86]:86s} {v['per_day']:6.2f}/d gross {v['gross_dev']:+6.2f}/{v['gross_test']:+6.2f} | net dev {n['dev']:+6.2f} "
              f"t{n['dev_t']:+4.1f} test {n['test']:+6.2f} t{n['test_t']:+4.1f} | at 1.25: {v['net_1.25']['dev']:+.2f}/{v['net_1.25']['test']:+.2f}")
    (ROOT / "strategies" / "mnq" / "bursts.json").write_text(json.dumps({"split": split, "days": len(days),
                                                                         "setups": dict(ranked)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
