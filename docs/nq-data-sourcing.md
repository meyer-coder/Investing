# How deep can NQ 5-minute history actually go?

Measured against the TradingView feed on 2026-09-22, not estimated. Every number
below came from a direct `get_bars` call.

## The cap is per-symbol and anchored to now

| Request | Result |
|---|---|
| `NQ1!` 5m, `bars=250000` | 5,798 bars — ≈1 month |
| `NQ1!` 5m, `bars=1000` | exactly 1,000 bars, still ending at the present |
| `NQ1!` 15m | 5,413 bars — ≈3 months |
| `NQ1!` 60m | 10,154 bars — ≈1.7 years |
| `CFI:US100` (CFD) 5m | 5,779 bars — ≈1 month |

Two things follow. The cap is a **bar count** (~5.3–5.8k below hourly, ~10k
hourly), not a date — which is why 15m reaches three times further back than 5m
for the same bar budget. And `bars` is only a ceiling: the window always ends at
the present, and the tool exposes no `from`/`to` anchor, so **you cannot
paginate backwards through one symbol.** Asking repeatedly returns the same
recent window.

The CFD rung is worth noting separately: it returns the same one month as the
future, so as a fallback for *depth* it buys nothing. It is a fallback for
*availability* only.

## Expired contracts are individually addressable — this is the batching route

Each quarterly contract keeps its own history, capped the same way but anchored
to **its expiry** rather than to today:

| Symbol | Bars | Span |
|---|---|---|
| `CME_MINI:NQZ2022` | 5,333 | 2022-11-20 → 2022-12-16 |
| `CME_MINI:NQZ2023` | 5,335 | 2023-11-19 → 2023-12-15 |
| `CME_MINI:NQZ2024` | 5,335 | 2024-11-24 → 2024-12-20 |
| `CME_MINI:NQU2025` | 5,369 | 2025-08-24 → 2025-09-19 |
| `CME_MINI:NQZ2025` | 5,201 | 2025-11-23 → 2025-12-19 |

Stable back to at least 2022. So history *can* be batched — across contract
symbols, not across pages.

## What stitching actually buys

Each contract yields ~5,335 bars ≈ **19 trading days** (the month before expiry).
Four expiries a year:

| Stitched | Bars | Trading days | Share of the calendar span |
|---|---|---|---|
| 4 quarterlies (1 year) | 21,340 | 77 | 31% |
| 12 quarterlies (3 years) | 64,020 | 232 | 31% |
| 20 quarterlies (5 years) | 106,700 | 387 | 31% |

Against the 576-variation example grid at a 400-trade floor:

| Data | Variations clearing the floor |
|---|---|
| `NQ1!` continuous only (~1 month) | **0 / 576** |
| 12 quarterlies stitched (3-year span) | 16 / 576 |
| 20 quarterlies stitched (5-year span) | 112 / 576 |
| True continuous 3 years (purchased) | **304 / 576** |

Stitching moves the needle off zero, which is not nothing. It does not get near
what the programme needs.

## The structural problem stitching cannot fix

The covered windows are always the ~26 days before a March, June, September or
December expiry. So coverage by calendar month is:

```
Jan  ---- NO DATA AT ALL        Jul  ---- NO DATA AT ALL
Feb  #### covered               Aug  #### covered
Mar  #### covered               Sep  #### covered
Apr  ---- NO DATA AT ALL        Oct  ---- NO DATA AT ALL
May  #### covered               Nov  #### covered
Jun  #### covered               Dec  #### covered
```

**A third of the calendar is permanently invisible, and adding more years never
fixes it** — more years add more Februaries, never a January. Any month-to-month
seasonality built on stitched data is not merely thin for Jan/Apr/Jul/Oct, it is
empty, and the remaining months are all expiry-adjacent, which is itself an
unusual volume regime. Stitched data is therefore usable as a **regime
robustness check** (does the edge survive 2022's bear, 2023–24's rally,
2025–26?) and unusable as the basis for a seasonality claim.

## The four options, ranked

1. **Start accumulating forward today.** The MCP server reads from a local store
   that `evotrader tv-fetch` fills. A scheduled weekly pull grows true
   continuous 5-minute history from now on — six months from now you have six
   real months, gap-free. Free, and worth starting whatever else is decided.
   *(Unverified from here: that the store persists and dedupes across fetches.
   Confirm on the machine running the tunnel before relying on it.)*
2. **Run the 3-year window at 60-minute.** Free, continuous, no gaps, full
   seasonal coverage. A different and slower question than the 5-minute one, but
   an honest one, and available right now.
3. **Stitch the quarterlies** as a regime robustness check, never as the primary
   backtest and never for seasonality.
4. **Buy the history.** Databento GLBX.MDP3 or equivalent — the only route to
   true continuous multi-year 5-minute data, and the only one that gets the full
   grid to 304/576.

These are not exclusive: 2 and 1 together cost nothing and answer most of the
question while the data for 4 accumulates or is purchased.
