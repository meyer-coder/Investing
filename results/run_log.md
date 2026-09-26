# Confluence production run — 2026-09-26 05:03

* strategies tested: **11,370** (10,290 confluence + 1,080 random controls)
* test window: **2018-09-26 → 2026-09-25** (8 years), intraday only, flat at each session's exit
* recency weights in the score: 8y 0.25 · 3y 0.35 · 6m 0.40 (shrinkage 30 trades)
* wall clock: 2.1 min on 4 workers
* total trades simulated: **9,462,812**

## Data

| market | feed | cost model (round trip) | proxy check vs real contract (5-min returns, last 60 days) |
|---|---|---|---|
| MNQ | NSXUSD | $1.40 RT commission + 2 ticks slippage = 1.20 pts | corr 0.987 vs NQ=F over 13,144 bars |
| MES | SPXUSD | $1.40 RT commission + 2 ticks slippage = 0.78 pts | corr 0.977 vs ES=F over 13,138 bars |
| NAS100 | NSXUSD | 1.5 pt spread + 0.3 pt slippage | corr 0.987 vs NQ=F over 13,144 bars |
| USOIL | WTIUSD | 3 cent spread + 1 cent slippage | corr 0.957 vs CL=F over 13,627 bars |
| EURUSD | EURUSD | 0.5 pip raw spread + $7/lot commission + 0.2 pip slippage = 1.2 pips | corr 0.855 vs EURUSD=X over 16,704 bars |
| GBPUSD | GBPUSD | 0.8 pip spread + $7/lot commission + 0.1 pip slippage = 1.6 pips | corr 0.877 vs GBPUSD=X over 16,991 bars |
| USDJPY | USDJPY | 0.6 pip spread + commission + slippage = 1.4 pips | corr 0.990 vs JPY=X over 16,992 bars |
| XAUUSD | XAUUSD | 25 cent spread + 10 cent slippage | corr 0.975 vs GC=F over 13,633 bars |
| GER40 | GRXEUR | 1.2 pt spread + 0.4 pt slippage | corr 0.972 vs ^GDAXI over 6,115 bars |
* TradingView spot check: CME_MINI:MNQ1! vs NSXUSD, 5-min return corr 0.9992 over 41 bars (2026-09-25 16:50-20:10 UTC (last bars TradingView serves))
* TradingView spot check: CME_MINI:MES1! vs SPXUSD, 5-min return corr 0.9980 over 41 bars (2026-09-25 16:50-20:10 UTC (last bars TradingView serves))

## Top 25 by recency-weighted score (min 30 trades)

| # | id | strategy | trades | win% | net R/tr | 3y R/tr | 6m R/tr | score | $/day | P(pass) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 14-028 | Asia Sweep London Reversal · MNQ 15m London · stop entry, ATR 1.0 stop, session | 312 | 19 | +0.226 | +1.097 | +3.491 | +0.755 | +8.4 | 44% |
| 2 | 18-169 | Prior-Week Low Sweep · USDJPY 3m all · market entry, signal bar stop, session | 243 | 15 | +0.248 | +0.694 | +3.292 | +0.755 | +6.1 | 21% |
| 3 | 14-066 | Asia Sweep London Reversal + range spike · NAS100 15m London · market entry, ATR 1.0 stop, session | 260 | 20 | +0.297 | +1.002 | +4.897 | +0.654 | +9.2 | 39% |
| 4 | 14-182 | Asia Sweep London Reversal + range spike · MES 5m Ldn+NY · limit entry, ATR 1.5 stop, session | 614 | 13 | +0.000 | +0.640 | +2.153 | +0.622 | +0.0 | 42% |
| 5 | CTRL-376 | RANDOM control · USDJPY 5m all · stop entry, ATR 1.0 stop, session | 687 | 11 | -0.072 | +0.162 | +2.195 | +0.555 | -5.0 | 15% |
| 6 | 06-027 | ADX Trend MACD Pullback + ATR expanding · GER40 5m Asia · market entry, signal bar stop, session | 142 | 18 | +0.003 | +1.182 | +1.764 | +0.485 | +0.1 | 25% |
| 7 | 25-190 | Asia Range London Breakout + ADX rising · MNQ 5m Ldn+NY · stop entry, ATR 1.5 stop, session | 1402 | 14 | +0.200 | +0.298 | +1.136 | +0.480 | +33.6 | 48% |
| 8 | 44-102 | London Killzone Continuation + RSI room · NAS100 5m Ldn+NY · stop entry, ATR 1.0 stop, session | 2342 | 9 | -0.059 | +0.244 | +1.171 | +0.468 | -16.6 | 40% |
| 9 | 27-174 | Donchian Breakout HTF ADX + ATR expanding · NAS100 15m Asia · limit entry, signal bar stop, session | 193 | 27 | +0.135 | +0.711 | +1.763 | +0.461 | +3.1 | 30% |
| 10 | 35-027 | Keltner Snapback Exhaustion + range spike · GER40 3m Ldn+NY · market entry, signal bar stop, session | 471 | 18 | +0.434 | +0.802 | +0.584 | +0.454 | +24.8 | 40% |
| 11 | 18-177 | Prior-Week Low Sweep + ATR calm · GBPUSD 1m NY pm · market entry, swing stop, session | 39 | 33 | +1.113 | +2.290 | -1.362 | +0.419 | +4.4 | 3% |
| 12 | 17-118 | Turtle Soup 200EMA · MNQ 5m all · stop entry, swing stop, session | 2862 | 10 | +0.112 | +0.144 | +0.958 | +0.405 | +38.2 | 35% |
| 13 | 17-055 | Turtle Soup 200EMA · MNQ 15m all · stop entry, signal bar stop, session | 1180 | 19 | +0.057 | +0.377 | +0.939 | +0.404 | +8.1 | 46% |
| 14 | 39-091 | Initial Balance Fade · MNQ 1m NY am · limit entry, signal bar stop, session | 225 | 12 | +0.232 | +0.424 | +1.399 | +0.351 | +6.2 | 23% |
| 15 | 46-160 | EMA 9/21 Cross VWAP ADX + ADX rising · USDJPY 15m London · market entry, ATR 1.0 stop, trail | 52 | 27 | +0.214 | +0.562 | +1.849 | +0.349 | +1.1 | 18% |
| 16 | 32-118 | Displacement into FVG + ADX rising · MNQ 3m all · stop entry, swing stop, session | 1868 | 18 | +0.037 | +0.041 | +1.020 | +0.348 | +8.2 | 46% |
| 17 | 05-104 | Supertrend Pullback RSI Reset + ADX rising · EURUSD 3m London · market entry, ATR 1.0 stop, session | 100 | 8 | -0.346 | +0.399 | +3.716 | +0.314 | -3.5 | 22% |
| 18 | 47-154 | Supertrend Flip HTF + strong close · MNQ 15m all · limit entry, ATR 1.0 stop, session | 836 | 16 | -0.052 | +0.247 | +0.903 | +0.309 | -5.2 | 42% |
| 19 | 19-162 | Double Bottom RSI Divergence + strong close · GER40 1m Asia · limit entry, signal bar stop, session | 1071 | 4 | -0.293 | +0.386 | +0.813 | +0.304 | -38.1 | 19% |
| 20 | 44-138 | London Killzone Continuation + RSI room · NAS100 5m Ldn+NY · market entry, signal bar stop, session | 2528 | 11 | -0.130 | +0.099 | +0.882 | +0.303 | -39.4 | 38% |
| 21 | 01-190 | EMA Pullback Engulf · MNQ 15m all · stop entry, ATR 1.5 stop, session | 1719 | 23 | +0.140 | +0.144 | +0.693 | +0.301 | +28.8 | 51% |
| 22 | 03-012 | Triple-Stack Pullback + strong close · NAS100 5m Ldn+NY · limit entry, ATR 1.5 stop, session | 3192 | 12 | -0.128 | +0.112 | +0.819 | +0.292 | -48.7 | 40% |
| 23 | 47-021 | Supertrend Flip HTF · NAS100 15m Ldn+NY · stop entry, ATR 1.5 stop, session | 1005 | 20 | +0.038 | +0.285 | +0.703 | +0.291 | +4.5 | 46% |
| 24 | 44-055 | London Killzone Continuation · MNQ 30m London · limit entry, ATR 1.0 stop, session | 212 | 27 | -0.041 | +0.320 | +2.014 | +0.288 | -1.0 | 17% |
| 25 | 17-010 | Turtle Soup 200EMA + RSI room · MNQ 15m London · stop entry, signal bar stop, session | 367 | 25 | +0.262 | +0.508 | +0.455 | +0.286 | +11.5 | 29% |

## Lessons

**The luck baseline: random entries.** 1,080 coin-flip strategies were run through the same markets, sessions, stops, targets and costs. 5% of them finished the 8 years net-profitable (median -0.162R/trade). Measured against each other, the 95th percentile of the controls' edge t-statistic is 1.55 — the bar a real strategy's edge must clear to look like more than luck. 847 of 9,086 confluence strategies with 30+ trades clear it with a positive edge over the matching controls (9.3% vs 5% expected from luck alone).

**Costs decide more than signals on low timeframes.** Before costs 58% of strategies are profitable per trade; after commission, spread and slippage only 15% are. The median cost per trade, in R, by timeframe: 1m 0.464R, 3m 0.249R, 5m 0.193R, 15m 0.107R, 30m 0.077R, 60m 0.057R. A 1-minute strategy has to out-earn roughly ten times the friction of a 60-minute one.

**Does stacking confluence help?** Grouped by how many legs each strategy requires. 2 legs: 534 strategies, median -0.131R net, -0.002R edge vs random, 2.00 trades/week; 3 legs: 2,762 strategies, median -0.127R net, +0.002R edge vs random, 1.11 trades/week; 4 legs: 4,179 strategies, median -0.124R net, +0.000R edge vs random, 0.81 trades/week; 5 legs: 1,611 strategies, median -0.114R net, +0.007R edge vs random, 0.88 trades/week.

**Families with the largest edge over random.** Median gross edge over the matching random controls. Best: Supertrend Pullback RSI Reset (+0.036R, 34% profitable); NY Open Drive (+0.023R, 25% profitable); MACD Zero-Line 50EMA (+0.018R, 21% profitable); Midnight-Open Order Block (+0.017R, 15% profitable); Judas Swing (+0.017R, 29% profitable). Weakest: Displacement into FVG (-0.013R); Asia Sweep London Reversal (-0.015R); Overnight Low Sweep VWAP Reclaim (-0.023R).

**Market: where the numbers were best.** MNQ: -0.034R median, 36% profitable; NAS100: -0.065R median, 25% profitable; GER40: -0.066R median, 25% profitable; XAUUSD: -0.132R median, 11% profitable; MES: -0.145R median, 10% profitable; USDJPY: -0.171R median, 11% profitable; USOIL: -0.174R median, 7% profitable; GBPUSD: -0.176R median, 7% profitable; EURUSD: -0.183R median, 6% profitable.

**Session: where the numbers were best.** NY am: -0.091R median, 18% profitable; Ldn+NY: -0.115R median, 17% profitable; NY pm: -0.123R median, 14% profitable; all: -0.135R median, 13% profitable; London: -0.151R median, 15% profitable; Asia: -0.194R median, 11% profitable.

**Exit style: where the numbers were best.** session: -0.093R median, 24% profitable; trail: -0.112R median, 16% profitable; 2R: -0.127R median, 14% profitable; 1.5R: -0.128R median, 12% profitable; 3R: -0.130R median, 16% profitable; 1R: -0.141R median, 10% profitable. Random controls, gross, by exit: 1.5R +0.006R, 1R -0.001R, 2R +0.013R, 3R +0.012R, session +0.017R, trail +0.030R — exit style alone moves results, which is why edge is measured against controls with the same exit.

**Do winners stay winners?** 1,400 strategies were net-profitable over 8 years. 73% of those were also profitable over the last 3 years, and 41% were profitable in all three windows (8y, 3y, 6m). Filter 'profitable 8y + 3y + 6m' to see them.

**Blind test: would the ranking have worked six months ago?** Scoring every strategy with data up to 6 months ago (same 8y/3y weights) and keeping the top 5% (403 strategies): in the following 6 months their median was -0.068R/trade and 41% made money, versus -0.116R and 32% for all strategies and -0.136R / 27% for random controls. This is the only number here that was not visible when the ranking was made — weigh the leaderboard by it.

**Prop evaluations reward variance as well as edge.** With $250 risked per trade, a $3,000 target is 12R and the $2,000 trailing drawdown is 8R. Random controls average 4.6% P(pass) (95th percentile 19.1%), because frequent trading alone gives a coin-flip a real chance to hit +12R before -8R. 570 strategies beat the 95th-percentile control; judge P(pass) against that, not against zero.

