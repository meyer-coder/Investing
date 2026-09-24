"""Paper-trade the two quick trades that held up, one session at a time, after each close.

    python strategies/quick/paper.py              # replay every finished session since START not yet in the ledger
    python strategies/quick/paper.py --print      # the ledger so far

* Nasdaq-100 noise-area breakout (trend.py): on Yahoo's one-minute NQ=F bars
  (archived by strategies/soxl/minute.py), the band from the last 14
  sessions, checks every half hour, the VWAP exit, flat at the close.  Booked
  as 2 MNQ ($2 a point each, 1.25 points a round trip) and, for the $25,000
  stock account, as QQQ at 4x (the same return on $100,000, 1 bp a round trip).
* Gap breakout on large caps (stock_orb.py): the three names among the 72
  that opened more than 2% from their previous close, taking the first five
  minutes' bar direction; a stop order at that bar's high (low) after 09:35,
  a stop one 14-day average daily range away, out at the close; 2% of $25,000
  at risk a trade, at most 4x buying power in all; a cent of spread and
  $0.007 a share of fees.  Yahoo's one-minute and daily bars.

A signal shows at a bar's close and fills at the next bar's open (the stop
order at its price, or a worse open).  The ledger,
profitable-strategies/quick-trades/paper.json, is written once per session and
never recomputed.  Paper only: nothing here can place an order.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402

NY = ZoneInfo("America/New_York")
OUT = ROOT / "profitable-strategies" / "quick-trades"
LEDGER = OUT / "paper.json"
START = "2026-09-24"
ACCOUNT = 25_000.0
MNQ, POINT, MNQ_COST = 2, 2.0, 1.25
LOOKBACK, EVERY = 14, 30
TICKER = {"FB": "META", "SQ": "XYZ"}


# ---------------------------------------------------------------- Nasdaq-100 noise area on NQ=F

def _session_arrays(rows: Dict[str, tuple], day: str) -> Optional[np.ndarray]:
    """(390, 4) o/h/l/c for the day's 09:30-15:59 bars, forward-filled; None when too few bars."""
    y, m, d = map(int, day.split("-"))
    open_utc = dt.datetime(y, m, d, 9, 30, tzinfo=NY).astimezone(dt.timezone.utc)
    a = np.full((390, 4), np.nan)
    for t, v in rows.items():
        if minute.session_of(t) != day:
            continue
        k = (dt.datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc) - open_utc).seconds // 60
        if 0 <= k < 390:
            a[k] = v[:4]
    if np.isnan(a[:, 3]).sum() > 30:
        return None
    for j in range(390):
        if np.isnan(a[j, 3]):
            a[j] = a[j - 1, 3] if j else a[np.flatnonzero(~np.isnan(a[:, 3]))[0], 0]
    return a


def noise_area_day(day: str) -> Optional[dict]:
    rows = minute.read("NQ=F")
    days = sorted({minute.session_of(t) for t in rows})
    if day not in days:
        return None
    past = [d for d in days if d < day]
    arrs = {d: _session_arrays(rows, d) for d in past[-(LOOKBACK + 1):] + [day]}
    prior = [d for d in past[-(LOOKBACK + 1):] if arrs[d] is not None]
    if len(prior) < LOOKBACK + 1 or arrs[day] is None:
        return {"skipped": f"only {len(prior)} earlier sessions on file"}
    a = arrs[day]
    o, h, l, c = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    pc = arrs[prior[-1]][-1, 3]
    move = np.array([np.abs(arrs[d][:, 3] / arrs[d][0, 0] - 1.0) for d in prior[-LOOKBACK:]])
    sig = move.mean(axis=0)
    up = max(o[0], pc) * (1 + sig)
    dn = min(o[0], pc) * (1 - sig)
    vwap = np.cumsum((h + l + c) / 3) / np.arange(1, 391)
    trades, pos, px, t_in = [], 0, 0.0, 0
    for t in range(EVERY - 1, 389, EVERY):
        if pos:
            out = c[t] < max(up[t], vwap[t]) if pos > 0 else c[t] > min(dn[t], vwap[t])
            if out:
                trades.append({"side": "long" if pos > 0 else "short", "in": _hm(t_in), "entry": round(px, 2),
                               "out": _hm(t + 1), "exit": round(o[t + 1], 2), "points": round(pos * (o[t + 1] - px), 2)})
                pos = 0
                continue
        if pos == 0:
            side = 1 if c[t] > up[t] else (-1 if c[t] < dn[t] else 0)
            if side:
                pos, px, t_in = side, o[t + 1], t + 1
    if pos:
        trades.append({"side": "long" if pos > 0 else "short", "in": _hm(t_in), "entry": round(px, 2),
                       "out": "15:59 close", "exit": round(c[389], 2), "points": round(pos * (c[389] - px), 2)})
    pts = sum(x["points"] for x in trades)
    mnq_usd = pts * POINT * MNQ - MNQ_COST * POINT * MNQ * len(trades)
    ret = sum(x["points"] / x["entry"] for x in trades) - 1e-4 * len(trades)
    return {"trades": trades, "band_at_10:00": [round(dn[29], 2), round(up[29], 2)], "points": round(pts, 2),
            "mnq_usd": round(mnq_usd, 2), "qqq_4x_usd": round(ret * 4 * ACCOUNT, 2)}


def _hm(k: int) -> str:
    return f"{9 + (30 + k) // 60:02d}:{(30 + k) % 60:02d}"


# ---------------------------------------------------------------- gap breakout on large caps (Yahoo bars)

def _yahoo(sym: str, interval: str, rng: str) -> Optional[dict]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range={rng}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            return {"t": res["timestamp"], "o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"]}
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def gap_breakout_day(day: str, names=None, top: int = 3, gap_min: float = 0.02, stop_atr: float = 1.0,
                     risk: float = 0.02, lev: float = 4.0) -> dict:
    import panel
    names = names or panel.NAMES
    cands = []
    for n in names:
        sym = TICKER.get(n, n)
        dly = _yahoo(sym, "1d", "2mo")
        if not dly:
            continue
        dates = [dt.datetime.fromtimestamp(t, tz=NY).strftime("%Y-%m-%d") for t in dly["t"]]
        if day not in dates:
            continue
        i = dates.index(day)
        if i < 15 or None in dly["c"][i - 15:i + 1] or None in dly["h"][i - 14:i] or None in dly["l"][i - 14:i]:
            continue
        atr = float(np.mean([dly["h"][j] - dly["l"][j] for j in range(i - 14, i)]))
        pc, op = dly["c"][i - 1], dly["o"][i]
        g = op / pc - 1.0
        if abs(g) >= gap_min:
            cands.append((abs(g), n, sym, g, atr, pc))
    cands.sort(reverse=True)
    trades, total = [], 0.0
    per_cap = lev * ACCOUNT / top
    for _, n, sym, g, atr, pc in cands[:top]:
        m = _yahoo(sym, "1m", "5d")
        if not m:
            continue
        bars = [(dt.datetime.fromtimestamp(t, tz=NY), o, h, l, c) for t, o, h, l, c in zip(m["t"], m["o"], m["h"], m["l"], m["c"])
                if None not in (o, h, l, c)]
        bars = [b for b in bars if b[0].strftime("%Y-%m-%d") == day and (9, 30) <= (b[0].hour, b[0].minute) < (16, 0)]
        if len(bars) < 300:
            continue
        first5 = bars[:5]
        hi, lo = max(b[2] for b in first5), min(b[3] for b in first5)
        side = 1 if first5[-1][4] > first5[0][1] else (-1 if first5[-1][4] < first5[0][1] else 0)
        if not side:
            continue
        lvl = hi if side > 0 else lo
        entry = None
        for k, b in enumerate(bars[5:], 5):
            if (side > 0 and b[2] >= lvl) or (side < 0 and b[3] <= lvl):
                entry = (k, max(b[1], lvl) if side > 0 else min(b[1], lvl))
                break
        if entry is None:
            trades.append({"name": n, "gap": round(g * 100, 2), "side": "long" if side > 0 else "short", "result": "no break"})
            continue
        k0, px = entry
        stop = px - side * stop_atr * atr
        exit_px, out_t, why = bars[-1][4], bars[-1][0].strftime("%H:%M"), "close"
        for k in range(k0, len(bars)):
            b = bars[k]
            if (side > 0 and b[3] <= stop) or (side < 0 and b[2] >= stop):
                exit_px = (min(b[1], stop) if side > 0 else max(b[1], stop)) if k > k0 else stop
                out_t, why = b[0].strftime("%H:%M"), "stop"
                break
        shares = min(risk * ACCOUNT / (stop_atr * atr), per_cap / px)
        usd = side * shares * (exit_px - px) - shares * 0.017
        total += usd
        trades.append({"name": n, "gap": round(g * 100, 2), "side": "long" if side > 0 else "short", "in": bars[k0][0].strftime("%H:%M"),
                       "entry": round(px, 2), "stop": round(stop, 2), "out": out_t, "exit": round(exit_px, 2), "why": why,
                       "shares": int(shares), "usd": round(usd, 2)})
    return {"gappers": [(n, round(g * 100, 2)) for _, n, _, g, _, _ in cands[:10]], "trades": trades, "usd": round(total, 2)}


# ---------------------------------------------------------------- ledger

def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"start": START, "updated_after_close": None, "sessions": {}}


def finished_sessions() -> List[str]:
    rows = minute.read("NQ=F")
    today = dt.datetime.now(NY)
    done = []
    for d in sorted({minute.session_of(t) for t in rows}):
        if d < START:
            continue
        if d == today.strftime("%Y-%m-%d") and (today.hour, today.minute) < (16, 5):
            continue
        done.append(d)
    return done


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    led = load_ledger()
    if "--print" in sys.argv:
        print(json.dumps(led, indent=1))
        return 0
    minute.update(["NQ=F"])                                                  # add today's bars to the archive
    for day in finished_sessions():
        if day in led["sessions"]:
            continue
        na = noise_area_day(day)
        gb = gap_breakout_day(day)
        led["sessions"][day] = {"noise_area": na, "gap_breakout": gb}
        led["updated_after_close"] = day
        lines = [f"# Quick trades, {day}", ""]
        if na and "trades" in na:
            lines.append(f"Nasdaq-100 noise-area breakout: {len(na['trades'])} trade(s), {na['points']:+.2f} points; "
                         f"2 MNQ ${na['mnq_usd']:+.2f}; QQQ at 4x on $25,000 ${na['qqq_4x_usd']:+.2f}.")
            for t in na["trades"]:
                lines.append(f"- {t['side']} {t['in']} at {t['entry']}, out {t['out']} at {t['exit']} ({t['points']:+.2f} points)")
        else:
            lines.append(f"Nasdaq-100 noise-area breakout: {na}")
        lines.append("")
        lines.append(f"Gap breakout on large caps: ${gb['usd']:+.2f}. Gappers: " + ", ".join(f"{n} {g:+.1f}%" for n, g in gb["gappers"]))
        for t in gb["trades"]:
            if "usd" in t:
                lines.append(f"- {t['name']} {t['side']} {t['in']} at {t['entry']}, stop {t['stop']}, out {t['out']} at {t['exit']} "
                             f"({t['why']}), {t['shares']} shares, ${t['usd']:+.2f}")
            else:
                lines.append(f"- {t['name']} ({t['gap']:+.1f}% gap, {t['side']}): {t['result']}")
        (OUT / "paper").mkdir(exist_ok=True)
        (OUT / "paper" / f"{day}.md").write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
    LEDGER.write_text(json.dumps(led, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
