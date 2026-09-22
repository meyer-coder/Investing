"""Variation grid: turn a handful of axes into 500-800 concrete strategies.

A full cartesian product almost never lands in the target band, so this module
does two things the honest way: it reports the true product size, and when it
has to reduce it says so and reduces by seeded random subsampling rather than
by truncating (truncation would drop whole axis values and quietly bias the
comparison).
"""
from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .spec import Axis, AxisValue, Spec


@dataclass
class Variation:
    index: int
    choices: Dict[str, str]          # axis name -> value label
    selectivity: float               # product of pass rates
    trades_per_day: float
    attainable_trades: int
    required_days: int
    feasible: bool
    attainable_recent: int = 0
    feasible_recent: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {"index": self.index, "choices": dict(self.choices),
                "selectivity": round(self.selectivity, 6),
                "trades_per_day": round(self.trades_per_day, 4),
                "attainable_trades": self.attainable_trades,
                "required_days": self.required_days, "feasible": self.feasible,
                "attainable_trades_recent": self.attainable_recent,
                "feasible_recent": self.feasible_recent}


@dataclass
class Grid:
    variations: List[Variation]
    full_product: int
    reduced: bool
    axis_sizes: Dict[str, int]

    @property
    def feasible(self) -> List[Variation]:
        return [v for v in self.variations if v.feasible]

    @property
    def infeasible(self) -> List[Variation]:
        return [v for v in self.variations if not v.feasible]

    @property
    def feasible_both(self) -> List[Variation]:
        """Variations that clear the full-window floor AND the emphasis-window floor."""
        return [v for v in self.variations if v.feasible and v.feasible_recent]


def _combos(axes: List[Axis]) -> itertools.product:
    return itertools.product(*[ax.values for ax in axes])


def build_grid(spec: Spec) -> Grid:
    axes = spec.axes
    axis_sizes = {ax.name: len(ax.values) for ax in axes}
    full = math.prod(axis_sizes.values())

    combos: List[Tuple[AxisValue, ...]] = list(_combos(axes))
    reduced = False
    if full > spec.grid_max:
        rng = random.Random(spec.seed)
        combos = rng.sample(combos, spec.grid_max)
        reduced = True

    variations: List[Variation] = []
    for i, combo in enumerate(combos):
        selectivity = math.prod(v.pass_rate for v in combo)
        per_day = spec.base_signals_per_day * selectivity
        attainable = int(per_day * spec.history_days)
        required = math.ceil(spec.min_trades / per_day) if per_day > 0 else 10**9
        emph = spec.window.emphasis_days
        recent = int(per_day * emph)
        variations.append(Variation(
            index=i,
            choices={ax.name: v.label for ax, v in zip(axes, combo)},
            selectivity=selectivity, trades_per_day=per_day,
            attainable_trades=attainable, required_days=required,
            feasible=attainable >= spec.min_trades,
            attainable_recent=recent,
            feasible_recent=(not emph) or recent >= spec.window.min_trades_recent,
        ))
    return Grid(variations=variations, full_product=full, reduced=reduced,
                axis_sizes=axis_sizes)


def grid_notes(spec: Spec, grid: Grid) -> List[str]:
    """Human-readable warnings about the grid's size, before anything is run."""
    notes: List[str] = []
    shape = " x ".join(f"{n}({k})" for n, k in grid.axis_sizes.items())
    notes.append(f"axes: {shape} = {grid.full_product} combinations")
    if grid.reduced:
        notes.append(
            f"full product {grid.full_product} exceeds the {spec.grid_max} ceiling, so the "
            f"grid was reduced to {len(grid.variations)} by seeded random subsampling "
            f"(seed={spec.seed}); axis balance is preserved in expectation, and the same "
            f"seed reproduces the same grid")
    elif grid.full_product < spec.grid_min:
        short = spec.grid_min - grid.full_product
        best = max(grid.axis_sizes, key=lambda k: grid.axis_sizes[k])
        notes.append(
            f"full product {grid.full_product} is {short} short of the {spec.grid_min} floor. "
            f"Add values to an axis (largest is '{best}') or add an axis; "
            f"do NOT pad with duplicates")
    else:
        notes.append(f"{len(grid.variations)} variations, inside the "
                     f"{spec.grid_min}-{spec.grid_max} band, no reduction needed")
    return notes
