#!/usr/bin/env bash
# Round 3: Claude's children into five islands, 12 more generations each,
# then the calm-trend v2 island from its structured seeds.
#   strategies/nq2x/round3.sh ISLANDS_INDEX   (the "name run_id" lines run_islands.sh printed)
set -u
cd "$(dirname "$0")/../.."
index="${1:?usage: round3.sh ISLANDS_INDEX}"
for island in trend_plus_dip volume_flush deep_pullback calendar quick_flush; do
  rid=$(awk -v n="$island" '$1 == n {print $2}' "$index")
  python -m evotrader.cli inject "$rid" "strategies/nq2x/children/r3_${island}.json"
  python -m evotrader.cli resume "$rid" --generations 12 > "runs/logs/island_${island}_r3.log" 2>&1
done
python -m evotrader.cli run --config configs/nq_islands/calm_trend_v2.json > runs/logs/island_calm_trend_v2_r3.log 2>&1
