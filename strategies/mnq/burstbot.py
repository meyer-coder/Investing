"""The burst bot on 10-second bars: one position at a time, flat by 15:55.

    python strategies/mnq/burstbot.py

Runs a burst rule from bursts.py through the MNQ simulator (sim.py) on
Dukascopy's 10-second Nasdaq-100 bars: a decision on each 10-second bar's
close, the fill at the next bar's open, out after a set number of bars or at
a resting stop, never past 15:55.  Reports points and dollars a day per MNQ
contract, first half of the days against the second, and replays the days as
Topstep 100K accounts at a few contract sizes (account.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
import account                                                               # noqa: E402
import duka                                                                  # noqa: E402
import sim                                                                   # noqa: E402
from data import Day                                                         # noqa: E402


def sessions10(start: str = "2000-01-01", end: str = "2100-01-01") -> Dict[str, Day]:
    """10-second bars 09:30-15:59 New York as Day objects, stamps 'YYYY-MM-DD HH:MM:SS' UTC."""
    import datetime as dt
    out = {}
    for d, a in duka.load_seconds(start, end, first=(9, 30), last=(15, 59)).items():
        if len(a) < 2000:
            continue
        stamps = [dt.datetime.fromtimestamp(t, tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") for t in a[:, 0]]
        out[d] = Day(d, stamps, a[:, 1].copy(), a[:, 2].copy(), a[:, 3].copy(), a[:, 4].copy())
    return out


def features10(day: Day, prev: Day = None) -> Dict[str, np.ndarray]:
    """Minutes since 09:30 (fractional), 10/20/30-second moves and the typical
    10-second move of the last half hour (180 bars), from closed bars only."""
    import datetime as dt
    c = day.c
    n = len(c)
    t0 = dt.datetime.strptime(day.stamps[0], "%Y-%m-%d %H:%M:%S")
    secs = np.array([(dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S") - t0).total_seconds() for s in day.stamps])
    r1 = np.concatenate([[0.0], c[1:] / c[:-1] - 1.0])
    sq = np.concatenate([[0.0], np.cumsum(r1 ** 2)])
    lo = np.maximum(np.arange(n) - 179, 0)
    cnt = np.arange(1, n + 1) - lo
    sd = np.maximum(np.sqrt((sq[1:] - sq[lo]) / np.maximum(cnt, 1)), 1e-6)
    f = {"mso": secs / 60.0, "sd": sd, "r10": r1}
    for k in (2, 3):
        r = np.full(n, np.nan)
        r[k:] = c[k:] / c[:-k] - 1.0
        f[f"r{k * 10}"] = r
    return f


def fade(k: int = 1, z: float = 4.0, start: float = 6.0, end: float = 385.0):
    """Sell a burst up / buy a burst down of more than z typical 10-second
    moves over k bars, between `start` and `end` minutes after 09:30."""
    def signal(f):
        r = f[f"r{k * 10}"]
        w = (f["mso"] >= start) & (f["mso"] <= end)
        big = np.abs(r) > z * f["sd"] * np.sqrt(k)
        return np.where(w & big, -np.sign(r), 0).astype(int)
    return signal


def evaluate(days: Dict[str, Day], rules: sim.Rules, contracts=(1, 3, 5, 8)) -> dict:
    keys = sorted(days)
    split = keys[len(keys) // 2]
    res = sim.run(days, rules, features10)
    first = sim.Result([t for t in res.trades if t.day < split], [d for d in keys if d < split])
    second = sim.Result([t for t in res.trades if t.day >= split], [d for d in keys if d >= split])
    out = {"split": split, "all": sim.summary(res), "first_half": sim.summary(first), "second_half": sim.summary(second),
           "cost_2.5": sim.summary(res, cost=2.5), "topstep_100k": {}}
    for n in contracts:
        out["topstep_100k"][n] = account.replay(res, n)
    return out


def main() -> int:
    days = sessions10()
    print(f"{len(days)} sessions of 10-second bars, {min(days)} to {max(days)}", flush=True)
    results = {}
    for name, rules in {
        "fade a 10s burst >4x, hold 2m": sim.Rules(signal=fade(1, 4.0), hold=12, last_entry=375, flat_at=385),
        "fade a 10s burst >4x, hold 1m": sim.Rules(signal=fade(1, 4.0), hold=6, last_entry=375, flat_at=385),
        "fade a 30s burst >4x, hold 2m": sim.Rules(signal=fade(3, 4.0), hold=12, last_entry=375, flat_at=385),
        "fade a 10s burst >6x, hold 2m": sim.Rules(signal=fade(1, 6.0), hold=12, last_entry=375, flat_at=385),
        # the screenshot's shape: about a 15-point stop (5 bp at 29,000) and a target three times as far
        "fade a 10s burst >4x, stop 5bp, target 15bp": sim.Rules(signal=fade(1, 4.0), hold=60, stop_bp=5, target_bp=15,
                                                                last_entry=375, flat_at=385),
        "go with a 10s burst >4x, stop 5bp, target 15bp": sim.Rules(signal=lambda f: -fade(1, 4.0)(f), hold=60, stop_bp=5,
                                                                   target_bp=15, last_entry=375, flat_at=385),
    }.items():
        r = results[name] = evaluate(days, rules)
        a, f1, f2 = r["all"], r["first_half"], r["second_half"]
        print(f"{name:34s} {a['trades_per_day']:5.2f} tr/d {a['avg_points']:+6.2f} pts win {a['win']:.0%} hold {a['avg_minutes'] * 10 / 60:.1f}m "
              f"${a['usd_per_day']:6.1f}/d/MNQ up {a['days_up']:.0%} | halves ${f1['usd_per_day']:6.1f} / ${f2['usd_per_day']:6.1f} "
              f"| at 2.5 pts ${r['cost_2.5']['usd_per_day']:6.1f}", flush=True)
        for n, t in r["topstep_100k"].items():
            print(f"    {n} MNQ: ${t['usd_per_day']:7.1f}/d median ${t['median_day']:6.1f} $150+ days {t['days_150_plus']:.0%} "
                  f"worst ${t['worst_day']:7.0f} | combine pass {t['combine_pass']:.0%} breach {t['combine_breach']:.0%} "
                  f"| funded payout first {t['funded_payout_first']:.0%} breach first {t['funded_breach_first']:.0%}", flush=True)
    (ROOT / "strategies" / "mnq" / "burstbot.json").write_text(json.dumps(results, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
