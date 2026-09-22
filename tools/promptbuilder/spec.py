"""The strategy spec: what a backtest prompt must contain before it is worth sending.

The whole point of this module is the validation.  A backtest brief that does
not state its strategy produces confident work aimed at the wrong target, so
:func:`load_spec` refuses to return one.  Every other check here exists because
an unstated field was silently guessed at some point.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


class SpecError(ValueError):
    """A spec that cannot produce an honest prompt."""


@dataclass
class AxisValue:
    label: str
    pass_rate: float = 1.0      # fraction of base signals that survive this filter

    @staticmethod
    def parse(raw: Any) -> "AxisValue":
        if isinstance(raw, dict):
            if "label" not in raw:
                raise SpecError(f"axis value {raw!r} needs a 'label'")
            rate = float(raw.get("pass_rate", 1.0))
            if not 0.0 < rate <= 1.0:
                raise SpecError(f"pass_rate for {raw['label']!r} must be in (0, 1]; got {rate}")
            return AxisValue(str(raw["label"]), rate)
        return AxisValue(str(raw), 1.0)


@dataclass
class Axis:
    name: str
    values: List[AxisValue]

    @staticmethod
    def parse(raw: Dict[str, Any]) -> "Axis":
        if "name" not in raw or "values" not in raw:
            raise SpecError(f"each grid axis needs 'name' and 'values'; got {raw!r}")
        values = [AxisValue.parse(v) for v in raw["values"]]
        if len(values) < 2:
            raise SpecError(f"axis {raw['name']!r} needs at least 2 values to be a variation axis")
        return Axis(str(raw["name"]), values)


@dataclass
class DataSource:
    name: str
    note: str = ""


@dataclass
class Strategy:
    name: str
    instrument: str
    timeframe: str
    thesis: str
    entry_rules: List[str]
    exit_rules: List[str]
    risk: Dict[str, Any]
    direction: str = "long-only"
    session_in_spec: str = ""
    override_session: bool = True


@dataclass
class Window:
    """Lookback window and the recency emphasis inside it."""
    lookback_years: float
    emphasis_months: float
    recent_weight: float
    method: str
    require_recent_positive: bool
    min_trades_recent: int
    half_life_days: int

    @property
    def lookback_days(self) -> int:
        return int(round(self.lookback_years * 252))

    @property
    def emphasis_days(self) -> int:
        return int(round(self.emphasis_months * 21))


@dataclass
class Spec:
    strategy: Strategy
    sources: List[DataSource]
    history_days: int
    base_signals_per_day: float
    timezone: str
    axes: List[Axis]
    grid_min: int
    grid_max: int
    seed: int
    min_trades: int
    target_trades: List[int]
    oos_fraction: float
    session_buckets: List[str]
    seasonality: List[str]
    events: bool
    window: Window
    deliverables: List[str]
    raw: Dict[str, Any] = field(default_factory=dict)


_REQUIRED_STRATEGY = ("name", "instrument", "timeframe", "thesis",
                      "entry_rules", "exit_rules", "risk")


def load_spec(path: str) -> Spec:
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: top level must be a mapping")
    return parse_spec(raw)


def parse_spec(raw: Dict[str, Any]) -> Spec:
    strat = raw.get("strategy")
    if not isinstance(strat, dict):
        raise SpecError(
            "spec has no 'strategy' block.\n"
            "This is the failure this tool exists to prevent: a brief that does not\n"
            "say what it is testing produces polished work on the wrong strategy.\n"
            "Add strategy.name/instrument/timeframe/thesis/entry_rules/exit_rules/risk.")

    missing = [k for k in _REQUIRED_STRATEGY if not strat.get(k)]
    if missing:
        raise SpecError(f"strategy block is missing required fields: {', '.join(missing)}")
    for key in ("entry_rules", "exit_rules"):
        if not isinstance(strat[key], list) or not strat[key]:
            raise SpecError(f"strategy.{key} must be a non-empty list of rules")
    if not isinstance(strat["risk"], dict) or not strat["risk"]:
        raise SpecError("strategy.risk must be a non-empty mapping (stop, target, sizing, ...)")

    strategy = Strategy(
        name=str(strat["name"]), instrument=str(strat["instrument"]),
        timeframe=str(strat["timeframe"]), thesis=str(strat["thesis"]),
        entry_rules=[str(r) for r in strat["entry_rules"]],
        exit_rules=[str(r) for r in strat["exit_rules"]],
        risk=dict(strat["risk"]), direction=str(strat.get("direction", "long-only")),
        session_in_spec=str(strat.get("session_in_spec", "")),
        override_session=bool(strat.get("override_session", True)),
    )

    data = raw.get("data") or {}
    sources_raw = data.get("sources") or []
    if not sources_raw:
        raise SpecError("data.sources must list at least one source, in preference order")
    sources = [DataSource(str(s["name"]), str(s.get("note", "")))
               if isinstance(s, dict) else DataSource(str(s))
               for s in sources_raw]

    win_raw = raw.get("window") or {}
    lookback_years = float(win_raw.get("lookback_years", 0) or 0)
    history_days = int(data.get("history_days", 0))
    if history_days <= 0 and lookback_years > 0:
        history_days = int(round(lookback_years * 252))
    if history_days <= 0:
        raise SpecError("data.history_days must be a positive number of trading days "
                        "(what you believe the best source can actually deliver)")
    base_rate = float(data.get("base_signals_per_day", 0))
    if base_rate <= 0:
        raise SpecError("data.base_signals_per_day must be > 0 — your estimate of how often "
                        "the unfiltered strategy fires per trading day. Feasibility "
                        "depends on it; a guess you state beats a guess you hide.")

    guards = raw.get("guardrails") or {}
    min_trades = int(guards.get("min_trades", 400))

    grid = raw.get("grid") or {}
    axes = [Axis.parse(a) for a in (grid.get("axes") or [])]
    if len(axes) < 2:
        raise SpecError("grid.axes needs at least 2 axes to build a variation grid")

    target = list(guards.get("target_trades", [400, 500]))
    oos = float(guards.get("oos_fraction", 0.3))
    if not 0.0 < oos < 1.0:
        raise SpecError("guardrails.oos_fraction must be between 0 and 1")

    if lookback_years <= 0:
        lookback_years = history_days / 252.0
    emphasis_months = float(win_raw.get("emphasis_months", 0) or 0)
    if emphasis_months < 0:
        raise SpecError("window.emphasis_months cannot be negative")
    emphasis_days = int(round(emphasis_months * 21))
    if emphasis_days >= history_days:
        raise SpecError(
            f"window.emphasis_months ({emphasis_months:g} months = {emphasis_days} days) must be "
            f"shorter than the lookback window ({history_days} days). Emphasising the whole "
            f"window is the same as not emphasising anything.")
    recent_weight = float(win_raw.get("recent_weight", 0.5))
    if emphasis_months and not 0.0 < recent_weight < 1.0:
        raise SpecError("window.recent_weight must be strictly between 0 and 1; "
                        "1.0 would discard the older history the window exists to cover")
    method = str(win_raw.get("method", "weighted"))
    if method not in ("weighted", "half_life", "gate"):
        raise SpecError(f"window.method must be weighted, half_life or gate; got {method!r}")
    # Default the recent floor proportionally: the emphasis window is a fraction
    # of the whole, so demanding the same absolute trade count is unsatisfiable.
    default_recent = max(30, int(round(min_trades * emphasis_days / history_days))) \
        if emphasis_days else min_trades
    min_trades_recent = int(win_raw.get("min_trades_recent", default_recent))
    if emphasis_days and min_trades_recent > min_trades:
        raise SpecError("window.min_trades_recent cannot exceed guardrails.min_trades — "
                        "the emphasis window is a subset of the lookback window")
    window = Window(lookback_years=lookback_years, emphasis_months=emphasis_months,
                    recent_weight=recent_weight, method=method,
                    require_recent_positive=bool(win_raw.get("require_recent_positive", True)),
                    min_trades_recent=min_trades_recent,
                    half_life_days=int(win_raw.get("half_life_days", max(1, emphasis_days))))

    analysis = raw.get("analysis") or {}
    deliverables = list(raw.get("deliverables") or ["pdf", "html_dashboard"])

    return Spec(
        strategy=strategy, sources=sources, history_days=history_days,
        base_signals_per_day=base_rate, timezone=str(data.get("timezone", "America/New_York")),
        axes=axes, grid_min=int(grid.get("target_min", 500)),
        grid_max=int(grid.get("target_max", 800)), seed=int(grid.get("seed", 7)),
        min_trades=min_trades, target_trades=target, oos_fraction=oos,
        session_buckets=list(analysis.get("session_buckets") or []),
        seasonality=list(analysis.get("seasonality") or ["month", "year", "day_of_week"]),
        events=bool(analysis.get("events", True)), window=window,
        deliverables=deliverables, raw=raw,
    )
