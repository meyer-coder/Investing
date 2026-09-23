# 41. AMDL / MUU / TSMX 52-Week High: within 7% of the high, 15% trailing stop

Funds: AMDL, MUU, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `pct_of_52w_high > 0.93 and close > sma50`
- **Sell** when `pct_of_52w_high < 0.85`
- **Risk:** stop 10.0% under entry (on a close), trailing stop 15.0% off the best close

Terms: `pct_of_52w_high` close / 52-week high; `sma50` 50-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $236 | +158% | 5 | 40% | +83.3% | -8.4% | 3.77 | -36% | -$5,438 |
| Last 12 months | $230 | +501% | 10 | 60% | +54.1% | -8.8% | 4.76 | -39% | -$5,438 |
| 2019 to Mar 2026 (bred on) | $36 | +377% | 36 | 47% | +28.7% | -11.2% | 2.07 | -52% | -$6,672 |
| 2012 to 2018 | $36 | +479% | 33 | 48% | +26.5% | -9.4% | 2.69 | -67% | -$4,318 |

Every rolling three-month stretch since 2019 (1878): 45% made money; the typical one made $0 a session and the worst -$166.

At 3x slippage: $234 a session over the last six months, $34 over 2019 to March 2026.

On the real funds (AMDL, MUU, TSMX, traded since 2025-10-13): $232 a session over the last six months, $217 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +37% | $38 | 1 | 100% |
| 2013 | +51% | $58 | 8 | 50% |
| 2014 | -30% | -$28 | 6 | 33% |
| 2015 | -28% | -$29 | 4 | 25% |
| 2016 | +81% | $73 | 4 | 50% |
| 2017 | +73% | $63 | 3 | 100% |
| 2018 | +77% | $80 | 7 | 43% |
| 2019 | +19% | $20 | 2 | 0% |
| 2020 | +40% | $53 | 8 | 50% |
| 2021 | +68% | $70 | 6 | 67% |
| 2022 | +0% | $0 | 0 | 0% |
| 2023 | -9% | -$3 | 3 | 0% |
| 2024 | -11% | $8 | 8 | 50% |
| 2025 | +50% | $63 | 7 | 43% |
| 2026 | +263% | $233 | 7 | 57% |
