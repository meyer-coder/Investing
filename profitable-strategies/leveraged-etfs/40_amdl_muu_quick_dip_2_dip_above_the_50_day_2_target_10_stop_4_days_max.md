# 40. AMDL / MUU Quick Dip: 2% dip above the 50-day, 2% target, 10% stop, 4 days max

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma50`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $244 | +160% | 27 | 67% | +12.5% | -12.2% | 1.52 | -42% | $-3,847 |
| Last 12 months | $179 | +257% | 53 | 68% | +11.2% | -13.2% | 1.48 | -42% | $-4,152 |
| 2019 to Mar 2026 (bred on) | $28 | +130% | 252 | 63% | +7.0% | -9.7% | 1.11 | -66% | $-5,861 |
| 2012 to 2018 | $58 | +1754% | 250 | 69% | +6.6% | -9.3% | 1.5 | -66% | $-7,019 |

Every rolling three-month stretch since 2019 (1878): 63% made money; the typical one made $41 a session and the worst $-233.

At 3x slippage: $198 a session over the last six months, $20 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2024-12-19): $235 a session over the last six months, $92 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -7% | $2 | 26 | 58% |
| 2013 | +192% | $131 | 46 | 72% |
| 2014 | +4% | $16 | 32 | 62% |
| 2015 | -27% | $-23 | 21 | 57% |
| 2016 | +256% | $154 | 47 | 81% |
| 2017 | -24% | $-10 | 40 | 62% |
| 2018 | +229% | $136 | 38 | 76% |
| 2019 | +5% | $20 | 37 | 51% |
| 2020 | +9% | $26 | 43 | 70% |
| 2021 | +31% | $39 | 37 | 62% |
| 2022 | -45% | $-47 | 20 | 55% |
| 2023 | +89% | $76 | 33 | 67% |
| 2024 | +44% | $52 | 36 | 67% |
| 2025 | -26% | $-5 | 35 | 63% |
| 2026 | +257% | $230 | 38 | 68% |
