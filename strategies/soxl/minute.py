"""One-minute SOXL and SOXS bars from Yahoo, kept in an archive that grows.

    python strategies/soxl/minute.py            # fetch what Yahoo has and merge it into the archive

Yahoo serves one-minute bars for the last 30 days only, seven days a request,
so the archive (data/intraday/<SYMBOL>_1m.csv) is what makes a longer test
possible later: every run adds the finished sessions Yahoo still has.  Regular
hours only (09:30-16:00 New York), stamped in UTC like the engine's other
intraday bars ("2026-09-23 13:30" is the 09:30 bar), so the session features
(time of day, session VWAP, opening range) work on them.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evotrader.data import Bars, Universe                                  # noqa: E402

ARCHIVE = ROOT / "data" / "intraday"
#: the opening dip scalper's names (strategies/scalp): liquid, fast, a cent at most ~4 bp
SCALP_NAMES = ("SOXL", "SOXS", "MUU", "NVDL", "SMCI", "MSTR", "COIN", "MRVL", "MU", "ARM", "PLTR", "AMD",
               "META", "TSLA", "AVGO", "NVDA", "TQQQ")
#: 30 names nothing was chosen on, added to test the scalpers out of sample; with SCALP_NAMES
#: they are the own-drop scalper's pool
FRESH_NAMES = ("HOOD", "RKLB", "IONQ", "NET", "CRWD", "SHOP", "UBER", "NFLX", "ANET", "APP", "CVNA", "SNOW",
               "DDOG", "ORCL", "GOOGL", "AMZN", "AAPL", "MSFT", "INTC", "QCOM", "LRCX", "AMAT", "KLAC", "CRWV",
               "OKLO", "HIMS", "AFRM", "RDDT", "DELL", "ASTS")
POOL_NAMES = SCALP_NAMES + FRESH_NAMES
NY = ZoneInfo("America/New_York")
Row = Tuple[float, float, float, float, float]


def _chunk(symbol: str, p1: float, p2: float) -> Dict[str, Row]:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
           f"&period1={int(p1)}&period2={int(p2)}&includePrePost=false")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read())["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    out: Dict[str, Row] = {}
    for i, ts in enumerate(res.get("timestamp") or []):
        row = tuple(q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in row[:4]:
            continue
        t = datetime.fromtimestamp(ts, tz=timezone.utc)
        local = t.astimezone(NY)
        if (local.hour, local.minute) < (9, 30) or local.hour >= 16:
            continue
        out[t.strftime("%Y-%m-%d %H:%M")] = tuple(float(x or 0.0) for x in row)
    return out


def fetch(symbol: str, days: float = 29.5) -> Dict[str, Row]:
    """Every regular-hours minute Yahoo still has, in seven-day requests."""
    now, rows = time.time(), {}
    t = now - days * 86400
    while t < now:
        rows.update(_chunk(symbol, t, min(t + 7 * 86400, now)))
        t += 7 * 86400
    return rows


def session_of(stamp: str) -> str:
    t = datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return t.astimezone(NY).strftime("%Y-%m-%d")


def _path(symbol: str) -> Path:
    return ARCHIVE / f"{symbol.upper()}_1m.csv"


def read(symbol: str) -> Dict[str, Row]:
    p = _path(symbol)
    if not p.exists():
        return {}
    with p.open() as f:
        return {r["stamp"]: tuple(float(r[k]) for k in ("open", "high", "low", "close", "volume"))
                for r in csv.DictReader(f)}


def update(symbols: Sequence[str] = ("SOXL", "SOXS")) -> Dict[str, int]:
    """Merge Yahoo's finished sessions into the archive; a session still
    trading is left for the next run.  Returns the archive's session count."""
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    today = datetime.now(NY)
    open_now = today.weekday() < 5 and (9, 30) <= (today.hour, today.minute) < (16, 5)
    counts = {}
    for s in symbols:
        rows = read(s)
        for stamp, row in fetch(s).items():
            if open_now and session_of(stamp) == today.strftime("%Y-%m-%d"):
                continue
            rows[stamp] = row
        with _path(s).open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["stamp", "open", "high", "low", "close", "volume"])
            for stamp in sorted(rows):
                w.writerow([stamp, *[f"{x:.6g}" for x in rows[stamp]]])
        counts[s] = len({session_of(k) for k in rows})
    return counts


def short_series(rows: Dict[str, Row], scale: float = 10_000.0) -> Dict[str, Row]:
    """A short in a fund as a long in its reciprocal: over minutes the
    reciprocal's return is minus the fund's, give or take its square."""
    return {t: (scale / o, scale / l, scale / h, scale / c, v) for t, (o, h, l, c, v) in rows.items()}


def read_any(symbol: str) -> Dict[str, Row]:
    """Archive rows; "SOXL.SHORT" is the short side of SOXL."""
    if symbol.upper().endswith(".SHORT"):
        return short_series(read(symbol.split(".")[0]))
    return read(symbol)


def universe(symbols: Sequence[str], sessions: Sequence[str] = ()) -> Universe:
    """The archive's bars for these symbols on their common minutes,
    optionally only the listed sessions."""
    data = {s: read_any(s) for s in symbols}
    stamps = sorted(set.intersection(*(set(d) for d in data.values())))
    if sessions:
        keep = set(sessions)
        stamps = [t for t in stamps if session_of(t) in keep]
    bars = {s: Bars(s, list(stamps), *[np.array([data[s][t][k] for t in stamps]) for k in range(5)])
            for s in symbols}
    return Universe(bars, list(stamps))


def sessions(symbols: Sequence[str] = ("SOXL", "SOXS")) -> List[str]:
    data = [set(read(s)) for s in symbols]
    return sorted({session_of(t) for t in set.intersection(*data)})


if __name__ == "__main__":
    print(update(POOL_NAMES))
