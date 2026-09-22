"""The evaluate path: hand-written genomes scored over a config's windows."""
import json
import os

from evotrader.cli import main
from evotrader.config import EvolutionConfig
from evotrader.evaluate import evaluate, format_markdown, format_text, load_genomes


def _write(tmp_path, genomes):
    path = tmp_path / "strats.json"
    path.write_text(json.dumps({"genomes": genomes}))
    return str(path)


def _cfg(**over):
    base = dict(symbols=["AAA", "BBB"], start="2015-01-01", end="2025-12-31", offline=True,
                test_frac=0.25, verbose=False)
    base.update(over)
    return EvolutionConfig(**base)


GOOD = {"name": "Fast Dip", "thesis": "buy a red day, sell in two",
        "entry_rules": [{"when": "ret1 < -0.01", "weight": 0.3}],
        "exit_rules": ["bars_held >= 2"],
        "risk": {"max_position_pct": 0.3, "max_positions": 2, "stop_loss_pct": 0.05,
                 "max_hold_bars": 3}}


def test_load_rejects_bad_rules_before_any_backtest(tmp_path):
    path = _write(tmp_path, [GOOD, {**GOOD, "name": "bad",
                                    "entry_rules": [{"when": "alpha > 1", "weight": 0.2}]}])
    try:
        load_genomes(path)
    except ValueError as exc:
        assert "alpha" in str(exc)
    else:
        raise AssertionError("expected the unknown feature to be rejected")


def test_evaluate_scores_train_heldout_and_years(tmp_path):
    genomes = load_genomes(_write(tmp_path, [GOOD]))
    reports = evaluate(genomes, _cfg(), by_year=True)
    assert len(reports) == 1
    r = reports[0]
    assert [w.label for w in r.windows] == ["train", "held-out"]
    assert all(w.metrics.trades > 0 for w in r.windows)
    years = [y.year for y in r.years]
    assert years and years[0] == "2015" and years == sorted(years) and len(years) >= 3
    assert all(y.trades >= 0 for y in r.years)
    assert r.symbols and sum(s.trades for s in r.symbols) == sum(y.trades for y in r.years)
    assert r.worst and r.best and r.worst[0].ret <= r.best[0].ret
    text = format_text(reports)
    assert "Fast Dip" in text and "held-out" in text and "by year" in text
    md = format_markdown(reports, title="T", cfg=_cfg())
    assert md.startswith("# T") and "| held-out |" in md and "| 2016 |" in md
    assert "| AAA |" in md or "| BBB |" in md
    assert "Worst trades" in md


def test_test_frac_zero_scores_one_full_window(tmp_path):
    genomes = load_genomes(_write(tmp_path, [GOOD]))
    reports = evaluate(genomes, _cfg(test_frac=0.0))
    assert [w.label for w in reports[0].windows] == ["full"]


def test_cli_evaluate_writes_markdown_and_signals_unprofitable(tmp_path, capsys):
    never = {**GOOD, "name": "Never", "entry_rules": [{"when": "rsi14 < 1", "weight": 0.2}]}
    path = _write(tmp_path, [GOOD, never])
    out_md = str(tmp_path / "report.md")
    code = main(["evaluate", path, "--offline", "--symbols", "AAA,BBB", "--start", "2015-01-01",
                 "--end", "2025-12-31", "--by-year", "--slippage", "20", "--markdown", out_md])
    printed = capsys.readouterr().out
    assert code == 2                       # "Never" trades nothing, so it is not profitable
    assert "Never" in printed and "not profitable" in printed
    assert os.path.exists(out_md) and "## Fast Dip" in open(out_md).read()


def test_signals_fire_on_the_latest_bar(tmp_path, capsys):
    from evotrader.evaluate import latest_signals
    always = {**GOOD, "name": "Always", "entry_rules": [{"when": "close > 0", "weight": 0.2}]}
    never = {**GOOD, "name": "Never", "entry_rules": [{"when": "rsi14 < 1", "weight": 0.2}]}
    slow = {**GOOD, "name": "Slow", "entry_rules": [{"when": "close > sma200 * 0", "weight": 0.2}]}
    genomes = load_genomes(_write(tmp_path, [always, never, slow]))
    date, signals, skipped = latest_signals(genomes, _cfg(start="2019-06-01", end="2020-09-29",
                                                          test_frac=0.0))
    assert date.startswith("2020")
    assert {s.symbol for s in signals if s.genome == "Always"} == {"AAA", "BBB"}
    assert {s.symbol for s in signals if s.genome == "Slow"} == {"AAA", "BBB"}
    assert not [s for s in signals if s.genome == "Never"]
    assert skipped == []
    assert all(s.date == date and s.weight == 0.2 for s in signals)
    capped = {**GOOD, "name": "Capped", "entry_rules": [{"when": "close > 0", "weight": 0.9}],
              "risk": {**GOOD["risk"], "max_position_pct": 0.15}}
    _, capped_signals, _ = latest_signals(load_genomes(_write(tmp_path, [capped])), _cfg())
    assert capped_signals and all(abs(s.weight - 0.15) < 1e-9 for s in capped_signals)
    assert all("close" in s.context for s in signals if s.genome == "Always")
    path = _write(tmp_path, [always, never])
    assert main(["signals", path, "--offline", "--symbols", "AAA,BBB", "--end", "2020-06-30"]) == 0
    out = capsys.readouterr().out
    assert "latest bar 2020-06" in out and "BUY AAA" in out and "Never: no signal" in out


def test_since_rows_report_the_trailing_window(tmp_path):
    genomes = load_genomes(_write(tmp_path, [GOOD]))
    reports = evaluate(genomes, _cfg(test_frac=0.0), since=["2019-01-01", "2020-06-01"])
    r = reports[0]
    assert [p.label for p in r.periods] == ["since 2019-01-01", "since 2020-06-01"]
    a, b = r.periods
    assert a.start < "2019-01-01" <= a.end and b.metrics.trades <= a.metrics.trades
    assert a.metrics.worst_day <= 0.0
    assert r.years == []                       # since does not imply the year table
    text = format_text(reports)
    assert "since 2020-06-01" in text and "worst day" in text
    md = format_markdown(reports, title="T")
    assert "| since 2019-01-01 |" in md and "| worst day |" in md


def test_recent_mode_judges_and_ranks_on_the_trailing_window(tmp_path, capsys):
    from evotrader.evaluate import parse_recent
    assert [parse_recent(x) for x in ("6m", "3m", "1y", "2w", "90")] == [126, 63, 252, 10, 90]
    never = {**GOOD, "name": "Never", "entry_rules": [{"when": "rsi14 < 1", "weight": 0.2}]}
    genomes = load_genomes(_write(tmp_path, [never, GOOD]))
    reports = evaluate(genomes, _cfg(test_frac=0.0), recent_bars=126)
    assert [r.genome.name for r in reports] == ["Fast Dip", "Never"]      # ranked by the window
    good, idle = reports
    assert good.recent is not None and good.recent.label == "last 126 bars"
    assert good.recent.metrics.trades > 0
    assert idle.recent is not None and idle.recent.metrics.trades == 0 and not idle.profitable
    assert idle.verdict.startswith("too few trades over the last 126 bars")
    assert idle.windows and idle.windows[0].verdict == "too few trades (0)"
    text = format_text(reports)
    assert "over the last 126 bars" in text and "<-- too few trades (0)" in text
    md = format_markdown(reports, title="T")
    assert "| last 126 bars |" in md
    code = main(["evaluate", _write(tmp_path, [GOOD]), "--offline", "--symbols", "AAA,BBB",
                 "--start", "2015-01-01", "--end", "2025-12-31", "--test-frac", "0", "--recent", "6m"])
    assert code in (0, 2)
    assert "strategies profitable over the last 126 bars" in capsys.readouterr().out


def test_by_month_buckets_by_calendar_month(tmp_path):
    genomes = load_genomes(_write(tmp_path, [GOOD]))
    reports = evaluate(genomes, _cfg(test_frac=0.0), by_month=True)
    months = [y.year for y in reports[0].years]
    assert months[0] == "2015-01" and all(len(m) == 7 for m in months) and months == sorted(months)
    yearly = evaluate(genomes, _cfg(test_frac=0.0), by_year=True)[0].years
    # the monthly returns compound to the yearly return
    import math
    for y in yearly:
        comp = math.prod(1 + m.ret for m in reports[0].years if m.year.startswith(y.year)) - 1
        assert abs(comp - y.ret) < 1e-9, y.year
    assert "by month" in format_text(reports)
