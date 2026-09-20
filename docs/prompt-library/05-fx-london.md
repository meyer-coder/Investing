# FX majors — session-boundary breakout (London open)

**Why FX:** the lowest friction of any market in this library, and the cleanest
session structure that exists. The Asian range compresses overnight, London
opens at 03:00 ET and expands it, and the London/NY overlap (08:00-12:00 ET)
carries the day's liquidity peak. That is a *structural, mechanical, daily*
pattern driven by when institutions in different time zones are actually at
their desks — not a statistical artifact. Free tick data back to 2003 makes it
one of the few markets where a twenty-year backtest is genuinely achievable.

---

```
## 1. ROLE
Quantitative researcher specialising in intraday FX. I am not a quant — plain
language, define terms on first use. Do not ask clarifying questions; resolve
ambiguity with the most defensible reading, state the assumption, continue.
Report failures as prominently as wins.

## 2. INSTRUMENTS
Primary:   FX:EURUSD   (deepest, tightest, lowest volatility)
Secondary: FX:GBPJPY   (the classic session-breakout vehicle — far higher range,
                        wider spread; the two together test whether an edge is
                        structural or merely a volatility artifact)
Also test: FX:GBPUSD, FX:USDJPY, FX:AUDUSD
Standard lot 100,000 units. EURUSD pip = 0.0001 = $10/lot.
JPY crosses: pip = 0.01 — a frequent and expensive coding error. Handle pip
scale per pair explicitly and print your pip definitions in the report.
Hours: Sunday 17:00 ET - Friday 17:00 ET, continuous. Daily rollover 17:00 ET.
No central exchange: there is no true volume, only tick count. Never build a
volume-threshold signal here and never compare tick volume across venues.

## 3. DATA — COVERAGE GATE (FIRST)
Target 10+ years of 5m bars. Achievable here, so accept nothing less.
  1. HistData.com — free 1-minute OHLC per pair per month back to ~2000.
     Bulk download and aggregate to 5m. Primary source.
  2. Dukascopy historical tick data — free, back to ~2003, with real bid/ask.
     Use this to MEASURE historical spread rather than assuming it. That single
     step separates a credible FX backtest from a worthless one.
  3. TradingView MCP `bars` for spot-checks only (1000-candle cap, no date range).
Print a data inventory before testing: first/last bar, count, gaps, weekend
boundaries, holiday sessions, and any period where the spread data is missing.
Gate: if you cannot obtain real bid/ask spread history, say so explicitly and
treat every result as an upper bound on achievable performance.

## 4. CLOCK
5m bars, UTC storage, reported in BOTH America/New_York and Europe/London,
DST-aware. FX sessions are defined by local business hours in each financial
centre, and London and New York shift DST on DIFFERENT DATES — for a few weeks
each year the overlap window moves. Handle it properly; most retail backtests
do not, and it silently corrupts the single most important window in this study.
Tag each bar with session:
  Sydney 17:00-02:00 ET | Tokyo 19:00-04:00 ET | London 03:00-12:00 ET
  New York 08:00-17:00 ET | Overlap (London+NY) 08:00-12:00 ET
Tag: asian_range_high, asian_range_low, asian_range_width, minutes_since_london
_open, day of week, month, year.

## 5. COST MODEL (mandatory)
ECN: ~$3.50 per side per standard lot = $7 round turn, PLUS the spread.
Spread: use MEASURED historical spread from tick data where available. Where not:
  EURUSD 0.2 pip typical, 0.1 in the overlap, 1.5+ during Asian hours and in the
  first seconds after a release.
  GBPJPY 1.5 pip typical, 4+ in thin hours.
SPREAD IS TIME-OF-DAY DEPENDENT AND THIS IS THE CENTRAL MODELLING ISSUE IN FX.
A strategy that looks profitable trading the Asian session at overlap spreads is
pure fiction. Charge a session-specific spread, and report each variant's result
at 1x and 2x the assumed spread. If the edge dies at 2x, it does not exist.
Swap/rollover: charge real overnight swap for positions held past 17:00 ET.
Triple swap on Wednesdays (value-date convention). Model it.
Signal on close, fill at NEXT open, at the ask for buys and the bid for sells.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: mark the Asian range (19:00-03:00 ET). On the first
5m close beyond it after 03:00 ET, enter in the breakout direction. Stop at the
opposite side of the range, target 1x range width, flat by 12:00 ET.

## 7. VARIANT SPACE — 500 variants
  - Range definition window: 19:00-03:00 / 20:00-03:00 / 00:00-03:00 ET; also
    the prior day's full range and the prior day's NY-session range.
  - Breakout trigger: first close beyond / close beyond by N pips / close beyond
    by a fraction of ATR / second consecutive close beyond (a slower, cleaner
    confirmation that trades fewer false breaks).
  - Range-width gate: only trade when the Asian range is in the bottom
    30/40/50th percentile of its own 20-day distribution. COMPRESSION PRECEDING
    EXPANSION IS THE CORE PREMISE OF THIS ENTIRE STRATEGY FAMILY — spend a large
    share of your variants here, it is the highest-value axis in the brief.
  - False-break handling: reverse on a failed break vs stand aside vs re-enter once.
  - Session window: all 24 hours independently, and specifically test whether
    the London open is genuinely special or whether NY open (08:00 ET) or the
    Tokyo open (19:00 ET) work as well. This is the seasonality-of-hours question
    and the whole brief hinges on it.
  - Trend: EMA 9/21/50/200 on 5m, 1h daily bias, higher-timeframe alignment.
  - Calendar: day of week (Monday ranges behave differently after the weekend
    gap — isolate it), month, month-end (corporate fixing flows), quarter-end.
  - Events: ECB, BoE, Fed, BoJ rate decisions; NFP; CPI. Test inclusion AND
    exclusion. Also test the London 04:00 ET fix and the 11:00 ET WMR fix.
  - Risk: stop at range-opposite / N pips / ATR multiple; targets 0.5x/1x/2x
    range width; trailing on/off; time stop; flat-by time 10:00/12:00/17:00 ET.
  - Direction: long / short / both.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
FX-SPECIFIC:
  - Cross-pair transfer: fit on EURUSD, test UNCHANGED on GBPUSD, USDJPY,
    AUDUSD, GBPJPY. A session-structure edge SHOULD transfer, because the
    mechanism (when traders are at their desks) is shared. If it does not
    transfer, you have fitted one pair's noise. This is the single most
    informative test in the brief — report it prominently.
  - Regime split: pre-2015 / 2015-2019 / 2020-2021 / 2022+ (the rate-differential
    regime shift materially changed FX behaviour).
  - Report results at 1x and 2x assumed spread, side by side.

## 9. SLICING
Hour (all 24, counts shown, < 30 suppressed); day of week; month; year over
year; Asian-range-width decile; realized-vol decile; spread decile.
Named events (2015 SNB franc de-peg, Brexit 2016, Mar 2020, 2022 BoJ
interventions) as an explicitly underpowered secondary check with n stated.
NOTE on the SNB event: EURCHF moved ~30% in minutes with no liquidity. If you
include CHF pairs, that single day will dominate every statistic. Exclude it
from headline numbers, report it separately, and say why.

## 10. RANKING
Walk-forward net profit factor after spread, commission and swap, subject to
max drawdown < 15% and >= 200 trades. Secondary: net PnL, Sharpe, Sortino, MAR,
expectancy in pips AND dollars, win rate, avg win/avg loss, longest losing
streak, total swap paid. Tie-break toward variants that transfer across pairs.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade logs;
plus a cross-pair transfer matrix (variant x pair, coloured by walk-forward
profit factor) — that matrix is the most decision-relevant chart in this study.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. Flag suspected overfits even if they rank first. State prominently if an
edge depends on optimistic spread assumptions. Nothing is tradeable on a
backtest alone.
```
