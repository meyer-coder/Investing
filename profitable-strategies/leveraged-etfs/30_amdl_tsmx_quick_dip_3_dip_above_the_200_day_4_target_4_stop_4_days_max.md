# 30. AMDL / TSMX Quick Dip: 3% dip above the 200-day, 4% target, 4% stop, 4 days max

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.03 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 4.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $287 | +239% | 36 | 61% | +9.7% | -5.2% | 2.25 | -27% | -$4,989 |
| Last 12 months | $147 | +197% | 63 | 57% | +8.8% | -6.5% | 1.7 | -35% | -$5,539 |
| 2019 to Mar 2026 (bred on) | $36 | +376% | 259 | 54% | +8.1% | -7.2% | 1.17 | -64% | -$5,539 |
| 2012 to 2018 | $26 | +114% | 198 | 56% | +7.9% | -7.9% | 1.07 | -63% | -$12,119 |

Every rolling three-month stretch since 2019 (1878): 61% made money; the typical one made $25 a session and the worst -$284.

At 3x slippage: $254 a session over the last six months, $27 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $268 a session over the last six months, $151 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -11% | -$7 | 27 | 48% |
| 2013 | +74% | $62 | 27 | 59% |
| 2014 | -45% | -$46 | 23 | 44% |
| 2015 | +6% | $7 | 11 | 55% |
| 2016 | +246% | $150 | 48 | 65% |
| 2017 | -22% | $2 | 28 | 61% |
| 2018 | -12% | $11 | 34 | 53% |
| 2019 | +38% | $44 | 33 | 52% |
| 2020 | +63% | $74 | 53 | 58% |
| 2021 | -16% | -$7 | 38 | 47% |
| 2022 | -44% | -$51 | 11 | 27% |
| 2023 | +51% | $50 | 34 | 62% |
| 2024 | +131% | $105 | 47 | 49% |
| 2025 | +72% | $69 | 33 | 70% |
| 2026 | +155% | $168 | 46 | 54% |
