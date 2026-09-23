# 50. AMDL / MUU 52-Week High: within 7% of the high, 10% trailing stop

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `pct_of_52w_high > 0.93 and close > sma50`
- **Sell** when `pct_of_52w_high < 0.85`
- **Risk:** stop 10.0% under entry (on a close), trailing stop 10.0% off the best close

Terms: `pct_of_52w_high` close / 52-week high; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $214 | +134% | 7 | 29% | +83.3% | -6.9% | 2.57 | -38% | -$5,438 |
| Last 12 months | $179 | +269% | 15 | 40% | +55.4% | -8.8% | 2.57 | -46% | -$5,438 |
| 2019 to Mar 2026 (bred on) | $28 | +246% | 36 | 47% | +22.2% | -9.2% | 1.81 | -54% | -$4,781 |
| 2012 to 2018 | $36 | +405% | 43 | 44% | +27.5% | -9.5% | 1.89 | -58% | -$4,979 |

Every rolling three-month stretch since 2019 (1878): 41% made money; the typical one made $0 a session and the worst -$180.

At 3x slippage: $210 a session over the last six months, $26 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2025-10-13): $212 a session over the last six months, $162 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +0% | $0 | 0 | 0% |
| 2013 | +111% | $89 | 7 | 43% |
| 2014 | -8% | $0 | 8 | 25% |
| 2015 | -19% | -$21 | 1 | 0% |
| 2016 | +24% | $45 | 8 | 50% |
| 2017 | +41% | $53 | 11 | 64% |
| 2018 | +85% | $81 | 8 | 38% |
| 2019 | +45% | $39 | 1 | 100% |
| 2020 | +8% | $20 | 5 | 40% |
| 2021 | +39% | $49 | 9 | 56% |
| 2022 | +0% | $0 | 0 | 0% |
| 2023 | -26% | -$26 | 4 | 0% |
| 2024 | +2% | $17 | 9 | 56% |
| 2025 | +55% | $59 | 7 | 43% |
| 2026 | +218% | $210 | 8 | 38% |
