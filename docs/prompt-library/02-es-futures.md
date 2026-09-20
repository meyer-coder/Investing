# ES E-mini S&P 500 — VWAP mean reversion

**Why a separate brief from NQ:** ES is not "NQ with smaller numbers." It has a
materially deeper book, a wider mega-cap-weighted composition, and empirically
more intraday mean reversion where NQ trends. A fleet running the same momentum
logic on both owns one position twice. Run ES as a *reversion* programme so it
diversifies rather than duplicates.

---

```
## 1. ROLE
Quantitative researcher, intraday index futures. I am not a quant — plain
language, define terms on first use. Do not ask clarifying questions; resolve
ambiguity with the most defensible reading, state the assumption, continue.
Report failures as prominently as wins.

## 2. INSTRUMENT
Primary:    CME_MINI:ES1!   Multiplier $50/pt.  Tick 0.25 = $12.50
Micro:      CME_MINI:MES1!  Multiplier $5/pt.   Tick 0.25 = $1.25
Session:    Sun 18:00 ET - Fri 17:00 ET, daily halt 17:00-18:00 ET. 276 5m bars/day.
Roll:       Quarterly H/M/U/Z, volume-crossover roll, Panama back-adjustment.
Note:       ES is quoted 1 tick wide almost continuously in RTH. That tight
            spread is the entire reason a reversion strategy is viable here and
            marginal on NQ — but the tick is worth $12.50, so a 1-tick round
            trip is $25. Reversion strategies take many small trades; friction
            dominates. Model it before you get excited by any result.

## 3. DATA — COVERAGE GATE (FIRST, before any backtest)
Target 5 years of 5m bars (~350,000).
  1. Databento GLBX.MDP3 `ohlcv-1m`, aggregate to 5m yourself. Primary source.
  2. TradingView MCP `bars` — caps at 1000 candles, NO date range parameter.
     ~3.6 days at 5m. Sanity check only, never the dataset.
  3. Any other free CME source; state provenance.
Print a data inventory (source, first/last bar, count, bars-per-session vs 276,
gaps, duplicates, zero-volume bars) and STOP for review before testing.
Gates: < 6 months -> intraday structure only, no seasonality/YoY/event study.
       < 3 years  -> no month-of-year claims.
Never splice futures with CFD or SPY data into one equity curve.

## 4. CLOCK
5m bars, stored UTC, reported America/New_York, DST-aware. Tag hour, DOW,
month, year, session phase (Asian / London / pre-market / open / late-morning /
midday / afternoon / close / post).

## 5. COST MODEL (mandatory)
ES: $4.00 commission RT + 1 tick ($12.50) slippage each side = ~$29 RT.
MES: ~$1.50 commission RT + 1 tick ($1.25) each side = ~$4 RT.
Add 1 extra tick each side in 09:30-09:35, 15:55-16:00, and within 2 minutes of
a scheduled release.
Signal on close, fill at NEXT open. Stops fill at the worse of stop and next open.
Report gross and net side by side, plus friction as a % of gross PnL.
A reversion strategy targeting 4 ticks that pays 2 ticks of friction needs a
~67% win rate just to break even. Compute and display that break-even win rate
for every variant — it is the most honest single number in this study.

## 6. BASELINE
<<PASTE STRATEGY SPEC — entry, exit, stop, target, sizing, position limits.>>
If you have no baseline, use this control: fade a move of >= 1.5 session-VWAP
standard deviations, target VWAP, stop at 2x ATR(14), flat by 15:55 ET.

## 7. VARIANT SPACE — 500 variants
  - VWAP anchor: 18:00 ET (globex) vs 09:30 ET (cash). Test both — they diverge
    materially on gap days and this alone is a meaningful variant axis.
  - Band entry: 1.0 / 1.5 / 2.0 / 2.5 / 3.0 sigma. Target: VWAP / 0.5 sigma /
    opposite band.
  - Reversion gate: only fade when ADX < threshold, or when price is inside the
    prior day's value area, or when the opening drive has already failed.
    Reversion strategies die on trend days — the filter that identifies a trend
    day IS the strategy. Spend variants here.
  - Trend veto: EMA 50/200 alignment on 5m and 15m; veto fades against a stacked
    higher-timeframe trend.
  - Volume: relative volume vs same-hour-of-day 20-day average (never raw).
  - Prior-day levels: prior high/low/close, overnight high/low, initial balance
    (first 60 min) high/low.
  - Session window: all 23 hours independently plus 24h. Reversion is expected
    to work best midday and worst at the open — TEST that, do not assume it.
  - Calendar: DOW, opex Friday, month end, roll week, FOMC/CPI/NFP days both
    included and excluded.
  - Risk: stop 1.0/1.5/2.0/3.0 x ATR; time stop 6/12/24 bars; scale-out on/off.
  - Direction: long-only / short-only / both.
No look-ahead: VWAP resets at the anchor, indicators warmed up, no forward
normalisation. Discard variants with < 30 trades and report the count.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological, test touched once.
Walk-forward 12mo fit / 3mo OOS, concatenated — this is the headline curve.
Deflated Sharpe adjusted for trial count. Benjamini-Hochberg FDR across variants.
Report the full distribution of all 500 (median, quartiles, % profitable net).
1000 Monte Carlo trade-order shuffles on the top 5; report 5th-percentile
terminal equity and max drawdown. Parameter sensitivity +/-1 step with surfaces.
SPECIFIC TO REVERSION: report the worst single trade and the worst day for every
top variant. Reversion strategies show smooth equity curves and then give it all
back in one trend day. A high Sharpe here means less than it does elsewhere —
say so, and show the tail.

## 9. SLICING
Hour of session (all 23, trade count shown, buckets < 30 trades suppressed);
DOW; month; year-over-year stability; realized-vol decile and relative-volume
decile as CONTINUOUS regime variables; named event windows as an explicitly
underpowered secondary check with n stated.
Add: performance on the 20 largest trend days in the sample, identified by
close-to-open range vs ATR. This is the failure mode; quantify it.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 12% and >= 150 trades
and worst-single-day loss < 3% of equity. Secondary: net PnL, Sharpe, Sortino,
MAR, expectancy in ticks and dollars, break-even win rate vs actual win rate,
longest losing streak. Tie-break toward fewer parameters.

## 11. DELIVERABLES
PDF report; self-contained interactive HTML dashboard; 500-variant spaghetti PnL
chart with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade
logs for baseline and top 5.

## 12. HONESTY
Lead with what failed and what the data could not answer. Collect all
assumptions in one place. Flag suspected overfits even if they rank first.
Nothing is tradeable on a backtest alone.
```
