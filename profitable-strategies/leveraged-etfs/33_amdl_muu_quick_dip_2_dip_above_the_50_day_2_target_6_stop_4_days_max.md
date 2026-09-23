# 33. AMDL / MUU Quick Dip: 2% dip above the 50-day, 2% target, 6% stop, 4 days max

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma50`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $273 | +208% | 29 | 62% | +12.3% | -8.6% | 1.77 | -31% | $-3,847 |
| Last 12 months | $235 | +548% | 58 | 64% | +11.7% | -9.5% | 1.78 | -31% | $-4,152 |
| 2019 to Mar 2026 (bred on) | $29 | +163% | 274 | 60% | +7.1% | -8.6% | 1.17 | -54% | $-5,861 |
| 2012 to 2018 | $69 | +4042% | 268 | 66% | +6.9% | -8.1% | 1.74 | -66% | $-7,019 |

Every rolling three-month stretch since 2019 (1878): 56% made money; the typical one made $20 a session and the worst $-239.

At 3x slippage: $230 a session over the last six months, $18 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2024-12-19): $264 a session over the last six months, $115 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -4% | $6 | 30 | 57% |
| 2013 | +342% | $171 | 49 | 71% |
| 2014 | -9% | $3 | 37 | 57% |
| 2015 | -10% | $-3 | 23 | 61% |
| 2016 | +283% | $159 | 49 | 76% |
| 2017 | -23% | $-10 | 40 | 57% |
| 2018 | +304% | $155 | 40 | 75% |
| 2019 | -18% | $-5 | 41 | 54% |
| 2020 | -26% | $-15 | 45 | 62% |
| 2021 | +48% | $50 | 41 | 63% |
| 2022 | -25% | $-19 | 20 | 50% |
| 2023 | +18% | $27 | 37 | 57% |
| 2024 | +147% | $109 | 38 | 68% |
| 2025 | -17% | $2 | 40 | 57% |
| 2026 | +404% | $275 | 41 | 63% |
