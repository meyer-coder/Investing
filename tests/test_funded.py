"""The funded-account replay for the breakout bot (strategies/sweeps/funded.py): each firm's limit, daily limit
and consistency rule on made-up days."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies" / "sweeps"))
import funded  # noqa: E402


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
