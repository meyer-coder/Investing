"""Wait for the bounce: small targets, no stop, big size.

    python strategies/mnq/bounce.py

The idea: the Nasdaq-100 wiggles 0.05-0.15% all the time, so be in with
size, take a small profit, and if it goes the wrong way just wait, it comes
back.  This tests it as stated on Dukascopy's Nasdaq-100 minutes, September
2020 to September 2026: from 09:31, be long (or short) at the next minute's
open, take profit at +0.05%, +0.10% or +0.15%, no stop, back in at the next
open after each win, and whatever is open at 15:55 is closed at the market.
Each day's worst open loss counts against Topstep 100K's $3,000 limit in
real time, at 5, 8 and 10 MNQ (10 MNQ is about $590,000 of index, 5.9 times a
100K account).
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import account                                                               # noqa: E402
import data                                                                  # noqa: E402
import sim                                                                   # noqa: E402

_DAYS: dict = {}


def _features(day, prev):
    return {"mso": np.arange(len(day.o), dtype=float)}


def _run(job):
    side, target_bp = job
    rules = sim.Rules(signal=lambda f: np.full(len(f["mso"]), side), hold=10_000, target_bp=target_bp,
                      last_entry=375, flat_at=385)
    res = sim.run(_DAYS["d"], rules, _features)
    pts = res.points()
    worst = np.array([t.worst_bp for t in res.trades]) * sim.TODAY_LEVEL / 1e4
    wins = pts[pts > 0]
    losses = pts[pts <= 0]
    out = {"side": "long" if side > 0 else "short", "target_bp": target_bp,
           "trades_per_day": round(len(pts) / len(res.days), 2),
           "trade_win_rate": round(float((pts > 0).mean()), 3),
           "avg_win_points": round(float(wins.mean()), 1) if len(wins) else 0.0,
           "avg_loss_points": round(float(losses.mean()), 1) if len(losses) else 0.0,
           "worst_trade_points": round(float(pts.min()), 1),
           "worst_open_loss_points": round(float(worst.min()), 1),
           "per_mnq": sim.summary(res), "topstep_100k": {n: account.replay(res, n) for n in (5, 8, 10)}}
    return out


def main() -> int:
    import multiprocessing as mp
    _DAYS["d"] = data.sessions("duka")
    jobs = list(itertools.product((1, -1), (5.0, 10.0, 15.0)))
    with mp.get_context("fork").Pool(4) as pool:
        results = pool.map(_run, jobs)
    print(f"{len(_DAYS['d'])} sessions, {min(_DAYS['d'])} to {max(_DAYS['d'])}; take profit at the target, no stop, "
          "flat at 15:55; points per MNQ contract ($2 a point), after 1.25 points a round trip")
    for r in results:
        m = r["per_mnq"]
        print(f"\n{r['side']:5s} target {r['target_bp'] / 100:.2f}%: {r['trades_per_day']} trades a day, {r['trade_win_rate']:.0%} of them win "
              f"(avg win {r['avg_win_points']:+.1f} pts, avg loss {r['avg_loss_points']:+.1f} pts, worst {r['worst_trade_points']:+.0f} pts, "
              f"worst open loss {r['worst_open_loss_points']:+.0f} pts)")
        print(f"      per MNQ: ${m['usd_per_day']:+.1f} a day, days up {m['days_up']:.0%}, worst day ${m['worst_day']:+,.0f}, "
              f"by year " + " ".join(f"{y[2:]}:{v:+.0f}" for y, v in m["years"].items()))
        for n, t in r["topstep_100k"].items():
            print(f"      {n:2d} MNQ: ${t['usd_per_day']:+8.1f}/day, median ${t['median_day']:+7.1f}, $150+ days {t['days_150_plus']:.0%}, "
                  f"down days {t['days_down']:.0%}, worst ${t['worst_day']:+9,.0f} | Topstep Combine pass {t['combine_pass']:.0%}, "
                  f"breach {t['combine_breach']:.0%}")
    (ROOT / "strategies" / "mnq" / "bounce.json").write_text(json.dumps(results, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
