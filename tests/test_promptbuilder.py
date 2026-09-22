"""Tests for the strategy prompt builder.

The important ones are the refusals: a spec that cannot produce an honest
prompt must fail loudly rather than emit a plausible-looking brief.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from promptbuilder.feasibility import assess, statistics_for
from promptbuilder.grid import build_grid
from promptbuilder.render import render
from promptbuilder.spec import SpecError, parse_spec

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "tools",
                       "promptbuilder", "specs", "example-nq-5m.yaml")


def _minimal(**over):
    spec = {
        "strategy": {
            "name": "T", "instrument": "NQ", "timeframe": "5m", "thesis": "th",
            "entry_rules": ["e"], "exit_rules": ["x"], "risk": {"stop": "1R"},
        },
        "data": {"sources": ["yahoo"], "history_days": 1000,
                 "base_signals_per_day": 2.0},
        "grid": {"axes": [{"name": "a", "values": ["1", "2"]},
                          {"name": "b", "values": ["3", "4"]}]},
    }
    spec.update(over)
    return spec


# --------------------------------------------------------------- refusals
def test_missing_strategy_block_is_rejected():
    with pytest.raises(SpecError, match="no 'strategy' block"):
        parse_spec({"data": {"sources": ["y"], "history_days": 1,
                             "base_signals_per_day": 1},
                    "grid": {"axes": []}})


@pytest.mark.parametrize("field", ["name", "instrument", "timeframe", "thesis",
                                   "entry_rules", "exit_rules", "risk"])
def test_every_required_strategy_field_is_enforced(field):
    raw = _minimal()
    del raw["strategy"][field]
    with pytest.raises(SpecError, match="missing required fields"):
        parse_spec(raw)


def test_empty_rule_list_is_rejected():
    raw = _minimal()
    raw["strategy"]["entry_rules"] = []
    with pytest.raises(SpecError):
        parse_spec(raw)


def test_history_and_signal_rate_must_be_positive():
    for key in ("history_days", "base_signals_per_day"):
        raw = _minimal()
        raw["data"][key] = 0
        with pytest.raises(SpecError):
            parse_spec(raw)


def test_single_axis_is_not_a_grid():
    raw = _minimal()
    raw["grid"]["axes"] = [{"name": "a", "values": ["1", "2"]}]
    with pytest.raises(SpecError, match="at least 2 axes"):
        parse_spec(raw)


def test_axis_needs_more_than_one_value():
    raw = _minimal()
    raw["grid"]["axes"][0]["values"] = ["only"]
    with pytest.raises(SpecError, match="at least 2 values"):
        parse_spec(raw)


def test_pass_rate_out_of_range_is_rejected():
    raw = _minimal()
    raw["grid"]["axes"][0]["values"] = [{"label": "x", "pass_rate": 1.4}, "y"]
    with pytest.raises(SpecError, match="pass_rate"):
        parse_spec(raw)


# ------------------------------------------------------------------ grid
def test_grid_is_the_full_product_when_inside_the_band():
    spec = parse_spec(_minimal(grid={"target_min": 2, "target_max": 10, "axes": [
        {"name": "a", "values": ["1", "2"]}, {"name": "b", "values": ["3", "4"]}]}))
    grid = build_grid(spec)
    assert grid.full_product == 4
    assert len(grid.variations) == 4
    assert not grid.reduced


def test_grid_is_subsampled_when_over_the_ceiling_and_is_reproducible():
    axes = [{"name": f"ax{i}", "values": list("abcde")} for i in range(4)]  # 625
    spec = parse_spec(_minimal(grid={"target_min": 100, "target_max": 200,
                                     "seed": 3, "axes": axes}))
    a, b = build_grid(spec), build_grid(spec)
    assert a.full_product == 625
    assert len(a.variations) == 200 and a.reduced
    assert [v.choices for v in a.variations] == [v.choices for v in b.variations]


# ----------------------------------------------------------- feasibility
def test_selectivity_drives_required_history():
    raw = _minimal()
    raw["data"]["base_signals_per_day"] = 1.0
    raw["data"]["history_days"] = 100
    raw["grid"]["axes"] = [
        {"name": "f", "values": [{"label": "none", "pass_rate": 1.0},
                                 {"label": "tight", "pass_rate": 0.1}]},
        {"name": "g", "values": ["p", "q"]}]
    raw["guardrails"] = {"min_trades": 50}
    spec = parse_spec(raw)
    grid = build_grid(spec)
    loose = [v for v in grid.variations if v.choices["f"] == "none"]
    tight = [v for v in grid.variations if v.choices["f"] == "tight"]
    assert all(v.feasible for v in loose)          # 1/day x 100d = 100 >= 50
    assert not any(v.feasible for v in tight)      # 0.1/day x 100d = 10 < 50
    assert tight[0].required_days == 500
    rep = assess(spec, grid)
    assert (rep.n_feasible, rep.n_infeasible) == (2, 2)


def test_statistics_grow_with_the_number_of_tests():
    small, large = statistics_for(10), statistics_for(800)
    assert large.expected_max_t > small.expected_max_t
    assert large.bonferroni_alpha < small.bonferroni_alpha
    assert 3.5 < large.expected_max_t < 3.8      # sqrt(2 ln 800)
    assert large.bonferroni_z > 3.8


# ---------------------------------------------------------------- render
def test_rendered_prompt_has_no_unfilled_slots_and_carries_the_guardrails():
    spec = parse_spec(_minimal())
    grid = build_grid(spec)
    text = render(spec, grid, assess(spec, grid), spec_path="s.yaml",
                  manifest_path="m.json")
    assert "{{" not in text
    assert "at least 400 trades" in text
    assert "insufficient sample" in text
    assert "Rank on the\n   out-of-sample numbers" in text


def test_session_override_is_explicit_when_the_spec_restricts_hours():
    raw = _minimal()
    raw["strategy"]["session_in_spec"] = "09:30-11:00"
    raw["strategy"]["override_session"] = True
    spec = parse_spec(raw)
    grid = build_grid(spec)
    text = render(spec, grid, assess(spec, grid), spec_path="s", manifest_path="m")
    assert "Session override" in text and "Ignore that restriction" in text


# --------------------------------------------------------------- recency
def test_lookback_years_drives_history_days():
    spec = parse_spec(_minimal(window={"lookback_years": 3}, data={
        "sources": ["y"], "base_signals_per_day": 2.0}))
    assert spec.history_days == 756
    assert spec.window.lookback_days == 756


def test_recent_floor_defaults_proportionally_and_is_never_the_full_floor():
    spec = parse_spec(_minimal(
        window={"lookback_years": 3, "emphasis_months": 6},
        data={"sources": ["y"], "base_signals_per_day": 2.0},
        guardrails={"min_trades": 400}))
    assert spec.window.emphasis_days == 126
    assert spec.window.min_trades_recent == 67        # 400 * 126/756
    assert spec.window.min_trades_recent < spec.min_trades


def test_recent_floor_cannot_exceed_the_full_window_floor():
    with pytest.raises(SpecError, match="cannot exceed"):
        parse_spec(_minimal(
            window={"lookback_years": 3, "emphasis_months": 6, "min_trades_recent": 500},
            data={"sources": ["y"], "base_signals_per_day": 2.0},
            guardrails={"min_trades": 400}))


def test_emphasis_window_must_be_shorter_than_the_lookback():
    with pytest.raises(SpecError, match="must be\\s+shorter"):
        parse_spec(_minimal(
            window={"lookback_years": 1, "emphasis_months": 18},
            data={"sources": ["y"], "base_signals_per_day": 2.0}))


def test_recent_weight_of_one_is_rejected():
    with pytest.raises(SpecError, match="recent_weight"):
        parse_spec(_minimal(
            window={"lookback_years": 3, "emphasis_months": 6, "recent_weight": 1.0},
            data={"sources": ["y"], "base_signals_per_day": 2.0}))


def test_unknown_recency_method_is_rejected():
    with pytest.raises(SpecError, match="window.method"):
        parse_spec(_minimal(
            window={"lookback_years": 3, "emphasis_months": 6, "method": "vibes"},
            data={"sources": ["y"], "base_signals_per_day": 2.0}))


def test_recent_window_feasibility_is_tracked_separately():
    spec = parse_spec(_minimal(
        window={"lookback_years": 3, "emphasis_months": 6},
        data={"sources": ["y"], "base_signals_per_day": 1.0},
        guardrails={"min_trades": 400},
        grid={"axes": [
            {"name": "f", "values": [{"label": "none", "pass_rate": 1.0},
                                     {"label": "tight", "pass_rate": 0.2}]},
            {"name": "g", "values": ["p", "q"]}]}))
    grid = build_grid(spec)
    rep = assess(spec, grid)
    loose = [v for v in grid.variations if v.choices["f"] == "none"]
    tight = [v for v in grid.variations if v.choices["f"] == "tight"]
    assert all(v.feasible_recent for v in loose)      # 1/day x 126d = 126 >= 67
    assert not any(v.feasible_recent for v in tight)  # 0.2/day x 126d = 25 < 67
    assert rep.n_feasible_both == 2


@pytest.mark.parametrize("method,marker", [
    ("weighted", "60% x recent"),
    ("half_life", "Exponential decay"),
    ("gate", "disqualify any variation")])
def test_each_recency_method_renders_its_own_instruction(method, marker):
    spec = parse_spec(_minimal(
        window={"lookback_years": 3, "emphasis_months": 6, "recent_weight": 0.6,
                "method": method},
        data={"sources": ["y"], "base_signals_per_day": 2.0}))
    grid = build_grid(spec)
    text = render(spec, grid, assess(spec, grid), spec_path="s", manifest_path="m")
    assert marker in text
    assert "walk-forward" in text          # the selection-leak warning is always present


def test_no_emphasis_means_no_recency_section():
    spec = parse_spec(_minimal(window={"lookback_years": 3},
                               data={"sources": ["y"], "base_signals_per_day": 2.0}))
    grid = build_grid(spec)
    text = render(spec, grid, assess(spec, grid), spec_path="s", manifest_path="m")
    assert "No recency emphasis" in text


# ------------------------------------------------------------- end to end
def test_example_spec_builds_and_flags_infeasible_variations(tmp_path):
    from promptbuilder.cli import main
    out = tmp_path / "out"
    assert main([EXAMPLE, "-o", str(out), "--quiet"]) == 0
    manifest = json.loads((out / "example-nq-5m.variations.json").read_text())
    assert manifest["grid"]["emitted"] == 576
    assert manifest["window"]["lookback_days"] == 756       # 3 years
    assert manifest["window"]["emphasis_days"] == 126       # 6 months
    assert manifest["window"]["min_trades_recent"] == 67    # 400 scaled by 126/756
    assert manifest["feasibility"]["feasible"] == 304
    assert manifest["feasibility"]["infeasible"] == 272
    prompt = (out / "example-nq-5m.prompt.md").read_text()
    assert "{{" not in prompt
    assert "576" in prompt


def test_cli_rejects_a_spec_with_no_strategy(tmp_path, capsys):
    from promptbuilder.cli import main
    bad = tmp_path / "bad.yaml"
    bad.write_text("data:\n  sources: [y]\n  history_days: 5\n"
                   "  base_signals_per_day: 1\ngrid:\n  axes: []\n")
    assert main([str(bad), "-o", str(tmp_path / "o")]) == 2
    assert "no 'strategy' block" in capsys.readouterr().err
