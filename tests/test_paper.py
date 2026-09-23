"""The paper ledger: fills at the open with slippage, synced go-live positions, marks at the close."""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies" / "etf"))

import paper  # noqa: E402
from evotrader.data import Bars, Universe  # noqa: E402


def _universe(closes):
    d, days = date(2026, 1, 5), []
    while len(days) < len(closes):
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    c = np.asarray(closes, dtype=float)
    o = np.concatenate([[c[0]], c[:-1]]) * 1.001          # opens a touch over the last close
    b = Bars("AAA", days, o, np.maximum(o, c) * 1.01, np.minimum(o, c) * 0.99, c, np.full(len(c), 1e6))
    return Universe({"AAA": b}, days)


def _account(start):
    item = {"rank": 1, "name": "Dip", "symbols": ["AAA"],
            "genome": {"name": "Dip", "entry_rules": [{"when": "ret1 < -0.02", "weight": 1.0}],
                       "exit_rules": [{"when": "bars_held >= 3"}],
                       "risk": {"max_position_pct": 1.0, "max_positions": 1, "max_gross_exposure": 1.0}}}
    acct = paper.open_account({"id": "t", "rank": 1, "size": 1.0, "label": "#1"}, item)
    acct["start"] = start
    return acct


CLOSES = [100.0] * 12 + [96.0] + [97.0, 98.0, 99.0, 100.0, 101.0] + [100.0] * 4 + [95.0] + [96.0] * 7


def test_fills_at_the_open_with_slippage_and_marks_every_close():
    u = _universe(CLOSES)
    acct = _account(u.calendar[5])
    paper.advance(acct, u, with_levels=False)
    sides = [f["side"] for f in acct["fills"]]
    assert sides[:4] == ["buy", "sell", "buy", "sell"] or sides[:3] == ["buy", "sell", "buy"]
    s = paper.SLIP / 1e4
    for f in acct["fills"]:
        i = u.calendar.index(f["date"])
        opened = float(u.bars["AAA"].open[i])
        want = opened * (1 + s) if f["side"] == "buy" else opened * (1 - s)
        assert abs(f["price"] - want) < 1e-3
    assert len(acct["marks"]) == len(u.calendar) - 5
    m = acct["marks"][-1]
    held = acct["position"]["shares"] * CLOSES[-1] if acct["position"] else 0.0
    assert abs(m["equity"] - (acct["cash"] + held)) < 0.01
    assert all(not f.get("synced") for f in acct["fills"])


def test_a_position_held_at_go_live_is_bought_at_that_open_and_marked_synced():
    u = _universe(CLOSES)
    buy_day = u.calendar.index("2026-01-22")      # the day after the first dip's close
    acct = _account(u.calendar[buy_day + 1])      # go live one session into that trade
    paper.advance(acct, u, with_levels=False)
    first = acct["fills"][0]
    assert first["side"] == "buy" and first["synced"] and first["date"] == acct["start"]


def test_the_ledger_is_never_recomputed():
    u = _universe(CLOSES)
    acct = _account(u.calendar[5])
    paper.advance(acct, u.slice(0, 20), with_levels=False)
    before = [dict(f) for f in acct["fills"]]
    paper.advance(acct, u, with_levels=False)
    assert acct["fills"][:len(before)] == before
    assert [m["date"] for m in acct["marks"]] == u.calendar[5:]


def test_a_retired_bot_leaves_the_roster_with_its_record_and_reason():
    ledger = {"accounts": [_account("2026-01-05"), {**_account("2026-01-05"), "id": "u"}]}
    paper.retire(ledger, ["t"], "trades a fund the owner dropped", "2026-01-20")
    assert [a["id"] for a in ledger["accounts"]] == ["u"]
    gone = ledger["retired"][0]
    assert gone["id"] == "t" and gone["retired"] == "2026-01-20" and gone["why_retired"]


def test_each_symbol_pays_its_own_slippage():
    from evotrader.broker import PaperBroker
    b = PaperBroker(10_000.0, commission_bps=0.0, slippage_bps=2.0, slippage_by_symbol={"CHEAP": 30.0})
    assert b.buy("CHEAP", 1_000.0, 10.0, "d", 0, "t")
    assert b.buy("DEAR", 1_000.0, 10.0, "d", 0, "t")
    assert abs(b.positions["CHEAP"].entry_price - 10.0 * 1.003) < 1e-9
    assert abs(b.positions["DEAR"].entry_price - 10.0 * 1.0002) < 1e-9
