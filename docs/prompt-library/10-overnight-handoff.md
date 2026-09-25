# Overnight session handoff — pricing what happened while the cash market slept

**Why this family, and why it needs the Databento file:** NQ trades 23 hours a
day. The US cash market trades 6.5. That leaves roughly 17 hours in which Asia
opens, Europe opens, European data prints, and overnight news arrives — all of
it transacted in the futures while equity traders are asleep. The 09:30 ET open
is the moment the largest pool of capital arrives and either ratifies that
overnight pricing or rejects it.

That handoff is only visible if your data covers the overnight session. The
TradingView tunnel gives **regular hours only** for equities (measured:
13:30-19:55 UTC), so this family is unreachable there. The Databento file covers
the full Globex session, which is exactly what this needs.

Distinct from the FX brief (`05`): that one trades the London breakout as it
happens. This one treats the entire overnight session as a **predictor** of what
the New York session will do — a different question with a different mechanism.

---

```
## 1. ROLE
You are a quantitative researcher specialising in intraday index futures and
session structure. I am not a quant — plain language, define terms on first use.
Do not ask clarifying questions: resolve ambiguity with the most defensible
reading, state the assumption, continue. Report failures as prominently as wins.

## 2. INSTRUMENT
Primary:    NQ. $20/pt, tick 0.25 = $5.00
Also test:  ES — ES is broader and less tech-concentrated, and the two often
            disagree overnight. That disagreement is itself a signal (see 7).
Session:    Sun 18:00 ET - Fri 17:00 ET, halt 17:00-18:00 ET.
Continuous contract already volume-rolled in the data file; confirm roll dates.

## 3. DATA
Primary:  data/futures/NQ_v_5m.parquet  (and ES for the cross-check)
Coverage: ~9 years from 2017-05-22, full 23-hour session — the overnight bars
are the entire point, so verify they are present before anything else.

Context layer: the TradingView MCP tunnel serves 1000 daily bars (~4 years) per
call, one call per symbol. Pull daily bars for DXY, VIX and a bond proxy to tag
overnight macro regime. It caps at 1000 bars with no date-range parameter, so it
cannot supply intraday history.

Print a data inventory BEFORE testing, and include a check this family lives or
dies on: bars present per session in EACH sub-window (Asian, London,
pre-market, RTH). If overnight bars are thin or missing for a period, the whole
premise collapses for that period — find out now, not after 500 backtests.

## 4. CLOCK
5-minute bars, UTC storage, America/New_York reporting, DST-aware. This brief is
unusually sensitive to DST: London and New York change on different dates, so for
a few weeks each year the European session sits an hour differently relative to
the US open. Handle it properly.
Sub-sessions:
  Asian      18:00-03:00 ET
  London     03:00-08:00 ET
  Pre-market 08:00-09:30 ET
  RTH        09:30-16:00 ET
  Post       16:00-17:00 ET

## 5. COST MODEL (mandatory)
NQ: $4.00 commission RT + 1 tick ($5) each side = ~$14 RT. Two ticks each side
in 09:30-09:35 and 15:55-16:00 and within 2 minutes of a scheduled release.
IMPORTANT: overnight liquidity is materially thinner. For any entry between
20:00 and 03:00 ET, charge 2 ticks of slippage each side, not 1. A strategy that
only works with RTH-quality fills at 01:00 ET does not work.
Signal on close, fill at NEXT open. Gross and net reported side by side.

## 6. FEATURES TO BUILD FIRST
Per session, computed from bars already closed:
  overnight_high, overnight_low, overnight_range, overnight_range / ATR20
  overnight_volume, overnight_volume / 20-day average
  gap = RTH open - prior RTH close, in points and in ATR units
  london_direction  = sign(London close - London open)
  asian_direction   = sign(Asian close - Asian open)
  sessions_agree    = london_direction == asian_direction
  open_location     = RTH open vs overnight high/low/midpoint
  initial_balance   = high/low of 09:30-10:30 ET
  ib_vs_on_range    = initial balance width / overnight range
  es_nq_divergence  = sign difference between ES and NQ overnight moves

## 7. VARIANT SPACE — 500 variants
Three sub-families, ranked separately:

  FAMILY A — GAP FILL vs CONTINUATION
  The core question: does the RTH session reject or ratify the overnight move?
  Bucket by gap size (0-0.25 / 0.25-0.5 / 0.5-1.0 / >1.0 ATR) and test fill and
  continuation in each. Expect the answer to INVERT across buckets — small gaps
  fill, large gaps run — and report each bucket separately rather than fitting
  one rule across all of them. Finding the crossover point is the edge.

  FAMILY B — OVERNIGHT RANGE AS THE DAY'S FRAME
  Treat overnight high/low as levels. Test: break and go after 09:30; fade the
  first touch from inside; require the break to hold N bars; condition on
  overnight range being narrow (compressed) vs wide (already expanded).

  FAMILY C — SESSION AGREEMENT AND DIVERGENCE
  Does it matter whether Asia and London moved the same way? Test entries gated
  on agreement, on disagreement, and on ES/NQ overnight divergence — when the
  two indices disagree overnight, one of them is usually wrong by lunchtime, and
  which one is a testable question rather than a slogan.

  CROSS-CUTTING
  - Entry timing: at the open / +5m / +15m / +30m / after the initial balance
    completes at 10:30.
  - Overnight volume as a conviction filter: high overnight volume means real
    business was done, not just thin drift.
  - Day of week: Monday carries the weekend gap and behaves differently —
    isolate it rather than pooling it.
  - Event days: FOMC, CPI, NFP. Overnight positioning ahead of an 08:30 release
    is a distinct regime; test inclusion and exclusion.
  - Macro regime from the TradingView daily pull: VIX level, DXY direction.
  - Risk: stops at overnight extreme / ATR multiples; targets 1R/2R/3R; flat-by
    11:00 / 12:00 / 16:00 ET.
  - Direction: long / short / both, tested for asymmetry.

No look-ahead: the overnight session must be COMPLETE before any RTH decision
uses it. Any feature referencing 09:30-16:00 data cannot gate a 09:30 entry.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological; test touched once.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500, per family.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
SPECIFIC TO THIS FAMILY: this is a once-per-day setup, so ~9 years gives about
2,250 opportunities before any filtering. Once bucketed by gap size AND
day of week AND regime, cells empty out fast. Report the trade count for EVERY
cell and suppress any under 30 rather than ranking it. Sample exhaustion is the
most likely way this brief produces a false positive.
Cross-instrument: validate the top 5 unchanged on ES.

## 9. SLICING
Gap-size bucket; open-location bucket; day of week; month; year over year;
overnight-range decile; overnight-volume decile; VIX regime; event vs non-event
days. Hour-of-day is less relevant here since entries cluster at the open —
report entry-timing variants instead.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 15% and >= 120 trades.
Secondary: net PnL, Sharpe, Sortino, MAR, expectancy in points and dollars,
win rate, avg win/avg loss, worst single trade, longest losing streak.
Tie-break toward fewer parameters and toward transfer to ES.

## 11. DELIVERABLES
PDF report; self-contained interactive HTML dashboard; 500-variant spaghetti PnL
chart with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade
logs; PLUS a chart of average RTH path conditioned on gap-size bucket, with
confidence bands — that single chart is the whole thesis, visible or refuted.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. Report cell trade counts prominently. Flag suspected overfits even if they
rank first. Nothing is tradeable on a backtest alone.
```
