# 36. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Quick Dip: 2% dip above the 200-day, 2% target, 4% stop, 2 days max

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 4.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $252 | +155% | 56 | 57% | +9.0% | -7.2% | 1.37 | -49% | -$5,763 |
| Last 12 months | $214 | +364% | 112 | 57% | +8.8% | -7.3% | 1.39 | -49% | -$5,763 |
| 2019 to Mar 2026 (bred on) | $49 | +687% | 547 | 56% | +6.0% | -6.1% | 1.26 | -64% | -$5,479 |
| 2012 to 2018 | $57 | +1281% | 496 | 60% | +5.5% | -6.2% | 1.14 | -68% | -$6,941 |

Every rolling three-month stretch since 2019 (1878): 70% made money; the typical one made $56 a session and the worst -$278.

At 3x slippage: $200 a session over the last six months, $25 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2025-07-30): $281 a session over the last six months, $268 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -16% | -$10 | 53 | 57% |
| 2013 | +221% | $135 | 77 | 66% |
| 2014 | -52% | -$56 | 74 | 49% |
| 2015 | +80% | $73 | 66 | 64% |
| 2016 | +265% | $157 | 79 | 67% |
| 2017 | +67% | $71 | 71 | 59% |
| 2018 | -3% | $31 | 76 | 55% |
| 2019 | +4% | $17 | 68 | 53% |
| 2020 | +12% | $42 | 89 | 63% |
| 2021 | +72% | $71 | 88 | 58% |
| 2022 | -40% | -$43 | 27 | 44% |
| 2023 | +73% | $71 | 82 | 58% |
| 2024 | -9% | $15 | 97 | 47% |
| 2025 | +196% | $135 | 70 | 63% |
| 2026 | +259% | $239 | 82 | 56% |
