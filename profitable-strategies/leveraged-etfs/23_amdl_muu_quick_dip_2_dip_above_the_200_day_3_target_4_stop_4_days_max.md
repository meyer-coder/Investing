# 23. AMDL / MUU Quick Dip: 2% dip above the 200-day, 3% target, 4% stop, 4 days max

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 4.0% under entry (on a close), target 3.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $297 | +214% | 42 | 57% | +13.0% | -9.3% | 1.65 | -39% | -$4,947 |
| Last 12 months | $226 | +422% | 83 | 55% | +11.7% | -8.3% | 1.63 | -40% | -$5,442 |
| 2019 to Mar 2026 (bred on) | $36 | +347% | 303 | 55% | +7.5% | -7.1% | 1.24 | -67% | -$5,479 |
| 2012 to 2018 | $47 | +555% | 277 | 60% | +7.8% | -8.5% | 1.18 | -67% | -$12,119 |

Every rolling three-month stretch since 2019 (1878): 55% made money; the typical one made $19 a session and the worst -$300.

At 3x slippage: $276 a session over the last six months, $29 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2025-07-30): $296 a session over the last six months, $205 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -27% | -$28 | 17 | 41% |
| 2013 | +76% | $76 | 52 | 60% |
| 2014 | -25% | -$7 | 48 | 56% |
| 2015 | +6% | $6 | 3 | 67% |
| 2016 | +259% | $154 | 53 | 68% |
| 2017 | -22% | $11 | 50 | 60% |
| 2018 | +129% | $118 | 54 | 59% |
| 2019 | -13% | -$1 | 41 | 51% |
| 2020 | +56% | $67 | 56 | 62% |
| 2021 | +64% | $64 | 53 | 58% |
| 2022 | -53% | -$67 | 14 | 29% |
| 2023 | +33% | $39 | 45 | 51% |
| 2024 | +63% | $59 | 38 | 55% |
| 2025 | +18% | $35 | 38 | 55% |
| 2026 | +419% | $294 | 60 | 57% |
