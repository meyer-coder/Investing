"""What the bid-ask spread of each panel name really is during the session.

    python strategies/scalp/spreads.py [minutes=15] [--every 20]

The bounce after a sharp drop measured on mid prices is a few basis points;
whether a bot that buys at the offer and sells at the bid keeps any of it
depends on each name's spread.  Historical exchange quotes are not free, so
this samples the live best bid and offer from Nasdaq's quote service for all
72 names every `--every` seconds while the market is open, and writes each
name's median and 90th-percentile spread (in basis points of the mid) to
strategies/scalp/spreads.json, appending the session to what is there.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402

OUT = ROOT / "strategies" / "scalp" / "spreads.json"
URL = "https://api.nasdaq.com/api/quote/{sym}/info?assetclass=stocks"
TICKER = {"FB": "META", "SQ": "XYZ"}                                          # today's tickers for renamed names


def quote(sym: str):
    req = urllib.request.Request(URL.format(sym=TICKER.get(sym, sym)), headers={"User-Agent": "Mozilla/5.0",
                                                                                  "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())["data"]["primaryData"]
        bid = float(str(d["bidPrice"]).replace("$", "").replace(",", ""))
        ask = float(str(d["askPrice"]).replace("$", "").replace(",", ""))
        if bid > 0 and ask >= bid:
            return bid, ask
    except Exception:
        return None
    return None


def main() -> int:
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else 15.0
    every = float(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 20.0
    samples = {n: [] for n in panel.NAMES}
    stop = time.time() + minutes * 60
    rounds = 0
    with ThreadPoolExecutor(8) as ex:
        while time.time() < stop:
            t0 = time.time()
            for n, q in zip(panel.NAMES, ex.map(quote, panel.NAMES)):
                if q is not None:
                    bid, ask = q
                    samples[n].append((ask - bid, (ask - bid) / ((ask + bid) / 2) * 1e4))
            rounds += 1
            time.sleep(max(0.0, every - (time.time() - t0)))
    now = dt.datetime.now(dt.timezone.utc)
    ny = now.astimezone(panel.NY)
    session = {"utc": now.isoformat(timespec="seconds"), "new_york": ny.strftime("%Y-%m-%d %H:%M"), "rounds": rounds, "names": {}}
    for n, v in samples.items():
        if v:
            c = np.array([x[0] for x in v])
            bp = np.array([x[1] for x in v])
            session["names"][n] = {"n": len(v), "median_cents": round(float(np.median(c)) * 100, 1),
                                   "median_bp": round(float(np.median(bp)), 2), "p90_bp": round(float(np.percentile(bp, 90)), 2)}
    old = json.loads(OUT.read_text()) if OUT.exists() else {"sessions": []}
    old["sessions"].append(session)
    OUT.write_text(json.dumps(old, indent=1))
    got = session["names"]
    print(f"{len(got)} names quoted over {rounds} rounds ({session['new_york']} New York)")
    for n, v in sorted(got.items(), key=lambda kv: -kv[1]["median_bp"]):
        print(f"  {n:6s} median {v['median_cents']:6.1f} c = {v['median_bp']:5.2f} bp, 90th pct {v['p90_bp']:5.2f} bp ({v['n']} quotes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
