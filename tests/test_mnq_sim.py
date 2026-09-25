"""The MNQ simulator: next-open fills, time, stop and target exits, one position at a time,
nothing past 15:55, and the daily caps."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
# tests/test_funded.py imports strategies/sweeps/data.py as `data`; drop it so sim and this file get strategies/mnq/data.py
sys.modules.pop("data", None)

import sim  # noqa: E402
from data import Day  # noqa: E402


def _day(date="2026-09-22", n=390, path=None):
    t0 = datetime.strptime(date + " 13:30", "%Y-%m-%d %H:%M")
    stamps = [(t0 + timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M") for m in range(n)]
    c = np.full(n, 29_000.0) if path is None else np.asarray(path, dtype=float)
    o = np.concatenate([[c[0]], c[:-1]])
    return Day(date, stamps, o, np.maximum(o, c) + 1.0, np.minimum(o, c) - 1.0, c)


def _features(day, prev):
    return {"mso": np.arange(len(day.o), dtype=float)}


def _at(*minutes, side=1):
    def signal(f):
        s = np.zeros(len(f["mso"]))
        s[list(minutes)] = side
        return s
    return signal


def test_fills_at_the_next_open_and_leaves_after_the_hold():
    c = 29_000.0 + np.arange(390, dtype=float)             # a point a minute, every minute
    res = sim.run({"2026-09-22": _day(path=c)}, sim.Rules(signal=_at(100), hold=10), _features)
    (t,) = res.trades
    assert (t.entry_i, t.exit_i, t.why) == (101, 111, "time")
    assert t.entry == c[100] and t.exit == c[110]          # opens are the previous closes here
    assert abs(res.points(cost=0.0)[0] - 10 / c[100] * sim.TODAY_LEVEL) < 1e-9


def test_a_resting_stop_fills_at_the_stop_or_at_a_gap_open():
    c = np.full(390, 29_000.0)
    c[103:] = 28_900.0                                      # a 100-point drop after the entry
    res = sim.run({"2026-09-22": _day(path=c)}, sim.Rules(signal=_at(100), hold=10, stop_bp=10), _features)
    (t,) = res.trades
    assert t.why == "stop" and t.exit == 29_000.0 * (1 - 10 / 1e4)   # traded down through it: filled at the stop
    day = _day()
    day.o[103:], day.h[103:], day.l[103:], day.c[103:] = 28_900.0, 28_901.0, 28_899.0, 28_900.0
    res = sim.run({"2026-09-22": day}, sim.Rules(signal=_at(100), hold=10, stop_bp=10), _features)
    (t,) = res.trades
    assert t.why == "stop" and t.exit == 28_900.0           # opened below the stop: filled at the open
    c = np.full(390, 29_000.0)
    c[103] = 28_990.0                                       # a gentle dip: the low touches the stop
    res = sim.run({"2026-09-22": _day(path=c)}, sim.Rules(signal=_at(100), hold=10, stop_bp=0.2), _features)
    (t,) = res.trades
    assert t.why == "stop" and abs(t.exit - 29_000.0 * (1 - 0.2 / 1e4)) < 1e-6


def test_a_target_takes_profit_and_a_short_profits_on_a_drop():
    c = np.full(390, 29_000.0)
    c[104:] = 28_950.0
    res = sim.run({"2026-09-22": _day(path=c)}, sim.Rules(signal=_at(100, side=-1), hold=10, target_bp=5), _features)
    (t,) = res.trades
    assert t.side == -1 and t.why == "target" and t.ret_bp > 0


def test_one_position_at_a_time_and_flat_before_the_close():
    res = sim.run({"2026-09-22": _day()}, sim.Rules(signal=_at(100, 102, 104, 380), hold=10), _features)
    assert [t.entry_i for t in res.trades] == [101]         # the later signals came while it was held; 380 is after 15:45
    res = sim.run({"2026-09-22": _day()}, sim.Rules(signal=_at(374), hold=30), _features)
    (t,) = res.trades
    assert t.exit_i == 385 and t.why == "close"             # out at 15:55 whatever the hold


def test_the_daily_caps_stop_new_trades_once_reached():
    r = sim.Result(days=["d"])
    r.trades = [sim.Trade("d", 1, 1, 2, 29_000.0, 29_000.0 * (1 + x / 1e4), "time") for x in (-10.0, -10.0, 20.0)]
    full = r.daily_usd(cost=0.0)["d"]
    capped = r.daily_usd(cost=0.0, day_loss=100.0)["d"]
    assert abs(full - 0.0) < 1e-6
    assert abs(capped - (-116.0)) < 1e-6                    # two 29-point losses on $2 a point, then no more
    r.trades = [sim.Trade("d", 1, 1, 2, 29_000.0, 29_000.0 * (1 + x / 1e4), "time") for x in (30.0, -10.0)]
    assert abs(r.daily_usd(cost=0.0, day_target=150.0)["d"] - 174.0) < 1e-6
