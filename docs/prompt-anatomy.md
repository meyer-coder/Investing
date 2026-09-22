# Anatomy of the NQ backtest prompt

A clause-by-clause reading of the prompt, what each part means in quant terms,
what it causes an agent to actually produce, and where it breaks.

---

## 1. What each component means

| # | Your words | Term of art | What it makes the agent do |
|---|---|---|---|
| 1 | "backseat results of the strategy given" | **backtest** | Replay a fixed rule set over historical bars and record every simulated trade. |
| 2 | "a pdf and a dashboard html format" | **reporting layer** | Build two artifacts: a frozen PDF (archive, review, send to someone) and an interactive HTML dashboard (filter variants, hover equity curves, sort tables). Asking for both forces the agent to separate *computation* from *presentation* — a good instinct. |
| 3 | "performed on Nasdaq" | **instrument selection** | Underspecified. "Nasdaq" is five different tradeable things with different economics (see §2). |
| 4 | "use the trading view mcp tunnel for as much data as possible" | **primary data source** | Pull OHLCV from the TradingView MCP server. This is the binding constraint on the whole study — see §3. |
| 5 | "Then use external resources" | **fallback authorization** | Permission to leave the primary source when it is exhausted. Necessary, because it *will* be exhausted. |
| 6 | "five minute timeframe not the 45 seconds" | **bar resolution** | Aggregate to 5-minute candles. Sets signal frequency, noise level, and — critically — the ratio of transaction cost to average move. |
| 7 | "databentos free resources for futures NQ data" | **vendor fallback** | Databento sells CME (GLBX.MDP3) data and offers signup credit plus limited free sample windows. Genuinely useful, but CME licensing means deep history is not free. |
| 8 | "if you run out of candlesticks switch to CFD data" | **second fallback** | Substitute a broker CFD feed (NAS100) when futures data runs out. Carries a serious caveat — CFD "volume" is tick count, not contracts traded. |
| 9 | "London strategic is the final data for NQ futures than NQ CFD" | **ambiguous** | Most likely a dictation artifact. Three readings in §4. |
| 10 | "comparing all time frames specifically the New York open from 9-10am and 10-11am" | **time-of-day bucketing** | Note: you are using "timeframe" to mean *hour of the session*, not *bar resolution*. These are different axes. This clause means: tag every trade with its entry hour and compute performance per hour. |
| 11 | "The strategy spec may limit the trading window... we want to test around the clock" | **constraint → variable** | Take a hardcoded rule and promote it to a tested parameter. This is the single best instinct in the prompt. |
| 12 | "seasonal trends... month to month and... year to year" | **seasonality + regime stability** | Two separate tests: is there a calendar effect, and is the edge stable across years or concentrated in one lucky regime? |
| 13 | "Identify large historical events that cause volume increases... find correlations" | **event study / regime conditioning** | Tag dates (COVID, rate-hike cycle, carry unwind), compare strategy performance inside vs outside those windows. |
| 14 | "creative freedom... 500 variations... EMA, VWAP, VOLUME, DAY OF THE WEEK" | **combinatorial parameter sweep** | Enumerate a grid over filter dimensions, backtest every cell, rank. This is the engine of the whole request. |
| 15 | "all of these on a pnl chart" | **overlaid equity curves** | Plot cumulative PnL for every variant on shared axes. |
| 16 | "You are a quantitative backtesting expert. I am lacking in experience... Do not ask for my input" | **role + autonomy grant + no-clarification constraint** | Forces the agent to resolve every ambiguity silently. Raises throughput, and converts each ambiguity into an unstated assumption. |

---

## 2. "Nasdaq" is five instruments

| Instrument | Ticker | Multiplier | Tick | Hours | Notes |
|---|---|---|---|---|---|
| Nasdaq-100 index | NDX | — | — | RTH | Not tradeable. No volume. |
| E-mini future | `CME_MINI:NQ1!` | $20/pt | 0.25 = **$5** | 23h/day | True volume. Quarterly roll. |
| Micro future | `CME_MINI:MNQ1!` | $2/pt | 0.25 = **$0.50** | 23h/day | ~3x worse commission drag proportionally. |
| ETF | `NASDAQ:QQQ` | — | $0.01 | RTH + ext | Different tax, PDT rule, no leverage. |
| CFD | `FOREXCOM:NAS100` etc. | broker-defined | broker-defined | ~24/5 | Synthetic. Tick volume only. |

These are not interchangeable. A strategy tuned on CFD spreads can fail on futures costs and vice versa.

---

## 3. The measured data ceiling (this is the finding that matters)

The prompt assumes TradingView is a deep well and the fallbacks are for the tail.
For **intraday** resolutions it is the opposite. Measured directly against the
live tunnel, not assumed:

| Request | Bars returned | Coverage |
|---|---|---|
| `bars(NQ1!, 5m, count=1000)` | 1000 | 2026-09-16 10:55 -> 2026-09-22 02:10 UTC = **5.6 calendar days** (~4 trading days) |
| `bars(NQ1!, 5m, count=5000)` | **1000** (clamped) | identical window — the request for 5000 was silently reduced |
| `bars(NQ1!, 1h, count=1000)` | 1000 | 2026-07-22 -> 2026-09-22 = **61.6 calendar days** |
| `bars(NQ1!, 1D, count=1000)` | 1000 | 2022-09-29 -> 2026-09-21 = **~4 years** |

Three facts follow, and together they define what is buildable:

1. **`count` is hard-clamped to 1000.** Asking for 5000 returns 1000 and the
   response header says "1000 bars". No error, no warning. Code that assumes it
   got 5000 bars will silently analyse a fifth of the intended window.
2. **There is no date-range parameter.** The tool accepts `symbol`, `timeframe`
   and `count` only — no `from`, `to`, `end` or `offset`. Every call returns the
   *most recent* N bars. Calling it repeatedly returns the same window. **There
   is no pagination, so history cannot be walked backwards at any resolution.**
3. **Depth is purely a function of resolution**, because coverage is always
   `1000 x timeframe`:

| Timeframe | Coverage at the 1000-bar cap |
|---|---|
| 5m | ~4 trading days *(measured)* |
| 15m | ~2 weeks *(derived)* |
| 1h | ~2 months *(measured)* |
| 4h | ~8 months *(derived)* |
| 1D | ~4 years *(measured)* |
| 1W | ~19 years *(derived)* |

**The deep history is real — it is simply not available at intraday
resolution.** The daily feed reaches back four years through the same tunnel.
That is a genuinely useful dataset, just not the one a 5-minute strategy needs.

What the requested study actually needs: NQ trades 23h/day, so 276 five-minute
bars per session, ~252 sessions = **~69,500 bars/year**. Ten years is
**~695,000 bars** — 695 times the per-call cap, with no mechanism to page back.

### The consequence for the work

Split the study by what each resolution can actually support:

| Question | Resolution needed | Reachable through the tunnel? |
|---|---|---|
| Market regimes, volatility deciles, event identification | Daily | **Yes — 4 years, today** |
| Month-of-year and year-over-year *market* behaviour | Daily | **Yes — 4 years, today** |
| Strategy PnL attributed to month/year/regime | 5m | No — needs the strategy run on 5m over the same span |
| Hour-of-day buckets, opening range, 9-10 vs 10-11am | 5m | No — 4 trading days gives ~4 samples per hour bucket |

The daily feed supplies the **conditioning variables** (which months were
volatile, which events moved volume) but not strategy returns. Attributing PnL
to those regimes still requires 5m bars across the same years.

**Design implication:** make the agent *declare its coverage before it tests
anything* — bars retrieved, date span, bars per session, gaps — and refuse
seasonality when the span is under three years. Otherwise it will build a
month-by-month chart from four days and present it with a straight face. That
is why every brief in the library opens with a coverage gate.

## 4. The ambiguous clause

> "London strategic is the final data for NQ futures than NQ CFD"

Plausible readings, none certain:

1. **Priority ladder**: TradingView → Databento → [something] → CFD, with "final" meaning last resort.
2. **Session scope**: the London session (03:00–08:00 ET) is the final *window* to analyse.
3. **A vendor name** garbled by dictation.

An agent told not to ask will pick one. Reading 1 is most consistent with the surrounding sentences. Worth pinning down explicitly in future prompts — this is exactly the kind of clause that silently changes a study.

---

## 5. How the input becomes the output

The prompt implies this pipeline, whether or not it names it:

```
1. ACQUIRE    TradingView MCP -> Databento -> CFD, per the ladder
2. ASSEMBLE   timezone-normalize, handle quarterly roll, splice sources,
              tag each bar with session/hour/DOW/month/year
3. FEATURIZE  EMA, VWAP (session-anchored), relative volume, ATR, ranges
4. ENUMERATE  build the 500-cell variant grid from the filter dimensions
5. SIMULATE   vectorized backtest per variant; signal on bar close,
              fill next bar open, charge commission + slippage
6. MEASURE    per variant: net PnL, Sharpe, profit factor, max DD, win rate,
              expectancy, trade count
7. SLICE      re-cut every variant's trades by hour / DOW / month / year / regime
8. RANK       order variants by the chosen objective
9. RENDER     PDF report + HTML dashboard + overlaid equity-curve chart
```

Each clause of your prompt attaches to one stage. Clause 4/7/8 -> stage 1.
Clause 6 -> stage 2. Clause 14 -> stages 3–4. Clause 10/12/13 -> stage 7.
Clause 2/15 -> stage 9. That mapping is why the prompt "works": it happens to
touch every stage. What it never specifies is **stages 5 and 8** — the cost
model and the ranking objective — which are the two that decide whether the
answer is real.

---

## 6. What breaks

Ordered by how much damage each does.

**1. The strategy is not attached.** "the strategy given" and "the strategy spec"
refer to a document that is not in the message. Everything downstream is
decoration without it. This is the first thing to fix.

**2. 500 variations with no out-of-sample protocol.** This is the serious one.
Test 500 strategies on one dataset and the best one looks excellent *by
construction*. With 500 independent coin-flip strategies you expect a
best-of-500 t-statistic around 3.0 from luck alone — the number most people
treat as proof. The defences are standard and cheap:

- Split train / validation / **locked test** (never touched until the end).
- **Walk-forward**: fit on a rolling window, trade the next window, concatenate.
- **Deflated Sharpe Ratio** (Bailey & López de Prado) — adjusts the winner's Sharpe for the number of trials.
- Benjamini–Hochberg FDR across variants, not raw p-values.
- Report the **whole distribution** of 500 results, not the top 10. If the median variant loses money, the top variant is a lottery ticket.

Note your own repo already does this correctly in `README.md` — a held-out 25%
that is scored every generation but **never used for selection**. The prompt
abandons a discipline the codebase already has.

**3. No cost model.** On 5m bars this usually decides everything:

| | Tick value | Spread (1 tick) RT | Commission RT | ~Total RT |
|---|---|---|---|---|
| NQ | $5.00 | $10.00 | ~$4 | **~$14** |
| MNQ | $0.50 | $1.00 | ~$1.25 | **~$2.25** |

Three trades/day ≈ 750/year ≈ **$10,500/year per NQ contract** in friction. Many
5-minute "edges" are smaller than that. A backtest without costs is not
optimistic, it is unrelated.

**4. Splicing futures and CFD into one series.** Different price levels (CFD
tracks cash, futures carry basis), different hours, and volume that means
different things. Any variant using a VOLUME filter — which you explicitly
requested — produces results that do not transfer across the splice.

**5. No contract-roll handling.** NQ rolls quarterly (H/M/U/Z). Naively chaining
front months injects fake gaps four times a year. Needs back-adjustment
(Panama or ratio), and the method changes returns.

**6. Timezone and DST.** Your data arrives in **UTC**; "9–10am" is **ET**. The
offset changes twice a year. Bucket on DST-aware ET or the opening hour smears
across two buckets for ~8 months of every year.

**7. Event study has no statistical power.** There are maybe 5–10 "large
historical events" in a decade. With n=8 you can describe, but you cannot
establish correlation. Reframe as a *continuous* regime variable — realized
volatility decile, or relative volume — which gives thousands of observations
instead of eight.

**8. "Most profitable" is undefined.** Highest net PnL, Sharpe, profit factor,
MAR, and lowest drawdown select different winners. Unspecified, the agent picks
one silently — usually total return, which favours the most levered, most
overfit variant.

**9. No bridge to deployment.** Your stated goal is deploying agents to live
accounts. The prompt ends at a ranked table. Missing: forward paper period,
capital allocation across agents, correlation between agents (10 agents running
one edge is one position, not a portfolio), and kill-switch rules.

---

## 7. What the prompt gets right

Worth keeping, because these are not obvious:

- **Two output formats** — forces separation of computation from presentation.
- **Explicit data fallback ladder** — most prompts fail silently on data; this one plans for exhaustion.
- **Overriding the strategy's own session constraint** — refusing to inherit an unvalidated assumption is exactly right.
- **Requesting the full variant distribution on one chart** — the instinct to see all 500, not just the winner, is the correct defence against cherry-picking.
- **Explicit autonomy grant** — removes the clarification round-trips that stall long analytical runs.

---

## 8. The one-line diagnosis

The prompt is a well-shaped *research brief* with a broken *evidence base*: it
specifies the analysis in more detail than the data can support, and specifies
the validation not at all. Fix the data ladder and add an out-of-sample
protocol, and the rest of it is sound.

See `docs/prompt-library/00-master-template.md` for the hardened version.
