# 11. AMDL / TSMX Momentum (bred 831B)

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `dist_sma200 > -0.28 and volume_ratio < 1.24 and atr_pct > 0.0263 or volume_ratio > 1.89 or cross_above(macd, macd_signal) or cross_above(sma20, sma50)`
- **Buy** when `rsi14 > 67`
- **Sell** when `atr_pct < 0.0438`
- **Sell** when `vol_ratio_20_60 > 1.46`
- **Risk:** stop 5.0% under entry (on a close), target 30.0% (on a close), waits 2 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `dist_sma200` distance above the 200-day average; `macd` MACD line; `macd_signal` MACD signal line; `rsi14` RSI, 14 days; `sma20` 20-day average; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $350 | +327% | 17 | 53% | +32.6% | -6.1% | 3.66 | -31% | $-5,403 |
| Last 12 months | $284 | +882% | 27 | 48% | +37.7% | -7.2% | 3.28 | -33% | $-5,403 |
| 2019 to Mar 2026 (bred on) | $109 | +22142% | 212 | 36% | +25.6% | -7.9% | 1.74 | -68% | $-6,940 |
| 2012 to 2018 | $68 | +1327% | 227 | 42% | +15.0% | -7.6% | 1.33 | -64% | $-12,119 |

Every rolling three-month stretch since 2019 (1878): 76% made money; the typical one made $118 a session and the worst $-278.

At 3x slippage: $363 a session over the last six months, $99 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $411 a session over the last six months, $270 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +0% | $24 | 27 | 37% |
| 2013 | +27% | $54 | 37 | 40% |
| 2014 | +64% | $67 | 28 | 46% |
| 2015 | -28% | $-14 | 28 | 32% |
| 2016 | +417% | $201 | 37 | 54% |
| 2017 | -12% | $34 | 40 | 48% |
| 2018 | +107% | $111 | 30 | 33% |
| 2019 | +355% | $189 | 32 | 56% |
| 2020 | +289% | $179 | 34 | 44% |
| 2021 | +88% | $87 | 31 | 29% |
| 2022 | -62% | $-64 | 18 | 11% |
| 2023 | +60% | $67 | 28 | 25% |
| 2024 | +105% | $106 | 35 | 29% |
| 2025 | +225% | $161 | 30 | 43% |
| 2026 | +599% | $324 | 21 | 52% |
