# 43. SOXL Pullback in Uptrend: 12% five-day pullback above the 200-day

Funds: SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret5 < -0.12 and close > sma200`
- **Sell** when `ret1 > 0.04`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 15.0% under entry (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `ret5` 5-day return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $230 | +165% | 13 | 62% | +18.4% | -6.9% | 4.12 | -21% | $-3,774 |
| Last 12 months | $154 | +272% | 20 | 60% | +15.9% | -5.2% | 4.29 | -21% | $-3,774 |
| 2019 to Mar 2026 (bred on) | $21 | +224% | 55 | 64% | +8.8% | -8.0% | 1.8 | -41% | $-3,529 |
| 2012 to 2018 | $12 | +115% | 25 | 64% | +7.2% | -3.6% | 2.85 | -28% | $-3,563 |

Every rolling three-month stretch since 2019 (1878): 52% made money; the typical one made $5 a session and the worst $-134.

At 3x slippage: $222 a session over the last six months, $18 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +6% | $6 | 2 | 100% |
| 2013 | +12% | $12 | 2 | 100% |
| 2014 | +11% | $11 | 5 | 60% |
| 2015 | +38% | $33 | 4 | 75% |
| 2016 | +20% | $19 | 4 | 75% |
| 2017 | -8% | $-8 | 3 | 33% |
| 2018 | +7% | $12 | 5 | 40% |
| 2019 | -14% | $-12 | 5 | 40% |
| 2020 | -1% | $4 | 7 | 86% |
| 2021 | +131% | $90 | 16 | 81% |
| 2022 | -11% | $-10 | 2 | 50% |
| 2023 | +23% | $24 | 7 | 57% |
| 2024 | +2% | $9 | 9 | 44% |
| 2025 | +21% | $21 | 6 | 50% |
| 2026 | +225% | $192 | 16 | 62% |
