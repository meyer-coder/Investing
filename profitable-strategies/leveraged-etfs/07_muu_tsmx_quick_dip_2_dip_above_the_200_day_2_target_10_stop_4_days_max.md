# 07. MUU / TSMX Quick Dip: 2% dip above the 200-day, 2% target, 10% stop, 4 days max

Funds: MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 2.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $433 | +498% | 36 | 69% | +11.9% | -8.5% | 3.02 | -26% | -$5,937 |
| Last 12 months | $297 | +967% | 71 | 68% | +10.4% | -9.0% | 2.65 | -34% | -$5,937 |
| 2019 to Mar 2026 (bred on) | $76 | +8293% | 259 | 66% | +6.7% | -7.0% | 1.86 | -52% | -$5,654 |
| 2012 to 2018 | $38 | +654% | 247 | 67% | +5.0% | -6.8% | 1.24 | -43% | -$4,376 |

Every rolling three-month stretch since 2019 (1878): 68% made money; the typical one made $59 a session and the worst -$230.

At 3x slippage: $410 a session over the last six months, $65 over 2019 to March 2026.

On the real funds (MUU, TSMX, traded since 2025-07-30): $431 a session over the last six months, $275 over its whole life.

Buying and holding over the last six months: MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +39% | $39 | 32 | 69% |
| 2013 | +30% | $38 | 39 | 69% |
| 2014 | +82% | $74 | 43 | 65% |
| 2015 | -24% | -$24 | 19 | 53% |
| 2016 | +100% | $74 | 34 | 76% |
| 2017 | +66% | $59 | 43 | 72% |
| 2018 | -9% | $6 | 37 | 57% |
| 2019 | +2% | $10 | 26 | 62% |
| 2020 | +235% | $140 | 44 | 70% |
| 2021 | +85% | $73 | 40 | 65% |
| 2022 | -43% | -$50 | 8 | 50% |
| 2023 | +0% | $9 | 35 | 51% |
| 2024 | +619% | $219 | 51 | 78% |
| 2025 | +98% | $85 | 39 | 64% |
| 2026 | +880% | $387 | 52 | 71% |
