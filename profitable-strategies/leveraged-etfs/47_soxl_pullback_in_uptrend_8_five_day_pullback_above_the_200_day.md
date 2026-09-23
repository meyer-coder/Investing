# 47. SOXL Pullback in Uptrend: 8% five-day pullback above the 200-day

Funds: SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret5 < -0.08 and close > sma200`
- **Sell** when `ret1 > 0.04`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 15.0% under entry (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `ret5` 5-day return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $218 | +143% | 14 | 64% | +16.4% | -8.6% | 3.59 | -21% | -$3,774 |
| Last 12 months | $173 | +330% | 25 | 68% | +13.1% | -7.0% | 3.9 | -21% | -$3,774 |
| 2019 to Mar 2026 (bred on) | $29 | +399% | 85 | 72% | +7.3% | -10.0% | 1.85 | -49% | -$3,529 |
| 2012 to 2018 | $7 | +40% | 50 | 58% | +6.8% | -6.9% | 1.12 | -61% | -$3,438 |

Every rolling three-month stretch since 2019 (1878): 55% made money; the typical one made $20 a session and the worst -$230.

At 3x slippage: $209 a session over the last six months, $25 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +11% | $11 | 3 | 67% |
| 2013 | +55% | $45 | 7 | 100% |
| 2014 | -20% | -$19 | 10 | 40% |
| 2015 | +32% | $30 | 8 | 62% |
| 2016 | +47% | $40 | 6 | 83% |
| 2017 | +21% | $21 | 9 | 67% |
| 2018 | -57% | -$78 | 7 | 0% |
| 2019 | -5% | $1 | 12 | 67% |
| 2020 | +9% | $15 | 11 | 73% |
| 2021 | +153% | $102 | 22 | 77% |
| 2022 | -18% | -$17 | 3 | 67% |
| 2023 | -0% | $5 | 11 | 64% |
| 2024 | -3% | $6 | 12 | 67% |
| 2025 | +83% | $66 | 10 | 80% |
| 2026 | +216% | $192 | 18 | 67% |
