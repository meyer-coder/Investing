# Generations

Every NQ 2x run, from the run database. Scores are training fitness (Sharpe plus excess return, less drawdown, churn and hold penalties, with the most recent training months weighted 60-70%); held-out results were never part of a score. Hand-bred genomes are the ones Claude wrote: generation 0 of each island and the round-three children injected at generation 15.

## quick-trade run

Run `run-20260922-233458-d1bf`, population 80, 12 generations, seeded from `the nq_2x style archetypes`. NQ E-mini at 2x, quick trades: holds of about three sessions. Trained 2019-01 to 2026-03-20; the last six months (from 2026-03-23) are held out and never used for selection. Costs 0.2 bp commission + 1 bp slippage a side, about $15 per MNQ round trip.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +2.70 | -4.90 | NQ RSI Washout | +33% | 33 | -37.8% |
| 1 | +3.52 | +1.53 | NQ-Swing | +44% | 53 | -33.4% |
| 2 | +3.80 | +2.52 | Faster NQ-Swing | +162% | 54 | -25.9% |
| 4 | +4.11 | +2.89 | Bolder-NQ-Swing | +318% | 46 | -31.2% |
| 7 | +4.41 | +3.49 | Wider-Bolder-NQ-Swing | +541% | 105 | -15.5% |
| 10 | +4.67 | +3.19 | Faster-Leaner-Wider-Bolder-NQ-Swing-Wider-Bolder | +763% | 102 | -15.5% |
| 11 | +4.71 | +3.37 | Tighter Adaptive-Wider-Bolder-NQ-Swing | +617% | 158 | -22.9% |

## swing run

Run `run-20260922-233529-a664`, population 80, 12 generations, seeded from `the nq_2x style archetypes`. NQ E-mini at 2x, swing: holds up to about two weeks. Trained 2019-01 to 2026-03-20 with the last training year weighted 60%; the last six months are held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.89 | -1.47 | Cautious NQ Prior-Low Break | +201% | 131 | -22.6% |
| 1 | +3.36 | +1.01 | Tighter-Break | +1615% | 160 | -26.5% |
| 2 | +3.41 | +1.87 | Tighter-Break-Tighter-Break | +1594% | 190 | -25.9% |
| 4 | +3.49 | +2.46 | Cautious Tighter-Break-Tighter-Break | +1265% | 198 | -25.9% |
| 7 | +3.55 | +2.55 | Leaner Tighter-Break-Tighter-Break | +1389% | 197 | -27.1% |
| 10 | +3.68 | +2.73 | Tighter Tighter-Break-Tighter-Break | +1291% | 193 | -27.1% |
| 11 | +3.76 | +2.82 | Tighter Tighter-Break-Tighter-Break | +1463% | 194 | -25.9% |

## calendar

Run `run-20260922-233925-dde1`, population 60, 27 generations, seeded from `strategies/nq2x/seeds/calendar.json`. NQ 2x island 'calendar' (swing fitness). Generation 0 written by Claude from strategies/nq2x/seeds/calendar.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.66 | -0.17 | Cautious Turn of the Month, Wide | +319% | 360 | -38.2% |
| 1 | +2.13 | +0.64 | Faster-3211 | +121% | 228 | -27.3% |
| 2 | +2.30 | +1.45 | Patient Faster-Dip | +113% | 129 | -38.3% |
| 4 | +2.60 | +1.73 | Bolder Leaner-Faster-Dip | +170% | 128 | -40.3% |
| 7 | +2.97 | +2.08 | Leaner Stubborn-Leaner-Faster-Dip | +215% | 138 | -24.0% |
| 10 | +3.27 | +2.15 | Adaptive Stubborn-Leaner-Faster-Dip | +286% | 134 | -26.5% |
| 14 | +3.70 | +1.90 | Greedier Stubborn-Leaner-Faster-Dip | +362% | 304 | -38.5% |
| 15 | +3.73 | +2.58 | Patient Stubborn-Leaner-Faster-Dip | +406% | 304 | -38.5% |
| 16 | +3.86 | +3.03 | Cautious Stubborn-Leaner-Faster-Dip | +450% | 299 | -38.5% |
| 20 | +4.08 | +2.94 | Faster Stubborn-Leaner-Faster-Dip | +555% | 303 | -35.3% |
| 26 | +4.13 | +3.00 | Patient Stubborn-Leaner-Faster-Dip | +619% | 303 | -35.3% |

## calm_trend

Run `run-20260922-233956-cb5c`, population 60, 15 generations, seeded from `strategies/nq2x/seeds/calm_trend.json`. NQ 2x island 'calm_trend' (return fitness). Generation 0 written by Claude from strategies/nq2x/seeds/calm_trend.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.72 | +0.02 | Cautious Calm Uptrend | +138% | 276 | -21.6% |
| 1 | +2.26 | +0.97 | Leaner Calm Uptrend | +209% | 450 | -48.9% |
| 2 | +2.48 | +1.11 | Faster Calm Uptrend | +275% | 465 | -48.9% |
| 4 | +2.98 | +1.61 | Patient Calmer-Uptrend | +230% | 474 | -54.0% |
| 7 | +3.36 | +2.44 | Patient-Uptrend-Calmer-Uptrend | +421% | 479 | -48.9% |
| 10 | +3.42 | +2.41 | Adaptive-Patient-Uptrend-Calmer-Uptrend | +489% | 479 | -48.9% |
| 14 | +3.42 | +2.40 | Adaptive-Patient-Uptrend-Calmer-Uptrend | +489% | 479 | -48.9% |

## deep_pullback

Run `run-20260922-234031-4e9e`, population 60, 27 generations, seeded from `strategies/nq2x/seeds/deep_pullback.json`. NQ 2x island 'deep_pullback' (quick fitness). Generation 0 written by Claude from strategies/nq2x/seeds/deep_pullback.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +3.47 | -0.49 | Patient Pullback Book | +1064% | 183 | -33.1% |
| 1 | +3.56 | +1.56 | Greedier Pullback Book | +952% | 200 | -35.8% |
| 2 | +3.57 | +2.80 | Patient-Book | +945% | 198 | -33.4% |
| 4 | +3.83 | +2.59 | Faster Patient-Book | +1209% | 204 | -33.4% |
| 7 | +4.24 | +3.05 | Bolder Patient-Book | +1569% | 212 | -29.8% |
| 10 | +4.31 | +3.44 | Adaptive Patient-Book | +1412% | 233 | -28.0% |
| 14 | +4.38 | +2.89 | Patient Patient-Book | +1397% | 233 | -28.0% |
| 15 | +4.39 | +3.18 | Adaptive Patient-Book | +1419% | 232 | -28.0% |
| 16 | +4.41 | +3.07 | Faster Patient-Book | +1481% | 230 | -28.9% |
| 20 | +4.41 | +1.03 | Faster Patient-Book | +1481% | 230 | -28.9% |
| 26 | +4.45 | +3.33 | Wider Patient-Book | +1533% | 218 | -28.9% |

## momentum

Run `run-20260922-234059-d75d`, population 60, 15 generations, seeded from `strategies/nq2x/seeds/momentum.json`. NQ 2x island 'momentum' (swing fitness). Generation 0 written by Claude from strategies/nq2x/seeds/momentum.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.31 | -0.42 | Calmer Strong Close | +98% | 113 | -21.5% |
| 1 | +1.85 | +0.65 | Leaner Strong Close | +135% | 91 | -19.4% |
| 2 | +1.85 | +1.21 | Greedier Strong Close | +85% | 94 | -14.9% |
| 4 | +2.00 | +1.31 | Tighter Strong Close | +125% | 76 | -21.3% |
| 7 | +2.52 | +1.59 | Patient Tighter-Close | +159% | 251 | -52.1% |
| 10 | +2.85 | +1.21 | Cautious Stubborn-Adaptive-Close-Tighter-Close-T | +315% | 206 | -30.5% |
| 14 | +2.92 | +1.87 | Leaner Stubborn-Adaptive-Close-Tighter-Close-Tig | +314% | 209 | -30.5% |

## patterns

Run `run-20260922-234128-fb09`, population 60, 15 generations, seeded from `strategies/nq2x/seeds/patterns.json`. NQ 2x island 'patterns' (quick fitness). Generation 0 written by Claude from strategies/nq2x/seeds/patterns.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.55 | -0.66 | Wider Three Lower Lows | +18% | 39 | -21.5% |
| 1 | +1.90 | +0.34 | Sharper Narrow Range Day | +1% | 34 | -27.3% |
| 2 | +2.32 | +1.19 | Calmer-Tighter-Lows | +75% | 134 | -26.9% |
| 4 | +2.35 | +1.37 | Sharper Calmer-Tighter-Lows | +86% | 137 | -23.9% |
| 7 | +2.41 | +1.99 | Wider Calmer-Tighter-Lows | +111% | 137 | -23.9% |
| 10 | +2.44 | +1.59 | Sharper Calmer-Tighter-Lows | +68% | 112 | -27.8% |
| 14 | +2.57 | +1.79 | Leaner Calmer-Tighter-Lows | +93% | 101 | -25.1% |

## quick_flush

Run `run-20260922-234156-83fb`, population 60, 27 generations, seeded from `strategies/nq2x/seeds/quick_flush.json`. NQ 2x island 'quick_flush' (quick fitness). Generation 0 written by Claude from strategies/nq2x/seeds/quick_flush.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +2.05 | -0.16 | Greedier 2% Drop in a Bull Market | +47% | 60 | -9.6% |
| 1 | +2.71 | +0.97 | Calmer-Days | +222% | 252 | -29.5% |
| 2 | +2.75 | +1.93 | Faster Calmer-Days | +182% | 278 | -29.2% |
| 4 | +3.08 | +1.26 | Faster Calmer-Days | +84% | 288 | -36.9% |
| 7 | +3.39 | +2.02 | Greedier Calmer-Days | +120% | 293 | -36.1% |
| 10 | +3.55 | +1.60 | Cautious Faster-Cautious-Calmer-Days | +195% | 299 | -30.0% |
| 14 | +3.65 | +2.47 | Cautious Cautious-Faster-Cautious-Calmer-Days | +191% | 286 | -30.4% |
| 15 | +3.77 | +2.42 | Calmer Cautious-Cautious-Faster-Cautious-Calmer- | +243% | 269 | -30.4% |
| 16 | +3.83 | +0.21 | Wider Cautious-Cautious-Faster-Cautious-Calmer-D | +302% | 269 | -30.4% |
| 20 | +4.06 | +3.14 | Faster Cautious-Cautious-Faster-Cautious-Calmer- | +431% | 280 | -29.5% |
| 26 | +4.11 | +3.42 | Greedier Cautious-Cautious-Faster-Cautious-Calme | +488% | 279 | -27.8% |

## trend_plus_dip

Run `run-20260922-234226-bc54`, population 60, 27 generations, seeded from `strategies/nq2x/seeds/trend_plus_dip.json`. NQ 2x island 'trend_plus_dip' (swing fitness). Generation 0 written by Claude from strategies/nq2x/seeds/trend_plus_dip.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +1.61 | +0.40 | Cautious Calm Trend or Z-Dip | +423% | 191 | -48.3% |
| 1 | +2.03 | +0.57 | Stubborn Calm Trend or Z-Dip | +1428% | 131 | -26.5% |
| 2 | +2.67 | +1.26 | Tighter-Z-Dip | +852% | 340 | -41.1% |
| 4 | +2.89 | +0.79 | Faster-Tighter-Z-Dip | +1687% | 135 | -25.0% |
| 7 | +2.96 | +2.16 | Wider Faster-Tighter-Z-Dip | +1848% | 134 | -26.8% |
| 10 | +3.07 | +2.11 | Patient Tighter-Faster-Tighter-Z-Dip | +2707% | 131 | -22.0% |
| 14 | +3.17 | +2.31 | Cautious Tighter-Faster-Tighter-Z-Dip-Faster-Tig | +2297% | 141 | -22.1% |
| 15 | +3.20 | +2.14 | Cautious Tighter-Faster-Tighter-Z-Dip-Faster-Tig | +1985% | 143 | -22.0% |
| 16 | +3.20 | +2.29 | Cautious Tighter-Faster-Tighter-Z-Dip-Faster-Tig | +1985% | 143 | -22.0% |
| 20 | +3.20 | +2.58 | Wider Tighter-Faster-Tighter-Z-Dip-Faster-Tighte | +2113% | 143 | -21.5% |
| 26 | +3.63 | +2.21 | Wider Tighter-Faster-Tighter-Z-Dip-Faster-Tighte | +1751% | 129 | -20.1% |

## volume_flush

Run `run-20260922-234258-18fb`, population 60, 27 generations, seeded from `strategies/nq2x/seeds/volume_flush.json`. NQ 2x island 'volume_flush' (quick fitness). Generation 0 written by Claude from strategies/nq2x/seeds/volume_flush.json; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +3.33 | -0.63 | Flush or Washout Book | +691% | 119 | -22.2% |
| 1 | +3.81 | +2.60 | Calmer Flush or Washout Book | +1531% | 110 | -22.2% |
| 2 | +3.81 | +2.44 | Calmer Flush or Washout Book | +1531% | 110 | -22.2% |
| 4 | +4.50 | +2.82 | Calmer Flush or Washout Book | +2365% | 118 | -23.9% |
| 7 | +4.61 | +3.24 | Wider Flush or Washout Book | +2501% | 118 | -19.8% |
| 10 | +4.62 | +3.32 | Adaptive Flush or Washout Book | +2667% | 115 | -15.4% |
| 14 | +4.92 | +4.02 | Calmer Flush or Washout Book | +2493% | 99 | -13.5% |
| 15 | +4.92 | +3.41 | Calmer Flush or Washout Book | +2493% | 99 | -13.5% |
| 16 | +4.92 | +3.22 | Calmer Flush or Washout Book | +2493% | 99 | -13.5% |
| 20 | +5.03 | +3.88 | Adaptive Flush or Washout Book | +2495% | 98 | -13.5% |
| 26 | +5.04 | +3.62 | Patient Flush or Washout Book | +2480% | 96 | -11.8% |

## calm_trend_v2

Run `run-20260922-234904-edb6`, population 60, 15 generations, seeded from `strategies/nq2x/seeds/calm_trend_v2.json`. NQ 2x island 'calm_trend_v2' (return fitness, stricter drawdown). Generation 0 written by Claude after v1 bred itself into buy-and-hold; trained 2019-01 to 2026-03-20, last six months held out.

| generation | best score | mean score | best agent | its training return | trades | max drawdown |
|---|---|---|---|---|---|---|
| 0 | +2.41 | -0.50 | Bolder Calm Trend, Managed | +946% | 189 | -40.2% |
| 1 | +2.41 | +0.24 | Bolder Calm Trend, Managed | +946% | 189 | -40.2% |
| 2 | +2.71 | +1.91 | Sharper Calm Trend, Managed | +1153% | 169 | -38.8% |
| 4 | +2.98 | +2.06 | Adaptive-Managed | +2012% | 169 | -30.8% |
| 7 | +3.06 | +2.26 | Patient-Adaptive-Managed | +1552% | 166 | -28.1% |
| 10 | +3.08 | +2.52 | Cautious Patient-Adaptive-Managed-Leaner-Adaptiv | +1930% | 167 | -28.1% |
| 14 | +3.08 | +2.45 | Cautious Patient-Adaptive-Managed-Leaner-Adaptiv | +1930% | 167 | -28.1% |
