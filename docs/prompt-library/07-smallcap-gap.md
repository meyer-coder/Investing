# US small-cap equities — cross-sectional gap-and-go

**Why this market:** the largest per-trade moves available to a retail account.
A low-float small cap with a catalyst can move 20-200% in a session, so the edge
per trade dwarfs anything in futures or FX. And unlike every other brief here,
the *opportunity set regenerates daily* — a screener produces a fresh candidate
list every morning, which suits an agent fleet unusually well.

**Why it is last in build order:** this is the hardest brief in the library to
backtest honestly. Four biases will destroy your results if unaddressed, and
three of them are invisible unless you look for them. Read section 3 carefully.
If you cannot satisfy the delisted-securities requirement, run a different brief.

---

```
## 1. ROLE
Quantitative researcher specialising in cross-sectional intraday equity
strategies. I am not a quant — plain language, define terms on first use. Do not
ask clarifying questions; resolve ambiguity with the most defensible reading,
state the assumption, continue. Report failures as prominently as wins.
Be especially rigorous about survivorship and liquidity bias — in this market
they are the difference between a real result and a fantasy.

## 2. UNIVERSE (selected daily, not a fixed ticker list)
Each trading day, from PRE-MARKET data only:
  - Price $1-$20 (below $1 is delisting/manipulation territory; above $20 the
    percentage moves compress)
  - Gap >= 10% vs prior close
  - Pre-market volume >= 100,000 shares
  - Float < 50M shares where obtainable (low float is the mechanism — it is why
    these moves are violent; without float data, proxy with shares outstanding
    and say that you did)
  - Listed on NASDAQ or NYSE. NO OTC — fills are unmodellable there.
  - Has an identifiable catalyst where obtainable (news, earnings, FDA, offering)
Take the top N by pre-market dollar volume as that day's candidates.
EVERY FILTER MUST USE ONLY DATA AVAILABLE BEFORE 09:30 ET. Selecting on the
day's closing price or full-day volume is look-ahead bias, and it is the single
most common error in published gap-and-go backtests. It will make a losing
strategy look spectacular.

## 3. DATA — COVERAGE GATE (FIRST, AND THIS IS THE HARD PART)
Target 3+ years, 5m bars (plus 1m for the opening 30 minutes), pre-market included.
  1. Polygon.io — free/cheap tier, full intraday history INCLUDING pre-market
     and INCLUDING delisted tickers. The delisted coverage is the critical
     feature; most sources silently omit it.
  2. Alpaca market data as a cross-check.
  3. TradingView MCP `bars` for spot-checks only (1000-candle cap, no date range).

FOUR BIASES, ALL OF WHICH MUST BE ADDRESSED EXPLICITLY IN THE REPORT:
  a) SURVIVORSHIP — the universe MUST include tickers that have since been
     delisted, reverse-split or acquired. Small-cap pump candidates delist at a
     high rate. A universe of today's listed tickers systematically excludes the
     ones that went to zero, and inflates long-side results enormously.
     If your data source cannot supply delisted securities, STOP and say so.
     Do not proceed with a survivorship-biased universe and caveat it in a
     footnote — the result would be worse than no result.
  b) LIQUIDITY — a backtest will happily "fill" 10,000 shares of a stock that
     traded 2,000 that bar. Cap every simulated fill at 1% of that bar's actual
     volume and report how many signals were rejected for insufficient liquidity.
     That rejection count is a headline number, not a footnote.
  c) HALTS — LULD volatility halts are frequent and material here. You cannot
     trade through one, and prices gap across them. Detect halts (a gap in
     bars during RTH, or an anomalous price jump) and model the inability to
     exit. Report how many trades were affected.
  d) BORROW — short selling requires locate, and hard-to-borrow fees on these
     names run 10-300% annualised. If you test short variants, charge a borrow
     cost and flag those where locate would plausibly have been unavailable.
     An unborrowable short is not a trade.
Print a data inventory before testing: candidate-days, unique tickers, % of
tickers now delisted, bars per ticker-day, missing pre-market coverage, halts.

## 4. CLOCK
5m bars (1m for 09:30-10:00), UTC storage, America/New_York reporting, DST-aware.
Sessions: pre-market 04:00-09:30 | open 09:30-10:00 | morning 10:00-12:00 |
midday 12:00-14:00 | afternoon 14:00-15:30 | close 15:30-16:00 | post 16:00-20:00
Tag gap %, pre-market volume, pre-market high/low, float, catalyst type, DOW,
month, year.

## 5. COST MODEL (mandatory, and larger here than anywhere else in this library)
Commission: $0.005/share, $1 minimum, both sides.
SEC/TAF fees on sales. Borrow cost on shorts, per above.
Spread: MEASURED from the data where possible, not assumed. These names run
0.3-1.5% wide, and the spread WIDENS exactly when you most want to exit.
Slippage: 0.5% of price in the 09:30-09:35 window; 0.25% thereafter; 1.0% on any
bar whose volume exceeds 5x its average. These are large numbers and they are
realistic — a 20% winner that pays 1.5% round-trip friction is still excellent,
but a 2% scalp is not viable here at all. Demonstrate that distinction.
Signal on bar close, fill at NEXT bar open, capped at 1% of that bar's volume.
Report gross and net side by side, plus friction as a % of gross PnL.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: on the first 5m close above the pre-market high after
09:30, buy; stop at the 09:30-09:35 bar low; target 2R; flat by 11:00 ET.

## 7. VARIANT SPACE — 500 variants
  - Entry trigger: break of pre-market high / break of the first 5m bar high /
    break of the first 15m range / pullback to VWAP after an initial drive.
  - Gap-size bucket: 10-20% / 20-50% / 50-100% / >100%. Behaviour differs
    sharply across these, and a single rule for all of them is almost certainly
    wrong. Report each bucket separately.
  - Float bucket: <5M / 5-20M / 20-50M / >50M. Float is the mechanism; this is
    the highest-value axis in the brief.
  - Catalyst type: earnings / FDA / offering / merger / no identifiable news.
    "No news" gaps behave differently and are often the best fades.
  - Relative volume: pre-market volume vs the ticker's own 20-day average.
  - Direction: LONG the break vs SHORT the fade. The short side is where the
    statistical edge historically lives — these moves overextend and revert —
    but it is also where borrow and halt risk live. Test both, and be explicit
    that a profitable short variant may be untradeable in practice.
  - Time of day: open drive / late-morning continuation / afternoon fade /
    the 15:30-16:00 close ramp. All tested independently.
  - Position in range: distance from pre-market high, from VWAP, from prior close.
  - Risk: stop at the opening-bar low / N% / ATR multiple; targets 1R/2R/3R;
    trailing; time stop; flat-by 10:00/11:00/12:00/16:00.
  - Position sizing: fixed dollar / fixed risk / volatility-scaled. In a universe
    this heterogeneous, sizing is itself a strategy dimension, not a detail.
  - Candidates per day: top 1 / 3 / 5 / 10 by pre-market dollar volume.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological.
Walk-forward 12mo/3mo, concatenated — the headline.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500. 1000 Monte Carlo shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
CROSS-SECTIONAL SPECIFICS:
  - Report the distribution of per-trade returns, not just the mean. This market
    produces extreme right tails; a strategy whose entire profit comes from 3
    trades out of 400 is a lottery ticket, however good the Sharpe looks. Show
    the result with the top 1% of trades removed. That single number is the most
    honest statistic in this study.
  - Concentration: what % of total PnL comes from the top 10 trades, and from
    the top 5 tickers? High concentration means low reliability.
  - Report the liquidity-rejection rate and the halt-affected trade count as
    headline figures.
  - Bootstrap by DAY, not by trade — trades on the same day are highly correlated
    and per-trade bootstrapping will overstate your confidence badly.

## 9. SLICING
Time of day (all buckets, counts shown, < 30 suppressed); DOW; month; year over
year; gap-size bucket; float bucket; catalyst type; market-regime split (VIX
decile — small-cap speculation is strongly regime-dependent, and this study will
likely show the edge concentrated in high-retail-participation periods).
Named regimes (Jan 2021 meme squeeze, 2022 bear, 2023-24 recovery) as an
explicitly underpowered secondary check with n stated. Note specifically whether
the edge is concentrated in 2021 — if so, this is a bull-market-retail-mania
strategy, not a general edge, and the report must lead with that.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 25%, >= 200 trades,
AND top-10-trade PnL concentration < 50%. Secondary: net PnL, Sharpe, Sortino,
MAR, expectancy in % and dollars, win rate, avg win/avg loss, worst single trade,
longest losing streak, liquidity-rejection rate.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade logs;
plus a per-trade return distribution histogram and a PnL-concentration chart.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. State survivorship, liquidity, halt and borrow handling explicitly and
prominently — if any could not be addressed, that belongs in the opening
paragraph, not an appendix. Flag suspected overfits even if they rank first.
Nothing is tradeable on a backtest alone.
```
