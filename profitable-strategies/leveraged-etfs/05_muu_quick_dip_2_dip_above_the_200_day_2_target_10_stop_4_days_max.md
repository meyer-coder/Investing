# 05. MUU Quick Dip: 2% dip above the 200-day, 2% target, 10% stop, 4 days max

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $479 | +651% | 30 | 70% | +15.5% | -10.5% | 2.99 | -31% | -$4,527 |
| Last 12 months | $328 | +1306% | 55 | 71% | +13.1% | -11.7% | 2.77 | -39% | -$6,177 |
| 2019 to Mar 2026 (bred on) | $43 | +948% | 157 | 67% | +7.4% | -8.7% | 1.54 | -53% | -$6,177 |
| 2012 to 2018 | $40 | +828% | 163 | 72% | +5.9% | -8.9% | 1.43 | -40% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 47% made money; the typical one made $0 a session and the worst -$176.

At 3x slippage: $459 a session over the last six months, $36 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $487 a session over the last six months, $286 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +15% | $17 | 8 | 75% |
| 2013 | +96% | $79 | 35 | 80% |
| 2014 | +53% | $59 | 39 | 67% |
| 2015 | -15% | -$15 | 2 | 50% |
| 2016 | +16% | $18 | 14 | 79% |
| 2017 | +104% | $82 | 38 | 79% |
| 2018 | +33% | $41 | 27 | 56% |
| 2019 | +8% | $14 | 18 | 56% |
| 2020 | +33% | $36 | 17 | 76% |
| 2021 | +112% | $84 | 33 | 70% |
| 2022 | -34% | -$36 | 7 | 57% |
| 2023 | +22% | $25 | 20 | 55% |
| 2024 | +186% | $118 | 29 | 79% |
| 2025 | -18% | -$5 | 21 | 52% |
| 2026 | +1276% | $436 | 42 | 74% |
