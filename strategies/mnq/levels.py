"""Options-derived levels for the Nasdaq-100, the way GEX traders draw them.

    python strategies/mnq/levels.py              # today's levels from CBOE's delayed QQQ chain, in NQ points
    python strategies/mnq/levels.py --save       # also write data/levels/<date>.json

From CBOE's free delayed option chain for QQQ (open interest, implied
volatility and gamma for every contract), for the contracts expiring in the
next 45 days:

* gamma exposure by strike: gamma x open interest x 100 x spot^2 x 1%, calls
  counted positive and puts negative (the usual assumption that dealers are
  long the calls customers sell and short the puts they buy);
* the gamma flip: the price where the total exposure, recomputed with
  Black-Scholes at each candidate price from each contract's own implied
  volatility, changes sign (above it dealers damp moves, below it they chase);
* the call wall and the put wall: the strikes with the most call and put
  exposure;
* max pain for the nearest expiry: the price at which that expiry's option
  holders would collect the least.

QQQ levels become NQ points through the ratio of the two prices at the time
of the snapshot.  These are approximations of what paid services sell; they
are for testing whether price reacts at them, not for trading on faith.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "levels"
URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{sym}.json"
RATE, DIVIDEND = 0.04, 0.006
HORIZON_DAYS = 45


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def chain(sym: str = "QQQ") -> dict:
    return _get_json(URL.format(sym=sym))


def parse(option: str):
    """'QQQ260922C00500000' -> (expiry date, 'C' or 'P', strike)."""
    tail = option[-15:]
    exp = dt.date(2000 + int(tail[0:2]), int(tail[2:4]), int(tail[4:6]))
    return exp, tail[6], int(tail[7:]) / 1000.0


def _bs_gamma(s: np.ndarray, k: np.ndarray, t: np.ndarray, iv: np.ndarray) -> np.ndarray:
    sig = np.maximum(iv, 0.01)
    t = np.maximum(t, 1.0 / 365 / 24)
    d1 = (np.log(s / k) + (RATE - DIVIDEND + 0.5 * sig ** 2) * t) / (sig * np.sqrt(t))
    return np.exp(-DIVIDEND * t) * np.exp(-0.5 * d1 ** 2) / (np.sqrt(2 * np.pi) * s * sig * np.sqrt(t))


def compute(raw: dict, today: Optional[dt.date] = None) -> dict:
    data = raw["data"]
    spot = float(data["current_price"])
    today = today or dt.date.today()
    rows = []
    for o in data["options"]:
        exp, cp, k = parse(o["option"])
        days = (exp - today).days
        oi = float(o.get("open_interest") or 0.0)
        if days < 0 or days > HORIZON_DAYS or oi <= 0:
            continue
        rows.append((exp, cp, k, oi, float(o.get("iv") or 0.0), float(o.get("gamma") or 0.0), days))
    if not rows:
        raise ValueError("no contracts with open interest in the horizon")
    exp = np.array([r[0] for r in rows])
    cp = np.array([r[1] for r in rows])
    k = np.array([r[2] for r in rows])
    oi = np.array([r[3] for r in rows])
    iv = np.array([r[4] for r in rows])
    gam = np.array([r[5] for r in rows])
    t = np.array([(r[6] + 0.25) / 365.0 for r in rows])        # a quarter day left on the expiry day itself
    sign = np.where(cp == "C", 1.0, -1.0)
    gex = sign * gam * oi * 100 * spot ** 2 * 0.01              # dollars of delta per 1% move
    by_strike: Dict[float, float] = {}
    calls: Dict[float, float] = {}
    puts: Dict[float, float] = {}
    for kk, g, c in zip(k, gex, cp):
        by_strike[kk] = by_strike.get(kk, 0.0) + g
        (calls if c == "C" else puts)[kk] = (calls if c == "C" else puts).get(kk, 0.0) + abs(g)
    # the gamma flip: total exposure recomputed at candidate prices from each contract's own volatility
    grid = spot * np.linspace(0.9, 1.1, 401)
    ok = iv > 0
    prof = np.array([np.sum(sign[ok] * _bs_gamma(np.full(ok.sum(), s), k[ok], t[ok], iv[ok]) * oi[ok] * 100 * s ** 2 * 0.01)
                     for s in grid])
    flip = None
    cross = np.flatnonzero(np.sign(prof[:-1]) != np.sign(prof[1:]))
    if len(cross):
        j = cross[np.argmin(np.abs(grid[cross] - spot))]         # the crossing nearest the price
        flip = float(grid[j] - prof[j] * (grid[j + 1] - grid[j]) / (prof[j + 1] - prof[j]))
    # max pain for the nearest expiry
    first = min(exp)
    sel = exp == first
    strikes = np.unique(k[sel])
    pain = [np.sum(np.where(cp[sel] == "C", np.maximum(p - k[sel], 0), np.maximum(k[sel] - p, 0)) * oi[sel]) for p in strikes]
    max_pain = float(strikes[int(np.argmin(pain))])
    top = sorted(by_strike.items(), key=lambda kv: -abs(kv[1]))[:6]
    return {"symbol": data.get("symbol", "QQQ"), "spot": spot, "timestamp": raw.get("timestamp"),
            "contracts": len(rows), "expiries": sorted({str(e) for e in exp}),
            "total_gex_usd_per_1pct": round(float(np.sum(gex)), 0),
            "gamma_flip": round(flip, 2) if flip else None,
            "call_wall": float(max(calls, key=calls.get)), "put_wall": float(max(puts, key=puts.get)),
            "max_pain": max_pain, "max_pain_expiry": str(first),
            "largest_strikes": [(float(kk), round(float(g), 0)) for kk, g in top]}


def nq_ratio() -> Optional[float]:
    """NQ futures over QQQ, from Yahoo's latest one-minute prices."""
    try:
        def last(sym):
            j = _get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d")
            return float(j["chart"]["result"][0]["meta"]["regularMarketPrice"])
        return last("NQ=F") / last("QQQ")
    except Exception:
        return None


NASDAQ = ("https://api.nasdaq.com/api/quote/{sym}/option-chain?assetclass=etf&limit=10000&fromdate={a}&todate={b}"
          "&excode=oprac&callput=callput&money=all&type=all")
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0 Safari/537.36",
           "Accept": "application/json, text/plain, */*", "Origin": "https://www.nasdaq.com",
           "Referer": "https://www.nasdaq.com/"}


def _bs_price(s, k, t, iv, call):
    from math import erf
    sig = np.maximum(iv, 1e-4)
    d1 = (np.log(s / k) + (RATE - DIVIDEND + 0.5 * sig ** 2) * t) / (sig * np.sqrt(t))
    d2 = d1 - sig * np.sqrt(t)
    n = np.vectorize(lambda x: 0.5 * (1 + erf(x / math.sqrt(2))))
    c = s * np.exp(-DIVIDEND * t) * n(d1) - k * np.exp(-RATE * t) * n(d2)
    p = k * np.exp(-RATE * t) * n(-d2) - s * np.exp(-DIVIDEND * t) * n(-d1)
    return np.where(call, c, p)


def implied_vol(price, s, k, t, call) -> np.ndarray:
    """Bisection on Black-Scholes, 1% to 300% a year; NaN where the price is below intrinsic."""
    lo, hi = np.full(len(k), 0.01), np.full(len(k), 3.0)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        too_high = _bs_price(s, k, t, mid, call) > price
        hi = np.where(too_high, mid, hi)
        lo = np.where(too_high, lo, mid)
    iv = 0.5 * (lo + hi)
    intrinsic = np.where(call, np.maximum(s - k * np.exp(-RATE * t), 0), np.maximum(k * np.exp(-RATE * t) - s, 0))
    return np.where((price > intrinsic + 1e-3) & (iv > 0.011) & (iv < 2.99), iv, np.nan)


def nasdaq_chain(sym: str = "QQQ", days: int = HORIZON_DAYS, session: Optional[dt.date] = None) -> dict:
    """Nasdaq's option chain as CBOE-shaped data (spot, and per contract: option code,
    open interest, implied volatility and gamma worked out from the bid/ask mid).  The
    volatility is solved at the chain's close; gamma is taken at `session` when that is later."""
    today = dt.date.today()
    url = NASDAQ.format(sym=sym, a=today.isoformat(), b=(today + dt.timedelta(days=days)).isoformat())
    req = urllib.request.Request(url, headers=BROWSER)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())["data"]
    last = d["lastTrade"]                                        # "LAST TRADE: $741.21 (AS OF SEP 23, 2026)"
    spot = float(last.split("$")[1].split()[0].replace(",", ""))
    asof = dt.datetime.strptime(last.split("AS OF ")[1].rstrip(")").title(), "%b %d, %Y").date()
    rows, exp = [], None
    for r in d["table"]["rows"]:
        if r["expirygroup"]:
            exp = dt.datetime.strptime(r["expirygroup"], "%B %d, %Y").date()
            continue
        if not r["strike"] or exp is None:
            continue
        k = float(r["strike"].replace(",", ""))
        for cp, pre in (("C", "c_"), ("P", "p_")):
            try:
                bid, ask = float(r[pre + "Bid"]), float(r[pre + "Ask"])
                oi = float(str(r[pre + "Openinterest"]).replace(",", ""))
            except (TypeError, ValueError):
                continue
            if oi <= 0 or ask <= 0:
                continue
            rows.append((exp, cp, k, oi, 0.5 * (bid + ask)))
    exp_a = np.array([r[0] for r in rows])
    call = np.array([r[1] == "C" for r in rows])
    k = np.array([r[2] for r in rows])
    mid = np.array([r[4] for r in rows])
    t = np.array([max((e - asof).days, 0) + 0.25 for e in exp_a]) / 365.0
    iv = implied_vol(mid, spot, k, t, call)
    t0 = max(asof, session) if session else asof
    t_s = np.array([max((e - t0).days, 0) + 0.25 for e in exp_a]) / 365.0
    gamma = np.nan_to_num(_bs_gamma(np.full(len(k), spot), k, t_s, np.nan_to_num(iv, nan=0.2)) * ~np.isnan(iv))
    options = [{"option": f"{sym}{e:%y%m%d}{'C' if c else 'P'}{int(round(kk * 1000)):08d}", "open_interest": r[3],
                "iv": float(np.nan_to_num(v)), "gamma": float(g)}
               for (e, _, kk, _, _), r, c, v, g in zip(rows, rows, call, iv, gamma)]
    return {"timestamp": f"{asof} 16:00 New York (Nasdaq, as of the last close)", "asof": str(asof),
            "data": {"symbol": sym, "current_price": spot, "options": options}}


def close_ratio(asof: str) -> Optional[float]:
    """NQ futures over QQQ at the 15:59 New York bar of `asof`, both from Yahoo."""
    try:
        def at_close(sym):
            j = _get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=5d")["chart"]["result"][0]
            best = None
            for ts, c in zip(j["timestamp"], j["indicators"]["quote"][0]["close"]):
                t = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
                if c is not None and t.strftime("%Y-%m-%d") == asof and (t.hour, t.minute) <= (15, 59):
                    best = c
            return best
        nq, qqq = at_close("NQ=F"), at_close("QQQ")
        return nq / qqq if nq and qqq else None
    except Exception:
        return None


MIN_CONTRACTS = 1000                                              # before the open most contracts carry no quote


def session_for(now: Optional[dt.datetime] = None) -> dt.date:
    """The session the levels are for: today before 16:00 New York, else the next weekday."""
    from zoneinfo import ZoneInfo
    now = now or dt.datetime.now(ZoneInfo("America/New_York"))
    d = now.date()
    if now.hour >= 16:
        d += dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def today_levels(save: bool = False) -> dict:
    """Levels from the latest chain.  Nasdaq stamps its chain with today's date from midnight, but until the
    open it holds the previous close's prices and only a few contracts have quotes: then `asof` is the last
    weekday before today, and a pull with fewer than MIN_CONTRACTS contracts never replaces a saved file."""
    from zoneinfo import ZoneInfo
    session = session_for()
    try:
        raw = nasdaq_chain("QQQ", session=session)
        today = dt.date.fromisoformat(raw["asof"])
        now = dt.datetime.now(ZoneInfo("America/New_York"))
        if today >= now.date() and (now.hour, now.minute) < (9, 30):
            prev = now.date() - dt.timedelta(days=1)
            while prev.weekday() >= 5:
                prev -= dt.timedelta(days=1)
            raw["asof"], today = str(prev), prev
            raw["timestamp"] = f"{prev} 16:00 New York (Nasdaq, as of the last close)"
    except Exception:
        raw, today = chain("QQQ"), None
    # times to expiry run from the session the levels are for: after the close that is the next weekday, so the
    # contracts that expired at the close (the day's 0DTE, the biggest gamma at the money) drop out
    lv = compute(raw, session)
    lv["session"] = session.isoformat()
    ratio = close_ratio(raw["asof"]) if "asof" in raw else nq_ratio()
    lv["nq_per_qqq"] = round(ratio, 4) if ratio else None
    if ratio:
        lv["nq"] = {name: round(lv[name] * ratio, 2) for name in ("spot", "gamma_flip", "call_wall", "put_wall", "max_pain")
                    if lv.get(name)}
    if save:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{session.isoformat()}.json"
        if path.exists() and (lv.get("contracts") or 0) < MIN_CONTRACTS:
            kept = json.loads(path.read_text())
            if (kept.get("contracts") or 0) > (lv.get("contracts") or 0):
                print(f"kept {path.name}: this pull has {lv.get('contracts')} contracts with quotes, the saved one "
                      f"{kept.get('contracts')}", file=sys.stderr)
                return kept
        path.write_text(json.dumps(lv, indent=1))
    return lv


if __name__ == "__main__":
    print(json.dumps(today_levels(save="--save" in sys.argv), indent=1))
