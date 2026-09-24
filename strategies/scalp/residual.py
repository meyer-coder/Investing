"""Residual reversal: buy a name that drops while the market does not.

    python strategies/scalp/residual.py

A one-minute drop shared by the whole market is news; one a name takes alone is
often one seller leaning on the book, and it tends to come back.  For each
name and minute, the residual is its one-minute return less the average of
the other names' that minute; its size is judged against its own last 20
minutes of residuals.  Measured as in events.py (next open in, the open h
minutes later out, less a cent and 1 bp each way), on the 17 names the first
scalper used, first 14 sessions against the last 7, and on the 30 fresh names
nothing was ever chosen on.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from events import cost_bp                                                   # noqa: E402
from inplay import FRESH                                                     # noqa: E402

ORIGINAL = list(minute.SCALP_NAMES)
OUT = ROOT / "strategies" / "scalp" / "residual.json"


def rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        w = x[i - n:i]
        out[i] = np.nanstd(w)
    return out


def study(names: List[str], dev_days: set) -> Dict[str, dict]:
    u = minute.universe(names)
    stamps = u.calendar
    sess = np.array([minute.session_of(t) for t in stamps])
    new_sess = np.concatenate([[True], sess[1:] != sess[:-1]])
    O = np.array([np.asarray(u.bars[s].open, dtype=float) for s in names])
    C = np.array([np.asarray(u.bars[s].close, dtype=float) for s in names])
    R = np.full_like(C, np.nan)
    R[:, 1:] = C[:, 1:] / C[:, :-1] - 1.0
    R[:, new_sess] = np.nan                            # no overnight gaps
    tot = np.nansum(R, axis=0)
    cnt = np.sum(~np.isnan(R), axis=0)
    mso = np.array([(int(t[11:13]) * 60 + int(t[14:16])) for t in stamps])   # UTC minutes of day
    res: Dict[str, dict] = {}
    for i, s in enumerate(names):
        others = (tot - np.nan_to_num(R[i])) / np.maximum(cnt - (~np.isnan(R[i])).astype(int), 1)
        resid = R[i] - others
        z = resid / rolling_std(resid, 20)
        c2 = 2 * cost_bp(C[i])
        local_open = np.array([minute.session_of(t) for t in stamps])
        # minutes since the 09:30 open, from the UTC stamp and the session's first bar
        first_idx = {}
        for k, d in enumerate(local_open):
            first_idx.setdefault(d, k)
        since = np.array([k - first_idx[d] for k, d in enumerate(local_open)])
        for (wn, (a, b)), zz, h in itertools.product({"09:35-09:50": (5, 20), "09:35-10:30": (5, 60),
                                                      "all day": (5, 375)}.items(), (2.0, 3.0, 4.0), (1, 2, 3, 4)):
            cond = (z < -zz) & (since >= a) & (since <= b)
            idx = np.flatnonzero(np.nan_to_num(cond.astype(float))[: len(stamps) - 6].astype(bool))
            j, k = idx + 1, idx + 1 + h
            same = sess[j] == sess[k]
            j, k, i0 = j[same], k[same], idx[same]
            net = (O[i][k] / O[i][j] - 1.0) * 1e4 - c2
            key = f"buy residual drop z<-{zz} {wn} | hold {h}m"
            r = res.setdefault(key, {"dev": [], "test": []})
            dmask = np.array([sess[x] in dev_days for x in i0], dtype=bool)
            r["dev"].extend(net[dmask].tolist())
            r["test"].extend(net[~dmask].tolist())
    return res


def summarise(res: Dict[str, dict], ndev: int, ntest: int) -> List[dict]:
    rows = []
    for key, r in res.items():
        d, t = np.array(r["dev"]), np.array(r["test"])
        if len(d) < 20:
            continue
        rows.append({"setup": key, "dev_bp": round(float(d.mean()), 2), "dev_n_day": round(len(d) / max(ndev, 1), 1),
                     "dev_win": round(float((d > 0).mean()), 3),
                     "test_bp": round(float(t.mean()), 2) if len(t) else None,
                     "test_n_day": round(len(t) / max(ntest, 1), 1) if ntest else None})
    return rows


def main() -> int:
    days = minute.sessions(ORIGINAL)
    dev = set(days[:14])
    orig = summarise(study(ORIGINAL, dev), 14, 7)
    fresh = summarise(study(FRESH, set(days)), len(days), 0)       # all fresh sessions are out of sample
    fr = {x["setup"]: x for x in fresh}
    orig.sort(key=lambda x: x["dev_bp"] * np.sqrt(x["dev_n_day"]), reverse=True)
    out = []
    print("setup | original 17: first 14 sessions, last 7 | 30 fresh names, all 21 sessions")
    for x in orig[:24]:
        f = fr.get(x["setup"], {})
        out.append({**x, "fresh_bp": f.get("dev_bp"), "fresh_n_day": f.get("dev_n_day"), "fresh_win": f.get("dev_win")})
        print(f"  {x['setup'][:48]:48s} {x['dev_bp']:+6.1f}bp x{x['dev_n_day']:5.1f}/d, {x['test_bp']:+6.1f}bp x{x['test_n_day']:5.1f}/d "
              f"| fresh {f.get('dev_bp', float('nan')):+6.1f}bp x{f.get('dev_n_day', 0):5.1f}/d win {f.get('dev_win', 0):.0%}")
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
