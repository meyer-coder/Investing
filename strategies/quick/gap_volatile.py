"""The gap breakout on volatile single stocks: 60 days of five-minute bars and two years of hourly bars.

    python strategies/quick/gap_volatile.py

The gap breakout (stock_orb.py) made $30-60 a day on 72 large caps over four
years.  The published results came from "stocks in play", names that move far
more, and one month on 47 volatile names looked much stronger.  Minute bars
for those names go back only 30 days (Yahoo), so this tests what Yahoo keeps
longer, on about 70 volatile single stocks (no leveraged or inverse funds):

* five-minute bars for 60 days: the rule as written, the opening range being
  the first five-minute bar; entries, stops and exits on five-minute bars (a
  bar that reaches both the entry and the stop counts the stop);
* hourly bars for two years: the same rule with the first hour as the range,
  a coarser cousin that shows whether the edge lasts beyond one quarter.

Each morning the `top` names that opened at least `gap` from the previous close
are traded in the first bar's direction, with a stop one 14-day average daily
range away and out at the close; 2% of $25,000 at risk a trade, at most 4x
buying power split over the names, a cent of spread and $0.007 a share.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NY = ZoneInfo("America/New_York")
CACHE = ROOT / "data" / "cache" / "quick" / "yahoo"
ACCOUNT = 25_000.0
NAMES = ["MSTR", "COIN", "SMCI", "PLTR", "HOOD", "RKLB", "IONQ", "ARM", "CRWD", "NET", "SHOP", "APP", "CVNA", "SNOW", "DDOG",
         "AFRM", "RDDT", "ASTS", "HIMS", "OKLO", "CRWV", "DELL", "MU", "AMD", "NVDA", "TSLA", "META", "AVGO", "MRVL", "ANET",
         "UBER", "NFLX", "ORCL", "INTC", "QCOM", "LRCX", "AMAT", "KLAC", "MARA", "RIOT", "CLSK", "UPST", "SOFI", "RIVN", "LCID",
         "PLUG", "AI", "PATH", "U", "DKNG", "RBLX", "ROKU", "ENPH", "FSLR", "TTD", "ZS", "OKTA", "MDB", "TEAM", "SNAP", "PINS",
         "ABNB", "DASH", "LYFT", "BILL", "NIO", "XPEV", "LI", "BABA", "PDD", "JD", "SQ", "PYPL", "W", "CHWY", "GME", "AMC"]
TICKER = {"SQ": "XYZ"}


def yahoo(sym: str, interval: str, rng: str) -> Optional[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{sym}_{interval}_{rng}.json"
    if path.exists() and time.time() - path.stat().st_mtime < 6 * 3600:
        return json.loads(path.read_text())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{TICKER.get(sym, sym)}?interval={interval}&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            out = {"t": res["timestamp"], "o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"]}
            path.write_text(json.dumps(out))
            return out
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def sessions(bars: dict) -> Dict[str, List[tuple]]:
    """{date: [(time, o, h, l, c)]} for regular-hours bars."""
    out: Dict[str, List[tuple]] = {}
    for t, o, h, l, c in zip(bars["t"], bars["o"], bars["h"], bars["l"], bars["c"]):
        if None in (o, h, l, c):
            continue
        x = dt.datetime.fromtimestamp(t, tz=NY)
        if (9, 30) <= (x.hour, x.minute) < (16, 0):
            out.setdefault(x.strftime("%Y-%m-%d"), []).append((x, o, h, l, c))
    return out


def run(daily: Dict[str, dict], intraday: Dict[str, Dict[str, List[tuple]]], gap: float = 0.02, top: int = 3,
        stop_atr: float = 1.0, risk: float = 0.02, lev: float = 4.0, min_bars: int = 60):
    days = sorted({d for s in intraday.values() for d, b in s.items() if len(b) >= min_bars})
    per_day = {}
    for day in days:
        cands = []
        for s, dly in daily.items():
            if s not in intraday or day not in intraday[s]:
                continue
            ds = dly["dates"]
            if day not in ds:
                continue
            i = ds.index(day)
            if i < 15 or dly["o"][i] is None or dly["c"][i - 1] is None or None in dly["h"][i - 14:i] or None in dly["l"][i - 14:i]:
                continue
            atr = float(np.mean([dly["h"][j] - dly["l"][j] for j in range(i - 14, i)]))
            g = dly["o"][i] / dly["c"][i - 1] - 1.0
            if abs(g) >= gap and atr > 0:
                cands.append((abs(g), s, g, atr))
        cands.sort(reverse=True)
        tot, trades = 0.0, []
        for _, s, g, atr in cands[:top]:
            bars = intraday[s][day]
            if len(bars) < min_bars:
                continue
            f = bars[0]
            hi, lo = f[2], f[3]
            side = 1 if f[4] > f[1] else (-1 if f[4] < f[1] else 0)
            if not side:
                continue
            lvl = hi if side > 0 else lo
            k0 = next((k for k in range(1, len(bars)) if (side > 0 and bars[k][2] >= lvl) or (side < 0 and bars[k][3] <= lvl)), None)
            if k0 is None:
                continue
            px = max(bars[k0][1], lvl) if side > 0 else min(bars[k0][1], lvl)
            stop = px - side * stop_atr * atr
            out = bars[-1][4]
            for k in range(k0, len(bars)):
                if (side > 0 and bars[k][3] <= stop) or (side < 0 and bars[k][2] >= stop):
                    out = stop if k == k0 else (min(bars[k][1], stop) if side > 0 else max(bars[k][1], stop))
                    break
            sh = min(risk * ACCOUNT / (stop_atr * atr), lev * ACCOUNT / top / px)
            usd = side * sh * (out - px) - sh * 0.017
            tot += usd
            trades.append((s, side, round(usd, 0)))
        per_day[day] = (tot, trades)
    return per_day


def summary(per_day, label):
    v = np.array([x[0] for x in per_day.values()])
    ds = sorted(per_day)
    eq = np.cumsum([per_day[d][0] for d in ds])
    dd = float((eq - np.maximum.accumulate(eq)).min()) if len(eq) else 0.0
    halves = [np.mean([per_day[d][0] for d in ds[:len(ds) // 2]]), np.mean([per_day[d][0] for d in ds[len(ds) // 2:]])] if len(ds) > 1 else [0, 0]
    row = {"sessions": len(v), "usd_per_day": round(float(v.mean()), 1), "median": round(float(np.median(v)), 1),
           "up": round(float((v > 0).mean()), 3), "days_200": round(float((v >= 200).mean()), 3), "worst_day": round(float(v.min()), 0),
           "best_day": round(float(v.max()), 0), "max_drawdown": round(dd, 0), "first_half": round(float(halves[0]), 1),
           "second_half": round(float(halves[1]), 1), "sharpe": round(float(v.mean() / (v.std() + 1e-9) * np.sqrt(252)), 2),
           "se_of_mean": round(float(v.std() / np.sqrt(max(len(v), 1))), 1)}
    print(f"  {label:46s} {row['sessions']:4d} sessions ${row['usd_per_day']:+6.0f} a day (+/- {row['se_of_mean']:.0f}; median ${row['median']:+.0f}) "
          f"| halves ${row['first_half']:+.0f} / ${row['second_half']:+.0f} | up {row['up']:.0%} $200+ {row['days_200']:.0%} | "
          f"worst ${row['worst_day']:+.0f} dd ${row['max_drawdown']:+.0f} | Sharpe {row['sharpe']:+.2f}", flush=True)
    return row


def main() -> int:
    daily, five, hour = {}, {}, {}
    for s in NAMES:
        d = yahoo(s, "1d", "3y")
        if not d:
            continue
        d["dates"] = [dt.datetime.fromtimestamp(t, tz=NY).strftime("%Y-%m-%d") for t in d["t"]]
        daily[s] = d
        f = yahoo(s, "5m", "60d")
        if f:
            five[s] = sessions(f)
        h = yahoo(s, "60m", "730d")
        if h:
            hour[s] = sessions(h)
    print(f"{len(daily)} names with daily bars, {len(five)} with five-minute bars, {len(hour)} with hourly bars")
    res = {"five_minute": {}, "hourly": {}}
    for g, top, sa in itertools.product((0.02, 0.03, 0.05), (1, 3, 5), (0.5, 1.0)):
        label = f"gap>{g:.0%} top {top} stop {sa} ATR"
        res["five_minute"][label] = summary(run(daily, five, g, top, sa, min_bars=70), "5-min ORB | " + label)
    for g, top, sa in itertools.product((0.02, 0.03, 0.05), (1, 3, 5), (0.5, 1.0)):
        label = f"gap>{g:.0%} top {top} stop {sa} ATR"
        res["hourly"][label] = summary(run(daily, hour, g, top, sa, min_bars=6), "first-hour range | " + label)
    (ROOT / "strategies" / "quick" / "gap_volatile.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
