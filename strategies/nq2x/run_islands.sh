#!/usr/bin/env bash
# Round 2: run every NQ 2x island in configs/nq_islands (generation 0 from its
# seed file in strategies/nq2x/seeds); one log per island.
set -u
cd "$(dirname "$0")/../.."
mkdir -p runs/logs
round="${1:-r2}"
for cfg in configs/nq_islands/*.json; do
  name=$(basename "$cfg" .json)
  [ "$name" = "calm_trend_v2" ] && continue          # round 3, see round3.sh
  python -m evotrader.cli run --config "$cfg" > "runs/logs/island_${name}_${round}.log" 2>&1
  echo "$name $(grep -m1 -o 'run-[0-9-]*-[0-9a-f]*' "runs/logs/island_${name}_${round}.log")"
done
