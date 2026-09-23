# 28. AMDL / MUU Quick Dip: 2% dip above the 50-day, 2% target, 4% stop, 4 days max

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma50`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 4.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $290 | +242% | 29 | 62% | +12.1% | -7.5% | 1.95 | -24% | -$3,509 |
| Last 12 months | $240 | +599% | 60 | 62% | +11.4% | -7.9% | 1.95 | -32% | -$5,442 |
| 2019 to Mar 2026 (bred on) | $25 | +135% | 296 | 55% | +7.0% | -7.0% | 1.12 | -67% | -$5,442 |
| 2012 to 2018 | $60 | +2236% | 279 | 62% | +7.1% | -7.5% | 1.51 | -62% | -$7,019 |

Every rolling three-month stretch since 2019 (1878): 55% made money; the typical one made $17 a session and the worst -$171.

At 3x slippage: $247 a session over the last six months, $16 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2024-12-19): $279 a session over the last six months, $102 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +23% | $31 | 33 | 55% |
| 2013 | +101% | $90 | 53 | 62% |
| 2014 | -5% | $8 | 37 | 57% |
| 2015 | -17% | -$13 | 23 | 52% |
| 2016 | +346% | $174 | 50 | 76% |
| 2017 | -16% | -$4 | 42 | 55% |
| 2018 | +220% | $131 | 41 | 68% |
| 2019 | +21% | $31 | 46 | 54% |
| 2020 | -18% | -$6 | 48 | 60% |
| 2021 | +43% | $47 | 43 | 58% |
| 2022 | -41% | -$44 | 21 | 33% |
| 2023 | +31% | $37 | 40 | 55% |
| 2024 | +70% | $65 | 43 | 54% |
| 2025 | -32% | -$19 | 42 | 55% |
| 2026 | +529% | $303 | 42 | 62% |
