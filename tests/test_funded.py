"""The funded-account replays for the breakout bot (strategies/sweeps/funded.py and sweetspot.py): each firm's
limit, daily limit, consistency rule, payouts and fees on made-up days."""
import sys
from pathlib import Path

import numpy as np

from evotrader import accounts

# funded.py imports its sibling data.py as `data`, and strategies/quick/index.py (through trend) imports
# strategies/mnq/data.py under the same name: load funded on its own, then put sys.path and sys.modules back
# so the other test files get their own modules
_path, _before = list(sys.path), dict(sys.modules)
for _name in ("data", "sweeps", "trend", "index"):
    sys.modules.pop(_name, None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies" / "sweeps"))
import funded  # noqa: E402
import sweetspot  # noqa: E402
sys.path[:] = _path
for _name in ("data", "sweeps", "trend", "index"):
    sys.modules.pop(_name, None)
    if _name in _before:
        sys.modules[_name] = _before[_name]


def test_a_bad_day_inside_the_limit_is_survived_and_booked_whole():
    pnl, low = [-2500.0, 100.0], [-2600.0, 0.0]
    assert funded.replay(pnl, low, 0, 3000.0, 0.0, 0.5, 0.0, horizon=2) == (2, 2, -2400.0)


def test_the_daily_limit_closes_the_day_at_the_limit():
    pnl, low = [-2500.0, 100.0], [-2600.0, 0.0]
    assert funded.replay(pnl, low, 0, 3000.0, 0.0, 0.5, 2000.0, horizon=2) == (2, 2, -1900.0)


def test_the_daily_limit_does_not_save_an_account_with_less_room_than_it():
    # up $500 then down: the floor has trailed to -$2,500, so a -$1,000 day after a -$2,000 day breaches
    pnl, low = [500.0, -2400.0, -1000.0], [0.0, -2400.0, -1000.0]
    assert funded.replay(pnl, low, 0, 3000.0, 0.0, 0.5, 2000.0, horizon=3) == (0, 3, -2500.0)


def test_an_intraday_touch_of_the_trailing_floor_ends_the_account():
    pnl, low = [1000.0, 0.0], [0.0, -1000.0]                              # the floor trails to $0 after day one
    assert funded.replay(pnl, low, 0, 1000.0, 0.0, 0.4, 0.0, horizon=2) == (0, 2, 0.0)


def test_consistency_share_sets_how_far_past_the_target_a_big_day_pushes_the_pass():
    pnl, low = [4000.0] + [1000.0] * 7, [0.0] * 8
    assert funded.replay(pnl, low, 0, 3000.0, 6000.0, 0.5, 2000.0, horizon=8) == (1, 5, 8000.0)   # 4,000 / 0.5
    assert funded.replay(pnl, low, 0, 3000.0, 6000.0, 0.4, 0.0, horizon=8) == (1, 7, 10000.0)     # 4,000 / 0.4


def test_the_ladder_sizes_up_only_when_the_room_allows():
    small = ([100.0] * 3, [0.0] * 3, 50.0)
    big = ([1000.0] * 3, [0.0] * 3, 700.0)
    # the floor trails, so the room stays $1,000 and a third of it never reaches the big rung's $700 bad day
    assert funded.replay_ladder([small, big], 0, 1000.0, 0.0, 0.4, 0.0, 1 / 3, horizon=3) == (2, 3, 300.0)
    # with $3,000 of room, a third is $1,000: the big rung every day
    assert funded.replay_ladder([small, big], 0, 3000.0, 0.0, 0.4, 0.0, 1 / 3, horizon=3) == (2, 3, 3000.0)


def _rung(pnl: float, low: float, n: int = 60) -> list:
    return [("1 MNQ", np.full(n, pnl), np.full(n, low), 100.0)]


def test_funded_payouts_leave_one_limit_of_room_and_pay_the_split():
    # +$200 a day on the FundedNext 25K: day 6 is the first above $1,000 with five winning days, and pays $200;
    # five more winning days bring $2,000 and pay half of it (80% to the owner each time)
    res = sweetspot.simulate(_rung(200.0, 0.0), accounts.FUNDEDNEXT_25K, [0], "funded", fixed=0, horizon=11)
    assert res["take"][0] == 0.8 * 200 + 0.8 * 1000
    assert res["left"][0] == 1000.0


def test_topstep_pays_the_first_ten_thousand_in_full():
    res = sweetspot.simulate(_rung(3000.0, 0.0), accounts.TOPSTEP_100K, [0], "funded", fixed=0, horizon=10)
    # day 5: $15,000, pays min(half, all but $3,000, the $5,000 cap) = $5,000; day 10: $25,000 -> $5,000 again
    assert res["take"][0] == 10_000.0


def test_a_lost_challenge_buys_the_next_one():
    # -$1,000 a day on the Topstep 100K: lost on days 3 and 6, three challenges in six sessions
    res = sweetspot.simulate(_rung(-1000.0, -1000.0), accounts.TOPSTEP_100K, [0], "career", fixed=0, horizon=6)
    assert res["bought"][0] == 3 and res["fees"][0] == 3 * 99.0 and res["net"][0] == -297.0


def test_topstep_bills_the_combine_monthly():
    res = sweetspot.simulate(_rung(0.0, 0.0), accounts.TOPSTEP_100K, [0], "career", fixed=0, horizon=42)
    assert res["fees"][0] == 3 * 99.0


def test_a_pass_needs_the_target_and_the_best_day_under_the_firm_share():
    res = sweetspot.simulate(_rung(1000.0, 0.0), accounts.TOPSTEP_100K, [0], "challenge", fixed=0, horizon=20)
    assert (res["event"][0], res["when"][0]) == (1, 6)
    res = sweetspot.simulate(_rung(1000.0, 0.0), accounts.TOPSTEP_100K, [0], "career", fixed=0, horizon=6)
    assert res["fees"][0] == 99.0 + 149.0 and res["passes"][0] == 1


def test_the_size_follows_the_room():
    small = ("1 MYM", np.full(5, 10.0), np.zeros(5), 100.0)
    big = ("1 MNQ", np.full(5, 1000.0), np.zeros(5), 900.0)
    # a third of $1,000 of room never reaches the big size's $900 bad day; a share of 1 does
    assert sweetspot.simulate([small, big], accounts.FUNDEDNEXT_25K, [0], "funded", 1 / 3, 1 / 3, horizon=5)["left"][0] == 50.0
    assert sweetspot.simulate([small, big], accounts.FUNDEDNEXT_25K, [0], "funded", 1.0, 1.0, horizon=1)["left"][0] == 1000.0


def test_the_room_guard_stops_the_day_before_the_limit():
    # a -$1,200 day on a $1,000 limit ends the account; a guard at half the room stops it at -$500
    rung = [("1 MNQ", np.array([-1200.0, 0.0]), np.array([-1200.0, 0.0]), 100.0)]
    lost = sweetspot.simulate(rung, accounts.FUNDEDNEXT_25K, [0], "funded", fixed=0, horizon=2)
    kept = sweetspot.simulate(rung, accounts.FUNDEDNEXT_25K, [0], "funded", fixed=0, guard=0.5, horizon=2)
    assert (lost["event"][0], lost["when"][0]) == (0, 1)
    assert kept["event"][0] == 2 and kept["left"][0] == -500.0


def test_an_account_without_room_for_one_small_stop_is_lost():
    # the guard halves the room each bad day; below $80 the account cannot trade and counts as lost
    rung = [("1 MYM", np.full(10, -1e9), np.full(10, -1e9), 100.0)]
    res = sweetspot.simulate(rung, accounts.FUNDEDNEXT_25K, [0], "funded", fixed=0, guard=0.5, min_room=80.0, horizon=10)
    assert (res["event"][0], res["when"][0]) == (0, 5)                   # 1000 -> 500 -> 250 -> 125 -> 62.5: lost
