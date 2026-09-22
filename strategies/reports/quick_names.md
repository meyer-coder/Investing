# Quick leveraged strategies on TQQQ/SQQQ, MUU/MUD, RIOX, SOXL/SOXS (2025-2026)

Universe: TQQQ, SQQQ, MUU, MUD, RIOX, SOXL, SOXS; 2024-10-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 10 bp per side; fills at the next open.

## Capitulation Close

*A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.*

```
Capitulation Close (id=ba134f956898, gen=0, origin=seed)
  thesis: A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.
  BUY  25% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +85.6% | +555.2% | 1.10 | -21.6% | 107 | 56% | 1.65 | +2.66% | 1.9 bars | -0.16 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +27.7% | 50 | 56% |
| 2026 | +45.4% | 57 | 56% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| RIOX | 17 | 71% | +8.60% | +48,063 |
| SOXL | 13 | 69% | +6.19% | +26,343 |
| MUU | 12 | 67% | +4.72% | +17,960 |
| SOXS | 22 | 59% | +2.03% | +12,919 |
| TQQQ | 12 | 75% | +2.22% | +7,087 |
| SQQQ | 7 | 29% | -1.30% | -5,858 |
| MUD | 24 | 29% | -2.54% | -20,504 |

Worst trades over the full window, then best:

- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-04-04 to 2025-04-07, 1 bars, -20.4%: stop loss hit (-18.0% <= -8.0%)
- TQQQ 2025-04-04 to 2025-04-07, 1 bars, -20.3%: stop loss hit (-10.7% <= -8.0%)
- RIOX 2025-02-28 to 2025-03-03, 1 bars, +37.2%: take profit hit (15.4% >= 4.0%)
- MUU 2026-07-30 to 2026-07-31, 1 bars, +31.4%: take profit hit (19.7% >= 4.0%)
- RIOX 2025-12-31 to 2026-01-05, 2 bars, +30.7%: take profit hit (21.8% >= 4.0%)

Verdict: **profitable on every window**

## Red Day Above the 50

*A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.*

```
Red Day Above the 50 (id=74d3bea563fc, gen=0, origin=seed)
  thesis: A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.
  BUY  25% when: ret1 < -0.045 and close > sma50 and volume_ratio > 1.0
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +38.0% | +658.5% | 0.92 | -14.8% | 70 | 59% | 1.42 | +2.07% | 1.8 bars | -0.96 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +26.4% | 33 | 70% |
| 2026 | +9.2% | 37 | 49% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 21 | 81% | +5.16% | +33,044 |
| MUU | 21 | 57% | +1.22% | +7,107 |
| SOXS | 1 | 100% | +22.66% | +5,664 |
| RIOX | 16 | 44% | +0.38% | -125 |
| TQQQ | 7 | 43% | -0.51% | -1,773 |
| SQQQ | 4 | 25% | -3.66% | -5,649 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- MUU 2026-07-06 to 2026-07-08, 2 bars, -20.3%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-11-19 to 2025-11-21, 2 bars, -20.3%: stop loss hit (-22.8% <= -8.0%)
- MUU 2026-02-10 to 2026-02-12, 2 bars, +24.6%: take profit hit (17.6% >= 4.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: take profit hit (7.5% >= 4.0%)
- SOXS 2025-04-08 to 2025-04-09, 1 bars, +22.7%: take profit hit (25.6% >= 4.0%)

Verdict: **profitable on every window**

## Oversold Dip Above the 50

*A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.*

```
Oversold Dip Above the 50 (id=b018b81521f3, gen=0, origin=seed)
  thesis: A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.
  BUY  25% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +16.2% | +658.5% | 0.86 | -11.9% | 28 | 64% | 1.54 | +2.34% | 2.1 bars | -1.78 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +17.2% | 20 | 75% |
| 2026 | -0.9% | 8 | 38% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| RIOX | 5 | 60% | +9.32% | +13,262 |
| SOXL | 7 | 86% | +4.82% | +8,742 |
| TQQQ | 7 | 71% | +1.99% | +3,335 |
| SQQQ | 2 | 100% | +5.63% | +2,834 |
| MUD | 2 | 50% | +2.24% | +1,141 |
| MUU | 5 | 20% | -8.91% | -13,078 |

Worst trades over the full window, then best:

- MUU 2025-11-20 to 2025-11-21, 1 bars, -22.4%: stop loss hit (-24.9% <= -10.0%)
- MUU 2026-07-06 to 2026-07-08, 2 bars, -20.3%: stop loss hit (-13.2% <= -10.0%)
- MUU 2025-07-15 to 2025-07-18, 3 bars, -11.4%: stop loss hit (-12.5% <= -10.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: take profit hit (7.5% >= 4.0%)
- RIOX 2025-10-17 to 2025-10-20, 1 bars, +22.1%: take profit hit (11.3% >= 4.0%)
- RIOX 2025-10-23 to 2025-10-24, 1 bars, +21.8%: take profit hit (12.3% >= 4.0%)

Verdict: **profitable on every window**

## Pullback Cluster

*Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.*

```
Pullback Cluster (id=11e0f6352641, gen=0, origin=seed)
  thesis: Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +8.1% | +658.5% | 0.40 | -12.7% | 31 | 61% | 1.23 | +1.29% | 2.4 bars | -2.25 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | -1.0% | 19 | 63% |
| 2026 | +9.2% | 12 | 58% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 10 | 70% | +3.99% | +9,467 |
| TQQQ | 7 | 71% | +1.53% | +2,159 |
| MUU | 7 | 57% | +0.66% | +734 |
| RIOX | 5 | 60% | +0.09% | -106 |
| SQQQ | 2 | 0% | -7.78% | -4,084 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- MUU 2025-11-19 to 2025-11-21, 2 bars, -20.3%: stop loss hit (-22.8% <= -8.0%)
- RIOX 2025-11-03 to 2025-11-05, 2 bars, -11.1%: stop loss hit (-12.1% <= -8.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: take profit hit (7.5% >= 4.0%)
- RIOX 2025-10-17 to 2025-10-20, 1 bars, +22.1%: take profit hit (11.3% >= 4.0%)
- MUU 2026-05-19 to 2026-05-20, 1 bars, +21.8%: take profit hit (10.5% >= 4.0%)

Verdict: **profitable on every window**

## Prior-Low Break on Volume

*A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.*

```
Prior-Low Break on Volume (id=6b975f3b78f0, gen=0, origin=seed)
  thesis: A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.
  BUY  25% when: close < prev(low) and close > sma50 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +19.2% | +658.5% | 0.69 | -12.9% | 54 | 63% | 1.36 | +1.47% | 2.1 bars | -1.31 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +15.1% | 31 | 77% |
| 2026 | +3.6% | 23 | 43% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| SOXL | 11 | 82% | +4.95% | +14,543 |
| RIOX | 11 | 64% | +3.17% | +10,430 |
| SQQQ | 7 | 43% | +1.62% | +2,207 |
| TQQQ | 11 | 73% | +0.24% | -15 |
| MUU | 14 | 50% | -1.71% | -7,823 |

Worst trades over the full window, then best:

- RIOX 2025-07-30 to 2025-08-04, 3 bars, -37.4%: stop loss hit (-39.6% <= -8.0%)
- MUU 2025-11-19 to 2025-11-21, 2 bars, -20.3%: stop loss hit (-22.8% <= -8.0%)
- MUU 2026-05-13 to 2026-05-15, 2 bars, -19.1%: stop loss hit (-8.8% <= -8.0%)
- RIOX 2026-04-29 to 2026-05-01, 2 bars, +22.7%: take profit hit (7.5% >= 4.0%)
- RIOX 2025-10-17 to 2025-10-20, 1 bars, +22.1%: take profit hit (11.3% >= 4.0%)
- MUU 2026-05-19 to 2026-05-20, 1 bars, +21.8%: take profit hit (10.5% >= 4.0%)

Verdict: **profitable on every window**

## Combo: Capitulation or Oversold

*Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.*

```
Combo: Capitulation or Oversold (id=7ce36b782301, gen=0, origin=seed)
  thesis: Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.
  BUY  20% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  BUY  20% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +66.6% | +658.5% | 1.16 | -21.7% | 118 | 58% | 1.59 | +2.41% | 2.0 bars | -0.64 |

| year | return | trades | win |
|---|---|---|---|
| 2025 | +19.5% | 55 | 60% |
| 2026 | +39.4% | 63 | 56% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| RIOX | 18 | 72% | +9.10% | +42,110 |
| SOXL | 16 | 81% | +6.71% | +26,466 |
| TQQQ | 14 | 79% | +3.27% | +9,923 |
| SOXS | 22 | 59% | +1.53% | +7,769 |
| MUU | 16 | 50% | -0.09% | -335 |
| SQQQ | 7 | 29% | -1.94% | -5,124 |
| MUD | 25 | 32% | -2.05% | -13,859 |

Worst trades over the full window, then best:

- MUU 2025-11-20 to 2025-11-21, 1 bars, -22.4%: stop loss hit (-24.9% <= -8.0%)
- SOXL 2025-04-04 to 2025-04-07, 1 bars, -21.8%: stop loss hit (-13.2% <= -8.0%)
- MUU 2025-04-04 to 2025-04-07, 1 bars, -20.4%: stop loss hit (-18.0% <= -8.0%)
- MUU 2026-07-30 to 2026-07-31, 1 bars, +31.4%: take profit hit (19.7% >= 4.0%)
- RIOX 2025-12-31 to 2026-01-05, 2 bars, +30.7%: take profit hit (21.8% >= 4.0%)
- SOXL 2025-04-09 to 2025-04-10, 1 bars, +28.5%: take profit hit (50.4% >= 4.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=c4a1c370db19, gen=0, origin=seed)
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
| full | 2025-01-03 to 2026-09-22 | +76.4% | +658.5% | 1.18 | -16.6% | 169 | 57% | 1.44 | +1.87% | 2.0 bars | -0.60 |

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

## Two Red Days (evolved)

*Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Two Red Days (evolved) (id=870726ca8e85, gen=0, origin=llm)
  thesis: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2025-01-03 to 2026-09-22 | +29.3% | +658.5% | 1.12 | -10.1% | 31 | 71% | 1.96 | +4.50% | 1.5 bars | -1.26 |

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
