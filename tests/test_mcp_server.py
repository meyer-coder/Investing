import json

import pytest

from evotrader import backtest_api, screener
from evotrader.mcp_server import (backtest, compare_strategies, data_cache,
                                  describe_strategy, list_columns, list_features,
                                  list_presets, list_strategies, optimize_strategy,
                                  quote, save_universe, screen_symbols,
                                  validate_strategy, walk_forward_test)

OFFLINE = dict(symbols=["AAA", "BBB", "CCC"], start="2015-01-01",
               end="2030-01-01", offline=True)


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    backtest_api.clear_cache()
    monkeypatch.setattr(screener, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(screener, "UNIVERSE_DIR", str(tmp_path / "universes"))
    yield
    backtest_api.clear_cache()


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _stub_scanner(monkeypatch, rows, total=None):
    body = json.dumps({"totalCount": total if total is not None else len(rows),
                       "data": rows})
    monkeypatch.setattr(screener.urllib.request, "urlopen",
                        lambda req, timeout=None: _FakeResponse(body))


# ─── backtesting tools ────────────────────────────────────────────────────────

def test_backtest_returns_metrics_and_a_benchmark():
    out = backtest(strategy="rsi", **OFFLINE)
    assert "error" not in out
    assert out["metrics"]["benchmark_return"] is not None
    assert out["period"]["bars"] > 0


def test_backtest_accepts_raw_rules():
    out = backtest(entry_rules=["rsi14 < 25"], exit_rules=["rsi14 > 70"], **OFFLINE)
    assert "error" not in out
    assert out["metrics"]["trades"] >= 0


def test_backtest_reports_errors_instead_of_raising():
    """An MCP tool that raises gives the caller nothing to act on."""
    assert "error" in backtest(strategy="no_such_thing", **OFFLINE)
    assert "error" in backtest(entry_rules=["close > not_a_feature"],
                               exit_rules=["rsi14 > 70"], **OFFLINE)
    assert "error" in backtest(**OFFLINE)          # neither strategy nor rules
    assert "error" in backtest(strategy="rsi", params={"bogus": 1}, **OFFLINE)


def test_backtest_rejects_an_unknown_interval():
    out = backtest(strategy="rsi", **{**OFFLINE, "interval": "3s"})
    assert "error" in out


def test_backtest_can_include_trades():
    out = backtest(strategy="rsi", include_trades=True, **OFFLINE)
    assert "trade_count" in out and isinstance(out["trades"], list)


def test_compare_ranks_and_reports_the_benchmark_once():
    out = compare_strategies(names=["rsi", "macd", "squeeze"], limit=3,
                             workers=1, **OFFLINE)
    assert out["tested"] == 3
    fitness = [r["fitness"] for r in out["results"]]
    assert fitness == sorted(fitness, reverse=True)
    assert out["benchmark_return"] is not None


def test_compare_can_select_a_family():
    out = compare_strategies(family="trend", workers=1, limit=20, **OFFLINE)
    assert out["tested"] >= 4


def test_compare_excludes_archetypes_by_default():
    out = compare_strategies(workers=1, limit=50, **OFFLINE)
    assert not any(r["strategy"].startswith("archetype:") for r in out["results"])


def test_compare_reports_an_empty_selection():
    assert "error" in compare_strategies(family="nonexistent", **OFFLINE)


def test_walk_forward_labels_what_it_measures():
    out = walk_forward_test(strategy="rsi", folds=3, **OFFLINE)
    assert out["folds"]
    assert "not overfitting" in out["note"]


def test_optimize_reports_held_out_degradation():
    out = optimize_strategy(strategy="rsi", grid={"oversold": [25, 30, 35]},
                            top=2, workers=1, **OFFLINE)
    assert out["combinations_tested"] == 3
    assert out["degradation"]["verdict"]
    assert out["train_window"] != out["test_window"]


def test_optimize_reports_a_bad_grid_as_an_error():
    assert "error" in optimize_strategy(strategy="rsi", grid={}, **OFFLINE)
    assert "error" in optimize_strategy(strategy="rsi",
                                        grid={"nope": [1]}, **OFFLINE)


# ─── discovery tools ──────────────────────────────────────────────────────────

def test_list_strategies_covers_every_family():
    out = list_strategies()
    assert out["count"] == len(out["strategies"])
    assert set(out["families"]) >= {"trend", "mean-reversion", "breakout"}


def test_describe_strategy_round_trips_a_name_from_the_listing():
    name = list_strategies(family="trend")["strategies"][0]["name"]
    assert describe_strategy(name)["entries"]


def test_describe_unknown_strategy_errors():
    assert "error" in describe_strategy("nope")


def test_list_features_documents_what_rules_may_reference():
    out = list_features()
    assert "rsi14" in out["market_features"]
    assert "bars_held" in out["portfolio_features"]
    assert "cross_above" in out["functions"]
    assert out["intervals"][0] == "1d"


def test_every_documented_example_validates():
    for rule in list_features()["examples"]:
        assert validate_strategy(entry_rules=[rule], exit_rules=["rsi14 > 70"])["valid"]


def test_validate_reports_the_offending_rule():
    out = validate_strategy(entry_rules=["close > moon_phase"], exit_rules=["rsi14 > 70"])
    assert out["valid"] is False
    assert "moon_phase" in out["error"]


def test_data_cache_reports_and_clears():
    backtest(strategy="rsi", **OFFLINE)
    assert data_cache()["entries"] == 1
    assert data_cache(clear=True)["entries"] == 0


# ─── screening tools ──────────────────────────────────────────────────────────

def test_screen_warns_when_the_universe_post_dates_the_backtest(monkeypatch):
    _stub_scanner(monkeypatch, [{"s": "NASDAQ:NVDA", "d": ["NVDA"]}], total=450)
    out = screen_symbols(filters=["mcap > 1e9"], limit=1, backtest_start="2015-01-01")
    assert out["symbols"] == ["NVDA"]
    assert "look-ahead bias" in out["bias_warning"]


def test_screen_omits_the_warning_without_a_backtest_window(monkeypatch):
    _stub_scanner(monkeypatch, [{"s": "NASDAQ:NVDA", "d": ["NVDA"]}])
    assert "bias_warning" not in screen_symbols(filters=["mcap > 1e9"], limit=1)


def test_screen_reports_a_bad_filter():
    assert "error" in screen_symbols(filters=["mcap is enormous"])


def test_quote_lists_symbols_it_could_not_find(monkeypatch):
    _stub_scanner(monkeypatch, [{"s": "AMEX:SPY", "d": ["SPY", 1.0]}])
    out = quote(symbols=["SPY", "NOPE"])
    assert out["missing"] == ["NOPE"]


def test_save_universe_writes_a_dated_snapshot(monkeypatch, tmp_path):
    _stub_scanner(monkeypatch, [{"s": "AMEX:SPY", "d": ["SPY"]}])
    out = save_universe(name="mine", filters=["mcap > 1e9"], limit=1)
    assert out["saved"].endswith(".json")
    assert "mine-" in out["saved"]


def test_presets_and_columns_are_listable():
    assert "liquid-large-cap" in list_presets()
    assert "mcap" in list_columns()["columns"]
