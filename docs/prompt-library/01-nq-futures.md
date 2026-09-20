# NQ E-mini Nasdaq-100 — opening-range momentum

Your original brief, rebuilt on the master template. The substantive changes:
a coverage gate before any testing, an explicit cost model, an out-of-sample
protocol, and a hard ban on splicing futures with CFD data into one curve.

---

```
## 1. ROLE
You are a quantitative researcher specialising in intraday index-futures
strategies. I am not a quant — explain findings in plain language and define
terms on first use. Do not ask me clarifying questions: where this brief is
ambiguous, choose the most defensible interpretation, state the assumption
explicitly in the report, and continue. Think deeply, take the time you need,
and report what failed as prominently as what worked.

## 2. INSTRUMENT
Primary:    CME_MINI:NQ1!  (E-mini Nasdaq-100)
Multiplier: $20 per index point.  Tick 0.25 = $5.00
Session:    Sunday 18:00 ET - Friday 17:00 ET, with a daily halt 17:00-18:00 ET.
            23 hours/day = 276 five-minute bars/session.
Roll:       Quarterly (H/M/U/Z). Roll on volume crossover, back-adjust with the
            Panama method, and report how many roll points fall inside the test
            window.
Substitutes, in strict order: CME_MINI:MNQ1! (micro, same underlying, cheaper
            tick) -> NAS100 CFD (LAST RESORT, see the splice rule in 3).

## 3. DATA — COVERAGE GATE (do this FIRST, before any backtesting)
Target: 5 years of 5-minute bars (~350,000 bars).

Acquire in this order, stopping once the target is met:
  1. TradingView MCP `bars`. BE AWARE: it caps at 1000 candles per call and
     accepts NO date-range argument, only `count`. At 5m that is ~3.6 calendar
     days, roughly 0.3% of one year. Treat it as a live sanity check on
     price levels and session boundaries, NOT as the study dataset.
  2. Databento GLBX.MDP3 (CME Globex) — free signup credit plus free sample
     windows. Use `ohlcv-1m` and aggregate to 5m yourself so you control the
     bar boundaries. Report exactly how many bars the free tier yielded and
     what a full-history pull would cost.
  3. Any other free CME source you can find (state what you used and its
     provenance).
  4. NAS100 CFD, LAST RESORT ONLY.

THEN STOP AND PRINT A DATA INVENTORY before testing anything:
source, symbol, first bar, last bar, total bars, bars-per-session vs the
expected 276, all gaps > 1 bar, duplicate timestamps, zero-volume bars.

Enforce these gates. Do not silently proceed:
  - < 6 months  -> report intraday structure only. NO seasonality, NO
                   year-over-year, NO event study. State this prominently.
  - < 3 years   -> no month-of-year seasonality claims.
  - SPLICE RULE: futures and CFD data must NEVER be concatenated into one
    equity curve. They differ in price level (basis), in hours, and — critically
    — CFD volume is TICK COUNT, not contracts traded. Report CFD segments
    separately and re-validate every volume-based signal inside them. If a
    variant's edge exists only in the CFD segment, say so in bold.

If you cannot reach 5 years, state how much you obtained and which of the
analyses below are therefore unanswerable. "Insufficient data for seasonality"
is a correct and valuable output. A month-by-month chart built on four days is
not — do not produce one.

## 4. BAR RESOLUTION AND CLOCK
5-minute bars. Store UTC, report in America/New_York, DST-aware (the source
data is UTC, the analysis windows are ET, and the offset changes twice a year —
get this wrong and the opening hour smears across two buckets).
Tag every bar with hour, day-of-week, month, year, and session phase:
  Asian 18:00-03:00 | London 03:00-08:00 | Pre-market 08:00-09:30
  Open 09:30-10:30  | Late-morning 10:30-12:00 | Midday 12:00-14:00
  Afternoon 14:00-15:00 | Close 15:00-16:00 | Post 16:00-17:00

## 5. COST MODEL (mandatory)
Commission: $4.00 round turn per contract, all-in (broker + exchange + NFA).
Slippage:   1 tick ($5) each side. 2 ticks each side in 09:30-09:35 and
            15:55-16:00, and within 2 minutes of any scheduled release listed
            in section 9.
Fills:      signal on bar CLOSE, fill at NEXT bar OPEN. Stops fill at the worse
            of the stop price and the next open. No same-bar fills, ever.
Baseline total friction: ~$14 round turn per contract. At 3 trades/day that is
~$10,500/year per contract — often larger than a 5-minute edge. Report gross
and net side by side and show friction as a % of gross PnL. If net is negative
while gross is positive, that is the headline of the report.

## 6. BASELINE STRATEGY
<<PASTE THE FULL STRATEGY SPEC HERE — entry, exit, stop, target, sizing,
position limits, and any session restriction it imposes. This brief cannot be
run without it.>>
Backtest exactly as written first. That is the control; every variant is a
delta against it.

## 7. VARIANT SPACE — 500 variants
Systematic grid, not random sampling. Report the variant count per dimension.
  - Session window: ALL 23 hours tested independently, plus 24h unrestricted.
    If the baseline restricts trading to the open, test that restriction as a
    HYPOTHESIS, not a constraint — I want to know whether the open is genuinely
    special or merely conventional.
  - Trend: EMA 9/21/50/200 on 5m; price vs EMA; EMA slope sign; EMA stack
    alignment; higher-timeframe (15m/1h) EMA agreement.
  - VWAP: session-anchored VWAP (reset 18:00 ET and 09:30 ET — test BOTH
    anchors), plus +/-1 and +/-2 standard-deviation bands.
  - Volume: relative volume against the same-hour-of-day 20-day average.
    NEVER raw volume — raw volume is mostly a proxy for time of day, and a
    filter on it silently becomes a session filter.
  - Volatility: ATR(14) percentile regime; overnight range vs 20-day average;
    opening 5m bar range vs its own 20-day average.
  - Calendar: day of week; first/last trading day of month; monthly opex
    (3rd Friday); quarterly roll week.
  - Events: FOMC, CPI, NFP, PCE, quad witching. Test BOTH inclusion and
    exclusion — "avoid news days" is itself a variant worth measuring.
  - Risk: stop at 0.5/1.0/1.5/2.0 x ATR; targets at 1R/1.5R/2R/3R; time stop
    at 6/12/24/48 bars; breakeven-at-1R on/off.
  - Direction: long-only / short-only / both (NQ has an upward drift — a
    long-only variant may simply be capturing beta, so flag any variant whose
    edge disappears when measured against buy-and-hold over the same window).

Constraints: every variant is a named reproducible parameter set dumped to CSV;
no variant may use information unavailable at that bar's close; anchored VWAP
resets at the session open; indicators must be fully warmed up before the first
trade. Report how many variants were discarded for having < 30 trades.

## 8. VALIDATION (non-negotiable)
Searching 500 variants will produce an impressive in-sample winner even from
pure noise — expected best-of-500 t-stat from luck alone is about 3.0.
  - Split train 50% / validation 25% / LOCKED TEST 25%, chronological. The test
    set is touched once, at the end, by the top 5 only.
  - Walk-forward: 12-month fit, 3-month out-of-sample, rolled and concatenated.
    THE WALK-FORWARD CURVE IS THE HEADLINE, not the in-sample curve.
  - Deflated Sharpe Ratio adjusted for the number of trials actually run.
  - Benjamini-Hochberg FDR control across all variants.
  - Report the FULL DISTRIBUTION of all 500: median, quartiles, and % profitable
    net of costs. If the median variant loses money, state plainly that the top
    variant is probably selection noise.
  - 1000 Monte Carlo trade-order shuffles on the top 5; report 5th-percentile
    terminal equity and max drawdown.
  - Parameter sensitivity: perturb each parameter +/-1 step. A real edge decays
    gracefully; a cliff is a curve-fit. Show the surface for the top 5.

## 9. SLICING ANALYSES
For the baseline and top 10 variants:
  - Hour of session, all 23 hours, with trade count per bucket. Report 09:30-
    10:30 and 10:30-11:30 explicitly as requested, but rank them against every
    other hour rather than assuming they win. Suppress any bucket with < 30
    trades instead of ranking it.
  - Day of week; month of year; year over year (I care about STABILITY across
    years, not the average across years — show me whether one year carries it).
  - Volatility regime as a CONTINUOUS variable: realized-vol decile and relative
    volume decile. This is the statistically sound version of "find events that
    increase volume", because it yields thousands of observations.
  - Named event windows — COVID crash (Feb-Mar 2020), 2022 rate-hike cycle,
    Aug 2024 yen-carry unwind, Apr 2025 tariff selloff, and any others you
    identify from the volume data itself — as a SECONDARY, explicitly
    underpowered check. State n for each. With n < 30, describe the behaviour;
    do not claim a correlation.

## 10. RANKING OBJECTIVE
Rank by walk-forward net profit factor, subject to max drawdown < 15% and at
least 100 trades. Secondary metrics: net PnL, Sharpe, Sortino, MAR, expectancy
per trade in BOTH ticks and dollars, win rate, avg win / avg loss, longest
losing streak, and time in market. Tie-break toward fewer parameters.

## 11. DELIVERABLES
  1. PDF report — methodology, data inventory, baseline, top variants, all
     slicing tables, validation results, and a "why this might be wrong"
     section written as seriously as the results.
  2. Self-contained interactive HTML dashboard — sortable variant table, equity
     curves with toggles, hour/DOW/month heatmaps, drawdown chart, sensitivity
     surfaces.
  3. PnL chart of all 500 variants: baseline bold, all variants as faint
     spaghetti, median and 25/75 percentile bands shaded, top 5 highlighted.
  4. CSV: one row per variant, all parameters and all metrics.
  5. Trade logs for baseline and top 5.

## 12. HONESTY REQUIREMENTS
Lead with what did not work and what the data could not answer. Collect every
ambiguity-resolving assumption in one place. Flag any result you believe is
overfit even if it ranks first. Do not describe anything as tradeable on the
strength of a backtest alone.
```
