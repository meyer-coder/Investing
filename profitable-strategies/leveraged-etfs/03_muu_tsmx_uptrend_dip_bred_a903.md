# 03. MUU / TSMX Uptrend Dip (bred A903)

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `(bb_pct > 0.86 or macd_hist > 0.5) and atr_pct > 0.0534`
- **Buy** when `ret1 < -0.02 and close > sma200`
- **Buy** when `cross_above(macd, macd_signal)`
- **Sell** when `zscore20 < -0.78 or cross_above(close, bb_upper)`
- **Sell** when `vol_ratio_20_60 < 0.6 and ret20 > 0.14`
- **Risk:** stop 6.0% under entry (on a close), target 8.7% (on a close), trailing stop 10.6% off the best close, waits 1 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `bb_pct` position inside the bands (0 = lower, 1 = upper); `bb_upper` upper Bollinger band (20, 2); `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `macd` MACD line; `macd_hist` MACD histogram; `macd_signal` MACD signal line; `ret1` the day's return; `ret20` 20-day return; `sma200` 200-day average; `vol_ratio_20_60` 20-day over 60-day volatility; `zscore20` standard deviations from the 20-day mean.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $492 | +692% | 37 | 60% | +17.8% | -9.2% | 2.34 | -38% | -$6,005 |
| Last 12 months | $489 | +7113% | 73 | 64% | +15.4% | -8.1% | 2.46 | -38% | -$6,005 |
| 2019 to Mar 2026 (bred on) | $81 | +7373% | 302 | 53% | +11.2% | -7.8% | 3.49 | -69% | -$5,861 |
| 2012 to 2018 | $68 | +3761% | 252 | 53% | +9.8% | -7.1% | 1.27 | -56% | -$5,406 |

Every rolling three-month stretch since 2019 (1878): 69% made money; the typical one made $48 a session and the worst -$231.

At 3x slippage: $499 a session over the last six months, $71 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-07-30): $524 a session over the last six months, $435 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +63% | $60 | 31 | 58% |
| 2013 | +244% | $140 | 43 | 58% |
| 2014 | +73% | $69 | 36 | 58% |
| 2015 | -39% | -$37 | 25 | 36% |
| 2016 | +114% | $94 | 39 | 56% |
| 2017 | +240% | $139 | 36 | 64% |
| 2018 | -10% | $11 | 42 | 38% |
| 2019 | +1% | $17 | 30 | 50% |
| 2020 | +49% | $63 | 44 | 52% |
| 2021 | -9% | $5 | 41 | 46% |
| 2022 | -43% | -$36 | 38 | 34% |
| 2023 | +47% | $53 | 36 | 44% |
| 2024 | +111% | $97 | 45 | 64% |
| 2025 | +543% | $217 | 52 | 65% |
| 2026 | +3701% | $577 | 53 | 64% |
