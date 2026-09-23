# 50. SOXL Quick Dip: 2% dip above the 50-day, 4% target, 10% stop, 4 days max

Funds: SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma50`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $212 | +147% | 12 | 67% | +16.3% | -7.1% | 3.35 | -21% | $-5,248 |
| Last 12 months | $114 | +141% | 26 | 65% | +11.8% | -10.3% | 2.08 | -25% | $-5,248 |
| 2019 to Mar 2026 (bred on) | $33 | +409% | 155 | 67% | +6.9% | -9.5% | 1.33 | -67% | $-5,264 |
| 2012 to 2018 | $15 | +104% | 132 | 64% | +5.6% | -7.7% | 1.11 | -51% | $-3,425 |

Every rolling three-month stretch since 2019 (1878): 62% made money; the typical one made $32 a session and the worst $-180.

At 3x slippage: $204 a session over the last six months, $27 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +7% | $12 | 16 | 62% |
| 2013 | +133% | $89 | 26 | 85% |
| 2014 | +10% | $14 | 19 | 63% |
| 2015 | -19% | $-15 | 15 | 53% |
| 2016 | +44% | $42 | 22 | 68% |
| 2017 | -6% | $-1 | 20 | 55% |
| 2018 | -33% | $-33 | 14 | 50% |
| 2019 | +61% | $57 | 24 | 67% |
| 2020 | +38% | $45 | 26 | 73% |
| 2021 | -27% | $-20 | 25 | 56% |
| 2022 | -29% | $-25 | 11 | 46% |
| 2023 | +103% | $81 | 24 | 79% |
| 2024 | +52% | $53 | 19 | 68% |
| 2025 | +24% | $33 | 19 | 68% |
| 2026 | +184% | $172 | 19 | 68% |
