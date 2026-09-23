# 20. MUU / SOXL Quick Dip: 2% dip above the 200-day, 4% target, 4% stop, 2 days max

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 4.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $327 | +234% | 44 | 48% | +16.3% | -8.1% | 1.49 | -40% | $-4,527 |
| Last 12 months | $307 | +965% | 83 | 54% | +13.7% | -8.0% | 1.58 | -40% | $-4,527 |
| 2019 to Mar 2026 (bred on) | $41 | +566% | 286 | 54% | +7.6% | -6.6% | 1.39 | -59% | $-5,347 |
| 2012 to 2018 | $47 | +1246% | 279 | 60% | +6.2% | -6.1% | 1.5 | -47% | $-4,704 |

Every rolling three-month stretch since 2019 (1878): 52% made money; the typical one made $9 a session and the worst $-237.

At 3x slippage: $299 a session over the last six months, $30 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-07-30): $306 a session over the last six months, $267 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -23% | $-23 | 18 | 33% |
| 2013 | +166% | $109 | 56 | 64% |
| 2014 | -22% | $-12 | 54 | 54% |
| 2015 | -0% | $5 | 24 | 58% |
| 2016 | +98% | $74 | 32 | 72% |
| 2017 | +137% | $99 | 49 | 63% |
| 2018 | +79% | $74 | 46 | 59% |
| 2019 | -24% | $-15 | 39 | 46% |
| 2020 | +93% | $81 | 40 | 70% |
| 2021 | +26% | $41 | 57 | 54% |
| 2022 | -40% | $-47 | 11 | 27% |
| 2023 | +27% | $34 | 49 | 51% |
| 2024 | +75% | $68 | 38 | 53% |
| 2025 | +10% | $25 | 34 | 53% |
| 2026 | +734% | $376 | 62 | 53% |
