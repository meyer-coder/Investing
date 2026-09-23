# 08. MUU / SOXL Quick Dip: 2% dip above the 200-day, 2% target, 6% stop, 4 days max

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $415 | +402% | 41 | 58% | +15.0% | -9.5% | 1.88 | -45% | -$4,527 |
| Last 12 months | $333 | +1255% | 80 | 62% | +12.3% | -9.5% | 1.89 | -45% | -$4,527 |
| 2019 to Mar 2026 (bred on) | $60 | +2484% | 282 | 63% | +6.8% | -7.4% | 1.63 | -60% | -$5,347 |
| 2012 to 2018 | $31 | +348% | 254 | 65% | +5.3% | -7.4% | 1.31 | -55% | -$5,194 |

Every rolling three-month stretch since 2019 (1878): 58% made money; the typical one made $31 a session and the worst -$225.

At 3x slippage: $389 a session over the last six months, $46 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-07-30): $397 a session over the last six months, $305 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -16% | -$13 | 19 | 58% |
| 2013 | +105% | $83 | 50 | 70% |
| 2014 | -26% | -$16 | 48 | 60% |
| 2015 | -21% | -$19 | 22 | 50% |
| 2016 | +49% | $46 | 30 | 73% |
| 2017 | +39% | $43 | 44 | 70% |
| 2018 | +113% | $92 | 41 | 63% |
| 2019 | +10% | $23 | 41 | 54% |
| 2020 | +98% | $82 | 40 | 75% |
| 2021 | +66% | $68 | 57 | 63% |
| 2022 | -18% | -$12 | 11 | 55% |
| 2023 | +28% | $36 | 42 | 55% |
| 2024 | +117% | $95 | 38 | 68% |
| 2025 | +42% | $50 | 36 | 58% |
| 2026 | +999% | $417 | 58 | 64% |
