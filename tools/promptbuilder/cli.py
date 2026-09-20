"""Build a backtest prompt and its variation manifest from a strategy spec.

    python3 -m promptbuilder.cli tools/promptbuilder/specs/example.yaml -o build/
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .feasibility import assess
from .grid import build_grid, grid_notes
from .render import render
from .spec import SpecError, load_spec


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate a backtest prompt from a strategy spec.")
    p.add_argument("spec", help="path to the strategy spec YAML")
    p.add_argument("-o", "--out-dir", default="build/prompts", help="output directory")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    try:
        spec = load_spec(args.spec)
    except SpecError as exc:
        print(f"spec rejected: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"no such spec: {args.spec}", file=sys.stderr)
        return 2

    grid = build_grid(spec)
    report = assess(spec, grid)

    os.makedirs(args.out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.spec))[0]
    manifest_path = os.path.join(args.out_dir, f"{stem}.variations.json")
    prompt_path = os.path.join(args.out_dir, f"{stem}.prompt.md")

    manifest = {
        "strategy": spec.strategy.name,
        "instrument": spec.strategy.instrument,
        "timeframe": spec.strategy.timeframe,
        "generated_from": args.spec,
        "grid": {"full_product": grid.full_product, "emitted": len(grid.variations),
                 "reduced": grid.reduced, "seed": spec.seed,
                 "axis_sizes": grid.axis_sizes},
        "guardrails": {"min_trades": spec.min_trades,
                       "oos_fraction": spec.oos_fraction,
                       "bonferroni_alpha": report.stats.bonferroni_alpha,
                       "expected_max_t_under_null": report.stats.expected_max_t},
        "feasibility": {"feasible": report.n_feasible, "infeasible": report.n_infeasible,
                        "history_days": report.history_days},
        "variations": [v.to_dict() for v in grid.variations],
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    text = render(spec, grid, report, spec_path=args.spec, manifest_path=manifest_path)
    with open(prompt_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    if not args.quiet:
        for note in grid_notes(spec, grid):
            print(f"  grid: {note}")
        print(f"  sample: {report.n_feasible}/{report.n_total} variations reach "
              f"{spec.min_trades} trades on {report.history_days} days "
              f"({report.history_years:.1f}y)")
        if report.n_infeasible:
            print(f"  sample: worst case needs {report.worst_required_days} days "
                  f"({report.years_needed_for_all:.1f}y) — reported as insufficient")
        print(f"  stats: E[max t] under null = {report.stats.expected_max_t:.2f}, "
              f"Bonferroni alpha = {report.stats.bonferroni_alpha:.2e}")
        print(f"  wrote: {prompt_path}")
        print(f"  wrote: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
