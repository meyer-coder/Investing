"""The options levels (strategies/mnq/levels.py): contracts that expired before the session drop out."""
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies" / "mnq"))

import levels  # noqa: E402


def _raw(contracts):
    return {"timestamp": "test", "data": {"symbol": "QQQ", "current_price": 100.0, "options": [
        {"option": code, "open_interest": oi, "iv": 0.2, "gamma": 0.05} for code, oi in contracts]}}


def test_the_closing_days_expiry_is_left_out_of_the_next_sessions_levels():
    raw = _raw([("QQQ260924C00105000", 90_000),                     # expires at the Sep 24 close: the biggest call
                ("QQQ260925C00103000", 1_000), ("QQQ260925P00097000", 1_000),
                ("QQQ260924P00095000", 90_000)])
    same_day = levels.compute(raw, dt.date(2026, 9, 24))
    next_day = levels.compute(raw, dt.date(2026, 9, 25))
    assert same_day["call_wall"] == 105.0 and same_day["contracts"] == 4
    assert next_day["expiries"] == ["2026-09-25"] and next_day["contracts"] == 2
    assert (next_day["call_wall"], next_day["put_wall"], next_day["max_pain_expiry"]) == (103.0, 97.0, "2026-09-25")
