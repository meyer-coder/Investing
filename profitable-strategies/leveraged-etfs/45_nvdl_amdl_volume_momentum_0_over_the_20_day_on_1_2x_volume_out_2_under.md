# 45. NVDL / AMDL Volume Momentum: 0% over the 20-day on 1.2x volume, out 2% under

Funds: NVDL, AMDL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `mkt_above_sma200 == 1 and dist_sma20 > 0.0 and volume_ratio > 1.2`
- **Sell** when `dist_sma20 < -0.02`
- **Sell** when `mkt_above_sma200 == 0`
- **Risk:** stop 12.0% under entry (on a close), waits 5 sessions after an exit

Terms: `dist_sma20` distance above the 20-day average (0.05 = 5%); `mkt_above_sma200` 1 when the first fund is above its 200-day average; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $292 | +231% | 5 | 40% | +106.2% | -5.3% | 6.71 | -35% | -$5,438 |
| Last 12 months | $112 | +99% | 10 | 30% | +71.4% | -9.2% | 2.5 | -53% | -$8,393 |
| 2019 to Mar 2026 (bred on) | $46 | +597% | 50 | 32% | +45.2% | -9.0% | 1.26 | -68% | -$8,393 |
| 2012 to 2018 | $46 | +467% | 53 | 40% | +33.9% | -10.0% | 2.4 | -70% | -$8,100 |

Every rolling three-month stretch since 2019 (1878): 48% made money; the typical one made $0 a session and the worst -$297.

At 3x slippage: $289 a session over the last six months, $43 over 2019 to March 2026.

On the real funds (NVDL, AMDL, traded since 2025-01-02): $223 a session over the last six months, $13 over its whole life.

Buying and holding over the last six months: NVDL $118 a session, AMDL $494 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -22% | -$23 | 4 | 0% |
| 2013 | -19% | -$1 | 7 | 29% |
| 2014 | -35% | -$24 | 10 | 30% |
| 2015 | +58% | $66 | 9 | 44% |
| 2016 | +160% | $122 | 9 | 67% |
| 2017 | -20% | $13 | 9 | 44% |
| 2018 | +318% | $169 | 5 | 40% |
| 2019 | +30% | $31 | 2 | 50% |
| 2020 | +32% | $51 | 10 | 20% |
| 2021 | +62% | $71 | 10 | 40% |
| 2022 | -15% | -$15 | 3 | 0% |
| 2023 | +263% | $158 | 6 | 67% |
| 2024 | +11% | $37 | 10 | 30% |
| 2025 | +15% | $31 | 6 | 17% |
| 2026 | +113% | $158 | 8 | 38% |
