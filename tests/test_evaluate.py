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
