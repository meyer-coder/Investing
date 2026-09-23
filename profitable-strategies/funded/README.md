# FundedNext day-trade strategies

As of 2026-09-23. Backtests on daily bars, not advice.

FundedNext Futures closes every position at 3:10 PM Chicago time and allows no
overnight or weekend holds ([help center](https://helpfutures.fundednext.com/en/articles/14268506-does-fundednext-futures-allow-overnight-and-weekend-trade-holding)).
The 20 NQ strategies in `../nq-2x/` hold for days, so they cannot run there as
written. Everything here is flat every afternoon.

## Bottom line

- **Safest set found:** the three bred strategies (`bred/`) run together on a
  Legacy 50K ($199.99): 2 MYM and 1 MES, daily stops of $261 and $392.
  - Breached 0 to 12% of challenges in every period since 2000.
  - Passed 22 to 53% within a year, a median of 5 to 6 months.
  - Profit is small: $2 to $15 a session.
- **Staying on the 25K:** S&P Calm Momentum alone on 1 MES passed 22% and breached
  3% on 2000–2009, and 51% / 18% on 2019–2026. It had seven trades in the last
  12 months, mostly losers.
- **For more profit:** the reworked top 10 (`top10/`) on 1 MES in a 50K. The best,
  Calm Trend, Fast Exit, passed 48% and breached 48% on 2019–2026, and 61% / 23%
  on 2010–2018.
- **Don't trade MNQ on the 25K.** On one MNQ every strategy breached 71–82% of
  challenges.

## FundedNext Legacy rules used

| Account | Fee | Profit target | Max loss limit (end-of-day trailing) |
| --- | --- | --- | --- |
| 25K | $79.99 | $1,250 | $1,000 |
| 50K | $199.99 | $3,000 | $2,000 |
| 100K | $239.99 | $6,000 | $3,000 |

The limit trails the best end-of-day balance and locks at the starting balance.
A floating loss that touches it breaches at once. The challenge has a 40%
consistency rule and no daily loss limit. Source:
[fundednext.com/futures/legacy](https://fundednext.com/futures/legacy).

## How the strategies trade

- Each session is the Globex day: bought at the 5:00 PM Chicago reopen, sold at
  the close (tested at the 3:00 PM settlement; be flat by 3:10).
- A strategy keeps its own position from day to day. The account holds it only
  inside a session and buys it back at the next open while the strategy still
  wants it.
- A resting stop under each day's fill caps that day. After a stopped day, the
  position comes back at the next open if the strategy still holds it.
- Being flat every night removes gap risk: the stop is working from the moment
  of entry.

## Top 10, reworked (`top10/`)

Profit a session on 2019 to March 2026, and the worst single day:

| # | Strategy | Published, 1 MNQ | Reworked, 1 MNQ, 0.8% day stop | Reworked, 1 MES, 1% day stop | 25K pass / breach, reworked MES |
| --- | --- | --- | --- | --- | --- |
| 1 | Calm Trend Champion | $59, −$3,565 | $31, −$493 | $14, −$393 | 33% / 66% |
| 2 | Calm Trend Champion, No Crash Entry | $57, −$3,565 | $24, −$493 | $13, −$393 | 29% / 70% |
| 3 | Calm Trend, Volume-Checked Dips | $64, −$3,565 | $33, −$493 | $13, −$393 | 24% / 73% |
| 4 | Quieter Trend + Z-Dip | $39, −$3,565 | $25, −$493 | $12, −$393 | 30% / 70% |
| 5 | Calm Trend, Fast Exit | $37, −$3,565 | $25, −$493 | $10, −$393 | 38% / 62% |
| 6 | Calm Trend Champion, 6% Target | $61, −$3,565 | $28, −$493 | $13, −$393 | 33% / 67% |
| 7 | Calm Trend + Washout | $54, −$3,172 | $26, −$493 | $9, −$393 | 27% / 73% |
| 8 | Calm Trend, 10-Session Holds | $33, −$3,565 | $25, −$493 | $11, −$393 | 30% / 70% |
| 9 | Calm Trend + Z-Dip Core | $40, −$3,565 | $26, −$493 | $8, −$393 | 28% / 72% |
| 10 | Quiet MACD Trend | $19, −$3,094 | $10, −$493 | $6, −$393 | 40% / 58% |

Each file holds the strategy, its settings, the published and reworked results
on every window, and its odds on the 25K, 50K and 100K with one to three
contracts. The Pine runs on a daily MNQ1! chart. For MES, take the same signals
and buy one MES with a 1% stop under its fill.

## Bred for the rules (`bred/`)

Bred on FundedNext pass rate minus breach rate, flat every day, with a 1% daily
stop. Each held up on years it never saw.

| Strategy | Contract, day stop | Never seen: pass / breach | 2019–2026: pass / breach |
| --- | --- | --- | --- |
| Dow Inside Day, One Session | 1 MYM, $261 | 2000–09: 19% / 28%; 2010–18: 22% / 10% | 47% / 1% |
| S&P Calm Momentum | 1 MES, $392 | 2000–09: 22% / 3% | 51% / 18% |
| Dow Dip Above the 50 | 1 MYM, $261 | 2000–09: 15% / 39% | 55% / 12% |

All three in one 50K account:

| Period | Passed | Breached | Profit a session | Median sessions to pass |
| --- | --- | --- | --- | --- |
| 2000–2009 | 22% | 10% | $2.00 | 111 |
| 2010–2018 | 41% | 12% | $7.90 | 124 |
| 2019 – Mar 2026 | 53% | 0% | $15.00 | 132 |
| Last 12 months | 33% | 0% | $11.10 | 128 |

Their Pine runs on daily MYM1! and MES1! charts.

## Trading the open and the close

- **Overnight vs regular hours:** QQQ made +996% overnight (4:00 PM close to
  9:30 AM open) and +103% in regular hours since 2005.
- **The overnight part is still available:** FundedNext won't let you hold
  overnight, but the Globex session (5:00 PM to 3:10 PM Chicago) contains most
  of it.
- **Gap trades at the 9:30 open:** none of 264 rules held up.
- **Last hour into the 4:00 close:** about zero on 2025–2026 hourly bars.

Details: `reports/sessions_study.json`.

## Daily routine

1. After the close, check the strategy's alert. "Buy at the next open" means it
   holds tomorrow.
2. At the 5:00 PM Chicago reopen, buy the contract and place the stop order at
   the daily stop under your fill at once.
3. Close by 3:05 PM Chicago the next day (FundedNext closes at 3:10 anyway).
4. Repeat while the strategy holds. Never add contracts to win back a loss.

## Files

- `top10/`, `bred/`: one `.json` (settings, results, odds, strategy) and one `.pine` per strategy.
- `reports/day_trades.json`: the top 10, every session, stop and contract tested.
- `reports/account_sizes.json`: 25K, 50K and 100K odds with one to four contracts.
- `reports/validation.json`, `reports/validation_r3.json`: the bred strategies on unseen years.
- `reports/book.json`: the bred strategies combined in one account.
- `reports/sessions_study.json`: the open and close study.
- `strategies/funded/*.py` reproduces every file; `configs/funded/` holds the island configs.
