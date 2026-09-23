# 09. MUU / SOXL Uptrend Dip (bred FBB5)

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret20 > 0.24 and ret1 < -0.02 and dist_sma20 > 0`
- **Buy** when `bb_pct < 0.05 and dist_sma200 > -0.1`
- **Buy** when `vol20 < 0.547 and macd_hist < -0.26 and mkt_ret20 < 0.035`
- **Sell** when `bb_pct > 0.75`
- **Sell** when `ret5 < -0.09`
- **Sell** when `portfolio_drawdown > -0.13 and pct_of_52w_high < 0.56`
- **Risk:** stop 10.0% under entry (on a close)

Terms: `bb_pct` position inside the bands (0 = lower, 1 = upper); `dist_sma20` distance above the 20-day average (0.05 = 5%); `dist_sma200` distance above the 200-day average; `macd_hist` MACD histogram; `mkt_ret20` the first fund's 20-day return; `pct_of_52w_high` close / 52-week high; `ret1` the day's return; `ret20` 20-day return; `ret5` 5-day return; `vol20` 20-day volatility, annualised (0.6 = 60%).

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $379 | +436% | 22 | 73% | +14.7% | -6.7% | 7.37 | -19% | -$4,527 |
| Last 12 months | $361 | +2485% | 48 | 73% | +13.0% | -6.2% | 6.2 | -21% | -$4,527 |
| 2019 to Mar 2026 (bred on) | $53 | +2460% | 181 | 57% | +8.4% | -5.9% | 2.53 | -37% | -$4,053 |
| 2012 to 2018 | $37 | +782% | 134 | 59% | +7.0% | -5.2% | 1.53 | -36% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 70% made money; the typical one made $40 a session and the worst -$139.

At 3x slippage: $364 a session over the last six months, $47 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-10-13): $379 a session over the last six months, $378 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -12% | -$11 | 18 | 61% |
| 2013 | +74% | $61 | 24 | 62% |
| 2014 | +240% | $133 | 22 | 73% |
| 2015 | -4% | -$2 | 9 | 56% |
| 2016 | +2% | $4 | 16 | 50% |
| 2017 | +15% | $22 | 20 | 50% |
| 2018 | +50% | $51 | 25 | 56% |
| 2019 | -10% | -$5 | 23 | 44% |
| 2020 | +61% | $56 | 23 | 61% |
| 2021 | +51% | $53 | 30 | 57% |
| 2022 | +0% | $7 | 16 | 44% |
| 2023 | +23% | $27 | 23 | 48% |
| 2024 | +9% | $14 | 22 | 50% |
| 2025 | +340% | $160 | 33 | 76% |
| 2026 | +961% | $371 | 33 | 73% |
