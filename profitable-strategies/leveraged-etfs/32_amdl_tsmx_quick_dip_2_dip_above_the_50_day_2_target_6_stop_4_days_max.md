# 32. AMDL / TSMX Quick Dip: 2% dip above the 50-day, 2% target, 6% stop, 4 days max

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma50`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $265 | +214% | 26 | 62% | +10.5% | -4.1% | 2.68 | -20% | -$4,989 |
| Last 12 months | $124 | +160% | 49 | 55% | +8.8% | -5.5% | 1.85 | -40% | -$4,989 |
| 2019 to Mar 2026 (bred on) | $27 | +192% | 252 | 58% | +6.6% | -7.3% | 1.11 | -50% | -$5,112 |
| 2012 to 2018 | $54 | +1910% | 227 | 67% | +5.8% | -7.0% | 1.71 | -61% | -$7,019 |

Every rolling three-month stretch since 2019 (1878): 56% made money; the typical one made $14 a session and the worst -$190.

At 3x slippage: $248 a session over the last six months, $17 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2024-12-12): $268 a session over the last six months, $69 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +32% | $36 | 33 | 67% |
| 2013 | +145% | $106 | 32 | 66% |
| 2014 | -12% | -$4 | 26 | 69% |
| 2015 | -7% | -$1 | 23 | 61% |
| 2016 | +250% | $149 | 49 | 71% |
| 2017 | -29% | -$29 | 30 | 53% |
| 2018 | +202% | $122 | 34 | 79% |
| 2019 | +72% | $68 | 38 | 66% |
| 2020 | -2% | $14 | 50 | 64% |
| 2021 | -14% | -$7 | 30 | 53% |
| 2022 | -15% | -$8 | 20 | 45% |
| 2023 | +58% | $57 | 34 | 68% |
| 2024 | +79% | $76 | 36 | 53% |
| 2025 | -6% | $6 | 34 | 53% |
| 2026 | +179% | $174 | 36 | 58% |
