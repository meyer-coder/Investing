# 18. MUU / SOXL Uptrend Dip (bred CBE3)

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `dist_sma200 > -0.08 and rsi14 < 37`
- **Buy** when `ret1 < -0.01 and vol_ratio_20_60 > 1.43 and bb_pct > 0.5`
- **Buy** when `vol_ratio_20_60 < 0.75 and close > sma50 or pct_of_52w_high > 0.855`
- **Sell** when `mkt_vol20 < 0.499`
- **Sell** when `position_return > 0.25`
- **Risk:** trailing stop 8.0% off the best close

Terms: `bb_pct` position inside the bands (0 = lower, 1 = upper); `dist_sma200` distance above the 200-day average; `mkt_vol20` the first fund's 20-day volatility; `pct_of_52w_high` close / 52-week high; `position_return` the trade's return so far; `ret1` the day's return; `rsi14` RSI, 14 days; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $311 | +203% | 16 | 44% | +32.8% | -9.2% | 2.07 | -55% | -$7,628 |
| Last 12 months | $320 | +1075% | 36 | 50% | +30.5% | -10.2% | 2.15 | -55% | -$7,628 |
| 2019 to Mar 2026 (bred on) | $75 | +4438% | 161 | 46% | +18.4% | -8.3% | 2.1 | -68% | -$5,551 |
| 2012 to 2018 | $63 | +2720% | 165 | 49% | +14.3% | -8.0% | 1.46 | -53% | -$4,349 |

Every rolling three-month stretch since 2019 (1878): 58% made money; the typical one made $37 a session and the worst -$363.

At 3x slippage: $302 a session over the last six months, $66 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-10-13): $309 a session over the last six months, $301 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -36% | -$37 | 9 | 22% |
| 2013 | +240% | $143 | 24 | 67% |
| 2014 | +58% | $63 | 40 | 45% |
| 2015 | -46% | -$52 | 17 | 35% |
| 2016 | +228% | $135 | 19 | 63% |
| 2017 | +330% | $166 | 40 | 52% |
| 2018 | +8% | $22 | 16 | 38% |
| 2019 | -11% | $3 | 16 | 38% |
| 2020 | +136% | $111 | 24 | 38% |
| 2021 | -6% | $18 | 38 | 47% |
| 2022 | -27% | -$25 | 6 | 33% |
| 2023 | +144% | $103 | 17 | 53% |
| 2024 | -31% | -$1 | 32 | 38% |
| 2025 | +1454% | $301 | 19 | 74% |
| 2026 | +264% | $263 | 25 | 44% |
