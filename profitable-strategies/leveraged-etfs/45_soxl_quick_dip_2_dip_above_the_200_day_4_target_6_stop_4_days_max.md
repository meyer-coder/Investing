# 45. SOXL Quick Dip: 2% dip above the 200-day, 4% target, 6% stop, 4 days max

Funds: SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $220 | +131% | 25 | 56% | +14.4% | -8.7% | 1.61 | -31% | $-5,248 |
| Last 12 months | $137 | +170% | 45 | 60% | +11.4% | -9.8% | 1.51 | -37% | $-5,248 |
| 2019 to Mar 2026 (bred on) | $29 | +250% | 187 | 58% | +7.5% | -8.0% | 1.2 | -63% | $-6,334 |
| 2012 to 2018 | $14 | +81% | 151 | 59% | +5.7% | -6.6% | 1.12 | -57% | $-3,563 |

Every rolling three-month stretch since 2019 (1878): 50% made money; the typical one made $0 a session and the worst $-206.

At 3x slippage: $168 a session over the last six months, $23 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -13% | $-11 | 13 | 54% |
| 2013 | +92% | $71 | 29 | 76% |
| 2014 | -9% | $-5 | 24 | 54% |
| 2015 | -24% | $-23 | 18 | 44% |
| 2016 | +75% | $61 | 22 | 68% |
| 2017 | +12% | $17 | 25 | 60% |
| 2018 | -19% | $-12 | 20 | 45% |
| 2019 | +21% | $31 | 29 | 48% |
| 2020 | +42% | $51 | 30 | 67% |
| 2021 | -0% | $15 | 39 | 59% |
| 2022 | -14% | $-13 | 4 | 25% |
| 2023 | +22% | $32 | 33 | 61% |
| 2024 | +29% | $39 | 25 | 52% |
| 2025 | +5% | $12 | 17 | 59% |
| 2026 | +232% | $212 | 35 | 63% |
