# 01. MUU / TSMX Uptrend Dip (bred 3BAF)

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `pct_off_52w_low < 0.84 and cross_above(close, bb_upper) and ret1 > 0.038`
- **Buy** when `ret1 < -0.026 and close > sma200 or rsi14 < 27`
- **Buy** when `cross_below(sma20, sma50) and zscore20 < 1.1 and dist_sma50 > -0.103`
- **Buy** when `mkt_vol20 < 0.314`
- **Sell** when `cross_below(close, bb_lower)`
- **Sell** when `ret5 > 0.05`
- **Sell** when `bars_held > 6`
- **Sell** when `vol20 < 0.335`
- **Risk:** stop 5.4% under entry (on a close), waits 1 sessions after an exit

Terms: `bars_held` sessions the trade has been held; `bb_lower` lower Bollinger band; `bb_upper` upper Bollinger band (20, 2); `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `dist_sma50` distance above the 50-day average; `mkt_vol20` the first fund's 20-day volatility; `pct_off_52w_low` gain off the 52-week low; `ret1` the day's return; `ret5` 5-day return; `rsi14` RSI, 14 days; `sma20` 20-day average; `sma200` 200-day average; `sma50` 50-day average; `vol20` 20-day volatility, annualised (0.6 = 60%); `zscore20` standard deviations from the 20-day mean.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $530 | +860% | 30 | 67% | +17.8% | -7.4% | 2.54 | -34% | -$5,937 |
| Last 12 months | $450 | +4614% | 63 | 62% | +16.0% | -6.6% | 2.57 | -34% | -$5,937 |
| 2019 to Mar 2026 (bred on) | $95 | +28730% | 259 | 54% | +9.3% | -5.5% | 2.71 | -45% | -$5,442 |
| 2012 to 2018 | $57 | +2477% | 250 | 56% | +7.5% | -5.5% | 1.37 | -37% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 76% made money; the typical one made $85 a session and the worst -$116.

At 3x slippage: $512 a session over the last six months, $83 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-10-13): $591 a session over the last six months, $463 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +33% | $37 | 29 | 59% |
| 2013 | +135% | $96 | 38 | 60% |
| 2014 | +10% | $21 | 41 | 44% |
| 2015 | +40% | $39 | 23 | 65% |
| 2016 | +91% | $74 | 34 | 62% |
| 2017 | +90% | $77 | 53 | 55% |
| 2018 | +48% | $55 | 32 | 50% |
| 2019 | +59% | $54 | 32 | 59% |
| 2020 | +277% | $148 | 32 | 66% |
| 2021 | +46% | $53 | 45 | 56% |
| 2022 | -31% | -$28 | 17 | 29% |
| 2023 | +3% | $12 | 35 | 46% |
| 2024 | +294% | $157 | 45 | 56% |
| 2025 | +384% | $189 | 38 | 55% |
| 2026 | +2219% | $508 | 45 | 64% |
