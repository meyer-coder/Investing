"""The best book's own trades, replayed on one-second quotes: what is left after 1 to 10 seconds?

    python strategies/scalp/onesec.py [--book open|model] [--from 2025-09-24] [--every 3]

latency.py and fastdrop.py use ten-second bars.  A bot that reads minute bars
from a live feed gets each bar a second or two after it closes and is filled
a moment later, so the question is what the bounce is worth 1, 2, 3, 5 and 10
seconds after the signal minute ends.  For every trade the opening-window
own-drop book (09:35-10:00, k1.5, z1.5, three slots, three-minute hold) made
in the period, this fetches one-second bid and offer bars from Dukascopy
around the entry and measures the mid-to-mid return for each entry delay
(same three-minute hold), and ask-to-bid on the CFD's own (wider) spread.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import book                                                                  # noqa: E402

NY = ZoneInfo("America/New_York")
CACHE = ROOT / "data" / "cache" / "duka" / "onesec"
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument={sym}.US%2FUSD&offer_side={side}&interval=1SEC"
       "&splits=true&stocks=true&limit=260&time_direction=N&timestamp={ms}&jsonp=cb")
LAGS = (0, 1, 2, 3, 5, 10)
HOLD = 180


def _get(sym: str, side: str, ms: int):
    req = urllib.request.Request(URL.format(sym=sym, side=side, ms=ms), headers={"User-Agent": "Mozilla/5.0",
                                                                                  "Referer": "https://freeserv.dukascopy.com/"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode()
            rows = [x for x in json.loads(text[text.index("(") + 1:text.rindex(")")]) if x]
            return np.array([[x[0] / 1000.0, x[1], x[2], x[3], x[4]] for x in rows]) if rows else np.zeros((0, 5))
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def trades(start: str, which: str = "open"):
    """The trades of the opening-window book ("open") or of the model's book (dropmodel.py, "model")."""
    d = book.load()
    f = d["f"]
    if which == "model":
        taken = list(np.load(book.candidates.panel.CACHE / "model_trades.npy"))
    else:
        m = (f["r1_atr"] < -1.5) & (f["resid_z"] < -1.5) & (f["minute"] >= 5) & (f["minute"] <= 30)
        taken = []
        book.replay(d, m, np.ones(len(m)), -f["resid_z"], hold=3, slots=3, taken=taken)
    out = []
    for e in taken:
        if d["date_of"][e] >= start:
            out.append({"date": str(d["date_of"][e]), "name": str(d["names"][d["name"][e]]), "minute": int(f["minute"][e]),
                        "px": float(f["px"][e]), "y_min": float(d["y"][e, 0, 2])})
    return out


def measure(tr: dict):
    y, mo, da = map(int, tr["date"].split("-"))
    t0 = dt.datetime(y, mo, da, 9, 30, tzinfo=NY).timestamp() + (tr["minute"] + 1) * 60
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{tr['date']}_{tr['name']}_{tr['minute']}.npz"
    if path.exists():
        z = np.load(path)
        b, a = z["b"], z["a"]
    else:
        b = _get(tr["name"], "B", int((t0 - 5) * 1000))
        a = _get(tr["name"], "A", int((t0 - 5) * 1000))
        if b is None or a is None:
            return None
        np.savez_compressed(path, b=b, a=a)
    if len(b) < 100 or len(a) < 100:
        return None

    def quote(arr, t):
        """The last price at or before time t (the close of the last bar that started before t)."""
        j = np.searchsorted(arr[:, 0], t, side="right") - 1
        if j < 0:
            return None
        # a bar starting exactly at t: its open is the first price at t
        if arr[j, 0] == t:
            return arr[j, 1]
        return arr[j, 4]

    row = dict(tr)
    for lag in LAGS:
        bi, ai = quote(b, t0 + lag), quote(a, t0 + lag)
        bo, ao = quote(b, t0 + lag + HOLD), quote(a, t0 + lag + HOLD)
        if None in (bi, ai, bo, ao):
            return None
        row[f"mid_{lag}"] = ((bo + ao) / 2) / ((bi + ai) / 2) - 1.0
        row[f"bid_{lag}"] = bo / bi - 1.0
        row[f"ab_{lag}"] = bo / ai - 1.0
    return row


def main() -> int:
    start = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "2025-09-24"
    every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 1
    which = sys.argv[sys.argv.index("--book") + 1] if "--book" in sys.argv else "open"
    tr = trades(start, which)[::every]
    print(f"{len(tr)} trades of the {which} book since {start} (every {every})", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:
        got = list(ex.map(measure, tr))
    rows = [r for r in got if r is not None]
    cost = np.array([(0.01 / r["px"] + 1e-4) for r in rows]) * 1e4
    res = {"trades": len(rows), "from": start, "minute_bar_bid_bp": round(float(np.mean([r["y_min"] for r in rows]) * 1e4), 2),
           "tight_cost_bp": round(float(cost.mean()), 2), "by_lag": {}}
    print(f"{len(rows)} trades measured; minute-bar bid return {res['minute_bar_bid_bp']:+.2f} bp, tight cost {res['tight_cost_bp']:.2f} bp")
    for lag in LAGS:
        mid = np.array([r[f"mid_{lag}"] for r in rows]) * 1e4
        bid = np.array([r[f"bid_{lag}"] for r in rows]) * 1e4
        ab = np.array([r[f"ab_{lag}"] for r in rows]) * 1e4
        res["by_lag"][lag] = {"mid_bp": round(float(mid.mean()), 2), "bid_bp": round(float(bid.mean()), 2),
                              "ask_to_bid_bp": round(float(ab.mean()), 2), "mid_net_tight_bp": round(float((mid - cost).mean()), 2),
                              "win_mid": round(float((mid > 0).mean()), 3)}
        x = res["by_lag"][lag]
        print(f"  enter {lag:2d}s after the minute: mid {x['mid_bp']:+6.2f} | bid {x['bid_bp']:+6.2f} | ask->bid {x['ask_to_bid_bp']:+6.2f} "
              f"| mid less tight cost {x['mid_net_tight_bp']:+6.2f} bp | mid up {x['win_mid']:.0%}", flush=True)
    res["book"] = which
    (ROOT / "strategies" / "scalp" / f"onesec_{which}.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
