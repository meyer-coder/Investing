# Recent-regime strategies on 2x long/short mega-cap pairs (2023-2026), with trailing 6, 9 and 12 month windows

Universe: AAPU, AAPD, TSLL, TSLS, AMZU, AMZD, MSFU, MSFD, GGLL, GGLS, NVDL, NVDD; 2023-09-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 10 bp per side; fills at the next open.

## Combo: Recent Winners

*The five setups that have worked over the last six months, in one book; first match wins, five 20% slots.*

```
Combo: Recent Winners (id=49297aafec3f, gen=0, origin=seed)
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
| full | 2023-09-13 to 2026-09-22 | +9.2% | +60.1% | 0.29 | -21.2% | -4.4% | 291 | 51% | 1.06 | +0.22% | 2.5 bars | +0.05 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +1.8% | 46 | 48% | 1.04 | +0.09% | -7.6% | -2.6% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -9.1% | 72 | 47% | 0.77 | -0.60% | -15.9% | -2.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -12.6% | 96 | 48% | 0.73 | -0.66% | -18.7% | -2.7% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +0.5% | 5 | 80% |
| 2024 | -3.3% | 111 | 50% |
| 2025 | +23.1% | 104 | 55% |
| 2026 | -8.8% | 71 | 46% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| GGLL | 28 | 68% | +2.66% | +16,729 |
| NVDL | 31 | 55% | +2.56% | +16,435 |
| AAPU | 30 | 53% | +0.98% | +5,673 |
| TSLL | 39 | 64% | +0.62% | +5,644 |
| NVDD | 20 | 40% | +0.59% | +1,990 |
| GGLS | 17 | 47% | -0.11% | -876 |
| AAPD | 14 | 50% | -0.42% | -1,475 |
| MSFD | 13 | 31% | -0.97% | -2,390 |
| MSFU | 28 | 57% | -0.43% | -3,423 |
| AMZD | 22 | 36% | -1.09% | -5,067 |
| TSLS | 22 | 36% | -2.23% | -11,415 |
| AMZU | 27 | 48% | -1.90% | -12,019 |

Worst trades over the full window, then best:

- AMZU 2026-02-04 to 2026-02-06, 2 bars, -28.9%: stop loss hit (-13.5% <= -8.0%)
- NVDL 2024-08-29 to 2024-09-04, 3 bars, -26.1%: stop loss hit (-22.1% <= -8.0%)
- TSLL 2024-04-11 to 2024-04-16, 3 bars, -18.1%: stop loss hit (-13.0% <= -8.0%)
- NVDL 2025-04-07 to 2025-04-08, 1 bars, +40.5%: take profit hit (25.0% >= 4.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- NVDL 2024-02-01 to 2024-02-05, 2 bars, +20.2%: take profit hit (13.1% >= 4.0%)

Verdict: **profitable on every window**

## Band Break on Volume

*A close under the lower Bollinger band on 1.2x volume, any regime.*

```
Band Break on Volume (id=133174bbe6f9, gen=0, origin=seed)
  thesis: A close under the lower Bollinger band on 1.2x volume, any regime.
  BUY  25% when: bb_pct < 0.0 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +15.9% | +67.3% | 0.47 | -15.2% | -3.4% | 140 | 50% | 1.19 | +0.50% | 2.5 bars | +0.19 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +2.6% | 20 | 50% | 1.09 | +0.24% | -4.3% | -2.4% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -0.4% | 35 | 51% | 0.99 | +0.02% | -6.6% | -2.4% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -2.3% | 44 | 50% | 0.92 | -0.15% | -6.6% | -2.4% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +3.6% | 9 | 56% |
| 2024 | +0.4% | 53 | 47% |
| 2025 | +12.0% | 43 | 51% |
| 2026 | -0.4% | 35 | 51% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 10 | 70% | +7.30% | +18,627 |
| AAPU | 14 | 64% | +2.36% | +9,184 |
| AMZU | 12 | 58% | +1.58% | +4,607 |
| TSLL | 15 | 53% | +1.12% | +4,366 |
| GGLL | 13 | 62% | +0.96% | +3,608 |
| GGLS | 12 | 50% | -0.05% | -610 |
| AAPD | 8 | 38% | -0.93% | -2,137 |
| MSFD | 9 | 33% | -1.03% | -2,474 |
| MSFU | 11 | 55% | -0.72% | -2,528 |
| NVDD | 9 | 22% | -1.06% | -2,547 |
| AMZD | 15 | 40% | -1.20% | -4,963 |
| TSLS | 12 | 42% | -2.62% | -8,819 |

Worst trades over the full window, then best:

- TSLL 2025-02-10 to 2025-02-12, 2 bars, -14.8%: stop loss hit (-15.5% <= -8.0%)
- MSFU 2026-01-30 to 2026-02-04, 3 bars, -12.8%: stop loss hit (-12.5% <= -8.0%)
- TSLS 2024-06-27 to 2024-07-02, 3 bars, -11.4%: max hold reached (2 bars)
- NVDL 2025-04-07 to 2025-04-08, 1 bars, +40.5%: take profit hit (25.0% >= 4.0%)
- TSLL 2024-04-23 to 2024-04-25, 2 bars, +21.0%: take profit hit (26.0% >= 4.0%)
- AMZU 2025-04-09 to 2025-04-10, 1 bars, +15.6%: take profit hit (22.7% >= 4.0%)

Verdict: **profitable on every window**

## Volume Climax

*Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.*

```
Volume Climax (id=169666aaa12e, gen=0, origin=seed)
  thesis: Twice normal volume on a 3% down day, any regime: a flush that gets bought within two sessions.
  BUY  25% when: volume_ratio > 2.0 and ret1 < -0.03
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | -7.5% | +67.3% | -0.18 | -19.7% | -5.5% | 124 | 46% | 0.91 | -0.18% | 2.5 bars | -0.24 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +0.5% | 18 | 50% | 1.08 | +0.14% | -4.6% | -2.1% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -8.7% | 28 | 46% | 0.58 | -1.23% | -13.8% | -4.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -9.2% | 36 | 47% | 0.61 | -1.02% | -14.4% | -4.7% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | -0.4% | 8 | 50% |
| 2024 | -0.8% | 48 | 44% |
| 2025 | +2.4% | 40 | 48% |
| 2026 | -8.7% | 28 | 46% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| GGLL | 16 | 75% | +2.72% | +10,043 |
| NVDL | 7 | 57% | +3.85% | +6,878 |
| TSLL | 10 | 60% | +2.55% | +6,390 |
| AAPU | 15 | 47% | +0.48% | +1,459 |
| MSFD | 6 | 33% | -0.98% | -1,278 |
| GGLS | 8 | 25% | -1.60% | -3,120 |
| AMZD | 9 | 22% | -1.47% | -3,304 |
| NVDD | 12 | 33% | -1.05% | -3,332 |
| AAPD | 6 | 17% | -2.42% | -3,662 |
| AMZU | 13 | 54% | -1.28% | -4,166 |
| MSFU | 11 | 45% | -1.91% | -5,524 |
| TSLS | 11 | 45% | -2.67% | -7,622 |

Worst trades over the full window, then best:

- AMZU 2026-02-04 to 2026-02-06, 2 bars, -28.9%: stop loss hit (-13.5% <= -8.0%)
- TSLS 2024-04-25 to 2024-04-30, 3 bars, -17.3%: stop loss hit (-20.3% <= -8.0%)
- TSLL 2025-04-08 to 2025-04-09, 1 bars, -16.1%: stop loss hit (-18.3% <= -8.0%)
- TSLL 2025-03-11 to 2025-03-12, 1 bars, +19.4%: take profit hit (4.1% >= 4.0%)
- TSLL 2024-07-12 to 2024-07-15, 1 bars, +17.5%: take profit hit (10.6% >= 4.0%)
- NVDL 2024-02-22 to 2024-02-23, 1 bars, +14.4%: take profit hit (8.3% >= 4.0%)

Verdict: **not profitable**

## Red Day Near the Mean

*A 4% down day within 3% of the 20-day mean on 1.2x volume.*

```
Red Day Near the Mean (id=b5d43a62cedb, gen=0, origin=seed)
  thesis: A 4% down day within 3% of the 20-day mean on 1.2x volume.
  BUY  25% when: ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | -14.1% | +70.1% | -0.43 | -30.7% | -4.6% | 92 | 50% | 0.81 | -0.56% | 2.6 bars | -1.08 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | -3.8% | 19 | 47% | 0.64 | -0.77% | -10.0% | -1.6% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -6.9% | 24 | 46% | 0.59 | -1.11% | -11.4% | -1.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -7.1% | 31 | 48% | 0.63 | -0.91% | -12.0% | -2.2% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | -1.8% | 4 | 50% |
| 2024 | -0.2% | 39 | 56% |
| 2025 | -4.9% | 26 | 46% |
| 2026 | -7.7% | 23 | 43% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| GGLL | 8 | 75% | +2.95% | +5,764 |
| NVDL | 16 | 50% | +0.84% | +3,241 |
| NVDD | 6 | 50% | +2.04% | +3,142 |
| AAPU | 9 | 56% | -0.03% | -238 |
| GGLS | 2 | 50% | -0.68% | -317 |
| MSFD | 1 | 0% | -2.33% | -503 |
| AAPD | 3 | 33% | -2.81% | -1,808 |
| MSFU | 11 | 55% | -0.78% | -2,059 |
| AMZD | 5 | 40% | -1.92% | -2,267 |
| AMZU | 11 | 45% | -1.72% | -4,239 |
| TSLS | 7 | 14% | -2.95% | -5,450 |
| TSLL | 13 | 62% | -2.40% | -9,092 |

Worst trades over the full window, then best:

- NVDL 2024-08-29 to 2024-09-04, 3 bars, -26.1%: stop loss hit (-22.1% <= -8.0%)
- TSLL 2024-04-11 to 2024-04-16, 3 bars, -18.1%: stop loss hit (-13.0% <= -8.0%)
- NVDL 2025-01-08 to 2025-01-13, 2 bars, -17.4%: stop loss hit (-9.4% <= -8.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- NVDL 2024-02-01 to 2024-02-05, 2 bars, +20.2%: take profit hit (13.1% >= 4.0%)
- NVDD 2024-08-01 to 2024-08-02, 1 bars, +12.6%: take profit hit (7.1% >= 4.0%)

Verdict: **not profitable**

## Two Red Days (evolved)

*Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.*

```
Two Red Days (evolved) (id=4fd6fcac74a7, gen=0, origin=seed)
  thesis: Yesterday down more than 2.8%, today down again, five-day loss beyond 7.8%, close still above the 50-day mean.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +21.0% | +60.1% | 1.23 | -6.3% | -1.8% | 30 | 63% | 2.96 | +3.26% | 2.4 bars | +1.43 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +6.3% | 7 | 71% | 19.63 | +4.43% | -1.0% | -0.7% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +5.0% | 8 | 62% | 4.20 | +3.10% | -2.0% | -1.0% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +0.5% | 11 | 45% | 1.10 | +0.29% | -6.2% | -1.8% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +0.0% | 0 | 0% |
| 2024 | +11.0% | 8 | 62% |
| 2025 | +2.8% | 14 | 64% |
| 2026 | +6.1% | 8 | 62% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TSLL | 9 | 78% | +7.00% | +13,655 |
| NVDL | 6 | 67% | +4.11% | +4,924 |
| GGLL | 4 | 75% | +3.79% | +3,575 |
| GGLS | 1 | 100% | +6.62% | +1,498 |
| TSLS | 1 | 100% | +3.48% | +782 |
| AAPD | 1 | 100% | +2.29% | +519 |
| MSFD | 1 | 0% | -0.43% | -102 |
| AMZD | 1 | 0% | -1.23% | -283 |
| AAPU | 4 | 50% | -1.25% | -1,084 |
| AMZU | 2 | 0% | -5.37% | -2,451 |

Worst trades over the full window, then best:

- NVDL 2025-11-06 to 2025-11-07, 1 bars, -12.0%: stop loss hit (-8.5% <= -6.0%)
- AAPU 2025-01-06 to 2025-01-13, 4 bars, -9.2%: stop loss hit (-6.4% <= -6.0%)
- AMZU 2025-11-17 to 2025-11-19, 2 bars, -8.2%: stop loss hit (-9.0% <= -6.0%)
- TSLL 2024-11-04 to 2024-11-06, 2 bars, +33.2%: exit rule: ret1 > 0.02
- TSLL 2025-01-02 to 2025-01-06, 2 bars, +16.0%: exit rule: ret1 > 0.02
- NVDL 2024-02-22 to 2024-02-23, 1 bars, +14.4%: exit rule: ret1 > 0.02

Verdict: **profitable on every window**

## Pullback Cluster

*Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.*

```
Pullback Cluster (id=7384abe5e147, gen=0, origin=seed)
  thesis: Two red closes and a 3% weekly loss above the 50-day mean on above-average volume.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50
  SELL when: ret1 > 0.01
  SELL when: bars_held >= 3
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=0% trail=0% hold<=3 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +13.6% | +60.1% | 0.41 | -14.4% | -4.1% | 158 | 54% | 1.17 | +0.39% | 2.4 bars | -0.04 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | -0.8% | 34 | 41% | 0.95 | -0.07% | -5.4% | -2.2% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -4.4% | 44 | 41% | 0.79 | -0.38% | -8.8% | -2.2% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -8.1% | 57 | 40% | 0.72 | -0.56% | -13.7% | -3.2% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +2.0% | 3 | 100% |
| 2024 | +12.0% | 60 | 58% |
| 2025 | +1.3% | 52 | 58% |
| 2026 | -1.8% | 43 | 42% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 22 | 55% | +2.48% | +13,909 |
| MSFU | 15 | 67% | +1.47% | +6,112 |
| TSLL | 17 | 65% | +1.20% | +5,488 |
| GGLL | 21 | 52% | +0.61% | +3,557 |
| TSLS | 14 | 71% | +0.36% | +1,025 |
| AAPD | 9 | 56% | +0.34% | +840 |
| MSFD | 6 | 33% | -0.58% | -888 |
| AAPU | 14 | 50% | -0.25% | -925 |
| GGLS | 7 | 43% | -1.08% | -2,139 |
| NVDD | 3 | 0% | -2.82% | -2,445 |
| AMZD | 7 | 57% | -1.62% | -3,549 |
| AMZU | 23 | 48% | -0.99% | -6,918 |

Worst trades over the full window, then best:

- TSLL 2024-12-30 to 2025-01-03, 3 bars, -18.0%: stop loss hit (-18.8% <= -10.0%)
- TSLS 2024-04-25 to 2024-04-29, 2 bars, -17.1%: exit rule: ret1 > 0.01
- AMZU 2024-07-15 to 2024-07-19, 4 bars, -13.8%: stop loss hit (-11.1% <= -10.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: exit rule: ret1 > 0.01
- TSLL 2024-11-01 to 2024-11-06, 3 bars, +25.2%: exit rule: ret1 > 0.01
- GGLL 2025-11-14 to 2025-11-18, 2 bars, +12.4%: exit rule: ret1 > 0.01

Verdict: **profitable on every window**

## Squeeze Days (evolved)

*Volatility contraction followed by a close above the upper band; ride the release for two sessions. Combined with: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Squeeze Days (evolved) (id=bcaf8dd8f3d9, gen=0, origin=seed)
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
| full | 2023-09-13 to 2026-09-22 | +37.6% | +60.1% | 1.57 | -6.5% | -1.8% | 84 | 61% | 2.33 | +1.96% | 2.2 bars | +1.43 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | +4.2% | 16 | 56% | 1.91 | +1.30% | -3.2% | -1.6% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | +4.9% | 23 | 61% | 1.73 | +1.08% | -3.2% | -1.6% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | +0.3% | 29 | 55% | 1.03 | +0.08% | -6.4% | -1.8% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +0.9% | 3 | 67% |
| 2024 | +18.4% | 26 | 54% |
| 2025 | +8.6% | 32 | 66% |
| 2026 | +6.0% | 23 | 61% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TSLL | 17 | 65% | +6.44% | +24,609 |
| NVDL | 10 | 60% | +3.21% | +7,266 |
| GGLL | 11 | 73% | +1.89% | +5,245 |
| AAPU | 9 | 56% | +0.84% | +2,315 |
| TSLS | 2 | 100% | +3.14% | +1,540 |
| GGLS | 4 | 75% | +1.15% | +1,030 |
| MSFD | 6 | 67% | +0.57% | +976 |
| AAPD | 5 | 60% | +0.25% | +596 |
| MSFU | 5 | 80% | +0.38% | +313 |
| AMZD | 5 | 20% | -0.95% | -1,245 |
| NVDD | 1 | 0% | -4.70% | -1,246 |
| AMZU | 9 | 44% | -1.44% | -3,601 |

Worst trades over the full window, then best:

- NVDL 2025-11-06 to 2025-11-07, 1 bars, -12.0%: stop loss hit (-8.5% <= -6.0%)
- AMZU 2025-11-17 to 2025-11-19, 2 bars, -8.2%: stop loss hit (-9.0% <= -6.0%)
- TSLL 2026-08-24 to 2026-08-25, 1 bars, -6.8%: stop loss hit (-7.0% <= -6.0%)
- TSLL 2024-11-04 to 2024-11-06, 2 bars, +33.2%: exit rule: ret1 > 0.02
- TSLL 2024-06-27 to 2024-07-02, 3 bars, +24.8%: take profit hit (15.0% >= 8.0%)
- TSLL 2025-01-02 to 2025-01-06, 2 bars, +16.0%: take profit hit (9.5% >= 8.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=5edcdbad437c, gen=0, origin=seed)
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
| full | 2023-09-13 to 2026-09-22 | +47.5% | +60.1% | 0.93 | -21.1% | -4.1% | 364 | 52% | 1.24 | +0.60% | 2.6 bars | -0.22 |

| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |
|---|---|---|---|---|---|---|---|---|
| since 2026-03-22 | 2026-03-20 to 2026-09-22 | -6.8% | 63 | 48% | 0.75 | -0.60% | -15.5% | -3.7% |
| since 2025-12-22 | 2025-12-19 to 2026-09-22 | -13.3% | 96 | 49% | 0.70 | -0.70% | -21.1% | -3.7% |
| since 2025-09-22 | 2025-09-19 to 2026-09-22 | -10.8% | 126 | 51% | 0.81 | -0.40% | -21.1% | -3.7% |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +3.6% | 12 | 58% |
| 2024 | +9.9% | 135 | 50% |
| 2025 | +48.1% | 127 | 58% |
| 2026 | -12.4% | 90 | 48% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TSLL | 42 | 71% | +2.67% | +29,687 |
| NVDL | 44 | 59% | +2.54% | +25,168 |
| GGLL | 31 | 61% | +1.19% | +13,090 |
| AMZD | 21 | 48% | +0.57% | +2,212 |
| NVDD | 26 | 46% | +0.24% | +587 |
| GGLS | 20 | 45% | -0.02% | -74 |
| MSFU | 29 | 48% | +0.15% | -1,293 |
| TSLS | 31 | 55% | -0.30% | -2,469 |
| AAPD | 25 | 36% | -0.49% | -3,401 |
| MSFD | 23 | 43% | -0.49% | -3,487 |
| AMZU | 38 | 50% | -0.14% | -4,788 |
| AAPU | 34 | 47% | -0.77% | -6,688 |

Worst trades over the full window, then best:

- TSLS 2025-03-20 to 2025-03-25, 3 bars, -19.2%: stop loss hit (-17.7% <= -8.0%)
- TSLS 2024-11-07 to 2024-11-11, 2 bars, -17.7%: stop loss hit (-10.7% <= -8.0%)
- NVDL 2025-01-08 to 2025-01-13, 2 bars, -17.4%: stop loss hit (-9.4% <= -8.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- NVDL 2024-02-01 to 2024-02-05, 2 bars, +20.2%: take profit hit (13.1% >= 4.0%)
- TSLL 2025-04-07 to 2025-04-08, 1 bars, +19.9%: take profit hit (9.0% >= 4.0%)

Verdict: **profitable on every window**
