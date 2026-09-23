# Profitable strategies on the long Nasdaq funds (TQQQ, SOXL, QLD), 2010-03-11 to 2026-09-22

Universe: TQQQ, SOXL, QLD; 2010-03-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 5 bp per side; fills at the next open.

## Capitulation Close

*A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.*

```
Capitulation Close (id=b1f8b938545f, gen=0, origin=seed)
  thesis: A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.
  BUY  25% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +111.4% | +22228.0% | 0.39 | -28.8% | -20.5% | 375 | 62% | 1.36 | +0.95% | 2.2 bars | -2.03 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | -2.2% | 10 | 40% |
| 2011 | -11.7% | 29 | 52% |
| 2012 | +2.7% | 18 | 44% |
| 2013 | +11.3% | 18 | 83% |
| 2014 | +6.7% | 23 | 65% |
| 2015 | +13.7% | 27 | 70% |
| 2016 | +2.4% | 16 | 62% |
| 2017 | +7.7% | 18 | 67% |
| 2018 | -19.2% | 28 | 39% |
| 2019 | +20.5% | 21 | 81% |
| 2020 | +16.0% | 39 | 62% |
| 2021 | +13.6% | 21 | 67% |
| 2022 | -24.6% | 31 | 39% |
| 2023 | +9.4% | 13 | 92% |
| 2024 | +10.8% | 31 | 68% |
| 2025 | +19.8% | 18 | 78% |
| 2026 | +13.9% | 14 | 71% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 165 | 60% | +1.19% | +65,655 |
| TQQQ | 127 | 66% | +0.85% | +29,050 |
| QLD | 83 | 60% | +0.63% | +17,868 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-02-26 to 2020-02-28, 2 bars, -23.5%: stop loss hit (-15.1% <= -8.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Red Day Above the 50

*A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.*

```
Red Day Above the 50 (id=d4542f7e14e9, gen=0, origin=seed)
  thesis: A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.
  BUY  25% when: ret1 < -0.045 and close > sma50 and volume_ratio > 1.0
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +92.7% | +26870.9% | 0.54 | -18.1% | -9.4% | 228 | 63% | 1.56 | +1.23% | 2.3 bars | -3.20 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | -2.9% | 3 | 0% |
| 2011 | +8.1% | 19 | 68% |
| 2012 | +5.6% | 6 | 67% |
| 2013 | +13.2% | 15 | 93% |
| 2014 | -3.6% | 10 | 30% |
| 2015 | +5.7% | 12 | 67% |
| 2016 | +1.9% | 7 | 57% |
| 2017 | +5.4% | 15 | 60% |
| 2018 | -8.1% | 10 | 30% |
| 2019 | +0.3% | 13 | 62% |
| 2020 | +7.8% | 29 | 69% |
| 2021 | +3.7% | 19 | 68% |
| 2022 | -6.2% | 6 | 33% |
| 2023 | +11.6% | 14 | 79% |
| 2024 | +1.1% | 19 | 53% |
| 2025 | +20.4% | 14 | 93% |
| 2026 | +6.9% | 17 | 47% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 132 | 67% | +1.86% | +84,652 |
| TQQQ | 72 | 56% | +0.31% | +5,926 |
| QLD | 24 | 62% | +0.54% | +2,856 |

Worst trades over the full window, then best:

- QLD 2020-02-25 to 2020-02-28, 3 bars, -21.1%: stop loss hit (-15.6% <= -8.0%)
- SOXL 2021-01-25 to 2021-01-28, 3 bars, -16.8%: stop loss hit (-21.2% <= -8.0%)
- SOXL 2011-03-08 to 2011-03-10, 2 bars, -13.8%: stop loss hit (-9.2% <= -8.0%)
- SOXL 2026-06-10 to 2026-06-12, 2 bars, +15.9%: take profit hit (16.9% >= 4.0%)
- SOXL 2025-10-23 to 2025-10-24, 1 bars, +15.0%: take profit hit (9.1% >= 4.0%)
- SOXL 2012-01-17 to 2012-01-19, 2 bars, +14.9%: take profit hit (11.7% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Oversold Dip Above the 50

*A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.*

```
Oversold Dip Above the 50 (id=f2c88bd40f38, gen=0, origin=seed)
  thesis: A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.
  BUY  25% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +158.3% | +26870.9% | 0.79 | -18.3% | -7.6% | 252 | 72% | 2.09 | +1.59% | 2.5 bars | -4.42 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +2.1% | 3 | 100% |
| 2011 | +2.6% | 14 | 79% |
| 2012 | -4.7% | 11 | 27% |
| 2013 | +20.5% | 22 | 86% |
| 2014 | +3.4% | 22 | 55% |
| 2015 | +7.9% | 17 | 65% |
| 2016 | +10.4% | 13 | 85% |
| 2017 | +10.5% | 23 | 78% |
| 2018 | -5.0% | 19 | 53% |
| 2019 | -3.2% | 15 | 60% |
| 2020 | -3.2% | 9 | 67% |
| 2021 | +11.9% | 21 | 71% |
| 2022 | +9.5% | 7 | 86% |
| 2023 | +7.2% | 14 | 93% |
| 2024 | +14.2% | 18 | 83% |
| 2025 | +22.3% | 19 | 95% |
| 2026 | -3.4% | 5 | 20% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TQQQ | 86 | 72% | +1.68% | +59,357 |
| SOXL | 75 | 72% | +1.86% | +54,338 |
| QLD | 91 | 71% | +1.29% | +45,531 |

Worst trades over the full window, then best:

- QLD 2020-02-25 to 2020-02-28, 3 bars, -21.1%: stop loss hit (-15.6% <= -10.0%)
- SOXL 2011-03-08 to 2011-03-11, 3 bars, -17.8%: stop loss hit (-16.1% <= -10.0%)
- SOXL 2018-02-05 to 2018-02-06, 1 bars, -16.5%: stop loss hit (-11.1% <= -10.0%)
- SOXL 2024-03-20 to 2024-03-21, 1 bars, +14.4%: take profit hit (4.3% >= 4.0%)
- TQQQ 2024-11-05 to 2024-11-07, 2 bars, +12.9%: take profit hit (11.1% >= 4.0%)
- SOXL 2022-08-23 to 2022-08-26, 3 bars, +12.6%: take profit hit (13.1% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Pullback Cluster (volume-gated)

*Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.*

```
Pullback Cluster (volume-gated) (id=255612d6d3fc, gen=0, origin=seed)
  thesis: Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +62.1% | +26870.9% | 0.45 | -27.9% | -6.5% | 197 | 63% | 1.53 | +1.08% | 2.5 bars | -3.31 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +4.0% | 6 | 83% |
| 2011 | -0.2% | 14 | 71% |
| 2012 | +4.1% | 10 | 50% |
| 2013 | +13.2% | 16 | 81% |
| 2014 | +4.1% | 15 | 53% |
| 2015 | +3.9% | 10 | 70% |
| 2016 | -0.4% | 6 | 33% |
| 2017 | -1.8% | 10 | 50% |
| 2018 | -12.0% | 13 | 31% |
| 2019 | -10.8% | 13 | 46% |
| 2020 | +5.8% | 17 | 71% |
| 2021 | +14.7% | 16 | 88% |
| 2022 | -1.0% | 5 | 40% |
| 2023 | +1.5% | 8 | 62% |
| 2024 | +14.9% | 16 | 69% |
| 2025 | +12.6% | 16 | 75% |
| 2026 | +1.1% | 6 | 50% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 68 | 62% | +1.18% | +24,534 |
| TQQQ | 68 | 62% | +1.00% | +19,899 |
| QLD | 61 | 66% | +1.04% | +18,253 |

Worst trades over the full window, then best:

- SOXL 2019-08-01 to 2019-08-05, 2 bars, -17.5%: stop loss hit (-9.5% <= -8.0%)
- TQQQ 2011-08-02 to 2011-08-05, 3 bars, -14.2%: stop loss hit (-16.9% <= -8.0%)
- TQQQ 2019-08-01 to 2019-08-06, 3 bars, -14.1%: stop loss hit (-16.3% <= -8.0%)
- SOXL 2024-02-21 to 2024-02-23, 2 bars, +19.9%: take profit hit (17.9% >= 4.0%)
- SOXL 2025-10-23 to 2025-10-24, 1 bars, +15.0%: take profit hit (9.1% >= 4.0%)
- SOXL 2026-05-19 to 2026-05-20, 1 bars, +13.9%: take profit hit (7.5% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Prior-Low Break on Volume

*A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.*

```
Prior-Low Break on Volume (id=e2914de0ae2f, gen=0, origin=seed)
  thesis: A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.
  BUY  25% when: close < prev(low) and close > sma50 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +74.8% | +26870.9% | 0.41 | -33.9% | -9.4% | 391 | 60% | 1.33 | +0.65% | 2.5 bars | -4.86 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +1.2% | 12 | 67% |
| 2011 | +4.8% | 21 | 67% |
| 2012 | +3.2% | 13 | 54% |
| 2013 | +14.0% | 31 | 71% |
| 2014 | +17.0% | 43 | 70% |
| 2015 | +0.3% | 17 | 47% |
| 2016 | -1.8% | 15 | 40% |
| 2017 | +4.0% | 34 | 50% |
| 2018 | -19.5% | 25 | 20% |
| 2019 | -1.8% | 25 | 64% |
| 2020 | +8.3% | 34 | 71% |
| 2021 | +17.2% | 37 | 70% |
| 2022 | -9.9% | 7 | 14% |
| 2023 | +5.6% | 14 | 64% |
| 2024 | +4.7% | 25 | 56% |
| 2025 | +28.5% | 29 | 86% |
| 2026 | -8.9% | 9 | 11% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 119 | 66% | +1.54% | +60,948 |
| QLD | 138 | 56% | +0.31% | +9,773 |
| TQQQ | 134 | 58% | +0.20% | +5,422 |

Worst trades over the full window, then best:

- SOXL 2011-09-20 to 2011-09-22, 2 bars, -17.6%: stop loss hit (-10.8% <= -8.0%)
- SOXL 2019-08-01 to 2019-08-05, 2 bars, -17.5%: stop loss hit (-9.5% <= -8.0%)
- SOXL 2020-02-21 to 2020-02-25, 2 bars, -17.1%: stop loss hit (-20.4% <= -8.0%)
- SOXL 2025-10-23 to 2025-10-24, 1 bars, +15.0%: take profit hit (9.1% >= 4.0%)
- TQQQ 2020-02-03 to 2020-02-05, 2 bars, +14.0%: take profit hit (10.0% >= 4.0%)
- SOXL 2021-02-01 to 2021-02-02, 1 bars, +11.4%: take profit hit (6.4% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Combo: Capitulation or Oversold

*Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.*

```
Combo: Capitulation or Oversold (id=b9f249e7b0c6, gen=0, origin=seed)
  thesis: Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.
  BUY  20% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  BUY  20% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +223.8% | +26870.9% | 0.64 | -20.1% | -16.6% | 529 | 65% | 1.65 | +1.22% | 2.3 bars | -2.46 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +0.0% | 8 | 50% |
| 2011 | -3.9% | 35 | 60% |
| 2012 | -4.4% | 26 | 35% |
| 2013 | +18.4% | 32 | 81% |
| 2014 | +4.9% | 35 | 63% |
| 2015 | +12.7% | 37 | 65% |
| 2016 | +7.1% | 23 | 70% |
| 2017 | +14.6% | 34 | 74% |
| 2018 | -11.4% | 40 | 48% |
| 2019 | +12.0% | 31 | 74% |
| 2020 | +3.5% | 42 | 60% |
| 2021 | +16.8% | 38 | 68% |
| 2022 | -10.5% | 35 | 49% |
| 2023 | +13.3% | 23 | 96% |
| 2024 | +13.6% | 41 | 68% |
| 2025 | +31.0% | 33 | 82% |
| 2026 | +13.1% | 16 | 69% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 205 | 63% | +1.46% | +110,431 |
| TQQQ | 174 | 68% | +1.06% | +62,891 |
| QLD | 150 | 65% | +1.07% | +52,124 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-02-26 to 2020-02-28, 2 bars, -23.5%: stop loss hit (-15.1% <= -8.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=847437fd39b9, gen=0, origin=seed)
  thesis: Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.
  BUY  20% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  BUY  20% when: rsi7 < 40 and close > sma50
  BUY  20% when: ret1 < -0.045 and close > sma50 and volume_ratio > 1.0
  BUY  20% when: close < prev(low) and close > sma50 and volume_ratio > 1.2
  BUY  20% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +294.1% | +26870.9% | 0.68 | -23.7% | -16.6% | 746 | 62% | 1.58 | +1.01% | 2.4 bars | -2.21 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +1.1% | 17 | 59% |
| 2011 | -9.3% | 45 | 53% |
| 2012 | +1.5% | 37 | 46% |
| 2013 | +17.3% | 44 | 70% |
| 2014 | +11.7% | 59 | 71% |
| 2015 | +1.3% | 42 | 52% |
| 2016 | +7.5% | 31 | 61% |
| 2017 | +14.2% | 50 | 64% |
| 2018 | -16.3% | 50 | 38% |
| 2019 | +19.5% | 44 | 73% |
| 2020 | +30.3% | 60 | 68% |
| 2021 | +11.9% | 57 | 63% |
| 2022 | -14.3% | 38 | 47% |
| 2023 | +19.5% | 36 | 81% |
| 2024 | +11.0% | 53 | 58% |
| 2025 | +34.3% | 52 | 77% |
| 2026 | +16.9% | 31 | 55% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 284 | 63% | +1.57% | +187,220 |
| TQQQ | 241 | 63% | +0.74% | +62,628 |
| QLD | 221 | 57% | +0.58% | +46,793 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-03-13 to 2020-03-16, 1 bars, -22.6%: take profit hit (8.8% >= 4.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Two Red Days (evolved)

*Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Two Red Days (evolved) (id=75c7bbadce12, gen=0, origin=llm)
  thesis: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +60.0% | +26870.9% | 0.81 | -8.0% | -3.2% | 69 | 81% | 3.74 | +3.49% | 1.7 bars | -0.84 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +0.3% | 1 | 100% |
| 2011 | +0.6% | 4 | 75% |
| 2012 | +2.4% | 2 | 100% |
| 2013 | +1.1% | 1 | 100% |
| 2014 | +3.5% | 2 | 100% |
| 2015 | +3.5% | 5 | 100% |
| 2016 | +0.0% | 0 | 0% |
| 2017 | +2.1% | 3 | 100% |
| 2018 | -1.7% | 2 | 50% |
| 2019 | -1.6% | 6 | 67% |
| 2020 | -2.2% | 6 | 33% |
| 2021 | +10.8% | 9 | 100% |
| 2022 | +4.8% | 8 | 75% |
| 2023 | +1.2% | 4 | 75% |
| 2024 | +7.7% | 6 | 100% |
| 2025 | +3.9% | 4 | 75% |
| 2026 | +12.7% | 6 | 83% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 44 | 77% | +3.99% | +45,741 |
| TQQQ | 21 | 90% | +3.03% | +14,010 |
| QLD | 4 | 75% | +0.36% | +409 |

Worst trades over the full window, then best:

- SOXL 2019-05-08 to 2019-05-14, 4 bars, -14.2%: stop loss hit (-17.2% <= -6.0%)
- SOXL 2011-03-08 to 2011-03-10, 2 bars, -13.8%: stop loss hit (-9.2% <= -6.0%)
- SOXL 2018-06-25 to 2018-06-28, 3 bars, -11.9%: stop loss hit (-11.4% <= -6.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: exit rule: ret1 > 0.02
- SOXL 2026-02-05 to 2026-02-09, 2 bars, +16.8%: exit rule: ret1 > 0.02
- SOXL 2026-06-11 to 2026-06-12, 1 bars, +15.4%: exit rule: ret1 > 0.02

Verdict: **PROFITABLE on every window**

## Combo: Recent Winners

*The five setups that have worked over the last six months, in one book; first match wins, five 20% slots.*

```
Combo: Recent Winners (id=a08083b76fd8, gen=0, origin=seed)
  thesis: The five setups that have worked over the last six months, in one book; first match wins, five 20% slots.
  BUY  20% when: volume_ratio > 2.0 and ret1 < -0.03
  BUY  20% when: bb_pct < 0.0 and volume_ratio > 1.2
  BUY  20% when: ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2
  BUY  20% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  BUY  20% when: ret1 < 0 and prev(ret1) < -0.028 and close > sma50 and ret5 < -0.078
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +160.9% | +26870.9% | 0.56 | -27.5% | -16.6% | 529 | 62% | 1.45 | +1.00% | 2.3 bars | -2.57 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +6.6% | 15 | 67% |
| 2011 | +7.1% | 36 | 75% |
| 2012 | +1.6% | 23 | 39% |
| 2013 | +18.7% | 30 | 80% |
| 2014 | +7.2% | 37 | 62% |
| 2015 | +7.6% | 31 | 65% |
| 2016 | +2.9% | 27 | 52% |
| 2017 | +10.1% | 30 | 60% |
| 2018 | -16.0% | 34 | 44% |
| 2019 | +0.8% | 28 | 61% |
| 2020 | +2.0% | 41 | 63% |
| 2021 | +16.7% | 42 | 71% |
| 2022 | -17.6% | 31 | 35% |
| 2023 | +8.1% | 22 | 68% |
| 2024 | +11.7% | 41 | 63% |
| 2025 | +37.6% | 39 | 79% |
| 2026 | +5.2% | 22 | 50% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 197 | 60% | +1.29% | +84,272 |
| TQQQ | 184 | 63% | +0.83% | +44,468 |
| QLD | 148 | 63% | +0.82% | +33,807 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-03-13 to 2020-03-16, 1 bars, -22.6%: take profit hit (8.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)
- TQQQ 2025-04-09 to 2025-04-10, 1 bars, +25.5%: take profit hit (35.7% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Band Break on Volume

*A close under the lower Bollinger band on 1.2x volume, any regime.*

```
Band Break on Volume (id=2c8e3d0b1256, gen=0, origin=seed)
  thesis: A close under the lower Bollinger band on 1.2x volume, any regime.
  BUY  25% when: bb_pct < 0.0 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | -5.9% | +22228.0% | 0.03 | -49.2% | -20.5% | 232 | 58% | 0.97 | +0.08% | 2.2 bars | -1.20 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | -0.1% | 7 | 57% |
| 2011 | -9.2% | 14 | 57% |
| 2012 | +5.2% | 10 | 60% |
| 2013 | +15.0% | 16 | 81% |
| 2014 | -6.9% | 19 | 42% |
| 2015 | +3.0% | 14 | 57% |
| 2016 | -0.2% | 16 | 44% |
| 2017 | +1.8% | 7 | 71% |
| 2018 | -6.1% | 21 | 57% |
| 2019 | +9.8% | 12 | 83% |
| 2020 | -25.8% | 10 | 30% |
| 2021 | +5.7% | 19 | 68% |
| 2022 | -24.4% | 17 | 24% |
| 2023 | +3.3% | 7 | 57% |
| 2024 | +4.0% | 12 | 75% |
| 2025 | +13.9% | 16 | 69% |
| 2026 | +17.5% | 15 | 67% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| QLD | 80 | 61% | +0.21% | +853 |
| SOXL | 71 | 52% | +0.19% | -598 |
| TQQQ | 81 | 60% | -0.14% | -5,634 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- SOXL 2020-02-26 to 2020-02-28, 2 bars, -24.0%: stop loss hit (-15.5% <= -8.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- TQQQ 2025-04-09 to 2025-04-10, 1 bars, +25.5%: take profit hit (35.7% >= 4.0%)
- SOXL 2026-07-30 to 2026-07-31, 1 bars, +20.8%: take profit hit (6.8% >= 4.0%)

Verdict: **not profitable**

## Volume Climax

*Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.*

```
Volume Climax (id=7abd7a7ce26f, gen=0, origin=seed)
  thesis: Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.
  BUY  25% when: volume_ratio > 2.0 and ret1 < -0.03
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +65.6% | +22228.0% | 0.42 | -26.5% | -9.9% | 139 | 60% | 1.69 | +1.59% | 2.3 bars | -1.21 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +4.0% | 12 | 58% |
| 2011 | -8.2% | 12 | 58% |
| 2012 | -3.0% | 3 | 0% |
| 2013 | +6.5% | 5 | 100% |
| 2014 | +2.1% | 5 | 60% |
| 2015 | +13.9% | 9 | 56% |
| 2016 | +7.6% | 11 | 82% |
| 2017 | +2.7% | 16 | 56% |
| 2018 | -7.6% | 12 | 25% |
| 2019 | -0.7% | 7 | 57% |
| 2020 | -9.8% | 8 | 25% |
| 2021 | +14.4% | 12 | 75% |
| 2022 | +1.2% | 4 | 50% |
| 2023 | +0.0% | 0 | 0% |
| 2024 | +0.2% | 7 | 57% |
| 2025 | +28.8% | 14 | 93% |
| 2026 | +5.8% | 2 | 100% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TQQQ | 39 | 67% | +2.94% | +32,597 |
| SOXL | 57 | 56% | +0.90% | +17,158 |
| QLD | 43 | 60% | +1.29% | +16,251 |

Worst trades over the full window, then best:

- SOXL 2020-02-26 to 2020-02-28, 2 bars, -24.0%: stop loss hit (-15.5% <= -8.0%)
- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.7%: stop loss hit (-13.2% <= -8.0%)
- QLD 2020-02-25 to 2020-02-28, 3 bars, -21.1%: stop loss hit (-15.6% <= -8.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- TQQQ 2025-04-07 to 2025-04-08, 1 bars, +23.4%: take profit hit (12.2% >= 4.0%)
- SOXL 2026-07-30 to 2026-07-31, 1 bars, +20.8%: take profit hit (6.8% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Red Day Near the Mean

*A 4% down day within 3% of the 20-day mean on 1.2x volume.*

```
Red Day Near the Mean (id=c9b2b5bf438f, gen=0, origin=seed)
  thesis: A 4% down day within 3% of the 20-day mean on 1.2x volume.
  BUY  25% when: ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +27.4% | +20084.9% | 0.26 | -17.3% | -9.4% | 176 | 59% | 1.26 | +0.62% | 2.4 bars | -2.38 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | -0.4% | 7 | 43% |
| 2011 | +8.6% | 11 | 82% |
| 2012 | -4.6% | 4 | 0% |
| 2013 | +5.8% | 8 | 88% |
| 2014 | +7.6% | 10 | 70% |
| 2015 | +2.3% | 8 | 62% |
| 2016 | -0.6% | 5 | 40% |
| 2017 | +6.8% | 16 | 50% |
| 2018 | -9.3% | 12 | 33% |
| 2019 | -3.7% | 11 | 55% |
| 2020 | +10.9% | 25 | 72% |
| 2021 | +0.9% | 12 | 67% |
| 2022 | -7.9% | 5 | 20% |
| 2023 | +2.8% | 10 | 60% |
| 2024 | -0.8% | 17 | 59% |
| 2025 | +10.1% | 12 | 67% |
| 2026 | -1.1% | 3 | 33% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 83 | 63% | +1.07% | +23,586 |
| QLD | 33 | 55% | +0.70% | +6,183 |
| TQQQ | 60 | 55% | -0.05% | -1,837 |

Worst trades over the full window, then best:

- SOXL 2020-02-21 to 2020-02-25, 2 bars, -17.1%: stop loss hit (-20.4% <= -8.0%)
- SOXL 2021-01-25 to 2021-01-28, 3 bars, -16.8%: stop loss hit (-21.2% <= -8.0%)
- SOXL 2022-02-11 to 2022-02-14, 1 bars, -14.7%: stop loss hit (-15.1% <= -8.0%)
- SOXL 2026-06-10 to 2026-06-12, 2 bars, +15.9%: take profit hit (16.9% >= 4.0%)
- SOXL 2025-10-23 to 2025-10-24, 1 bars, +15.0%: take profit hit (9.1% >= 4.0%)
- SOXL 2020-04-13 to 2020-04-14, 1 bars, +11.5%: take profit hit (4.3% >= 4.0%)

Verdict: **PROFITABLE on every window**

## Pullback Cluster (ungated)

*Two red closes and a 3% loss over five sessions, above the 50-day mean; out at the first close up 1% or after three bars, 10% stop. No volume gate: this is the original version, not the volume-gated one in the durable set.*

```
Pullback Cluster (ungated) (id=097b9f0c78bd, gen=0, origin=seed)
  thesis: Two red closes and a 3% loss over five sessions, above the 50-day mean; out at the first close up 1% or after three bars, 10% stop. No volume gate: this is the original version, not the volume-gated one in the durable set.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50
  SELL when: ret1 > 0.01
  SELL when: bars_held >= 3
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=0% trail=0% hold<=3 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +125.0% | +26870.9% | 0.61 | -28.6% | -7.8% | 319 | 70% | 1.87 | +1.11% | 1.9 bars | -0.91 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +1.8% | 9 | 78% |
| 2011 | +0.4% | 20 | 80% |
| 2012 | +2.6% | 19 | 68% |
| 2013 | +11.5% | 20 | 85% |
| 2014 | +7.1% | 23 | 74% |
| 2015 | -6.7% | 16 | 44% |
| 2016 | +2.4% | 11 | 64% |
| 2017 | +5.8% | 18 | 83% |
| 2018 | -6.6% | 17 | 53% |
| 2019 | -9.4% | 16 | 56% |
| 2020 | -4.4% | 25 | 68% |
| 2021 | +21.1% | 28 | 82% |
| 2022 | +5.1% | 12 | 75% |
| 2023 | +19.8% | 28 | 68% |
| 2024 | +15.0% | 25 | 64% |
| 2025 | +6.0% | 20 | 65% |
| 2026 | +18.3% | 12 | 75% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 132 | 67% | +1.74% | +86,396 |
| TQQQ | 106 | 72% | +0.88% | +31,217 |
| QLD | 81 | 72% | +0.38% | +8,385 |

Worst trades over the full window, then best:

- SOXL 2020-02-24 to 2020-02-28, 4 bars, -29.4%: stop loss hit (-21.5% <= -10.0%)
- QLD 2020-02-24 to 2020-02-28, 4 bars, -19.9%: stop loss hit (-14.2% <= -10.0%)
- SOXL 2011-03-08 to 2011-03-11, 3 bars, -17.8%: stop loss hit (-16.1% <= -10.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: exit rule: ret1 > 0.01
- SOXL 2024-02-21 to 2024-02-23, 2 bars, +19.9%: exit rule: ret1 > 0.01
- SOXL 2022-11-29 to 2022-12-01, 2 bars, +17.8%: exit rule: ret1 > 0.01

Verdict: **PROFITABLE on every window**

## Squeeze Days (evolved)

*Volatility contraction followed by a close above the upper band; ride the release for two sessions. Combined with: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Squeeze Days (evolved) (id=a8c2d33e531d, gen=0, origin=seed)
  thesis: Volatility contraction followed by a close above the upper band; ride the release for two sessions. Combined with: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.
  BUY  50% when: vol_ratio_20_60 < 0.8 and cross_above(close, bb_upper)   # archetype
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  SELL when: bars_held >= 2   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=8% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +95.4% | +26870.9% | 0.88 | -13.5% | -3.6% | 183 | 70% | 2.58 | +1.89% | 2.0 bars | -0.27 |

| period | return | trades | win |
|---|---|---|---|
| 2010 | +1.9% | 5 | 60% |
| 2011 | +2.7% | 11 | 73% |
| 2012 | +2.1% | 10 | 60% |
| 2013 | +1.0% | 6 | 33% |
| 2014 | +8.0% | 13 | 85% |
| 2015 | +3.6% | 6 | 100% |
| 2016 | -2.3% | 1 | 0% |
| 2017 | +4.8% | 11 | 91% |
| 2018 | -2.5% | 10 | 50% |
| 2019 | -4.0% | 19 | 58% |
| 2020 | -3.3% | 20 | 40% |
| 2021 | +15.7% | 17 | 82% |
| 2022 | +8.8% | 12 | 83% |
| 2023 | +2.5% | 6 | 83% |
| 2024 | +4.0% | 12 | 75% |
| 2025 | +10.7% | 13 | 77% |
| 2026 | +17.3% | 11 | 91% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 78 | 76% | +3.32% | +73,041 |
| TQQQ | 62 | 69% | +1.42% | +22,361 |
| QLD | 43 | 60% | -0.05% | +425 |

Worst trades over the full window, then best:

- SOXL 2011-03-08 to 2011-03-10, 2 bars, -13.8%: stop loss hit (-9.2% <= -6.0%)
- SOXL 2019-05-08 to 2019-05-13, 3 bars, -13.2%: exit rule: bars_held >= 2
- SOXL 2018-06-25 to 2018-06-28, 3 bars, -11.9%: stop loss hit (-11.4% <= -6.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: take profit hit (22.6% >= 8.0%)
- SOXL 2021-01-06 to 2021-01-08, 2 bars, +18.8%: take profit hit (13.4% >= 8.0%)
- SOXL 2026-02-05 to 2026-02-09, 2 bars, +16.8%: take profit hit (20.3% >= 8.0%)

Verdict: **PROFITABLE on every window**
