# CL WTI Crude Oil — scheduled-event reaction

**Why crude:** the highest ATR% of the liquid futures, and a *hard weekly
catalyst* — the EIA petroleum status report, Wednesdays 10:30 ET — that produces
a volume and volatility spike at a known time, every week, for decades. Most
"event edges" suffer from tiny sample sizes. This one gives you ~52 events a
year, ~260 in five years. That is enough observations to actually test.

---

```
## 1. ROLE
Quantitative researcher, intraday commodity futures. I am not a quant — plain
language, define terms on first use. Do not ask clarifying questions; resolve
ambiguity with the most defensible reading, state the assumption, continue.
Report failures as prominently as wins.

## 2. INSTRUMENT
Primary:    NYMEX:CL1!   1,000 barrels. Tick $0.01 = $10.00
Micro:      NYMEX:MCL1!  100 barrels.   Tick $0.01 = $1.00
Session:    Sun 18:00 ET - Fri 17:00 ET, daily halt 17:00-18:00 ET.
Roll:       MONTHLY, not quarterly — expiry ~3 business days before the 25th of
            the month prior to delivery. This is the single most common modelling
            error in crude backtests: 12 roll points a year, not 4. Roll on
            volume crossover, Panama back-adjust, and report every roll date
            falling inside the test window.
Warning:    Crude has had negative settlement prices (April 2020). Any code
            assuming price > 0, or using percentage returns near zero, will
            produce nonsense across that window. Handle it explicitly or
            exclude it and say you did.

## 3. DATA — COVERAGE GATE (FIRST)
Target 5 years of 5m bars.
  1. Databento GLBX.MDP3 (NYMEX is on Globex) `ohlcv-1m`, aggregate to 5m.
  2. TradingView MCP `bars` — 1000-candle cap, NO date range. Sanity check only.
Print a full data inventory and STOP before testing.
Gates: < 2 years -> no seasonality claims (crude seasonality is real but needs
years to separate from trend). < 6 months -> event study only, no calendar work.

## 4. CLOCK
5m bars, UTC storage, America/New_York reporting, DST-aware.
Tag hour, DOW, month, year, and these crude-specific flags:
  is_eia_day (Wednesday, or Thursday when Monday is a holiday — GET THIS RIGHT,
  the report shifts on holiday weeks and a naive "Wednesday" filter will
  mislabel roughly 8 events a year)
  minutes_to_eia, minutes_since_eia
  is_api_day (Tuesday 16:30 ET private inventory estimate)
  is_opec_meeting, is_roll_week, is_expiry_week

## 5. COST MODEL (mandatory)
CL:  $4.00 commission RT + 1 tick ($10) slippage each side = ~$24 RT.
MCL: ~$1.50 RT + 1 tick ($1) each side = ~$3.50 RT.
CRITICAL: at 10:30:00 ET on EIA day the book thins and gaps. Model slippage in
the 10:30-10:35 bar at 5 TICKS each side, not 1. A strategy that appears to
print money by entering at the release is almost always an artifact of
unrealistic fills. Run the whole study at 1, 3 and 5 ticks of release-window
slippage and show how the ranking changes. If the edge only survives at 1 tick,
it does not exist.
Signal on close, fill at NEXT open. Gross and net reported side by side.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: at the 10:35 ET bar close on EIA day, trade in the
direction of the 10:30-10:35 bar, stop at that bar's opposite extreme, target 2R,
time stop 12 bars.

## 7. VARIANT SPACE — 500 variants
  - Event timing: enter at release+5m / +10m / +15m / +30m; fade vs follow the
    initial move; wait for a pullback to the release bar's midpoint.
  - Pre-positioning: enter before 10:30 based on the prior 60m drift (test it,
    and expect it to fail — this is the variant most likely to be a fill fantasy).
  - Release-bar character: range vs ATR, volume vs average, close position
    within the bar's range (a close near the extreme implies continuation).
  - API cross-check: whether Tuesday's API print agreed in sign with Wednesday's
    EIA. Disagreement historically implies a larger move. Genuinely interesting.
  - Non-event baseline: the same logic on non-EIA days, as the control that
    isolates whether the event matters at all. REQUIRED.
  - Trend: EMA 9/21/50/200; higher-timeframe alignment; daily trend direction.
  - VWAP: session-anchored, plus a VWAP anchored to the 10:30 release itself.
  - Session window: all 23 hours. Crude's London/US overlap (03:00-11:00 ET) is
    its liquidity core — test whether the edge lives there.
  - Calendar: DOW, month (crude has genuine seasonal demand patterns), roll
    week, expiry week, OPEC meeting proximity.
  - Risk: stop 1.0/1.5/2.0/3.0 x ATR(14); targets 1R/2R/3R; trailing on/off;
    time stop 6/12/24/48 bars.
  - Direction: long / short / both. Test asymmetry explicitly — crude's
    response to bullish vs bearish surprises is not symmetric.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological.
Walk-forward 12mo/3mo, concatenated — the headline curve.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500 variants, not just the top.
1000 Monte Carlo shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
EVENT-SPECIFIC: report the number of EIA events in the sample. Below 100, treat
every event conclusion as provisional and say so. Also report the result with
the single best and single worst event REMOVED — if the edge disappears, it was
two data points wearing a strategy costume.

## 9. SLICING
Hour of session (all 23, counts shown, < 30 suppressed); DOW with EIA day
isolated; month of year; year over year; realized-vol and relative-volume
deciles as continuous regime variables; performance conditioned on inventory
surprise magnitude where you can obtain consensus vs actual.
Named events (2020 negative prices, 2022 Russia invasion, OPEC cut
announcements) as an explicitly underpowered secondary check with n stated.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 20% and >= 80 trades.
Secondary: net PnL, Sharpe, Sortino, MAR, expectancy in ticks and dollars, win
rate, avg win/avg loss, worst single trade, longest losing streak.
Report every metric separately for EIA-day trades and non-EIA-day trades.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade logs;
plus an event-study chart of average cumulative PnL in the 60 minutes around
10:30 ET, with confidence bands, EIA days vs non-EIA days.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. Flag suspected overfits even if they rank first. State prominently if the
edge depends on optimistic release-window fills. Nothing is tradeable on a
backtest alone.
```
