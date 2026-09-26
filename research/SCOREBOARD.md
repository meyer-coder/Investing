# Scoreboard: what works and what doesn't

This is the one page to check before trying an idea. It is updated after
every test; each row links to the full write-up.

Last updated 2026-09-26.

**Verdicts:**
- **WORKS:** it held up on data it wasn't chosen on.
- **UNPROVEN:** it looked good on a short sample and hasn't been tested on
  13 years.
- **FAILS:** tested properly, with no edge.

## Works

| Idea | Market | Evidence | Where |
|---|---|---|---|
| **Noise-area breakout (Bot A)**: follow a move once price leaves its usual range for that time of day | NQ / MNQ | Three separate checks agree (see below). | [bot-a](bot-a-accounts-findings.md), [edges](edges-findings.md), [lab](lab/findings.md) |
| **Breakouts with a "let it run" exit**: Donchian, opening range, volume spike, with a 1 ATR stop, half off at 1R, stop to breakeven and a 3R target | NQ 15m | Confirmed on 2013-2022. Small on 2023-2026: +0.00 to +0.07R a trade. | [lab](lab/findings.md) |

**The three checks on Bot A:**
- **The rebuild:** $20 a day per MNQ over 13 years, t = 4.2.
- **The 13-market search:** +4.75 bp a trade on 2023-2026.
- **The lab:** confirmed in all 6 of its confluence sets, but only about
  +0.03R a trade on 2023-2026.

The edge is real but small.

## Unproven (promising on short data)

| Idea | Evidence so far | Where |
|---|---|---|
| **Basic fade**: after 15 minutes of all-red candles buy; after all-green, short (after 10:00) | Two years of hourly bars: +$8,389, beat 84% of coin flips. 60 days of 5-minute bars: +$4,887, beat 90%. | [shortbot](../shortbot/README.md) |
| **Big-drop short**: one large short on a sharp drop | Two years hourly: +$2,633, but all of it in the last 11 months. Beat 73% of coin flips. | [shortbot](../shortbot/README.md) |
| **Buy a fast 15-minute drop**, hold 60 minutes | 44 sessions: +$47 a trade. But the market rose 7.5% in that time, and shorting fast rallies made nothing. | [candle moves](candle-moves-findings.md) |

Fading moves has failed everywhere else on 13 years, so I expect basic fade
to fail too. It is still worth a proper test.

## Fails

| Idea | Tested on | Result | Where |
|---|---|---|---|
| Your screenshot's strategies (volume spike, Asian range, EMA ribbon, ORB, Judas, VWAP bands, Bollinger, round numbers, gap fade, MACD, Donchian, z-score) with its 1:1 pullback exit | 13 years, 19 cards | All fail. Random controls take the top 10 of 299. | [lab](lab/findings.md) |
| The 1:1 exit: 50% pullback limit, 1 ATR stop, 1 ATR target | 13 years, 8 signals × 6 filter sets | Fails with every signal | [lab](lab/findings.md) |
| Fade and reversion signals: sweep & reclaim, Bollinger, z-score, VWAP bands | 13 years, both exits | All fail | [lab](lab/findings.md) |
| Confluence filters: 200 EMA trend, VWAP side, relative volume, high ATR, all three together | 13 years | Don't improve the breakout. Stacking three did no better than none. | [lab](lab/findings.md) |
| Judas swing fade in Asia, London and New York | 13 years, 8 versions | None pass. NY 2R made $8 a day in 2023-26 but lost $6 a day in 2020-22. | [judas](judas-findings.md) |
| The "Three MNQ Setups" document | 43 days, then 13 years with 384 variants | −$480 out of sample. On 13 years none of the 384 pass; the document's rules make −1.13 bp a trade, t = −3.3. | [three setups](three-setups-findings.md) |
| Gold round-number rejection, 15m, NY PM | 13 years, 4 versions | About zero before costs | [three ideas](three-ideas-findings.md) |
| Crude z-score reversion, 15m, all sessions | 13 years, 4 versions | Zero before costs; loses 3.5 bp a trade to costs | [three ideas](three-ideas-findings.md) |
| Euro EMA crossover, 3m, NY PM | 13 years, 4 versions | Zero before costs; loses 2.6 bp a trade to costs | [three ideas](three-ideas-findings.md) |
| 16 intraday patterns on 12 other markets: noise breakout, ORB, first-half-hour momentum, gap follow and fade | 13 years, 192 variants | None pass. The S&P breakout worked only in 2020-22. Crude was positive before 2020 and negative after. | [edges](edges-findings.md) |
| Any short-term strategy on currency micros | 13 years | Costs of 2.6-4.7 bp a trade beat every pattern tested | [edges](edges-findings.md) |
| shortbot's three short setups | 2 years hourly | −$2,181, beat 29% of coin flips | [shortbot](../shortbot/README.md) |
| Basic follow: buy green runs, short red runs | 2 years hourly | −$7,495 | [shortbot](../shortbot/README.md) |
| Fading big-move days into the close | 2 years hourly | Every variant lost | [candle moves](candle-moves-findings.md) |
| Sizing Bot A by volatility | 13 years, 6 rules | The chosen rule did worse than plain 1 MNQ on 2023-26 | [bot-a](bot-a-accounts-findings.md) |

## Accounts and money

- **$150 a day per account is out of reach.** It needs a strategy far
  steadier than anything found here.
- **$50-60 a day paid from one Topstep 100K** needs about 6-8 unrelated edges
  as good as Bot A. We have one. ([edges](edges-findings.md))
- **Bot A at 1 MNQ on the Topstep 100K,** on 2023-26:
  - 93% of funded accounts survive a year;
  - it pays about $14 a day;
  - after fees, about $5 a day at the median.
- **The FundedNext 25K can't hold Bot A,** even at 1 MNQ: 7% of funded
  accounts last a year. ([edges](edges-findings.md))
- **Moving a 25K strategy to the 100K** gives about 1.5x, not 4x.
  ([bot-a](bot-a-accounts-findings.md))

## Lessons (the rules every test now follows)

1. **Write the idea down before testing it.** Every lab card is logged
   first, so the count of everything tried stays honest.
2. **Compare with random entries that use the same exits.** In big searches
   most "winners" are luck; in the screenshots, a random control ranked #5
   of 10,500.
3. **Use three periods.** Pick on 2013-2019, confirm on 2020-2022, and look
   at 2023-2026 once.
4. **Costs decide short-timeframe trading.** A round trip costs 0.36 bp on
   MNQ, 3.5 bp on MCL and 2.6-4.7 bp on FX micros. Most patterns don't make
   that much before costs.
5. **On Nasdaq, following moves works a little and fading them doesn't.**
6. **Rules read off one day or a few weeks fall apart on more data.**
7. **Check the data before believing a result.** Problems found so far:
   - Yahoo's contract rolls;
   - Dukascopy's stale 2013-14 overnight quotes and frozen day-session
     quotes;
   - crude's roll gaps;
   - two fill bugs in the lab, both caught because random entries didn't
     break even.

## Next to test

- **Basic fade and big-drop short on 13 years,** in the lab: they are the
  only unproven leads left.
- **A news filter on Bot A:** release days only, no release days, or no
  entries around release times. This waits on the owner's go-ahead and on
  finding historical release dates.
- **Bot A's lab version (L0390)** through the Topstep 100K rules.
