"""Run configuration: one JSON file describes an entire evolution run."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

from .fitness import FitnessConfig
from .llm import DEFAULT_MODEL
from .styles import get_style

DEFAULT_SYMBOLS = ["SPY", "QQQ", "IWM", "EFA", "TLT", "GLD", "XLE", "XLF", "XLK", "XLV"]


@dataclass
class EvolutionConfig:
    # --- what to trade
    symbols: List[str] = field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    start: str = "2010-01-01"
    end: str = "2024-12-31"
    offline: bool = False              # use synthetic data instead of fetching
    refresh_data: bool = False
    test_frac: float = 0.25            # held-out tail, never used for selection
    test_start: str = ""               # held-out window from this date instead (overrides test_frac)
    leverage: float = 1.0              # account notional per unit of equity (2.0 = 2x futures)
    intrabar_stops: bool = False       # stop losses as resting orders filled inside the bar
    # Same-day trading, for prop firms that forbid holding overnight: bought at
    # the open, sold the same day at a resting stop or target, else the close.
    day_trade: bool = False
    carry: bool = False                # keep the strategy's position across days, flat every night
    day_stop: float = 0.0              # with carry: resting stop under each day's entry (0.01 = 1%)
    day_stop_exit: bool = True         # the day stop ends the carried position (else caps the day only)
    session: str = "globex"            # globex (18:00 open to settlement) or cash (09:30 to 16:00)
    # Prop-firm fitness: score each agent by how often a fresh funded-account
    # challenge started on it passes rather than breaches (evotrader/prop.py).
    fitness_mode: str = "metrics"      # "metrics" (Sharpe, excess, penalties) or "prop"
    prop_micro: str = "MNQ"            # MNQ | MES | MYM | M2K; the universe must hold its index
    prop_account: str = "25K"          # FundedNext Legacy size: 25K | 50K | 100K
    prop_open_penalty: float = 0.0     # charge per account neither passed nor breached in a year
    prop_contracts: int = 1
    prop_every: int = 5                # a new account every N training bars
    prop_recent_weight: float = 0.6    # share of the score from accounts started in the last year

    # --- the loop
    population: int = 100
    generations: int = 1000
    elites: int = 5                    # survivors that breed and carry over
    survivor_reports: int = 5          # how many elite journals Claude reads
    seed: int = 0
    starting_cash: float = 100_000.0
    commission_bps: float = 1.0
    slippage_bps: float = 5.0

    # --- breeding
    breeder: str = "hybrid"            # hybrid | llm | mutation
    llm_share: float = 0.5             # share of each generation written by Claude
    llm_every: int = 1                 # call Claude every N generations
    model: str = DEFAULT_MODEL
    effort: str = "high"
    max_tokens: int = 16_000
    budget_usd: float = 0.0            # 0 = no ceiling
    immigrant_rate: float = 0.10
    crossover_rate: float = 0.35
    style: str = ""                    # a TradingStyle name (styles.py); "" = none
    seed_file: str = ""                # genome JSON that seeds generation 0 instead of archetypes

    # --- fitness
    fitness: FitnessConfig = field(default_factory=FitnessConfig)

    # --- plumbing
    run_id: str = ""
    db_path: str = os.path.join("runs", "evotrader.sqlite")
    workers: int = 0                   # 0 = auto
    checkpoint_every: int = 1
    validate_top: int = 10             # genomes scored on the held-out window
    verbose: bool = True
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["fitness"] = self.fitness.to_dict()
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EvolutionConfig":
        known = {f.name for f in fields(EvolutionConfig)}
        clean = {k: v for k, v in (d or {}).items() if k in known}
        fit = clean.pop("fitness", None)
        cfg = EvolutionConfig(**clean)
        if isinstance(fit, dict):
            valid = {f.name for f in fields(FitnessConfig)}
            cfg.fitness = FitnessConfig(**{k: v for k, v in fit.items() if k in valid})
        return cfg

    @staticmethod
    def load(path: str) -> "EvolutionConfig":
        with open(path) as fh:
            return EvolutionConfig.from_dict(json.load(fh))

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    def validate(self) -> None:
        if self.population < 4:
            raise ValueError("population must be at least 4")
        if self.elites < 1 or self.elites >= self.population:
            raise ValueError("elites must be between 1 and population-1")
        if self.generations < 1:
            raise ValueError("generations must be at least 1")
        if self.breeder not in ("hybrid", "llm", "mutation"):
            raise ValueError("breeder must be hybrid, llm or mutation")
        if not self.symbols:
            raise ValueError("at least one symbol is required")
        if not 1.0 <= float(self.leverage) <= 10.0:
            raise ValueError("leverage must be between 1 and 10")
        if not 0.0 <= float(self.day_stop) < 0.5:
            raise ValueError("day_stop must be a fraction between 0 and 0.5")
        if (self.carry or self.day_stop) and not self.day_trade:
            raise ValueError("carry and day_stop are for same-day trading: set day_trade")
        if self.session not in ("globex", "cash"):
            raise ValueError("session must be globex or cash")
        if self.session == "cash":
            from .data import CASH_PROXIES
            if not self.day_trade:
                raise ValueError("session cash is for same-day trading: set day_trade")
            missing = [x for x in self.symbols if x.upper() not in CASH_PROXIES]
            if missing:
                raise ValueError(f"no cash-session proxy for {', '.join(missing)} "
                                 f"(have {', '.join(CASH_PROXIES)})")
        if self.fitness_mode not in ("metrics", "prop"):
            raise ValueError("fitness_mode must be metrics or prop")
        if self.fitness_mode == "prop":
            from .prop import MICROS
            if self.prop_account not in ("25K", "50K", "100K"):
                raise ValueError("prop_account must be 25K, 50K or 100K")
            if self.prop_micro not in MICROS:
                raise ValueError(f"prop_micro must be one of {', '.join(MICROS)}")
            if MICROS[self.prop_micro].data_symbol not in [x.upper() for x in self.symbols]:
                raise ValueError(f"a {self.prop_micro} prop run needs "
                                 f"{MICROS[self.prop_micro].data_symbol} in symbols")
        if self.style:
            get_style(self.style)      # raises ValueError for an unknown name
