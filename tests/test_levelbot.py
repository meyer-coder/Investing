"""The options-level paper trader: first touch only, next-minute fill, stop and target, flat at 15:55."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))

import levelbot  # noqa: E402


def _bars(path):
    """One-minute bars from 09:30 New York (13:30 UTC in September), opens at the previous close."""
    t0 = datetime(2026, 9, 22, 13, 30)
    out, prev = [], path[0]
    for m, c in enumerate(path):
        o = prev
        out.append(((t0 + timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M"), o, max(o, c) + 0.5, min(o, c) - 0.5, c, 100.0))
        prev = c
    return out


def test_sells_the_first_touch_of_the_call_wall_and_takes_its_target(monkeypatch):
    path = [30_000.0] * 30 + [30_000.0 + 10 * k for k in range(1, 11)] + [30_100.0 - 10 * k for k in range(1, 20)]
    path += [29_910.0] * (390 - len(path))
    monkeypatch.setattr(levelbot, "bars", lambda day: _bars(path))
    res = levelbot.replay("2026-09-22", {"call_wall": 30_100.0})
    (t,) = res["trades"]
    assert t["side"] == "short" and t["why"] == "target"
    assert t["entry"] == 30_100.0                       # the bar reaching 30,100 is the touch; in at the next open
    assert t["exit"] == 30_100.0 - levelbot.TARGET
    assert abs(t["usd"] - (levelbot.TARGET - levelbot.COST) * levelbot.POINT * levelbot.CONTRACTS) < 1e-6


def test_a_put_wall_long_that_keeps_falling_is_stopped_and_the_level_is_not_traded_twice(monkeypatch):
    path = [30_000.0] * 30 + [30_000.0 - 10 * k for k in range(1, 30)] + [29_710.0 + 10 * k for k in range(1, 30)]
    path += [30_000.0] * (390 - len(path))
    monkeypatch.setattr(levelbot, "bars", lambda day: _bars(path))
    res = levelbot.replay("2026-09-22", {"put_wall": 29_900.0})
    assert len(res["trades"]) == 1                      # the second pass through 29,900 is not traded
    (t,) = res["trades"]
    assert t["side"] == "long" and t["why"] == "stop"
    assert t["exit"] == t["entry"] - levelbot.STOP


def test_nothing_is_held_past_1555(monkeypatch):
    path = [30_000.0] * 355 + [30_050.0] + [30_049.0] * 34     # touches at 15:25, then sits still
    monkeypatch.setattr(levelbot, "bars", lambda day: _bars(path))
    res = levelbot.replay("2026-09-22", {"call_wall": 30_050.0})
    (t,) = res["trades"]
    assert t["why"] == "15:55" and t["out"] == "15:55"
