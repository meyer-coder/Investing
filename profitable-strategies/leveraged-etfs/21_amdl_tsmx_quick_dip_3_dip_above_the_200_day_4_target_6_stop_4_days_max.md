# 21. AMDL / TSMX Quick Dip: 3% dip above the 200-day, 4% target, 6% stop, 4 days max

Funds: AMDL, TSMX. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `ret1 < -0.03 and close > sma200`
- **Sell** when `bars_held >= 4`
- **Risk:** stop 6.0% under entry (on a close), target 4.0% (on a close)

Terms: `bars_held` sessions the trade has been held; `ret1` the day's return; `sma200` 200-day average.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $321 | +295% | 34 | 62% | +10.5% | -5.0% | 2.45 | -29% | -$4,989 |
| Last 12 months | $170 | +277% | 59 | 58% | +9.0% | -5.8% | 1.98 | -29% | -$4,989 |
| 2019 to Mar 2026 (bred on) | $38 | +417% | 248 | 56% | +8.1% | -7.6% | 1.22 | -67% | -$5,479 |
| 2012 to 2018 | $22 | +53% | 190 | 58% | +7.7% | -8.8% | 1.04 | -67% | -$12,119 |

Every rolling three-month stretch since 2019 (1878): 61% made money; the typical one made $25 a session and the worst -$208.

At 3x slippage: $300 a session over the last six months, $30 over 2019 to March 2026.

On the real funds (AMDL, TSMX, traded since 2025-07-23): $304 a session over the last six months, $150 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, TSMX $133 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -19% | -$16 | 27 | 52% |
| 2013 | +89% | $71 | 23 | 65% |
| 2014 | -41% | -$38 | 23 | 48% |
| 2015 | +12% | $14 | 11 | 64% |
| 2016 | +147% | $117 | 47 | 66% |
| 2017 | -35% | -$14 | 27 | 59% |
| 2018 | -6% | $18 | 32 | 53% |
| 2019 | +7% | $16 | 32 | 53% |
| 2020 | +120% | $106 | 52 | 62% |
| 2021 | -30% | -$24 | 37 | 46% |
| 2022 | -33% | -$32 | 9 | 33% |
| 2023 | +15% | $24 | 33 | 58% |
| 2024 | +213% | $136 | 43 | 58% |
| 2025 | +39% | $47 | 33 | 64% |
| 2026 | +271% | $221 | 43 | 58% |
