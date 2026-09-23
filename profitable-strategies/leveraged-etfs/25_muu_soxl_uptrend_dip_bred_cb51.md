# 25. MUU / SOXL Uptrend Dip (bred CB51)

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `vol_ratio_20_60 < 0.75 and close > sma50 or pct_of_52w_high > 0.855 or vol_ratio_20_60 < 0.71`
- **Buy** when `dist_sma200 > -0.08 and rsi14 < 44`
- **Buy** when `ret1 < -0.01 and vol_ratio_20_60 > 1.43`
- **Sell** when `mkt_vol20 < 0.499`
- **Sell** when `position_return > 0.25`
- **Risk:** trailing stop 8.0% off the best close

Terms: `dist_sma200` distance above the 200-day average; `mkt_vol20` the first fund's 20-day volatility; `pct_of_52w_high` close / 52-week high; `position_return` the trade's return so far; `ret1` the day's return; `rsi14` RSI, 14 days; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $381 | +284% | 26 | 54% | +26.7% | -12.0% | 2.29 | -57% | -$7,628 |
| Last 12 months | $319 | +954% | 48 | 52% | +25.7% | -11.4% | 2.13 | -57% | -$7,628 |
| 2019 to Mar 2026 (bred on) | $97 | +14698% | 202 | 49% | +18.1% | -8.5% | 1.74 | -63% | -$6,334 |
| 2012 to 2018 | $72 | +4163% | 201 | 48% | +15.0% | -7.8% | 1.27 | -65% | -$5,194 |

Every rolling three-month stretch since 2019 (1878): 75% made money; the typical one made $85 a session and the worst -$273.

At 3x slippage: $369 a session over the last six months, $89 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-10-13): $286 a session over the last six months, $229 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -36% | -$35 | 11 | 27% |
| 2013 | +668% | $225 | 29 | 62% |
| 2014 | +72% | $73 | 41 | 49% |
| 2015 | -47% | -$47 | 23 | 39% |
| 2016 | +178% | $120 | 23 | 52% |
| 2017 | +268% | $150 | 39 | 56% |
| 2018 | -8% | $17 | 35 | 37% |
| 2019 | +54% | $64 | 24 | 50% |
| 2020 | +233% | $169 | 37 | 43% |
| 2021 | +49% | $69 | 41 | 49% |
| 2022 | -45% | -$50 | 10 | 30% |
| 2023 | +157% | $113 | 24 | 50% |
| 2024 | -6% | $29 | 34 | 47% |
| 2025 | +1040% | $271 | 23 | 70% |
| 2026 | +391% | $318 | 35 | 51% |
