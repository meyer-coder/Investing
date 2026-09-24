"""Market-neutral intraday books across the 72 names: buy some, short as many, rebalance every half hour.

    python strategies/quick/xsection.py

Holding one name for hours is mostly a bet on the market; a long-short book
nets the market out and spreads the bet over many names, which is where an
intraday edge can be steady.  Three documented effects, on the mid-price
panel (Sep 2022 to Sep 2026; dev to Aug 2024, test after):

* short-term reversal: the names that beat (lagged) the others most over the
  last half hour give some of it back (catch up) in the next;
* its momentum mirror, and the same on the day's move so far;
* intraday periodicity (Heston, Korajczyk and Sadka, 2010): a name's return in
  a given half hour of the day tends to repeat that half hour's average over
  the past 20 sessions;
* the overnight gap reversed from the open.

Each half hour the book buys the `n` names ranked lowest and shorts the `n`
ranked highest (or the reverse), equal dollars, entering a minute after the
half hour and leaving a minute after the next one, so no trade is filled on
the price that set it.  Gross exposure is 4x $25,000; each name traded pays
COST_BP of its notional per round trip (a spread of about 2 bp, half each
way, plus fees); names held into the next half hour on the same side pay
nothing to stay.
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
_P: dict = {}


def prepare(slot: int = 30):
    cube, dates, names = panel.load_panel("mid")
    O = cube[..., 0].astype(np.float64)
    C = cube[..., 3].astype(np.float64)
    # trades fill at the open a minute after each boundary (09:31, 10:01, ..., 15:31) and at the 15:59 close;
    # signals read the close of the minute before the fill
    marks = [1] + list(range(slot + 1, 390, slot))
    E = np.concatenate([O[:, :, marks], C[:, :, -1:]], axis=2)             # (days, names, slots + 1)
    S = C[:, :, [m - 1 for m in marks]]                                     # (days, names, slots)
    prev_close = np.concatenate([np.full((1, O.shape[1]), np.nan), C[:-1, :, -1]], axis=0)
    return {"E": E, "S": S, "dates": dates, "names": names, "prev_close": prev_close, "open0": O[:, :, 0],
            "slot": slot, "marks": marks}


def _res(x):
    return x - np.nanmean(x, axis=1, keepdims=True)


def book(P, kind="reversal", n=7, lookback=20, hold=1, source="last"):
    """Per-day P&L (dollars on $25,000 at 4x gross) and names traded."""
    E, S, pc = P["E"], P["S"], P["prev_close"]
    nd, nn, _ = E.shape
    R = E[:, :, 1:] / E[:, :, :-1] - 1.0                                     # what each slot's position earns
    Rres = _res(R)
    # what a trader knows at each fill: the move over the last slot and since the previous close, to the minute before
    S_prev = np.concatenate([pc[:, :, None], S[:, :, :-1]], axis=2)
    last = _res(S / S_prev - 1.0)
    day_so_far = _res(S / pc[:, :, None] - 1.0)
    gap = _res(P["open0"] / pc - 1.0)
    gross = 4 * ACCOUNT
    pnl = np.full(nd, np.nan)
    traded = np.zeros(nd)
    nslots = R.shape[2]
    for i in range(lookback + 1, nd):
        day, cnt = 0.0, 0
        prev_pos = np.zeros(nn)
        for j in range(nslots):
            if kind == "periodicity":
                sig = np.nanmean(Rres[i - lookback:i, :, j], axis=0)
                direction = 1                                                   # buy the names whose slot usually rises
            elif kind in ("reversal", "momentum"):
                sig = last[i, :, j] if source == "last" else day_so_far[i, :, j]
                direction = -1 if kind == "reversal" else 1
            elif kind == "gap":
                if j >= hold:
                    break
                sig = gap[i]
                direction = -1
            else:
                raise ValueError(kind)
            ok = ~np.isnan(sig) & ~np.isnan(R[i, :, j])
            if ok.sum() < 2 * n + 10:
                continue
            idx = np.flatnonzero(ok)
            order = idx[np.argsort(sig[idx])]
            lo, hi = order[:n], order[-n:]
            pos = np.zeros(nn)
            if direction > 0:
                pos[hi], pos[lo] = 1.0, -1.0
            else:
                pos[lo], pos[hi] = 1.0, -1.0
            w = pos * (gross / (2 * n))
            day += float(np.nansum(w * R[i, :, j]))
            turnover = np.abs(pos - prev_pos)                                  # 1 for a new name, 2 for a flip
            day -= float((turnover * (gross / (2 * n))).sum()) * COST_BP / 2 * 1e-4
            cnt += int((turnover > 0).sum())
            prev_pos = pos
        day -= float((np.abs(prev_pos) * (gross / (2 * n))).sum()) * COST_BP / 2 * 1e-4
        pnl[i] = day
        traded[i] = cnt
    return pnl, traded


def summarize(dates, pnl, ntr, label=""):
    ok = ~np.isnan(pnl)
    ds, v, n = np.array(dates)[ok], pnl[ok], ntr[ok]
    dev, test = ds < SPLIT, ds >= SPLIT
    eq = np.cumsum(v)
    dd = float((eq - np.maximum.accumulate(eq)).min())
    years = {y: round(float(v[np.array([x[:4] == y for x in ds])].mean()), 1) for y in sorted({x[:4] for x in ds})}
    row = {"dev_usd": round(float(v[dev].mean()), 1), "test_usd": round(float(v[test].mean()), 1),
           "test_up": round(float((v[test] > 0).mean()), 3), "names_traded_per_day": round(float(n.mean()), 1),
           "worst_day": round(float(v.min()), 0), "max_drawdown": round(dd, 0),
           "sharpe_dev": round(float(v[dev].mean() / (v[dev].std() + 1e-9) * np.sqrt(252)), 2),
           "sharpe_test": round(float(v[test].mean() / (v[test].std() + 1e-9) * np.sqrt(252)), 2),
           "days_200_test": round(float((v[test] >= 200).mean()), 3), "years": years}
    if label:
        print(f"  {label:52s} ${row['dev_usd']:+6.1f}/${row['test_usd']:+6.1f} a day at 4x | Sharpe {row['sharpe_dev']:+.2f}/{row['sharpe_test']:+.2f} "
              f"| worst ${row['worst_day']:+.0f} dd ${row['max_drawdown']:+.0f} | {row['names_traded_per_day']:.0f} names/d | "
              + " ".join(f"{y[2:]}:{x:+.0f}" for y, x in years.items()), flush=True)
    return row


def main() -> int:
    res = {}
    for slot in (30, 15, 60):
        P = prepare(slot)
        dates = P["dates"]
        print(f"--- {slot}-minute rebalancing; {len(dates)} sessions; cost {COST_BP} bp a round trip")
        for kind, n, source in itertools.product(("reversal", "momentum"), (5, 10), ("last", "day")):
            label = f"{kind} on the {'last ' + str(slot) + 'm' if source == 'last' else 'day so far'} n{n} ({slot}m)"
            pnl, tr = book(P, kind, n, source=source)
            res[label] = summarize(dates, pnl, tr, label)
        for n, lb in itertools.product((5, 10), (10, 20, 40)):
            label = f"periodicity lb{lb} n{n} ({slot}m)"
            pnl, tr = book(P, "periodicity", n, lookback=lb)
            res[label] = summarize(dates, pnl, tr, label)
        if slot == 30:
            for n, hold in itertools.product((5, 10), (1, 2, 13)):
                label = f"gap reversal n{n} held {hold} slot(s)"
                pnl, tr = book(P, "gap", n, hold=hold)
                res[label] = summarize(dates, pnl, tr, label)
    ranked = sorted(res.items(), key=lambda kv: -min(kv[1]["dev_usd"], kv[1]["test_usd"]))
    print("best by the weaker of dev and test:")
    for k_, v in ranked[:12]:
        print(f"  {k_:52s} ${v['dev_usd']:+6.1f}/${v['test_usd']:+6.1f} | Sharpe {v['sharpe_dev']:+.2f}/{v['sharpe_test']:+.2f} | dd ${v['max_drawdown']:+.0f}")
    (ROOT / "strategies" / "quick" / "xsection.json").write_text(json.dumps(dict(ranked), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
