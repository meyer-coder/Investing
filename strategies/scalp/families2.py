"""More short-hold stock families: moves against the sector, and laggards catching up.

    python strategies/scalp/families2.py

* sector drop, bought: a name falls hard against the other names in its own
  sector that minute (chips against chips, software against software), as
  own drop in families.py but with the sector for the market;
* catch-up: when the whole group of 72 names moves hard in one minute (its
  average one-minute return more than z typical market minutes), the names
  that have not moved yet (under a third of the market's move) are traded in
  the market's direction for one to three minutes, laggards first.

Same book, costs, periods and name halves as families.py.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import families                                                              # noqa: E402
import panel                                                                 # noqa: E402

SECTORS = {
    "chips": ["MRVL", "MU", "AMD", "AVGO", "NVDA", "INTC", "QCOM", "LRCX", "AMAT", "TXN", "ADI", "MCHP", "ON", "TSM"],
    "software": ["PLTR", "SNOW", "ORCL", "ADBE", "CRM", "NOW", "INTU", "WDAY", "TEAM", "MDB", "ZS", "FTNT", "PANW",
                 "OKTA", "DOCU", "TWLO", "ZM", "MSFT", "IBM", "CSCO", "DELL"],
    "internet": ["FB", "GOOGL", "AMZN", "NFLX", "UBER", "SPOT", "SNAP", "ROKU", "PYPL", "SQ", "BABA", "AAPL", "CVNA"],
    "consumer": ["WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS", "TSLA", "F", "GM", "NIO", "BA"],
    "finance_energy_health": ["JPM", "GS", "BAC", "V", "MA", "XOM", "CVX", "LLY", "UNH", "PFE", "MRNA", "JNJ"],
}


def sector_resid(f: Dict[str, np.ndarray], names) -> np.ndarray:
    """Each name's one-minute return less its sector's other names, over its last 20 values (z)."""
    r1 = f["r1"]
    n, T = r1.shape
    z = np.full((n, T), np.nan)
    for members in SECTORS.values():
        idx = [names.index(m) for m in members if m in names]
        if len(idx) < 4:
            continue
        sub = r1[idx]
        tot = np.nansum(sub, axis=0)
        cnt = (~np.isnan(sub)).sum(axis=0)
        res = sub - (tot[None, :] - np.nan_to_num(sub)) / np.maximum(cnt[None, :] - 1, 1)
        sq = np.nancumsum(np.nan_to_num(res) ** 2, axis=1)
        c = np.cumsum(~np.isnan(res), axis=1)
        lo = np.maximum(np.arange(T) - 20, 0)
        prev_sq = np.where(np.arange(T) - 20 >= 0, sq[:, np.maximum(np.arange(T) - 21, 0)], 0.0)
        prev_c = np.where(np.arange(T) - 20 >= 0, c[:, np.maximum(np.arange(T) - 21, 0)], 0)
        # the standard deviation of the 20 values before this minute
        s_sq = np.concatenate([np.zeros((len(idx), 1)), sq[:, :-1]], axis=1) - prev_sq
        s_c = np.concatenate([np.zeros((len(idx), 1)), c[:, :-1]], axis=1) - prev_c
        sd = np.sqrt(s_sq / np.maximum(s_c, 1))
        z[idx] = np.where((s_c >= 10) & (sd > 0), res / np.where(sd > 0, sd, 1), np.nan)
    return z


def rules() -> Dict[str, dict]:
    out = {}
    for (wn, (a, b)), k, z, hold in itertools.product(families.WINDOWS.items(), (0.75, 1.5), (2.0, 3.0), (1, 2, 3)):
        out[f"buy sector drop {wn} k{k} z{z} hold {hold}m"] = dict(kind="sector_drop", side=1, a=a, b=b, k=k, z=z, hold=hold)
    for (wn, (a, b)), mz, hold in itertools.product((("09:35-10:30", (5, 60)), ("10:30-15:50", (60, 380))), (3.0, 5.0), (1, 2, 3)):
        out[f"catch-up with the market {wn} mz{mz} hold {hold}m"] = dict(kind="catch_up", side=1, a=a, b=b, mz=mz, hold=hold)
        out[f"fade the market move in laggards {wn} mz{mz} hold {hold}m"] = dict(kind="catch_up", side=-1, a=a, b=b, mz=mz, hold=hold)
    return out


def signal(f: Dict[str, np.ndarray], r: dict):
    n, T = f["r1"].shape
    side = np.zeros((n, T), dtype=int)
    prio = np.zeros((n, T))
    if r["kind"] == "sector_drop":
        z = f["sector_z"]
        m = (-f["r1"] > r["k"] * f["atr"]) & (-z > r["z"])
        m[:, :r["a"]] = False
        m[:, r["b"] + 1:] = False
        side[np.nan_to_num(m.astype(float)).astype(bool)] = r["side"]
        prio = np.nan_to_num(-z)
    elif r["kind"] == "catch_up":
        mk = np.nanmean(f["r1"], axis=0)
        sq = np.cumsum(np.nan_to_num(mk) ** 2)
        lo = np.maximum(np.arange(T) - 20, 0)
        sd = np.sqrt((np.concatenate([[0.0], sq[:-1]]) - np.concatenate([[0.0], sq])[lo]) / np.maximum(np.arange(T) - lo, 1))
        big = (np.abs(mk) > r["mz"] * np.where(sd > 0, sd, np.inf)) & (np.arange(T) >= r["a"]) & (np.arange(T) <= r["b"])
        for t in np.flatnonzero(big):
            lag = np.abs(f["r1"][:, t]) < np.abs(mk[t]) / 3
            side[lag, t] = int(r["side"] * np.sign(mk[t]))
            prio[:, t] = -np.abs(np.nan_to_num(f["r1"][:, t]))
    return side, prio


def main() -> int:
    import multiprocessing as mp
    cube, dates, names = panel.load_panel()
    families._P.update(cube=cube, dates=dates, names=names)
    orig_signal, orig_features = families.signal, panel.features

    def feats(cb, prev_close, prev_cube):
        f = orig_features(cb, prev_close, prev_cube)
        f["sector_z"] = sector_resid(f, names)
        return f

    panel.features = feats
    families.signal = signal
    n = len(names)
    masks = {"all names": np.ones(n), "even names": (np.arange(n) % 2 == 0).astype(float),
             "odd names": (np.arange(n) % 2 == 1).astype(float)}
    items = list(rules().items())
    days = dates[1:]
    chunks = [days[i::4] for i in range(4)]
    with mp.get_context("fork").Pool(4) as pool:
        parts = pool.map(families._run_days, [(c, items, masks) for c in chunks])
    acc: Dict[tuple, Dict[str, tuple]] = {}
    for part in parts:
        for key, byday in part.items():
            acc.setdefault(key, {}).update(byday)
    rows = {}
    for (rname, mname), byday in acc.items():
        ds = sorted(byday)
        dev = np.array([byday[d][0] for d in ds if d < families.SPLIT])
        test = np.array([byday[d][0] for d in ds if d >= families.SPLIT])
        tr = np.array([byday[d][1] for d in ds])
        rows.setdefault(rname, {})[mname] = {
            "dev_usd": round(float(dev.mean()), 1), "test_usd": round(float(test.mean()), 1),
            "dev_up": round(float((dev > 0).mean()), 3), "test_up": round(float((test > 0).mean()), 3),
            "trades_per_day": round(float(tr.mean()), 2),
            "years": {y: round(float(np.mean([byday[d][0] for d in ds if d[:4] == y])), 1) for y in sorted({d[:4] for d in ds})}}
    ranked = sorted(rows.items(), key=lambda kv: -min(kv[1]["all names"]["dev_usd"], kv[1]["all names"]["test_usd"]))
    print(f"{len(days)} sessions; $ a day on $25,000 at 1x (x4 at the day-trading maximum); dev before {families.SPLIT}")
    for rname, v in ranked[:30]:
        a, e, o_ = v["all names"], v["even names"], v["odd names"]
        print(f"  {rname:52s} all ${a['dev_usd']:+6.1f}/${a['test_usd']:+6.1f} up {a['test_up']:.0%} {a['trades_per_day']:5.2f} tr/d | "
              f"even ${e['dev_usd']:+6.1f}/${e['test_usd']:+6.1f} | odd ${o_['dev_usd']:+6.1f}/${o_['test_usd']:+6.1f} | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in a["years"].items()))
    (ROOT / "strategies" / "scalp" / "families2.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
