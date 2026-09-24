"""Four years of one-minute stock bars lined up by session, and a scalping portfolio simulator.

    from panel import sessions, simulate

`sessions()` reads the Dukascopy stock CFD minutes (duka_stocks.py) and yields,
for each New York session with enough names trading, aligned arrays of shape
(names, 390): open, high, low, close for 09:30-15:59, forward-filled where a
minute is missing, plus the previous session's close.  `features()` adds what
the scalpers read: the one-minute return, the typical one-minute range (14
minutes, ATR as a share of price), the move against the other names that
minute scaled by its last 20 values (resid_z), the gap and the minute of the
session.

`simulate()` runs a rule over the sessions as a small book: a signal on a
minute's close buys (or sells) at the next minute's open and sells (or buys
back) `hold` minutes later at the open; at most `slots` positions, each an
equal share of the buying power; when more names signal than slots are free,
the strongest signal goes first.  Each name pays a cent plus 1 bp each way at
its own price.  Nothing is held past 15:55.  The result is dollars a day on a
$25,000 account at the chosen buying power.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import duka_stocks                                                           # noqa: E402

NY = ZoneInfo("America/New_York")
CACHE = ROOT / "data" / "cache" / "duka" / "panel"
NAMES = ["MRVL", "MU", "PLTR", "AMD", "FB", "TSLA", "AVGO", "NVDA", "UBER", "NFLX", "CVNA", "SNOW", "ORCL", "GOOGL",
         "AMZN", "AAPL", "MSFT", "INTC", "QCOM", "LRCX", "AMAT", "DELL", "ADBE", "CRM", "PYPL", "SQ", "BA", "DIS", "JPM",
         "GS", "BAC", "XOM", "CVX", "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "V", "MA", "LLY", "UNH", "PFE", "MRNA",
         "JNJ", "TXN", "ADI", "MCHP", "ON", "TSM", "BABA", "NIO", "F", "GM", "SNAP", "ROKU", "ZM", "DOCU", "TWLO", "PANW",
         "FTNT", "ZS", "OKTA", "WDAY", "NOW", "INTU", "TEAM", "MDB", "SPOT", "CSCO", "IBM"]
ACCOUNT = 25_000.0


def _ny_offsets(ts: np.ndarray) -> np.ndarray:
    """UTC offset in seconds (negative) for each epoch second, New York time, by UTC date."""
    days = np.floor(ts / 86400).astype(np.int64)
    out = np.empty(len(ts))
    for d in np.unique(days):
        noon = dt.datetime.fromtimestamp(int(d) * 86400 + 12 * 3600, tz=dt.timezone.utc).astimezone(NY)
        out[days == d] = noon.utcoffset().total_seconds()
    return out


def _ffill(x: np.ndarray) -> np.ndarray:
    """Forward-fill NaN along the last axis, then back-fill the leading NaN."""
    n, T = x.shape
    valid = ~np.isnan(x)
    idx = np.where(valid, np.arange(T)[None, :], 0)
    np.maximum.accumulate(idx, axis=1, out=idx)
    out = x[np.arange(n)[:, None], idx]
    first = np.argmax(valid, axis=1)
    lead = np.arange(T)[None, :] < first[:, None]
    out = np.where(lead, x[np.arange(n), first][:, None], out)
    return out


def build(names: Sequence[str] = NAMES, min_names: int = 50) -> Path:
    """Aligned session arrays, cached as one compressed file."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "panel.npz"
    per: Dict[str, dict] = {}
    for n in names:
        p = duka_stocks.STORE / f"{n}.npz"
        if not p.exists():
            continue
        a = np.load(p)["a"]
        if not len(a):
            continue
        local = a[:, 0] + _ny_offsets(a[:, 0])
        day = np.floor(local / 86400).astype(np.int64)
        mod = ((local % 86400) // 60).astype(np.int64) - (9 * 60 + 30)          # minute of the session
        keep = (mod >= 0) & (mod < 390)
        day, mod, ohlc = day[keep], mod[keep], a[keep, 1:5]
        u, first, counts = np.unique(day, return_index=True, return_counts=True)
        per[n] = {"mod": mod, "ohlc": ohlc, "slices": {int(d): (int(f), int(f + c)) for d, f, c in zip(u, first, counts) if c >= 370}}
    names = [n for n in names if n in per]
    all_days = sorted(set().union(*[set(v["slices"]) for v in per.values()]))
    cubes, dates = [], []
    for d in all_days:
        rows = [k for k, n in enumerate(names) if d in per[n]["slices"]]
        if len(rows) < min_names:
            continue
        cube = np.full((len(names), 390, 4), np.nan)
        for k in rows:
            v = per[names[k]]
            a, b = v["slices"][d]
            cube[k, v["mod"][a:b]] = v["ohlc"][a:b]
        c = cube[:, :, 3]
        has = ~np.isnan(c).all(axis=1)
        if has.any():
            cf = _ffill(c[has])
            miss = np.isnan(c[has])
            for j in range(3):
                col = cube[has][:, :, j]
                cube[np.flatnonzero(has)[:, None], np.arange(390)[None, :], j] = np.where(miss, cf, col)
            cube[has, :, 3] = cf
        cubes.append(cube.astype(np.float32))
        dates.append(dt.date.fromordinal(dt.date(1970, 1, 1).toordinal() + int(d)).isoformat())
    np.savez_compressed(path, cube=np.stack(cubes), dates=np.array(dates), names=np.array(names))
    return path


def load_panel():
    z = np.load(CACHE / "panel.npz", allow_pickle=True)
    return z["cube"], list(z["dates"]), list(z["names"])


def features(cube: np.ndarray, prev_close: np.ndarray, prev_cube: Optional[np.ndarray]) -> Dict[str, np.ndarray]:
    """Per (name, minute), from bars already closed."""
    o, h, l, c = (cube[:, :, i].astype(float) for i in range(4))
    n, T = c.shape
    r1 = np.full((n, T), np.nan)
    r1[:, 1:] = c[:, 1:] / c[:, :-1] - 1.0
    r1[:, 0] = c[:, 0] / o[:, 0] - 1.0
    # true range over 14 minutes, seeded with the previous session's last 14 minutes
    if prev_cube is not None:
        pc = prev_cube[:, -14:, :].astype(float)
        seed_tr = (pc[:, :, 1] - pc[:, :, 2]) / pc[:, :, 3]
    else:
        seed_tr = np.full((n, 14), np.nan)
    tr = (h - l) / c
    tr_all = np.concatenate([seed_tr, tr], axis=1)
    cs = np.nancumsum(np.nan_to_num(tr_all), axis=1)
    atr = (cs[:, 14:] - cs[:, :-14]) / 14.0
    atr = atr[:, :T]
    # the move against the others that minute, over its last 20 values
    valid = ~np.isnan(r1)
    tot = np.nansum(r1, axis=0)
    cnt = valid.sum(axis=0)
    others = (tot[None, :] - np.nan_to_num(r1)) / np.maximum(cnt[None, :] - valid.astype(int), 1)
    resid = r1 - others
    if prev_cube is not None:
        pc = prev_cube[:, -21:, 3].astype(float)
        pr = pc[:, 1:] / pc[:, :-1] - 1.0
        pothers = (pr.sum(axis=0)[None, :] - pr) / max(n - 1, 1)
        seed = pr - pothers
    else:
        seed = np.full((n, 20), np.nan)
    allr = np.concatenate([seed, resid], axis=1)
    sq = np.nancumsum(np.nan_to_num(allr) ** 2, axis=1)
    cnt2 = np.cumsum(~np.isnan(allr), axis=1)
    sd = np.sqrt((sq[:, 19:-1] - np.concatenate([np.zeros((n, 1)), sq[:, :-21]], axis=1)[:, :T]) /
                 np.maximum(cnt2[:, 19:-1] - np.concatenate([np.zeros((n, 1)), cnt2[:, :-21]], axis=1)[:, :T], 1))
    resid_z = resid / np.where(sd > 0, sd, np.nan)
    gap = o[:, 0] / prev_close - 1.0 if prev_close is not None else np.full(n, np.nan)
    return {"o": o, "h": h, "l": l, "c": c, "r1": r1, "atr": atr, "resid": resid, "resid_z": resid_z,
            "gap": gap, "mkt_r1": others.mean(axis=0) if n else others}


Rule = Callable[[Dict[str, np.ndarray]], Tuple[np.ndarray, np.ndarray]]


def simulate(rule: Rule, hold: int, slots: int, leverage: float, days: Sequence[str], cube: np.ndarray,
             dates: List[str], names: List[str], cost_mult: float = 1.0, delay: int = 0) -> dict:
    """rule(features) -> (side matrix +1/-1/0, priority matrix: higher goes first)."""
    idx = {d: i for i, d in enumerate(dates)}
    size = leverage * ACCOUNT / slots
    daily: Dict[str, float] = {}
    trades = []
    for d in days:
        i = idx.get(d)
        if i is None or i == 0:
            continue
        cb, prev = cube[i], cube[i - 1]
        f = features(cb, prev[:, -1, 3].astype(float), prev)
        side, prio = rule(f)
        o = f["o"]
        pnl, busy = 0.0, []
        free_at = []                                  # minute each open position frees its slot
        held = set()
        cand_minutes = np.flatnonzero((side != 0).any(axis=0))
        for t in cand_minutes:
            t_in = t + 1 + delay
            t_out = t_in + hold
            if t_out >= 386:
                continue
            free_at = [x for x in free_at if x[0] > t_in]
            held = {x[1] for x in free_at}
            ks = np.flatnonzero(side[:, t] != 0)
            ks = ks[np.argsort(-prio[ks, t])]
            for k in ks:
                if len(free_at) >= slots:
                    break
                if k in held or np.isnan(o[k, t_in]) or np.isnan(o[k, t_out]):
                    continue
                px_in, px_out = o[k, t_in], o[k, t_out]
                s = side[k, t]
                cost = 2 * (0.01 / px_in + 1e-4) * cost_mult
                ret = s * (px_out / px_in - 1.0) - cost
                pnl += size * ret
                trades.append((d, names[k], int(t_in), s, ret))
                free_at.append((t_out, k))
                held.add(k)
        daily[d] = pnl
    v = np.array(list(daily.values())) if daily else np.zeros(1)
    rets = np.array([x[4] for x in trades]) if trades else np.zeros(1)
    years: Dict[str, List[float]] = {}
    for d, x in daily.items():
        years.setdefault(d[:4], []).append(x)
    return {"sessions": len(daily), "usd_per_day": round(float(v.mean()), 1), "median": round(float(np.median(v)), 1),
            "days_up": round(float((v > 0).mean()), 3), "days_200_plus": round(float((v >= 200).mean()), 3),
            "worst_day": round(float(v.min()), 0), "trades_per_day": round(len(trades) / max(len(daily), 1), 2),
            "win": round(float((rets > 0).mean()), 3), "bp_per_trade": round(float(rets.mean() * 1e4), 2),
            "years": {y: round(float(np.mean(x)), 1) for y, x in sorted(years.items())}, "daily": daily}
