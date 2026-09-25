"""The NQ and ES day-trading bot, sized in micro contracts for large leverage.

    python strategies/sweeps/bot.py

The legs, on the same one-minute bars (data.py, January 2013 to September 2026):

* noise: the noise-area breakout (Zarattini and Aziz, 2023), checked every 30
  minutes, out when the close is back in the band or through VWAP, a resting
  stop 0.30% from the entry, flat at the close (strategies/quick/trend.py);
* pm break: a one-minute close beyond the pre-market range (07:00-09:29 New
  York) that holds five more minutes, entered by 11:30, the stop 0.02% back
  past the broken level, held to the close (sweeps.py, "break PM to 11:30
  hold 5m target close");
* pd break: the same off yesterday's high and low, out at 1R (sweeps.py's
  best ES setting on 2013-2019);
* sweep: the best liquidity sweep on 2013-2019 for each index, to show what
  adding one does.

Each leg's trades cost 1 bp of the price a round trip, $6 on an MNQ at
today's level (the real cost is nearer $2.50) and $3.85 on an MES, and every
trade is priced at today's level, so a 2013 trade counts at today's contract
size.  A day's worst is each trade's worst open loss added up, which is more
cautious than the real path.

Sizing: one "unit" is 1 MNQ on each NQ leg and 2 MES on each ES leg (an MES
moves about half as many dollars).  The units are run on a $25,000 account
and through $50K and $150K funded evaluations started every fifth session:
a $3,000 / $9,000 target, a $2,000 / $4,500 drawdown limit that trails the
best end-of-day balance, a $1,000 / $3,000 daily loss limit, and no day more
than half the profit.  Firms differ; these are typical.  Written to bot.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "strategies" / "quick"))
import data                                                                  # noqa: E402
import sweeps                                                                # noqa: E402
import trend                                                                 # noqa: E402

OPEN = data.OPEN
SPLIT = sweeps.SPLIT
LAST3 = "2023-09-22"
ACCOUNT = 25_000.0
POINT = {"NQ": 2.0, "ES": 5.0}                     # dollars a point on an MNQ and an MES
PER_UNIT = {"NQ": 1, "ES": 2}                      # micros of each on a leg, per unit
STOP = 0.003
LEGS = {
    "NQ noise": ("NQ", "noise", {}),
    "NQ pm break": ("NQ", "level", {"mode": "break", "kind": "PM", "until": "11:30", "hold": 5, "target": None}),
    "NQ sweep": ("NQ", "level", {"mode": "sweep", "kind": "PD", "until": "15:00", "back": 5, "target": 2.0}),
    "ES noise": ("ES", "noise", {}),
    "ES pd break": ("ES", "level", {"mode": "break", "kind": "PD", "until": "15:00", "hold": 5, "target": 1.0}),
    "ES sweep": ("ES", "level", {"mode": "sweep", "kind": "PD", "until": "11:30", "back": 15, "target": "mid"}),
}
FUNDED = {"50K": dict(max_loss=2000.0, daily_loss=1000.0, target=3000.0),
          "150K": dict(max_loss=4500.0, daily_loss=3000.0, target=9000.0)}


def rth(D: dict) -> dict:
    return {"O": D["O"][:, OPEN:], "H": D["H"][:, OPEN:], "L": D["L"][:, OPEN:], "C": D["C"][:, OPEN:], "pc": D["pc"]}


def leg_days(D: dict, how: str, setting: dict):
    """Per session: net return on the notional, the day's worst open return, trades."""
    if how == "noise":
        r, lo, n, _ = trend.noise_days(rth(D), hard_stop=STOP)
        return np.nan_to_num(r), np.nan_to_num(lo), n
    nd = len(D["dates"])
    r, lo, n = np.zeros(nd), np.zeros(nd), np.zeros(nd)
    H, L = D["H"], D["L"]
    for i, side, net, _, _, e, u, entry in sweeps.run(D, **setting):
        worst = (L[i, e:u + 1].min() / entry - 1.0) if side > 0 else (1.0 - H[i, e:u + 1].max() / entry)
        r[i] += net
        lo[i] += min(worst - sweeps.COST / 2, net)
        n[i] += 1
    return r, lo, n


def summary(ds: np.ndarray, usd: np.ndarray, low: np.ndarray, account: float = ACCOUNT) -> dict:
    eq = np.cumsum(usd)
    dd = float((eq - np.maximum.accumulate(np.r_[0.0, eq])[1:]).min())
    dev, test, last3 = ds < SPLIT, ds >= SPLIT, ds >= LAST3
    years = {y: round(float(usd[np.char.startswith(ds, y)].mean()), 1) for y in sorted({d[:4] for d in ds})}
    return {"usd_day": round(float(usd.mean()), 1), "dev_usd_day": round(float(usd[dev].mean()), 1),
            "test_usd_day": round(float(usd[test].mean()), 1), "last3_usd_day": round(float(usd[last3].mean()), 1),
            "sharpe": round(float(usd.mean() / (usd.std() + 1e-12) * np.sqrt(252)), 2),
            "up_days": round(float((usd[usd != 0] > 0).mean()), 3), "worst_day": round(float(usd.min()), 0),
            "worst_intraday": round(float(low.min()), 0), "max_drawdown": round(dd, 0),
            "max_drawdown_pct": round(-dd / account * 100, 1), "years_usd_day": years,
            "losing_years": sum(v < 0 for v in years.values())}


def main() -> int:
    Ds = {inst: data.load(inst) for inst in ("NQ", "ES")}
    level = {inst: float(D["C"][-1, -1]) for inst, D in Ds.items()}
    micro = {inst: level[inst] * POINT[inst] for inst in Ds}                 # dollars of index per micro contract
    print(f"Today's level: NQ {level['NQ']:,.0f} (an MNQ is ${micro['NQ']:,.0f} of index), "
          f"ES {level['ES']:,.0f} (an MES ${micro['ES']:,.0f})")
    common = np.array(sorted(set(Ds["NQ"]["dates"]) & set(Ds["ES"]["dates"])))
    out = {"level": level, "legs": {}, "correlation": {}, "books": {}}
    per_unit, nq_only = {}, {}
    print("\nEach leg, one unit (1 MNQ or 2 MES), on its own sessions; $ a day at today's level")
    print(f"  {'leg':14s} {'trades':>6} {'a day':>6} {'$/day':>7} {'13-19':>7} {'20-26':>7} {'last 3y':>7} {'Sharpe':>6} "
          f"{'worst day':>9} {'max dd':>8}  by year")
    for name, (inst, how, setting) in LEGS.items():
        D = Ds[inst]
        r, lo, n = leg_days(D, how, setting)
        mult = PER_UNIT[inst] * micro[inst]
        ds = np.array(D["dates"])
        st = summary(ds, r * mult, lo * mult)
        st["trades"] = int(n.sum())
        st["trades_a_day"] = round(float(n.mean()), 2)
        out["legs"][name] = st
        print(f"  {name:14s} {st['trades']:6d} {st['trades_a_day']:6.2f} {st['usd_day']:+7.1f} {st['dev_usd_day']:+7.1f} "
              f"{st['test_usd_day']:+7.1f} {st['last3_usd_day']:+7.1f} {st['sharpe']:+6.2f} {st['worst_day']:+9.0f} "
              f"{st['max_drawdown']:+8.0f}  " + " ".join(f"{y[2:]}:{v:+.0f}" for y, v in st["years_usd_day"].items()), flush=True)
        keep = np.isin(ds, common)
        per_unit[name] = (r[keep] * mult, lo[keep] * mult)
        if inst == "NQ":
            nq_only[name] = (r * mult, lo * mult)
    names = list(LEGS)
    cor = np.corrcoef(np.array([per_unit[k][0] for k in names]))
    print("\nDaily correlation of the legs (sessions both indexes have):")
    for a, k in enumerate(names):
        print(f"  {k:14s} " + " ".join(f"{cor[a, b]:+.2f}" for b in range(len(names))))
        out["correlation"][k] = {names[b]: round(float(cor[a, b]), 2) for b in range(len(names))}

    books = {"NQ noise": ["NQ noise"], "NQ noise + pm break": ["NQ noise", "NQ pm break"],
             "NQ noise + pm break + ES noise": ["NQ noise", "NQ pm break", "ES noise"],
             "all four breakouts": ["NQ noise", "NQ pm break", "ES noise", "ES pd break"],
             "all four + both sweeps": names}
    print(f"\nBooks at one unit, {len(common)} sessions both indexes have, {common[0]} to {common[-1]}")
    for bname, legs in books.items():
        usd = sum(per_unit[k][0] for k in legs)
        low = sum(per_unit[k][1] for k in legs)
        st = summary(common, usd, low)
        mu, sd = float(usd.mean()), float(usd.std())
        st["kelly_units_25k"] = round(mu / sd ** 2 * ACCOUNT, 1)
        out["books"][bname] = {"legs": legs, "one_unit": st}
        print(f"  {bname:32s} ${st['usd_day']:+6.1f} a day (13-19 {st['dev_usd_day']:+.1f}, 20-26 {st['test_usd_day']:+.1f}, "
              f"last 3y {st['last3_usd_day']:+.1f}) Sharpe {st['sharpe']:+.2f} worst day {st['worst_day']:+.0f} "
              f"max dd {st['max_drawdown']:+.0f}; growth-optimal (Kelly) on $25k: {st['kelly_units_25k']:.1f} units", flush=True)

    nq_dates = np.array(Ds["NQ"]["dates"])
    print(f"\nThe leverage ladder on all {len(nq_dates)} NQ sessions: each bot on its own account "
          f"(the book is the two together, e.g. two $12,500 accounts)")
    for bname in ("NQ noise", "NQ pm break", "NQ noise + pm break"):
        legs = books.get(bname, [bname])
        usd1 = sum(nq_only[k][0] for k in legs)
        low1 = sum(nq_only[k][1] for k in legs)
        eq = np.cumsum(usd1)
        trough = int(np.argmin(eq - np.maximum.accumulate(eq)))
        peak = int(np.argmax(eq[:trough + 1])) if trough else 0
        back = np.flatnonzero(eq[trough:] >= eq[peak])
        print(f"-- {bname}: worst stretch {nq_dates[peak]} to {nq_dates[trough]}, "
              f"{'back to the old high ' + str(nq_dates[trough + back[0]]) if back.size else 'not back to its old high yet'}")
        ladder = {}
        for units in (1, 2, 3, 5, 8, 10, 15, 20):
            usd, low = usd1 * units, low1 * units
            st = summary(nq_dates, usd, low)
            before = np.r_[0.0, np.cumsum(usd)[:-1]]
            st["units"] = units
            st["notional_x"] = round(units * len(legs) * micro["NQ"] / ACCOUNT, 1)
            st["lowest_account"] = round(float(ACCOUNT + (before + np.minimum(low, usd)).min()), 0)
            # the same leverage kept on a growing or shrinking account: contracts resized each day
            g = np.cumprod(1 + np.clip(usd / ACCOUNT, -1, None))
            st["growth_a_year"] = round(float(g[-1] ** (252 / len(g)) - 1), 3) if g[-1] > 0 else -1.0
            st["resized_deepest_fall"] = round(float((g / np.maximum.accumulate(np.r_[1.0, g])[1:] - 1).min()), 3)
            for f in FUNDED:
                st[f"funded_{f}"] = trend.topstep(nq_dates, usd, low, **FUNDED[f])
            ladder[units] = st
            print(f"  {units:2d} MNQ a leg ({st['notional_x']:4.1f}x of $25k): ${st['usd_day']:+6.0f} a day, last 3y ${st['last3_usd_day']:+6.0f}; "
                  f"worst day {st['worst_day']:+7.0f} (intraday {st['worst_intraday']:+7.0f}); worst stretch {st['max_drawdown']:+8.0f} "
                  f"({st['max_drawdown_pct']:.0f}% of $25k); resized daily {st['growth_a_year']:+.0%} a year, deepest fall {st['resized_deepest_fall']:.0%}; "
                  f"50K eval pass {st['funded_50K']['pass']:.0%} breach {st['funded_50K']['breach']:.0%} "
                  f"({st['funded_50K']['median_days_to_pass']} sessions); "
                  f"150K pass {st['funded_150K']['pass']:.0%} breach {st['funded_150K']['breach']:.0%} "
                  f"({st['funded_150K']['median_days_to_pass']} sessions)", flush=True)
        out["books"].setdefault(bname, {"legs": legs})["ladder"] = ladder
        out["books"][bname]["worst_stretch"] = [str(nq_dates[peak]), str(nq_dates[trough])]
    (HERE / "bot.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
