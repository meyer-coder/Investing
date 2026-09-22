# Forward-test ledger

Every signal from `signals` after the 22 September 2026 close, taken or
not, with the fill and the exit. One row per position. Slot sizes are the
4%-daily-limit sizes from the README unless noted.

Weekly check: `python -m evotrader.cli evaluate profitable-strategies/all.json --config configs/quick_names_long.json --test-frac 0 --since 2026-09-23 --refresh`

| signal date | strategy | fund | signal close | taken? | fill date | fill price | slot | exit date | exit price | exit reason | P&L $ | P&L % | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-09-22 | Squeeze Days (evolved) | MUU | 38.92 | | 2026-09-23 | | 13% | | | | | | squeeze breakout: vol ratio 0.59, close above the upper band 37.19 |
