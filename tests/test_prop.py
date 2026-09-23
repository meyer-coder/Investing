"""The prop-firm replay follows FundedNext's Legacy rules."""
import pytest

from evotrader.prop import LEGACY_25K, LEGACY_25K_FUNDED, Rules, TradePath, replay


def path(entry, eod, worst=None, realized=None):
    worst = worst if worst is not None else list(eod)
    days = list(range(entry, entry + len(eod)))
    return TradePath(entry, entry + len(eod), days, list(eod), list(worst),
                     realized if realized is not None else eod[-1])


def test_steady_days_pass_at_the_target():
    p = path(0, [400, 800, 1200, 1600])
    o = replay([p], 0, LEGACY_25K, horizon=50)
    assert o.result == "pass" and o.days == 4 and o.pnl == 1600


def test_one_big_day_raises_the_target_under_the_consistency_rule():
    # a +900 day means total profit must reach 900 / 0.4 = 2,250
    p = path(0, [900, 1300, 1700, 2100, 2300])
    o = replay([p], 0, LEGACY_25K, horizon=50)
    assert o.result == "pass" and o.pnl == 2300 and o.days == 5
    no_rule = Rules("x", 25_000, 1_250, 1_000, 0.0)
    assert replay([p], 0, no_rule, horizon=50).days == 2


def test_a_floating_loss_that_touches_the_trailing_floor_breaches():
    # up 800 at the close of day 1 -> floor rises to -200; day 2's low at -250 breaches
    p = path(0, [800, 300], worst=[700, -250])
    o = replay([p], 0, LEGACY_25K, horizon=50)
    assert o.result == "breach" and o.days == 2


def test_the_floor_locks_at_the_starting_balance():
    rules = LEGACY_25K_FUNDED
    # up 1,500 -> the floor would be +500 if it kept trailing, but it locks at 0
    p = path(0, [1500, 200], worst=[1400, 100])
    assert replay([p], 0, rules, horizon=50).result == "open"
    q = path(0, [1500, -50], worst=[1400, -60])
    assert replay([q], 0, rules, horizon=50).result == "breach"


def test_an_account_starts_with_the_next_entry_not_a_trade_already_open():
    a = path(0, [-900, -950], worst=[-950, -990], realized=-990)
    b = path(5, [300, 600], realized=600)
    o = replay([a, b], 1, LEGACY_25K, horizon=50)       # starts after trade a began
    assert o.result == "open" and o.pnl == 600
