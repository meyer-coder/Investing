#!/usr/bin/env python3
"""Summarise passive-cooler temperature logs.

Reads CSV exports from USB temperature data loggers and reports, per run:

  hold        hours until the payload first exceeds the upper limit (8 C)
  freeze      whether the payload ever dropped below 0 C, and for how long
  in-window   fraction of the run spent inside 2-8 C
  min / max   extremes observed

Usage:
    python3 analyze.py logs/*.csv
    python3 analyze.py --fahrenheit logs/*.csv
    python3 analyze.py --time-col Timestamp --temp-col "Value(C)" logs/*.csv

Stdlib only. See ../SAMPLE_TESTING.md for the protocol these logs come from.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from datetime import datetime
from pathlib import Path

# Refrigerated storage window for GLP-1 pens, insulin and reconstituted
# peptides. Confirm against the labeling of the products your customers
# actually carry before putting any of this in ad copy.
DEFAULT_LO = 2.0
DEFAULT_HI = 8.0

# Below this the payload is destroyed, usually invisibly. Treated as a veto
# rather than a deduction when ranking suppliers.
FREEZE_LIMIT = 0.0

TIME_HEADERS = ("time", "timestamp", "date", "datetime", "recorded")
TEMP_HEADERS = ("temp", "temperature", "value", "celsius", "fahrenheit", "reading")

TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y%m%d %H%M%S",
)


class LogError(Exception):
    """A log file that cannot be read as a temperature run."""


def parse_time(raw: str) -> datetime:
    text = raw.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise LogError(f"unrecognised timestamp {raw!r}")


def find_column(header: list[str], candidates: tuple[str, ...], kind: str) -> int:
    for idx, name in enumerate(header):
        if any(c in name.strip().lower() for c in candidates):
            return idx
    raise LogError(
        f"no {kind} column found in {header!r} - pass --{kind}-col explicitly"
    )


def find_header(rows: list[list[str]]) -> int:
    """Locate the header row.

    Loggers commonly emit several lines of device metadata before the real
    header, so the first row is not reliably it.
    """
    for idx, row in enumerate(rows[:40]):
        lowered = [c.strip().lower() for c in row]
        has_time = any(any(c in cell for c in TIME_HEADERS) for cell in lowered)
        has_temp = any(any(c in cell for c in TEMP_HEADERS) for cell in lowered)
        if has_time and has_temp:
            return idx
    raise LogError("could not locate a header row with time and temperature columns")


def read_log(
    path: Path, time_col: str | None, temp_col: str | None, fahrenheit: bool
) -> list[tuple[datetime, float]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rows = [r for r in csv.reader(fh) if any(cell.strip() for cell in r)]

    if not rows:
        raise LogError("file is empty")

    head_idx = find_header(rows)
    header = rows[head_idx]

    if time_col:
        try:
            t_idx = [c.strip() for c in header].index(time_col)
        except ValueError:
            raise LogError(f"time column {time_col!r} not in {header!r}")
    else:
        t_idx = find_column(header, TIME_HEADERS, "time")

    if temp_col:
        try:
            v_idx = [c.strip() for c in header].index(temp_col)
        except ValueError:
            raise LogError(f"temp column {temp_col!r} not in {header!r}")
    else:
        v_idx = find_column(header, TEMP_HEADERS, "temp")

    readings: list[tuple[datetime, float]] = []
    for row in rows[head_idx + 1 :]:
        if len(row) <= max(t_idx, v_idx):
            continue
        try:
            when = parse_time(row[t_idx])
            value = float(row[v_idx].strip().rstrip("CF°").strip())
        except (LogError, ValueError):
            continue  # trailing summary lines and blank rows
        if fahrenheit:
            value = (value - 32.0) * 5.0 / 9.0
        readings.append((when, value))

    if len(readings) < 2:
        raise LogError("fewer than two usable readings")

    readings.sort(key=lambda r: r[0])
    return readings


def hours_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600.0


def first_sustained(
    readings: list[tuple[datetime, float]],
    predicate,
    debounce: int,
) -> datetime | None:
    """First timestamp beginning `debounce` consecutive matching readings.

    Requiring consecutive samples keeps a single spurious sample - a probe
    brushed by a warm hand, a logger glitch - from ending a run early.
    """
    streak = 0
    start: datetime | None = None
    for when, value in readings:
        if predicate(value):
            if streak == 0:
                start = when
            streak += 1
            if streak >= debounce:
                return start
        else:
            streak = 0
            start = None
    return None


def summarise(
    path: Path,
    readings: list[tuple[datetime, float]],
    lo: float,
    hi: float,
    debounce: int,
) -> dict:
    begin = readings[0][0]
    end = readings[-1][0]
    temps = [v for _, v in readings]

    breach = first_sustained(readings, lambda v: v > hi, debounce)
    freeze = first_sustained(readings, lambda v: v < FREEZE_LIMIT, debounce)

    in_window = sum(1 for v in temps if lo <= v <= hi)
    frozen_samples = sum(1 for v in temps if v < FREEZE_LIMIT)
    duration = hours_between(begin, end)

    return {
        "name": path.stem,
        "samples": len(readings),
        "duration_h": duration,
        "hold_h": hours_between(begin, breach) if breach else None,
        "held_throughout": breach is None,
        "freeze_h": hours_between(begin, freeze) if freeze else None,
        "freeze_frac": frozen_samples / len(temps),
        "in_window_frac": in_window / len(temps),
        "min_c": min(temps),
        "max_c": max(temps),
    }


def render(results: list[dict], lo: float, hi: float) -> None:
    name_w = max([len(r["name"]) for r in results] + [len("run")])

    print()
    print(f"Window {lo:.1f}-{hi:.1f} C   freeze limit {FREEZE_LIMIT:.1f} C")
    print()
    header = (
        f"{'run':<{name_w}}  {'hold':>9}  {'in-win':>7}  "
        f"{'min':>7}  {'max':>7}  {'run len':>8}  flags"
    )
    print(header)
    print("-" * len(header))

    for r in results:
        if r["held_throughout"]:
            hold = f">{r['duration_h']:.1f} h"
        else:
            hold = f"{r['hold_h']:.1f} h"

        flags = []
        if r["freeze_h"] is not None:
            flags.append(f"FROZE @ {r['freeze_h']:.1f} h")
        if r["held_throughout"]:
            flags.append("never breached - extend run")
        if r["duration_h"] < 1:
            flags.append("very short run")

        print(
            f"{r['name']:<{name_w}}  {hold:>9}  "
            f"{r['in_window_frac'] * 100:>6.1f}%  "
            f"{r['min_c']:>6.1f}C  {r['max_c']:>6.1f}C  "
            f"{r['duration_h']:>6.1f} h  {', '.join(flags)}"
        )

    print()

    froze = [r for r in results if r["freeze_h"] is not None]
    if froze:
        print(f"{len(froze)} of {len(results)} runs dropped below "
              f"{FREEZE_LIMIT:.1f} C:")
        for r in froze:
            print(f"  {r['name']}: min {r['min_c']:.1f} C, "
                  f"{r['freeze_frac'] * 100:.0f}% of samples below freezing")
        print()
        print("  A run that freezes the payload is a veto, not a deduction.")
        print("  Retest with a longer gel-pack resting interval before ranking it.")
        print()

    measured = [r for r in results if not r["held_throughout"]]
    if measured:
        worst = min(r["hold_h"] for r in measured)
        claim = (int(worst) // 2) * 2 * 0.8
        print(f"Worst measured hold across these runs: {worst:.1f} h")
        print(f"Defensible advertised claim: {claim:.0f} h  "
              "(rounded down to even hours, x0.8 margin)")
        print("State the ambient temperature alongside it.")
    else:
        print("No run breached the upper limit - runs were too short to")
        print("establish a hold time. Extend to 48 h before claiming anything.")
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("logs", nargs="+", help="logger CSV exports (globs accepted)")
    ap.add_argument("--fahrenheit", action="store_true",
                    help="logger exports F rather than C")
    ap.add_argument("--lo", type=float, default=DEFAULT_LO,
                    help=f"window lower bound, C (default {DEFAULT_LO})")
    ap.add_argument("--hi", type=float, default=DEFAULT_HI,
                    help=f"window upper bound, C (default {DEFAULT_HI})")
    ap.add_argument("--debounce", type=int, default=3,
                    help="consecutive readings needed to count a breach "
                         "(default 3)")
    ap.add_argument("--time-col", help="exact timestamp column name")
    ap.add_argument("--temp-col", help="exact temperature column name")
    args = ap.parse_args(argv)

    paths: list[Path] = []
    for pattern in args.logs:
        expanded = sorted(glob.glob(pattern))
        if expanded:
            paths.extend(Path(p) for p in expanded)
        else:
            # Not a glob, or a shell that already expanded it. Let the open()
            # fail below so the path is reported rather than silently dropped.
            paths.append(Path(pattern))

    results, failed = [], []
    for path in paths:
        try:
            readings = read_log(path, args.time_col, args.temp_col, args.fahrenheit)
            results.append(
                summarise(path, readings, args.lo, args.hi, args.debounce)
            )
        except (LogError, OSError) as exc:
            failed.append((path, exc))

    for path, exc in failed:
        print(f"skipped {path}: {exc}", file=sys.stderr)

    if not results:
        print("no readable logs", file=sys.stderr)
        return 1

    render(results, args.lo, args.hi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
