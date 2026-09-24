"""Today's quick-trade signals while the market is open (paper): what the two bots would do right now.

    python strategies/quick/live.py gaps      # after 09:35: the gap breakout's three names, levels, stops, shares
    python strategies/quick/live.py nasdaq    # the noise-area band on QQQ and the position it implies so far
    python strategies/quick/live.py watch     # both, then the Nasdaq check every half hour until the close

Yahoo's one-minute bars (QQQ and the stocks are real time; NQ futures there
are ten minutes late, so the live check uses QQQ, which carries the same
signal).  The rules are paper.py's.  Nothing here places an order.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
import paper                                                                 # noqa: E402

NY = ZoneInfo("America/New_York")
LOG = ROOT / "profitable-strategies" / "quick-trades" / "live"


def now_ny():
    return dt.datetime.now(NY)


def gaps(day=None, top=3, gap_min=0.02, stop_atr=1.0, risk=0.02, lev=4.0):
    import panel
    day = day or now_ny().strftime("%Y-%m-%d")
    cands = []
    for n in panel.NAMES:
        sym = paper.TICKER.get(n, n)
        dly = paper._yahoo(sym, "1d", "2mo")
        if not dly:
            continue
        ds = [dt.datetime.fromtimestamp(t, tz=NY).strftime("%Y-%m-%d") for t in dly["t"]]
        if day not in ds:
            continue
        i = ds.index(day)
        if i < 15 or dly["o"][i] is None or None in dly["c"][i - 1:i] or None in dly["h"][i - 14:i] or None in dly["l"][i - 14:i]:
            continue
        atr = float(np.mean([dly["h"][j] - dly["l"][j] for j in range(i - 14, i)]))
        g = dly["o"][i] / dly["c"][i - 1] - 1.0
        if abs(g) >= gap_min:
            cands.append((abs(g), n, sym, g, atr))
    cands.sort(reverse=True)
    out = []
    for _, n, sym, g, atr in cands[:top]:
        m = paper._yahoo(sym, "1m", "1d")
        bars = [(dt.datetime.fromtimestamp(t, tz=NY), o, h, l, c) for t, o, h, l, c in zip(m["t"], m["o"], m["h"], m["l"], m["c"])
                if None not in (o, h, l, c)] if m else []
        bars = [b for b in bars if (9, 30) <= (b[0].hour, b[0].minute) < (16, 0)]
        if len(bars) < 5:
            out.append({"name": n, "gap_pct": round(g * 100, 2), "note": "first five minutes not in yet"})
            continue
        f5 = bars[:5]
        hi, lo = max(b[2] for b in f5), min(b[3] for b in f5)
        side = 1 if f5[-1][4] > f5[0][1] else (-1 if f5[-1][4] < f5[0][1] else 0)
        if not side:
            out.append({"name": n, "gap_pct": round(g * 100, 2), "note": "first five minutes flat: no trade"})
            continue
        lvl = hi if side > 0 else lo
        shares = int(min(risk * paper.ACCOUNT / (stop_atr * atr), lev * paper.ACCOUNT / top / lvl))
        trig = next((b for b in bars[5:] if (side > 0 and b[2] >= lvl) or (side < 0 and b[3] <= lvl)), None)
        out.append({"name": n, "gap_pct": round(g * 100, 2), "order": ("buy stop" if side > 0 else "sell-short stop"),
                    "level": round(lvl, 2), "protective_stop": round(lvl - side * stop_atr * atr, 2), "shares": shares,
                    "risk_usd": round(shares * stop_atr * atr, 0), "last": round(bars[-1][4], 2),
                    "triggered_at": trig[0].strftime("%H:%M") if trig else None})
    return {"day": day, "gappers": [(n, round(g * 100, 2)) for _, n, _, g, _ in cands[:8]], "orders": out}


def nasdaq(symbol="QQQ", lookback=14, every=30):
    rows = minute.fetch(symbol, days=25)
    days = sorted({minute.session_of(t) for t in rows})
    today = now_ny().strftime("%Y-%m-%d")
    past = [d for d in days if d < today]
    arrs = {d: paper._session_arrays(rows, d) for d in past[-(lookback + 1):]}
    prior = [d for d in past[-(lookback + 1):] if arrs[d] is not None]
    if len(prior) < lookback:
        return {"error": f"only {len(prior)} earlier sessions"}
    # today so far, bar by bar
    y, m, d = map(int, today.split("-"))
    open_utc = dt.datetime(y, m, d, 9, 30, tzinfo=NY).astimezone(dt.timezone.utc)
    a = np.full((390, 4), np.nan)
    for t, v in rows.items():
        if minute.session_of(t) == today:
            k = int((dt.datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc) - open_utc).total_seconds() // 60)
            if 0 <= k < 390:
                a[k] = v[:4]
    have = np.flatnonzero(~np.isnan(a[:, 3]))
    if not len(have):
        return {"day": today, "note": "no bars yet today"}
    last = int(have[-1])
    for j in range(last + 1):
        if np.isnan(a[j, 3]):
            a[j] = a[j - 1, 3] if j else a[have[0], 0]
    o, h, l, c = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    pc = arrs[prior[-1]][-1, 3]
    sig = np.array([np.abs(arrs[x][:, 3] / arrs[x][0, 0] - 1.0) for x in prior[-lookback:]]).mean(axis=0)
    up = max(o[0], pc) * (1 + sig)
    dn = min(o[0], pc) * (1 - sig)
    vwap = np.cumsum((h + l + c) / 3) / np.arange(1, 391)
    pos, px, log = 0, 0.0, []
    for t in range(every - 1, min(last, 388) + 1, every):
        if t + 1 > last and pos == 0:
            pass
        if pos:
            out = c[t] < max(up[t], vwap[t]) if pos > 0 else c[t] > min(dn[t], vwap[t])
            if out:
                fill = o[t + 1] if t + 1 <= last else None
                log.append(f"{paper._hm(t + 1)} exit {'long' if pos > 0 else 'short'} at {fill if fill else 'next open'}")
                pos = 0
                continue
        if pos == 0:
            side = 1 if c[t] > up[t] else (-1 if c[t] < dn[t] else 0)
            if side:
                pos = side
                px = o[t + 1] if t + 1 <= last else float("nan")
                log.append(f"{paper._hm(t + 1)} {'buy' if side > 0 else 'sell short'} at {round(px, 2) if px == px else 'next open'}")
    return {"day": today, "symbol": symbol, "as_of": paper._hm(last), "price": round(c[last], 2),
            "band_now": [round(dn[last], 2), round(up[last], 2)], "vwap": round(vwap[last], 2),
            "position": {1: "long", -1: "short", 0: "flat"}[pos], "entry": round(px, 2) if pos else None,
            "open_pnl_pct": round(pos * (c[last] / px - 1.0) * 100, 3) if pos and px == px else None, "log": log}


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else "watch"
    LOG.mkdir(parents=True, exist_ok=True)
    if what == "gaps":
        print(json.dumps(gaps(), indent=1))
    elif what == "nasdaq":
        print(json.dumps(nasdaq(), indent=1))
    else:
        path = LOG / f"{now_ny():%Y-%m-%d}.jsonl"
        done = set()
        while now_ny().hour < 16:
            t = now_ny()
            mins = (t.hour - 9) * 60 + t.minute - 30
            key = None
            if mins >= 6 and "gaps" not in done:
                key = "gaps"
                rec = {"at": t.strftime("%H:%M"), "gaps": gaps()}
            elif mins >= 31 and (mins - 1) % 30 == 0 and mins not in done:
                key = mins
                rec = {"at": t.strftime("%H:%M"), "nasdaq": nasdaq()}
            if key is not None:
                done.add(key)
                with path.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(json.dumps(rec), flush=True)
            time.sleep(20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
