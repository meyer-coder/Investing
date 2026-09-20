# Master template — day-trading agent research brief

Fill the `<<ANGLE BRACKETS>>` and paste. Every numbered section exists because
leaving it out causes a specific, known failure. Sections 3, 5, 8 and 10 are the
ones most often omitted and are the ones that decide whether the result is real.

---

```
## 1. ROLE
You are a quantitative researcher specialising in intraday systematic strategies.
I am not a quant — explain findings in plain language, define terms on first use.
Do not ask me clarifying questions. Where the brief is ambiguous, choose the most
defensible interpretation, STATE the assumption in the report, and continue.
Think deeply and take the time you need. Report failures as prominently as wins.

## 2. INSTRUMENT
Primary:   <<EXCHANGE:TICKER>>
Multiplier: <<$X per point>>   Tick: <<0.25 = $5>>
Session:   <<hours, exchange timezone, halts>>
Roll:      <<quarterly H/M/U/Z, back-adjust using Panama method>> (futures only)
Substitutes permitted, in order: <<A, then B>>

## 3. DATA — COVERAGE GATE (do this FIRST, before any backtesting)
Acquire in this order, stopping when you have >= <<N>> years:
  1. <<source 1>>
  2. <<source 2>>
  3. <<source 3>>

Then STOP and print a data inventory BEFORE testing anything:
  - source, symbol, first bar, last bar, total bars
  - bars per session vs expected (flag missing sessions)
  - gaps > 1 bar, duplicate timestamps, zero-volume bars
  - if multiple sources were spliced: the splice timestamps and the price
    discontinuity at each

Then enforce these gates. Do not silently proceed:
  - < 6 months  -> report structure/microstructure only. NO seasonality, NO
                   year-over-year, NO event study. Say so explicitly.
  - < 3 years   -> no month-of-year seasonality claims.
  - Any splice across instrument TYPES (futures <-> CFD <-> ETF) -> report those
    segments SEPARATELY. Never concatenate into one equity curve. Volume-based
    signals must be re-validated per segment, because CFD volume is tick count,
    not contracts.

If you cannot reach the target coverage, say exactly how much you got and which
requested analyses are therefore unanswerable. An honest "insufficient data" is
the correct output. A seasonality chart built on four days is not.

## 4. BAR RESOLUTION AND CLOCK
Resolution: <<5m>>
Store all timestamps UTC. Bucket and report in <<America/New_York>>, DST-aware.
Tag every bar with: session-hour, day-of-week, month, year, and session phase
(<<pre-market / open / midday / close / overnight>>).

## 5. COST MODEL (mandatory — no zero-cost backtests)
Commission: <<$X>> round turn, all-in
Slippage:   <<1 tick>> each side on market orders; <<2 ticks>> in the first and
            last 5 minutes of the session and within 2 minutes of a scheduled
            <<high-impact release>>
Spread:     <<charge explicitly if not already in slippage>>
Financing:  <<overnight/funding, if positions can be held>>
Fills:      signal on bar CLOSE, fill at NEXT bar OPEN. Never fill on the
            signal bar. Stops fill at the worse of stop price and next open.
Report gross AND net side by side, plus total friction paid as a % of gross PnL.
If net < 0 while gross > 0, lead the report with that.

## 6. BASELINE STRATEGY
<<PASTE THE FULL STRATEGY SPEC HERE — entry, exit, stop, target, sizing,
position limits, and any session restriction it imposes.>>
Backtest this EXACTLY as written first. That is the control. Every variant is
measured as a delta against it.

## 7. VARIANT SPACE
Generate <<500>> variants across these dimensions. Vary systematically, not
randomly, and report the variant count per dimension so I can see the grid:
  - Session window:  <<test ALL hours, 24h, even if the baseline restricts it>>
  - Trend filter:    EMA <<9/21/50/200>>, price vs EMA, EMA slope, EMA stack
  - Mean/value:      session-anchored VWAP, VWAP std-dev bands (+/-1, 2)
  - Volume:          relative volume vs same-hour-of-day 20-day average
                     (NOT raw volume — raw volume encodes time of day)
  - Volatility:      ATR percentile regime, realized-vol decile
  - Calendar:        day of week, week of month, month
  - Events:          <<release calendar>> — test inclusion AND exclusion
  - Risk:            stop distance in ATR multiples, R:R target, time stop
  - Direction:       long-only / short-only / both

Rules:
  - Every variant must be a named, reproducible parameter set, dumped to CSV.
  - No variant may use information unavailable at the bar's close. Anchored
    VWAP resets at session open; no forward-looking normalisation; indicator
    warm-up must precede the first trade.
  - Report the count of variants that were DISCARDED for < <<30>> trades.

## 8. VALIDATION (non-negotiable — this is what makes the result mean anything)
Searching 500 variants guarantees an impressive in-sample winner even from pure
noise. Expected best-of-500 t-stat from luck alone is ~3.0. Therefore:
  - Split: train <<50%>> / validation <<25%>> / LOCKED TEST <<25%>>.
    The test set is touched exactly once, at the end, by the top 5 only.
  - Walk-forward: rolling <<12mo>> fit / <<3mo>> out-of-sample, concatenated.
    Walk-forward equity is the headline number, not in-sample equity.
  - Compute the Deflated Sharpe Ratio (Bailey & Lopez de Prado), adjusted for
    the number of trials actually run.
  - Apply Benjamini-Hochberg FDR control across variants.
  - Report the FULL DISTRIBUTION of all <<500>> results: median, quartiles,
    % profitable net of costs. If the median variant loses money, say plainly
    that the top variant is likely selection noise.
  - Run <<1000>> Monte Carlo trade-order shuffles on the top 5; report the 5th
    percentile of terminal equity and max drawdown.
  - Sensitivity: for each top variant, perturb each parameter +/-1 step. A real
    edge degrades gracefully. A parameter cliff is a curve-fit. Show the surface.

## 9. SLICING ANALYSES
For the baseline and the top <<10>> variants, cut results by:
  - Hour of session (every hour, 24h) — with trade count per bucket. Suppress
    any bucket with < <<30>> trades rather than ranking it.
  - Day of week, month of year, year over year (stability, not just average)
  - Volatility regime (realized-vol decile — a CONTINUOUS variable, which has
    thousands of observations, instead of ~8 named historical events)
  - <<Named event windows>> as a secondary, explicitly underpowered check.
    State n. With n < 30, describe; do not claim correlation.

## 10. RANKING OBJECTIVE (state the formula, do not improvise)
Rank by: <<walk-forward net profit factor, subject to max drawdown < X% and
>= 100 trades>>. Report secondary metrics: net PnL, Sharpe, Sortino, MAR,
expectancy per trade in ticks AND dollars, win rate, avg win/avg loss,
longest losing streak, time in market.
Tie-break toward FEWER parameters and SHALLOWER optimisation.

## 11. DELIVERABLES
  1. PDF report — methodology, data inventory, baseline, top variants,
     all slicing tables, validation results, and a "why this might be wrong"
     section written as seriously as the results section.
  2. Interactive HTML dashboard — sortable variant table, equity curves with
     variant toggles, hour/DOW/month heatmaps, drawdown chart, parameter
     sensitivity surface. Self-contained, no external dependencies.
  3. PnL chart of all <<500>> variants: baseline as a bold line, all variants as
     faint spaghetti, median and 25/75 percentile bands shaded, top 5 highlighted.
  4. CSV: one row per variant, all parameters + all metrics.
  5. Trade log CSV for the baseline and top 5.

## 12. HONESTY REQUIREMENTS
  - Lead with what did NOT work and what the data could not answer.
  - List every assumption you made resolving ambiguity, in one place.
  - Flag any result you believe is overfit, even if it ranks first.
  - No result is to be described as tradeable on the basis of a backtest alone.
```

---

## Deployment addendum

Add this when the goal is live capital rather than research. The base template
stops at a ranked table; live trading needs four more things:

```
## 13. PATH TO LIVE
  - Forward paper trade the top <<3>> for <<60>> sessions before any capital.
    Compare live-paper slippage against the modelled slippage and report drift.
  - Correlation matrix of the candidates' DAILY RETURNS. Agents above <<0.7>>
    are one position wearing several hats — allocate to them as one.
  - Sizing: <<fixed fractional, X% risk per trade>>, capped at <<Y>> concurrent
    positions across all agents.
  - Kill switches, defined numerically before going live:
      * daily loss limit <<$X>> -> flatten, stop for the day
      * drawdown exceeding <<1.5x>> backtest max DD -> halt agent, re-examine
      * live win rate outside the backtest 95% CI over <<50>> trades -> halt
      * data feed gap or stale quote -> flatten, do not re-enter
  - Define in advance what evidence would make you RETIRE an agent.
```
