# 17. AMDL Uptrend Dip (bred 9D0B)

Funds: AMDL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `(ret1 < -0.06 and (close - low) / (high - low + 0.0001) < 0.28 and volume_ratio > 1.71 or cross_below(sma20, sma50)) and ret1 < 0.04 or cross_below(macd, macd_signal)`
- **Buy** when `dist_sma200 > -0.2 and rsi14 > 64 and vol_ratio_20_60 < 1.37 and rsi14 < 82 and pct_off_52w_low > 0.4`
- **Buy** when `ret1 < 0.03 and prev(ret1) < 0.004 and close > sma50 and rsi7 < 58`
- **Buy** when `ret5 < 0.052 and vol_ratio_20_60 > 1.31 and dist_sma200 < -0.24 or atr_pct < 0.0514`
- **Sell** when `ret1 > 0.02`
- **Sell** when `position_return > 0.04`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 12.3% under entry (on a close)

Terms: `atr_pct` 14-day average range as a share of price; `bars_held` sessions the trade has been held; `dist_sma200` distance above the 200-day average; `macd` MACD line; `macd_signal` MACD signal line; `pct_off_52w_low` gain off the 52-week low; `position_return` the trade's return so far; `prev` prev(x): x one session earlier; `ret1` the day's return; `ret5` 5-day return; `rsi14` RSI, 14 days; `rsi7` RSI, 7 days; `sma20` 20-day average; `sma50` 50-day average; `vol_ratio_20_60` 20-day over 60-day volatility; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $312 | +299% | 24 | 75% | +10.8% | -6.9% | 3.59 | -23% | -$3,509 |
| Last 12 months | $251 | +839% | 39 | 74% | +10.4% | -5.6% | 3.85 | -23% | -$3,509 |
| 2019 to Mar 2026 (bred on) | $49 | +1072% | 264 | 62% | +6.5% | -7.2% | 1.78 | -65% | -$5,505 |
| 2012 to 2018 | $60 | +2027% | 271 | 63% | +6.7% | -7.2% | 1.68 | -59% | -$4,586 |

Every rolling three-month stretch since 2019 (1878): 65% made money; the typical one made $45 a session and the worst -$312.

At 3x slippage: $324 a session over the last six months, $38 over 2019 to March 2026.

On the real fund (AMDL, traded since 2025-03-19): $350 a session over the last six months, $244 over its whole life.

Buying and holding over the last six months: AMDL $494 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +34% | $40 | 30 | 50% |
| 2013 | +23% | $35 | 32 | 62% |
| 2014 | +3% | $13 | 41 | 58% |
| 2015 | -20% | -$9 | 32 | 62% |
| 2016 | +175% | $136 | 58 | 67% |
| 2017 | +27% | $37 | 35 | 63% |
| 2018 | +346% | $167 | 43 | 72% |
| 2019 | +37% | $42 | 43 | 63% |
| 2020 | +1% | $27 | 43 | 58% |
| 2021 | -1% | $11 | 41 | 54% |
| 2022 | -14% | -$6 | 15 | 47% |
| 2023 | +117% | $92 | 42 | 69% |
| 2024 | -28% | -$21 | 35 | 54% |
| 2025 | +294% | $159 | 38 | 76% |
| 2026 | +554% | $292 | 31 | 77% |
