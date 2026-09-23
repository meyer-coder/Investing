"""Same-day trading: flat by the close, as a prop firm without overnight holds requires."""
import numpy as np
import pytest

from evotrader.config import EvolutionConfig
from evotrader.data import Bars, Universe, cash_session_bars
from evotrader.features import build_features
from evotrader.genome import Genome, compile_genome
from evotrader.journal import Trade
from evotrader.prop import MICROS, trade_paths
from evotrader.runner import run_backtest


def _days(n):
    return [str(np.datetime64("2026-01-01") + np.timedelta64(i, "D")) for i in range(n)]


def _universe(rows, symbol="X"):
    """rows: (open, high, low, close), one per day."""
    dates = _days(len(rows))
    cols = [np.asarray([r[k] for r in rows], dtype=float) for k in range(4)]
    bars = Bars(symbol, dates, cols[0], cols[1], cols[2], cols[3], np.full(len(rows), 1e6))
    return Universe({symbol: bars}, dates)


def _genome(stop=0.0, target=0.0, cooldown=0):
    return compile_genome(Genome.from_dict({
        "name": "Every Day", "entry_rules": [{"when": "close > 0", "weight": 1.0}],
        "exit_rules": [{"when": "bars_held >= 50"}],
        "risk": {"max_position_pct": 1.0, "stop_loss_pct": stop, "take_profit_pct": target,
                 "cooldown_bars": cooldown}}))


def _run(u, genome, **kw):
    return run_backtest(genome, u, build_features(u), starting_cash=10_000, commission_bps=0.0,
                        slippage_bps=0.0, start_bar=1, day_trade=True, **kw)


def test_every_trade_is_bought_at_the_open_and_sold_at_that_days_close():
    u = _universe([(100, 101, 99, 100), (100, 101, 99, 100), (100, 103, 99.5, 102),
                   (102, 102.5, 100, 101), (101, 102, 100, 101.5)])
    trades = _run(u, _genome()).journal.trades
    assert len(trades) == 3                       # days 2, 3 and 4: a fresh entry every open
    for t, (o, c) in zip(trades, [(100, 102), (102, 101), (101, 101.5)]):
        assert t.entry_date == t.exit_date
        assert t.entry_price == pytest.approx(o) and t.exit_price == pytest.approx(c)
        assert t.bars_held == 0


def test_a_same_day_stop_fills_at_the_stop():
    u = _universe([(100, 101, 99, 100), (100, 101, 99, 100), (100, 100.5, 98.5, 100.2),
                   (100, 101, 99, 100)])
    t = _run(u, _genome(stop=0.01)).journal.trades[0]
    assert t.exit_price == pytest.approx(99.0) and "stop order" in t.exit_reason


def test_a_same_day_target_fills_at_the_target():
    u = _universe([(100, 101, 99, 100), (100, 101, 99, 100), (100, 102.5, 99.5, 100.2),
                   (100, 101, 99, 100)])
    t = _run(u, _genome(stop=0.01, target=0.02)).journal.trades[0]
    assert t.exit_price == pytest.approx(102.0) and "target order" in t.exit_reason


def test_with_both_inside_the_days_range_the_stop_is_assumed_first():
    u = _universe([(100, 101, 99, 100), (100, 101, 99, 100), (100, 103, 98, 102),
                   (100, 101, 99, 100)])
    t = _run(u, _genome(stop=0.01, target=0.02)).journal.trades[0]
    assert t.exit_price == pytest.approx(99.0)


def test_nothing_is_held_at_any_close():
    u = _universe([(100, 101, 99, 100)] * 3 + [(100, 104, 99, 103)] * 5)
    r = _run(u, _genome())
    assert r.exposure == 0.0
    assert all(t.entry_date == t.exit_date for t in r.journal.trades)
    assert r.journal.trades[-1].exit_date == u.calendar[-1]


def test_a_cooldown_of_n_skips_n_days_after_each_trade():
    u = _universe([(100, 101, 99, 100)] * 8)
    days = lambda cd: [t.entry_date for t in _run(u, _genome(cooldown=cd)).journal.trades]
    assert days(1) == [u.calendar[2], u.calendar[4], u.calendar[6]]
    assert days(2) == [u.calendar[2], u.calendar[5]]


def test_exec_bars_fill_at_other_prices_than_the_features_are_built_from():
    rows = [(100, 101, 99, 100)] * 4
    u = _universe(rows)
    other = _universe([(200, 206, 199, 204)] * 4).bars["X"]
    t = _run(u, _genome(), exec_bars={"X": other}).journal.trades[0]
    assert t.entry_price == pytest.approx(200) and t.exit_price == pytest.approx(204)


def test_cash_session_bars_keep_the_future_close_and_take_the_funds_shape():
    dates = _days(3)
    fut = Bars("NQ1!", dates, np.array([990.0, 1000, 1010]), np.array([1010.0, 1020, 1030]),
               np.array([980.0, 990, 1000]), np.array([1000.0, 1010, 1020]), np.array([5.0, 6, 7]))
    # the fund misses day 2 (a stock-market holiday the future traded through)
    proxy = Bars("QQQ", [dates[0], dates[1]], np.array([49.0, 50.0]), np.array([51.0, 50.8]),
                 np.array([48.5, 49.5]), np.array([50.0, 50.5]), np.array([1.0, 1.0]))
    cash = cash_session_bars(fut, proxy)
    assert list(cash.close) == [1000, 1010, 1020] and list(cash.volume) == [5, 6, 7]
    assert cash.open[0] == pytest.approx(980.0)            # 49 / 50 of the 1000 close
    assert cash.high[0] == pytest.approx(1020.0) and cash.low[0] == pytest.approx(970.0)
    assert cash.open[1] == pytest.approx(1010 * 50.0 / 50.5)
    assert cash.open[2] == cash.high[2] == cash.low[2] == cash.close[2] == 1020   # nothing to trade


def _trade(date, entry, exit_, reason):
    return Trade(symbol="NQ1!", entry_date=date, exit_date=date, entry_price=entry,
                 exit_price=exit_, shares=1.0, pnl=0.0, ret=exit_ / entry - 1, bars_held=0,
                 entry_reason="x", exit_reason=reason)


def test_prop_paths_of_a_same_day_trade_use_the_days_low_unless_stopped_above_it():
    dates = _days(2)
    bars = Bars("NQ1!", dates, np.array([100.0, 100]), np.array([102.0, 102]),
                np.array([97.0, 97]), np.array([101.0, 101]), np.ones(2))
    micro = MICROS["MNQ"]
    flat = trade_paths([_trade(dates[0], 100.0, 101.0, "flat at the close: same-day trade")], bars,
                       micro=micro, contracts=1, price_now=100.0)[0]
    # $200 of notional: +1% is $2, the day's low (-3%) is -$6, before costs
    assert flat.days == [0] and flat.entry_bar == flat.exit_bar == 0
    assert flat.eod == [pytest.approx(flat.realized)]
    assert flat.worst[0] == pytest.approx(-6.0 - 0.75 - 0.5)
    stopped = trade_paths([_trade(dates[1], 100.0, 99.0, "stop order hit intrabar (-1.00%)")], bars,
                          micro=micro, contracts=1, price_now=100.0)[0]
    assert stopped.stopped and stopped.worst[0] == pytest.approx(stopped.realized)


def test_the_cash_session_is_for_same_day_trading_with_a_known_fund():
    with pytest.raises(ValueError, match="day_trade"):
        EvolutionConfig(symbols=["NQ1!"], session="cash", population=10, elites=2).validate()
    with pytest.raises(ValueError, match="proxy"):
        EvolutionConfig(symbols=["AAPL"], session="cash", day_trade=True,
                        population=10, elites=2).validate()
    EvolutionConfig(symbols=["NQ1!"], session="cash", day_trade=True,
                    population=10, elites=2).validate()


# ------------------------------------------------------------------ carried positions

def _carry_genome(exit_when="bars_held >= 2", stop=0.0, cooldown=5):
    return compile_genome(Genome.from_dict({
        "name": "Carry", "entry_rules": [{"when": "close > 0", "weight": 1.0}],
        "exit_rules": [{"when": exit_when}],
        "risk": {"max_position_pct": 1.0, "stop_loss_pct": stop, "cooldown_bars": cooldown}}))


def _carry(u, genome, **kw):
    return run_backtest(genome, u, build_features(u), starting_cash=10_000, commission_bps=0.0,
                        slippage_bps=0.0, start_bar=1, day_trade=True, carry=True, **kw)


def test_a_carried_position_is_flat_every_night_and_bought_back_each_open():
    u = _universe([(100, 101, 99, 100)] * 2 + [(100, 102, 99, 101), (103, 104, 102, 103),
                                               (99, 100, 98, 99.5), (99, 100, 98, 99)] + [(99, 100, 98, 99)] * 3)
    r = _carry(u, _carry_genome())
    trades = r.journal.trades
    # entered at day 2's open; bars_held reaches 2 at day 4's close, so days 2, 3 and 4
    assert [t.entry_date for t in trades] == u.calendar[2:5]
    assert all(t.entry_date == t.exit_date for t in trades)
    assert [(t.entry_price, t.exit_price) for t in trades] == [(100, 101), (103, 103), (99, 99.5)]
    assert trades[1].entry_reason.startswith("carried")
    # the 101 -> 103 and 103 -> 99 gaps were never held
    assert r.final_equity == pytest.approx(10_000 * (1 + (101 / 100 - 1) + 0 + (99.5 / 99 - 1)), rel=1e-3)


def test_the_daily_stop_ends_the_carried_position():
    u = _universe([(100, 101, 99, 100)] * 2 + [(100, 102, 99.5, 101), (101, 101.5, 99.8, 100)]
                  + [(100, 101, 99.5, 100)] * 4)
    trades = _carry(u, _carry_genome(exit_when="bars_held >= 5"), day_stop=0.01).journal.trades
    assert len(trades) == 2
    assert trades[1].exit_price == pytest.approx(99.99) and "daily stop" in trades[1].exit_reason


def test_the_strategys_own_stop_is_measured_from_its_first_entry():
    # down 1% a day from a 100 entry: the 2.5% stop (on the close) ends it at day 4's close
    rows = [(100, 101, 99, 100)] * 2 + [(100, 100.2, 98.8, 99), (99, 99.2, 97.8, 98),
                                        (98, 98.2, 96.8, 97)] + [(97, 98, 96, 97)] * 3
    trades = _carry(_universe(rows), _carry_genome(exit_when="bars_held >= 50", stop=0.025)).journal.trades
    assert [t.entry_date for t in trades] == _universe(rows).calendar[2:5]


def test_carry_and_day_stop_need_same_day_trading():
    with pytest.raises(ValueError, match="day_trade"):
        EvolutionConfig(symbols=["NQ1!"], carry=True, population=10, elites=2).validate()


def test_a_day_stop_that_only_caps_the_day_buys_back_at_the_next_open():
    u = _universe([(100, 101, 99, 100)] * 2 + [(100, 102, 99.5, 101), (101, 101.5, 99.8, 100)]
                  + [(100, 101, 99.5, 100)] * 4)
    trades = _carry(u, _carry_genome(exit_when="bars_held >= 3"), day_stop=0.01,
                    day_stop_exit=False).journal.trades
    assert "daily stop" in trades[1].exit_reason
    assert [t.entry_date for t in trades] == u.calendar[2:6]      # still held on days 4 and 5


def test_without_a_day_stop_a_carried_run_holds_the_same_days_as_a_multi_day_run():
    rng = np.random.default_rng(7)
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.012, 400))
    opn = close * (1 + rng.normal(0, 0.003, 400))
    rows = [(o, max(o, c) * 1.004, min(o, c) * 0.996, c) for o, c in zip(opn, close)]
    u = _universe(rows)
    g = compile_genome(Genome.from_dict({
        "name": "Dips", "entry_rules": [{"when": "zscore20 < -1", "weight": 1.0}],
        "exit_rules": [{"when": "zscore20 > 0.5"}],
        "risk": {"max_position_pct": 1.0, "stop_loss_pct": 0.04, "trailing_stop_pct": 0.03,
                 "max_hold_bars": 8, "cooldown_bars": 2}}))
    f = build_features(u)
    multi = run_backtest(g, u, f, starting_cash=10_000, commission_bps=0.0, slippage_bps=0.0)
    carried = run_backtest(g, u, f, starting_cash=10_000, commission_bps=0.0, slippage_bps=0.0,
                           day_trade=True, carry=True)
    held = lambda trades: {d for t in trades for d in u.calendar[u.calendar.index(t.entry_date):
                                                                 u.calendar.index(t.exit_date)]}
    multi_days = held(multi.journal.trades)
    carried_days = {t.entry_date for t in carried.journal.trades} - {u.calendar[-1]}
    assert len(multi_days) > 20 and carried_days == multi_days     # the last bar is a liquidation
