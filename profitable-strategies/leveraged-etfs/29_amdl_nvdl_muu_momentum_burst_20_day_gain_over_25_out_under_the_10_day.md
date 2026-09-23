# 29. AMDL / NVDL / MUU Momentum Burst: 20-day gain over 25%, out under the 10-day

Funds: AMDL, NVDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret20 > 0.25 and close > sma10`
- **Sell** when `close < sma10`
- **Risk:** stop 10.0% under entry (on a close), trailing stop 15.0% off the best close

Terms: `ret20` 20-day return; `sma10` 10-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $273 | +166% | 13 | 38% | +61.0% | -11.1% | 1.6 | -51% | $-6,177 |
| Last 12 months | $205 | +307% | 22 | 46% | +49.0% | -10.8% | 1.78 | -52% | $-6,177 |
| 2019 to Mar 2026 (bred on) | $44 | +514% | 114 | 44% | +16.1% | -7.4% | 1.44 | -62% | $-5,112 |
| 2012 to 2018 | $45 | +547% | 107 | 33% | +24.9% | -6.7% | 1.56 | -58% | $-6,577 |

Every rolling three-month stretch since 2019 (1878): 62% made money; the typical one made $36 a session and the worst $-209.

At 3x slippage: $265 a session over the last six months, $39 over 2019 to March 2026.

On the real funds (AMDL, NVDL, MUU, traded since 2024-11-07): $276 a session over the last six months, $143 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, NVDL $118 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -28% | $-24 | 10 | 30% |
| 2013 | +142% | $116 | 12 | 58% |
| 2014 | +11% | $17 | 13 | 38% |
| 2015 | +9% | $18 | 16 | 12% |
| 2016 | -13% | $14 | 27 | 33% |
| 2017 | -16% | $1 | 20 | 25% |
| 2018 | +321% | $171 | 9 | 44% |
| 2019 | +23% | $32 | 13 | 54% |
| 2020 | +104% | $98 | 20 | 45% |
| 2021 | +65% | $64 | 14 | 36% |
| 2022 | -30% | $-22 | 16 | 31% |
| 2023 | +1% | $17 | 15 | 47% |
| 2024 | -18% | $0 | 16 | 31% |
| 2025 | +140% | $111 | 17 | 65% |
| 2026 | +184% | $219 | 16 | 38% |
