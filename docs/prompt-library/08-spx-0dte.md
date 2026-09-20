# SPX 0DTE options — defined-risk premium selling

**Why this belongs in the fleet:** every other brief in this library is
directional — the agent predicts where price goes. This one is not. The premise
is *structural*: index options have historically been priced above subsequent
realised volatility (the variance risk premium), so systematically selling
defined-risk premium harvests a spread that exists for reasons unrelated to
chart patterns. Its return stream is close to uncorrelated with the directional
agents, which is exactly what a portfolio needs.

SPX now has 0DTE expirations every weekday, so there is a fresh, self-liquidating
instrument every single session — no roll, no overnight gap risk, cash settled.

**The honest warning, up front:** this strategy family has a return profile that
flatters backtests more than almost anything else in finance. Many small wins,
rare enormous losses. A one-year backtest can show a beautiful straight equity
line and be catastrophically negative-expectancy. Section 8 exists to catch that
and is not optional.

---

```
## 1. ROLE
Quantitative researcher specialising in index options and volatility strategies.
I am not a quant — plain language, define terms on first use (start by explaining
what 0DTE, a credit spread, an iron condor, gamma and the variance risk premium
are, in one paragraph each). Do not ask clarifying questions; resolve ambiguity
with the most defensible reading, state the assumption, continue. Be especially
rigorous about tail risk — report failures as prominently as wins.

## 2. INSTRUMENT
SPX index options. $100 multiplier. Cash settled. EUROPEAN exercise — no early
assignment, which is the main reason to use SPX rather than SPY here.
Expirations: every weekday (Mon-Fri).
Tax: Section 1256, 60/40 treatment. Note it; do not model it in the PnL.
Underlying: S&P 500 cash index. Settlement for AM-expiry uses SET (the special
opening quotation), which is NOT the index open — if you model AM expiries,
handle SET explicitly or restrict the study to PM-settled 0DTE and say so.
Hours: 09:30-16:15 ET for SPX. Note the extra 15 minutes after the cash close —
the index stops moving at 16:00 but the options keep trading.

## 3. DATA — COVERAGE GATE (FIRST, AND THIS IS THE BINDING CONSTRAINT)
Target 3+ years of intraday options chains. This is the hardest data in the
library to obtain and there is no free complete source. Be honest about it.
  1. CBOE DataShop — authoritative, paid, per-day intraday chain snapshots.
     Get a quote for the window you need and report the cost.
  2. ORATS / OptionMetrics / Polygon options — paid, varying granularity.
  3. FALLBACK, IF NO CHAIN DATA IS AVAILABLE: reconstruct theoretical option
     prices from SPX 5m bars plus VIX/VIX1D using Black-Scholes. THIS IS AN
     APPROXIMATION AND YOU MUST SAY SO ON EVERY PAGE OF THE REPORT. It will
     misprice the wings, understate skew, and — most importantly — understate
     the bid/ask spread, which is where most of this strategy's real cost lives.
     A reconstructed-price backtest is a feasibility screen, not evidence.
Whichever path you take, print a data inventory before testing: date range,
expirations covered, strikes per expiry, snapshot frequency, missing days, and
whether quotes are real bid/ask or modelled. Gate: if you have < 1 year OR only
modelled prices, report the study as EXPLORATORY and do not rank variants as
though they were validated.

## 4. CLOCK
Underlying on 5m bars. Option chain snapshots at least every 15m, ideally 5m.
UTC storage, America/New_York reporting, DST-aware.
Tag: minutes since open, minutes to expiry (the key variable in this entire
study — gamma risk is a function of time remaining, not of clock time), DOW,
month, year, VIX level, VIX1D level, realised vol of the session so far.

## 5. COST MODEL (mandatory — and the usual reason 0DTE backtests are wrong)
Commission: $0.65 per contract per leg, both open and close. A 4-leg iron condor
opened and closed is 8 legs = ~$5.20. On a $100 credit that is 5% of gross.
Spread: ATM SPX 0DTE is typically $0.05-$0.20 wide; wings are wider. Assume you
pay HALF the spread on entry and HALF on exit, at minimum. If using modelled
prices, impose a spread assumption explicitly and test at 1x and 2x.
Assignment/settlement: cash settled at expiry. Model expiring-in-the-money legs
at intrinsic value. DO NOT assume you can always close before expiry — model
both "hold to expiry" and "close by 15:45 ET" as separate variants, because they
have materially different tail behaviour.
Margin: compute the defined-risk width requirement per position and report
return on margin, not just return on credit. Return on credit is the number
that makes these strategies look amazing and it is close to meaningless.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: at 10:00 ET, sell an iron condor with short strikes
at ~16 delta on each side, wings $25 wide, hold to expiry, no management.

## 7. VARIANT SPACE — 500 variants
  - Structure: iron condor / put credit spread / call credit spread / iron
    butterfly / broken-wing butterfly.
  - Short-strike delta: 5 / 10 / 16 / 25 / 30. This is the core risk dial —
    lower delta wins more often and loses more when it loses. Expect a near-flat
    expectancy curve across delta with wildly different tail shapes, and report
    the tails, not the averages.
  - Wing width: $10 / $25 / $50 (defines max loss and margin).
  - Entry time: 09:35 / 10:00 / 11:00 / 12:00 / 13:00 / 14:00 ET. Later entry
    means less time for the trade to go wrong but also less premium — this axis
    directly trades expectancy against gamma exposure.
  - Management: hold to expiry / close at 25% / 50% / 75% of max profit /
    stop at 1x / 2x credit received / close by 15:45 ET regardless.
  - Directional bias: neutral / skewed by the session's trend at entry
    (EMA slope, position vs VWAP, gap direction) / skewed by prior-day close.
  - Volatility gate: only enter when VIX1D is above/below a threshold, or when
    implied vol exceeds the trailing realised vol by a margin. This is the
    direct expression of the variance-risk-premium premise and deserves a large
    share of the variant budget — it is the most theoretically grounded filter
    in the brief.
  - Calendar: DOW (Monday and Friday 0DTEs have different character), FOMC days,
    CPI days, opex, month end. Test inclusion AND exclusion of event days —
    "don't sell premium into FOMC" is folklore worth actually measuring.
  - Trend gate: skip entry when the session is already trending strongly
    (opening range broken and holding) — trend days are what kill short premium.

## 8. VALIDATION (non-negotiable, and MORE important here than anywhere else)
Short-premium strategies produce many small wins and rare large losses. Standard
metrics actively mislead on this shape. Therefore, in addition to the usual:
  - Train 50% / validation 25% / LOCKED TEST 25%, chronological.
  - Walk-forward 12mo/3mo, concatenated — the headline.
  - Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
  - Full distribution of all 500 variants.
  - REQUIRED AND NON-NEGOTIABLE: report the worst single day, the worst week,
    and the 1st-percentile daily return for EVERY top variant. A Sharpe ratio on
    a short-gamma strategy is close to meaningless — the distribution is not
    remotely normal, and Sharpe assumes it is. Say so in the report.
  - Stress test the top 5 explicitly against the largest intraday SPX moves in
    the sample (Feb 2018 volmageddon, Mar 2020, Aug 2024 carry unwind, Apr 2025
    tariff selloff). If the sample does not include a >5% intraday down day,
    SYNTHESISE one and report what it would have done. A 0DTE premium strategy
    that has not been tested against a crash day has not been tested.
  - Report the ratio of largest loss to average win. Above ~20, the strategy is
    picking up pennies in front of a steamroller regardless of its Sharpe, and
    the report must say that in those terms.
  - Monte Carlo: 1000 shuffles, report 5th-percentile terminal equity AND the
    probability of a >50% drawdown.

## 9. SLICING
Entry time of day; DOW; month; year over year; VIX-level decile; VIX1D decile;
realised-vs-implied vol spread decile; trend-day vs range-day classification.
Named events as a stress check per section 8, with n stated.

## 10. RANKING
Walk-forward return on MARGIN (not on credit), subject to max drawdown < 20%,
>= 200 trades, AND largest-single-loss < 10% of peak equity.
Secondary: net PnL, Sortino (NOT Sharpe as the primary — the distribution is
too skewed for Sharpe to mean anything), MAR, win rate, avg win/avg loss,
largest loss / average win ratio, longest losing streak, worst day, worst week.
Tie-break toward variants with the SHALLOWEST tail, not the highest mean.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands and top 5 highlighted; per-variant CSV; trade logs;
plus a per-trade PnL distribution histogram with the left tail called out
explicitly, and a chart of cumulative PnL with the worst 5 days annotated.

## 12. HONESTY
Lead with tail risk, not with the equity curve. State prominently whether prices
were real quotes or modelled. All assumptions in one place. Flag suspected
overfits even if they rank first. If the strategy has not experienced a genuine
volatility shock in the sample window, that must be the report's opening
sentence. Nothing is tradeable on a backtest alone.
```
