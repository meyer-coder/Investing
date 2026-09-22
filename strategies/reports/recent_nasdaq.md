# Recent-regime strategies on TQQQ/SQQQ, SOXL/SOXS, QLD/QID (2010-2026), with trailing 6, 9 and 12 month windows

Universe: TQQQ, SQQQ, SOXL, SOXS, QLD, QID; 2010-03-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 5 bp per side; fills at the next open.

## Combo: Recent Winners

*The five setups that have worked over the last six months, in one book; first match wins, five 20% slots.*

```
Combo: Recent Winners (id=b63c9379eff6, gen=0, origin=seed)
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
| full | 2010-03-11 to 2026-09-22 | +216.0% | +13213.4% | 0.58 | -29.8% | -16.2% | 818 | 57% | 1.37 | +0.79% | 2.3 bars | -1.07 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +17.7% | 26 | 46% | 2.34 | +3.28% | -4.0% | -2.4% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +17.3% | 39 | 46% | 1.72 | +1.96% | -4.5% | -2.4% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +24.8% | 57 | 49% | 1.86 | +2.06% | -8.6% | -2.4% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +3.6% | 24 | 62% |
| 2011 | +1.4% | 48 | 65% |
| 2012 | +2.0% | 37 | 41% |
| 2013 | +18.8% | 46 | 76% |
| 2014 | +8.3% | 49 | 59% |
| 2015 | +11.1% | 41 | 61% |
| 2016 | +1.1% | 42 | 50% |
| 2017 | +8.1% | 38 | 50% |
| 2018 | -15.8% | 53 | 47% |
| 2019 | -1.8% | 51 | 49% |
| 2020 | +9.3% | 58 | 62% |
| 2021 | +21.6% | 59 | 64% |
| 2022 | -5.1% | 66 | 50% |
| 2023 | -7.8% | 45 | 49% |
| 2024 | +11.0% | 64 | 56% |
| 2025 | +49.6% | 60 | 68% |
| 2026 | +18.4% | 37 | 49% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 197 | 60% | +1.29% | +87,309 |
| TQQQ | 184 | 63% | +0.83% | +45,392 |
| SOXS | 86 | 56% | +0.80% | +41,342 |
| QLD | 148 | 63% | +0.82% | +34,084 |
| QID | 82 | 45% | +0.35% | +8,376 |
| SQQQ | 121 | 43% | +0.16% | +2,098 |

Worst trades over the full window, then best:

- SOXL 2020-03-13 to 2020-03-16, 1 bars, -26.0%: take profit hit (7.2% >= 4.0%)
- TQQQ 2015-08-21 to 2015-08-24, 1 bars, -25.4%: stop loss hit (-8.6% <= -8.0%)
- TQQQ 2020-03-13 to 2020-03-16, 1 bars, -22.6%: take profit hit (8.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- SOXL 2020-02-28 to 2020-03-02, 1 bars, +26.3%: take profit hit (19.1% >= 4.0%)
- SQQQ 2020-03-11 to 2020-03-12, 1 bars, +25.8%: take profit hit (5.1% >= 4.0%)

Verdict: **profitable on every window**

## Band Break on Volume

*A close under the lower Bollinger band on 1.2x volume, any regime.*

```
Band Break on Volume (id=b9e0a5b20340, gen=0, origin=seed)
  thesis: A close under the lower Bollinger band on 1.2x volume, any regime.
  BUY  25% when: bb_pct < 0.0 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | -9.9% | +10921.6% | 0.02 | -53.8% | -20.5% | 328 | 55% | 0.96 | +0.02% | 2.4 bars | -1.43 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +10.6% | 9 | 56% | 4.76 | +4.71% | -2.5% | -1.1% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +17.0% | 16 | 62% | 4.14 | +4.09% | -5.4% | -1.8% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +22.5% | 20 | 65% | 4.82 | +4.21% | -5.4% | -1.8% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +0.8% | 9 | 67% |
| 2011 | -11.7% | 18 | 44% |
| 2012 | +4.9% | 16 | 50% |
| 2013 | +20.5% | 27 | 85% |
| 2014 | -6.9% | 19 | 42% |
| 2015 | +4.6% | 15 | 60% |
| 2016 | +3.5% | 18 | 50% |
| 2017 | -0.5% | 15 | 40% |
| 2018 | -5.4% | 26 | 58% |
| 2019 | +13.0% | 21 | 71% |
| 2020 | -26.3% | 18 | 44% |
| 2021 | +5.7% | 29 | 55% |
| 2022 | -27.4% | 19 | 21% |
| 2023 | -6.4% | 23 | 39% |
| 2024 | +5.0% | 21 | 62% |
| 2025 | +14.5% | 18 | 72% |
| 2026 | +17.0% | 16 | 62% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SQQQ | 36 | 44% | +0.37% | +4,113 |
| QID | 32 | 47% | -0.02% | +829 |
| QLD | 80 | 61% | +0.21% | -149 |
| SOXL | 71 | 52% | +0.19% | -3,250 |
| SOXS | 28 | 50% | -0.92% | -3,532 |
| TQQQ | 81 | 60% | -0.14% | -7,113 |

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
Volume Climax (id=3c7c96dc7ebf, gen=0, origin=seed)
  thesis: Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.
  BUY  25% when: volume_ratio > 2.0 and ret1 < -0.03
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +98.8% | +10921.6% | 0.51 | -22.4% | -9.9% | 187 | 58% | 1.77 | +1.60% | 2.3 bars | -0.01 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +18.6% | 7 | 71% | 9.95 | +10.00% | -1.8% | -1.8% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +18.7% | 10 | 70% | 7.60 | +7.03% | -1.8% | -1.8% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +25.8% | 14 | 79% | 9.59 | +6.71% | -2.7% | -2.5% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | +4.0% | 12 | 58% |
| 2011 | -7.9% | 14 | 64% |
| 2012 | -3.0% | 3 | 0% |
| 2013 | +4.8% | 6 | 83% |
| 2014 | -0.2% | 9 | 44% |
| 2015 | +15.4% | 10 | 60% |
| 2016 | +5.0% | 14 | 64% |
| 2017 | +1.3% | 18 | 50% |
| 2018 | -4.7% | 15 | 33% |
| 2019 | -0.3% | 14 | 50% |
| 2020 | -6.8% | 11 | 36% |
| 2021 | +15.7% | 16 | 69% |
| 2022 | +4.3% | 7 | 57% |
| 2023 | -2.7% | 3 | 67% |
| 2024 | +0.2% | 7 | 57% |
| 2025 | +34.8% | 18 | 83% |
| 2026 | +18.7% | 10 | 70% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXS | 24 | 62% | +3.73% | +33,640 |
| TQQQ | 39 | 67% | +2.94% | +32,652 |
| SOXL | 57 | 56% | +0.90% | +20,448 |
| QLD | 43 | 60% | +1.29% | +16,488 |
| QID | 12 | 50% | +0.69% | +2,066 |
| SQQQ | 12 | 25% | -1.63% | -5,978 |

Worst trades over the full window, then best:

- SOXL 2020-02-26 to 2020-02-28, 2 bars, -24.0%: stop loss hit (-15.5% <= -8.0%)
- SOXS 2023-05-26 to 2023-05-30, 1 bars, -21.9%: stop loss hit (-16.0% <= -8.0%)
- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.7%: stop loss hit (-13.2% <= -8.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.6%: take profit hit (50.5% >= 4.0%)
- TQQQ 2025-04-07 to 2025-04-08, 1 bars, +23.4%: take profit hit (12.2% >= 4.0%)
- SOXS 2025-04-08 to 2025-04-09, 1 bars, +22.8%: take profit hit (25.7% >= 4.0%)

Verdict: **profitable on every window**

## Red Day Near the Mean

*A 4% down day within 3% of the 20-day mean on 1.2x volume.*

```
Red Day Near the Mean (id=511892b4d899, gen=0, origin=seed)
  thesis: A 4% down day within 3% of the 20-day mean on 1.2x volume.
  BUY  25% when: ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +59.0% | +9866.3% | 0.34 | -20.4% | -9.4% | 303 | 54% | 1.28 | +0.70% | 2.3 bars | -1.41 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +5.6% | 8 | 38% | 1.87 | +2.94% | -3.5% | -3.0% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +0.2% | 13 | 31% | 0.86 | -0.43% | -8.5% | -3.0% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +3.6% | 24 | 38% | 1.19 | +0.71% | -14.8% | -3.0% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -3.2% | 11 | 27% |
| 2011 | +4.3% | 17 | 71% |
| 2012 | -3.3% | 7 | 29% |
| 2013 | +3.0% | 13 | 69% |
| 2014 | +12.6% | 16 | 69% |
| 2015 | +3.6% | 15 | 53% |
| 2016 | -3.7% | 13 | 38% |
| 2017 | +6.8% | 16 | 50% |
| 2018 | -6.5% | 23 | 43% |
| 2019 | -8.3% | 20 | 45% |
| 2020 | +22.3% | 35 | 69% |
| 2021 | +6.1% | 19 | 68% |
| 2022 | +7.6% | 20 | 60% |
| 2023 | -5.6% | 15 | 47% |
| 2024 | -1.2% | 27 | 52% |
| 2025 | +16.5% | 25 | 48% |
| 2026 | +1.4% | 11 | 36% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 83 | 63% | +1.07% | +25,951 |
| SQQQ | 66 | 45% | +0.78% | +12,197 |
| QID | 36 | 44% | +0.89% | +9,296 |
| SOXS | 25 | 56% | +0.76% | +8,377 |
| QLD | 33 | 55% | +0.70% | +6,315 |
| TQQQ | 60 | 55% | -0.05% | -2,175 |

Worst trades over the full window, then best:

- SOXL 2020-02-21 to 2020-02-25, 2 bars, -17.1%: stop loss hit (-20.4% <= -8.0%)
- SOXS 2023-01-05 to 2023-01-09, 2 bars, -17.0%: stop loss hit (-12.0% <= -8.0%)
- SOXL 2021-01-25 to 2021-01-28, 3 bars, -16.8%: stop loss hit (-21.2% <= -8.0%)
- SQQQ 2020-03-11 to 2020-03-12, 1 bars, +25.8%: take profit hit (5.1% >= 4.0%)
- SOXS 2026-07-31 to 2026-08-03, 1 bars, +23.6%: take profit hit (15.2% >= 4.0%)
- SOXS 2025-04-08 to 2025-04-09, 1 bars, +22.8%: take profit hit (25.7% >= 4.0%)

Verdict: **profitable on every window**

## Two Red Days (evolved)

*Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.*

```
Two Red Days (evolved) (id=55fc0f1bdb0a, gen=0, origin=seed)
  thesis: Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +49.1% | +13213.4% | 0.53 | -9.1% | -3.3% | 122 | 66% | 1.87 | +1.71% | 2.0 bars | -0.72 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +9.0% | 5 | 80% | 6.33 | +8.84% | -1.6% | -0.8% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +12.7% | 6 | 83% | 8.25 | +10.16% | -1.6% | -0.8% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +12.1% | 8 | 75% | 6.15 | +7.32% | -1.6% | -0.8% |

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

## Pullback Cluster

*Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.*

```
Pullback Cluster (id=86ba9990615c, gen=0, origin=seed)
  thesis: Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50
  SELL when: ret1 > 0.01
  SELL when: bars_held >= 3
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=0% trail=0% hold<=3 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2010-03-11 to 2026-09-22 | +50.6% | +13213.4% | 0.28 | -30.7% | -7.8% | 453 | 64% | 1.23 | +0.45% | 2.0 bars | -1.67 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +8.2% | 14 | 57% | 2.06 | +2.43% | -5.2% | -3.7% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +12.6% | 17 | 59% | 2.36 | +2.97% | -7.2% | -3.9% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +14.4% | 25 | 56% | 2.18 | +2.29% | -7.2% | -3.9% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -5.1% | 16 | 62% |
| 2011 | -8.3% | 27 | 59% |
| 2012 | +4.1% | 27 | 67% |
| 2013 | +9.0% | 22 | 77% |
| 2014 | -3.7% | 29 | 59% |
| 2015 | -1.3% | 23 | 57% |
| 2016 | +9.4% | 21 | 67% |
| 2017 | +5.8% | 18 | 83% |
| 2018 | -12.2% | 32 | 56% |
| 2019 | -6.6% | 25 | 60% |
| 2020 | -4.3% | 26 | 69% |
| 2021 | +21.2% | 31 | 81% |
| 2022 | -2.7% | 42 | 60% |
| 2023 | +8.7% | 35 | 57% |
| 2024 | +8.4% | 35 | 57% |
| 2025 | +12.8% | 27 | 74% |
| 2026 | +12.6% | 17 | 59% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 132 | 67% | +1.74% | +62,987 |
| TQQQ | 106 | 72% | +0.88% | +23,356 |
| QLD | 81 | 72% | +0.38% | +6,682 |
| QID | 44 | 55% | -0.60% | -8,319 |
| SOXS | 44 | 52% | -0.84% | -10,318 |
| SQQQ | 46 | 46% | -1.82% | -22,656 |

Worst trades over the full window, then best:

- SOXL 2020-02-24 to 2020-02-28, 4 bars, -29.4%: stop loss hit (-21.5% <= -10.0%)
- QLD 2020-02-24 to 2020-02-28, 4 bars, -19.9%: stop loss hit (-14.2% <= -10.0%)
- SOXS 2022-07-14 to 2022-07-18, 2 bars, -17.9%: stop loss hit (-14.0% <= -10.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: exit rule: ret1 > 0.01
- SOXL 2024-02-21 to 2024-02-23, 2 bars, +19.9%: exit rule: ret1 > 0.01
- SOXL 2022-11-29 to 2022-12-01, 2 bars, +17.8%: exit rule: ret1 > 0.01

Verdict: **profitable on every window**

## Squeeze Days (evolved)

*Volatility contraction followed by a close above the upper band; ride the release for two sessions. Combined with: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Squeeze Days (evolved) (id=f807cb32232d, gen=0, origin=seed)
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
| full | 2010-03-11 to 2026-09-22 | +43.8% | +13213.4% | 0.39 | -22.5% | -4.1% | 279 | 58% | 1.39 | +0.71% | 2.0 bars | -0.25 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +16.9% | 12 | 92% | 10.90 | +6.64% | -1.8% | -0.8% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +15.0% | 16 | 75% | 3.31 | +4.50% | -4.8% | -1.1% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +16.3% | 19 | 74% | 3.27 | +4.10% | -5.6% | -1.1% |

| year | return | trades | win |
|---|---|---|---|
| 2010 | -2.1% | 12 | 50% |
| 2011 | -1.2% | 16 | 56% |
| 2012 | +0.3% | 16 | 44% |
| 2013 | -1.0% | 9 | 22% |
| 2014 | +7.0% | 20 | 70% |
| 2015 | +5.1% | 7 | 100% |
| 2016 | -4.9% | 10 | 40% |
| 2017 | +0.2% | 14 | 71% |
| 2018 | -2.5% | 16 | 56% |
| 2019 | -8.8% | 27 | 48% |
| 2020 | -3.3% | 20 | 40% |
| 2021 | +12.6% | 24 | 58% |
| 2022 | +11.2% | 28 | 61% |
| 2023 | -1.0% | 9 | 56% |
| 2024 | +1.3% | 16 | 62% |
| 2025 | +12.6% | 19 | 74% |
| 2026 | +15.0% | 16 | 75% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 78 | 76% | +3.29% | +55,597 |
| TQQQ | 62 | 69% | +1.41% | +18,075 |
| QLD | 43 | 60% | -0.05% | +535 |
| QID | 25 | 32% | -0.97% | -5,157 |
| SQQQ | 32 | 38% | -1.66% | -10,761 |
| SOXS | 39 | 33% | -1.70% | -13,911 |

Worst trades over the full window, then best:

- SOXL 2011-03-08 to 2011-03-10, 2 bars, -13.8%: stop loss hit (-9.2% <= -6.0%)
- SOXS 2026-01-02 to 2026-01-06, 2 bars, -13.5%: stop loss hit (-9.3% <= -6.0%)
- SOXL 2019-05-08 to 2019-05-13, 3 bars, -13.2%: exit rule: bars_held >= 2
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.1%: take profit hit (22.6% >= 8.0%)
- SOXL 2021-01-06 to 2021-01-08, 2 bars, +18.8%: take profit hit (13.4% >= 8.0%)
- SOXL 2026-02-05 to 2026-02-09, 2 bars, +16.8%: take profit hit (20.3% >= 8.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=a6481c57fd4c, gen=0, origin=seed)
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
| full | 2010-03-11 to 2026-09-22 | +325.1% | +13213.4% | 0.64 | -25.9% | -15.7% | 1099 | 58% | 1.38 | +0.75% | 2.4 bars | -2.21 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | -0.5% | 35 | 37% | 0.99 | +0.03% | -10.7% | -5.0% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +13.5% | 59 | 49% | 1.32 | +1.17% | -10.7% | -5.0% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +20.2% | 81 | 52% | 1.37 | +1.24% | -10.7% | -5.0% |

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
