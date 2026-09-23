# 19. AMDL / TSMX Quick Dip: 3% dip above the 200-day, 4% target, 10% stop, 4 days max

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.03 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $328 | +287% | 31 | 74% | +10.5% | -10.0% | 2.27 | -42% | $-4,989 |
| Last 12 months | $172 | +253% | 56 | 66% | +9.1% | -9.0% | 1.82 | -42% | $-4,989 |
| 2019 to Mar 2026 (bred on) | $44 | +669% | 229 | 60% | +7.8% | -8.2% | 1.27 | -57% | $-5,479 |
| 2012 to 2018 | $22 | +47% | 176 | 62% | +7.5% | -9.8% | 1.03 | -68% | $-12,119 |

Every rolling three-month stretch since 2019 (1878): 64% made money; the typical one made $31 a session and the worst $-205.

At 3x slippage: $309 a session over the last six months, $36 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $307 a session over the last six months, $159 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -29% | $-29 | 23 | 48% |
| 2013 | +106% | $80 | 23 | 70% |
| 2014 | -37% | $-31 | 23 | 52% |
| 2015 | +15% | $16 | 11 | 64% |
| 2016 | +238% | $153 | 39 | 80% |
| 2017 | -47% | $-35 | 26 | 58% |
| 2018 | -23% | $-0 | 31 | 55% |
| 2019 | +53% | $53 | 32 | 56% |
| 2020 | +70% | $81 | 46 | 63% |
| 2021 | -20% | $-10 | 35 | 49% |
| 2022 | -32% | $-31 | 7 | 43% |
| 2023 | +35% | $41 | 29 | 62% |
| 2024 | +122% | $103 | 39 | 64% |
| 2025 | +89% | $80 | 32 | 69% |
| 2026 | +273% | $231 | 40 | 70% |
