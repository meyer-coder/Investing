# 26. MUU Quick Dip: 2% dip above the 200-day, 3% target, 4% stop, 4 days max

Funds: MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 4.0% under entry (on a close), target 3.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $282 | +185% | 31 | 55% | +16.3% | -10.2% | 1.77 | -37% | $-4,947 |
| Last 12 months | $250 | +557% | 58 | 57% | +14.7% | -9.4% | 1.88 | -41% | $-6,177 |
| 2019 to Mar 2026 (bred on) | $42 | +926% | 168 | 60% | +7.9% | -7.3% | 1.63 | -54% | $-6,177 |
| 2012 to 2018 | $43 | +1038% | 175 | 62% | +7.0% | -7.0% | 1.65 | -44% | $-4,376 |

Every rolling three-month stretch since 2019 (1878): 47% made money; the typical one made $0 a session and the worst $-157.

At 3x slippage: $262 a session over the last six months, $37 over 2019 to March 2026.

On the real fund (MUU, traded since 2025-07-30): $307 a session over the last six months, $208 over its whole life.

Buying and holding over the last six months: MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -20% | $-20 | 8 | 38% |
| 2013 | +75% | $67 | 37 | 65% |
| 2014 | +26% | $36 | 40 | 60% |
| 2015 | -1% | $-0 | 2 | 50% |
| 2016 | +45% | $41 | 15 | 73% |
| 2017 | +104% | $84 | 39 | 67% |
| 2018 | +119% | $90 | 34 | 59% |
| 2019 | +26% | $30 | 21 | 57% |
| 2020 | +43% | $45 | 19 | 74% |
| 2021 | +65% | $60 | 32 | 62% |
| 2022 | -27% | $-29 | 9 | 33% |
| 2023 | +22% | $25 | 23 | 52% |
| 2024 | +69% | $60 | 27 | 70% |
| 2025 | -13% | $1 | 23 | 48% |
| 2026 | +657% | $349 | 45 | 60% |
