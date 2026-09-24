"""Two bots on one account: short the sharp dips, buy the sharp rallies.

    python strategies/mnq/twobots.py

The idea: do not short all the time; when the Nasdaq-100 drops hard, short it
(one bot), and when it rallies hard, buy it (the other).  Two bots trading the
same contract on one account net out (long 10 and short 10 is flat), so on
the account they are one bot: after a drop of more than a threshold over the
last 5 or 15 minutes, sell; after a rise of as much, buy; one position at a
time, next minute's open, a resting stop and target, out at 15:55.  The dip
buyer (the reverse) is shown beside it.  Six years of Dukascopy Nasdaq-100
minutes, points at 29,000 after 1.25 a round trip, and Topstep 100K replays
at 5 and 10 MNQ.
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
from edges import features                                                   # noqa: E402

_DAYS: dict = {}


def signal(window: int, thr: float, how: str):
    def f(ft):
        r = ft[f"r{window}"]
        w = (ft["mso"] >= 5) & (ft["mso"] <= 375)
        sgn = np.where(r < -thr, -1, np.where(r > thr, 1, 0))           # go with the move
        if how == "short dips only":
            sgn = np.where(sgn < 0, -1, 0)
        elif how == "buy the dip (reverse)":
            sgn = np.where(r < -thr, 1, 0)
        return np.where(w, sgn, 0)
    return f


def _run(job):
    window, thr, how, (stop, target) = job
    rules = sim.Rules(signal=signal(window, thr, how), hold=10_000, stop_bp=stop, target_bp=target,
                      last_entry=375, flat_at=385)
    res = sim.run(_DAYS["d"], rules, features)
    keys = sorted(_DAYS["d"])
    split = "2024-01-01"
    first = sim.Result([t for t in res.trades if t.day < split], [d for d in keys if d < split])
    second = sim.Result([t for t in res.trades if t.day >= split], [d for d in keys if d >= split])
    return {"window": window, "threshold": thr, "how": how, "stop_bp": stop, "target_bp": target,
            "all": sim.summary(res), "2020-2023": sim.summary(first), "2024-2026": sim.summary(second),
            "topstep_100k": {n: account.replay(res, n) for n in (5, 10)}}


def main() -> int:
    import multiprocessing as mp
    _DAYS["d"] = data.sessions("duka")
    jobs = list(itertools.product((5, 15), (0.0025, 0.005),
                                  ("short dips and buy rallies", "short dips only", "buy the dip (reverse)"),
                                  ((5.0, 15.0), (10.0, 20.0), (10.0, 10.0))))
    jobs = [j for j in jobs if not (j[0] == 5 and j[1] == 0.005)]           # a 0.5% drop in 5 minutes is too rare
    with mp.get_context("fork").Pool(4) as pool:
        results = pool.map(_run, jobs)
    print(f"{len(_DAYS['d'])} sessions; points per MNQ at 29,000 after 1.25 a round trip; $ per day per MNQ")
    for r in results:
        a, x, y = r["all"], r["2020-2023"], r["2024-2026"]
        t5, t10 = r["topstep_100k"][5], r["topstep_100k"][10]
        print(f"  {r['window']:2d}m move > {r['threshold']:.2%} | {r['how']:27s} | stop/target {r['stop_bp']:g}/{r['target_bp']:g} bp: "
              f"{a['trades_per_day']:.2f} tr/d win {a['win']:.0%} {a['avg_points']:+6.2f} pts | ${x['usd_per_day']:+6.1f} / ${y['usd_per_day']:+6.1f} a day "
              f"(2020-23 / 2024-26) | 10 MNQ: ${t10['usd_per_day']:+7.1f}/d, breach {t10['combine_breach']:.0%}, pass {t10['combine_pass']:.0%}")
    (ROOT / "strategies" / "mnq" / "twobots.json").write_text(json.dumps(results, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
