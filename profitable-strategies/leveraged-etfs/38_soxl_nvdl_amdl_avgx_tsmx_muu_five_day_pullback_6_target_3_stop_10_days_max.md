# 38. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Five-Day Pullback: 6% target, 3% stop, 10 days max

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret5 < -0.08 and close > sma200`
- **Sell** when `bars_held >= 10`
- **Risk:** stop 3.0% under entry (on a close), target 6.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret5` 5-day return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $238 | +156% | 39 | 62% | +10.3% | -8.5% | 1.89 | -33% | -$5,182 |
| Last 12 months | $221 | +506% | 66 | 64% | +10.4% | -8.8% | 1.94 | -33% | -$5,182 |
| 2019 to Mar 2026 (bred on) | $47 | +699% | 251 | 48% | +10.3% | -6.9% | 1.37 | -67% | -$7,324 |
| 2012 to 2018 | $25 | +142% | 187 | 54% | +8.5% | -7.6% | 1.06 | -69% | -$10,696 |

Every rolling three-month stretch since 2019 (1878): 66% made money; the typical one made $38 a session and the worst -$193.

At 3x slippage: $214 a session over the last six months, $36 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2025-07-30): $238 a session over the last six months, $200 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -8% | -$6 | 15 | 33% |
| 2013 | +36% | $38 | 25 | 48% |
| 2014 | +31% | $37 | 28 | 57% |
| 2015 | +87% | $67 | 18 | 78% |
| 2016 | +21% | $34 | 28 | 57% |
| 2017 | +41% | $45 | 32 | 53% |
| 2018 | -54% | -$44 | 41 | 49% |
| 2019 | -36% | -$27 | 28 | 39% |
| 2020 | +90% | $93 | 44 | 43% |
| 2021 | +33% | $44 | 41 | 51% |
| 2022 | -45% | -$55 | 15 | 13% |
| 2023 | +190% | $119 | 33 | 58% |
| 2024 | +58% | $70 | 45 | 51% |
| 2025 | +6% | $21 | 32 | 50% |
| 2026 | +373% | $264 | 52 | 64% |
