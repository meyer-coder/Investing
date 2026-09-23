# 90. AMDL / TSMX Momentum (bred 77AE)

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `dist_sma200 > -0.255 and volume_ratio <= 1.24 and atr_pct > 0.0235 or volume_ratio > 2.39 or cross_above(macd, macd_signal)`
- **Sell** when `atr_pct < 0.0438`
- **Sell** when `vol_ratio_20_60 > 1.46`
- **Risk:** stop 5.0% under entry (on a close), target 30.0% (on a close), waits 2 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `dist_sma200` distance above the 200-day average; `macd` MACD line; `macd_signal` MACD signal line; `vol_ratio_20_60` 20-day over 60-day volatility; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $317 | +251% | 18 | 50% | +34.6% | -8.2% | 2.29 | -31% | $-5,438 |
| Last 12 months | $320 | +1261% | 32 | 47% | +36.1% | -7.2% | 2.45 | -31% | $-5,438 |
| 2019 to Mar 2026 (bred on) | $110 | +27843% | 201 | 34% | +26.0% | -8.1% | 2.07 | -65% | $-6,940 |
| 2012 to 2018 | $69 | +1736% | 237 | 41% | +15.3% | -6.9% | 1.34 | -68% | $-12,119 |

Every rolling three-month stretch since 2019 (1878): 80% made money; the typical one made $131 a session and the worst $-292.

At 3x slippage: $329 a session over the last six months, $96 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $324 a session over the last six months, $265 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -19% | $-3 | 30 | 37% |
| 2013 | +47% | $71 | 36 | 39% |
| 2014 | +95% | $79 | 35 | 37% |
| 2015 | -35% | $-27 | 25 | 28% |
| 2016 | +676% | $236 | 39 | 54% |
| 2017 | +0% | $44 | 38 | 45% |
| 2018 | +57% | $80 | 34 | 41% |
| 2019 | +220% | $148 | 33 | 48% |
| 2020 | +180% | $144 | 25 | 40% |
| 2021 | +98% | $95 | 31 | 26% |
| 2022 | -44% | $-31 | 19 | 16% |
| 2023 | +64% | $70 | 28 | 25% |
| 2024 | +187% | $141 | 26 | 38% |
| 2025 | +195% | $149 | 33 | 36% |
| 2026 | +618% | $331 | 24 | 50% |
