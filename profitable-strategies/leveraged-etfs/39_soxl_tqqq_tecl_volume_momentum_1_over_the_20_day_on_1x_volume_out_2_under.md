# 39. SOXL / TQQQ / TECL Volume Momentum: 1% over the 20-day on 1x volume, out 2% under

Funds: SOXL, TQQQ, TECL. $25,000 cash account, the whole account in one position, fills at the next open, 8 bp slippage a side. Backtests, not advice.

## Rules

- **Buy** when `mkt_above_sma200 == 1 and dist_sma20 > 0.01 and volume_ratio > 1.0`
- **Sell** when `dist_sma20 < -0.02`
- **Sell** when `mkt_above_sma200 == 0`
- **Risk:** stop 12.0% under entry (on a close), waits 5 sessions after an exit

Terms: `dist_sma20` distance above the 20-day average (0.05 = 5%); `mkt_above_sma200` 1 when the first fund is above its 200-day average; `volume_ratio` volume / 20-day average volume.

## Results

| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | Profit factor | Max drawdown | Worst day |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Last 6 months (never bred on) | $237 | +165% | 3 | 33% | +208.7% | -7.3% | 4.77 | -36% | $-7,628 |
| Last 12 months | $116 | +127% | 9 | 44% | +61.4% | -9.7% | 2.88 | -43% | $-7,628 |
| 2019 to Mar 2026 (bred on) | $25 | +171% | 56 | 45% | +15.8% | -7.5% | 1.18 | -63% | $-5,812 |
| 2012 to 2018 | $13 | +65% | 64 | 42% | +11.3% | -5.9% | 1.21 | -68% | $-3,425 |

Every rolling three-month stretch since 2019 (1878): 60% made money; the typical one made $30 a session and the worst $-230.

At 3x slippage: $235 a session over the last six months, $23 over 2019 to March 2026.

Buying and holding over the last six months: SOXL $335 a session, TQQQ $143 a session, TECL $223 a session.

## By year

| Year | Return | $ a session | Trades | Win rate |
| --- | --- | --- | --- | --- |
| 2012 | +8% | $13 | 7 | 71% |
| 2013 | +43% | $41 | 10 | 40% |
| 2014 | +38% | $39 | 9 | 56% |
| 2015 | -48% | $-58 | 12 | 17% |
| 2016 | -19% | $-16 | 11 | 18% |
| 2017 | +69% | $58 | 8 | 62% |
| 2018 | +9% | $13 | 7 | 57% |
| 2019 | +99% | $77 | 4 | 100% |
| 2020 | +101% | $87 | 5 | 80% |
| 2021 | -13% | $1 | 13 | 46% |
| 2022 | -12% | $-12 | 1 | 0% |
| 2023 | +41% | $43 | 7 | 14% |
| 2024 | +11% | $24 | 11 | 55% |
| 2025 | -37% | $-32 | 13 | 23% |
| 2026 | +136% | $159 | 5 | 40% |
