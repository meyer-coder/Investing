# 27. MUU Quick Dip: 2% dip above the 200-day, 4% target, 10% stop, 4 days max

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $382 | +354% | 28 | 61% | +16.6% | -9.8% | 2.08 | -36% | -$4,976 |
| Last 12 months | $239 | +463% | 51 | 61% | +14.5% | -11.1% | 1.86 | -47% | -$6,177 |
| 2019 to Mar 2026 (bred on) | $27 | +233% | 138 | 64% | +8.1% | -10.1% | 1.23 | -62% | -$6,177 |
| 2012 to 2018 | $45 | +1078% | 152 | 67% | +7.7% | -9.3% | 1.43 | -37% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 43% made money; the typical one made $0 a session and the worst -$224.

At 3x slippage: $364 a session over the last six months, $23 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $280 a session over the last six months, $177 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -17% | -$14 | 6 | 33% |
| 2013 | +151% | $106 | 33 | 79% |
| 2014 | +48% | $54 | 37 | 65% |
| 2015 | -15% | -$15 | 2 | 50% |
| 2016 | +32% | $31 | 14 | 79% |
| 2017 | +196% | $124 | 34 | 74% |
| 2018 | +15% | $27 | 26 | 50% |
| 2019 | -5% | $2 | 15 | 53% |
| 2020 | +23% | $29 | 14 | 71% |
| 2021 | +51% | $51 | 28 | 68% |
| 2022 | -35% | -$37 | 7 | 57% |
| 2023 | +25% | $28 | 20 | 55% |
| 2024 | +138% | $96 | 24 | 79% |
| 2025 | -30% | -$20 | 19 | 47% |
| 2026 | +537% | $332 | 39 | 64% |
