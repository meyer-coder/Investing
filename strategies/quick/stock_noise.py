"""The noise-area breakout (index.py) run on each of the 72 stocks, and as one book across them.

    python strategies/quick/stock_noise.py

On the Nasdaq-100 the band breakout of Zarattini and Aziz (2023) was the one
quick trade positive in every year from 2020 to 2026, but small.  If the
same edge sits in single stocks, a book of many names spreads it over many
independent trades a day.  For each name and day: the band is the name's
average absolute move from its open at each minute over the past 14
sessions, around the larger (smaller) of the open and the previous close;
every half hour a close above the upper band buys (below the lower band
sells short) at the next minute's open, and a close back inside the band or
past the running average price exits at the next open; everything is out at
the 15:59 close.

The book: at most `slots` positions at once, each 4x $25,000 / slots; when
more names signal at a check than slots are free, the widest break (in
multiples of the band) goes first.  Mid prices (panel.build_mid); each round
trip pays COST_BP of notional.  Dev Sep 2022 to Aug 2024, test after.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402

SPLIT = "2024-09-01"
ACCOUNT = 25_000.0
COST_BP = 3.0
T = 390
_P: dict = {}


def prepare():
    cube, dates, names = panel.load_panel("mid")
    O, H, L, C = (cube[..., j].astype(np.float64) for j in range(4))
    pc = np.concatenate([np.full((1, O.shape[1]), np.nan), C[:-1, :, -1]], axis=0)
    move = np.abs(C / O[:, :, :1] - 1.0)
    return {"O": O, "H": H, "L": L, "C": C, "pc": pc, "move": move, "dates": dates, "names": names}


def signals(P, i, lookback=14, every=30, band_mult=1.0, vwap_exit=True):
    """For day i: per name, the list of (entry check t, side, strength, exit bar) of its trades, and per-trade returns."""
    O, H, L, C, pc, move = P["O"][i], P["H"][i], P["L"][i], P["C"][i], P["pc"][i], P["move"]
    sig = band_mult * np.nanmean(move[i - lookback:i], axis=0)               # (names, T)
    base_up = np.fmax(O[:, 0], pc)[:, None]
    base_dn = np.fmin(O[:, 0], pc)[:, None]
    up = base_up * (1 + sig)
    dn = base_dn * (1 - sig)
    vwap = np.cumsum((H + L + C) / 3, axis=1) / np.arange(1, T + 1)
    checks = list(range(every - 1, T - 1, every))
    trades = []                                                              # (name, t_entry_check, side, strength, ret)
    for k in range(O.shape[0]):
        if np.isnan(sig[k]).any() or np.isnan(C[k]).any() or np.isnan(pc[k]):
            continue
        pos, px, t0, strength = 0, 0.0, 0, 0.0
        for t in checks:
            c = C[k, t]
            if pos == 0:
                if c > up[k, t]:
                    pos, px, t0, strength = 1, O[k, t + 1], t, (c / up[k, t] - 1) / max(sig[k, t], 1e-6)
                elif c < dn[k, t]:
                    pos, px, t0, strength = -1, O[k, t + 1], t, (dn[k, t] / c - 1) / max(sig[k, t], 1e-6)
            else:
                out = (c < (max(up[k, t], vwap[k, t]) if vwap_exit else up[k, t])) if pos > 0 else \
                      (c > (min(dn[k, t], vwap[k, t]) if vwap_exit else dn[k, t]))
                if out:
                    trades.append((k, t0, pos, strength, pos * (O[k, t + 1] / px - 1.0) - COST_BP * 1e-4, t))
                    pos = 0
        if pos:
            trades.append((k, t0, pos, strength, pos * (C[k, T - 1] / px - 1.0) - COST_BP * 1e-4, T - 1))
    return trades


def book_day(trades, slots):
    """Replay the day's trades with at most `slots` at once, strongest break first at each check."""
    size = 4 * ACCOUNT / slots
    pnl, n = 0.0, 0
    busy = []                                                                # exit check of each open position
    for t0 in sorted({x[1] for x in trades}):
        busy = [e for e in busy if e > t0]
        cands = sorted([x for x in trades if x[1] == t0], key=lambda x: -x[3])
        for k, _, side, strength, ret, t_exit in cands:
            if len(busy) >= slots:
                break
            pnl += size * ret
            n += 1
            busy.append(t_exit)
    return pnl, n


def _job(args):
    i, cfg = args
    lb, every, bm, vw = cfg
    return i, signals(_P, i, lb, every, bm, vw)


def summarize(dates, v, n, label=""):
    ds = np.array(dates)
    ok = ~np.isnan(v)
    ds, v, n = ds[ok], v[ok], n[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean()), 1) for y in sorted({x[:4] for x in ds})}
    row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
           "test_up": round(float((v[test] > 0).mean()), 3), "trades_per_day": round(float(n.mean()), 1),
           "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0),
           "sharpe_dev": round(float(v[dev].mean() / (v[dev].std() + 1e-9) * np.sqrt(252)), 2),
           "sharpe_test": round(float(v[test].mean() / (v[test].std() + 1e-9) * np.sqrt(252)), 2),
           "days_200_test": round(float((v[test] >= 200).mean()), 3), "years": years}
    if label:
        print(f"  {label:56s} ${row['dev_usd']:+6.1f}/${row['test_usd']:+6.1f} a day at 4x | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} "
              f"| worst ${row['worst_day']:+.0f} dd ${row['max_drawdown']:+.0f} | {row['trades_per_day']:.1f} tr/d | $200+ {row['days_200_test']:.0%} | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()), flush=True)
    return row


def main() -> int:
    import multiprocessing as mp
    _P.update(prepare())
    dates, names = _P["dates"], _P["names"]
    nd = len(dates)
    res = {}
    per_name = {}
    for cfg in itertools.product((14,), (30, 15), (1.0, 1.5), (True,)):
        with mp.get_context("fork").Pool(4) as pool:
            got = dict(pool.map(_job, [(i, cfg) for i in range(15, nd)], chunksize=16))
        tag = f"lb{cfg[0]} every {cfg[1]}m x{cfg[2]}"
        # each name alone: average net return per trade, dev and test
        by = {}
        for i, trades in got.items():
            for k, t0, side, st, ret, te in trades:
                by.setdefault(names[k], {"dev": [], "test": []})["dev" if dates[i] < SPLIT else "test"].append(ret)
        per_name[tag] = {n: {"dev_bp": round(float(np.mean(v["dev"]) * 1e4), 2) if v["dev"] else None,
                             "test_bp": round(float(np.mean(v["test"]) * 1e4), 2) if v["test"] else None,
                             "trades": len(v["dev"]) + len(v["test"])} for n, v in by.items()}
        allr = [r for i, tr in got.items() for (_, _, _, _, r, _) in tr]
        dev_r = [r for i, tr in got.items() if dates[i] < SPLIT for (_, _, _, _, r, _) in tr]
        test_r = [r for i, tr in got.items() if dates[i] >= SPLIT for (_, _, _, _, r, _) in tr]
        print(f"--- {tag}: {len(allr)} single-name trades, {np.mean(dev_r) * 1e4:+.2f} bp dev / {np.mean(test_r) * 1e4:+.2f} bp test per trade after {COST_BP} bp; "
              f"names positive in both halves: {sum(1 for v in per_name[tag].values() if (v['dev_bp'] or 0) > 0 and (v['test_bp'] or 0) > 0)} of {len(per_name[tag])}")
        for slots in (3, 5, 10):
            v = np.full(nd, np.nan)
            n = np.zeros(nd)
            for i, trades in got.items():
                v[i], n[i] = book_day(trades, slots)
            res[f"{tag} | {slots} slots"] = summarize(dates, v, n, f"{tag} | {slots} slots")
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    (ROOT / "strategies" / "quick" / "stock_noise.json").write_text(json.dumps({"books": dict(ranked), "per_name": per_name}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
