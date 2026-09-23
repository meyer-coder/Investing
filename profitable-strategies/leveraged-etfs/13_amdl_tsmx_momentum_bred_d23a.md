# 13. AMDL / TSMX Momentum (bred D23A)

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `dist_sma200 > -0.28 and volume_ratio < 1.24 and atr_pct > 0.0263 or volume_ratio > 1.89 or cross_above(macd, macd_signal)`
- **Sell** when `atr_pct < 0.0438`
- **Risk:** stop 5.0% under entry (on a close), target 30.0% (on a close), waits 2 sessions after an exit

Terms: `atr_pct` 14-day average range as a share of price; `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `dist_sma200` distance above the 200-day average; `macd` MACD line; `macd_signal` MACD signal line; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $317 | +251% | 18 | 50% | +34.6% | -8.2% | 2.29 | -31% | -$5,438 |
| Last 12 months | $293 | +933% | 30 | 47% | +38.0% | -8.4% | 2.3 | -31% | -$5,438 |
| 2019 to Mar 2026 (bred on) | $116 | +40068% | 195 | 36% | +25.9% | -8.1% | 1.99 | -67% | -$6,940 |
| 2012 to 2018 | $78 | +2758% | 230 | 42% | +15.8% | -7.5% | 1.45 | -68% | -$12,119 |

Every rolling three-month stretch since 2019 (1878): 80% made money; the typical one made $129 a session and the worst -$278.

At 3x slippage: $329 a session over the last six months, $100 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $388 a session over the last six months, $293 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +0% | $24 | 27 | 37% |
| 2013 | +24% | $52 | 37 | 40% |
| 2014 | +40% | $56 | 33 | 48% |
| 2015 | -30% | -$18 | 29 | 31% |
| 2016 | +775% | $250 | 38 | 53% |
| 2017 | +29% | $71 | 34 | 41% |
| 2018 | +107% | $111 | 32 | 38% |
| 2019 | +339% | $186 | 30 | 53% |
| 2020 | +328% | $186 | 24 | 42% |
| 2021 | +67% | $75 | 32 | 28% |
| 2022 | -61% | -$67 | 18 | 11% |
| 2023 | +67% | $72 | 27 | 26% |
| 2024 | +188% | $141 | 28 | 36% |
| 2025 | +421% | $210 | 31 | 45% |
| 2026 | +359% | $269 | 23 | 48% |
