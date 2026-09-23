# 16. MUU Quick Dip: 3% dip above the 200-day, 2% target, 10% stop, 4 days max

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.03 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $315 | +249% | 26 | 65% | +15.7% | -12.8% | 1.95 | -33% | -$4,527 |
| Last 12 months | $286 | +941% | 50 | 72% | +13.0% | -12.9% | 2.05 | -33% | -$4,527 |
| 2019 to Mar 2026 (bred on) | $37 | +686% | 135 | 67% | +7.5% | -9.2% | 1.7 | -52% | -$5,347 |
| 2012 to 2018 | $27 | +299% | 130 | 68% | +6.1% | -8.4% | 1.21 | -40% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 44% made money; the typical one made $0 a session and the worst -$194.

At 3x slippage: $298 a session over the last six months, $31 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $317 a session over the last six months, $235 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +15% | $18 | 8 | 75% |
| 2013 | +125% | $89 | 29 | 79% |
| 2014 | +48% | $52 | 31 | 68% |
| 2015 | -9% | -$9 | 1 | 0% |
| 2016 | +12% | $14 | 13 | 77% |
| 2017 | +16% | $25 | 26 | 69% |
| 2018 | -13% | -$3 | 22 | 46% |
| 2019 | -1% | $4 | 14 | 57% |
| 2020 | +29% | $33 | 13 | 85% |
| 2021 | +83% | $68 | 30 | 67% |
| 2022 | -35% | -$39 | 6 | 50% |
| 2023 | +4% | $9 | 18 | 50% |
| 2024 | +82% | $71 | 22 | 73% |
| 2025 | +38% | $43 | 20 | 70% |
| 2026 | +588% | $330 | 38 | 71% |
