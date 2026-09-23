# 42. AMDL / MUU Volume Momentum: 0% over the 20-day on 1x volume, out 4% under

Funds: AMDL, MUU. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `mkt_above_sma200 == 1 and dist_sma20 > 0.0 and volume_ratio > 1.0`
- **Sell** when `dist_sma20 < -0.04`
- **Sell** when `mkt_above_sma200 == 0`
- **Risk:** stop 12.0% under entry (on a close), waits 5 sessions after an exit

Terms: `dist_sma20` distance above the 20-day average (0.05 = 5%); `mkt_above_sma200` 1 when the first fund is above its 200-day average; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $380 | +311% | 7 | 43% | +115.9% | -13.5% | 3.93 | -45% | -$6,596 |
| Last 12 months | $271 | +605% | 11 | 55% | +103.1% | -13.9% | 4.18 | -51% | -$6,596 |
| 2019 to Mar 2026 (bred on) | $35 | +203% | 47 | 36% | +40.1% | -10.7% | 1.7 | -68% | -$5,551 |
| 2012 to 2018 | $36 | +256% | 47 | 34% | +38.0% | -10.4% | 1.82 | -66% | -$7,186 |

Every rolling three-month stretch since 2019 (1878): 44% made money; the typical one made $0 a session and the worst -$284.

At 3x slippage: $377 a session over the last six months, $33 over 2019 to March 2026.

On the real funds (AMDL, MUU, traded since 2025-07-31): $232 a session over the last six months, $274 over its whole life.

Buying and holding over the last six months: AMDL $494 a session, MUU $438 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | -33% | -$37 | 4 | 0% |
| 2013 | +29% | $65 | 12 | 42% |
| 2014 | +18% | $32 | 7 | 29% |
| 2015 | -2% | -$2 | 1 | 0% |
| 2016 | +32% | $40 | 4 | 25% |
| 2017 | -23% | $1 | 10 | 30% |
| 2018 | +248% | $151 | 9 | 56% |
| 2019 | +8% | $21 | 4 | 0% |
| 2020 | +24% | $48 | 8 | 25% |
| 2021 | -25% | -$7 | 10 | 40% |
| 2022 | -25% | -$25 | 3 | 0% |
| 2023 | +16% | $32 | 9 | 22% |
| 2024 | +8% | $29 | 6 | 67% |
| 2025 | +264% | $156 | 5 | 80% |
| 2026 | +259% | $261 | 9 | 44% |
