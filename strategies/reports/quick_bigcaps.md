# Quick leveraged strategies on 2x long/short mega-cap pairs (2023-2026)

Universe: AAPU, AAPD, TSLL, TSLS, AMZU, AMZD, MSFU, MSFD, GGLL, GGLS, NVDL, NVDD; 2023-09-01 to 2026-09-22; held-out tail 0%; commission 1 bp, slippage 10 bp per side; fills at the next open.

## Capitulation Close

*A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.*

```
Capitulation Close (id=657b4b6e78ce, gen=0, origin=seed)
  thesis: A 4% down day that closes in the bottom quarter of its range on 1.3x volume is a capitulation print; the leveraged fund is usually bought back within two sessions.
  BUY  25% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +51.1% | +67.3% | 1.04 | -15.7% | 175 | 58% | 1.43 | +1.01% | 2.4 bars | +1.18 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +7.1% | 8 | 75% |
| 2024 | +5.3% | 62 | 60% |
| 2025 | +44.7% | 62 | 63% |
| 2026 | -7.5% | 43 | 47% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TSLL | 28 | 68% | +2.85% | +24,775 |
| AAPU | 14 | 71% | +2.63% | +14,235 |
| GGLL | 19 | 74% | +1.97% | +12,608 |
| NVDD | 19 | 63% | +1.47% | +7,950 |
| NVDL | 22 | 55% | +1.17% | +6,202 |
| TSLS | 19 | 58% | +0.35% | +2,150 |
| AMZD | 5 | 40% | -0.70% | -1,269 |
| MSFU | 16 | 56% | -0.17% | -2,122 |
| AMZU | 17 | 53% | -0.05% | -2,225 |
| MSFD | 3 | 0% | -2.63% | -2,831 |
| GGLS | 5 | 20% | -1.77% | -2,832 |
| AAPD | 8 | 38% | -1.65% | -4,985 |

Worst trades over the full window, then best:

- TSLS 2024-11-07 to 2024-11-11, 2 bars, -17.7%: stop loss hit (-10.7% <= -8.0%)
- NVDL 2025-01-08 to 2025-01-13, 2 bars, -17.4%: stop loss hit (-9.4% <= -8.0%)
- TSLL 2024-11-13 to 2024-11-15, 2 bars, -15.0%: stop loss hit (-14.6% <= -8.0%)
- TSLL 2025-04-07 to 2025-04-08, 1 bars, +19.9%: take profit hit (9.0% >= 4.0%)
- TSLL 2025-03-11 to 2025-03-12, 1 bars, +19.4%: take profit hit (4.1% >= 4.0%)
- TSLL 2024-07-12 to 2024-07-15, 1 bars, +17.5%: take profit hit (10.6% >= 4.0%)

Verdict: **profitable on every window**

## Red Day Above the 50

*A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.*

```
Red Day Above the 50 (id=04ca12d7caa4, gen=0, origin=seed)
  thesis: A 4.5% down day while the fund is still above its 50-day mean is a dip inside a trend, not a breakdown; take 3% or two bars.
  BUY  25% when: ret1 < -0.045 and close > sma50 and volume_ratio > 1.0
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +17.9% | +60.1% | 0.55 | -14.5% | 97 | 54% | 1.23 | +0.78% | 2.4 bars | +0.55 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +0.8% | 1 | 100% |
| 2024 | +7.2% | 33 | 55% |
| 2025 | +16.4% | 41 | 56% |
| 2026 | -6.3% | 22 | 45% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 26 | 58% | +2.33% | +14,885 |
| TSLL | 18 | 78% | +2.12% | +10,498 |
| GGLL | 10 | 60% | +2.04% | +5,982 |
| AAPU | 9 | 56% | +2.21% | +5,955 |
| NVDD | 3 | 67% | +2.85% | +2,463 |
| AMZD | 1 | 100% | +2.00% | +588 |
| MSFD | 2 | 0% | -1.85% | -1,069 |
| GGLS | 2 | 0% | -2.95% | -1,783 |
| AAPD | 1 | 0% | -6.81% | -2,002 |
| TSLS | 7 | 43% | -1.72% | -3,690 |
| AMZU | 12 | 42% | -1.57% | -5,731 |
| MSFU | 6 | 17% | -4.47% | -7,922 |

Worst trades over the full window, then best:

- TSLS 2025-03-20 to 2025-03-25, 3 bars, -19.2%: stop loss hit (-17.7% <= -8.0%)
- TSLS 2024-04-25 to 2024-04-30, 3 bars, -17.3%: stop loss hit (-20.3% <= -8.0%)
- TSLL 2024-11-13 to 2024-11-15, 2 bars, -15.0%: stop loss hit (-14.6% <= -8.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- TSLL 2025-01-03 to 2025-01-06, 1 bars, +22.0%: take profit hit (15.1% >= 4.0%)
- TSLS 2025-04-03 to 2025-04-07, 2 bars, +16.8%: take profit hit (9.6% >= 4.0%)

Verdict: **profitable on every window**

## Oversold Dip Above the 50

*A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.*

```
Oversold Dip Above the 50 (id=140bdb30cfa1, gen=0, origin=seed)
  thesis: A 7-bar RSI under 40 with the fund above its 50-day mean: multi-day selling inside an uptrend, sold into the first bounce.
  BUY  25% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=10% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +32.4% | +60.1% | 1.01 | -12.2% | 114 | 54% | 1.53 | +1.05% | 2.7 bars | +1.05 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +1.3% | 2 | 100% |
| 2024 | +3.2% | 45 | 47% |
| 2025 | +35.9% | 42 | 64% |
| 2026 | -6.8% | 25 | 48% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 15 | 73% | +4.49% | +19,691 |
| TSLL | 11 | 64% | +4.05% | +12,957 |
| TSLS | 8 | 100% | +4.56% | +10,562 |
| AMZD | 8 | 62% | +1.40% | +3,463 |
| GGLL | 11 | 64% | +1.30% | +3,351 |
| NVDD | 2 | 50% | +0.78% | +233 |
| AAPD | 6 | 50% | +0.15% | -10 |
| AMZU | 14 | 50% | -0.22% | -849 |
| GGLS | 7 | 43% | -0.51% | -957 |
| MSFD | 10 | 40% | -1.00% | -3,307 |
| MSFU | 10 | 30% | -1.16% | -4,133 |
| AAPU | 12 | 25% | -2.39% | -8,254 |

Worst trades over the full window, then best:

- AMZU 2024-07-16 to 2024-07-19, 3 bars, -14.6%: stop loss hit (-11.9% <= -10.0%)
- AAPU 2026-06-24 to 2026-06-26, 2 bars, -13.9%: stop loss hit (-13.5% <= -10.0%)
- AAPU 2024-08-02 to 2024-08-07, 3 bars, -11.2%: stop loss hit (-11.1% <= -10.0%)
- TSLS 2025-04-03 to 2025-04-07, 2 bars, +16.8%: take profit hit (9.6% >= 4.0%)
- TSLL 2025-01-02 to 2025-01-06, 2 bars, +16.0%: take profit hit (9.5% >= 4.0%)
- NVDL 2026-05-28 to 2026-06-02, 3 bars, +14.6%: take profit hit (12.0% >= 4.0%)

Verdict: **profitable on every window**

## Pullback Cluster

*Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.*

```
Pullback Cluster (id=3a78a17ca292, gen=0, origin=seed)
  thesis: Two consecutive red closes and a 3% loss over five sessions, above the 50-day mean, on above-average volume: a short, sharp pullback that mean-reverts.
  BUY  25% when: ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +31.7% | +60.1% | 1.17 | -9.5% | 56 | 55% | 2.25 | +2.06% | 2.5 bars | +1.13 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +0.2% | 1 | 100% |
| 2024 | +9.0% | 18 | 50% |
| 2025 | +27.2% | 25 | 80% |
| 2026 | -5.1% | 12 | 8% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 7 | 71% | +9.16% | +17,417 |
| TSLL | 7 | 100% | +7.02% | +13,345 |
| GGLL | 6 | 50% | +2.26% | +4,373 |
| AAPD | 5 | 80% | +1.82% | +2,562 |
| TSLS | 3 | 67% | +0.75% | +908 |
| GGLS | 2 | 50% | +0.69% | +569 |
| AAPU | 7 | 43% | +0.21% | +516 |
| MSFD | 3 | 33% | -0.27% | -63 |
| AMZD | 3 | 33% | -0.92% | -924 |
| NVDD | 1 | 0% | -2.75% | -941 |
| MSFU | 6 | 33% | -0.84% | -1,433 |
| AMZU | 6 | 33% | -2.38% | -4,420 |

Worst trades over the full window, then best:

- TSLS 2024-04-25 to 2024-04-30, 3 bars, -17.3%: stop loss hit (-20.3% <= -8.0%)
- AMZU 2024-04-17 to 2024-04-22, 3 bars, -8.4%: stop loss hit (-10.7% <= -8.0%)
- AMZU 2026-01-15 to 2026-01-21, 3 bars, -7.2%: max hold reached (2 bars)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- TSLL 2025-01-03 to 2025-01-06, 1 bars, +22.0%: take profit hit (15.1% >= 4.0%)
- TSLS 2025-04-03 to 2025-04-07, 2 bars, +16.8%: take profit hit (9.6% >= 4.0%)

Verdict: **profitable on every window**

## Prior-Low Break on Volume

*A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.*

```
Prior-Low Break on Volume (id=d1b653c7d75c, gen=0, origin=seed)
  thesis: A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is bought back.
  BUY  25% when: close < prev(low) and close > sma50 and volume_ratio > 1.2
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=25% max_open=4 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +27.2% | +60.1% | 0.70 | -17.1% | 164 | 51% | 1.27 | +0.67% | 2.6 bars | +0.67 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +1.4% | 9 | 44% |
| 2024 | +12.9% | 63 | 52% |
| 2025 | +22.9% | 53 | 53% |
| 2026 | -9.7% | 39 | 49% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| NVDL | 16 | 56% | +3.91% | +15,142 |
| GGLL | 18 | 67% | +2.04% | +13,174 |
| TSLL | 10 | 80% | +1.68% | +4,826 |
| AMZD | 13 | 54% | +0.68% | +2,535 |
| GGLS | 10 | 50% | +0.53% | +1,773 |
| MSFD | 16 | 50% | +0.07% | +499 |
| AAPD | 15 | 40% | -0.08% | -296 |
| TSLS | 9 | 33% | -0.01% | -512 |
| NVDD | 7 | 43% | -0.34% | -897 |
| AMZU | 19 | 47% | -0.00% | -1,338 |
| AAPU | 16 | 50% | -0.31% | -1,836 |
| MSFU | 15 | 40% | -0.85% | -5,361 |

Worst trades over the full window, then best:

- TSLL 2024-11-13 to 2024-11-15, 2 bars, -15.0%: stop loss hit (-14.6% <= -8.0%)
- TSLS 2024-04-24 to 2024-04-29, 3 bars, -14.9%: max hold reached (2 bars)
- GGLL 2025-02-04 to 2025-02-06, 2 bars, -14.1%: stop loss hit (-12.1% <= -8.0%)
- NVDL 2024-02-21 to 2024-02-23, 2 bars, +38.3%: take profit hit (30.9% >= 4.0%)
- TSLL 2025-01-03 to 2025-01-06, 1 bars, +22.0%: take profit hit (15.1% >= 4.0%)
- NVDL 2024-02-01 to 2024-02-05, 2 bars, +20.2%: take profit hit (13.1% >= 4.0%)

Verdict: **profitable on every window**

## Combo: Capitulation or Oversold

*Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.*

```
Combo: Capitulation or Oversold (id=4f1c152cc77e, gen=0, origin=seed)
  thesis: Trade the two best setups as one book: capitulation prints in any regime, oversold dips only above the 50-day. Five 20% slots.
  BUY  20% when: ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3
  BUY  20% when: rsi7 < 40 and close > sma50
  SELL when: position_return > 0.03
  SELL when: bars_held >= 2
  risk: max_pos=20% max_open=5 gross<=100% stop=8% target=4% trail=0% hold<=2 hold>=0 cooldown=1
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +40.2% | +60.1% | 0.96 | -18.7% | 255 | 55% | 1.30 | +0.72% | 2.6 bars | +1.03 |

| year | return | trades | win |
|---|---|---|---|
| 2023 | +2.4% | 3 | 100% |
| 2024 | +4.0% | 98 | 54% |
| 2025 | +50.4% | 94 | 62% |
| 2026 | -12.4% | 60 | 45% |

| symbol | trades | win | avg trade | P&L |
|---|---|---|---|---|
| TSLL | 34 | 68% | +3.35% | +29,101 |
| NVDL | 31 | 61% | +2.28% | +15,652 |
| GGLL | 23 | 65% | +1.07% | +6,433 |
| NVDD | 22 | 59% | +1.26% | +5,975 |
| TSLS | 25 | 68% | +0.91% | +5,898 |
| AMZD | 13 | 54% | +0.59% | +1,875 |
| MSFU | 23 | 52% | +0.04% | -1,469 |
| GGLS | 12 | 33% | -1.04% | -2,913 |
| AMZU | 26 | 54% | -0.36% | -3,712 |
| AAPD | 13 | 38% | -1.15% | -4,613 |
| MSFD | 11 | 27% | -1.79% | -5,478 |
| AAPU | 22 | 41% | -1.27% | -5,865 |

Worst trades over the full window, then best:

- TSLS 2024-11-07 to 2024-11-11, 2 bars, -17.7%: stop loss hit (-10.7% <= -8.0%)
- NVDL 2025-01-08 to 2025-01-13, 2 bars, -17.4%: stop loss hit (-9.4% <= -8.0%)
- TSLL 2024-11-13 to 2024-11-15, 2 bars, -15.0%: stop loss hit (-14.6% <= -8.0%)
- TSLL 2025-04-07 to 2025-04-08, 1 bars, +19.9%: take profit hit (9.0% >= 4.0%)
- TSLL 2025-03-11 to 2025-03-12, 1 bars, +19.4%: take profit hit (4.1% >= 4.0%)
- TSLL 2024-07-12 to 2024-07-15, 1 bars, +17.5%: take profit hit (10.6% >= 4.0%)

Verdict: **profitable on every window**

## Combo: All Five Setups

*Every setup above in one agent, first match wins, five 20% slots. The most active book and the broadest evidence base.*

```
Combo: All Five Setups (id=323b82214d8c, gen=0, origin=seed)
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
| full | 2023-09-13 to 2026-09-22 | +47.5% | +60.1% | 0.93 | -21.1% | 364 | 52% | 1.24 | +0.60% | 2.6 bars | +0.96 |

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

## Two Red Days (evolved)

*Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.*

```
Two Red Days (evolved) (id=b02291f4e58f, gen=0, origin=llm)
  thesis: Two consecutive down days inside a rising 50-day trend: buy the second, sell the first green close.
  BUY  50% when: (ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078   # archetype
  SELL when: ret1 > 0.02   # archetype
  SELL when: bars_held >= 3   # archetype
  risk: max_pos=20% max_open=4 gross<=100% stop=6% target=0% trail=0% hold<=3 hold>=0 cooldown=0
```

| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 2023-09-13 to 2026-09-22 | +21.0% | +60.1% | 1.23 | -6.3% | 30 | 63% | 2.96 | +3.26% | 2.4 bars | +0.68 |

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
