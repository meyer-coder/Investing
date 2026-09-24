"""Sharp ten-second moves in single stocks: fade them, or go with them (the 10-30 second spike idea).

    python strategies/scalp/fastdrop.py

latency.py shows that most of the bounce after a minute-bar drop is gone ten
seconds later, so a bot reading minute bars is late by construction.  Here the
drop itself is read on ten-second mid prices (bid and offer averaged): a name
falls hard against the Nasdaq-100 in one ten-second bar (beyond k of its
typical ten-second range and z standard deviations of its own recent moves
against the index), and the bot trades at the next bar's open (no delay, which no bot gets) or
a bar later (ten seconds, more than the two or three a live bot needs; the
truth is between the two), holds 30 seconds
to 3 minutes and sells at a bar's open.  Three modes: fade drops (buy them),
fade both (buy drops, short rises) and follow both (buy rises, short drops,
the momentum version of the spike idea).  Same book as the minute study: slots, one position per name, a cent
plus 1 bp for the round trip (tight) or a cent plus 1 bp each way (base) on
the price paid.  The last year of the 16 names with ten-second data.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import splits                                                                # noqa: E402

NY = ZoneInfo("America/New_York")
S10 = ROOT / "data" / "cache" / "duka" / "stocks10s"
IDX = ROOT / "data" / "cache" / "duka" / "seconds10"
BARS = 2340                                                                  # ten-second bars in 09:30-16:00
ACCOUNT = 25_000.0


def _grid(t: np.ndarray, vals: np.ndarray) -> Dict[str, np.ndarray]:
    """{date: (BARS, k) array} from epoch-stamped rows, forward-filled inside the session."""
    out: Dict[str, np.ndarray] = {}
    days = {}
    for i, x in enumerate(t):
        days.setdefault(int(x // 86400), []).append(i)
    for dnum, rows in days.items():
        rows = np.array(rows)
        date = dt.date.fromordinal(dt.date(1970, 1, 1).toordinal() + dnum)
        open_ = dt.datetime(date.year, date.month, date.day, 9, 30, tzinfo=NY).timestamp()
        slot = ((t[rows] - open_) // 10).astype(int)
        ok = (slot >= 0) & (slot < BARS)
        if ok.sum() < BARS * 0.6:
            continue
        g = np.full((BARS, vals.shape[1]), np.nan)
        g[slot[ok]] = vals[rows[ok]]
        # forward-fill, then back-fill the first bars
        idx = np.where(~np.isnan(g[:, -1]), np.arange(BARS), 0)
        np.maximum.accumulate(idx, out=idx)
        g = g[idx]
        first = np.argmax(~np.isnan(g[:, -1]))
        g[:first] = g[first]
        out[date.isoformat()] = g
    return out


def load_names() -> Dict[str, Dict[str, np.ndarray]]:
    out = {}
    for p in sorted(S10.glob("*_B.npz")):
        sym = p.stem[:-2]
        pa = S10 / f"{sym}_A.npz"
        if not pa.exists():
            continue
        b, a = np.load(p)["a"], np.load(pa)["a"]
        t = np.intersect1d(b[:, 0], a[:, 0])
        if not len(t):
            continue
        b, a = b[np.isin(b[:, 0], t)], a[np.isin(a[:, 0], t)]
        mid = (b[:, 1:5] + a[:, 1:5]) / 2
        out[sym] = _grid(t, mid)
    return out


def load_index(dates: List[str]) -> Dict[str, np.ndarray]:
    months = sorted({d[:7] for d in dates})
    rows = [np.load(IDX / f"{m}.npz")["a"] for m in months if (IDX / f"{m}.npz").exists()]
    a = np.concatenate(rows)
    return _grid(a[:, 0], a[:, 1:5])


def features(g: np.ndarray, gi: np.ndarray, prev: np.ndarray, prev_i: np.ndarray, win: int = 90):
    """Per ten-second bar: return, index return, residual z over the last `win` bars, typical range."""
    c = np.concatenate([prev[-win - 1:, 3], g[:, 3]])
    ci = np.concatenate([prev_i[-win - 1:, 3], gi[:, 3]])
    rng = np.concatenate([(prev[-win:, 1] - prev[-win:, 2]) / prev[-win:, 3], (g[:, 1] - g[:, 2]) / g[:, 3]])
    r = c[1:] / c[:-1] - 1.0
    ri = ci[1:] / ci[:-1] - 1.0
    res = r - ri
    cs2 = np.concatenate([[0.0], np.cumsum(res ** 2)])
    csr = np.concatenate([[0.0], np.cumsum(rng)])
    n = len(g)
    j = np.arange(n) + win                                                   # position of bar j in the padded arrays
    sd = np.sqrt((cs2[j] - cs2[j - win]) / win)
    typ = (csr[j] - csr[j - win]) / win
    return r[win:], ri[win:], np.where(sd > 0, res[win:] / sd, 0.0), typ


def run(data, index, dates, fac, configs):
    """{config: {date: (dollars at 1x, trades)}}."""
    names = sorted(data)
    out = {k: {} for k in configs}
    for i, date in enumerate(dates):
        if i == 0 or date not in index or dates[i - 1] not in index:
            continue
        pdate = dates[i - 1]
        feats = {}
        for s in names:
            if date in data[s] and pdate in data[s]:
                feats[s] = features(data[s][date], index[date], data[s][pdate], index[pdate])
        for key, (a, b, k, z, hold, lag, slots, cost, mode) in configs.items():
            events = []
            for s, (r, ri, zz, typ) in feats.items():
                for move in (-1, 1):                                         # -1: a sharp drop, +1: a sharp rise
                    if mode == "fade drops" and move == 1:
                        continue
                    m = (move * r > k * typ) & (move * zz > z)
                    m[:a] = False
                    m[b + 1:] = False
                    side = -move if mode in ("fade drops", "fade both") else move
                    for j in np.flatnonzero(m):
                        events.append((j, abs(zz[j]), s, side))
            events.sort(key=lambda e: (e[0], -e[1]))
            busy, pnl, n = [], 0.0, 0
            for j, pr, s, side in events:
                t_in = j + 1 + lag
                t_out = t_in + hold
                if t_out >= BARS - 6:
                    continue
                busy = [x for x in busy if x[0] > t_in]
                if len(busy) >= slots or any(x[1] == s for x in busy):
                    continue
                g = data[s][date]
                px_in, px_out = g[t_in, 0], g[t_out, 0]
                paid = px_in * fac.get(s, {}).get(date, 1.0)
                c = (0.01 / paid + 1e-4) * (2 if cost == "base" else 1)
                pnl += ACCOUNT / slots * (side * (px_out / px_in - 1.0) - c)
                n += 1
                busy.append((t_out, s))
            out[key][date] = (pnl, n)
    return out


def main() -> int:
    data = load_names()
    dates = sorted(set().union(*[set(v) for v in data.values()]))
    index = load_index(dates)
    fac = splits.factors()
    print(f"{len(data)} names, {len(dates)} sessions ({dates[0]} to {dates[-1]})", flush=True)
    configs = {}
    for mode, (wn, (a, b)), k, z, hold, lag in itertools.product(
            ("fade drops", "fade both", "follow both"),
            (("09:35-10:00", (30, 180)), ("10:00-15:50", (180, 2280)), ("09:35-15:50", (30, 2280))),
            (1.5, 3.0), (3.0, 5.0), (3, 6, 12, 18), (0, 1)):
        for cost in ("tight", "base"):
            configs[f"{mode} {wn} k{k} z{z} hold {hold * 10}s lag {lag * 10}s {cost}"] = (a, b, k, z, hold, lag, 3, cost, mode)
    res = run(data, index, dates, fac, configs)
    rows = {}
    for key, byday in res.items():
        v = np.array([x[0] for x in byday.values()])
        tr = np.array([x[1] for x in byday.values()])
        rows[key] = {"usd_per_day_1x": round(float(v.mean()), 1), "days_up": round(float((v > 0).mean()), 3),
                     "trades_per_day": round(float(tr.mean()), 1),
                     "bp_per_trade": round(float(v.sum() / max(tr.sum(), 1) / (ACCOUNT / 3) * 1e4), 2)}
    ranked = sorted(rows.items(), key=lambda kv: -kv[1]["usd_per_day_1x"])
    for key, v in ranked[:40]:
        print(f"  {key:60s} ${v['usd_per_day_1x']:+7.1f}/day at 1x (x4 ${4 * v['usd_per_day_1x']:+6.0f}) up {v['days_up']:.0%} "
              f"{v['trades_per_day']:5.1f} tr/d {v['bp_per_trade']:+6.2f} bp", flush=True)
    (ROOT / "strategies" / "scalp" / "fastdrop.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
