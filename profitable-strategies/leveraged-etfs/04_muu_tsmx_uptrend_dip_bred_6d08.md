# 04. MUU / TSMX Uptrend Dip (bred 6D08)

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `(atr_pct < 0.06 and pct_of_52w_high < 0.9 and bb_pct > 0.8 or bb_pct > 0.85 or macd_hist > 0.7) and atr_pct > 0.0442`
- **Buy** when `ret1 < -0.02 and close > sma200 or vol20 < 0.23`
- **Buy** when `cross_above(macd, macd_signal) or cross_below(sma20, sma50)`
- **Sell** when `zscore20 < -0.78 or cross_above(close, bb_upper)`
- **Sell** when `vol_ratio_20_60 < 0.66 and ret20 > 0.19`
- **Risk:** stop 6.0% under entry (on a close), target 8.7% (on a close), trailing stop 10.6% off the best close, waits 1 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `bb_pct` position inside the bands (0 = lower, 1 = upper); `bb_upper` upper Bollinger band (20, 2); `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `macd` MACD line; `macd_hist` MACD histogram; `macd_signal` MACD signal line; `pct_of_52w_high` close / 52-week high; `ret1` the day's return; `ret20` 20-day return; `sma20` 20-day average; `sma200` 200-day average; `sma50` 50-day average; `vol20` 20-day volatility, annualised (0.6 = 60%); `vol_ratio_20_60` 20-day over 60-day volatility; `zscore20` standard deviations from the 20-day mean.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $489 | +682% | 37 | 57% | +18.2% | -9.4% | 2.3 | -38% | -$6,005 |
| Last 12 months | $487 | +6923% | 74 | 61% | +15.3% | -8.0% | 2.41 | -38% | -$6,005 |
| 2019 to Mar 2026 (bred on) | $94 | +16856% | 333 | 52% | +11.6% | -8.0% | 3.44 | -67% | -$5,630 |
| 2012 to 2018 | $48 | +833% | 265 | 51% | +9.7% | -7.0% | 1.16 | -67% | -$5,406 |

Every rolling three-month stretch since 2019 (1878): 67% made money; the typical one made $66 a session and the worst -$231.

At 3x slippage: $496 a session over the last six months, $81 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-10-13): $484 a session over the last six months, $387 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +40% | $46 | 33 | 55% |
| 2013 | +140% | $104 | 46 | 59% |
| 2014 | +55% | $60 | 39 | 54% |
| 2015 | -38% | -$36 | 27 | 37% |
| 2016 | +76% | $74 | 38 | 50% |
| 2017 | +173% | $117 | 40 | 62% |
| 2018 | -40% | -$32 | 42 | 36% |
| 2019 | +13% | $28 | 37 | 51% |
| 2020 | +167% | $127 | 42 | 55% |
| 2021 | +17% | $32 | 45 | 51% |
| 2022 | -53% | -$55 | 42 | 31% |
| 2023 | +44% | $52 | 42 | 40% |
| 2024 | +128% | $105 | 52 | 60% |
| 2025 | +596% | $225 | 57 | 63% |
| 2026 | +3422% | $567 | 53 | 60% |
