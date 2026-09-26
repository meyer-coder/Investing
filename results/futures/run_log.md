# Futures confluence run (Topstep / FundedNext) — 2026-09-26 07:46

* strategies tested: **20,976** (19,920 confluence + 1,056 random controls)
* test window: **2018-09-26 → 2026-09-25** (8 years), intraday only, flat at each session's exit
* recency weights in the score: 8y 0.25 · 3y 0.35 · 6m 0.40 (shrinkage 30 trades)
* wall clock: 4.8 min on 4 workers
* total trades simulated: **15,994,768**

## Data

| market | feed | cost model (round trip) | proxy check vs real contract (5-min returns, last 60 days) |
|---|---|---|---|
| NQ | F_NQ | MNQ: $1.22 RT + 2 ticks | corr 0.990 vs NQ=F over 13,144 bars |
| ES | F_ES | MES: $1.22 RT + 2 ticks | corr 0.977 vs ES=F over 13,138 bars |
| YM | F_YM | MYM: $1.22 RT + 2 ticks | corr 0.980 vs YM=F over 13,180 bars |
| RTY | F_RTY | M2K: $1.22 RT + 2 ticks | corr 0.986 vs RTY=F over 13,134 bars |
| NKD | F_NKD | NKD: $5.32 RT + 2 ticks | corr 0.895 vs NKD=F over 12,109 bars |
| CL | F_CL | MCL: $1.52 RT + 2 ticks | corr 0.954 vs CL=F over 13,627 bars |
| NG | F_NG | MNG: $1.72 RT + 2 ticks | corr 0.901 vs NG=F over 13,230 bars |
| GC | F_GC | MGC: $1.92 RT + 2 ticks | corr 0.977 vs GC=F over 13,633 bars |
| SI | F_SI | SIL: $2.72 RT + 2 ticks | corr 0.973 vs SI=F over 13,596 bars |
| HG | F_HG | MHG: $1.92 RT + 2 ticks | corr 0.960 vs HG=F over 13,552 bars |
| 6E | F_6E | M6E: $1.00 RT + 2 ticks | corr 0.965 vs 6E=F over 13,588 bars |
| 6B | F_6B | M6B: $1.00 RT + 2 ticks | corr 0.961 vs 6B=F over 13,471 bars |
| 6J | F_6J | 6J: $4.22 RT + 2 ticks | corr 0.969 vs 6J=F over 13,590 bars |
| 6A | F_6A | M6A: $1.00 RT + 2 ticks | corr 0.968 vs 6A=F over 13,571 bars |
| 6C | F_6C | 6C: $4.22 RT + 2 ticks | corr 0.924 vs 6C=F over 13,466 bars |
| 6S | F_6S | 6S: $4.22 RT + 2 ticks | corr 0.916 vs 6S=F over 13,400 bars |
| 6N | F_6N | 6N: $4.22 RT + 2 ticks | corr 0.954 vs 6N=F over 13,471 bars |
| 6M | F_6M | 6M: $4.22 RT + 2 ticks | corr 0.863 vs 6M=F over 12,732 bars |
| ZB | F_ZB | ZB: $2.76 RT + 2 ticks | corr 0.867 vs ZB=F over 11,277 bars |
| ZS | F_ZS | ZS: $5.28 RT + 2 ticks | corr 0.957 vs ZS=F over 9,810 bars |
| ETH | F_ETH | MET: $0.72 RT + 2 ticks | corr 0.993 vs ETH-USD over 11,844 bars |
| BTC | F_BTC | MBT: $2.82 RT + 2 ticks | corr 0.977 vs BTC-USD over 11,844 bars |

## Top 25 by recency-weighted score (min 30 trades)

| # | id | strategy | trades | win% | net R/tr | 3y R/tr | 6m R/tr | score | $/day | P(pass) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 43-066 | 20EMA Pullback on Dry Volume + ATR expanding · BTC 15m Ldn+NY · market entry, ATR 1.0 stop, session | 141 | 29 | +0.245 | +1.393 | +3.168 | +0.556 | +4.1 | 24% |
| 2 | 66-206 | Volume Spike Donchian Break · GC 5m all · limit entry, ATR 1.5 stop, session | 3047 | 15 | -0.075 | +0.117 | +1.334 | +0.443 | -27.6 | 43% |
| 3 | 49-035 | Gann 2x1 Support Follow-through + ADX rising · 6J 120m Ldn+NY · limit entry, ATR 1.0 stop, session | 32 | 50 | +0.502 | +1.550 | +5.187 | +0.417 | +1.6 | 17% |
| 4 | 36-221 | Swing Support Engulf + ATR calm · NQ 15m Ldn+NY · stop entry, ATR 1.5 stop, session | 553 | 17 | +0.267 | +0.563 | +0.749 | +0.404 | +17.9 | 46% |
| 5 | 48-132 | Gann 1x1 in Structure + strong close · BTC 30m London · market entry, signal bar stop, session | 141 | 30 | +0.119 | +0.565 | +3.599 | +0.390 | +2.0 | 36% |
| 6 | 71-228 | Demand Zone Oversold + volume spike · GC 5m all · stop entry, signal bar stop, session | 74 | 18 | +0.176 | +0.465 | +7.565 | +0.388 | +1.6 | 23% |
| 7 | 60-089 | MACD Divergence at Lower Band + strong close · NQ 15m London · market entry, swing stop, session | 514 | 30 | +0.284 | +0.265 | +1.295 | +0.384 | +17.7 | 40% |
| 8 | 36-236 | Swing Support Engulf + strong close · 6S 120m Ldn+NY · limit entry, signal bar stop, session | 116 | 35 | +0.431 | +1.049 | +0.877 | +0.378 | +5.0 | 4% |
| 9 | 18-076 | Elliott Wave-2 Pocket Engulf + volume confirm · HG 5m Asia · market entry, ATR 1.5 stop, session | 211 | 26 | +0.009 | +0.031 | +2.358 | +0.337 | +0.2 | 26% |
| 10 | 67-030 | Dry-Volume Pullback in Structure + strong close · GC 15m London · limit entry, signal bar stop, session | 93 | 11 | -0.283 | +0.123 | +5.417 | +0.336 | -3.2 | 21% |
| 11 | 77-091 | BOS Retest Continuation · YM 120m Ldn+NY · limit entry, signal bar stop, trail | 62 | 29 | +0.291 | +0.449 | +4.503 | +0.334 | +2.2 | 19% |
| 12 | 17-178 | Elliott Wave-3 with HTF Trend + ADX rising · ES 1m NY am · market entry, ATR 1.0 stop, session | 1005 | 21 | +0.047 | +0.034 | +1.056 | +0.322 | +5.7 | 49% |
| 13 | 07-154 | Volatility Breakout in Structure + ADX rising · BTC 10m London · stop entry, ATR 1.0 stop, session | 664 | 26 | +0.055 | +0.433 | +0.863 | +0.317 | +4.3 | 43% |
| 14 | 57-096 | Williams %R in Structure + ADX rising · GC 15m Asia · limit entry, ATR 1.5 stop, session | 414 | 35 | -0.022 | +0.361 | +1.161 | +0.312 | -1.1 | 31% |
| 15 | 43-118 | 20EMA Pullback on Dry Volume + ADX rising · GC 60m all · market entry, ATR 1.5 stop, session | 189 | 36 | +0.210 | +0.829 | +0.798 | +0.312 | +4.8 | 8% |
| 16 | 19-074 | Elliott ABC End 200EMA · GC 3m NY am · stop entry, signal bar stop, 3R | 72 | 38 | +0.159 | +0.950 | +1.565 | +0.311 | +1.4 | 1% |
| 17 | 76-177 | BOS with HTF and Volume + volume confirm · NQ 3m NY am · market entry, ATR 1.5 stop, session | 438 | 25 | +0.400 | +0.221 | +0.842 | +0.308 | +21.2 | 34% |
| 18 | 26-203 | Engulfing at 200EMA + not extended · NKD 30m Ldn+NY · market entry, swing stop, trail | 277 | 40 | +0.075 | +0.188 | +1.522 | +0.288 | +2.5 | 23% |
| 19 | 31-204 | Gartley PRZ Rejection + volume confirm · CL 2m all · stop entry, swing stop, session | 692 | 16 | -0.014 | +0.297 | +0.746 | +0.283 | -1.2 | 42% |
| 20 | 71-222 | Demand Zone Oversold + volume spike · ES 10m all · market entry, ATR 1.0 stop, session | 199 | 14 | -0.011 | +0.058 | +2.515 | +0.283 | -0.3 | 25% |
| 21 | 71-045 | Demand Zone Oversold + volume confirm · NQ 30m Ldn+NY · market entry, ATR 1.5 stop, session | 156 | 33 | +0.326 | +0.635 | +1.221 | +0.282 | +6.2 | 8% |
| 22 | 39-203 | Daily Pivot Pin + RSI < 40 · NKD 3m London · limit entry, signal bar stop, session | 80 | 36 | +0.241 | +0.283 | +2.475 | +0.278 | +2.3 | 19% |
| 23 | 22-003 | FVG in the Golden Pocket + volume confirm · YM 3m NY pm · stop entry, signal bar stop, session | 75 | 39 | +0.494 | +0.478 | +4.516 | +0.268 | +4.5 | 5% |
| 24 | 09-200 | Squeeze Box Break · ES 15m Asia · stop entry, ATR 1.0 stop, trail | 41 | 49 | +0.490 | +0.948 | +1.098 | +0.262 | +2.4 | 2% |
| 25 | 28-035 | Harami Oversold in Structure + volume confirm · 6J 15m all · limit entry, ATR 1.0 stop, session | 332 | 20 | -0.061 | +0.074 | +1.627 | +0.251 | -2.0 | 24% |

## Top 25 by expected value per prop attempt (min 30 trades)

| # | id | strategy | best account | risk/trade | contracts | P(pass) | P(bust) | P(payout) | EV/attempt |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 71-228 | Demand Zone Oversold + volume spike · GC 5m all · stop entry, signal bar stop, session | FundedNext Rapid Daily 100K | $1,500 | 6 GC | 47% | 42% | 24% | $2,115 |
| 2 | 66-206 | Volume Spike Donchian Break · GC 5m all · limit entry, ATR 1.5 stop, session | Topstep Trading Combine 150K | $200 | 1 GC + 2 MGC | 50% | 45% | 36% | $1,887 |
| 3 | 19-074 | Elliott ABC End 200EMA · GC 3m NY am · stop entry, signal bar stop, 3R | FundedNext Rapid Daily 50K | $1,000 | 3 GC + 8 MGC | 70% | 13% | 55% | $1,644 |
| 4 | 40-096 | 200EMA Touch in Structure · GC 15m all · stop entry, signal bar stop, 1R | Topstep Trading Combine 150K | $2,000 | 5 GC + 2 MGC | 37% | 63% | 16% | $1,439 |
| 5 | 57-096 | Williams %R in Structure + ADX rising · GC 15m Asia · limit entry, ATR 1.5 stop, session | FundedNext Rapid Daily 100K | $500 | 1 GC + 8 MGC | 57% | 37% | 35% | $1,413 |
| 6 | 71-045 | Demand Zone Oversold + volume confirm · NQ 30m Ldn+NY · market entry, ATR 1.5 stop, session | FundedNext Rapid Daily 100K | $1,000 | 1 NQ + 1 MNQ | 52% | 35% | 31% | $1,398 |
| 7 | 07-023 | Volatility Breakout in Structure + ATR expanding · NQ 15m all · stop entry, swing stop, 1.5R | Topstep Trading Combine 150K | $1,500 | 8 MNQ | 36% | 64% | 18% | $1,330 |
| 8 | 17-178 | Elliott Wave-3 with HTF Trend + ADX rising · ES 1m NY am · market entry, ATR 1.0 stop, session | Topstep Trading Combine 150K | $300 | 2 ES | 50% | 39% | 35% | $1,323 |
| 9 | 58-142 | StochRSI above VWAP + not extended · HG 120m Asia · stop entry, signal bar stop, 3R | FundedNext Flex 150K | $1,500 | 2 HG + 7 MHG | 44% | 45% | 31% | $1,294 |
| 10 | 41-030 | Tick-Volume VWAP Retest OBV + not extended · GC 5m NY am · stop entry, ATR 1.5 stop, 2R | Topstep Trading Combine 150K | $1,500 | 4 GC + 3 MGC | 37% | 63% | 18% | $1,223 |
| 11 | 25-157 | Morning Star at Swing Support + strong close · YM 15m Ldn+NY · stop entry, swing stop, trail | FundedNext Rapid Daily 100K | $750 | 1 YM + 8 MYM | 55% | 23% | 38% | $1,215 |
| 12 | 54-001 | DI Cross with Volume + ATR expanding · NQ 15m NY am · stop entry, signal bar stop, session | Topstep Trading Combine 150K | $2,000 | 1 NQ + 4 MNQ | 40% | 59% | 22% | $1,196 |
| 13 | 36-221 | Swing Support Engulf + ATR calm · NQ 15m Ldn+NY · stop entry, ATR 1.5 stop, session | FundedNext Rapid Daily 100K | $300 | 6 MNQ | 54% | 37% | 33% | $1,151 |
| 14 | 41-111 | Tick-Volume VWAP Retest OBV + RSI room · NQ 120m London · limit entry, ATR 1.5 stop, session | FundedNext Flex 150K | $2,000 | 1 NQ + 1 MNQ | 40% | 55% | 25% | $1,143 |
| 15 | 14-028 | Bollinger Exhaustion Oversold · CL 10m NY pm · stop entry, signal bar stop, 3R | FundedNext Rapid Daily 100K | $1,000 | 4 CL + 1 MCL | 53% | 36% | 35% | $1,130 |
| 16 | 40-162 | 200EMA Touch in Structure + strong close · GC 15m Ldn+NY · stop entry, signal bar stop, 1R | Topstep Trading Combine 150K | $2,000 | 4 GC + 6 MGC | 36% | 64% | 18% | $1,128 |
| 17 | 52-023 | ROC Zero Cross in Structure + RSI room · NQ 30m London · stop entry, ATR 1.0 stop, 1R | Topstep Trading Combine 150K | $2,000 | 3 NQ + 9 MNQ | 41% | 59% | 22% | $1,108 |
| 18 | 60-089 | MACD Divergence at Lower Band + strong close · NQ 15m London · market entry, swing stop, session | FundedNext Rapid Daily 100K | $400 | 1 NQ | 48% | 48% | 27% | $1,095 |
| 19 | 47-115 | Trendline Break OBV · NKD 15m Asia · stop entry, swing stop, 2R | Topstep Trading Combine 150K | $2,000 | 2 NKD | 42% | 57% | 23% | $1,090 |
| 20 | 55-140 | Momentum BB Mid Pullback · GC 15m all · stop entry, ATR 1.0 stop, session | Topstep Trading Combine 150K | $250 | 1 GC + 2 MGC | 37% | 63% | 22% | $1,072 |
| 21 | 39-136 | Daily Pivot Pin + RSI < 40 · RTY 15m all · market entry, ATR 1.5 stop, 2R | Topstep Trading Combine 150K | $1,500 | 4 RTY + 9 M2K | 39% | 58% | 25% | $1,060 |
| 22 | 15-158 | Liquidity Sweep Key Reversal + strong close · RTY 15m London · limit entry, ATR 1.0 stop, 3R | FundedNext Rapid Daily 100K | $2,000 | 6 RTY | 42% | 32% | 22% | $1,059 |
| 23 | 15-010 | Liquidity Sweep Key Reversal + volume confirm · HG 5m Asia · market entry, signal bar stop, 3R | FundedNext Rapid Daily 100K | $2,000 | 6 HG | 48% | 47% | 26% | $1,038 |
| 24 | 06-001 | Range Box Break with Volume + strong close · NQ 15m NY am · market entry, ATR 1.5 stop, trail | FundedNext Rapid Daily 100K | $1,000 | 1 NQ + 4 MNQ | 46% | 47% | 25% | $1,035 |
| 25 | 54-118 | DI Cross with Volume · GC 30m NY pm · limit entry, ATR 1.0 stop, trail | FundedNext Rapid Daily 50K | $2,000 | 4 GC | 57% | 32% | 34% | $1,019 |

## Lessons

**The luck baseline: random entries.** 1,056 coin-flip strategies were run through the same markets, sessions, stops, targets and costs. 3% of them finished the 8 years net-profitable (median -0.189R/trade). Measured against each other, the 95th percentile of the controls' edge t-statistic is 1.54 — the bar a real strategy's edge must clear to look like more than luck. 1,357 of 15,989 confluence strategies with 30+ trades clear it with a positive edge over the matching controls (8.5% vs 5% expected from luck alone).

**Costs decide more than signals on low timeframes.** Before costs 53% of strategies are profitable per trade; after commission, spread and slippage only 7% are. The median cost per trade, in R, by timeframe: 1m 0.248R, 2m 0.245R, 3m 0.239R, 5m 0.229R, 10m 0.206R, 15m 0.188R, 30m 0.155R, 60m 0.110R, 120m 0.087R, 240m 0.061R. A 1-minute strategy has to out-earn roughly ten times the friction of a 60-minute one.

**Does stacking confluence help?** Grouped by how many legs each strategy requires. 1 legs: 417 strategies, median -0.201R net, -0.002R edge vs random, 0.73 trades/week; 2 legs: 4,111 strategies, median -0.184R net, -0.002R edge vs random, 0.99 trades/week; 3 legs: 8,744 strategies, median -0.187R net, -0.002R edge vs random, 0.80 trades/week; 4 legs: 2,717 strategies, median -0.185R net, -0.001R edge vs random, 0.84 trades/week.

**Families with the largest edge over random.** Median gross edge over the matching random controls. Best: Golden Pocket RSI Divergence (+0.021R, 12% profitable); CHoCH with Volume (+0.014R, 12% profitable); Butterfly PRZ Rejection (+0.014R, 15% profitable); Morning Star at Swing Support (+0.013R, 12% profitable); Turtle Soup Volume Spike (+0.013R, 14% profitable). Weakest: Round Number at Swing Support (-0.022R); RSI 30 Cross at Swing Support (-0.023R); Bat PRZ Rejection (-0.035R).

**Market: where the numbers were best.** NQ: -0.054R median, 28% profitable; YM: -0.120R median, 14% profitable; RTY: -0.127R median, 12% profitable; ES: -0.133R median, 12% profitable; GC: -0.138R median, 13% profitable; CL: -0.146R median, 10% profitable; NKD: -0.156R median, 8% profitable; BTC: -0.157R median, 8% profitable; HG: -0.172R median, 7% profitable; 6S: -0.172R median, 7% profitable; NG: -0.182R median, 5% profitable; 6J: -0.182R median, 6% profitable; SI: -0.192R median, 6% profitable; 6N: -0.199R median, 5% profitable; ZS: -0.201R median, 4% profitable; ETH: -0.219R median, 1% profitable; 6C: -0.231R median, 2% profitable; 6B: -0.231R median, 3% profitable; ZB: -0.233R median, 2% profitable; 6M: -0.235R median, 1% profitable; 6E: -0.236R median, 2% profitable; 6A: -0.241R median, 2% profitable.

**Session: where the numbers were best.** NY am: -0.157R median, 9% profitable; Ldn+NY: -0.180R median, 8% profitable; all: -0.183R median, 6% profitable; NY pm: -0.189R median, 7% profitable; London: -0.204R median, 7% profitable; Asia: -0.206R median, 6% profitable.

**Exit style: where the numbers were best.** session: -0.166R median, 12% profitable; 2R: -0.184R median, 7% profitable; trail: -0.185R median, 8% profitable; 3R: -0.188R median, 8% profitable; 1.5R: -0.196R median, 5% profitable; 1R: -0.198R median, 4% profitable. Random controls, gross, by exit: 1.5R +0.000R, 1R -0.001R, 2R +0.011R, 3R +0.004R, session +0.014R, trail +0.013R — exit style alone moves results, which is why edge is measured against controls with the same exit.

**Do winners stay winners?** 1,157 strategies were net-profitable over 8 years. 68% of those were also profitable over the last 3 years, and 41% were profitable in all three windows (8y, 3y, 6m). Filter 'profitable 8y + 3y + 6m' to see them.

**Blind test: would the ranking have worked six months ago?** Scoring every strategy with data up to 6 months ago (same 8y/3y weights) and keeping the top 5% (678 strategies): in the following 6 months their median was -0.073R/trade and 40% made money, versus -0.176R and 23% for all strategies and -0.164R / 19% for random controls. This is the only number here that was not visible when the ranking was made — weigh the leaderboard by it.

**The luck bar for account value.** The optimiser tries 15 plans x 11 risk levels on every strategy and keeps the best, so even coin-flip strategies can look worth an attempt. Of 1,056 random controls, 17% show a positive expected value per attempt and the 95th percentile is +$134. 2,014 of 16,818 confluence strategies have a positive expected value; 625 (3.7%) beat the controls' 95th percentile. Treat an account's EV as real only above that bar.

**Which account wins.** Best account among strategies above the luck bar: FundedNext Rapid Daily 50K: 181 (median EV +$230); Topstep Trading Combine 150K: 160 (median EV +$370); FundedNext Rapid Daily 100K: 108 (median EV +$464); FundedNext Flex 150K: 78 (median EV +$256); FundedNext Rapid Daily 25K: 38 (median EV +$186); Topstep Trading Combine 50K: 28 (median EV +$168); Topstep Trading Combine 100K: 25 (median EV +$189); FundedNext Flex 100K: 4 (median EV +$194). Plans with daily payouts and no consistency rule (FundedNext Rapid Daily) or large payout caps (Topstep 150K) tend to win because an attempt can lose only its fee while payouts keep coming.

**Blind test: pick the account six months ago, trade the last six months.** Using only data up to six months ago (same weights, measured from that date), the optimiser chose each strategy's plan and risk; the last six months were then traded once, in order, from a fresh evaluation. 651 confluence strategies had a pre-cut-off EV above the random controls' 95th percentile (+$204): 17% passed, 3% were paid, 75% blew the evaluation, average net −$148 per account. All 16,700 confluence strategies: 7% passed, 1% were paid, 52% blew the evaluation, average net −$99 per account. Random controls: 8% passed, 2% were paid, 71% blew the evaluation, average net −$110 per account. Split by the sign of the EV six months ago: positive 18% passed, 4% were paid, 77% blew the evaluation, average net −$70 per account; zero or negative 5% passed, 1% were paid, 47% blew the evaluation, average net −$105 per account. This is the only account number here that the choice could not see.

**More risk per trade often pays — with more blown accounts.** Risk per trade chosen for the best account: $100: 3, $150: 4, $200: 15, $250: 8, $300: 20, $400: 23, $500: 31, $750: 60, $1,000: 136, $1,500: 132, $2,000: 193. 552 of those strategies do best at $500 or more per trade; their median chance of blowing the evaluation is 61%. A prop attempt's loss is capped at its fee, so the expected value can rise with risk even as most attempts fail. Size down if you cannot afford a string of resets.


## What we learned: results by macro regime

Median net R per trade across confluence strategies (30+ trades overall, 10+ in the regime), with the random controls alongside.

**Volatility (VIX)** (prior day's VIX close)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| VIX < 15 | 22% | 14,953 | -0.206 | -0.198 | -0.008 | 0.224 |
| VIX 15–20 | 40% | 15,932 | -0.189 | -0.184 | -0.005 | 0.204 |
| VIX 20–30 | 30% | 15,650 | -0.184 | -0.172 | -0.011 | 0.192 |
| VIX ≥ 30 | 7% | 11,774 | -0.169 | -0.154 | -0.015 | 0.185 |

**VIX term structure** (prior day's VIX ÷ VIX3M; above 1 (backwardation) marks acute stress)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| contango | 92% | 15,989 | -0.189 | -0.191 | +0.002 | 0.203 |
| backwardation | 8% | 11,898 | -0.171 | -0.151 | -0.020 | 0.186 |

**Fed policy cycle** (63-day change in the 3-month T-bill yield: above +0.25 pt hiking, below −0.25 pt cutting)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| hiking | 21% | 14,862 | -0.183 | -0.167 | -0.016 | 0.197 |
| on hold | 59% | 15,989 | -0.189 | -0.188 | -0.002 | 0.204 |
| cutting | 19% | 14,702 | -0.191 | -0.183 | -0.008 | 0.207 |

**10-year yield trend** (63-day change in the 10-year Treasury yield, ±0.30 pt)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| yields falling | 21% | 14,949 | -0.195 | -0.179 | -0.015 | 0.209 |
| yields flat | 52% | 15,984 | -0.191 | -0.185 | -0.007 | 0.202 |
| yields rising | 26% | 15,410 | -0.173 | -0.171 | -0.002 | 0.195 |

**US dollar trend** (dollar index vs its 50-day average)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| dollar weak | 45% | 15,966 | -0.192 | -0.186 | -0.006 | 0.202 |
| dollar strong | 55% | 15,988 | -0.183 | -0.181 | -0.003 | 0.200 |

**Equity trend** (S&P 500 vs its 200-day average)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| S&P above 200d | 78% | 15,989 | -0.192 | -0.192 | +0.000 | 0.206 |
| S&P below 200d | 22% | 14,883 | -0.174 | -0.167 | -0.007 | 0.188 |

**Inflation** (latest published US CPI, year over year)

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| CPI < 2.5% | 37% | 15,839 | -0.198 | -0.194 | -0.004 | 0.211 |
| CPI 2.5–4% | 33% | 15,692 | -0.187 | -0.183 | -0.004 | 0.203 |
| CPI ≥ 4% | 31% | 15,668 | -0.178 | -0.168 | -0.010 | 0.193 |

**Event days** (FOMC statement days (federalreserve.gov) and NFP days (BLS rule))

| regime | days | strategies | median R/trade | controls | edge | cost R |
|---|---|---|---|---|---|---|
| normal day | 92% | 15,987 | -0.186 | -0.186 | +0.000 | 0.202 |
| FOMC day | 3% | 9,379 | -0.223 | -0.195 | -0.028 | 0.216 |
| jobs report day | 4% | 9,794 | -0.191 | -0.178 | -0.013 | 0.211 |

**Volatility decides how much the costs hurt.** With VIX under 15 the median strategy made -0.206R per trade and paid a median 0.224R in costs; with VIX at 30 or more it made -0.169R and paid 0.185R. Wider ranges mean wider stops, so the same commission and spread are a smaller slice of each trade. Random controls moved from -0.198R to -0.154R, so most of that shift is the market, not the setups.

**Different setups for calm and panic.** Measured against random entries in the same regime, the best group when VIX was 30 or more was Momentum (+0.009R edge) and the weakest Fibonacci (-0.052R). With VIX under 15 the best was Breakout (+0.016R) and the weakest Harmonic (-0.067R).

**The Fed cycle mattered less than volatility.** By policy cycle the median strategy ranged from -0.191R per trade (cutting) to -0.183R (hiking); edge over random stayed between -0.016R and -0.002R. Hiking months: 2018-09 to 2018-11, 2022-02 to 2023-07. Cutting months: 2019-07 to 2019-12, 2020-03 to 2020-05, 2024-09 to 2025-01, 2025-09 to 2026-01.

**Bear tapes paid the median strategy more than bull tapes.** With the S&P 500 below its 200-day average the median strategy made -0.174R per trade (16% of strategies profitable) against -0.192R (8%) above it. Controls: -0.167R vs -0.192R.

**Hot inflation years.** When the latest CPI print was 4% or higher the median strategy made -0.178R per trade, versus -0.198R below 2.5% (controls -0.168R and -0.194R). CPI was 4% or more in 2021-05 to 2023-06, 2026-07 to 2026-09, which overlaps the 2022 bear market and its high VIX, so this is not an independent effect.

**FOMC and jobs-report days.** Median net R per trade: normal days -0.186R, FOMC days -0.223R, jobs-report days -0.191R. Only strategies with at least 10 trades on those days count, so these rest on 9,379 and 9,794 strategies. Controls: -0.195R and -0.178R.

**Named episodes.** COVID crash (2020-02-20 to 2020-04-30): median -0.162R, 30% of strategies profitable, controls -0.146R; 2022 rate-hike bear market (2022-01-03 to 2022-10-12): median -0.168R, 23% of strategies profitable, controls -0.148R; April 2025 tariff shock (2025-04-02 to 2025-04-30): median -0.174R, 32% of strategies profitable, controls -0.144R. Across the whole 8 years the median was -0.186R.

