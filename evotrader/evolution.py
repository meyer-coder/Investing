"""The evolution loop.

    seed a population
    for each generation:
        backtest every agent on the training window   (free, deterministic)
        rank by fitness, keep the elites
        show the elites' genomes and journals to Claude, which explains what
            worked and writes the next generation                 (one API call)
        backfill with mutation and crossover, carry the elites over
        checkpoint everything to SQLite

The expensive part is bounded on purpose: one breeding call per generation, not
one call per trade.  A run of 1000 generations x 100 agents is 100k backtests
and about 1000 API calls.
"""
from __future__ import annotations

import math
import os
import random
import statistics
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .breeder import BreedResult, Elite, HybridBreeder, LLMBreeder, MutationBreeder
from .config import EvolutionConfig
from .data import Universe, date_cut, holdout_split, load_universe
from .features import FeatureSet, build_features
from .fitness import (Evaluation, FitnessConfig, Metrics, blended_score, compute_metrics,
                      fitness_score, rank, recency_score)
from .genome import Genome, GenomeError, compile_genome
from .journal import Journal
from .llm import Claude
from .population import ARCHETYPES, seed_from_genomes, seed_population
from .runner import buy_and_hold, run_backtest
from .store import Store
from .styles import TradingStyle, get_style


@dataclass
class Context:
    """Everything a worker process needs to score a genome."""

    train: Universe
    train_features: FeatureSet
    train_benchmark: List[float]
    test: Optional[Universe]
    test_features: Optional[FeatureSet]
    test_benchmark: Optional[List[float]]
    starting_cash: float
    commission_bps: float
    slippage_bps: float
    fitness: FitnessConfig
    leverage: float = 1.0
    intrabar_stops: bool = False
    day_trade: bool = False
    carry: bool = False
    day_stop: float = 0.0
    day_stop_exit: bool = True
    # prices trades fill at when they are not the features' own (cash session)
    train_exec: Optional[Universe] = None
    test_exec: Optional[Universe] = None
    # prop fitness: None for the metrics fitness
    prop: Optional[Dict[str, Any]] = None
    # When set, the held-out window is the full series traded from this bar:
    # indicators are warm on day one instead of losing fifty bars to warm-up.
    test_start_bar: Optional[int] = None


@dataclass
class Outcome:
    """One genome's evaluation plus the journal the breeder will read."""

    genome_id: str
    name: str
    generation: int
    score: float
    metrics: Metrics
    journal: Optional[Journal] = None
    error: str = ""


_CTX: Optional[Context] = None


def _init_worker(ctx: Context) -> None:  # pragma: no cover - process boundary
    global _CTX
    _CTX = ctx


def _score_in_worker(payload: Dict[str, Any]) -> Outcome:  # pragma: no cover
    assert _CTX is not None
    return score_genome(Genome.from_dict(payload), _CTX)


def score_genome(genome: Genome, ctx: Context, *, window: str = "train") -> Outcome:
    """Backtest one genome and turn the result into a fitness score."""
    universe = ctx.train if window == "train" else ctx.test
    features = ctx.train_features if window == "train" else ctx.test_features
    benchmark = ctx.train_benchmark if window == "train" else ctx.test_benchmark
    if universe is None or features is None:
        return Outcome(genome.id, genome.name, genome.generation, float("-inf"),
                       Metrics(), None, "no data for window")
    try:
        compiled = compile_genome(genome)
        start_bar = None
        if window == "test" and ctx.test_start_bar is not None:
            start_bar = max(ctx.test_start_bar,
                            features.warmup_for(compiled.feature_names()))
        exec_universe = ctx.train_exec if window == "train" else ctx.test_exec
        result = run_backtest(
            compiled, universe, features, starting_cash=ctx.starting_cash,
            commission_bps=ctx.commission_bps, slippage_bps=ctx.slippage_bps,
            leverage=ctx.leverage, start_bar=start_bar,
            intrabar_stops=ctx.intrabar_stops, day_trade=ctx.day_trade,
            carry=ctx.carry, day_stop=ctx.day_stop, day_stop_exit=ctx.day_stop_exit,
            exec_bars=exec_universe.bars if exec_universe is not None else None)
    except GenomeError as exc:
        return Outcome(genome.id, genome.name, genome.generation, float("-inf"),
                       Metrics(), None, f"invalid genome: {exc}")
    except Exception as exc:  # noqa: BLE001 - one bad genome must not stop a run
        return Outcome(genome.id, genome.name, genome.generation, float("-inf"),
                       Metrics(), None, f"backtest failed: {type(exc).__name__}: {exc}")

    if result.start_bar != features.warmup:
        # A fast genome starts before the slow features exist; benchmark it over
        # the bars it actually traded rather than the global warm-up window.
        benchmark = buy_and_hold(universe, features, starting_cash=ctx.starting_cash,
                                 start=result.start_bar)
    metrics = compute_metrics(result.journal.equity, result.journal.trades,
                              benchmark=benchmark, turnover=result.turnover,
                              exposure=result.exposure)
    journal = result.journal
    if ctx.prop is not None and window == "train":
        score = prop_score(result, exec_universe or universe, ctx.prop)
        journal.equity = []
        journal.equity_dates = []
        return Outcome(genome.id, genome.name, genome.generation, score, metrics, journal)
    score = fitness_score(metrics, ctx.fitness)
    if ctx.fitness.recent_bars > 0 and ctx.fitness.recent_weight > 0:
        score = blended_score(score, recency_score(
            journal.equity, journal.trades, journal.equity_dates, ctx.fitness,
            benchmark=benchmark, turnover=result.turnover, exposure=result.exposure),
            ctx.fitness)
    journal.equity = []          # the curve is large and only metrics need it
    journal.equity_dates = []
    return Outcome(genome.id, genome.name, genome.generation, score, metrics, journal)


def prop_score(result, universe: Universe, prop: Dict[str, Any]) -> float:
    """Pass rate minus breach rate of fresh Legacy challenges (25K unless the
    settings name another size), less a charge for funded accounts lost within
    six months, blended toward the last year.

    Trades come from the backtest run with the config's costs; the replay
    takes the slippage back out of the fills and charges per-contract costs.
    """
    from .prop import (LEGACY_25K, LEGACY_25K_FUNDED, LEGACY_50K, LEGACY_50K_FUNDED, LEGACY_100K,
                       LEGACY_100K_FUNDED, MICROS, challenge_stats, funded_stats, trade_paths)
    rules, funded_rules = {"25K": (LEGACY_25K, LEGACY_25K_FUNDED), "50K": (LEGACY_50K, LEGACY_50K_FUNDED),
                           "100K": (LEGACY_100K, LEGACY_100K_FUNDED)}[prop.get("account", "25K")]
    micro = MICROS[prop["micro"]]
    bars = universe.bars[micro.data_symbol]
    paths = trade_paths(result.journal.trades, bars, micro=micro,
                        contracts=int(prop.get("contracts", 1)), price_now=float(prop["price_now"]),
                        slippage_bps=float(prop.get("slippage_bps", 0.0)))
    n = len(bars)
    first = max(result.start_bar, 1)
    last = n - 21                                   # a month of data to resolve in, at least
    every = max(1, int(prop.get("every", 5)))
    starts = list(range(first, max(first + 1, last), every))
    recent = [s for s in starts if s >= n - 252]

    def block(ss):
        if not ss:
            return 0.0
        ch = challenge_stats(paths, ss, rules, horizon=252)
        fu = funded_stats(paths, ss, funded_rules)
        speed = 0.0 if ch.passed == 0 or ch.median_days_to_pass != ch.median_days_to_pass else \
            min(ch.median_days_to_pass / 252.0, 1.0)
        still_open = ch.still_open / ch.starts if ch.starts else 0.0
        return (ch.pass_rate - ch.breach_rate - 0.5 * fu.breach_126 - 0.1 * speed
                - float(prop.get("open_penalty", 0.0)) * still_open)

    w = float(prop.get("recent_weight", 0.6))
    full = block(starts)
    return full if not recent or w <= 0 else (1 - w) * full + w * block(recent)


def replay_genome(genome: Genome, cfg: EvolutionConfig, *,
                  symbols: Optional[Sequence[str]] = None,
                  start: str = "", end: str = "") -> Outcome:
    """Backtest one stored genome over an arbitrary window.

    The evolution loop shares one prepared :class:`Context` across a whole
    generation; this builds a throwaway one so a single genome can be re-run on
    dates, or symbols, it never evolved on.  Nothing is written anywhere.
    """
    universe = load_universe(list(symbols) if symbols else cfg.symbols,
                             start or cfg.start, end or cfg.end, offline=cfg.offline)
    features = build_features(universe)
    ctx = Context(train=universe, train_features=features,
                  train_benchmark=buy_and_hold(universe, features,
                                               starting_cash=cfg.starting_cash),
                  test=None, test_features=None, test_benchmark=None,
                  starting_cash=cfg.starting_cash, commission_bps=cfg.commission_bps,
                  slippage_bps=cfg.slippage_bps, fitness=cfg.fitness,
                  leverage=cfg.leverage, intrabar_stops=cfg.intrabar_stops,
                  day_trade=cfg.day_trade, carry=cfg.carry, day_stop=cfg.day_stop,
                  day_stop_exit=cfg.day_stop_exit, train_exec=exec_universe(cfg, universe))
    return score_genome(genome, ctx)


def exec_universe(cfg: EvolutionConfig, universe: Universe) -> Optional[Universe]:
    """The cash-session prices a ``session: cash`` run trades at, date for date;
    None when trades fill at the features' own bars."""
    if not (cfg.day_trade and cfg.session == "cash"):
        return None
    from .data import CASH_PROXIES, cash_session_bars, load_symbol
    out = {}
    for sym, bars in universe.bars.items():
        proxy = load_symbol(CASH_PROXIES[sym.upper()], cfg.start, cfg.end, offline=cfg.offline)
        out[sym] = cash_session_bars(bars, proxy)
    return Universe(out, list(universe.calendar))


@dataclass
class GenerationReport:
    generation: int
    best: Optional[Evaluation]
    evaluations: List[Evaluation]
    elapsed_s: float
    cost_usd: float
    analysis: str = ""
    lessons: List[str] = field(default_factory=list)
    breeding_error: str = ""

    @property
    def scores(self) -> List[float]:
        return [e.score for e in self.evaluations if not e.error and math.isfinite(e.score)]


class Evolution:
    """Owns one run: data, population, breeder, persistence."""

    #: Evaluated outcomes kept in memory, journals included, so unchanged agents
    #: (the elites) are not re-run.  Bounded and least-recently-used, because a
    #: journal is hundreds of trades and an unbounded cache over a long run is
    #: how a 100 x 1000 evolution gets killed for memory.
    CACHE_LIMIT = 1_000

    def __init__(self, cfg: EvolutionConfig, *, store: Optional[Store] = None,
                 claude: Optional[Claude] = None):
        cfg.validate()
        self.cfg = cfg
        self.style: Optional[TradingStyle] = get_style(cfg.style)
        self.run_id = cfg.run_id or f"run-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        cfg.run_id = self.run_id
        self.rng = random.Random(cfg.seed or None)
        self.store = store if store is not None else Store(cfg.db_path)
        self.claude = claude if claude is not None else Claude(
            model=cfg.model, max_tokens=cfg.max_tokens, effort=cfg.effort,
            budget_usd=cfg.budget_usd, verbose=cfg.verbose)
        self.breeder = self._make_breeder()
        self.ctx: Optional[Context] = None
        self.population: List[Genome] = []
        self.history: List[Dict[str, Any]] = []
        self.generation = 0
        self._cache: "OrderedDict[str, Outcome]" = OrderedDict()
        self._pool: Optional[ProcessPoolExecutor] = None
        self.window_label = ""

    # ------------------------------------------------------------- breeder
    def _make_breeder(self):
        if self.cfg.breeder == "mutation":
            m = MutationBreeder(self.rng, crossover_rate=self.cfg.crossover_rate,
                                immigrant_rate=self.cfg.immigrant_rate)
            return _MutationOnly(m)
        share = 1.0 if self.cfg.breeder == "llm" else self.cfg.llm_share
        breeder = HybridBreeder(self.claude, rng=self.rng, llm_share=share,
                                llm_every=self.cfg.llm_every, verbose=self.cfg.verbose)
        breeder.mutation.crossover_rate = self.cfg.crossover_rate
        breeder.mutation.immigrant_rate = self.cfg.immigrant_rate
        return breeder

    # ---------------------------------------------------------------- data
    def prepare(self) -> None:
        """Load market data, build features, split off the held-out window."""
        cfg = self.cfg
        self._log(f"loading {len(cfg.symbols)} symbols {cfg.start}..{cfg.end}"
                  f"{' (offline/synthetic)' if cfg.offline else ''}")
        universe = load_universe(cfg.symbols, cfg.start, cfg.end,
                                 offline=cfg.offline, refresh=cfg.refresh_data)
        test_start_bar: Optional[int] = None
        if cfg.test_start:
            cut = date_cut(universe, cfg.test_start)
            train = universe.slice(0, cut)
            test = universe                      # traded from ``cut``, warm from bar 0
            test_start_bar = cut
            test_features = build_features(test) if len(universe) - cut > 20 else None
        else:
            train, test = holdout_split(universe, cfg.test_frac)
            test_features = build_features(test) if len(test) > 60 else None
        train_features = build_features(train)
        full_exec = exec_universe(cfg, universe)
        if full_exec is not None:
            train_exec = full_exec.slice(0, len(train))
            test_exec = full_exec if test_start_bar is not None else \
                full_exec.slice(len(train), len(universe))
        else:
            train_exec = test_exec = None
        self.ctx = Context(
            train=train, train_features=train_features,
            train_benchmark=buy_and_hold(train, train_features,
                                         starting_cash=cfg.starting_cash),
            test=test if test_features else None, test_features=test_features,
            test_benchmark=(buy_and_hold(test, test_features, starting_cash=cfg.starting_cash,
                                         start=test_start_bar)
                            if test_features else None),
            starting_cash=cfg.starting_cash, commission_bps=cfg.commission_bps,
            slippage_bps=cfg.slippage_bps, fitness=cfg.fitness,
            leverage=cfg.leverage, test_start_bar=test_start_bar,
            intrabar_stops=cfg.intrabar_stops, prop=self._prop_settings(universe),
            day_trade=cfg.day_trade, carry=cfg.carry, day_stop=cfg.day_stop,
            day_stop_exit=cfg.day_stop_exit, train_exec=train_exec, test_exec=test_exec,
        )
        a, b = train.date_range()
        self.window_label = f"train {a}..{b} ({len(train)} bars, {len(train.symbols)} symbols)"
        if self.ctx.test is not None:
            if test_start_bar is not None:
                ta, tb = universe.calendar[test_start_bar], universe.calendar[-1]
                n_test = len(universe) - test_start_bar
            else:
                (ta, tb), n_test = self.ctx.test.date_range(), len(self.ctx.test)
            self.window_label += f"; held-out {ta}..{tb} ({n_test} bars)"
        if cfg.leverage != 1.0:
            self.window_label += f"; account leverage {cfg.leverage:g}x"
        if cfg.day_trade:
            self.window_label += ("; same-day trades, 09:30 to 16:00 New York" if cfg.session == "cash"
                                  else "; same-day trades, Globex open to settlement")
            if cfg.carry:
                self.window_label += (f", positions carried day to day"
                                      f"{f' with a {cfg.day_stop:.2%} daily stop' if cfg.day_stop else ''}")
        self._log(self.window_label)
        bh = self.ctx.train_benchmark
        if bh:
            self._log(f"buy-and-hold over the training window: "
                      f"{(bh[-1] / bh[0] - 1) * 100:+.1f}%")

    def _prop_settings(self, universe: Universe) -> Optional[Dict[str, Any]]:
        cfg = self.cfg
        if cfg.fitness_mode != "prop":
            return None
        from .prop import MICROS
        micro = MICROS[cfg.prop_micro]
        # today's contract size: the last close in the whole series, not the training window's
        price_now = float(universe.bars[micro.data_symbol].close[-1])
        self._log(f"prop fitness: FundedNext Legacy {cfg.prop_account} on {cfg.prop_contracts} {micro.name} "
                  f"(${price_now * micro.point_value * cfg.prop_contracts:,.0f} notional)")
        return {"micro": cfg.prop_micro, "contracts": cfg.prop_contracts, "every": cfg.prop_every,
                "account": cfg.prop_account, "open_penalty": cfg.prop_open_penalty,
                "recent_weight": cfg.prop_recent_weight, "price_now": price_now,
                "slippage_bps": cfg.slippage_bps}

    # ----------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self.ctx is None:
            self.prepare()
        self.store.create_run(self.run_id, self.cfg.to_dict(), self.cfg.note)
        if self.cfg.seed_file:
            # An island: generation 0 is these genomes and their variants only.
            self.population = seed_from_genomes(load_seed_genomes(self.cfg.seed_file),
                                                self.cfg.population, self.rng, generation=0)
        else:
            # A style's archetypes go first so they are guaranteed a seat in gen 0.
            library = (list(self.style.archetypes) + list(ARCHETYPES)) if self.style else None
            self.population = seed_population(self.cfg.population, self.rng, generation=0,
                                              archetypes=library)
        self._apply_style_size(self.population)
        self.generation = 0
        self._log(f"run {self.run_id}: seeded {len(self.population)} agents")
        if self.style:
            self._log(f"style {self.style.name!r}: {self.style.summary}")
        if not self.claude.available and self.cfg.breeder != "mutation":
            self._log(f"note: {self.claude.unavailable_reason}")

    def resume(self, run_id: str) -> None:
        """Continue a run from its most recent checkpoint."""
        stored = self.store.run_config(run_id)
        if stored is None:
            raise ValueError(f"unknown run {run_id!r}")
        checkpoint = self.store.latest_checkpoint(run_id)
        if checkpoint is None:
            raise ValueError(f"run {run_id!r} has no checkpoint to resume from")
        self.run_id = run_id
        self.cfg.run_id = run_id
        if self.ctx is None:
            self.prepare()
        self.population = checkpoint["population"]
        self.generation = int(checkpoint["generation"]) + 1
        self.history = self.store.generation_history(run_id)
        if isinstance(self.breeder, HybridBreeder) and self.breeder.llm:
            self.breeder.llm.lessons = list(checkpoint["lessons"])
        try:
            self.rng.setstate(_restore_state(checkpoint["rng_state"]))
        except (TypeError, ValueError):
            pass  # a fresh stream is acceptable; the population is what matters
        self.store.set_status(run_id, "running")
        self._log(f"resumed {run_id} at generation {self.generation} "
                  f"with {len(self.population)} agents")

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None

    # ---------------------------------------------------------------- loop
    def run(self, generations: Optional[int] = None) -> List[GenerationReport]:
        if not self.population:
            self.start()
        total = generations if generations is not None else self.cfg.generations
        reports: List[GenerationReport] = []
        try:
            for _ in range(total):
                reports.append(self.step())
        except KeyboardInterrupt:
            self._log("interrupted; the last checkpoint is intact "
                      f"(resume with: evotrader resume {self.run_id})")
            self.store.set_status(self.run_id, "interrupted")
            return reports
        finally:
            self.close()
        self.store.set_status(self.run_id, "finished")
        return reports

    def _apply_style_size(self, genomes: Sequence[Genome]) -> None:
        """A style with a fixed size owns sizing: every entry trades it."""
        size = self.style.fixed_size if self.style else None
        if not size:
            return
        for g in genomes:
            for rule in g.entry_rules:
                rule.weight = size
            g.risk.max_position_pct = size
            g.risk.max_gross_exposure = max(g.risk.max_gross_exposure, size)

    def step(self) -> GenerationReport:
        """Evaluate the current population, then breed the next one."""
        assert self.ctx is not None, "call prepare() or start() first"
        started = time.time()
        gen = self.generation
        # Covers the seeded generation, bred children and hand-injected ones.
        self._apply_style_size(self.population)

        outcomes = self._evaluate(self.population)
        by_id = {o.genome_id: o for o in outcomes}
        genome_by_id = {g.id: g for g in self.population}

        evals = [Evaluation(genome_id=o.genome_id, name=o.name, generation=gen,
                            score=o.score, metrics=o.metrics, error=o.error)
                 for o in outcomes]
        ranked = rank(evals)
        self._validate_top(ranked, genome_by_id)

        elites: List[Elite] = []
        for ev in ranked[:self.cfg.survivor_reports]:
            if ev.error:
                continue
            genome = genome_by_id.get(ev.genome_id)
            if genome is not None:
                elites.append((genome, ev, by_id[ev.genome_id].journal))

        self.store.save_genomes(self.run_id, self.population)
        self.store.save_evaluations(self.run_id, gen, ranked)
        for genome, ev, journal in elites[:self.cfg.elites]:
            if journal is not None:
                self.store.save_trades(self.run_id, gen, genome.id, journal.trades)

        best = ranked[0] if ranked and not ranked[0].error else None
        report = GenerationReport(generation=gen, best=best, evaluations=ranked,
                                  elapsed_s=time.time() - started, cost_usd=0.0)

        # ---- breed the next generation
        survivors = [g for g, _, _ in elites][:self.cfg.elites]
        n_offspring = self.cfg.population - len(survivors)
        breed = self.breeder.breed(
            elites[:self.cfg.survivor_reports], n_offspring, generation=gen,
            evals=ranked, history=self.history, window=self.window_label,
            parent_pool=survivors or self.population,
            extra=self.style.mandate if self.style else "",
        )
        report.cost_usd = breed.cost_usd
        report.analysis = breed.analysis
        report.lessons = list(breed.lessons)
        report.breeding_error = breed.error

        children = breed.genomes[:n_offspring]
        while len(children) < n_offspring:   # never let the population shrink
            filler = self.breeder.breed(elites[:1], n_offspring - len(children),
                                        generation=gen, parent_pool=survivors or self.population)
            if not filler.genomes:
                break
            children.extend(filler.genomes)
        next_population = [g.copy(generation=gen + 1, origin="elite",
                                  parents=[g.id], rationale="carried over as elite")
                           for g in survivors] + children[:n_offspring]
        self._apply_style_size(next_population)     # checkpoints hold what will be run

        scores = report.scores
        self.store.save_generation(
            self.run_id, gen,
            best_score=best.score if best else float("nan"),
            mean_score=statistics.fmean(scores) if scores else float("nan"),
            median_score=statistics.median(scores) if scores else float("nan"),
            best_genome_id=best.genome_id if best else "",
            analysis=breed.analysis, lessons=breed.lessons,
            cost_usd=breed.cost_usd, elapsed_s=report.elapsed_s)
        self.history.append({
            "generation": gen,
            "best_score": best.score if best else float("nan"),
            "mean_score": statistics.fmean(scores) if scores else float("nan"),
            "best_name": best.name if best else "?",
            "best_genome_id": best.genome_id if best else "",
        })

        if self.cfg.checkpoint_every and gen % self.cfg.checkpoint_every == 0:
            self.store.save_checkpoint(self.run_id, gen, next_population,
                                       self.breeder.lessons if hasattr(self.breeder, "lessons") else [],
                                       self.rng.getstate(), self.claude.usage.to_dict())

        self._log_generation(report, breed)
        self.population = next_population
        self.generation = gen + 1
        return report

    # ---------------------------------------------------------- evaluation
    def _evaluate(self, population: Sequence[Genome]) -> List[Outcome]:
        """Score every genome, reusing cached results for unchanged agents."""
        assert self.ctx is not None
        todo: List[Genome] = []
        outcomes: List[Outcome] = []
        for genome in population:
            cached = self._cache.get(genome.fingerprint())
            if cached is not None:
                self._cache.move_to_end(genome.fingerprint())   # survivors stay resident
                outcomes.append(Outcome(genome.id, genome.name, genome.generation,
                                        cached.score, cached.metrics, cached.journal,
                                        cached.error))
            else:
                todo.append(genome)

        if todo:
            workers = self._worker_count(len(todo))
            if workers > 1:
                pool = self._get_pool(workers)
                payloads = [g.to_dict() for g in todo]
                fresh = list(pool.map(_score_in_worker, payloads, chunksize=4))
            else:
                fresh = [score_genome(g, self.ctx) for g in todo]
            for genome, outcome in zip(todo, fresh):
                self._cache[genome.fingerprint()] = outcome
                while len(self._cache) > self.CACHE_LIMIT:
                    self._cache.popitem(last=False)             # evict the least recently used
                outcomes.append(outcome)
        return outcomes

    def _validate_top(self, ranked: Sequence[Evaluation],
                      genome_by_id: Dict[str, Genome]) -> None:
        """Score the leaders on the held-out window — reporting only, never
        selection, so the out-of-sample result stays honest."""
        assert self.ctx is not None
        if self.ctx.test is None or self.cfg.validate_top <= 0:
            return
        for ev in list(ranked)[:self.cfg.validate_top]:
            if ev.error:
                continue
            genome = genome_by_id.get(ev.genome_id)
            if genome is None:
                continue
            out = score_genome(genome, self.ctx, window="test")
            if not out.error:
                ev.test_metrics = out.metrics
                ev.test_score = out.score

    def _worker_count(self, jobs: int) -> int:
        if self.cfg.workers > 0:
            return min(self.cfg.workers, jobs)
        if self.cfg.workers == 0 and jobs >= 16:
            return min(max((os.cpu_count() or 2) - 1, 1), jobs, 16)
        return 1

    def _get_pool(self, workers: int) -> ProcessPoolExecutor:
        if self._pool is None or getattr(self._pool, "_max_workers", 0) != workers:
            if self._pool is not None:
                self._pool.shutdown(wait=False)
            self._pool = ProcessPoolExecutor(max_workers=workers,
                                             initializer=_init_worker,
                                             initargs=(self.ctx,))
        return self._pool

    # ------------------------------------------------------------ logging
    def _log(self, message: str) -> None:
        if self.cfg.verbose:
            print(message, flush=True)

    def _log_generation(self, report: GenerationReport, breed: BreedResult) -> None:
        if not self.cfg.verbose:
            return
        scores = report.scores
        best = report.best
        head = (f"gen {report.generation:>4} | best {best.score:+.3f} "
                f"| mean {statistics.fmean(scores):+.3f} " if best and scores
                else f"gen {report.generation:>4} | no scored agents ")
        detail = f"| {best.name[:28]:<28} {best.metrics.summary()}" if best else ""
        timing = f" | {report.elapsed_s:.1f}s"
        if breed.cost_usd:
            timing += f" | ${breed.cost_usd:.3f} (run ${self.claude.usage.cost_usd:.2f})"
        print(head + detail + timing, flush=True)
        if best is not None and best.test_metrics is not None:
            print(f"        held-out: {best.test_metrics.summary()}", flush=True)
        if breed.analysis:
            first = breed.analysis.strip().split("\n")[0]
            print(f"        claude: {first[:150]}", flush=True)


class _MutationOnly:
    """Adapter so the offline breeder matches the hybrid breeder's signature."""

    def __init__(self, mutation: MutationBreeder):
        self.mutation = mutation
        self.lessons: List[str] = []

    def breed(self, elites: Sequence[Elite], count: int, *, generation: int,
              evals: Sequence[Evaluation] = (), history: Sequence[Dict[str, Any]] = (),
              window: str = "", parent_pool: Optional[Sequence[Genome]] = None,
              extra: str = "") -> BreedResult:
        return self.mutation.breed(elites, count, generation=generation,
                                   parent_pool=parent_pool)


def load_seed_genomes(path: str) -> List[Genome]:
    """A JSON list of genomes, or ``{"genomes": [...]}``; every rule must compile."""
    import json
    with open(path) as fh:
        raw = json.load(fh)
    items = raw.get("genomes", []) if isinstance(raw, dict) else raw
    out: List[Genome] = []
    for item in items:
        g = Genome.from_dict(item)
        compile_genome(g)
        out.append(g)
    if not out:
        raise ValueError(f"no genomes in seed file {path}")
    return out


def _restore_state(state: Any) -> tuple:
    """JSON turns the RNG state's tuples into lists; turn them back."""
    if isinstance(state, list):
        return tuple(_restore_state(x) for x in state)
    return state
