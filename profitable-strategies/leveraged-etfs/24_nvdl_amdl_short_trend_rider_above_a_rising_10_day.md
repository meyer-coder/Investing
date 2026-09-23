# 24. NVDL / AMDL Short-Trend Rider: above a rising 10-day

Funds: NVDL, AMDL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `close > sma10 and sma20_slope > 0 and ret5 > 0`
- **Sell** when `close < sma10`
- **Risk:** stop 10.0% under entry (on a close)

Terms: `ret5` 5-day return; `sma10` 10-day average; `sma20_slope` 5-day change of the 20-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $292 | +213% | 15 | 40% | +51.2% | -6.5% | 2.29 | -49% | -$5,438 |
| Last 12 months | $111 | +104% | 26 | 31% | +39.7% | -6.0% | 1.68 | -49% | -$5,438 |
| 2019 to Mar 2026 (bred on) | $60 | +1591% | 120 | 41% | +20.1% | -7.3% | 1.2 | -68% | -$8,492 |
| 2012 to 2018 | $42 | +387% | 131 | 42% | +16.1% | -7.1% | 1.39 | -67% | -$8,100 |

Every rolling three-month stretch since 2019 (1878): 63% made money; the typical one made $44 a session and the worst -$244.

At 3x slippage: $282 a session over the last six months, $55 over 2019 to March 2026.

On the real funds (NVDL, AMDL, traded since 2024-04-22): $300 a session over the last six months, $61 over its whole life.

Buying and holding over the last six months: NVDL $118 a session, AMDL $494 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +20% | $27 | 12 | 42% |
| 2013 | -46% | -$42 | 20 | 35% |
| 2014 | -3% | $12 | 17 | 65% |
| 2015 | +52% | $60 | 20 | 30% |
| 2016 | +104% | $99 | 27 | 48% |
| 2017 | -11% | $8 | 22 | 36% |
| 2018 | +177% | $130 | 13 | 38% |
| 2019 | +49% | $56 | 18 | 44% |
| 2020 | +157% | $127 | 20 | 45% |
| 2021 | +215% | $133 | 15 | 40% |
| 2022 | -33% | -$24 | 15 | 33% |
| 2023 | +94% | $88 | 16 | 50% |
| 2024 | +67% | $73 | 14 | 43% |
| 2025 | -16% | $2 | 15 | 47% |
| 2026 | +142% | $174 | 22 | 27% |
