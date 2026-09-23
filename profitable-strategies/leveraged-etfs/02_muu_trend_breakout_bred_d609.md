# 02. MUU Trend Breakout (bred D609)

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `(rsi14 >= 39 and close > sma200 or atr_pct < 0.045) and mkt_vol20 > 0.515`
- **Buy** when `macd_hist > -0.05 and prev(macd_hist) <= -0.02 and close > sma200`
- **Buy** when `cross_above(macd, macd_signal) and mkt_ret20 < -0.11 or cross_above(close, sma200)`
- **Sell** when `bars_held > 10`
- **Sell** when `zscore20 <= -1.05`
- **Risk:** stop 8.6% under entry (on a close), trailing stop 14.2% off the best close, waits 3 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `bars_held` sessions the trade has been held; `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `macd` MACD line; `macd_hist` MACD histogram; `macd_signal` MACD signal line; `mkt_ret20` the first fund's 20-day return; `mkt_vol20` the first fund's 20-day volatility; `prev` prev(x): x one session earlier; `rsi14` RSI, 14 days; `sma200` 200-day average; `zscore20` standard deviations from the 20-day mean.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $521 | +745% | 12 | 67% | +48.4% | -13.0% | 2.54 | -50% | -$6,596 |
| Last 12 months | $527 | +9056% | 20 | 75% | +44.8% | -11.3% | 2.69 | -50% | -$6,596 |
| 2019 to Mar 2026 (bred on) | $88 | +15682% | 99 | 48% | +24.0% | -8.4% | 10.09 | -67% | -$5,551 |
| 2012 to 2018 | $43 | +713% | 99 | 44% | +17.8% | -8.3% | 1.21 | -66% | -$4,941 |

Every rolling three-month stretch since 2019 (1878): 68% made money; the typical one made $62 a session and the worst -$345.

At 3x slippage: $514 a session over the last six months, $83 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $513 a session over the last six months, $504 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -45% | -$53 | 8 | 12% |
| 2013 | +253% | $147 | 19 | 53% |
| 2014 | +185% | $118 | 16 | 62% |
| 2015 | -34% | -$34 | 9 | 22% |
| 2016 | +102% | $79 | 11 | 64% |
| 2017 | +112% | $90 | 17 | 59% |
| 2018 | -48% | -$44 | 19 | 21% |
| 2019 | +36% | $44 | 14 | 50% |
| 2020 | +64% | $60 | 9 | 44% |
| 2021 | -25% | -$9 | 18 | 39% |
| 2022 | -6% | $6 | 9 | 44% |
| 2023 | -5% | $7 | 17 | 24% |
| 2024 | +140% | $108 | 16 | 50% |
| 2025 | +1251% | $285 | 12 | 83% |
| 2026 | +2634% | $549 | 16 | 69% |
