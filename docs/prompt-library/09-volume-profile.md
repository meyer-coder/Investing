# Volume profile / value area — auction-theory mean reversion and breakout

**Why this family, and why it needs Databento specifically:** volume profile asks
*at which prices did business actually get done?* — and answering it requires a
real exchange tape. CFD and FX feeds report **tick counts**, not contracts
traded, so every profile built on them is fiction. The Databento pull gives real
CME contract volume at 1-minute resolution across ~9 years. This is the one
strategy family in the library that is impossible without that file, and it is
the native language of futures trading.

The premise is auction theory: a market spends most of its time near an agreed
fair value and comparatively little at the extremes. The **value area** — the
price band containing 70% of a session's volume — is that agreement, and its
edges are where the market decides whether to accept a new price or reject it.

Distinct from the ES VWAP brief (`02`): VWAP is a single average. A profile is
the whole distribution, and its shape carries information an average discards —
a thin node and a thick node sit at the same average but behave in opposite ways.

---

```
## 1. ROLE
You are a quantitative researcher specialising in futures market microstructure
and auction theory. I am not a quant — explain findings in plain language and
define every term on first use, starting with a short paragraph each on volume
profile, point of control, value area, and high- vs low-volume nodes. Do not ask
me clarifying questions: resolve ambiguity with the most defensible reading,
state the assumption in the report, and continue. Think deeply, take the time
you need, and report what failed as prominently as what worked.

## 2. INSTRUMENT
Primary:    NQ (E-mini Nasdaq-100). $20/pt, tick 0.25 = $5.00
Also test:  ES ($50/pt, tick 0.25 = $12.50), CL, GC — profile behaviour differs
            by product and a family that only works on one instrument is suspect.
Session:    Sun 18:00 ET - Fri 17:00 ET, daily halt 17:00-18:00 ET.
Contract roll is already handled: the data file uses volume-based continuous
rolling. Confirm the roll dates inside the sample and check whether profile
levels distort across them.

## 3. DATA
Primary:  data/futures/NQ_v_1m.parquet   <- USE THE 1-MINUTE FILE, NOT THE 5m
Build profiles from 1-minute bars. Aggregating volume into 5-minute buckets
before building the profile throws away exactly the price resolution the
strategy depends on. Execute on 5m bars; build profiles from 1m.
Coverage: ~9 years from 2017-05-22 (GLBX.MDP3 reaches 2010-06-06 but OHLCV
schemas are patchy before 2017-05-21).

Context layer (optional): the TradingView MCP tunnel serves 1000 daily bars
(~4 years) per call. Useful for volatility-regime tagging. It caps at 1000 bars
with no date-range parameter, so it cannot supply intraday history — do not try.

Print a data inventory BEFORE testing: first/last bar, total bars,
bars-per-session vs the expected 1380 at 1m, gaps, zero-volume bars, roll dates.
Flag any session with under half the median bar count and exclude it from
profile construction rather than building a distorted profile from partial data.

## 4. CLOCK
Store UTC, report America/New_York, DST-aware.
Define profile windows explicitly and test more than one — this choice matters
more than most parameters in the brief:
  RTH profile       09:30-16:00 ET (the cash-session auction)
  Globex profile    18:00-17:00 ET (the full 23-hour auction)
  Overnight profile 18:00-09:30 ET
Tag every bar with hour, day of week, month, year.

## 5. COST MODEL (mandatory)
NQ: $4.00 commission RT + 1 tick ($5) slippage each side = ~$14 RT.
Add a second tick each side in 09:30-09:35 and 15:55-16:00 and within 2 minutes
of a scheduled release. Signal on bar CLOSE, fill at NEXT bar OPEN; stops fill
at the worse of stop price and next open.
Value-area trades are often only 10-20 points wide, so friction can be 15-30% of
the gross move. Report gross and net side by side, friction as a % of gross, and
the break-even win rate for every variant.

## 6. PROFILE CONSTRUCTION (get this right before any strategy work)
For each session, from 1-minute bars:
  - Distribute each bar's volume across its high-low range. State your method —
    uniform distribution across the range is the standard approximation and its
    weakness at wide bars should be acknowledged in the report.
  - Bucket into price bins. Test bin widths of 1, 2 and 4 ticks.
  - POC = the price bin holding the most volume.
  - Value area = the contiguous band around POC holding 70% of session volume.
    Test 60%, 70%, 80%.
  - Classify nodes: HVN (high-volume node, price accepted) and LVN (low-volume
    node, price rejected — traded through quickly).
  - Record naked/virgin POCs: prior-session POCs that price has not revisited.
Validate the construction before trading it: POC should sit inside the value
area, the value area should contain ~70% of volume by definition, and profile
shape should visibly differ between trend days and range days. If it does not,
the construction is wrong and every downstream result is meaningless.

## 7. VARIANT SPACE — 500 variants
Two opposing sub-families. Run them as separate populations, ranked separately,
because a pooled ranking hides that one may work and the other not:

  FAMILY A — REVERSION AT VALUE EDGES
  Fade a probe of VAH/VAL back toward POC. Vary: entry at first touch vs after
  a rejection bar; target POC vs mid-value vs opposite edge; stop beyond the
  session extreme vs ATR-based; require the probe to fail within N bars.

  FAMILY B — ACCEPTANCE / BREAKOUT BEYOND VALUE
  Trade continuation once price is ACCEPTED outside value. Acceptance is the
  crux — define and test it several ways: N consecutive closes outside, time
  spent outside, volume transacted outside, a new POC forming outside. The
  distinction between a failed probe (Family A) and genuine acceptance
  (Family B) IS the edge; spend variants here above anywhere else.

  CROSS-CUTTING
  - Open location: open inside value / above VAH / below VAL, relative to the
    PRIOR session's profile. Open-outside-value is a classic and distinct setup.
  - Prior-day profile shape: normal/bell, double-distribution, trend day, thin.
    Classify each session and condition on it.
  - Naked POC as a magnet: does price revisit an unvisited prior POC more often
    than chance? Measure the base rate first, then the tradeable version.
  - LVN behaviour: price should move through low-volume nodes quickly. Test
    entries triggered on LVN penetration.
  - Value migration: profile overlapping / higher / lower vs the prior session.
  - Session window: all 23 hours tested independently. Does value-edge reversion
    work overnight, when volume is thin, or only in RTH?
  - Volatility regime: ATR percentile; value-area width vs its own 20-day average
    (a narrow value area signals a coiled market).
  - Calendar: day of week, month, opex, roll week.
  - Risk: stops at 0.5/1.0/1.5/2.0 x ATR; targets 1R/2R/3R; time stops.
  - Direction: long / short / both, tested for asymmetry.

No look-ahead, and this family is unusually easy to get wrong on this point:
a session's own profile is NOT KNOWN until that session ends. Trading today's
value area with today's completed profile is look-ahead bias and will produce
spectacular fake results. Use the PRIOR session's completed profile, or a
developing profile built only from bars already closed. State explicitly in the
report which you used and show that no bar's decision consumed future volume.

## 8. VALIDATION (non-negotiable)
Train 50% / validation 25% / LOCKED TEST 25%, chronological; test touched once.
Walk-forward 12mo fit / 3mo out-of-sample, concatenated — the headline curve.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR across variants.
Report the FULL distribution of all 500, per family: median, quartiles,
% profitable net of costs.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step, with surfaces — bin width and value-area
percentage especially. If results swing wildly between a 1-tick and 2-tick bin,
the edge is construction noise, not market structure.
SPECIFIC TO THIS FAMILY: report Family A's performance on the 20 largest trend
days in the sample. Value-edge reversion is precisely the strategy that dies on
trend days; quantify how badly.
Cross-instrument: validate the top 5 unchanged on ES. Auction structure is a
general mechanism, so a real edge should transfer. If it does not, you have
fitted NQ's noise.

## 9. SLICING
Hour of session (all 23, trade counts shown, buckets under 30 trades suppressed);
day of week; month; year over year (stability, not average); ATR-percentile
decile; value-area-width decile; prior-day profile shape; open-location bucket.

## 10. RANKING
Walk-forward net profit factor, subject to max drawdown < 15% and >= 150 trades.
Secondary: net PnL, Sharpe, Sortino, MAR, expectancy in ticks AND dollars,
break-even win rate vs actual win rate, worst single trade, longest losing
streak. Tie-break toward fewer parameters and toward variants that transfer to ES.

## 11. DELIVERABLES
PDF report; self-contained interactive HTML dashboard; 500-variant spaghetti PnL
chart with median and 25/75 bands, top 5 highlighted, the two families
colour-coded; per-variant CSV; trade logs; PLUS a rendered volume profile for a
representative trend day and range day with entries marked, so the mechanism is
visible rather than just asserted.

## 12. HONESTY
Lead with what failed and what the data could not answer. Collect every
assumption in one place. State explicitly how look-ahead was prevented in
profile construction. Flag suspected overfits even if they rank first. Nothing
is tradeable on a backtest alone.
```
