# 43. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Quick Dip: 2% dip above the 200-day, 2% target, 6% stop, 4 days max

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $251 | +162% | 50 | 62% | +8.8% | -8.4% | 1.52 | -43% | -$4,557 |
| Last 12 months | $133 | +124% | 93 | 59% | +8.4% | -8.7% | 1.32 | -54% | -$4,557 |
| 2019 to Mar 2026 (bred on) | $52 | +932% | 445 | 62% | +6.0% | -7.6% | 1.17 | -54% | -$5,479 |
| 2012 to 2018 | $58 | +1314% | 412 | 62% | +5.8% | -7.0% | 1.16 | -55% | -$6,941 |

Every rolling three-month stretch since 2019 (1878): 75% made money; the typical one made $57 a session and the worst -$236.

At 3x slippage: $196 a session over the last six months, $30 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2025-07-30): $232 a session over the last six months, $133 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -22% | -$17 | 46 | 59% |
| 2013 | +208% | $133 | 63 | 67% |
| 2014 | -16% | -$4 | 57 | 63% |
| 2015 | +55% | $59 | 53 | 58% |
| 2016 | +213% | $142 | 70 | 71% |
| 2017 | +60% | $67 | 58 | 64% |
| 2018 | -10% | $22 | 65 | 52% |
| 2019 | +29% | $41 | 55 | 62% |
| 2020 | +106% | $97 | 75 | 65% |
| 2021 | +41% | $52 | 70 | 66% |
| 2022 | -30% | -$26 | 24 | 54% |
| 2023 | +70% | $69 | 68 | 65% |
| 2024 | +91% | $89 | 73 | 62% |
| 2025 | -21% | -$2 | 61 | 57% |
| 2026 | +303% | $251 | 69 | 62% |
