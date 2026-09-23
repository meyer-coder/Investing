# 14. MUU / SOXL Quick Dip: 2% dip above the 200-day, 4% target, 10% stop, 4 days max

Funds: MUU, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.02 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 10.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $347 | +255% | 37 | 57% | +16.6% | -11.7% | 1.55 | -50% | -$5,927 |
| Last 12 months | $273 | +621% | 65 | 60% | +14.7% | -11.8% | 1.57 | -50% | -$5,927 |
| 2019 to Mar 2026 (bred on) | $57 | +1781% | 227 | 64% | +7.8% | -9.1% | 1.53 | -62% | -$5,347 |
| 2012 to 2018 | $41 | +750% | 213 | 65% | +6.8% | -8.8% | 1.32 | -49% | -$4,707 |

Every rolling three-month stretch since 2019 (1878): 61% made money; the typical one made $41 a session and the worst -$199.

At 3x slippage: $324 a session over the last six months, $49 over 2019 to March 2026.

On the real funds (MUU, SOXL, traded since 2025-07-30): $317 a session over the last six months, $257 over its whole life.

Buying and holding over the last six months: MUU $438 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -18% | -$16 | 15 | 47% |
| 2013 | +149% | $104 | 41 | 73% |
| 2014 | +10% | $23 | 41 | 66% |
| 2015 | -31% | -$31 | 18 | 50% |
| 2016 | +89% | $71 | 27 | 78% |
| 2017 | +117% | $92 | 37 | 70% |
| 2018 | +35% | $46 | 34 | 56% |
| 2019 | +32% | $42 | 34 | 59% |
| 2020 | +79% | $74 | 31 | 71% |
| 2021 | +8% | $27 | 46 | 61% |
| 2022 | -32% | -$33 | 8 | 62% |
| 2023 | +100% | $83 | 37 | 65% |
| 2024 | +131% | $100 | 32 | 69% |
| 2025 | +21% | $36 | 25 | 56% |
| 2026 | +597% | $356 | 51 | 63% |
