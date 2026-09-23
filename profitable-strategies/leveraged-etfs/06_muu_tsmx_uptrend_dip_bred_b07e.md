# 06. MUU / TSMX Uptrend Dip (bred B07E)

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `rsi14 < 32`
- **Buy** when `ret1 < -0.025 and close > sma200 or cross_above(macd, macd_signal)`
- **Buy** when `pct_off_52w_low < 0.84 and cross_above(close, bb_upper) and ret1 > 0.038`
- **Sell** when `cross_below(close, bb_lower)`
- **Sell** when `bars_held > 6`
- **Sell** when `ret5 > 0.04`
- **Risk:** stop 6.0% under entry (on a close), waits 1 sessions after an exit

Terms: `bars_held` sessions the trade has been held; `bb_lower` lower Bollinger band; `bb_upper` upper Bollinger band (20, 2); `cross_above` cross_above(a, b): a closed above b today after closing at or below it yesterday; `macd` MACD line; `macd_signal` MACD signal line; `pct_off_52w_low` gain off the 52-week low; `ret1` the day's return; `ret5` 5-day return; `rsi14` RSI, 14 days; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $492 | +692% | 36 | 56% | +17.9% | -6.0% | 2.15 | -34% | $-5,937 |
| Last 12 months | $418 | +3430% | 71 | 59% | +14.8% | -6.1% | 2.2 | -34% | $-5,937 |
| 2019 to Mar 2026 (bred on) | $116 | +107323% | 330 | 57% | +8.8% | -5.9% | 2.8 | -37% | $-8,826 |
| 2012 to 2018 | $41 | +657% | 291 | 55% | +6.9% | -6.0% | 1.2 | -53% | $-4,376 |

Every rolling three-month stretch since 2019 (1878): 86% made money; the typical one made $112 a session and the worst $-129.

At 3x slippage: $470 a session over the last six months, $97 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-10-13): $472 a session over the last six months, $384 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -1% | $8 | 40 | 55% |
| 2013 | +112% | $87 | 39 | 51% |
| 2014 | +28% | $36 | 48 | 48% |
| 2015 | +10% | $21 | 35 | 60% |
| 2016 | +31% | $39 | 44 | 57% |
| 2017 | +154% | $107 | 39 | 62% |
| 2018 | -23% | $-11 | 46 | 52% |
| 2019 | +75% | $66 | 39 | 59% |
| 2020 | +312% | $170 | 49 | 63% |
| 2021 | +57% | $61 | 52 | 54% |
| 2022 | +46% | $51 | 28 | 50% |
| 2023 | +35% | $42 | 44 | 59% |
| 2024 | +301% | $160 | 55 | 55% |
| 2025 | +342% | $176 | 48 | 56% |
| 2026 | +2056% | $498 | 51 | 59% |
