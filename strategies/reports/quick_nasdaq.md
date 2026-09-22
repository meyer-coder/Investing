# Quick leveraged strategies on TQQQ/SQQQ, SOXL/SOXS, QLD/QID (2010-2026)

Universe: TQQQ, SQQQ, SOXL, SOXS, QLD, QID; 2010-03-01 to 2026-09-22; held-out tail 25%; commission 1 bp, slippage 5 bp per side; fills at the next open.

## Capitulation Close

*A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.*

```
Capitulation Close (id=31a0a07fada0, gen=0, origin=seed)
  thesis: A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.
  BUY  25% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +56.9% | +1907.2% | 0.32 | -25.2% | 423 | 57% | 1.18 | +0.55% | 2.3 bars | -0.30 |
| held-out | 2022-08-01 to 2026-09-22 | +60.1% | +179.7% | 0.70 | -16.8% | 164 | 60% | 1.45 | +1.29% | 2.1 bars | +0.77 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -3.6% | 17 | 35% |
| 2011 | -18.8% | 40 | 45% |
| 2012 | +5.4% | 26 | 54% |
| 2013 | +10.6% | 24 | 79% |
| 2014 | +4.9% | 30 | 57% |
| 2015 | +22.4% | 36 | 72% |
| 2016 | -0.1% | 22 | 55% |
| 2017 | +6.3% | 20 | 60% |
| 2018 | -15.6% | 35 | 43% |
| 2019 | +18.9% | 37 | 65% |
| 2020 | +25.3% | 63 | 60% |
| 2021 | +12.6% | 37 | 62% |
| 2022 | -10.9% | 55 | 49% |
| 2023 | -1.7% | 30 | 63% |
| 2024 | +16.1% | 52 | 60% |
| 2025 | +29.4% | 30 | 67% |
| 2026 | +14.7% | 34 | 59% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 165 | 60% | +1.19% | +75,186 |
| TQQQ | 127 | 66% | +0.85% | +33,313 |
| QLD | 83 | 60% | +0.63% | +20,720 |
| SQQQ | 84 | 49% | +0.65% | +15,347 |
| QID | 43 | 49% | +0.88% | +13,119 |
| SOXS | 86 | 53% | +0.19% | +10,527 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-02-26 to 2020-02-28, 2 bars, -23.5%: stop loss hit (-15.1% <= -8.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **profitable on every window**

## Red Day Above the 50

*A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.*

```
Red Day Above the 50 (id=891a9af9df99, gen=0, origin=seed)
  thesis: A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.
  BUY  25% when: ret1 < -0.045 and close > sma50 and volume_ratio > 1.0
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +41.2% | +2321.9% | 0.32 | -23.3% | 233 | 58% | 1.24 | +0.69% | 2.3 bars | -0.45 |
| held-out | 2022-08-01 to 2026-09-22 | +30.1% | +447.9% | 0.58 | -15.5% | 98 | 56% | 1.47 | +1.17% | 2.3 bars | +0.17 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -6.9% | 5 | 0% |
| 2011 | +4.6% | 24 | 67% |
| 2012 | +6.5% | 10 | 70% |
| 2013 | +13.2% | 15 | 93% |
| 2014 | -5.2% | 12 | 25% |
| 2015 | +6.6% | 17 | 65% |
| 2016 | +1.3% | 12 | 58% |
| 2017 | +5.4% | 15 | 60% |
| 2018 | -11.8% | 20 | 40% |
| 2019 | -3.6% | 19 | 42% |
| 2020 | +16.8% | 38 | 66% |
| 2021 | +3.7% | 23 | 65% |
| 2022 | +0.6% | 35 | 49% |
| 2023 | +2.5% | 20 | 60% |
| 2024 | -4.2% | 28 | 50% |
| 2025 | +37.9% | 22 | 86% |
| 2026 | +1.3% | 21 | 38% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 132 | 67% | +1.86% | +81,710 |
| SOXS | 25 | 60% | +2.20% | +17,658 |
| TQQQ | 72 | 56% | +0.31% | +5,294 |
| QID | 31 | 42% | +0.54% | +3,837 |
| QLD | 24 | 62% | +0.54% | +3,114 |
| SQQQ | 52 | 42% | -1.63% | -30,313 |

Worst trades over the full window, then best:

- QLD 2020-02-25 to 2020-02-28, 3 bars, -21.1%: stop loss hit (-15.6% <= -8.0%)
- SOXL 2021-01-25 to 2021-01-28, 3 bars, -16.8%: stop loss hit (-21.2% <= -8.0%)
- SOXS 2024-08-09 to 2024-08-14, 3 bars, -16.3%: stop loss hit (-14.4% <= -8.0%)
- SQQQ 2020-03-11 to 2020-03-12, 1 bars, +25.8%: take profit hit (5.1% >= 4.0%)
- SOXS 2025-04-08 to 2025-04-09, 1 bars, +22.8%: take profit hit (25.7% >= 4.0%)
- SOXS 2022-01-27 to 2022-01-28, 1 bars, +18.6%: take profit hit (17.6% >= 4.0%)

Verdict: **profitable on every window**

## Oversold Dip Above the 50

*A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.*

```
Oversold Dip Above the 50 (id=9a548365bcca, gen=0, origin=seed)
  thesis: A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.
  BUY  25% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +72.0% | +2321.9% | 0.55 | -18.8% | 254 | 64% | 1.43 | +0.94% | 2.5 bars | -0.10 |
| held-out | 2022-08-01 to 2026-09-22 | +31.2% | +447.9% | 0.80 | -8.8% | 79 | 68% | 2.02 | +1.45% | 2.6 bars | +0.64 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +0.9% | 9 | 67% |
| 2011 | -1.3% | 19 | 63% |
| 2012 | -4.0% | 22 | 41% |
| 2013 | +20.5% | 22 | 86% |
| 2014 | +3.8% | 28 | 57% |
| 2015 | +8.0% | 18 | 67% |
| 2016 | +11.5% | 19 | 79% |
| 2017 | +10.5% | 23 | 78% |
| 2018 | -2.5% | 26 | 54% |
| 2019 | -6.2% | 21 | 43% |
| 2020 | -2.9% | 10 | 70% |
| 2021 | +8.8% | 23 | 65% |
| 2022 | +25.0% | 25 | 72% |
| 2023 | -2.3% | 21 | 62% |
| 2024 | +8.9% | 24 | 67% |
| 2025 | +26.3% | 23 | 91% |
| 2026 | -3.4% | 5 | 20% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TQQQ | 86 | 72% | +1.68% | +58,219 |
| SOXL | 75 | 72% | +1.86% | +52,778 |
| QLD | 91 | 71% | +1.29% | +45,094 |
| SQQQ | 29 | 45% | +0.09% | +2,444 |
| QID | 34 | 44% | -0.15% | -2,602 |
| SOXS | 23 | 52% | -0.16% | -4,829 |

Worst trades over the full window, then best:

- QLD 2020-02-25 to 2020-02-28, 3 bars, -21.1%: stop loss hit (-15.6% <= -10.0%)
- SOXL 2011-03-08 to 2011-03-11, 3 bars, -17.8%: stop loss hit (-16.1% <= -10.0%)
- SOXL 2018-02-05 to 2018-02-06, 1 bars, -16.5%: stop loss hit (-11.1% <= -10.0%)
- SQQQ 2022-06-08 to 2022-06-10, 2 bars, +15.7%: take profit hit (9.4% >= 4.0%)
- SOXL 2024-03-20 to 2024-03-21, 1 bars, +14.4%: take profit hit (4.3% >= 4.0%)
- TQQQ 2024-11-05 to 2024-11-07, 2 bars, +12.9%: take profit hit (11.1% >= 4.0%)

Verdict: **profitable on every window**

## Pullback Cluster

*Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.*

```
Pullback Cluster (id=ac4017a9f342, gen=0, origin=seed)
  thesis: Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +17.1% | +2321.9% | 0.21 | -27.2% | 166 | 60% | 1.16 | +0.47% | 2.4 bars | -0.60 |
| held-out | 2022-08-01 to 2026-09-22 | +27.1% | +447.9% | 0.81 | -8.4% | 54 | 63% | 1.96 | +1.88% | 2.6 bars | +0.39 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +4.3% | 7 | 86% |
| 2011 | -1.7% | 15 | 67% |
| 2012 | +4.4% | 11 | 55% |
| 2013 | +13.2% | 16 | 81% |
| 2014 | +2.3% | 17 | 47% |
| 2015 | +3.4% | 11 | 64% |
| 2016 | -0.4% | 6 | 33% |
| 2017 | -1.8% | 10 | 50% |
| 2018 | -10.8% | 15 | 40% |
| 2019 | -11.1% | 14 | 43% |
| 2020 | +5.8% | 17 | 71% |
| 2021 | +14.7% | 16 | 88% |
| 2022 | +7.2% | 15 | 60% |
| 2023 | +1.0% | 10 | 60% |
| 2024 | +12.1% | 19 | 63% |
| 2025 | +12.6% | 16 | 75% |
| 2026 | -2.8% | 8 | 38% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 68 | 62% | +1.18% | +25,494 |
| TQQQ | 68 | 62% | +1.00% | +20,501 |
| QLD | 61 | 66% | +1.04% | +18,647 |
| SOXS | 6 | 67% | +2.57% | +4,006 |
| QID | 8 | 38% | -0.97% | -2,752 |
| SQQQ | 12 | 50% | -0.72% | -4,850 |

Worst trades over the full window, then best:

- SOXL 2019-08-01 to 2019-08-05, 2 bars, -17.5%: stop loss hit (-9.5% <= -8.0%)
- SOXS 2022-07-15 to 2022-07-20, 3 bars, -14.5%: stop loss hit (-14.7% <= -8.0%)
- TQQQ 2011-08-02 to 2011-08-05, 3 bars, -14.2%: stop loss hit (-16.9% <= -8.0%)
- SOXS 2022-10-06 to 2022-10-10, 2 bars, +20.8%: take profit hit (19.7% >= 4.0%)
- SOXL 2024-02-21 to 2024-02-23, 2 bars, +19.9%: take profit hit (17.9% >= 4.0%)
- SOXL 2025-10-23 to 2025-10-24, 1 bars, +15.0%: take profit hit (9.1% >= 4.0%)

Verdict: **profitable on every window**

## Prior-Low Break on Volume

*A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.*

```
Prior-Low Break on Volume (id=3d52c0f11afe, gen=0, origin=seed)
  thesis: A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.
  BUY  25% when: close < prev(low) and close > sma50 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +61.6% | +2321.9% | 0.40 | -37.1% | 369 | 58% | 1.27 | +0.61% | 2.4 bars | -0.73 |
| held-out | 2022-08-01 to 2026-09-22 | +34.8% | +447.9% | 0.76 | -14.6% | 108 | 59% | 1.71 | +1.17% | 2.6 bars | +0.42 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +1.2% | 12 | 67% |
| 2011 | +4.8% | 25 | 68% |
| 2012 | +4.5% | 18 | 61% |
| 2013 | +14.0% | 31 | 71% |
| 2014 | +8.9% | 46 | 65% |
| 2015 | +1.7% | 22 | 45% |
| 2016 | -0.9% | 23 | 48% |
| 2017 | +4.0% | 34 | 50% |
| 2018 | -21.4% | 32 | 28% |
| 2019 | -4.4% | 32 | 50% |
| 2020 | +23.9% | 43 | 70% |
| 2021 | +15.3% | 38 | 68% |
| 2022 | +6.0% | 20 | 60% |
| 2023 | +2.1% | 22 | 59% |
| 2024 | +11.5% | 30 | 60% |
| 2025 | +34.2% | 33 | 82% |
| 2026 | -12.8% | 19 | 16% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 119 | 66% | +1.54% | +69,882 |
| SQQQ | 42 | 60% | +1.58% | +24,397 |
| SOXS | 8 | 75% | +5.61% | +13,951 |
| QLD | 138 | 56% | +0.31% | +11,790 |
| TQQQ | 134 | 58% | +0.20% | +6,628 |
| QID | 39 | 41% | -0.27% | -6,113 |

Worst trades over the full window, then best:

- SOXL 2011-09-20 to 2011-09-22, 2 bars, -17.6%: stop loss hit (-10.8% <= -8.0%)
- SOXL 2019-08-01 to 2019-08-05, 2 bars, -17.5%: stop loss hit (-9.5% <= -8.0%)
- SOXL 2020-02-21 to 2020-02-25, 2 bars, -17.1%: stop loss hit (-20.4% <= -8.0%)
- SOXS 2020-03-05 to 2020-03-09, 2 bars, +30.2%: take profit hit (7.3% >= 4.0%)
- SQQQ 2020-03-11 to 2020-03-12, 1 bars, +25.8%: take profit hit (5.1% >= 4.0%)
- SQQQ 2025-04-02 to 2025-04-04, 2 bars, +18.2%: take profit hit (8.9% >= 4.0%)

Verdict: **profitable on every window**

## Combo: Capitulation or Oversold

*Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.*

```
Combo: Capitulation or Oversold (id=848cb6f4ae8a, gen=0, origin=seed)
  thesis: Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.
  BUY  20% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  BUY  20% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +93.0% | +2321.9% | 0.47 | -25.4% | 596 | 59% | 1.25 | +0.64% | 2.4 bars | -0.28 |
| held-out | 2022-08-01 to 2026-09-22 | +90.6% | +447.9% | 1.09 | -13.8% | 212 | 64% | 1.69 | +1.62% | 2.2 bars | +0.91 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -2.4% | 18 | 44% |
| 2011 | -12.1% | 50 | 50% |
| 2012 | -2.6% | 45 | 47% |
| 2013 | +17.9% | 38 | 79% |
| 2014 | +3.8% | 48 | 58% |
| 2015 | +19.7% | 47 | 68% |
| 2016 | +5.9% | 35 | 63% |
| 2017 | +13.4% | 36 | 69% |
| 2018 | -6.4% | 54 | 50% |
| 2019 | +8.1% | 53 | 57% |
| 2020 | +10.4% | 67 | 60% |
| 2021 | +13.5% | 57 | 61% |
| 2022 | +17.9% | 75 | 59% |
| 2023 | -1.0% | 45 | 64% |
| 2024 | +13.7% | 68 | 57% |
| 2025 | +39.1% | 47 | 74% |
| 2026 | +13.8% | 36 | 58% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 205 | 63% | +1.46% | +127,790 |
| TQQQ | 174 | 68% | +1.06% | +71,745 |
| QLD | 150 | 65% | +1.07% | +57,467 |
| SQQQ | 109 | 48% | +0.49% | +14,586 |
| QID | 74 | 49% | +0.53% | +12,630 |
| SOXS | 107 | 54% | +0.20% | +10,107 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-02-26 to 2020-02-28, 2 bars, -23.5%: stop loss hit (-15.1% <= -8.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=7d39b5760c61, gen=0, origin=seed)
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

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +88.6% | +2321.9% | 0.42 | -25.9% | 789 | 57% | 1.20 | +0.49% | 2.4 bars | -0.38 |
| held-out | 2022-08-01 to 2026-09-22 | +113.3% | +447.9% | 1.16 | -14.8% | 296 | 60% | 1.57 | +1.36% | 2.3 bars | +0.93 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -3.8% | 28 | 50% |
| 2011 | -18.2% | 61 | 46% |
| 2012 | +4.8% | 58 | 53% |
| 2013 | +16.7% | 50 | 70% |
| 2014 | +5.8% | 73 | 66% |
| 2015 | +3.6% | 55 | 55% |
| 2016 | +8.1% | 46 | 61% |
| 2017 | +13.0% | 52 | 62% |
| 2018 | -11.4% | 70 | 44% |
| 2019 | +9.5% | 70 | 56% |
| 2020 | +38.2% | 89 | 64% |
| 2021 | +11.8% | 78 | 60% |
| 2022 | +8.0% | 91 | 55% |
| 2023 | +5.4% | 63 | 63% |
| 2024 | +7.4% | 84 | 52% |
| 2025 | +58.6% | 72 | 74% |
| 2026 | +13.5% | 59 | 49% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 284 | 63% | +1.57% | +198,374 |
| TQQQ | 241 | 63% | +0.74% | +62,103 |
| QLD | 221 | 57% | +0.58% | +46,869 |
| SOXS | 121 | 56% | +0.53% | +27,572 |
| QID | 97 | 45% | +0.09% | +3,536 |
| SQQQ | 135 | 47% | -0.06% | -9,695 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-03-13 to 2020-03-16, 1 bars, -22.6%: take profit hit (8.8% >= 4.0%)
- SOXL 2020-03-23 to 2020-03-25, 2 bars, +40.4%: take profit hit (37.9% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)

Verdict: **profitable on every window**

## Two Red Days (evolved)

*Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Two Red Days (evolved) (id=2092b9e3cc56, gen=0, origin=llm)
  thesis: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 2010-03-11 to 2022-07-29 | +14.6% | +2321.9% | 0.27 | -9.1% | 80 | 64% | 1.37 | +0.92% | 2.0 bars | -0.40 |
| held-out | 2022-08-01 to 2026-09-22 | +23.7% | +447.9% | 1.03 | -3.6% | 36 | 69% | 2.94 | +3.04% | 1.9 bars | +0.28 |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -2.5% | 6 | 67% |
| 2011 | -1.2% | 6 | 50% |
| 2012 | +2.1% | 7 | 57% |
| 2013 | +1.1% | 1 | 100% |
| 2014 | +1.6% | 5 | 60% |
| 2015 | +5.0% | 6 | 100% |
| 2016 | -0.6% | 4 | 50% |
| 2017 | +2.1% | 3 | 100% |
| 2018 | -3.4% | 7 | 57% |
| 2019 | -1.6% | 8 | 62% |
| 2020 | -2.2% | 6 | 33% |
| 2021 | +10.8% | 9 | 100% |
| 2022 | +6.8% | 24 | 54% |
| 2023 | -1.4% | 6 | 50% |
| 2024 | +4.8% | 10 | 70% |
| 2025 | +8.0% | 8 | 88% |
| 2026 | +12.7% | 6 | 83% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 44 | 77% | +3.99% | +42,794 |
| TQQQ | 21 | 90% | +3.03% | +13,133 |
| QLD | 4 | 75% | +0.36% | +420 |
| QID | 11 | 45% | +0.08% | +112 |
| SOXS | 23 | 43% | -0.58% | -3,497 |
| SQQQ | 19 | 53% | -1.01% | -3,579 |

Worst trades over the full window, then best:

- SOXL 2019-05-08 to 2019-05-14, 4 bars, -14.2%: stop loss hit (-17.2% <= -6.0%)
- SOXL 2011-03-08 to 2011-03-10, 2 bars, -13.8%: stop loss hit (-9.2% <= -6.0%)
- SOXS 2010-06-15 to 2010-06-16, 1 bars, -12.2%: stop loss hit (-14.7% <= -6.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: exit rule: ret1 > 0.02
- SOXL 2026-02-05 to 2026-02-09, 2 bars, +16.8%: exit rule: ret1 > 0.02
- SOXS 2022-04-20 to 2022-04-22, 2 bars, +15.5%: exit rule: ret1 > 0.02

Verdict: **profitable on every window**
