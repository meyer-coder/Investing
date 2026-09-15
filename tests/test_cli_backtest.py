import pytest

from evotrader import backtest_api, cli


OFFLINE = ["--symbols", "AAA,BBB,CCC", "--start", "2015-01-01",
           "--end", "2030-01-01", "--offline"]


@pytest.fixture(autouse=True)
def _clean():
    backtest_api.clear_cache()
    yield
    backtest_api.clear_cache()


def test_strategies_lists_the_library(capsys):
    assert cli.main(["strategies"]) == 0
    out = capsys.readouterr().out
    assert "mean-reversion" in out and "rsi_pullback" in out


def test_strategies_filters_by_family(capsys):
    assert cli.main(["strategies", "--family", "trend"]) == 0
    out = capsys.readouterr().out
    assert "triple_ma" in out and "rsi_pullback" not in out


def test_strategies_reports_an_unknown_family(capsys):
    assert cli.main(["strategies", "--family", "nope"]) == 1
    assert "try" in capsys.readouterr().err


def test_simulate_reports_return_against_buy_and_hold(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", *OFFLINE]) == 0
    out = capsys.readouterr().out
    assert "buy-and-hold" in out and "sharpe" in out and "costs paid" in out


def test_simulate_accepts_ad_hoc_rules(capsys):
    code = cli.main(["simulate", "--entry", "rsi14 < 25", "--exit", "rsi14 > 70",
                     *OFFLINE])
    assert code == 0
    assert "custom" in capsys.readouterr().out


def test_simulate_applies_a_parameter_override(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", "--param", "oversold=20",
                     *OFFLINE]) == 0
    assert "oversold=20" in capsys.readouterr().out


def test_simulate_rejects_a_malformed_parameter(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", "--param", "oversold",
                     *OFFLINE]) == 1
    assert "key=value" in capsys.readouterr().err


def test_simulate_reports_an_unknown_strategy(capsys):
    assert cli.main(["simulate", "--strategy", "nope", *OFFLINE]) == 1
    assert "simulate failed" in capsys.readouterr().err


def test_simulate_reports_an_invalid_rule(capsys):
    assert cli.main(["simulate", "--entry", "close > pixie_dust",
                     "--exit", "rsi14 > 70", *OFFLINE]) == 1
    assert "pixie_dust" in capsys.readouterr().err


def test_simulate_walk_forward_prints_folds_and_the_caveat(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", "--walk-forward", *OFFLINE]) == 0
    out = capsys.readouterr().out
    assert "fold1" in out and "not overfitting" in out


def test_compare_ranks_and_prints_the_benchmark(capsys):
    assert cli.main(["compare", "--names", "rsi,macd,squeeze", "--workers", "1",
                     *OFFLINE]) == 0
    out = capsys.readouterr().out
    assert "buy-and-hold over the same window" in out
    assert "fitness" in out


def test_compare_honours_a_family(capsys):
    assert cli.main(["compare", "--family", "trend", "--workers", "1", *OFFLINE]) == 0
    assert "triple_ma" in capsys.readouterr().out


def test_compare_reports_an_unknown_strategy(capsys):
    assert cli.main(["compare", "--names", "not_a_strategy", *OFFLINE]) == 1
    assert "compare failed" in capsys.readouterr().err


def test_simulate_rejects_an_unsupported_interval(capsys):
    with pytest.raises(SystemExit):
        cli.main(["simulate", "--strategy", "rsi", "--interval", "3s", *OFFLINE])


def test_report_survives_a_metric_that_is_not_finite(capsys):
    """A strategy with no losing trades has an infinite profit factor; the
    report must print it, not crash on it."""
    cli._print_result({
        "strategy": "s", "symbols": ["AAA"], "interval": "1d",
        "period": {"start": "2015-01-01", "end": "2020-01-01", "bars": 10, "years": 5},
        "metrics": {"total_return": 0.1, "benchmark_return": 0.2,
                    "excess_return": -0.1, "cagr": 0.02, "sharpe": None,
                    "sortino": None, "max_drawdown": -0.05, "calmar": None,
                    "trades": 3, "win_rate": 1.0, "profit_factor": None,
                    "turnover": None, "exposure": 0.5},
        "costs_paid": 10.0, "final_equity": 110.0, "fitness": None,
    })
    out = capsys.readouterr().out
    assert "n/a" in out and "profit factor" in out


def test_simulate_grid_reports_held_out_results(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", "--grid", "oversold=25,30,35",
                     "--workers", "1", *OFFLINE]) == 0
    out = capsys.readouterr().out
    assert "3 combinations" in out and "held out" in out
    assert "cost of the search" in out


def test_simulate_grid_needs_a_strategy(capsys):
    assert cli.main(["simulate", "--entry", "rsi14 < 25", "--exit", "rsi14 > 70",
                     "--grid", "oversold=25,30", *OFFLINE]) == 1
    assert "--grid needs --strategy" in capsys.readouterr().err


def test_simulate_rejects_a_malformed_grid(capsys):
    assert cli.main(["simulate", "--strategy", "rsi", "--grid", "oversold",
                     *OFFLINE]) == 1
    assert "key=v1,v2" in capsys.readouterr().err


def test_grid_parses_mixed_numeric_types():
    assert cli._parse_grid(["a=1,2", "b=0.5,1.5"]) == {"a": [1, 2], "b": [0.5, 1.5]}


def test_grid_rejects_an_empty_value_list():
    with pytest.raises(ValueError):
        cli._parse_grid(["a="])
