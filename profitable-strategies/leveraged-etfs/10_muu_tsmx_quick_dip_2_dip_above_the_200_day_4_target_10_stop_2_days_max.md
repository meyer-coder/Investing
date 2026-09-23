# 10. MUU / TSMX Quick Dip: 2% dip above the 200-day, 4% target, 10% stop, 2 days max

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 10.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $367 | +331% | 37 | 57% | +13.1% | -6.7% | 2.16 | -26% | $-5,937 |
| Last 12 months | $278 | +760% | 72 | 60% | +11.7% | -7.9% | 2.0 | -43% | $-5,937 |
| 2019 to Mar 2026 (bred on) | $62 | +3225% | 275 | 58% | +7.4% | -6.4% | 1.57 | -70% | $-5,442 |
| 2012 to 2018 | $36 | +513% | 255 | 61% | +5.6% | -6.3% | 1.18 | -48% | $-4,655 |

Every rolling three-month stretch since 2019 (1878): 63% made money; the typical one made $33 a session and the worst $-218.

At 3x slippage: $343 a session over the last six months, $53 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-07-30): $375 a session over the last six months, $278 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -2% | $4 | 30 | 60% |
| 2013 | +63% | $60 | 44 | 64% |
| 2014 | +90% | $79 | 46 | 65% |
| 2015 | -25% | $-25 | 20 | 50% |
| 2016 | +102% | $75 | 34 | 74% |
| 2017 | +99% | $83 | 45 | 62% |
| 2018 | -33% | $-26 | 36 | 47% |
| 2019 | +2% | $9 | 30 | 53% |
| 2020 | +261% | $146 | 44 | 68% |
| 2021 | +37% | $46 | 42 | 55% |
| 2022 | -42% | $-48 | 8 | 38% |
| 2023 | -27% | $-24 | 40 | 45% |
| 2024 | +521% | $200 | 56 | 70% |
| 2025 | +39% | $50 | 38 | 55% |
| 2026 | +676% | $356 | 54 | 59% |
