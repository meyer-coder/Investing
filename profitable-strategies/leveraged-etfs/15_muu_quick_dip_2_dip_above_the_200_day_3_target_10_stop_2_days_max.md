# 15. MUU Quick Dip: 2% dip above the 200-day, 3% target, 10% stop, 2 days max

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 2`
- **Risk:** stop 10.0% under entry (on a close), target 3.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $316 | +240% | 29 | 55% | +15.8% | -8.5% | 1.84 | -33% | $-4,976 |
| Last 12 months | $280 | +795% | 55 | 64% | +13.3% | -9.7% | 1.93 | -33% | $-5,442 |
| 2019 to Mar 2026 (bred on) | $34 | +500% | 162 | 60% | +7.3% | -7.3% | 1.59 | -66% | $-5,442 |
| 2012 to 2018 | $34 | +504% | 172 | 67% | +6.1% | -8.1% | 1.32 | -40% | $-4,655 |

Every rolling three-month stretch since 2019 (1878): 42% made money; the typical one made $0 a session and the worst $-235.

At 3x slippage: $297 a session over the last six months, $24 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $372 a session over the last six months, $275 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -13% | $-10 | 8 | 62% |
| 2013 | +63% | $59 | 37 | 70% |
| 2014 | +59% | $62 | 42 | 69% |
| 2015 | -15% | $-15 | 2 | 50% |
| 2016 | +24% | $24 | 14 | 79% |
| 2017 | +117% | $92 | 40 | 68% |
| 2018 | +16% | $27 | 29 | 55% |
| 2019 | -2% | $4 | 18 | 50% |
| 2020 | +44% | $44 | 18 | 78% |
| 2021 | +45% | $47 | 31 | 61% |
| 2022 | -40% | $-45 | 7 | 43% |
| 2023 | -16% | $-14 | 24 | 42% |
| 2024 | +100% | $76 | 28 | 68% |
| 2025 | +14% | $27 | 23 | 56% |
| 2026 | +764% | $368 | 42 | 64% |
