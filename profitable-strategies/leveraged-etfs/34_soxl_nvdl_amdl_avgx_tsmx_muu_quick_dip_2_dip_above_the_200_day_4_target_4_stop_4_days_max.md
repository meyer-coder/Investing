# 34. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Quick Dip: 2% dip above the 200-day, 4% target, 4% stop, 4 days max

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 4.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $261 | +169% | 50 | 56% | +10.1% | -7.4% | 1.51 | -39% | -$4,337 |
| Last 12 months | $195 | +302% | 99 | 54% | +9.9% | -7.0% | 1.47 | -39% | -$5,442 |
| 2019 to Mar 2026 (bred on) | $66 | +2121% | 470 | 53% | +7.8% | -6.5% | 1.28 | -57% | -$5,479 |
| 2012 to 2018 | $54 | +906% | 408 | 56% | +7.3% | -7.0% | 1.14 | -63% | -$8,100 |

Every rolling three-month stretch since 2019 (1878): 72% made money; the typical one made $62 a session and the worst -$208.

At 3x slippage: $222 a session over the last six months, $50 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2025-07-30): $313 a session over the last six months, $215 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +6% | $13 | 40 | 52% |
| 2013 | +53% | $62 | 63 | 59% |
| 2014 | -26% | -$6 | 56 | 57% |
| 2015 | +63% | $65 | 58 | 53% |
| 2016 | +127% | $103 | 62 | 61% |
| 2017 | +142% | $109 | 61 | 59% |
| 2018 | -6% | $31 | 68 | 48% |
| 2019 | +59% | $66 | 61 | 52% |
| 2020 | +56% | $78 | 77 | 56% |
| 2021 | +42% | $54 | 75 | 56% |
| 2022 | -32% | -$29 | 26 | 46% |
| 2023 | +86% | $77 | 69 | 61% |
| 2024 | +174% | $138 | 78 | 46% |
| 2025 | +16% | $42 | 63 | 51% |
| 2026 | +319% | $257 | 71 | 55% |
