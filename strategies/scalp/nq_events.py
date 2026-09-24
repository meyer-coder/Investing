"""Where is the edge in one-to-four-minute NQ futures trades?  Ten years of islands.

    python strategies/scalp/nq_events.py

TradingView serves about a week of one-minute bars for every expired quarterly
NQ contract (data/intraday/nq/, fetched 2026-09-23): 45 contracts from 2016,
so a couple of hundred regular sessions spread over ten years of different
markets.  For each candidate setup this measures the net points of entering at
the next minute's open and leaving at the open h minutes later, less 1.25
points a round trip (MNQ: a tick each way plus commission), long or short.
Only 09:35-15:45 New York counts and every exit is inside the same session.

Setups are chosen on 2016-2020 and tested on 2021-2026.
"""
from __future__ import annotations

import csv
import itertools
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evotrader.data import Bars                                             # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.data import Universe                                         # noqa: E402

NQ_DIR = ROOT / "data" / "intraday" / "nq"
NY = ZoneInfo("America/New_York")
COST_PTS = 1.25
HOLDS = (1, 2, 3, 4)
OUT = ROOT / "strategies" / "scalp" / "nq_events.json"


def sessions() -> Dict[str, Bars]:
    """Every complete regular session in the islands, one Bars per session,
    stamped in UTC.  A session present in two contracts comes from the one
    expiring later (the busier one)."""
    per_day: Dict[str, Tuple[str, List[tuple]]] = {}
    for path in sorted(NQ_DIR.glob("NQ[HMUZ]20[0-9][0-9]_1m.csv")):
        rows_by_day: Dict[str, List[tuple]] = defaultdict(list)
        with path.open() as f:
            for r in csv.DictReader(f):
                t = datetime.strptime(r["stamp"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                lt = t.astimezone(NY)
                if (lt.hour, lt.minute) < (9, 30) or lt.hour >= 16:
                    continue
                rows_by_day[lt.strftime("%Y-%m-%d")].append(
                    (r["stamp"][:16], *(float(r[k]) for k in ("open", "high", "low", "close", "volume"))))
        for day, rows in rows_by_day.items():
            if len(rows) >= 380:
                per_day[day] = (path.stem, sorted(rows))
    out = {}
    for day, (_, rows) in sorted(per_day.items()):
        cols = list(zip(*rows))
        out[day] = Bars("NQ", list(cols[0]), *[np.asarray(c, dtype=float) for c in cols[1:]])
    return out


def features_for(b: Bars) -> Dict[str, np.ndarray]:
    f = build_features(Universe({"NQ": b}, list(b.dates)))
    return {k: np.asarray(f.matrix["NQ"][k], dtype=float) for k in
            ("ret1", "atr_pct", "zscore20", "rsi7", "volume_ratio", "dist_session_vwap",
             "minutes_since_open", "minute_of_day", "sma20_slope")}


def setups(F: Dict[str, np.ndarray]) -> Dict[str, Tuple[np.ndarray, int]]:
    """Condition -> (boolean array, direction +1 long / -1 short)."""
    r1, atr = F["ret1"], F["atr_pct"]
    r2 = r1 + np.concatenate([[np.nan], r1[:-1]])
    mso, dv, z = F["minutes_since_open"], F["dist_session_vwap"], F["zscore20"]
    out: Dict[str, Tuple[np.ndarray, int]] = {}
    windows = {"09:35-09:50": (5, 20), "09:35-10:30": (5, 60), "all day": (5, 375)}
    for (wn, (a, b)), k in itertools.product(windows.items(), (0.75, 1.0, 1.5, 2.0, 3.0)):
        w = (mso >= a) & (mso <= b)
        out[f"buy 1m drop>{k}atr {wn}"] = ((r1 < -k * atr) & w, 1)
        out[f"short 1m rise>{k}atr {wn}"] = ((r1 > k * atr) & w, -1)
        out[f"chase 1m rise>{k}atr {wn}"] = ((r1 > k * atr) & w, 1)
        out[f"chase 1m drop>{k}atr {wn}"] = ((r1 < -k * atr) & w, -1)
        out[f"buy 2m drop>{k}atr z<-2 {wn}"] = ((r2 < -k * atr) & (z < -2) & w, 1)
        out[f"short 2m rise>{k}atr z>2 {wn}"] = ((r2 > k * atr) & (z > 2) & w, -1)
    for (wn, (a, b)), m in itertools.product(windows.items(), (3.0, 5.0, 8.0)):
        w = (mso >= a) & (mso <= b)
        out[f"buy stretch under vwap {m}atr {wn}"] = ((dv < -m * atr) & w, 1)
        out[f"short stretch over vwap {m}atr {wn}"] = ((dv > m * atr) & w, -1)
    return out


def main() -> int:
    days = sessions()
    print(f"{len(days)} complete sessions, {min(days)} to {max(days)}", flush=True)
    acc: Dict[str, Dict[str, list]] = {}
    for day, b in days.items():
        F = features_for(b)
        o = np.asarray(b.open, dtype=float)
        n = len(o)
        ok = (F["minute_of_day"] < 945)
        dev = day < "2021-01-01"
        for label, (cond, sign) in setups(F).items():
            cond = np.nan_to_num(cond.astype(float)).astype(bool) & ok
            idx = np.flatnonzero(cond[: n - 6])
            for h in HOLDS:
                j, k = idx + 1, idx + 1 + h
                pts = sign * (o[k] - o[j]) - COST_PTS
                r = acc.setdefault(f"{label} | hold {h}m", {"dev": [], "test": [], "dev_days": {}, "test_days": {}})
                part = "dev" if dev else "test"
                r[part].extend(pts.tolist())
                r[f"{part}_days"][day] = float(pts.sum())
    ndev = sum(1 for d in days if d < "2021-01-01")
    ntest = len(days) - ndev
    res = []
    for key, r in acc.items():
        d, t = np.array(r["dev"]), np.array(r["test"])
        if len(d) < 30 or len(t) < 30:
            continue
        dd = np.array([r["dev_days"].get(x, 0.0) for x in days if x < "2021-01-01"])
        td = np.array([r["test_days"].get(x, 0.0) for x in days if x >= "2021-01-01"])
        res.append({"setup": key, "dev_pts": round(float(d.mean()), 2), "dev_n_day": round(len(d) / ndev, 2),
                    "dev_win": round(float((d > 0).mean()), 3),
                    "dev_t": round(float(d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))), 2),
                    "dev_day_pts": round(float(dd.mean()), 2), "dev_days_up": round(float((dd > 0).mean()), 3),
                    "test_pts": round(float(t.mean()), 2), "test_n_day": round(len(t) / ntest, 2),
                    "test_win": round(float((t > 0).mean()), 3),
                    "test_t": round(float(t.mean() / (t.std(ddof=1) / np.sqrt(len(t)))), 2),
                    "test_day_pts": round(float(td.mean()), 2), "test_days_up": round(float((td > 0).mean()), 3)})
    res.sort(key=lambda x: x["dev_t"], reverse=True)
    OUT.write_text(json.dumps({"sessions": len(days), "dev_sessions": ndev, "test_sessions": ntest,
                               "cost_points": COST_PTS, "setups": res}, indent=1))
    print(f"dev 2016-2020: {ndev} sessions, test 2021-2026: {ntest}")
    for x in res[:25]:
        print(f"  {x['setup'][:52]:52s} dev {x['dev_pts']:+6.2f}pts x{x['dev_n_day']:5.2f}/d t {x['dev_t']:+5.1f} "
              f"day {x['dev_day_pts']:+6.1f}pts up {x['dev_days_up']:.0%} | test {x['test_pts']:+6.2f}pts x{x['test_n_day']:5.2f}/d "
              f"t {x['test_t']:+5.1f} day {x['test_day_pts']:+6.1f}pts up {x['test_days_up']:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
