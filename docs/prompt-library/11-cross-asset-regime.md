# Cross-asset regime conditioning — when a setup works, not what the setup is

**Why this family needs BOTH sources, and neither alone:** every other brief in
this library hunts for a better entry trigger. This one assumes the trigger is
already fine and asks a different question — *under what macro conditions does it
work, and under what conditions does it quietly bleed?*

The reason intraday strategies decay is rarely that the pattern stopped existing.
It is that the regime changed: rates started moving, the dollar turned, credit
widened, volatility repriced. The same opening-range breakout is a good trade in
one regime and a coin flip in another.

Answering this needs two things at once:

- **The TradingView tunnel** serves 1000 **daily** bars — about 4 years — for
  *any* symbol, one call each. So DXY, VIX, bonds, credit, gold and sector ETFs
  are all reachable. That is the macro state.
- **The Databento file** supplies 5-minute NQ for execution.

Neither does this alone. The tunnel cannot give intraday history; the futures
file is a single instrument with no macro context. Together they answer a
question neither can touch, and that is the whole reason this brief exists.

The deliverable is **not a new strategy**. It is a map of when your existing
strategies should be switched on.

---

```
## 1. ROLE
You are a quantitative researcher specialising in macro regime classification
and its effect on intraday strategy performance. I am not a quant — plain
language, define every term on first use, including what a "regime" is and why
a strategy's edge can be conditional on one. Do not ask clarifying questions:
resolve ambiguity with the most defensible reading, state the assumption,
continue. Report failures as prominently as wins.

## 2. INSTRUMENT
Execution:  NQ. $20/pt, tick 0.25 = $5.00. Session Sun 18:00 - Fri 17:00 ET.
Context basket (daily bars, via the TradingView tunnel):
  TVC:VIX        equity volatility
  TVC:DXY        US dollar
  CME_MINI:ES1!  broad market, for the NQ/ES ratio (tech leadership)
  CBOT:ZN1!      10-year note — the rates channel
  NYMEX:CL1!     energy / inflation impulse
  COMEX:GC1!     the risk-off and real-rate channel
  AMEX:HYG, AMEX:LQD   credit spread proxy
  NASDAQ:QQQ, AMEX:SPY, AMEX:IWM   breadth and size rotation

## 3. DATA
Execution layer: data/futures/NQ_v_5m.parquet, ~9 years from 2017-05-22.

Context layer: the TradingView MCP tunnel, `bars(symbol, "1D", count=1000)`.
MEASURED LIMITS, verify before relying on them: `count` is hard-clamped at 1000
(a request for 5000 returns 1000 and reports "1000 bars", with no error), and
there is NO date-range parameter — every call returns the most recent bars, so
history cannot be paged backwards. 1000 daily bars reaches back ~4 years.

THAT ASYMMETRY DEFINES THIS STUDY. The execution data spans ~9 years; the macro
context spans ~4. So:
  - The regime-conditioned analysis runs on the most recent ~4 years only.
  - The earlier ~5 years is your OUT-OF-SAMPLE CHECK — apply the regime rules
    learned on the recent window to the older window using any context you can
    reconstruct from the futures data itself (realized vol, NQ/ES ratio if you
    pull ES from Databento too).
  - Say plainly in the report that regime conclusions rest on ~4 years, which
    covers a limited number of genuine regime shifts.
If the tunnel is unreachable, say so and fall back to context features derivable
from the futures files alone. Do not silently proceed with fewer features.

Print a data inventory before testing: per context symbol, first/last bar,
bar count, missing days, and the overlap window shared with the execution data.

## 4. CLOCK
Execution on 5m bars, UTC stored, America/New_York reported, DST-aware.
Context on daily bars. JOIN RULE, and this is the one that will silently ruin
the study if you get it wrong: a trading day's intraday decisions may only use
context computed from bars that CLOSED BEFORE that session began. Today's VIX
close cannot gate today's 10:00 entry. Lag every context feature by one full
session and state the lag in the report.

## 5. COST MODEL (mandatory)
NQ: $4.00 commission RT + 1 tick ($5) each side = ~$14 RT; 2 ticks each side in
09:30-09:35, 15:55-16:00, and within 2 minutes of a scheduled release.
Signal on close, fill at NEXT open. Gross and net side by side.
Note a specific trap here: a regime filter that cuts trade count by 70% also
cuts total costs by 70%. Some of the apparent improvement is simply trading
less. Always report a control that trades the same REDUCED number of times on
randomly chosen days, so filter skill is separated from lower turnover.

## 6. BASELINE STRATEGY
<<PASTE A SIMPLE, ALREADY-UNDERSTOOD STRATEGY HERE. An opening-range breakout is
ideal. It does NOT need to be profitable — a mediocre baseline is arguably
better, because the question is whether regime conditioning can rescue it.>>
If none is supplied, use: buy the break of the 09:30-10:00 ET range, stop at the
opposite side, target 2R, flat by 16:00. Short the mirror image.
Backtest this unconditionally first. That is the control, and every regime
variant is measured as a delta against it.

## 7. VARIANT SPACE — 500 variants
Vary the FILTER, not the trigger. The trigger stays fixed throughout, which is
what makes the comparison clean.

  VOLATILITY REGIME
  VIX level deciles; VIX 5-day change; VIX vs its own 20-day average; realized
  vol of NQ vs implied (VIX) — the variance risk premium, which is a genuinely
  different signal from VIX level alone.

  RATES
  ZN direction and 5/20-day momentum; rate of change. Tech is a long-duration
  asset, so NQ's sensitivity to the rates channel is a real mechanism rather
  than a data-mined coincidence — expect this to be one of the stronger filters
  and give it a generous share of variants.

  DOLLAR
  DXY trend and momentum; DXY vs 50-day average.

  LEADERSHIP AND BREADTH
  NQ/ES ratio trend — is tech leading or lagging? IWM/SPY for size rotation.
  These say what KIND of market it is, not just how volatile.

  CREDIT
  HYG/LQD ratio, its trend and rate of change. Credit often turns before
  equities, which makes it a leading rather than coincident filter.

  COMPOSITE
  Simple scores combining 2-4 of the above. Test AND vs OR combinations and
  report how many variants survive as complexity rises — a composite that needs
  five conditions to fire is usually curve-fitting, and the count makes that
  visible.

  CROSS-CUTTING
  Filter direction: trade only in regime X / avoid regime X / flip direction in
  regime X. Filter strictness: top decile vs top tercile vs above-median.
  Also condition on day of week and month, as a deliberate NOISE CONTROL —
  calendar filters have no macro mechanism, so if they score as well as the
  macro filters, the macro results are noise and the report must say so.

## 8. VALIDATION (non-negotiable, and this brief is unusually easy to fool)
Train 50% / validation 25% / LOCKED TEST 25%, chronological; test touched once.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500 variants.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
SPECIFIC TO REGIME WORK, all required:
  - REGIME COUNT, not trade count, is the real sample size. Four years contains
    perhaps 3-6 genuine regime shifts. A filter fitted to two of them is fitted
    to two observations however many trades it touches. Report the number of
    distinct regime EPISODES each filter identifies and treat anything under 5
    as anecdote.
  - The turnover control from section 5 is mandatory, not optional.
  - Report the baseline's performance INSIDE and OUTSIDE each regime, with trade
    counts for both. A filter that helps only by removing three catastrophic
    days is a tail-risk filter, not an edge filter — say which it is.
  - Apply the winning filters to the older ~5 years of futures data using
    self-derived context. Survival there is the strongest evidence available.

## 9. SLICING
For the baseline and top 10 filtered variants: performance by each context
variable's decile; by year; by month; by VIX regime; by rates regime. Show the
baseline's full-sample equity curve with regime periods shaded — the visual
either shows losses clustering in identifiable regimes or it does not.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 15%, >= 100 trades,
AND at least 5 distinct regime episodes. Secondary: net PnL, Sharpe, Sortino,
MAR, expectancy, win rate, trade count retained vs baseline, and improvement
over the random-days turnover control. Tie-break toward filters with a stated
economic mechanism over ones that merely fit.

## 11. DELIVERABLES
PDF report; self-contained interactive HTML dashboard; 500-variant spaghetti PnL
chart with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade
logs; PLUS a regime-shaded equity curve and a heatmap of baseline performance
across context-variable deciles — that heatmap is the actual product of this
study and belongs on the report's first page.

## 12. HONESTY
Lead with what failed and what the data could not answer. State the ~4-year
context limit prominently, not in a footnote. Report regime-episode counts
alongside trade counts everywhere. If the calendar noise controls score as well
as the macro filters, say so in the opening paragraph. Nothing is tradeable on
a backtest alone.
```
