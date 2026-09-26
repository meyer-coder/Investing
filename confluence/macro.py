"""Macro context: what the world looked like on each trading day.

Every trade is tagged with the macro regime in force when it was entered,
using only information published *before* that trading day (the prior
close, or the latest CPI print already released), so the tags cannot leak
the future into the analysis.

Sources (all public, cached under ``data/cache/macro``):

* Yahoo Finance daily closes: ^VIX, ^VIX3M, ^IRX (3-month T-bill, a proxy
  for the Fed funds rate), ^TNX (10-year Treasury yield), DX-Y.NYB (US
  dollar index), ^GSPC (S&P 500).
* federalreserve.gov FOMC calendars: the date of every policy statement,
  unscheduled meetings included.
* US CPI, year over year, monthly (OECD via DBnomics — FRED and the BLS API
  are not reachable from every network).  A month's print is treated as
  known from the 15th of the following month.
* Jobs-report (NFP) days from the BLS rule: the third Friday after the week
  containing the 12th.  Releases displaced by the Oct–Nov 2025 government
  shutdown are left out rather than guessed.

``DIMENSIONS`` defines the regimes; ``tag_days`` labels trading days.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .data import CACHE, DataError, _http

MACRO = os.path.join(CACHE, "macro")
EPOCH = dt.date(1970, 1, 1)

YAHOO = {"vix": "^VIX", "vix3m": "^VIX3M", "irx": "^IRX", "tnx": "^TNX", "dxy": "DX-Y.NYB", "spx": "^GSPC"}


# ------------------------------------------------------------------ fetching

def _yahoo_daily(symbol: str, start: dt.date, end: dt.date) -> Dict[str, float]:
    p1 = int(dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(dt.datetime(end.year, end.month, end.day, tzinfo=dt.timezone.utc).timestamp()) + 86400
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?period1={p1}&period2={p2}&interval=1d")
    payload = json.loads(_http(url, timeout=40))
    res = payload["chart"]["result"][0]
    offset = int(res["meta"].get("gmtoffset", 0))
    out = {}
    for ts, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        out[dt.datetime.fromtimestamp(ts + offset, dt.timezone.utc).date().isoformat()] = float(c)
    return out


def fomc_dates(refresh: bool = False) -> List[str]:
    """Every FOMC policy-statement date, 2018 onward, from federalreserve.gov."""
    path = os.path.join(MACRO, "fomc.json")
    if os.path.exists(path) and not refresh:
        with open(path) as fh:
            return json.load(fh)
    dates = set()
    pages = [f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm" for y in (2018, 2019, 2020)]
    pages.append("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    for url in pages:
        html = _http(url, timeout=40).decode("utf-8", "replace")
        # Statements are press releases named monetaryYYYYMMDDa.htm.
        for d in re.findall(r"monetary(\d{8})a\.htm", html):
            dates.add(f"{d[:4]}-{d[4:6]}-{d[6:]}")
        # Scheduled meetings without a statement yet: take the last day of the meeting.
        if "fomccalendars" in url:
            for block in re.split(r"(\d{4}) FOMC Meetings", html)[1:]:
                pass
            for year, body in re.findall(r"(\d{4}) FOMC Meetings(.*?)(?=\d{4} FOMC Meetings|$)", html, re.S):
                for month, days in re.findall(r"fomc-meeting__month[^>]*><strong>([A-Za-z/]+)</strong>.*?"
                                              r"fomc-meeting__date[^>]*>([^<]+)<", body, re.S):
                    m = month.split("/")[-1]
                    last = re.findall(r"\d+", days)
                    if not last or "cancel" in days.lower():
                        continue
                    try:
                        d = dt.datetime.strptime(f"{year} {m} {last[-1]}", "%Y %B %d").date()
                    except ValueError:
                        continue
                    dates.add(d.isoformat())
    out = sorted(d for d in dates if d >= "2018-01-01")
    os.makedirs(MACRO, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    return out


def cpi_yoy(refresh: bool = False) -> Dict[str, float]:
    """US CPI, percent change over a year, by month ('YYYY-MM' -> %)."""
    path = os.path.join(MACRO, "cpi_yoy.json")
    if os.path.exists(path) and not refresh:
        with open(path) as fh:
            return json.load(fh)
    url = ("https://api.db.nomics.world/v22/series/OECD/DSD_G20_PRICES@DF_G20_PRICES/"
           "USA.M.N.CPI.PA._T.N.GY?observations=1&format=json")
    doc = json.loads(_http(url, timeout=60))["series"]["docs"][0]
    out = {p: float(v) for p, v in zip(doc["period"], doc["value"]) if v not in (None, "NA")}
    os.makedirs(MACRO, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    return out


def nfp_dates(start: dt.date, end: dt.date) -> List[str]:
    """Employment Situation release days by the BLS rule."""
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        twelfth = dt.date(y, m, 12)
        sat = twelfth + dt.timedelta(days=(5 - twelfth.weekday()) % 7)   # end of the reference week
        rel = sat + dt.timedelta(days=6 + 14)                            # third Friday after it
        if (rel.month, rel.day) in ((7, 3), (7, 4), (1, 1)):
            rel -= dt.timedelta(days=1)                                  # holiday: Thursday instead
        shutdown = dt.date(2025, 10, 1) <= rel <= dt.date(2025, 12, 31)
        if start <= rel <= end and not shutdown:
            out.append(rel.isoformat())
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def fetch_all(start: dt.date, end: dt.date, *, refresh: bool = False) -> Dict[str, object]:
    os.makedirs(MACRO, exist_ok=True)
    series = {}
    for key, sym in YAHOO.items():
        path = os.path.join(MACRO, f"{key}.json")
        if os.path.exists(path) and not refresh:
            with open(path) as fh:
                series[key] = json.load(fh)
            continue
        series[key] = _yahoo_daily(sym, start, end)
        with open(path, "w") as fh:
            json.dump(series[key], fh)
    return {"series": series, "fomc": fomc_dates(refresh), "cpi": cpi_yoy(refresh),
            "nfp": nfp_dates(start, end)}


# ------------------------------------------------------------------ regimes

@dataclass(frozen=True)
class Dimension:
    key: str
    title: str
    question: str
    order: Tuple[str, ...]
    note: str


DIMENSIONS: List[Dimension] = [
    Dimension("vix", "Volatility (VIX)", "How scared was the market?",
              ("VIX < 15", "VIX 15–20", "VIX 20–30", "VIX ≥ 30"),
              "prior day's VIX close"),
    Dimension("curve", "VIX term structure", "Was near-term fear above longer-term fear?",
              ("contango", "backwardation"),
              "prior day's VIX ÷ VIX3M; above 1 (backwardation) marks acute stress"),
    Dimension("fed", "Fed policy cycle", "Was the Fed hiking, cutting or holding?",
              ("hiking", "on hold", "cutting"),
              "63-day change in the 3-month T-bill yield: above +0.25 pt hiking, below −0.25 pt cutting"),
    Dimension("ust", "10-year yield trend", "Were long rates rising or falling?",
              ("yields falling", "yields flat", "yields rising"),
              "63-day change in the 10-year Treasury yield, ±0.30 pt"),
    Dimension("usd", "US dollar trend", "Was the dollar strengthening?",
              ("dollar weak", "dollar strong"),
              "dollar index vs its 50-day average"),
    Dimension("spx", "Equity trend", "Bull or bear tape?",
              ("S&P above 200d", "S&P below 200d"),
              "S&P 500 vs its 200-day average"),
    Dimension("cpi", "Inflation", "How hot was inflation?",
              ("CPI < 2.5%", "CPI 2.5–4%", "CPI ≥ 4%"),
              "latest published US CPI, year over year"),
    Dimension("event", "Event days", "Was it an FOMC or jobs-report day?",
              ("normal day", "FOMC day", "jobs report day"),
              "FOMC statement days (federalreserve.gov) and NFP days (BLS rule)"),
]
DIM_BY_KEY = {d.key: d for d in DIMENSIONS}

EPISODES = [
    ("COVID crash", "2020-02-20", "2020-04-30"),
    ("2022 rate-hike bear market", "2022-01-03", "2022-10-12"),
    ("April 2025 tariff shock", "2025-04-02", "2025-04-30"),
]


def _asof(series: Dict[str, float], dates: Sequence[str]) -> np.ndarray:
    """Value of the last observation strictly before each date."""
    keys = sorted(series)
    vals = np.array([series[k] for k in keys])
    pos = np.searchsorted(np.array(keys), np.array(dates), side="left") - 1
    out = np.full(len(dates), np.nan)
    ok = pos >= 0
    out[ok] = vals[pos[ok]]
    return out


def _roll(series: Dict[str, float], fn: Callable[[np.ndarray], np.ndarray]) -> Dict[str, float]:
    keys = sorted(series)
    v = fn(np.array([series[k] for k in keys]))
    return {k: float(x) for k, x in zip(keys, v) if not np.isnan(x)}


def _change(n):
    return lambda v: np.concatenate((np.full(n, np.nan), v[n:] - v[:-n]))


def _vs_sma(n):
    def f(v):
        c = np.cumsum(np.insert(v, 0, 0.0))
        sma = np.full(v.size, np.nan)
        sma[n - 1:] = (c[n:] - c[:-n]) / n
        return v / sma - 1.0
    return f


def tag_days(days: np.ndarray, macro: Dict[str, object]) -> Dict[str, np.ndarray]:
    """Regime label (as an index into ``Dimension.order``, -1 = unknown) per trading day."""
    s = macro["series"]
    dates = [(EPOCH + dt.timedelta(days=int(d))).isoformat() for d in days]
    out: Dict[str, np.ndarray] = {}
    vix = _asof(s["vix"], dates)
    out["vix"] = np.select([vix < 15, vix < 20, vix < 30, vix >= 30], [0, 1, 2, 3], -1)
    ratio = {k: s["vix"][k] / s["vix3m"][k] for k in s["vix"] if k in s["vix3m"] and s["vix3m"][k]}
    r = _asof(ratio, dates)
    out["curve"] = np.select([r < 1, r >= 1], [0, 1], -1)
    irx = _asof(_roll(s["irx"], _change(63)), dates)
    out["fed"] = np.select([irx > 0.25, irx < -0.25, np.abs(irx) <= 0.25], [0, 2, 1], -1)
    tnx = _asof(_roll(s["tnx"], _change(63)), dates)
    out["ust"] = np.select([tnx < -0.30, tnx > 0.30, np.abs(tnx) <= 0.30], [0, 2, 1], -1)
    usd = _asof(_roll(s["dxy"], _vs_sma(50)), dates)
    out["usd"] = np.select([usd < 0, usd >= 0], [0, 1], -1)
    spx = _asof(_roll(s["spx"], _vs_sma(200)), dates)
    out["spx"] = np.select([spx >= 0, spx < 0], [0, 1], -1)
    # CPI for month M is known from the 15th of month M+1.
    cpi = {}
    for ym, v in macro["cpi"].items():
        y, m = int(ym[:4]), int(ym[5:7])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        cpi[f"{y:04d}-{m:02d}-15"] = v
    c = _asof(cpi, dates)
    out["cpi"] = np.select([c < 2.5, c < 4.0, c >= 4.0], [0, 1, 2], -1)
    fomc, nfp = set(macro["fomc"]), set(macro["nfp"])
    out["event"] = np.array([1 if d in fomc else 2 if d in nfp else 0 for d in dates])
    return out


def episodes(days: np.ndarray) -> np.ndarray:
    """Episode index per trading day (-1 = none)."""
    out = np.full(days.size, -1)
    for k, (_, a, b) in enumerate(EPISODES):
        lo = (dt.date.fromisoformat(a) - EPOCH).days
        hi = (dt.date.fromisoformat(b) - EPOCH).days
        out[(days >= lo) & (days <= hi)] = k
    return out
