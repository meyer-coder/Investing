# Gold — macro-release reaction

**Why gold, and why specifically for a fleet:** gold's intraday moves are driven
by real rates and the dollar, which means it reacts hard and fast to a *known
calendar* — CPI, FOMC, NFP, PCE — at precisely scheduled times. Its correlation
to equity-index agents is low and sometimes negative, so a gold agent genuinely
diversifies a fleet rather than adding a correlated copy. That is worth more
than a slightly higher standalone Sharpe.

---

```
## 1. ROLE
Quantitative researcher specialising in intraday macro-sensitive commodities.
I am not a quant — plain language, define terms on first use. Do not ask
clarifying questions; resolve ambiguity with the most defensible reading, state
the assumption, continue. Report failures as prominently as wins.

## 2. INSTRUMENTS
Primary: COMEX:GC1!  100 troy oz. Tick $0.10 = $10.00
Micro:   COMEX:MGC1! 10 troy oz.  Tick $0.10 = $1.00
Spot CFD: OANDA:XAUUSD — 24/5, no roll, but broker-synthetic with tick volume
          only. Use as a CROSS-CHECK, never spliced into the futures curve.
Session: Sun 18:00 ET - Fri 17:00 ET, daily halt 17:00-18:00 ET.
Roll:    GC's active months are G/J/M/Q/V/Z (Feb/Apr/Jun/Aug/Oct/Dec) — SIX
         rolls a year, not four. Volume-crossover roll, Panama back-adjust,
         report every roll date inside the test window.

## 3. DATA — COVERAGE GATE (FIRST)
Target 5 years of 5m bars.
  1. Databento GLBX.MDP3 (COMEX is on Globex) `ohlcv-1m`, aggregate to 5m.
  2. XAUUSD spot from HistData/Dukascopy free archives as a cross-check.
  3. TradingView MCP `bars` for spot-checks only (1000-candle cap, no date range).
Print a data inventory before testing. Gate: < 2 years -> event study only.
Never splice GC futures with XAUUSD spot into a single equity curve.
You also need the RELEASE CALENDAR with timestamps, and ideally consensus vs
actual, for: CPI (08:30 ET), PCE (08:30), NFP (08:30, first Friday), FOMC
statement (14:00) and press conference (14:30), retail sales, PPI, and Treasury
auctions. Without consensus-vs-actual you can study the reaction but not the
surprise — state which you have.

## 4. CLOCK
5m bars, UTC storage, America/New_York reporting, DST-aware.
Tag hour, DOW, month, year, session phase, plus:
  is_cpi_day, is_fomc_day, is_nfp_day, is_pce_day,
  minutes_to_release, minutes_since_release, surprise_magnitude (where available),
  and the London AM (10:30 London) and PM (15:00 London) gold fix times —
  genuine structural liquidity events specific to this market.

## 5. COST MODEL (mandatory)
GC:  $4.00 commission RT + 1 tick ($10) slippage each side = ~$24 RT.
MGC: ~$1.50 RT + 1 tick ($1) each side = ~$3.50 RT.
CRITICAL: at 08:30:00 and 14:00:00 ET the book empties for seconds. Model the
release bar at 5 TICKS of slippage each side, not 1. Run the entire study at
1, 3 and 5 ticks of release-window slippage and show how the ranking changes.
An edge that survives only at 1 tick is a fill fantasy, not a strategy.
Signal on close, fill at NEXT open. Gross and net reported side by side.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: at the 08:35 ET bar close on a CPI day, trade in the
direction of the 08:30-08:35 bar, stop at that bar's opposite extreme, target 2R,
flat by 11:00 ET.

## 7. VARIANT SPACE — 500 variants
  - Release timing: enter at +5m / +10m / +15m / +30m / +60m; follow vs fade the
    initial impulse. The follow-vs-fade question is the core of this brief —
    gold frequently spikes and fully reverses within the hour, and separating
    the cases where it does from where it does not IS the edge.
  - Impulse character: release-bar range vs ATR; close position within the bar's
    range; volume vs average; whether the move broke a prior session level.
  - Surprise conditioning: where consensus data is available, bucket by surprise
    size and sign, and test whether reaction magnitude scales with surprise
    (it should — if it does not in your data, suspect your timestamps).
  - Dollar/rates confluence: DXY and 10Y yield direction at the release. Gold
    moving opposite the dollar is the mechanism; test whether confluence with
    DXY improves the edge. This is the most defensible filter in the brief
    because it encodes the actual causal channel rather than a chart pattern.
  - Non-event baseline: identical logic on non-release days, as the control that
    isolates whether the event matters at all. REQUIRED.
  - Fix-time behaviour: the London AM/PM fixes as their own event family.
  - Trend: EMA 9/21/50/200; higher-timeframe alignment; daily bias.
  - VWAP: session-anchored, plus VWAP anchored to the release bar itself.
  - Session window: all 23 hours. Gold trades meaningfully in Asian hours
    (physical demand) unlike the index futures — test whether that is exploitable.
  - Calendar: DOW, month (gold has genuine seasonal demand patterns around
    Indian wedding season and Chinese New Year — worth testing, with the caveat
    that these are weak effects needing many years to detect), roll week.
  - Risk: stop 1.0/1.5/2.0/3.0 x ATR(14); targets 1R/2R/3R; trailing; time stop.
  - Direction: long / short / both, with asymmetry tested explicitly — gold's
    response to risk-off is not the mirror of its response to risk-on.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500. 1000 Monte Carlo shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
EVENT-SPECIFIC: report the count of each event type in the sample (5 years gives
~60 CPI, ~40 FOMC, ~60 NFP). Below 100 per type, treat conclusions as
provisional and say so. Report every result with the single best and single
worst event removed — if the edge vanishes, it was two data points.
Cross-instrument: validate the top 5 unchanged on XAUUSD spot. An edge present
in GC but not XAUUSD is a futures-microstructure artifact, not a macro edge.

## 9. SLICING
Hour (all 23, counts shown, < 30 suppressed); DOW with event days isolated;
month; year over year; realized-vol decile; DXY-regime split (dollar
strengthening vs weakening); real-yield regime where obtainable.
Named events (2020 COVID, 2022 rate-hike cycle, 2023 banking stress, 2024-25
central-bank buying) as an explicitly underpowered secondary check with n stated.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 20% and >= 80 trades.
Secondary: net PnL, Sharpe, Sortino, MAR, expectancy in ticks and dollars, win
rate, avg win/avg loss, worst single trade, longest losing streak.
Report metrics separately for event-day and non-event-day trades.
ALSO REQUIRED: correlation of the top 5 daily returns against an equity-index
strategy's daily returns. Low correlation is the reason this market is in the
fleet — measure it, do not assume it.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade logs;
plus event-study charts of average cumulative PnL in the 120 minutes around each
release type, with confidence bands, against a non-event-day control.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. Flag suspected overfits even if they rank first. State prominently if an
edge depends on optimistic release-window fills. Nothing is tradeable on a
backtest alone.
```
