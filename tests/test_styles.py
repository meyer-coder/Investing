"""Trading styles: the mandate reaches the briefing, the archetypes lead
generation 0, and the fitness terms that make a style score behave."""
import os
import random

import pytest

from evotrader.breeder import HybridBreeder
from evotrader.config import EvolutionConfig
from evotrader.evolution import Evolution
from evotrader.fitness import FitnessConfig, Metrics, fitness_score
from evotrader.genome import is_valid
from evotrader.llm import Response, Usage
from evotrader.population import ARCHETYPES, seed_population
from evotrader.styles import STYLES, TradingStyle, get_style
from tests.test_breeder import FakeClaude, _elite, _payload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RecordingClaude:
    """Enough of the client for a full run: records prompts, returns a payload."""

    def __init__(self, payload):
        self.payload = payload
        self.prompts = []
        self.available = True
        self.unavailable_reason = ""
        self.usage = Usage()
        self.model = "fake"

    def budget_left(self):
        return float("inf")

    def complete(self, prompt, *, system="", schema=None, **kwargs):
        self.prompts.append(prompt)
        return Response(text="", data=self.payload, model="fake", cost_usd=0.01)


def test_registry_lookup():
    assert get_style("") is None
    style = get_style("leveraged_swing")
    assert isinstance(style, TradingStyle)
    assert "small wins" in style.mandate.lower()
    with pytest.raises(ValueError):
        get_style("day-trading-on-vibes")


def test_every_style_archetype_compiles_and_leads_generation_zero():
    for name, style in STYLES.items():
        library = list(style.archetypes) + list(ARCHETYPES)
        pop = seed_population(len(style.archetypes) + 2, random.Random(0), archetypes=library)
        assert all(is_valid(g) for g in pop), name
        assert [g.name for g in pop[:len(style.archetypes)]] == [a[0] for a in style.archetypes]
        assert all(g.origin == "seed" for g in pop)


def test_leveraged_swing_archetypes_hold_briefly_and_size_small():
    style = get_style("leveraged_swing")
    assert len(style.archetypes) >= 3
    for name, _, _, _, risk in style.archetypes:
        assert 0 < risk["max_hold_bars"] <= 10, name
        assert risk["max_position_pct"] <= 0.15, name
        assert risk["max_positions"] >= 5, name


def test_seed_population_without_a_library_is_unchanged():
    assert [g.name for g in seed_population(3, random.Random(0))] == [a[0] for a in ARCHETYPES[:3]]


def test_config_carries_the_style_and_rejects_unknown_ones():
    cfg = EvolutionConfig.from_dict({"style": "leveraged_swing", "population": 8, "elites": 2})
    assert cfg.style == "leveraged_swing"
    assert EvolutionConfig.from_dict(cfg.to_dict()).style == "leveraged_swing"
    cfg.validate()
    cfg.style = "nope"
    with pytest.raises(ValueError):
        cfg.validate()


def test_shipped_style_configs_load_and_validate():
    for name in ("leveraged_swing.json", "leveraged_swing_long.json"):
        cfg = EvolutionConfig.load(os.path.join(ROOT, "configs", name))
        cfg.validate()
        assert cfg.style == "leveraged_swing", name
        assert cfg.fitness.hold_limit_bars > 0 and cfg.fitness.win_rate_weight > 0, name
        assert cfg.fitness.turnover_limit >= 50, name
        assert cfg.fitness.excess_weight < 1.5, name


def test_mandate_reaches_the_breeding_prompt():
    claude = FakeClaude(_payload(3))
    breeder = HybridBreeder(claude, rng=random.Random(0), llm_share=1.0, verbose=False)
    style = get_style("leveraged_swing")
    breeder.breed([_elite()], 3, generation=2, parent_pool=[_elite()[0]], extra=style.mandate)
    prompt = claude.prompts[-1][0]
    assert "STYLE MANDATE" in prompt
    assert "3 new genomes" in prompt
    # and without a style nothing is appended
    breeder.breed([_elite()], 3, generation=3, parent_pool=[_elite()[0]])
    assert "STYLE MANDATE" not in claude.prompts[-1][0]


def test_fitness_style_terms_are_off_by_default():
    steady = Metrics(sharpe=1.0, trades=50, win_rate=0.9, avg_bars_held=3.0, years=1.0)
    lumpy = Metrics(sharpe=1.0, trades=50, win_rate=0.4, avg_bars_held=60.0, years=1.0)
    assert fitness_score(steady, FitnessConfig()) == fitness_score(lumpy, FitnessConfig())


def test_fitness_rewards_win_rate_and_short_holds_when_asked():
    cfg = FitnessConfig(win_rate_weight=2.0, hold_limit_bars=7.0, hold_penalty=1.0)
    steady = Metrics(sharpe=1.0, trades=80, win_rate=0.7, avg_bars_held=4.0, years=1.0)
    lumpy = Metrics(sharpe=1.0, trades=80, win_rate=0.4, avg_bars_held=4.0, years=1.0)
    slow = Metrics(sharpe=1.0, trades=80, win_rate=0.7, avg_bars_held=21.0, years=1.0)
    assert fitness_score(steady, cfg) - fitness_score(lumpy, cfg) == pytest.approx(0.6)
    assert fitness_score(steady, cfg) - fitness_score(slow, cfg) == pytest.approx(2.0)
    # a hold under the limit is never rewarded, only a long one charged
    quick = Metrics(sharpe=1.0, trades=80, win_rate=0.7, avg_bars_held=1.0, years=1.0)
    assert fitness_score(quick, cfg) == pytest.approx(fitness_score(steady, cfg))
    # with no trades there is nothing to reward or charge beyond inactivity
    idle = Metrics(sharpe=0.0, trades=0, years=1.0)
    assert fitness_score(idle, cfg) == fitness_score(idle, FitnessConfig())


def test_styled_run_seeds_its_archetypes_and_briefs_claude(tmp_path):
    style = get_style("leveraged_swing")
    cfg = EvolutionConfig(symbols=["AAA", "BBB", "CCC"], start="2015-01-01", end="2025-12-31",
                          offline=True, population=12, generations=2, elites=3,
                          survivor_reports=3, breeder="hybrid", llm_share=0.5, seed=5,
                          verbose=False, workers=1, validate_top=3, style="leveraged_swing",
                          db_path=str(tmp_path / "run.sqlite"))
    claude = RecordingClaude(_payload(4))
    evolution = Evolution(cfg, claude=claude)
    evolution.start()
    assert [g.name for g in evolution.population[:len(style.archetypes)]] \
        == [a[0] for a in style.archetypes]
    reports = evolution.run()
    assert len(reports) == 2
    assert claude.prompts and all("STYLE MANDATE" in p for p in claude.prompts)
    assert evolution.store.run_config(evolution.run_id)["style"] == "leveraged_swing"
    assert len(evolution.population) == 12 and all(is_valid(g) for g in evolution.population)


def test_unstyled_run_never_mentions_a_mandate(tmp_path):
    cfg = EvolutionConfig(symbols=["AAA", "BBB"], start="2015-01-01", end="2025-12-31",
                          offline=True, population=8, generations=1, elites=2,
                          survivor_reports=2, breeder="hybrid", llm_share=0.5, seed=3,
                          verbose=False, workers=1, validate_top=2,
                          db_path=str(tmp_path / "run.sqlite"))
    claude = RecordingClaude(_payload(3))
    Evolution(cfg, claude=claude).run()
    assert claude.prompts and not any("STYLE MANDATE" in p for p in claude.prompts)
