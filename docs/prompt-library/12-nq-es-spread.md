# NQ/ES intraday relative value — trading the gap between two indices

**Why this family, and why the Databento file is what makes it possible:** every
other brief in this library bets on direction. This one does not. NQ and ES
track each other closely — both are US large-cap equity indices — but NQ is
tech-concentrated and ES is broad, so the *ratio* between them wanders. It
mean-reverts intraday while trending over months. The trade is the deviation,
not the market.

This needs two instruments' intraday history with **aligned timestamps**, over
the same years, from the same tape. Stitching NQ from one vendor and ES from
another introduces timestamp and session mismatches that manufacture fake
spread dislocations — you end up trading your own data errors. Databento serves
every CME product from one dataset with consistent timestamps, which is exactly
the requirement.

The payoff for the extra complexity: this is **market-neutral**. Its returns
should be close to uncorrelated with every other brief here, which is worth more
to a portfolio of agents than a slightly higher standalone Sharpe.

---

```
## 1. ROLE
You are a quantitative researcher specialising in statistical arbitrage and
relative-value futures strategies. I am not a quant — explain everything in
plain language and define terms on first use, starting with short paragraphs on
what a spread trade is, what market-neutral means, what a z-score is, and why
two correlated instruments can drift apart and come back. Do not ask clarifying
questions: resolve ambiguity with the most defensible reading, state the
assumption, continue. Report failures as prominently as wins.

## 2. INSTRUMENTS
Leg 1: NQ  $20/pt, tick 0.25 = $5.00
Leg 2: ES  $50/pt, tick 0.25 = $12.50
Micros strongly preferred for this family: MNQ ($2/pt, tick $0.50) and
MES ($5/pt, tick $1.25). Micros allow far finer notional balancing between the
legs and cut friction per unit of exposure — with full-size contracts the
minimum position is lumpy enough to leave you meaningfully directional, which
defeats the purpose.
Session: Sun 18:00 - Fri 17:00 ET, halt 17:00-18:00 ET. Both legs share it.

## 3. DATA
data/futures/NQ_v_5m.parquet and data/futures/ES_v_5m.parquet
Pull ES with the same script and the same roll rule:
  python scripts/fetch_databento.py --symbol ES
Coverage ~9 years from 2017-05-22, full 23-hour session, volume-based
continuous roll on both legs.

CHECKS THIS BRIEF LIVES OR DIES ON, before any strategy work:
  - Timestamp alignment. Inner-join the two series and report how many bars
    exist in one leg but not the other. Any material mismatch invalidates the
    spread. Never forward-fill a missing leg to manufacture a bar — drop it.
  - Roll dates. NQ and ES roll on similar but NOT identical schedules. A roll in
    one leg and not the other creates a step change in the ratio that looks
    exactly like a tradeable dislocation and is not one. Identify every roll
    date in both legs and either exclude a window around them or demonstrate
    the back-adjustment handles it. Report which you chose.
  - Confirm both files use the SAME continuous roll rule. Mixing volume-rolled
    NQ with calendar-rolled ES silently corrupts the entire study.

The TradingView tunnel can supply ~4 years of daily bars for regime context
(VIX especially — see section 7). It caps at 1000 bars with no date-range
parameter and cannot supply intraday history.

## 4. CLOCK
5-minute bars, UTC stored, America/New_York reported, DST-aware.
Tag hour, day of week, month, year, and session phase (Asian / London /
pre-market / RTH open / midday / RTH close / post).

## 5. COST MODEL (mandatory — and this is the brief's central difficulty)
YOU PAY FRICTION TWICE. Every entry and exit crosses two spreads and two
commissions:
  Full size: NQ ~$14 RT + ES ~$29 RT = ~$43 per round trip per pair
  Micros:    MNQ ~$2.25 RT + MES ~$4 RT = ~$6.25 per round trip per pair
Spread dislocations worth trading are typically small. At full size the edge
must clear $43, which most intraday spread signals will not. RUN THE ENTIRE
STUDY AT BOTH FULL SIZE AND MICRO SIZE and report them side by side. If a
variant only works on micros, that is a legitimate and useful finding — say so
plainly rather than burying it.
Execution assumption: both legs fill at the NEXT bar's open after a signal on
the close. Model LEG RISK explicitly — in practice the two legs do not fill
simultaneously. Add 1 extra tick of slippage on the ES leg to represent it, and
report how sensitive results are to that assumption.
Report gross, net, and friction as a % of gross. If friction exceeds gross on
most variants, that is the headline of the report.

## 6. SPREAD CONSTRUCTION (settle this before any strategy work)
Test three definitions and carry the best forward, documenting the choice:
  a) Simple ratio:     NQ_price / ES_price
  b) Log ratio:        log(NQ) - log(ES)
  c) Beta-adjusted:    log(NQ) - beta * log(ES), beta from rolling OLS
Beta window: 20 / 60 / 120 days. Beta MUST be estimated only on data prior to
the bar being traded — a beta fitted on the full sample is look-ahead bias and
will produce a beautiful, fictional equity curve.
Position sizing for neutrality: notional per contract = multiplier x price. Size
the legs so notional is balanced, and report the residual directional exposure
each variant actually carries. A "market-neutral" strategy carrying 30% net long
exposure is a directional strategy wearing a disguise — measure it, do not
assume it.
Signal: z-score of the spread against a rolling mean and standard deviation.
Lookback: 20 / 60 / 120 / 240 bars, all computed on prior bars only.

## 7. VARIANT SPACE — 500 variants
  - Entry z-threshold: 1.0 / 1.5 / 2.0 / 2.5 / 3.0
  - Exit: z returns to 0 / 0.5 / opposite threshold; fixed time stop; fixed R
  - Stop: z extends to 3 / 4 / 5 — spread trades have unbounded loss if the
    relationship breaks, so stop policy is not a detail here, it is survival.
  - Lookback windows for mean and standard deviation, as above
  - Spread definition and beta window, as above
  - Session window: all 23 hours independently. Expect RTH to differ sharply
    from overnight, when one leg may be far thinner than the other — thin-leg
    dislocations look like signals and are liquidity artifacts.
  - Time-of-day gating: avoid the first and last 15 minutes, when the legs
    dislocate mechanically on the open and close auctions.
  - Regime gating: VIX level and trend from the TradingView daily pull. The
    NQ/ES relationship behaves differently in stress, and this is where the
    tail risk lives — spend real variant budget here.
  - Event days: FOMC, CPI, NFP. Test inclusion and exclusion.
  - Directional overlay: pure neutral vs a deliberate small tilt, as a control
    that shows how much of any profit is actually neutrality versus beta.
  - Half-life filter: estimate the spread's mean-reversion half-life
    (Ornstein-Uhlenbeck) and trade only when it is short enough for the holding
    period. This is the most theoretically grounded filter in the brief.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological; test touched once.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500; report separately at full size and micro size.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
SPECIFIC TO SPREAD TRADING, all required:
  - COINTEGRATION over time. Run an Engle-Granger or ADF test on the spread per
    year. If NQ and ES stop cointegrating in some years, the strategy has no
    basis in those years and no threshold tuning fixes it. Report the test by
    year.
  - CORRELATION BREAKDOWN is the tail risk. Report performance during the
    largest spread dislocations in the sample (Feb 2018, Mar 2020, Aug 2024,
    Apr 2025). Mean-reversion strategies make small steady gains and then give
    back years in one break. Show the worst single trade, worst day, worst week,
    and the ratio of largest loss to average win. Above ~20, say plainly that
    this is picking up pennies in front of a steamroller.
  - REALISED NEUTRALITY. Report each top variant's beta to ES daily returns. If
    it is not near zero, the strategy is not neutral whatever the construction
    intended.
  - Sharpe assumes symmetry and this distribution is not symmetric. Report
    Sortino alongside and say in the report why Sharpe flatters this family.

## 9. SLICING
Hour of session (all 23, trade counts shown, under 30 suppressed); day of week;
month; year over year INCLUDING the cointegration test per year; VIX decile;
spread-volatility decile; half-life decile; event vs non-event days.

## 10. RANKING
Walk-forward net profit factor AFTER double-leg costs, subject to max drawdown
< 12%, >= 200 trades, largest single loss < 8% of peak equity, AND realised beta
to ES below 0.2. Secondary: net PnL, Sortino (NOT Sharpe as primary), MAR,
expectancy in dollars per pair, win rate, largest-loss / average-win ratio,
friction as a % of gross. Tie-break toward the shallowest tail, not the highest
mean.

## 11. DELIVERABLES
PDF report; self-contained interactive HTML dashboard; 500-variant spaghetti PnL
chart with median and 25/75 bands, top 5 highlighted, full-size and micro-size
results distinguished; per-variant CSV; trade logs; PLUS a time-series chart of
the spread with z-score bands and trades marked, a per-year cointegration table,
and a rolling-correlation chart of NQ against ES so the relationship's stability
is visible rather than assumed.

## 12. HONESTY
Lead with tail risk and with the cost problem, not the equity curve. State
whether results survive full-size friction or only micros. Report realised beta
so the neutrality claim is tested rather than asserted. All assumptions in one
place. Flag suspected overfits even if they rank first. Nothing is tradeable on
a backtest alone.
```
