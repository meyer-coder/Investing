# 49. SOXL / TQQQ / TECL Pullback in Uptrend: 8% five-day pullback above the 200-day

Funds: SOXL, TQQQ, TECL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret5 < -0.08 and close > sma200`
- **Sell** when `ret1 > 0.04`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 15.0% under entry (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `ret5` 5-day return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $213 | +139% | 17 | 59% | +15.3% | -7.1% | 3.24 | -21% | -$3,774 |
| Last 12 months | $139 | +207% | 32 | 59% | +11.2% | -6.3% | 2.84 | -21% | -$3,774 |
| 2019 to Mar 2026 (bred on) | $27 | +322% | 112 | 66% | +7.3% | -9.0% | 1.48 | -51% | -$3,529 |
| 2012 to 2018 | $22 | +277% | 79 | 67% | +6.1% | -6.3% | 1.44 | -42% | -$3,438 |

Every rolling three-month stretch since 2019 (1878): 61% made money; the typical one made $21 a session and the worst -$244.

At 3x slippage: $204 a session over the last six months, $22 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session, TQQQ $143 a session, TECL $223 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +37% | $35 | 12 | 67% |
| 2013 | +61% | $49 | 9 | 89% |
| 2014 | -4% | $0 | 13 | 54% |
| 2015 | +60% | $49 | 12 | 83% |
| 2016 | +39% | $35 | 8 | 75% |
| 2017 | +12% | $13 | 9 | 67% |
| 2018 | -28% | -$25 | 16 | 50% |
| 2019 | -11% | -$5 | 14 | 57% |
| 2020 | +31% | $36 | 15 | 60% |
| 2021 | +151% | $103 | 23 | 78% |
| 2022 | -32% | -$36 | 3 | 33% |
| 2023 | -6% | -$0 | 14 | 64% |
| 2024 | +22% | $29 | 20 | 75% |
| 2025 | +56% | $51 | 17 | 59% |
| 2026 | +181% | $175 | 23 | 61% |
