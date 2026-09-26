# Strategy lab: first two batches

Numbers are from 2026-09-25, after the close. Run with:
- `python -m stratlab batch research/lab/batches/01-screenshots.json`
- `python -m stratlab batch research/lab/batches/02-confluence-nas100.json`

The lab and its test protocol are described in [README.md](README.md).

## What the screenshots show

The owner shared screenshots of a dashboard that ranks 10,500 strategies by
total net R.

- **Its own random control ranks #5 of 10,500** ("CTRL-309 RANDOM control",
  +0.477R a trade, $45,846 at $250 risk). Random entries beat 10,495 of the
  10,500 strategies. When you test that many strategies, the top of the list
  is mostly luck. A ranking alone can't tell a real edge from a lucky one.
- **The second screenshot's strategies made 20-84 trades each** over the
  whole test (0.05-0.22 a week). Win rates of 60-78% on 27 trades are well
  within luck when they are picked from 10,500 strategies.
- **The full card includes "skips Wed/Fri".** Day-of-week filters like this
  usually come from fitting the test data.

The card format itself is good, so the lab uses it: signal, family settings,
direction, entry, stop, target, trailing, partial, time stop, max trades a
day and filters.

## Batch 1: the screenshot strategies on 13 years

Batch 1 has 19 cards. They use the families, markets, timeframes and
sessions from the screenshots, all with the exit template from the one full
card:
- a 50% pullback limit entry, cancelled after 10 candles;
- a 1 ATR stop and a 1 ATR target;
- at most 2 trades a day.

L0001 is that card exactly, including "skips Wed/Fri". There are 20 random
controls for each market, timeframe and session.

| ID | Family | Setup | Trades 2013-19 | Net R a trade, 2013-19 | Beats random | 2020-22 | 2023-26 |
|---|---|---|---|---|---|---|---|
| L0001 | volume spike breakout (the card) | NAS100 15m NY pm, skips Wed/Fri | 93 | −0.278R, t −2.8 | 5% | +0.154R | +0.180R |
| L0002 | volume spike breakout | NAS100 15m NY pm | 160 | −0.161R, t −2.1 | 25% | +0.035R | +0.341R |
| L0003 | volume spike breakout | NAS100 15m NY am | 885 | −0.076R, t −2.2 | 20% | −0.022R | +0.007R |
| L0004 | Asian range break | NAS100 15m London | 236 | −0.004R, t −0.1 | 60% | −0.065R | −0.058R |
| L0005 | Asian range break | NAS100 5m all | 528 | −0.162R, t −3.7 | 0% | −0.083R | −0.131R |
| L0006 | EMA ribbon | NAS100 3m NY am | 1,906 | −0.089R, t −3.9 | 10% | −0.042R | −0.046R |
| L0007 | EMA ribbon | NAS100 5m NY am | 1,417 | −0.079R, t −3.0 | 5% | +0.016R | −0.017R |
| L0008 | opening range breakout | NAS100 5m all | 1,164 | −0.059R, t −2.0 | 85% | −0.007R | −0.035R |
| L0009 | opening range breakout | NAS100 15m NY am | 911 | −0.060R, t −1.8 | 40% | −0.015R | −0.078R |
| L0010 | sweep & reclaim (Judas) | NAS100 5m all | 2,950 | −0.090R, t −4.8 | 35% | −0.049R | −0.125R |
| L0011 | sweep & reclaim | NAS100 60m Ldn+NY am | 1,078 | −0.002R, t −0.1 | 90% | −0.017R | −0.041R |
| L0012 | VWAP band reversion | NAS100 3m NY am | 2,751 | −0.069R, t −3.6 | 25% | −0.081R | −0.114R |
| L0013 | Bollinger reclaim | NAS100 1m all | 2,950 | −0.238R, t −12.5 | 95% | −0.184R | −0.237R |
| L0014 | round number | NAS100 60m all | 1,031 | +0.007R, t +0.2 | 90% | −0.032R | −0.035R |
| L0015 | gap fade | NAS100 15m all | 334 | −0.115R, t −2.1 | 15% | −0.067R | +0.023R |
| L0016 | MACD cross | NAS100 30m all | 1,821 | −0.000R, t −0.0 | 80% | +0.019R | −0.024R |
| L0017 | Donchian break | US500 15m NY pm | 827 | −0.112R, t −3.3 | 25% | −0.037R | −0.089R |
| L0018 | z-score reversion | US30 15m all | 2,844 | −0.157R, t −8.4 | 0% | −0.047R | −0.116R |
| L0019 | noise breakout (Bot A's idea) | NAS100 30m NY | 932 | −0.039R, t −1.2 | 25% | +0.151R | −0.017R |

**What batch 1 says:**
- **All 19 failed the search.** The card from the screenshot (L0001) lost
  0.28R a trade on 2013-2019 and beat only 5% of its random controls.
- **Random controls fill the top of the ranking, as in the dashboard.** All
  of the top 10 of 299 rows are random controls. The best real card ranks
  #16.
- **The card's own shape shows how it was picked.** L0001 lost money on
  2013-2019 and made money on 2020-2026 (93, 30 and 25 trades). That looks
  like rules chosen on recent data.

## Batch 2: confluences on NAS100 15m (96 cards)

Batch 2 crosses three things, all fixed before any result:
- **8 signals:** volume spike, Donchian, opening range, EMA cross, sweep &
  reclaim, Bollinger reclaim, z-score and noise breakout.
- **6 confluence sets:** none; the 200 EMA trend; VWAP side; relative volume
  of at least 1.5x; high ATR; and trend + VWAP + volume together.
- **2 exit templates:**
  - **T1**, the screenshot card: 50% pullback limit, 1 ATR stop, 1 ATR
    target.
  - **T2**, "let it run": market entry, 1 ATR stop, 3R target, half off at
    1R, then the stop moves to breakeven.

Each template has 30 random controls. The session is New York, and the
limit is 2 trades a day.

**Results by template** (net R a trade, averaged over the 48 cards of each
template):

| | 2013-2019 | 2020-2022 | 2023-2026 |
|---|---|---|---|
| T1 (pullback, 1:1) cards | −0.037R (23% of cards positive) | −0.020R | −0.005R |
| T1 random controls | −0.037R | +0.000R | −0.018R |
| T2 (let it run) cards | +0.024R (67% positive) | +0.019R | +0.046R (73% positive) |
| T2 random controls | −0.013R | +0.009R | −0.020R |

**T2, by signal:**

| Signal | 2013-19 | 2020-22 | 2023-26 | Confirmed |
|---|---|---|---|---|
| noise breakout (Bot A's idea) | +0.088R | +0.101R | +0.032R | 6 of 6 |
| opening range breakout | +0.056R | +0.036R | +0.018R | 2 of 6 |
| volume spike breakout | +0.044R | +0.035R | +0.065R | 1 of 6 |
| Donchian break | +0.037R | +0.032R | +0.001R | 2 of 6 |
| Bollinger reclaim (fade) | +0.025R | +0.013R | −0.015R | 0 of 6 |
| EMA cross | −0.006R | −0.008R | +0.019R | 0 of 6 |
| z-score reversion (fade) | −0.008R | −0.028R | +0.257R | 0 of 6 |
| sweep & reclaim (fade) | −0.045R | −0.024R | −0.013R | 0 of 6 |

**The 11 confirmed cards,** all T2 breakouts:

| ID | Signal + confluences | 2013-19 | 2020-22 | 2023-26 (unseen) |
|---|---|---|---|---|
| L0391 | noise breakout + 200 EMA trend | +0.104R, t 3.6 | +0.117R, t 2.9 | +0.028R, t 0.8 |
| L0395 | noise breakout + trend + VWAP + volume | +0.106R, t 3.3 | +0.146R, t 3.3 | +0.019R, t 0.5 |
| L0393 | noise breakout + volume | +0.090R, t 3.0 | +0.082R, t 2.0 | +0.018R, t 0.5 |
| L0359 | Donchian + trend + VWAP + volume | +0.086R, t 2.9 | +0.087R, t 2.2 | +0.012R, t 0.3 |
| L0390 | noise breakout, no filter | +0.077R, t 2.7 | +0.085R, t 2.2 | +0.035R, t 1.0 |
| L0392 | noise breakout + VWAP | +0.077R, t 2.7 | +0.107R, t 2.7 | +0.048R, t 1.3 |
| L0394 | noise breakout + high ATR | +0.074R, t 2.5 | +0.067R, t 1.6 | +0.045R, t 1.2 |
| L0353 | volume spike + trend + VWAP + volume | +0.085R, t 2.5 | +0.046R, t 0.9 | +0.054R, t 1.4 |
| L0365 | opening range + trend + VWAP + volume | +0.087R, t 2.3 | +0.080R, t 1.6 | +0.018R, t 0.4 |
| L0355 | Donchian + trend | +0.054R, t 2.1 | +0.074R, t 2.2 | +0.005R, t 0.2 |
| L0361 | opening range + trend | +0.074R, t 2.1 | +0.089R, t 1.8 | +0.020R, t 0.4 |

About 900-1,300 trades each on 2023-2026, roughly 5 a week.

**What batch 2 says:**
- **Only one kind of strategy works:** breakouts in the direction of the
  move with the "let it run" exit. The screenshot's 1:1 pullback exit fails
  with every signal. Fading moves fails with both exits.
- **The best signal is Bot A's noise breakout,** confirmed in all 6 of its
  confluence sets. This is the third independent check of the same edge:
  - the branch's Bot A;
  - `research/edges.py`;
  - now the lab.
- **Confluences didn't make much difference.** The noise breakout made
  +0.035R a trade on 2023-2026 with no filter, and +0.019R to +0.048R with
  one. Stacking three filters did not beat none. Each filter added is one
  more thing that can be fitted to the past.
- **The edge shrank in 2023-2026,** to about +0.02R to +0.05R a trade from
  about +0.08R to +0.10R before. Every confirmed card stayed positive, but
  none is significant on those years alone (t from 0.2 to 1.4).

**In dollars:**
- **With no filter (L0390),** the noise breakout makes about +0.035R a
  trade at about 5 trades a week. At $250 risk a trade that is roughly
  $9 a trade, or $2,300 a year, before any prop-firm rules.
- **The contract size to risk $250** is about 2 MNQ. The stop, 1 ATR of the
  15-minute candles, has been about 21 bp since 2025. That is about 65
  points, or $130 on 1 MNQ, at today's prices.

## How many cards the log holds

After both batches the log holds:
- **115 cards:** 19 in batch 1, 96 in batch 2;
- **340 random controls.**

At t ≥ 2, about 3 of the 115 cards would pass the search by luck. Twelve
passed, all of them T2 breakouts. They also beat 100% of their random
controls on 2013-2019, which luck alone rarely does.
