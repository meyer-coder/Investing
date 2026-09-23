# 31. SOXL 20-Day Burst or Uptrend Flush, out 2% under the 20-day

Funds: SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret20 > 0.2 and close > sma10`
- **Buy** when `ret1 < -0.05 and close > sma50`
- **Sell** when `dist_sma20 < -0.02`
- **Risk:** stop 12.0% under entry (on a close), waits 3 sessions after an exit

Terms: `dist_sma20` distance above the 20-day average (0.05 = 5%); `ret1` the day's return; `ret20` 20-day return; `sma10` 10-day average; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $267 | +196% | 4 | 50% | +111.8% | -8.7% | 4.52 | -36% | -$7,628 |
| Last 12 months | $165 | +250% | 10 | 70% | +37.5% | -12.4% | 3.61 | -44% | -$7,628 |
| 2019 to Mar 2026 (bred on) | $29 | +141% | 55 | 47% | +18.7% | -10.3% | 1.31 | -67% | -$5,812 |
| 2012 to 2018 | $8 | +24% | 39 | 49% | +8.3% | -5.9% | 1.19 | -47% | -$3,698 |

Every rolling three-month stretch since 2019 (1878): 59% made money; the typical one made $23 a session and the worst -$262.

At 3x slippage: $264 a session over the last six months, $26 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -11% | -$7 | 6 | 33% |
| 2013 | +13% | $15 | 8 | 62% |
| 2014 | +9% | $13 | 7 | 43% |
| 2015 | -15% | -$12 | 4 | 25% |
| 2016 | -16% | -$11 | 6 | 50% |
| 2017 | +62% | $55 | 4 | 100% |
| 2018 | -3% | $1 | 4 | 25% |
| 2019 | +59% | $57 | 6 | 67% |
| 2020 | +12% | $35 | 8 | 50% |
| 2021 | -21% | -$11 | 9 | 33% |
| 2022 | -29% | -$19 | 7 | 29% |
| 2023 | +54% | $58 | 8 | 38% |
| 2024 | -8% | $9 | 7 | 43% |
| 2025 | +98% | $87 | 7 | 71% |
| 2026 | +155% | $175 | 7 | 57% |
