"""Split factors for the stock panel: what a share really cost that day.

    python strategies/scalp/splits.py            # fetch and cache
    from splits import factors                  # {name: {date: raw / adjusted}}

The Dukascopy minutes are split-adjusted, so NVDA in 2023 reads about $40
where the shares traded near $400.  Costs quoted per share (a cent of spread)
must be charged on the price actually paid, or a pre-split name looks ten
times as expensive to trade as it was.  Daily bars with and without the
adjustment give the factor for each session.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402

CACHE = ROOT / "strategies" / "scalp" / "splits.json"                      # small; kept with the code
URL = ("https://freeserv.dukascopy.com/2.0/?path=chart/json3&instrument={sym}.US%2FUSD&offer_side=B&interval=1DAY"
       "&splits={adj}&stocks=true&limit=2000&time_direction=N&timestamp={ms}&jsonp=cb")


def _daily(sym: str, adj: str, ms: int):
    req = urllib.request.Request(URL.format(sym=sym, adj=adj, ms=ms), headers={"User-Agent": "Mozilla/5.0",
                                                                                "Referer": "https://freeserv.dukascopy.com/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode()
    rows = [x for x in json.loads(text[text.index("(") + 1:text.rindex(")")]) if x]
    return {time.strftime("%Y-%m-%d", time.gmtime(x[0] / 1000)): x[4] for x in rows}


def fetch(start_ms: int = 1661990400000) -> Dict[str, Dict[str, float]]:
    out = {}
    for sym in panel.NAMES:
        adj, raw = _daily(sym, "true", start_ms), _daily(sym, "false", start_ms)
        f = {d: round(raw[d] / adj[d], 4) for d in adj if d in raw and adj[d] > 0}
        out[sym] = {d: v for d, v in f.items() if abs(v - 1.0) > 0.01}
        time.sleep(1.0)
    CACHE.write_text(json.dumps(out))
    return out


def factors() -> Dict[str, Dict[str, float]]:
    return json.loads(CACHE.read_text())


def matrix(dates, names) -> np.ndarray:
    """(days, names): raw price / adjusted price, 1 where no split came later."""
    f = factors()
    m = np.ones((len(dates), len(names)))
    for k, n in enumerate(names):
        for i, d in enumerate(dates):
            m[i, k] = f.get(n, {}).get(d, 1.0)
    return m


if __name__ == "__main__":
    got = fetch()
    for sym, f in got.items():
        if f:
            ds = sorted(f)
            print(f"{sym}: x{f[ds[0]]} from {ds[0]} to {ds[-1]} ({len(ds)} sessions)")
