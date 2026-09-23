# 12. AMDL Uptrend Dip (bred 852D)

Funds: AMDL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `(ret1 < -0.06 and (close - low) / (high - low + 0.0001) < 0.28 and volume_ratio > 1.71 or cross_below(sma20, sma50)) and ret1 < 0.04`
- **Buy** when `dist_sma200 > -0.2 and rsi14 > 64 and vol_ratio_20_60 < 1.37`
- **Buy** when `ret1 < 0.03 and prev(ret1) < 0.004 and close > sma50 and rsi7 < 58`
- **Buy** when `ret5 < 0.052 and vol_ratio_20_60 > 1.31 and dist_sma200 < -0.24 or atr_pct < 0.0514 or rsi7 > 76`
- **Sell** when `ret1 > 0.02`
- **Sell** when `position_return > 0.04`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 12.0% under entry (on a close)

Terms: `atr_pct` 14-day average range as a share of price; `bars_held` sessions the trade has been held; `dist_sma200` distance above the 200-day average; `position_return` the trade's return so far; `prev` prev(x): x one session earlier; `ret1` the day's return; `ret5` 5-day return; `rsi14` RSI, 14 days; `rsi7` RSI, 7 days; `sma20` 20-day average; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $341 | +357% | 23 | 78% | +11.6% | -7.8% | 3.55 | -23% | -$3,509 |
| Last 12 months | $269 | +931% | 38 | 76% | +11.3% | -6.9% | 3.6 | -23% | -$3,866 |
| 2019 to Mar 2026 (bred on) | $52 | +1298% | 255 | 63% | +6.7% | -7.5% | 1.84 | -64% | -$5,505 |
| 2012 to 2018 | $60 | +1928% | 270 | 62% | +7.0% | -7.4% | 1.63 | -61% | -$4,979 |

Every rolling three-month stretch since 2019 (1878): 63% made money; the typical one made $34 a session and the worst -$228.

At 3x slippage: $353 a session over the last six months, $41 over 2019 to March 2026.

On the real fund (AMDL, traded since 2024-12-31): $381 a session over the last six months, $238 over its whole life.

Buying and holding over the last six months: AMDL $494 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -0% | $12 | 30 | 47% |
| 2013 | +169% | $117 | 35 | 74% |
| 2014 | +7% | $16 | 38 | 58% |
| 2015 | -20% | -$8 | 37 | 60% |
| 2016 | +121% | $114 | 54 | 65% |
| 2017 | -30% | -$21 | 34 | 56% |
| 2018 | +473% | $193 | 42 | 71% |
| 2019 | +42% | $46 | 40 | 65% |
| 2020 | +19% | $43 | 43 | 60% |
| 2021 | -17% | -$6 | 40 | 52% |
| 2022 | -32% | -$31 | 14 | 43% |
| 2023 | +142% | $102 | 39 | 72% |
| 2024 | -16% | -$7 | 33 | 55% |
| 2025 | +476% | $207 | 41 | 78% |
| 2026 | +477% | $274 | 28 | 79% |
