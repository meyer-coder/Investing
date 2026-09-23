# 47. MUU / AMDL / SOXL Momentum Burst: 20-day gain over 40%, out under the 10-day

Funds: MUU, AMDL, SOXL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret20 > 0.4 and close > sma10`
- **Sell** when `close < sma10`
- **Risk:** stop 10.0% under entry (on a close), trailing stop 15.0% off the best close

Terms: `ret20` 20-day return; `sma10` 10-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $223 | +118% | 7 | 57% | +52.1% | -15.6% | 1.98 | -41% | $-6,177 |
| Last 12 months | $215 | +377% | 15 | 60% | +38.7% | -12.0% | 2.26 | -41% | $-6,177 |
| 2019 to Mar 2026 (bred on) | $22 | +92% | 68 | 37% | +18.1% | -7.1% | 1.39 | -59% | $-4,781 |
| 2012 to 2018 | $22 | +90% | 63 | 36% | +23.6% | -8.8% | 1.21 | -70% | $-6,283 |

Every rolling three-month stretch since 2019 (1878): 46% made money; the typical one made $0 a session and the worst $-170.

At 3x slippage: $219 a session over the last six months, $19 over 2019 to March 2026.

On the real funds (MUU, AMDL, SOXL, traded since 2024-11-07): $217 a session over the last six months, $144 over its whole life.

Buying and holding over the last six months: MUU $438 a session, AMDL $494 a session, SOXL $335 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -11% | $-5 | 6 | 33% |
| 2013 | +85% | $78 | 8 | 38% |
| 2014 | +3% | $6 | 5 | 60% |
| 2015 | -25% | $-21 | 6 | 17% |
| 2016 | -15% | $6 | 18 | 33% |
| 2017 | -41% | $-43 | 12 | 33% |
| 2018 | +197% | $136 | 8 | 50% |
| 2019 | -34% | $-32 | 11 | 18% |
| 2020 | +30% | $45 | 10 | 50% |
| 2021 | -10% | $-4 | 7 | 14% |
| 2022 | -20% | $-18 | 8 | 25% |
| 2023 | +11% | $20 | 8 | 50% |
| 2024 | -19% | $-12 | 9 | 33% |
| 2025 | +127% | $103 | 13 | 54% |
| 2026 | +233% | $233 | 9 | 56% |
