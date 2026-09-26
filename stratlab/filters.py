"""Filters (confluences).  Each returns (longs allowed, shorts allowed) per bar,
known at the bar's close.  A card's filters must all agree."""
from __future__ import annotations

import inspect
from typing import Callable, Dict, Tuple

import numpy as np

from . import indicators as ind
from .data import Bars, parse_clock

Allowed = Tuple[np.ndarray, np.ndarray]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def trend_ema(B: Bars, n: int = 200) -> Allowed:
    e = ind.ema(B.c, n)
    return B.c > e, B.c < e


def vwap_side(B: Bars) -> Allowed:
    vw, _ = ind.vwap(B)
    return B.c > vw, B.c < vw


def atr_regime(B: Bars, n: int = 14, lookback: int = 500, state: str = "high") -> Allowed:
    a = ind.atr(B, n)
    avg = ind.sma(np.nan_to_num(a), lookback)
    ok = a > avg if state == "high" else a < avg
    return ok, ok


def rel_volume(B: Bars, n: int = 50, min: float = 1.5) -> Allowed:  # noqa: A002
    ok = B.v >= min * ind.prior(ind.sma(B.v, n))
    return ok, ok


def prior_day(B: Bars, mode: str = "with") -> Allowed:
    """Longs after an up day and shorts after a down day (``with``), or the reverse."""
    po, pc = ind.previous_rth(B)
    up, dn = pc > po, pc < po
    return (up, dn) if mode == "with" else (dn, up)


def weekday(B: Bars, skip=("Wed", "Fri")) -> Allowed:
    # weekday of the date a trading day ends on (tday + 1); 1970-01-01 was a Thursday
    wd = (B.tday + 1 + 3) % 7
    ok = ~np.isin(wd, [WEEKDAYS.index(d) for d in skip])
    return ok, ok


def time_window(B: Bars, start: str = "09:30", end: str = "11:30") -> Allowed:
    lo, hi = parse_clock(start), parse_clock(end)
    close = B.tmin + B.tf
    ok = (close > lo) & (close <= hi)
    return ok, ok


FILTERS: Dict[str, Tuple[Callable[..., Allowed], str]] = {
    "trend_ema": (trend_ema, "longs only above the {n} EMA, shorts only below"),
    "vwap_side": (vwap_side, "longs only above the session VWAP, shorts only below"),
    "atr_regime": (atr_regime, "only when ATR({n}) is {state}er than its {lookback}-candle average"),
    "rel_volume": (rel_volume, "only when volume is {min}x its {n}-candle average"),
    "prior_day": (prior_day, "trade {mode} yesterday's 09:30-16:00 direction"),
    "weekday": (weekday, "skips {skip}"),
    "time_window": (time_window, "only signals closing {start}-{end}"),
}


def compute(B: Bars, spec: dict) -> Allowed:
    spec = dict(spec)
    fn, _ = FILTERS[spec.pop("type")]
    return fn(B, **spec)


def describe(spec: dict) -> str:
    spec = dict(spec)
    name = spec.pop("type")
    fn, text = FILTERS[name]
    defaults = {k: v.default for k, v in inspect.signature(fn).parameters.items() if k != "B"}
    vals = {**defaults, **spec}
    if "skip" in vals:
        vals["skip"] = "/".join(vals["skip"])
    return text.format(**vals)

