# The NQ and ES breakout and liquidity-sweep bot

As of 2026-09-25. Backtests on one-minute bars from January 2013 to September
2026, not advice. Paper and funded accounts only.

**The short answer:**

- **Breakouts pay on NQ.** Two NQ breakout rules made money in both halves
  of the test, 2013-2019 and 2020-2026. They are the bot.
- **Liquidity sweeps don't pay.** No sweep rule held up on NQ or ES, with or
  without ICT-style confirmation, so the bot has no sweep leg.
- **ES adds nothing lately.** Adding ES made the whole thing less
  consistent, and ES has lost money over the last three years.
- **Big leverage works against you.** More contracts means more dollars a
  day, but deeper losing stretches and lower odds of passing a funded
  evaluation. Past about 5 MNQ a bot per $25,000, the account actually grows
  more slowly.

## The bot: two NQ breakouts

| | Bot A: noise-area breakout | Bot B: pre-market range break |
| --- | --- | --- |
| Rule | Every 30 minutes (10:00 to 15:30) the close is compared with the "noise band": how far NQ usually moves from its open by that time of day, averaged over 14 sessions. Buy above the band, short below it. Exit when a check's close is back inside the band or through the session's average price. | The pre-market range is the 07:00-09:29 New York high and low. Between 09:30 and 11:30, a one-minute close beyond it followed by five more closes beyond it triggers an entry at the next open. The trade is held to the close. |
| Stop | A resting stop 0.30% from the entry | A resting stop 0.02% back inside the broken level |
| Out | By 16:00 at the latest | At 16:00, unless stopped out first |
| Trades | 3,171, about 1 a day | 1,862, about 1 every 2 days |
| $ a day, one MNQ | $21 (2013-19 $17, 2020-26 $25, last 3 years $16) | $11 (2013-19 $5, 2020-26 $16, last 3 years $10) |
| Sharpe | 1.17 | 0.70 |
| Worst day | -$945 | -$707 |
| Worst losing stretch | -$5,678, Apr 2025 to Feb 2026; now $1,796 below its high | -$8,182, Jul 2014 to Sep 2016; recovered Jan 2018 |
| Losing years | 2013 (-$1 a day) | 2013, 2015, 2016 |
| Pine Script | [noise_area_breakout_futures.pine](noise_area_breakout_futures.pine) | [pm_range_break.pine](pm_range_break.pine) |

**How the two bots fit together:**

- **They cover for each other.** Their daily results move together only
  +0.35. Over Bot A's worst stretch (Apr 2025 to Feb 2026, -$5,678), Bot B
  made +$5,051.
- **Run together at one MNQ each:**
  - $32 a day and a Sharpe of 1.16;
  - only one losing year (2013, -$2 a day);
  - $22 a day in 2013-2019, $41 in 2020-2026 and $26 over the last three
    years;
  - a worst losing stretch of -$6,302 (March 2020).

**Why Bot B isn't a lucky pick:** it was one of 48 breakout settings tested.

- On its own, its 2013-2019 edge was weak (t = 1.2).
- **What makes it credible is its neighbors.** Every pre-market break held
  to the close made money in both halves: hold 1 or 5 minutes, enter by
  11:30 or by 15:00.
- **The same breaks with a fixed 1R, 2R or 3R target lost.** The edge is in
  letting the rare trend day run. Bot B wins only about one trade in five.
- **Bot A has the stronger case** (t = 4.2 over 13 years). It was found on
  2020-2023, then confirmed on 2013-2019 and 2024-2026. It has been on the
  paper book since 2026-09-24.

**Year by year, $ a day at one MNQ each:**

| | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bot A | -1 | 18 | 14 | 4 | 8 | 72 | 1 | 13 | 22 | 46 | 39 | 28 | 18 | 5 |
| Bot B | -2 | 1 | -8 | -3 | 21 | 7 | 19 | 9 | 7 | 47 | 11 | 3 | 13 | 23 |
| Both | -2 | 19 | 6 | 1 | 29 | 78 | 20 | 22 | 29 | 93 | 50 | 31 | 31 | 28 |

## Leverage

Each figure below is per MNQ contract on each bot. Every trade is priced at
today's NQ level (30,478), where one MNQ controls $60,957 of index. Dollar
figures scale with the contract count. "Resized daily" means the same
leverage kept on a growing or shrinking account, i.e. the contracts are
resized every day.

**Both bots on $25,000 (e.g. one bot on each of two $12,500 accounts):**

| MNQ per bot | Leverage when both are in | $ a day (last 3 years) | Worst day | Worst losing stretch, fixed contracts | Resized daily: growth a year, deepest fall |
| --- | --- | --- | --- | --- | --- |
| 1 | 4.9x | $32 ($26) | -$1,336 | -$6,302 (25% of $25k) | +32%, -23% |
| 2 | 9.8x | $63 ($51) | -$2,673 | -$12,605 (50%) | +64%, -43% |
| 3 | 14.6x | $94 ($77) | -$4,009 | -$18,907 (76%) | +92%, -62% |
| 5 | 24.4x | $158 ($128) | -$6,682 | -$31,512 (126%) | +120%, -88% |
| 8 | 39.0x | $252 ($205) | -$10,692 | -$50,419 (202%) | +86%, -99% |
| 10 | 48.8x | $315 ($257) | -$13,365 | -$63,023 (252%) | +32%, -100% |
| 20 | 97.5x | $630 ($513) | -$26,729 | -$126,046 (504%) | wiped out |

**What leverage does here:**

- **Dollars a day scale straight up.** So do the worst day and the worst
  losing stretch.
- **Growth peaks at about 5 MNQ per bot.** Resized daily, the account grows
  fastest there, but at that size it has fallen 88% from a high. Past 5, it
  grows more slowly. At 20 it is wiped out, even though every trade has the
  same edge.
- **A workable "large" size is 2-3 MNQ per bot on $25,000.** That is 10-15x
  the account, for $63-94 a day, with falls of 43-62% along the way.
- **Bot A alone** peaks at about 8 MNQ: +126% a year, with a 90% deepest
  fall.

**Funded evaluations.** The table shows the share passed and breached. Each
test starts on every fifth session since 2013 and runs until it passes or
breaches; the median sessions to pass are in parentheses. Firms differ;
these are typical rules:

- 50K: a $3,000 target, a $2,000 drawdown limit that trails the best
  end-of-day balance (the day's worst point counts), and a $1,000 daily
  loss limit;
- 150K: a $9,000 target, a $4,500 drawdown limit and a $3,000 daily loss
  limit;
- in both, no single day can be more than half the profit.

| MNQ per bot | Bot A, 50K | Bot A, 150K | Bot B, 50K | Both on one 50K | Both on one 150K |
| --- | --- | --- | --- | --- | --- |
| 1 | **51% / 44% (81)** | **78% / 8% (363)** | 36% / 61% (123) | 42% / 56% (52) | 66% / 24% (233) |
| 2 | 34% / 63% (38) | **51% / 41% (141)** | 30% / 68% (52) | 24% / 75% (32) | 44% / 53% (76) |
| 3 | 26% / 73% (23) | 40% / 56% (70) | 23% / 76% (34) | 17% / 83% (25) | 33% / 65% (46) |
| 5 | 19% / 80% (20) | 30% / 68% (41) | 16% / 82% (31) | 9% / 91% (25) | 22% / 76% (32) |
| 10 | 11% / 88% (23) | 19% / 80% (20) | 12% / 87% (30) | 3% / 97% (21) | 11% / 88% (23) |

**What that means for a funded account:**

- **Trade the smallest size.** On an evaluation, every extra contract lowers
  the pass rate. The $2,000 limit is small next to what NQ moves in a day.
- **The best odds are Bot A with 1 MNQ on a 50K:** passed about half the
  time, in a median of 81 sessions (about four months).
- **On a 150K, 2 MNQ is the practical size.** At 1 MNQ it almost never
  breaches, but the median pass takes about a year and a half.
- **Run one bot per account.** Two strategies on one account net each
  other's positions, and one bot's exit can close the other's trade.

## What didn't make it

**Liquidity sweeps (`strategies/sweeps/sweeps.py`).** The levels:

- yesterday's high and low;
- the 07:00-09:29 pre-market high and low;
- the first 15 minutes' high and low.

A sweep is price running past one of those levels, then a one-minute close
back inside within 1, 5, 15 or 30 minutes. The fade enters at the next open,
with the stop just past the run's extreme and a target of 1R, 2R, 3R, the
middle of the range, or the close. The ICT-style versions add:

- +MSS: the entry waits for a close past the swing before the run;
- +trend: runs of the highs are faded only below the 20-day average, and
  runs of the lows only above it.

About 190 versions were tested on each index. The table shows the mean
trade after a 1 bp round-trip cost:

| Family | NQ 2013-19 | NQ 2020-26 | NQ settings positive after 2020 | ES 2013-19 | ES 2020-26 | ES settings positive after 2020 |
| --- | --- | --- | --- | --- | --- | --- |
| sweep | -0.69 bp | -0.86 bp | 11 of 72 | -0.42 bp | -0.90 bp | 8 of 72 |
| sweep +MSS | -2.44 | -1.80 | 6 of 24 | -2.01 | -1.72 | 3 of 24 |
| sweep +trend | -1.14 | +0.55 | 10 of 24 | -0.76 | -0.80 | 7 of 24 |
| sweep +MSS +trend | -2.58 | -1.16 | 11 of 24 | -3.19 | -2.90 | 4 of 24 |
| sweep to mid (4 families) | -0.50 to -1.11 | -0.71 to +0.48 | 17 of 45 | -0.13 to -0.79 | -1.09 to -2.23 | 0 of 43 |
| level breaks, for comparison | +0.14 | +0.19 | 22 of 48 | -0.35 | -0.07 | 17 of 48 |

**What the sweep results show:**

- **Every sweep family lost money on both indexes in 2013-2019.**
- **The sweeps that looked best in 2013-2019 didn't carry on.** On NQ their
  top ten averaged -1.04 bp a trade after 2020; on ES, -2.07.
- **Two NQ families were slightly positive after 2020** (+0.5 bp) after
  losing before, which is within noise.
- **Adding the best sweep to the bot lowered it.** The NQ breakouts plus the
  ES rules and both sweeps made -$1 a day over the last three years.

**ES.** The same two breakouts, at 2 MES:

- the noise-area breakout made $7 a day since 2013, -$9 over the last three
  years, with 7 losing years;
- yesterday's-range break made $7 a day, -$7 over the last three years.

Adding ES to the two NQ bots did this, per unit:

| | $ a day | Last 3 years | Sharpe | Worst stretch |
| --- | --- | --- | --- | --- |
| Both NQ bots | $34 | $26 | 1.21 | -$6,953 |
| + ES noise-area | $41 | $17 | 0.98 | -$11,106 |
| + ES noise and the ES yesterday's-range break | $48 | $10 | 1.06 | -$10,599 |

This comparison is on the 2,994 sessions both indexes have, so the NQ
figures differ slightly from those above.

## Caveats

- **The data:** Dukascopy's Nasdaq-100 and S&P 500 index CFDs, bid side,
  minute by minute. They follow the futures closely but are not the
  futures.
  - The pre-market is 07:00-09:29 New York, not the whole overnight session.
  - ES is missing much of 2014 and 2017.
- **Costs:** 1 bp of the price a round trip, $6 on an MNQ at today's level.
  - Commission plus a tick of slippage is nearer $2-3.
  - But stops can slip more in a fast market.
- **Today's prices:** every trade is priced at today's level, so a 2013
  trade counts at today's contract size.
- **Intraday low points** add up each trade's worst open loss, which is more
  cautious than the real path.
- **Bot A's recent run:** it is still below the high it set in April 2025.
  It fell $5,678 per MNQ from 2025-04-24 to 2026-02-02, and has made back
  $3,882 since.
- **Funded rules vary.** Some firms trail the drawdown intraday, which is
  stricter than the end-of-day trailing used here.

## Running it

1. **Chart:** one 1-minute MNQ1! chart per bot in TradingView. CME futures
   show the pre-market by default, and Bot B needs it.
2. **Script:** add the Pine Script. The order size defaults to 1 contract.
3. **Alerts:** create an alert on "any alert() function call". Each alert
   carries a JSON message (buy, sell short, flatten, with the stop for
   Bot B) for a webhook to the account's platform.
4. **Paper first.** Both scripts fill at the next bar's open, as the
   backtest does.

Reproduce:

```
python3 strategies/sweeps/data.py     # builds the minute arrays from the Dukascopy cache
python3 strategies/sweeps/sweeps.py   # the sweep and break study -> strategies/sweeps/sweeps.json
python3 strategies/sweeps/bot.py      # the legs, books, leverage and funded tables -> strategies/sweeps/bot.json
```
