#!/usr/bin/env bash
# Rebuild the minute data the NQ breakout bot's studies read (strategies/sweeps/:
# data.py, sweeps.py, bot.py, funded.py). A fresh container has none of it; it
# is git-ignored and re-downloadable.
#
#   bash scripts/rebuild-bot-data.sh        # about an hour at Dukascopy's pace, about 85 MB
#
# Resumable: months already on disk are skipped, so a rerun after an
# interruption only fetches what is missing. The paper runs do not need any of
# this; they read data/intraday/ and data/levels/ (in git) and fetch the rest live.
set -euo pipefail

cd "$(dirname "$0")/.."

today="$(date -u +%F)"
# the Nasdaq-100 to August 2020 (strategies/sweeps/data.py switches to months_wide/ after)
python3 strategies/quick/indexes.py 2013-01-01 2020-08-31 USATECH
# the S&P 500 and the Dow, 2013 on
python3 strategies/quick/indexes.py 2013-01-01 "$today" USA500 USA30
# the Nasdaq-100 from September 2020, 07:00 New York on
python3 strategies/mnq/duka.py 2020-09-01 "$today"
# the session arrays, data/cache/quick/sweep_<NQ|ES|YM>.npz
python3 - <<'PY'
import sys
sys.path.insert(0, "strategies/sweeps")
from data import load
for inst in ("NQ", "ES", "YM"):
    D = load(inst)
    print(inst, len(D["dates"]), "sessions,", D["dates"][0], "to", D["dates"][-1])
PY
