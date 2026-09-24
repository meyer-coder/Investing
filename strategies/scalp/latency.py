"""How much of the drop bounce is left a few seconds later, and is it there in the mid price?

    python strategies/scalp/latency.py

The minute study buys at the first quote of the next minute on the bid side.
Two things could make that look better than any bot could do:

* the bid alone can dip and come back when the spread widens for a moment,
  a bounce nobody can buy (the mid price is the check);
* the bounce may be over within seconds, before a bot reading minute bars has
  its order in (entries 10, 20 and 30 seconds late are the check).

Ten-second bars on both sides (duka_stocks.py --10s) for a year of the busiest
names give, for every drop signal on the minute bars, the return from each
entry time to the same holding time later: bid to bid (as the minute study),
mid to mid, and ask to bid (paying the CFD's own spread, wider than the
exchange's, so a floor).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import book                                                                  # noqa: E402

NY = ZoneInfo("America/New_York")
S10 = ROOT / "data" / "cache" / "duka" / "stocks10s"
LAGS = (0, 10, 20, 30)


def _open_epoch(date: str) -> float:
    y, m, d = map(int, date.split("-"))
    return dt.datetime(y, m, d, 9, 30, tzinfo=NY).timestamp()


def measure(d: dict, mask: np.ndarray, hold: int = 3) -> dict:
    names = list(d["names"])
    out = {"rows": []}
    for sym in sorted({p.stem[:-2] for p in S10.glob("*_B.npz")}):
        if not (S10 / f"{sym}_A.npz").exists() or sym not in names:
            continue
        b, a = np.load(S10 / f"{sym}_B.npz")["a"], np.load(S10 / f"{sym}_A.npz")["a"]
        if not len(b) or not len(a):
            continue
        tb, ta = b[:, 0], a[:, 0]
        k = names.index(sym)
        first, last = tb[0], tb[-1]
        idx = np.flatnonzero(mask & (d["name"] == k))
        for e in idx:
            date = d["date_of"][e]
            t0 = _open_epoch(date) + (int(d["f"]["minute"][e]) + 1) * 60
            if t0 < first or t0 + hold * 60 + 60 > last:
                continue
            row = {"date": date, "name": sym, "minute": int(d["f"]["minute"][e]), "z": float(d["f"]["resid_z"][e]),
                   "px": float(d["f"]["px"][e]), "y_min": float(d["y"][e, 0, list(d["horizons"]).index(hold)])}
            ok = True
            for lag in LAGS:
                ti, to = t0 + lag, t0 + lag + hold * 60
                # entry: the first quote at or after ti (a bar's open at ti, else the close of the bar that ends there)
                ib = np.searchsorted(tb, ti - (10 if lag else 0))
                ia = np.searchsorted(ta, ti - (10 if lag else 0))
                ob = np.searchsorted(tb, to)
                oa = np.searchsorted(ta, to)
                if max(ib, ob) >= len(tb) or max(ia, oa) >= len(ta):
                    ok = False
                    break
                if lag == 0:
                    if tb[ib] != ti or ta[ia] != ti:
                        ok = False
                        break
                    bid_in, ask_in = b[ib, 1], a[ia, 1]
                else:
                    if tb[ib] != ti - 10 or ta[ia] != ti - 10:
                        ok = False
                        break
                    bid_in, ask_in = b[ib, 4], a[ia, 4]
                if abs(tb[ob] - to) > 30 or abs(ta[oa] - to) > 30:
                    ok = False
                    break
                bid_out, ask_out = b[ob, 1], a[oa, 1]
                mid_in, mid_out = (bid_in + ask_in) / 2, (bid_out + ask_out) / 2
                row[f"bid_{lag}"] = bid_out / bid_in - 1.0
                row[f"mid_{lag}"] = mid_out / mid_in - 1.0
                row[f"ask_bid_{lag}"] = bid_out / ask_in - 1.0
                row[f"spread_{lag}"] = (ask_in - bid_in) / mid_in
            if ok:
                out["rows"].append(row)
    return out


def summarize(rows, label):
    if not rows:
        print(f"  {label}: no events")
        return {}
    r = {k: np.array([x[k] for x in rows]) for k in rows[0] if k not in ("date", "name")}
    cost = (0.01 / r["px"] + 1e-4) * 1e4
    s = {"events": len(rows), "minute_bars_bid": round(float(r["y_min"].mean() * 1e4), 2),
         "tight_cost_bp": round(float(cost.mean()), 2)}
    for lag in LAGS:
        s[f"lag{lag}"] = {"bid": round(float(r[f"bid_{lag}"].mean() * 1e4), 2), "mid": round(float(r[f"mid_{lag}"].mean() * 1e4), 2),
                          "ask_to_bid": round(float(r[f"ask_bid_{lag}"].mean() * 1e4), 2),
                          "cfd_spread": round(float(r[f"spread_{lag}"].mean() * 1e4), 2)}
    print(f"  {label}: {len(rows)} events; minute-bar bid return {s['minute_bars_bid']:+.2f} bp; tight cost {s['tight_cost_bp']:.2f} bp")
    for lag in LAGS:
        x = s[f"lag{lag}"]
        print(f"     enter {lag:2d}s late: bid {x['bid']:+6.2f} | mid {x['mid']:+6.2f} | ask->bid {x['ask_to_bid']:+6.2f} | CFD spread {x['cfd_spread']:.2f} bp")
    return s


def main() -> int:
    d = book.load()
    f = d["f"]
    recent = d["date_of"] >= "2025-09-24"
    sets = {
        "own drop 09:35-10:00 k1.5 z1.5": (f["r1_atr"] < -1.5) & (f["resid_z"] < -1.5) & (f["minute"] >= 5) & (f["minute"] <= 30),
        "own drop all day k1.5 z3.0": (f["r1_atr"] < -1.5) & (f["resid_z"] < -3.0) & (f["minute"] >= 5) & (f["minute"] <= 380),
        "own drop all day k1.0 z2.0": (f["r1_atr"] < -1.0) & (f["resid_z"] < -2.0) & (f["minute"] >= 5) & (f["minute"] <= 380),
    }
    res = {}
    for label, m in sets.items():
        rows = measure(d, m & recent)["rows"]
        res[label] = summarize(rows, label)
        by_name = {}
        for x in rows:
            by_name.setdefault(x["name"], []).append(x["mid_0"] - x["bid_0"] * 0)
        res[label]["by_name_mid0_bp"] = {k: round(float(np.mean(v) * 1e4), 2) for k, v in sorted(by_name.items())}
    (ROOT / "strategies" / "scalp" / "latency.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
