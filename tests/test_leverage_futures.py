"""Account leverage, continuous futures, date-based holdouts and hand breeding."""
import json
from datetime import datetime, timezone

import numpy as np
import pytest

from evotrader.broker import PaperBroker
from evotrader.cli import main
from evotrader.config import EvolutionConfig
from evotrader.data import (Bars, _session_complete, date_cut, fetch_tradingview_future,
                            is_continuous_future, load_universe, ratio_adjust,
                            tradingview_future)
from evotrader.evaluate import Signal, contracts_for, evaluate, format_signals
from evotrader.evolution import Evolution
from evotrader.features import build_features
from evotrader.genome import Genome, compile_genome
from evotrader.runner import run_backtest
from evotrader.sessions import session_features
from evotrader.store import Store
from evotrader.tvdata import _to_bars

ALWAYS = {"name": "Always", "entry_rules": [{"when": "close > 0", "weight": 1.0}],
          "exit_rules": [{"when": "close < 0"}],
          "risk": {"max_position_pct": 1.0, "max_positions": 1, "stop_loss_pct": 0.0}}


# ------------------------------------------------------------------ broker

def test_leverage_lets_the_broker_hold_twice_equity():
    b = PaperBroker(10_000.0, commission_bps=0.0, slippage_bps=0.0, leverage=2.0)
    assert b.buy("NQ", 20_000.0, 100.0, "d", 0, "in")
    assert b.cash == pytest.approx(-10_000.0)
    assert b.equity({"NQ": 100.0}) == pytest.approx(10_000.0)
    assert b.equity({"NQ": 101.0}) == pytest.approx(10_200.0)   # 1% move, 2% of equity


def test_unlevered_broker_is_still_bounded_by_cash():
    b = PaperBroker(10_000.0, commission_bps=0.0, slippage_bps=0.0)
    assert b.buy("NQ", 20_000.0, 100.0, "d", 0, "in")
    assert b.cash == pytest.approx(0.0)
    assert b.invested({"NQ": 100.0}) == pytest.approx(10_000.0)


def test_backtest_at_2x_doubles_the_first_day_and_the_exposure():
    universe = load_universe(["AAA"], "2015-01-01", "2016-06-30", offline=True, min_bars=100)
    features = build_features(universe)
    compiled = compile_genome(Genome.from_dict(ALWAYS))
    one = run_backtest(compiled, universe, features, starting_cash=10_000.0,
                       commission_bps=0.0, slippage_bps=0.0)
    two = run_backtest(compiled, universe, features, starting_cash=10_000.0,
                       commission_bps=0.0, slippage_bps=0.0, leverage=2.0)
    # twice the shares, so twice the dollars on every day after the fill
    d1 = one.journal.equity[3] - one.journal.equity[2]
    d2 = two.journal.equity[3] - two.journal.equity[2]
    assert d2 == pytest.approx(2 * d1, rel=1e-9)
    assert 1.5 < two.exposure < 2.5
    assert 0.7 < one.exposure <= 1.0 + 1e-9


def test_config_rejects_absurd_leverage():
    with pytest.raises(ValueError):
        EvolutionConfig(leverage=0.5).validate()
    with pytest.raises(ValueError):
        EvolutionConfig(leverage=50).validate()


# ------------------------------------------------------------------ futures data

def _bars(symbol, dates, close):
    c = np.asarray(close, dtype=float)
    return Bars(symbol, list(dates), c * 0.999, c * 1.01, c * 0.99, c, np.full(len(c), 1000.0))


def test_ratio_adjustment_keeps_the_new_contracts_return_across_a_roll():
    dates = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]
    # front contract 100 -> 101, then the switch to a contract trading 1.0 higher
    plain = _bars("NQ1!", dates, [100.0, 101.0, 102.5, 103.0])
    additive = _bars("NQ1!", dates, [101.0, 102.0, 102.5, 103.0])   # gap of +1.0 added before
    out = ratio_adjust(plain, additive)
    r = out.close[1:] / out.close[:-1] - 1
    assert r[0] == pytest.approx(101.0 / 100.0 - 1)             # inside the old contract
    assert r[1] == pytest.approx(102.5 / 102.0 - 1)             # the new contract's own return
    assert r[2] == pytest.approx(103.0 / 102.5 - 1)
    assert out.close[-1] == pytest.approx(103.0)                  # the live contract is untouched
    assert np.allclose(out.high / out.close, plain.high / plain.close)


def test_continuous_future_names():
    assert is_continuous_future("NQ1!") and is_continuous_future("CME_MINI:ES2!")
    assert not is_continuous_future("QQQ") and not is_continuous_future("NQ")
    assert tradingview_future("nq1!") == "CME_MINI:NQ1!"
    assert tradingview_future("CME_MINI:NQ1!") == "CME_MINI:NQ1!"


def test_fetch_future_pairs_plain_and_backadjusted_pulls():
    dates = [str(np.datetime64("2020-03-02") + np.timedelta64(i, "D")) for i in range(60)]
    later = list(np.linspace(111.0, 130.0, 59))
    calls = []

    def fake(symbol, timeframe, bars, **kw):
        calls.append((symbol, kw.get("backadjust", False), kw.get("trading_dates")))
        if kw.get("backadjust"):
            return _bars(symbol, dates, [110.0] + later)
        return _bars(symbol, dates, [100.0] + later)          # roll between bars 0 and 1

    out = fetch_tradingview_future("NQ1!", fetch=fake)
    assert out.symbol == "NQ1!" and len(out) == 60
    assert {c[1] for c in calls} == {False, True}
    assert all(c[0] == "CME_MINI:NQ1!" and c[2] for c in calls)
    assert out.close[1] / out.close[0] - 1 == pytest.approx(111.0 / 110.0 - 1)


def test_a_futures_session_is_complete_only_after_the_settlement():
    before = datetime(2026, 9, 22, 20, 59, tzinfo=timezone.utc)    # 16:59 New York
    after = datetime(2026, 9, 22, 21, 1, tzinfo=timezone.utc)
    assert not _session_complete("2026-09-22", before)
    assert _session_complete("2026-09-22", after)


def test_trading_dates_move_evening_opens_to_the_next_day():
    sunday_open = datetime(2026, 9, 20, 22, 0, tzinfo=timezone.utc).timestamp()   # 18:00 NY
    stock_open = datetime(2026, 9, 21, 13, 30, tzinfo=timezone.utc).timestamp()
    row = [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    fut = _to_bars("X", "1D", [[sunday_open] + row[1:]], trading_dates=True)
    stk = _to_bars("Y", "1D", [[stock_open] + row[1:]], trading_dates=True)
    raw = _to_bars("X", "1D", [[sunday_open] + row[1:]])
    assert fut.dates == ["2026-09-21"] and stk.dates == ["2026-09-21"]
    assert raw.dates == ["2026-09-20"]                                   # unchanged by default


def test_daily_bars_get_calendar_features():
    dates = ["2026-09-18", "2026-09-21", "2026-09-22"]
    n = len(dates)
    out = session_features(dates, np.ones(n), np.ones(n), np.ones(n), np.ones(n))
    assert list(out["day_of_week"]) == [4.0, 0.0, 1.0]
    assert list(out["day_of_month"]) == [18.0, 21.0, 22.0]
    assert np.isnan(out["session_vwap"]).all()


# ------------------------------------------------------------------ holdout by date

def _cfg(tmp_path, **over):
    base = dict(symbols=["AAA"], start="2015-01-01", end="2025-12-31", offline=True,
                population=12, generations=2, elites=3, survivor_reports=3,
                breeder="mutation", seed=5, verbose=False, workers=1, validate_top=3,
                db_path=str(tmp_path / "run.sqlite"), test_start="2019-06-01",
                leverage=2.0)
    base.update(over)
    return EvolutionConfig(**base)


def test_date_cut_finds_the_first_bar_on_or_after():
    universe = load_universe(["AAA"], "2015-01-01", "2025-12-31", offline=True)
    cut = date_cut(universe, "2019-06-01")
    assert universe.calendar[cut] >= "2019-06-01" > universe.calendar[cut - 1]
    assert date_cut(universe, "2099-01-01") == len(universe)


def test_evolution_holds_out_from_a_date_with_warm_indicators(tmp_path):
    evo = Evolution(_cfg(tmp_path))
    evo.run()
    assert "held-out 2019-06" in evo.window_label and "leverage 2x" in evo.window_label
    assert evo.ctx.test_start_bar is not None
    assert evo.ctx.train.calendar[-1] < "2019-06-01"


def test_evaluate_reports_the_date_held_out_window(tmp_path):
    cfg = _cfg(tmp_path)
    reports = evaluate([Genome.from_dict(ALWAYS)], cfg)
    labels = [w.label for w in reports[0].windows]
    assert labels == ["train", "held-out"]
    held = reports[0].windows[1]
    assert held.start >= "2019-06-01"
    assert reports[0].windows[0].end < "2019-06-01"
    # the held-out window trades from its first bar: no fifty-bar warm-up hole
    assert held.metrics.exposure > 1.5


# ------------------------------------------------------------------ style size and injection

def test_a_fixed_size_style_trades_every_agent_at_full_size(tmp_path):
    evo = Evolution(_cfg(tmp_path, style="nq_2x", population=24, elites=4))
    evo.run()
    for g in evo.population:
        assert all(r.weight == 1.0 for r in g.entry_rules)
        assert g.risk.max_position_pct == 1.0


def test_inject_puts_hand_bred_genomes_into_the_next_generation(tmp_path, capsys):
    cfg = _cfg(tmp_path)
    evo = Evolution(cfg)
    evo.run()
    run_id = evo.run_id
    evo.store.close()
    child = dict(ALWAYS, name="Hand Bred", rationale="because the leaders all held too long")
    path = tmp_path / "children.json"
    path.write_text(json.dumps({"genomes": [child]}))
    assert main(["inject", run_id, str(path), "--db", cfg.db_path,
                 "--lesson", "trend agents need a volatility exit"]) == 0
    store = Store(cfg.db_path)
    cp = store.latest_checkpoint(run_id)
    names = [g.name for g in cp["population"]]
    assert len(names) == cfg.population and names[-1] == "Hand Bred"
    injected = cp["population"][-1]
    assert injected.origin == "llm" and injected.generation == cp["generation"] + 1
    assert "trend agents need a volatility exit" in cp["lessons"]
    resumed = Evolution(_cfg(tmp_path, run_id=run_id), store=store)
    resumed.resume(run_id)
    assert any(g.name == "Hand Bred" for g in resumed.population)
    resumed.run(1)
    scored = store.conn.execute(
        "SELECT COUNT(*) FROM genomes WHERE run_id=? AND name='Hand Bred' AND origin='llm'",
        (run_id,)).fetchone()[0]
    assert scored == 1                                   # it was evaluated in its generation


# ------------------------------------------------------------------ signals in contracts

def test_signals_show_notional_and_micro_contracts():
    sig = Signal("S", "NQ1!", "2026-09-22", "close > 0", 1.0, {}, notional=2.0, price=31_000.0)
    text = format_signals("2026-09-22", [sig], [], [Genome.from_dict(dict(ALWAYS, name="S"))],
                          ["NQ1!"], account=25_000.0)
    assert "2.00x equity in notional" in text
    assert "0.81 MNQ" in text and "0.08 NQ" in text     # $50,000 / (31,000 x $2)
    assert contracts_for("QQQ", 50_000.0, 500.0) == ""


def test_a_seed_file_makes_an_island_of_one_family(tmp_path):
    seeds = [dict(ALWAYS, name="Island Seed A"),
             {"name": "Island Seed B", "entry_rules": [{"when": "ret1 < -0.01", "weight": 1.0}],
              "exit_rules": [{"when": "bars_held >= 2"}], "risk": {"max_position_pct": 1.0}}]
    path = tmp_path / "seeds.json"
    path.write_text(json.dumps({"genomes": seeds}))
    evo = Evolution(_cfg(tmp_path, seed_file=str(path), population=10, generations=1))
    evo.start()
    names = [g.name for g in evo.population]
    assert names[:2] == ["Island Seed A", "Island Seed B"]
    assert len(names) == 10
    assert sum(1 for g in evo.population if g.name.startswith("Random")) <= 2


# ------------------------------------------------------------------ resting stops

def _one_bar_universe(rows):
    """rows: (date, open, high, low, close)."""
    from evotrader.data import Universe
    dates = [r[0] for r in rows]
    cols = [np.asarray([r[k] for r in rows], dtype=float) for k in (1, 2, 3, 4)]
    bars = Bars("X", dates, cols[0], cols[1], cols[2], cols[3], np.full(len(rows), 1e6))
    return Universe({"X": bars}, dates)


def _stop_genome(stop):
    return compile_genome(Genome.from_dict({
        "name": "Stop Test", "entry_rules": [{"when": "close > 0 and in_position == 0", "weight": 1.0}],
        "exit_rules": [{"when": "bars_held >= 50"}],
        "risk": {"max_position_pct": 1.0, "stop_loss_pct": stop, "cooldown_bars": 99}}))


def test_a_resting_stop_fills_at_the_stop_inside_the_bar():
    # decisions start on bar 1, so the entry fills at bar 2's open (100)
    days = [str(np.datetime64("2026-01-01") + np.timedelta64(i, "D")) for i in range(7)]
    rows = [(days[0], 100, 101, 99, 100), (days[1], 100, 101, 99.5, 100),
            (days[2], 100, 100.5, 98.9, 99.2), (days[3], 99, 99.5, 98, 99),
            (days[4], 99, 100, 98, 99), (days[5], 99, 100, 98, 99), (days[6], 99, 100, 98, 99)]
    u = _one_bar_universe(rows)
    f = build_features(u)
    r = run_backtest(_stop_genome(0.01), u, f, starting_cash=10_000, commission_bps=0.0,
                     slippage_bps=0.0, start_bar=1, intrabar_stops=True)
    t = r.journal.trades[0]
    assert t.entry_date == days[2] and t.exit_date == days[2]      # stopped on the entry bar
    assert t.exit_price == pytest.approx(99.0)                     # 1% under the 100 fill
    assert "intrabar" in t.exit_reason
    closed = run_backtest(_stop_genome(0.01), u, f, starting_cash=10_000, commission_bps=0.0,
                          slippage_bps=0.0, start_bar=1)
    assert closed.journal.trades[0].exit_date != days[2]          # close-checked: 99.2 is above the stop


def test_a_gap_through_a_resting_stop_fills_at_the_open():
    days = [str(np.datetime64("2026-01-01") + np.timedelta64(i, "D")) for i in range(6)]
    rows = [(days[0], 100, 101, 99, 100), (days[1], 100, 101, 99.5, 100),
            (days[2], 100, 101, 99.5, 100.5), (days[3], 97, 98, 96, 97.5),
            (days[4], 97, 98, 96, 97), (days[5], 97, 98, 96, 97)]
    u = _one_bar_universe(rows)
    f = build_features(u)
    r = run_backtest(_stop_genome(0.01), u, f, starting_cash=10_000, commission_bps=0.0,
                     slippage_bps=0.0, start_bar=1, intrabar_stops=True)
    t = r.journal.trades[0]
    assert t.entry_date == days[2]
    assert t.exit_date == days[3] and t.exit_price == pytest.approx(97.0)   # the gap, not the stop
