"""The strategy card: the same fields for every strategy, with defaults.

    family, settings      the signal and its settings (signals.FAMILIES)
    market, tf            e.g. NAS100, 15 (minutes)
    session               when a signal may fire (SESSIONS)
    direction             both, long or short
    entry                 market | limit_pullback(frac, cancel_bars) | stop(ticks, cancel_bars)
    stop                  atr(mult, n) | signal_bar(ticks) | pct(pct)
    target                r(mult) | atr(mult, n) | level | none
    trailing              none | breakeven(at_r) | atr(mult, n, after_r)
    partial               none | take(frac, at_r)
    time_stop_bars        out after this many candles (null: none)
    max_trades_day        filled trades a day
    filters               confluences, all must agree (filters.FILTERS)
    flat                  New York time everything is closed by (Topstep: 16:10)
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Dict, List, Tuple

from . import filters as flt
from . import signals as sig
from .data import MARKETS, market, parse_clock

SESSIONS: Dict[str, Tuple[str, str, str]] = {
    "asia": ("20:00", "00:00", "Asia (signals 20:00-00:00 ET)"),
    "london": ("02:00", "05:00", "London (signals 02:00-05:00 ET)"),
    "ny_am": ("09:30", "12:00", "New York morning (signals 09:30-12:00 ET)"),
    "ny_pm": ("12:00", "15:30", "New York afternoon (signals 12:00-15:30 ET)"),
    "ny": ("09:30", "15:30", "New York (signals 09:30-15:30 ET)"),
    "ldn_ny_am": ("02:00", "12:00", "London and New York morning (signals 02:00-12:00 ET)"),
    "all": ("18:00", "15:30", "all sessions (signals 18:00-15:30 ET)"),
}

DEFAULTS = {
    "family": None,
    "settings": {},
    "market": "NAS100",
    "tf": 15,
    "session": "ny",
    "direction": "both",
    "entry": {"type": "market"},
    "stop": {"type": "atr", "mult": 1.0, "n": 14},
    "target": {"type": "r", "mult": 1.0},
    "trailing": {"type": "none"},
    "partial": {"type": "none"},
    "time_stop_bars": None,
    "max_trades_day": 2,
    "filters": [],
    "flat": "15:55",
}
ENTRY = {"market": {}, "limit_pullback": {"frac": 0.5, "cancel_bars": 10}, "stop": {"ticks": 1, "cancel_bars": 3}}
STOP = {"atr": {"mult": 1.0, "n": 14}, "signal_bar": {"ticks": 1}, "pct": {"pct": 0.3}}
TARGET = {"r": {"mult": 1.0}, "atr": {"mult": 1.0, "n": 14}, "level": {}, "none": {}}
TRAILING = {"none": {}, "breakeven": {"at_r": 1.0}, "atr": {"mult": 2.0, "n": 14, "after_r": 0.0}}
PARTIAL = {"none": {}, "take": {"frac": 0.5, "at_r": 1.0}}


def _part(value: dict, table: dict, what: str) -> dict:
    kind = value.get("type")
    if kind not in table:
        raise ValueError(f"{what}: type must be one of {sorted(table)}, not {kind!r}")
    extra = set(value) - {"type"} - set(table[kind])
    if extra:
        raise ValueError(f"{what} {kind}: unknown settings {sorted(extra)}")
    return {"type": kind, **table[kind], **{k: v for k, v in value.items() if k != "type"}}


def normalize(spec: dict) -> dict:
    """The card with every default filled in; raises ValueError on a bad field."""
    unknown = set(spec) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown card fields {sorted(unknown)}")
    s = copy.deepcopy(DEFAULTS)
    s.update(copy.deepcopy(spec))
    if s["family"] not in sig.FAMILIES:
        raise ValueError(f"family must be one of {sorted(sig.FAMILIES)}, not {s['family']!r}")
    if s["market"] not in MARKETS:
        raise ValueError(f"market must be one of {sorted(MARKETS)}")
    if s["tf"] not in (1, 3, 5, 15, 30, 60):
        raise ValueError("tf must be 1, 3, 5, 15, 30 or 60 minutes")
    if s["session"] not in SESSIONS:
        raise ValueError(f"session must be one of {sorted(SESSIONS)}")
    if s["direction"] not in ("both", "long", "short"):
        raise ValueError("direction must be both, long or short")
    s["entry"] = _part(s["entry"], ENTRY, "entry")
    s["stop"] = _part(s["stop"], STOP, "stop")
    s["target"] = _part(s["target"], TARGET, "target")
    s["trailing"] = _part(s["trailing"], TRAILING, "trailing")
    s["partial"] = _part(s["partial"], PARTIAL, "partial")
    for f in s["filters"]:
        if f.get("type") not in flt.FILTERS:
            raise ValueError(f"filter type must be one of {sorted(flt.FILTERS)}")
    if s["max_trades_day"] < 1:
        raise ValueError("max_trades_day must be at least 1")
    parse_clock(s["flat"])
    if parse_clock(s["flat"]) > parse_clock("16:10"):
        raise ValueError("flat must be by 16:10 New York time (Topstep's rule)")
    return s


def key(spec: dict) -> str:
    """A short fingerprint of the normalized card."""
    return hashlib.sha1(json.dumps(normalize(spec), sort_keys=True).encode()).hexdigest()[:10]


def _fmt_settings(d: dict) -> str:
    return ", ".join(f"{k} = {v}" for k, v in d.items()) or "defaults"


def card(spec: dict) -> List[Tuple[str, str]]:
    """The card as (field, text) rows, in plain words."""
    s = normalize(spec)
    m = market(s["market"])
    e, st, tg, tr, pa = s["entry"], s["stop"], s["target"], s["trailing"], s["partial"]
    tf = f"{s['tf']}m"
    if e["type"] == "market":
        entry = "market order at the next candle's open"
    elif e["type"] == "limit_pullback":
        entry = (f"limit order at a {e['frac'] * 100:.0f}% pullback into the signal candle, cancelled if not "
                 f"filled within {e['cancel_bars']} candles (price must trade through it)")
    else:
        entry = f"stop order {e['ticks']} tick(s) beyond the signal candle, cancelled after {e['cancel_bars']} candles"
    if st["type"] == "atr":
        stop = f"{st['mult']} x ATR({st['n']}) of the {tf} candles"
    elif st["type"] == "signal_bar":
        stop = f"{st['ticks']} tick(s) beyond the signal candle"
    else:
        stop = f"{st['pct']}% from the entry"
    if tg["type"] == "r":
        target = f"{tg['mult']}R (the stop distance x {tg['mult']})"
    elif tg["type"] == "atr":
        target = f"{tg['mult']} x ATR({tg['n']})"
    elif tg["type"] == "level":
        target = "the family's own level (the average or the previous close it fades toward)"
    else:
        target = "none"
    if tr["type"] == "breakeven":
        trailing = f"stop to breakeven once +{tr['at_r']}R"
    elif tr["type"] == "atr":
        trailing = f"{tr['mult']} x ATR({tr['n']}) behind the best price, from +{tr['after_r']}R"
    else:
        trailing = "none"
    partial = f"take {pa['frac'] * 100:.0f}% off at +{pa['at_r']}R" if pa["type"] == "take" else "none"
    return [
        ("Signal", f"{s['family'].replace('_', ' ')}: {sig.describe(s['family'], s['settings'])}"),
        ("Family settings", _fmt_settings(sig.settings_of(s["family"], s["settings"]))),
        ("Market", f"{s['market']} on {tf} candles (traded as {m.contract})"),
        ("Direction", {"both": "long and short", "long": "long only", "short": "short only"}[s["direction"]]),
        ("Entry", entry),
        ("Stop", stop),
        ("Target", target),
        ("Trailing", trailing),
        ("Partial", partial),
        ("Time stop", f"out after {s['time_stop_bars']} candles" if s["time_stop_bars"] else "none"),
        ("Session", SESSIONS[s["session"]][2]),
        ("Daily flat", f"flat by {s['flat']} ET every day"),
        ("Max trades/day", str(s["max_trades_day"])),
        ("Filters", "; ".join(flt.describe(f) for f in s["filters"]) or "none"),
    ]


def short_filters(spec: dict) -> str:
    fs = normalize(spec)["filters"]
    return "+".join(f["type"] for f in fs) or "-"
