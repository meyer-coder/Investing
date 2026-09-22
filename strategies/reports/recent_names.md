# Recent-regime strategies on TQQQ/SQQQ, MUU/MUD, RIOX, SOXL/SOXS (2025-2026), with trailing 6, 9 and 12 month windows

Universe: TQQQ, SQQQ, MUU, MUD, RIOX, SOXL, SOXS; 2024-10-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 10 bp per side; fills at the next open.

## Combo: Recent Winners

*The five setups that have worked over the last six months, in one book; first match wins, five 20% slots.*

```
Combo: Recent Winners (id=7b00fd1f034b, gen=0, origin=seed)
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
| full | 2025-01-03 to 2026-09-22 | +79.3% | +658.5% | 1.39 | -12.9% | -8.4% | 137 | 55% | 1.65 | +2.38% | 1.9 bars | -0.08 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +37.0% | 47 | 51% | 1.92 | +3.45% | -9.5% | -4.5% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +54.2% | 71 | 54% | 1.87 | +3.09% | -9.5% | -4.5% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +67.3% | 97 | 55% | 1.82 | +2.89% | -10.8% | -4.5% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +14.0% | 69 | 55% |
| 2026 | +57.3% | 68 | 56% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| RIOX | 25 | 72% | +6.54% | +40,639 |
| SOXL | 21 | 71% | +4.68% | +22,208 |
| SOXS | 14 | 57% | +4.87% | +18,134 |
| TQQQ | 16 | 69% | +2.27% | +7,500 |
| MUU | 23 | 52% | +0.66% | +5,881 |
| SQQQ | 15 | 27% | -1.01% | -5,543 |
| MUD | 23 | 35% | -1.77% | -9,132 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-04-04 to 2025-04-07, 1 bars, -20.4%: stop loss hit (-18.0% <= -8.0%)
- MUU 2026-07-30 to 2026-07-31, 1 bars, +31.4%: take profit hit (19.7% >= 4.0%)
- RIOX 2025-12-31 to 2026-01-05, 2 bars, +30.7%: take profit hit (21.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.5%: take profit hit (50.4% >= 4.0%)

Verdict: **profitable on every window**

## Band Break on Volume

*A close under the lower Bollinger band on 1.2x volume, any regime.*

```
Band Break on Volume (id=691e5d18169a, gen=0, origin=seed)
  thesis: A close under the lower Bollinger band on 1.2x volume, any regime.
  BUY  25% when: bb_pct < 0.0 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +28.9% | +555.2% | 0.66 | -15.9% | -10.5% | 48 | 54% | 1.61 | +2.54% | 1.8 bars | -0.98 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +17.2% | 16 | 56% | 2.07 | +4.46% | -7.5% | -3.9% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +23.7% | 24 | 58% | 2.13 | +3.89% | -7.5% | -3.9% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +33.1% | 28 | 61% | 2.44 | +4.44% | -7.5% | -3.9% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +3.7% | 25 | 48% |
| 2026 | +24.3% | 23 | 61% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 9 | 89% | +9.84% | +22,241 |
| MUU | 5 | 60% | +7.99% | +11,347 |
| RIOX | 7 | 71% | +6.15% | +10,920 |
| TQQQ | 11 | 55% | +0.93% | +1,661 |
| SQQQ | 1 | 0% | -1.85% | -619 |
| SOXS | 5 | 40% | -1.57% | -2,804 |
| MUD | 10 | 20% | -5.01% | -13,740 |

Worst trades over the full window, then best:

- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-04-04 to 2025-04-07, 1 bars, -20.4%: stop loss hit (-18.0% <= -8.0%)
- TQQQ 2025-04-04 to 2025-04-07, 1 bars, -20.3%: stop loss hit (-10.7% <= -8.0%)
- MUU 2026-07-30 to 2026-07-31, 1 bars, +31.4%: take profit hit (19.7% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.5%: take profit hit (50.4% >= 4.0%)
- TQQQ 2025-04-09 to 2025-04-10, 1 bars, +25.3%: take profit hit (35.6% >= 4.0%)

Verdict: **profitable on every window**

## Volume Climax

*Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.*

```
Volume Climax (id=62ca60fb9d55, gen=0, origin=seed)
  thesis: Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.
  BUY  25% when: volume_ratio > 2.0 and ret1 < -0.03
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +29.6% | +555.2% | 0.90 | -10.6% | -7.8% | 53 | 57% | 1.62 | +2.16% | 2.2 bars | -0.57 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +16.8% | 15 | 53% | 2.44 | +3.65% | -6.2% | -2.7% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +16.4% | 22 | 50% | 1.86 | +2.68% | -9.6% | -2.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +29.0% | 31 | 58% | 2.38 | +3.45% | -9.6% | -2.7% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +9.9% | 32 | 59% |
| 2026 | +17.9% | 21 | 52% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXS | 8 | 75% | +8.93% | +19,097 |
| SOXL | 6 | 83% | +9.22% | +15,231 |
| TQQQ | 4 | 100% | +8.14% | +7,618 |
| RIOX | 5 | 60% | +4.99% | +7,331 |
| SQQQ | 3 | 33% | -1.10% | -1,211 |
| MUU | 7 | 57% | -0.99% | -1,758 |
| MUD | 20 | 35% | -2.98% | -16,522 |

Worst trades over the full window, then best:

- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-04-04 to 2025-04-07, 1 bars, -20.4%: stop loss hit (-18.0% <= -8.0%)
- MUD 2026-05-04 to 2026-05-06, 2 bars, -16.4%: stop loss hit (-13.8% <= -8.0%)
- RIOX 2025-12-31 to 2026-01-05, 2 bars, +30.7%: take profit hit (21.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.5%: take profit hit (50.4% >= 4.0%)
- TQQQ 2025-04-07 to 2025-04-08, 1 bars, +23.3%: take profit hit (12.1% >= 4.0%)

Verdict: **profitable on every window**

## Red Day Near the Mean

*A 4% down day within 3% of the 20-day mean on 1.2x volume.*

```
Red Day Near the Mean (id=44c6144e991d, gen=0, origin=seed)
  thesis: A 4% down day within 3% of the 20-day mean on 1.2x volume.
  BUY  25% when: ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +23.9% | +723.0% | 0.76 | -13.5% | -8.5% | 59 | 53% | 1.41 | +1.67% | 2.0 bars | -1.26 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +16.3% | 18 | 50% | 1.75 | +3.13% | -7.5% | -5.7% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +14.7% | 29 | 48% | 1.41 | +1.83% | -12.5% | -5.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +21.4% | 43 | 53% | 1.52 | +2.01% | -13.5% | -5.7% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +6.7% | 32 | 53% |
| 2026 | +16.1% | 27 | 52% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXS | 6 | 83% | +10.08% | +15,845 |
| SOXL | 10 | 70% | +3.04% | +7,785 |
| RIOX | 13 | 62% | +1.67% | +4,821 |
| MUD | 5 | 40% | +0.79% | +1,594 |
| MUU | 12 | 50% | +0.14% | -57 |
| TQQQ | 2 | 50% | -0.74% | -158 |
| SQQQ | 11 | 18% | -1.68% | -5,795 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- MUU 2026-05-13 to 2026-05-15, 2 bars, -19.1%: stop loss hit (-8.8% <= -8.0%)
- RIOX 2026-03-06 to 2026-03-09, 1 bars, -16.8%: stop loss hit (-12.8% <= -8.0%)
- SOXS 2026-07-31 to 2026-08-03, 1 bars, +23.5%: take profit hit (15.2% >= 4.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: take profit hit (7.5% >= 4.0%)
- SOXS 2025-04-08 to 2025-04-09, 1 bars, +22.7%: take profit hit (25.6% >= 4.0%)

Verdict: **profitable on every window**

## Two Red Days (evolved)

*Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.*

```
Two Red Days (evolved) (id=7ebeca117908, gen=0, origin=seed)
  thesis: Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +29.3% | +658.5% | 1.12 | -10.1% | -7.0% | 31 | 71% | 1.96 | +4.50% | 1.5 bars | -1.16 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +14.6% | 13 | 69% | 2.16 | +5.78% | -10.1% | -4.2% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +22.8% | 16 | 75% | 2.69 | +6.90% | -10.1% | -4.2% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +26.0% | 23 | 70% | 2.27 | +5.41% | -10.1% | -4.2% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +5.3% | 15 | 67% |
| 2026 | +22.8% | 16 | 75% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 7 | 86% | +11.31% | +17,878 |
| MUU | 10 | 70% | +3.82% | +8,020 |
| SQQQ | 2 | 100% | +6.60% | +2,658 |
| MUD | 1 | 100% | +7.10% | +1,457 |
| TQQQ | 3 | 67% | +0.10% | -169 |
| RIOX | 8 | 50% | +0.19% | -487 |

Worst trades over the full window, then best:

- RIOX 2025-07-31 to 2025-08-04, 2 bars, -35.2%: stop loss hit (-37.5% <= -6.0%)
- RIOX 2026-07-01 to 2026-07-02, 1 bars, -21.4%: stop loss hit (-21.2% <= -6.0%)
- MUU 2026-07-06 to 2026-07-08, 2 bars, -20.3%: stop loss hit (-13.2% <= -6.0%)
- MUU 2026-05-19 to 2026-05-20, 1 bars, +21.8%: exit rule: ret1 > 0.02
- RIOX 2025-10-23 to 2025-10-24, 1 bars, +21.8%: exit rule: ret1 > 0.02
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.0%: exit rule: ret1 > 0.02

Verdict: **profitable on every window**

## Pullback Cluster

*Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.*

```
Pullback Cluster (id=fb2528d07505, gen=0, origin=seed)
  thesis: Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50
  SELL when: ret1 > 0.01
  SELL when: bars_held >= 3
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=0% trail=0% hold<=3 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +43.7% | +658.5% | 1.16 | -12.3% | -8.5% | 59 | 68% | 1.78 | +2.71% | 1.6 bars | -0.76 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +13.4% | 19 | 68% | 1.62 | +3.04% | -12.3% | -5.3% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +22.9% | 27 | 70% | 1.88 | +3.37% | -12.3% | -7.9% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +38.4% | 41 | 66% | 1.94 | +3.45% | -12.3% | -7.9% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +16.9% | 32 | 66% |
| 2026 | +22.9% | 27 | 70% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 14 | 64% | +5.42% | +23,155 |
| RIOX | 13 | 69% | +3.20% | +10,739 |
| TQQQ | 10 | 80% | +2.10% | +5,864 |
| MUU | 16 | 62% | +0.84% | +2,732 |
| MUD | 1 | 100% | +2.80% | +722 |
| SQQQ | 5 | 60% | +1.03% | +711 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -10.0%)
- MUU 2026-05-18 to 2026-05-19, 1 bars, -22.0%: stop loss hit (-17.9% <= -10.0%)
- RIOX 2026-07-01 to 2026-07-02, 1 bars, -21.4%: stop loss hit (-21.2% <= -10.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: exit rule: ret1 > 0.01
- RIOX 2025-10-17 to 2025-10-20, 1 bars, +22.1%: exit rule: ret1 > 0.01
- RIOX 2025-10-23 to 2025-10-24, 1 bars, +21.8%: exit rule: ret1 > 0.01

Verdict: **profitable on every window**

## Squeeze Days (evolved)

*Volatility contraction followed by a close above the upper band; ride the release for two sessions. Combined with: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Squeeze Days (evolved) (id=7c0826a1b254, gen=0, origin=seed)
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
| full | 2025-01-03 to 2026-09-22 | +32.0% | +658.5% | 1.12 | -16.5% | -7.0% | 47 | 70% | 1.71 | +3.24% | 1.5 bars | -1.07 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +9.6% | 19 | 63% | 1.46 | +2.84% | -16.5% | -6.4% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +15.8% | 23 | 65% | 1.68 | +3.59% | -16.5% | -6.4% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +20.8% | 31 | 65% | 1.67 | +3.38% | -16.5% | -6.4% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +14.0% | 24 | 75% |
| 2026 | +15.8% | 23 | 65% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 11 | 91% | +10.10% | +26,378 |
| MUU | 12 | 75% | +4.01% | +10,712 |
| TQQQ | 8 | 75% | +1.33% | +2,220 |
| SQQQ | 3 | 67% | +2.21% | +1,158 |
| RIOX | 8 | 50% | +0.19% | -448 |
| MUD | 2 | 50% | -4.88% | -3,258 |
| SOXS | 3 | 33% | -5.34% | -4,617 |

Worst trades over the full window, then best:

- RIOX 2025-07-31 to 2025-08-04, 2 bars, -35.2%: stop loss hit (-37.5% <= -6.0%)
- RIOX 2026-07-01 to 2026-07-02, 1 bars, -21.4%: stop loss hit (-21.2% <= -6.0%)
- MUU 2026-07-06 to 2026-07-08, 2 bars, -20.3%: stop loss hit (-13.2% <= -6.0%)
- MUU 2026-05-19 to 2026-05-20, 1 bars, +21.8%: take profit hit (10.5% >= 8.0%)
- RIOX 2025-10-23 to 2025-10-24, 1 bars, +21.8%: take profit hit (12.3% >= 8.0%)
- SOXL 2026-05-19 to 2026-05-21, 2 bars, +21.0%: take profit hit (22.5% >= 8.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=725d4df9f29c, gen=0, origin=seed)
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
| full | 2025-01-03 to 2026-09-22 | +76.4% | +658.5% | 1.18 | -16.6% | -8.5% | 169 | 57% | 1.44 | +1.87% | 2.0 bars | -1.00 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +14.6% | 55 | 45% | 1.24 | +1.29% | -16.6% | -5.2% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +48.9% | 91 | 55% | 1.56 | +2.38% | -16.6% | -5.2% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +48.0% | 123 | 54% | 1.42 | +1.77% | -16.6% | -5.2% |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +16.9% | 79 | 59% |
| 2026 | +50.9% | 90 | 56% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 34 | 76% | +4.96% | +44,406 |
| RIOX | 28 | 57% | +2.59% | +19,375 |
| MUU | 27 | 56% | +2.27% | +18,378 |
| SOXS | 23 | 61% | +2.19% | +9,496 |
| TQQQ | 21 | 67% | +1.08% | +4,780 |
| SQQQ | 11 | 36% | -0.78% | -5,506 |
| MUD | 25 | 32% | -2.05% | -14,082 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- RIOX 2025-11-05 to 2025-11-07, 2 bars, -28.4%: stop loss hit (-21.1% <= -8.0%)
- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2026-07-30 to 2026-07-31, 1 bars, +31.4%: take profit hit (19.7% >= 4.0%)
- RIOX 2025-12-31 to 2026-01-05, 2 bars, +30.7%: take profit hit (21.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.5%: take profit hit (50.4% >= 4.0%)

Verdict: **profitable on every window**
