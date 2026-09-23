# 22. SOXL / NVDL / AMDL / AVGX / TSMX / MUU Trend Breakout (bred 7752)

Funds: SOXL, NVDL, AMDL, AVGX, TSMX, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `vol_ratio_20_60 < 0.75 and close > sma50`
- **Buy** when `ret20 > -0.01 and ret5 < -0.082 and cross_above(close, sma50)`
- **Buy** when `cross_above(sma20, sma50)`
- **Buy** when `ret5 < -0.099 and vol_ratio_20_60 > 1.49`
- **Sell** when `vol_ratio_20_60 > 1.21`
- **Risk:** trailing stop 7.3% off the best close

Terms: `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `ret20` 20-day return; `ret5` 5-day return; `sma20` 20-day average; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $298 | +260% | 7 | 57% | +48.8% | -5.9% | 5.8 | -27% | $-3,377 |
| Last 12 months | $229 | +626% | 15 | 67% | +39.1% | -7.2% | 5.94 | -27% | $-3,377 |
| 2019 to Mar 2026 (bred on) | $110 | +59853% | 133 | 50% | +20.5% | -6.8% | 2.9 | -69% | $-8,707 |
| 2012 to 2018 | $70 | +2755% | 117 | 51% | +15.6% | -7.9% | 1.37 | -53% | $-6,577 |

Every rolling three-month stretch since 2019 (1878): 71% made money; the typical one made $99 a session and the worst $-300.

At 3x slippage: $293 a session over the last six months, $103 over 2019 to March 2026.

On the real funds (SOXL, NVDL, AMDL, AVGX, TSMX, MUU, traded since 2024-12-19): $318 a session over the last six months, $219 over its whole life.

Buying and holding over the last six months: SOXL $335 a session, NVDL $118 a session, AMDL $494 a session, AVGX $79 a session, TSMX $133 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -23% | $-17 | 11 | 36% |
| 2013 | +150% | $110 | 14 | 64% |
| 2014 | +30% | $35 | 18 | 39% |
| 2015 | +69% | $75 | 24 | 50% |
| 2016 | +484% | $240 | 20 | 60% |
| 2017 | +96% | $81 | 14 | 64% |
| 2018 | -41% | $-36 | 16 | 44% |
| 2019 | +141% | $102 | 16 | 44% |
| 2020 | +785% | $261 | 31 | 61% |
| 2021 | +176% | $115 | 14 | 57% |
| 2022 | -29% | $-27 | 8 | 25% |
| 2023 | +207% | $137 | 21 | 43% |
| 2024 | -42% | $-38 | 20 | 30% |
| 2025 | +479% | $203 | 20 | 65% |
| 2026 | +397% | $260 | 10 | 60% |
