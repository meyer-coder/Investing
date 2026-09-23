# 35. SOXL / TQQQ / TECL Uptrend Dip (bred 01D4)

Funds: SOXL, TQQQ, TECL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `dist_sma20 < -0.054 and cross_above(close, sma200)`
- **Buy** when `dist_sma20 < -0.02 and sma20 > sma50 and sma50 > sma200 or ret1 < -0.01 or vol_ratio_20_60 < 0.66`
- **Buy** when `macd_hist > 1.7`
- **Sell** when `ret1 > 0.02`
- **Sell** when `close < sma50`
- **Sell** when `mkt_vol20 < 0.38 and cross_below(close, bb_lower)`
- **Risk:** stop 16.0% under entry (on a close)

Terms: `bb_lower` lower Bollinger band; `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `dist_sma20` distance above the 20-day average (0.05 = 5%); `macd_hist` MACD histogram; `mkt_vol20` the first fund's 20-day volatility; `ret1` the day's return; `sma20` 20-day average; `sma200` 200-day average; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $254 | +164% | 84 | 57% | +6.9% | -5.8% | 1.35 | -45% | $-5,145 |
| Last 12 months | $212 | +422% | 135 | 58% | +6.4% | -5.5% | 1.4 | -45% | $-5,145 |
| 2019 to Mar 2026 (bred on) | $92 | +10117% | 743 | 60% | +5.3% | -5.7% | 1.45 | -65% | $-7,387 |
| 2012 to 2018 | $25 | +160% | 610 | 56% | +4.0% | -4.5% | 1.05 | -67% | $-3,929 |

Every rolling three-month stretch since 2019 (1878): 74% made money; the typical one made $88 a session and the worst $-230.

At 3x slippage: $206 a session over the last six months, $62 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session, TQQQ $143 a session, TECL $223 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -4% | $8 | 100 | 53% |
| 2013 | +80% | $64 | 69 | 67% |
| 2014 | +23% | $28 | 83 | 60% |
| 2015 | +17% | $30 | 107 | 56% |
| 2016 | +1% | $12 | 81 | 54% |
| 2017 | +107% | $79 | 60 | 65% |
| 2018 | -50% | $-46 | 110 | 47% |
| 2019 | +147% | $104 | 91 | 66% |
| 2020 | +330% | $198 | 110 | 68% |
| 2021 | +24% | $40 | 101 | 55% |
| 2022 | -35% | $-7 | 121 | 50% |
| 2023 | +99% | $85 | 85 | 59% |
| 2024 | -9% | $14 | 101 | 58% |
| 2025 | +257% | $161 | 111 | 60% |
| 2026 | +388% | $275 | 107 | 60% |
