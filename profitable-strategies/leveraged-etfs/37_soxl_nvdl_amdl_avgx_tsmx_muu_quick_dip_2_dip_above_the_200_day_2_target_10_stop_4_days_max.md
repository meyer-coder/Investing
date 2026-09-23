# 37. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Quick Dip: 2% dip above the 200-day, 2% target, 10% stop, 4 days max

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $266 | +174% | 41 | 68% | +9.7% | -11.4% | 1.77 | -51% | $-4,976 |
| Last 12 months | $172 | +214% | 79 | 66% | +8.6% | -10.6% | 1.56 | -51% | $-4,976 |
| 2019 to Mar 2026 (bred on) | $68 | +2544% | 392 | 66% | +6.1% | -8.2% | 1.28 | -54% | $-5,918 |
| 2012 to 2018 | $60 | +1405% | 382 | 66% | +5.9% | -8.2% | 1.17 | -65% | $-6,941 |

Every rolling three-month stretch since 2019 (1878): 77% made money; the typical one made $65 a session and the worst $-191.

At 3x slippage: $202 a session over the last six months, $50 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2025-07-30): $247 a session over the last six months, $161 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -24% | $-20 | 39 | 56% |
| 2013 | +191% | $127 | 55 | 71% |
| 2014 | +16% | $28 | 54 | 67% |
| 2015 | -6% | $9 | 50 | 56% |
| 2016 | +275% | $164 | 66 | 77% |
| 2017 | +68% | $79 | 56 | 71% |
| 2018 | -1% | $32 | 62 | 58% |
| 2019 | +83% | $80 | 51 | 63% |
| 2020 | +145% | $120 | 63 | 70% |
| 2021 | +15% | $34 | 64 | 66% |
| 2022 | -3% | $8 | 22 | 68% |
| 2023 | +105% | $89 | 60 | 68% |
| 2024 | +37% | $58 | 67 | 63% |
| 2025 | +0% | $25 | 48 | 60% |
| 2026 | +409% | $288 | 58 | 72% |
