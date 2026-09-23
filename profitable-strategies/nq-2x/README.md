# NQ E-mini at 2x: 20 profitable strategies, bred over generations

> **FundedNext:** these strategies hold positions for days, and FundedNext Futures
> allows no overnight holds (flat by 3:10 PM Chicago time). For that account use the
> same-day versions in [`../funded/`](../funded/README.md).

Twenty strategies for the Nasdaq-100 E-mini, long only, at twice the account
in notional: about 0.8 of a micro contract (MNQ) on $25,000 at NQ 31,000. Every
one of them:

- made money over the last six months, 23 March to 22 September 2026, a
  window no strategy was ever selected on;
- made money over its training window, January 2019 to March 2026, with a
  profit factor above 1.1 and a drawdown under 40%;
- made money over 2010 to 2018, nine older years the evolution never saw;
- still made money at three times the trading costs.

**The $85 target.** Five of them averaged more than $85 a session on $25,000
over the held-out six months: Calm Trend Champion $111, its No Crash Entry
sibling $110, Volume-Checked Dips $100, Quieter Trend + Z-Dip $93 and Fast
Exit $86. The Champion with a 6% target is just under, at $84.80. They are the
champion and its iterations: stay long while NQ's trend is intact and calm,
buy sharp dips inside it, and manage every trade with a stop, a target, a
trailing stop and a cap of about two and a half weeks.

**Three things to read before the numbers.**

1. The last six months were a steady rally, NQ up 25%, and plain
   buy-and-hold at 2x made about $83 a session. The trend strategies lead this
   ranking because of it. Over the last twelve months, which include a choppy
   half year when NQ lost 5%, Calendar Dips and two of the flush strategies
   made more per session ($62 to $69) than the trend champion ($56).
2. 179 candidates were scored on the held-out six months and these 20 kept,
   so that window worked as a filter, and the best of many results flatters.
   The 2010 to 2018 results and the forward test are the independent checks.
3. At 2x, the worst held-out day ran from -$435 to -$2,418 on $25,000, and 15
   of the 20 had at least one day worse than -$1,000. On a FundedNext $25,000
   account, whose trailing drawdown is $1,000, one such day ends the account,
   and one MNQ, the smallest position there, is already 2.5x. 2x on $25,000 is
   the size asked for; it is not a size that survives that account's rules.

## The plan

- **Paper first, one strategy per account.** All twenty trade the same
  instrument, so running several on one account stacks the exposure: at the
  22 September close fourteen of them say buy, which together would be 28x.
  Pick one, or split the 2x between two strategies at 1x each.
- **Which one.** For the $85 target, Calm Trend Champion (1), or Quieter
  Trend + Z-Dip (4) if you prefer five rules to six. For quick trades, Flush
  Book (14), which made $62 a session over the last twelve months, or Quick
  Dip, Trend-Assisted (11), which trades most often, 27 times in six months.
- **How, on TradingView.** Open a daily MNQ1! chart with back-adjustment on,
  add the strategy's `.pine` file, and set alerts on "buy at next open" and
  "sell at next open". The alert fires on the daily settlement (17:00 New
  York) and the order goes in at the 18:00 reopen. The default is one
  contract, 2.5x on $25,000, a little larger than tested.
- **How, from the repo.** After 17:00 New York,
  `python -m evotrader.cli signals profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --refresh`
  lists every buy for the next open with its MNQ count. Exits follow the
  strategy's rules; the `.pine` file shows them on the chart.
- **Every Friday,** the forward-test ledger:
  `python -m evotrader.cli evaluate profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --test-frac 0 --since 2026-09-23 --refresh`.
  The rules are frozen as of the commit that added this folder; every session
  after 22 September 2026 is out of sample for all twenty.
- **Judge after four to eight weeks,** not one: the trend strategies trade
  about twice a month.
- **At the 22 September close** fourteen say buy: the nine calm-trend
  iterations, Quiet MACD Trend, Quick Dip Trend-Assisted, Calendar Dips,
  Managed Long and Bull Market Crash-Day Exit. NQ settled at 31,028.5, 4.8%
  above its 50-day mean, with 20-day volatility at 16%.

## Ranking, most to least profitable

By return over the last six months, the window no strategy was selected on. Dollar figures are on $25,000 at 2x, per trading session, all sessions counted.

| # | strategy | family | last 6 months, held out | $ per session | trades | profit factor | worst day | training 2019-26 | older 2010-18 | 3x costs |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Calm Trend Champion | calm trend | +71.9% | +$111 | 10 | 15.74 | -$1,061 | +1832% | +172% | profitable |
| 2 | Calm Trend Champion, No Crash Entry | calm trend | +71.3% | +$110 | 12 | 5.69 | -$1,061 | +1504% | +262% | profitable |
| 3 | Calm Trend, Volume-Checked Dips | calm trend | +62.1% | +$100 | 10 | 9.68 | -$2,293 | +2670% | +416% | profitable |
| 4 | Quieter Trend + Z-Dip | calm trend | +57.1% | +$93 | 9 | 6.88 | -$1,061 | +613% | +297% | profitable |
| 5 | Calm Trend, Fast Exit | calm trend | +51.9% | +$86 | 11 | 6.69 | -$1,061 | +385% | +306% | profitable |
| 6 | Calm Trend Champion, 6% Target | calm trend | +50.1% | +$85 | 11 | 3.61 | -$2,287 | +2025% | +160% | profitable |
| 7 | Calm Trend + Washout | calm trend | +46.0% | +$80 | 9 | 9.18 | -$1,564 | +1498% | +406% | profitable |
| 8 | Calm Trend, 10-Session Holds | calm trend | +42.3% | +$74 | 11 | 2.57 | -$2,418 | +445% | +243% | profitable |
| 9 | Calm Trend + Z-Dip Core | calm trend | +38.8% | +$70 | 9 | 5.53 | -$1,564 | +626% | +318% | profitable |
| 10 | Quiet MACD Trend | trend | +34.7% | +$60 | 6 | 6.21 | -$835 | +151% | +170% | profitable |
| 11 | Quick Dip, Trend-Assisted | quick dip | +32.6% | +$59 | 27 | 2.18 | -$2,418 | +442% | +53% | profitable |
| 12 | Flush, Washout or Squeeze | flush and washout | +30.1% | +$54 | 5 | 7.45 | -$958 | +788% | +152% | profitable |
| 13 | Calendar Dips | calendar | +27.6% | +$50 | 25 | 2.29 | -$1,631 | +613% | +23% | profitable |
| 14 | Flush Book | flush and washout | +27.3% | +$49 | 6 | 8.98 | -$671 | +2444% | +86% | profitable |
| 15 | Managed Long | trend | +26.6% | +$53 | 16 | 1.60 | -$2,287 | +1820% | +1024% | profitable |
| 16 | Bull Market, Crash-Day Exit | trend | +24.2% | +$49 | 16 | 1.51 | -$2,287 | +231% | +369% | profitable |
| 17 | Quick Dip, Two Legs | quick dip | +24.0% | +$44 | 5 | 94.13 | -$435 | +67% | +64% | profitable |
| 18 | Washout or Squeeze, Early Exit | flush and washout | +23.0% | +$42 | 5 | 27.54 | -$671 | +906% | +269% | profitable |
| 19 | Deep Pullback Book | pullback | +15.4% | +$31 | 13 | 2.13 | -$1,585 | +1373% | +47% | profitable |
| 20 | Pullback Book, Clean | pullback | +11.5% | +$24 | 12 | 1.84 | -$1,585 | +911% | +110% | profitable |

## The strategies

### 1. Calm Trend Champion

*Calm trend family. Bred in the trend-plus-dip island: generation 25, a mutation of generation 24's leader.*

**In words.** Holds NQ at 2x through calm, intact uptrends and adds sharp-dip entries. It buys when the close crosses back over the 50-day mean, when the index sits at least 4.7% above that mean with 20-day volatility under 22%, when a 60-day slide reaches 9%, and after a 1.2-sigma dip below the 20-day mean while above the 200-day, a 5.7% five-day thrust, or a day when the 14-day average range tops 4.3% of price. It sells when 20-day volatility blows out past 45%, when the index closes under its 50-day mean without being oversold, or when it falls 23% under the 200-day mean. Every trade has a 4.2% stop, a 7% target, a 4.9% trailing stop off its best close and a 13-session cap, and it waits two sessions after an exit.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret60 <= -0.09 or cross_above(close, sma50)`
- BUY when `vol20 < 0.22 and dist_sma50 > 0.047`
- BUY when `zscore20 < -1.18 and close > sma200 or atr_pct > 0.043 or ret5 > 0.057`
- SELL when `vol20 > 0.45`
- SELL when `close < sma50 and zscore20 > -1`
- SELL when `dist_sma200 < -0.23`
- Risk, checked on the close and filled at the next open: stop 4.23%, target 7.00%, trailing stop 4.90% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +71.9% | 10 | 70% | 15.74 | -8.2% | -4.2% |
| last twelve months (six in-sample, six held out) | +68.9% | 18 | 61% | 5.56 | -18.3% | -7.0% |
| training, Jan 2019 to Mar 2026 | +1832% | 131 | 63% | 3.57 | -20.1% | -11.5% |
| older history, 2010 to 2018, never used | +172% | 126 | 55% | 1.29 | -30.4% | -10.0% |
| held out at three times the costs | +70.3% | 10 | | 14.30 | | |

- **Per session over the held-out six months:** +$111 on average; in the market 57% of sessions; best +$1,768, worst -$1,061; 10th and 90th percentile sessions -$265 and +$652; 4.7% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$56 a session on average.
- **Average trade** +2.88% of the position over 6.2 sessions in the held-out window; +1.25% over 6.9 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +2%  2011 -1%  2012 +54%  2013 +40%  2014 +36%  2015 -12%  2016 -9%  2017 +50%  2018 -23%  2019 +19%  2020 +79%  2021 +35%  2022 +43%  2023 +77%  2024 +13%  2025 +147%  2026 +84%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-09 to 04-20 +6.2%; 04-24 to 05-11 +8.5%; 05-14 to 06-04 +3.1%; 06-11 to 06-16 +7.3%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-06 to 08-07 -0.2%; 08-28 to 09-18 -0.7%.

Files: `01_calm_trend_champion.json` (the genome for `evaluate` and `signals`), `01_calm_trend_champion.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 2. Calm Trend Champion, No Crash Entry

*Calm trend family. Bred in the trend-plus-dip island: generation 24.*

**In words.** The champion's sibling without the volatility-spike entry. Its dip entry needs a 1.23-sigma dip, its thrust entry a 5.4% week, and its trend exit tolerates a little more weakness: it sells a close under the 50-day mean only while the z-score is above -1.19. Same 4.2% stop, 7% target, 4.9% trailing stop, 13-session cap and two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret60 <= -0.09 or cross_above(close, sma50)`
- BUY when `vol20 < 0.22 and dist_sma50 > 0.047`
- BUY when `zscore20 < -1.23 and close > sma200 or ret5 > 0.054`
- SELL when `vol20 > 0.45`
- SELL when `close < sma50 and zscore20 > -1.19`
- SELL when `dist_sma200 < -0.23`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 4.90% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +71.3% | 12 | 67% | 5.69 | -11.1% | -4.2% |
| last twelve months (six in-sample, six held out) | +52.5% | 21 | 48% | 2.82 | -22.2% | -7.0% |
| training, Jan 2019 to Mar 2026 | +1504% | 137 | 62% | 2.99 | -19.3% | -11.5% |
| older history, 2010 to 2018, never used | +262% | 131 | 56% | 1.42 | -28.4% | -10.0% |
| held out at three times the costs | +69.4% | 12 | | 5.44 | | |

- **Per session over the held-out six months:** +$110 on average; in the market 52% of sessions; best +$1,768, worst -$1,061; 10th and 90th percentile sessions -$240 and +$652; 4.7% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$46 a session on average.
- **Average trade** +2.41% of the position over 4.5 sessions in the held-out window; +1.12% over 6.4 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +2%  2011 +11%  2012 +42%  2013 +42%  2014 +41%  2015 -18%  2016 +12%  2017 +50%  2018 -19%  2019 +26%  2020 +58%  2021 +49%  2022 +46%  2023 +74%  2024 +8%  2025 +130%  2026 +76%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-09 to 04-20 +6.2%; 04-24 to 05-11 +8.5%; 05-14 to 06-04 +3.1%; 06-11 to 06-16 +7.3%; 07-10 to 07-14 -1.7%; 07-17 to 07-22 +0.4%; 07-27 to 07-31 -0.7%; 08-05 to 08-06 -0.7%; 08-28 to 09-03 -1.6%; 09-14 to 09-15 +0.6%; 09-18 to 09-22 +4.4%.

Files: `02_calm_trend_champion_no_crash_entry.json` (the genome for `evaluate` and `signals`), `02_calm_trend_champion_no_crash_entry.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 3. Calm Trend, Volume-Checked Dips

*Calm trend family. Bred in the trend-plus-dip island: generation 24.*

**In words.** Any close above the 50-day mean with 20-day volatility under 22% counts as trend. The dip and thrust entries (a 1.2-sigma dip above the 200-day, a 5.3% week) are taken only on ordinary volume, under 1.28 times average, so it does not buy into a panic. It also buys a close back over the 50-day and a 9% 60-day slide. Out when volatility passes 50% or the index breaks the 50-day without being oversold; 4.2% stop, 7.3% target, 4.9% trailing stop, 13 sessions, two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret60 <= -0.09 or cross_above(close, sma50)`
- BUY when `close > sma50 and vol20 < 0.22`
- BUY when `(zscore20 < -1.18 and close > sma200 or ret5 > 0.053) and volume_ratio < 1.28`
- SELL when `vol20 > 0.5`
- SELL when `close < sma50 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.23%, target 7.30%, trailing stop 4.90% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +62.1% | 10 | 60% | 9.68 | -11.6% | -9.2% |
| last twelve months (six in-sample, six held out) | +54.5% | 20 | 55% | 3.22 | -20.2% | -9.2% |
| training, Jan 2019 to Mar 2026 | +2670% | 143 | 63% | 2.89 | -23.3% | -11.5% |
| older history, 2010 to 2018, never used | +416% | 146 | 57% | 1.53 | -26.4% | -9.9% |
| held out at three times the costs | +60.5% | 10 | | 8.92 | | |

- **Per session over the held-out six months:** +$100 on average; in the market 59% of sessions; best +$1,768, worst -$2,293; 10th and 90th percentile sessions -$272 and +$658; 4.7% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$47 a session on average.
- **Average trade** +2.59% of the position over 6.5 sessions in the held-out window; +1.29% over 6.9 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +5%  2011 +14%  2012 +42%  2013 +32%  2014 +35%  2015 -8%  2016 +30%  2017 +54%  2018 -8%  2019 +31%  2020 +76%  2021 +28%  2022 +56%  2023 +80%  2024 +67%  2025 +89%  2026 +72%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-09 to 04-23 +8.1%; 04-28 to 05-14 +7.7%; 05-19 to 06-08 -0.9%; 06-11 to 06-16 +7.3%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-06 to 08-07 -0.2%; 08-28 to 09-18 -0.7%.

Files: `03_calm_trend_volume_checked_dips.json` (the genome for `evaluate` and `signals`), `03_calm_trend_volume_checked_dips.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 4. Quieter Trend + Z-Dip

*Calm trend family. Written by Claude in round three, injected into the trend-plus-dip island at generation 15, and scored exactly as written.*

**In words.** A cleaner, quieter version of the leader. Long above the 50-day mean while 20-day volatility is under 22%, after a 1.35-sigma dip above the 200-day, or on a close back over the 50-day. Out when volatility passes 50% or on a close under the 50-day that is not oversold; 4.2% stop, 7% target, 5% trailing stop, 13 sessions, two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma50 and vol20 < 0.22`
- BUY when `zscore20 < -1.35 and close > sma200`
- BUY when `cross_above(close, sma50)`
- SELL when `vol20 > 0.5`
- SELL when `close < sma50 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 5.00% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +57.1% | 9 | 67% | 6.88 | -10.0% | -4.2% |
| last twelve months (six in-sample, six held out) | +48.9% | 18 | 56% | 2.91 | -20.6% | -7.0% |
| training, Jan 2019 to Mar 2026 | +613% | 99 | 65% | 2.03 | -28.2% | -11.5% |
| older history, 2010 to 2018, never used | +297% | 128 | 59% | 1.55 | -27.6% | -9.9% |
| held out at three times the costs | +55.7% | 9 | | 6.55 | | |

- **Per session over the held-out six months:** +$93 on average; in the market 61% of sessions; best +$1,768, worst -$1,061; 10th and 90th percentile sessions -$320 and +$615; 5.5% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$43 a session on average.
- **Average trade** +2.69% of the position over 7.6 sessions in the held-out window; +1.12% over 9.1 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +5%  2011 -1%  2012 +34%  2013 +32%  2014 +35%  2015 -3%  2016 +5%  2017 +54%  2018 +2%  2019 +30%  2020 +59%  2021 +22%  2022 -7%  2023 +70%  2024 +52%  2025 +12%  2026 +67%.
- **Held-out trades:** 04-09 to 04-20 +6.2%; 04-24 to 05-11 +8.5%; 05-14 to 06-04 +3.1%; 06-11 to 06-16 +7.3%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-10 to 08-21 -1.8%; 08-28 to 09-18 -0.7%.

Files: `04_quieter_trend_z_dip.json` (the genome for `evaluate` and `signals`), `04_quieter_trend_z_dip.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 5. Calm Trend, Fast Exit

*Calm trend family. Written by Claude in round three to test a faster trend exit; scored exactly as written.*

**In words.** The core entries (above the 50-day with volatility under 25%, a 1.35-sigma dip above the 200-day, a close back over the 50-day) with a faster exit: it sells the first close under the 20-day mean that is not oversold instead of waiting for the 50-day, or when volatility passes 50%; 4.2% stop, 7% target, 5% trailing stop, 13 sessions, two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma50 and vol20 < 0.25`
- BUY when `zscore20 < -1.35 and close > sma200`
- BUY when `cross_above(close, sma50)`
- SELL when `vol20 > 0.5`
- SELL when `close < sma20 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 5.00% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +51.9% | 11 | 73% | 6.69 | -8.2% | -4.2% |
| last twelve months (six in-sample, six held out) | +32.4% | 23 | 61% | 2.07 | -23.8% | -7.0% |
| training, Jan 2019 to Mar 2026 | +385% | 122 | 56% | 1.51 | -26.9% | -11.5% |
| older history, 2010 to 2018, never used | +306% | 179 | 56% | 1.49 | -30.9% | -9.9% |
| held out at three times the costs | +50.3% | 11 | | 6.35 | | |

- **Per session over the held-out six months:** +$86 on average; in the market 61% of sessions; best +$1,711, worst -$1,061; 10th and 90th percentile sessions -$317 and +$616; 5.5% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$31 a session on average.
- **Average trade** +2.04% of the position over 6.0 sessions in the held-out window; +0.76% over 7.3 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +18%  2011 -19%  2012 +22%  2013 +60%  2014 +51%  2015 -2%  2016 +12%  2017 +47%  2018 -10%  2019 +41%  2020 +108%  2021 +12%  2022 -7%  2023 +54%  2024 +29%  2025 -4%  2026 +59%.
- **Held-out trades:** 04-09 to 04-20 +6.2%; 04-23 to 05-11 +8.2%; 05-14 to 06-04 +3.1%; 06-09 to 06-12 +0.1%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-10 to 08-25 -2.4%; 08-28 to 08-31 -0.3%; 09-04 to 09-09 +0.1%; 09-14 to 09-22 +5.9%.

Files: `05_calm_trend_fast_exit.json` (the genome for `evaluate` and `signals`), `05_calm_trend_fast_exit.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 6. Calm Trend Champion, 6% Target

*Calm trend family. Bred in the trend-plus-dip island: generation 25.*

**In words.** The champion's twin that takes profits sooner: a 6.2% target instead of 7%, no volatility-spike entry, and a 5.3% thrust entry. Everything else as the champion.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret60 <= -0.09 or cross_above(close, sma50)`
- BUY when `vol20 < 0.22 and dist_sma50 > 0.047`
- BUY when `zscore20 < -1.18 and close > sma200 or ret5 > 0.053`
- SELL when `vol20 > 0.45`
- SELL when `close < sma50 and zscore20 > -1`
- SELL when `dist_sma200 < -0.23`
- Risk, checked on the close and filled at the next open: stop 4.23%, target 6.20%, trailing stop 4.90% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +50.1% | 11 | 64% | 3.61 | -10.5% | -9.1% |
| last twelve months (six in-sample, six held out) | +44.4% | 20 | 55% | 2.45 | -18.3% | -9.1% |
| training, Jan 2019 to Mar 2026 | +2025% | 134 | 65% | 3.07 | -18.1% | -11.5% |
| older history, 2010 to 2018, never used | +160% | 126 | 55% | 1.28 | -30.4% | -10.0% |
| held out at three times the costs | +48.6% | 11 | | 3.48 | | |

- **Per session over the held-out six months:** +$85 on average; in the market 57% of sessions; best +$1,768, worst -$2,287; 10th and 90th percentile sessions -$341 and +$615; 5.5% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$41 a session on average.
- **Average trade** +2.01% of the position over 5.5 sessions in the held-out window; +1.26% over 6.9 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +2%  2011 -1%  2012 +46%  2013 +39%  2014 +36%  2015 -19%  2016 +0%  2017 +50%  2018 -23%  2019 +19%  2020 +78%  2021 +47%  2022 +48%  2023 +78%  2024 +12%  2025 +143%  2026 +61%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-09 to 04-20 +6.2%; 04-24 to 05-07 +6.2%; 05-12 to 06-02 +3.9%; 06-05 to 06-08 -5.2%; 06-11 to 06-16 +7.3%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-06 to 08-07 -0.2%; 08-28 to 09-18 -0.7%.

Files: `06_calm_trend_champion_6pct_target.json` (the genome for `evaluate` and `signals`), `06_calm_trend_champion_6pct_target.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 7. Calm Trend + Washout

*Calm trend family. Written by Claude in round three, crossing in the washout entry from the volume-flush island; scored exactly as written.*

**In words.** The calm trend plus a washout. Buys above the 50-day mean with volatility under 25%, after a 1.35-sigma dip above the 200-day, or on RSI(7) under 24 anywhere. Its only sell rule is a close under the 50-day that is not oversold; the 4.2% stop, 7% target, 5.1% trailing stop and 13-session cap do the rest, with a two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma50 and vol20 < 0.25`
- BUY when `zscore20 < -1.35 and close > sma200`
- BUY when `rsi7 < 24`
- SELL when `close < sma50 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 5.10% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +46.0% | 9 | 78% | 9.18 | -12.4% | -6.3% |
| last twelve months (six in-sample, six held out) | +39.2% | 19 | 63% | 2.70 | -20.2% | -7.0% |
| training, Jan 2019 to Mar 2026 | +1498% | 103 | 66% | 2.39 | -25.0% | -9.5% |
| older history, 2010 to 2018, never used | +406% | 134 | 61% | 1.62 | -29.4% | -10.0% |
| held out at three times the costs | +44.8% | 9 | | 8.68 | | |

- **Per session over the held-out six months:** +$80 on average; in the market 69% of sessions; best +$1,711, worst -$1,564; 10th and 90th percentile sessions -$497 and +$834; 10.2% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$37 a session on average.
- **Average trade** +2.23% of the position over 8.7 sessions in the held-out window; +1.50% over 8.8 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +5%  2011 +2%  2012 +40%  2013 +32%  2014 +35%  2015 +1%  2016 +22%  2017 +54%  2018 +1%  2019 +29%  2020 +135%  2021 +19%  2022 +7%  2023 +94%  2024 +39%  2025 +43%  2026 +55%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-09 to 04-20 +6.2%; 04-23 to 05-11 +8.2%; 05-14 to 06-04 +3.1%; 06-09 to 06-30 +0.9%; 07-17 to 07-22 +0.4%; 07-27 to 08-03 +0.2%; 08-12 to 08-21 -1.1%; 08-28 to 09-18 -0.7%.

Files: `07_calm_trend_washout.json` (the genome for `evaluate` and `signals`), `07_calm_trend_washout.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 8. Calm Trend, 10-Session Holds

*Calm trend family. Written by Claude in round three for shorter holds, closer to the quick-trade brief; scored exactly as written.*

**In words.** The core with trades capped at ten sessions instead of thirteen: long above the 50-day mean while volatility is under 25%, after a 1.35-sigma dip above the 200-day, or on a close back over the 50-day; out on a volatility blow-out or a non-oversold break of the 50-day; 4.2% stop, 7% target, 5.1% trailing stop, two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma50 and vol20 < 0.25`
- BUY when `zscore20 < -1.35 and close > sma200`
- BUY when `cross_above(close, sma50)`
- SELL when `vol20 > 0.5`
- SELL when `close < sma50 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 5.10% off the best close, at most 10 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +42.3% | 11 | 64% | 2.57 | -12.4% | -9.7% |
| last twelve months (six in-sample, six held out) | +35.4% | 21 | 52% | 1.74 | -20.1% | -9.7% |
| training, Jan 2019 to Mar 2026 | +445% | 112 | 62% | 1.83 | -28.5% | -11.5% |
| older history, 2010 to 2018, never used | +243% | 146 | 59% | 1.48 | -38.0% | -10.0% |
| held out at three times the costs | +40.8% | 11 | | 2.50 | | |

- **Per session over the held-out six months:** +$74 on average; in the market 61% of sessions; best +$1,768, worst -$2,418; 10th and 90th percentile sessions -$349 and +$596; 6.3% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$34 a session on average.
- **Average trade** +1.79% of the position over 6.1 sessions in the held-out window; +0.85% over 8.1 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 -0%  2011 -15%  2012 +17%  2013 +58%  2014 +14%  2015 -3%  2016 +22%  2017 +72%  2018 -6%  2019 +9%  2020 +51%  2021 +28%  2022 -23%  2023 +81%  2024 +46%  2025 +25%  2026 +35%.
- **Held-out trades:** 04-09 to 04-20 +6.2%; 04-23 to 05-08 +5.5%; 05-13 to 05-29 +4.0%; 06-03 to 06-08 -6.2%; 06-11 to 06-16 +7.3%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-10 to 08-21 -1.8%; 08-28 to 09-15 -1.5%; 09-18 to 09-22 +4.4%.

Files: `08_calm_trend_10_session_holds.json` (the genome for `evaluate` and `signals`), `08_calm_trend_10_session_holds.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 9. Calm Trend + Z-Dip Core

*Calm trend family. Written by Claude in round three: the trend-plus-dip leader reduced to its core; scored exactly as written.*

**In words.** Three entries: above the 50-day mean while 20-day volatility is under 25%, a 1.35-sigma dip below the 20-day mean above the 200-day, a close back over the 50-day. Two exits: volatility over 50%, or a close under the 50-day that is not oversold. 4.2% stop, 7% target, 5.1% trailing stop, 13 sessions, two-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma50 and vol20 < 0.25`
- BUY when `zscore20 < -1.35 and close > sma200`
- BUY when `cross_above(close, sma50)`
- SELL when `vol20 > 0.5`
- SELL when `close < sma50 and zscore20 > -1`
- Risk, checked on the close and filled at the next open: stop 4.20%, target 7.00%, trailing stop 5.10% off the best close, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +38.8% | 9 | 67% | 5.53 | -10.6% | -6.3% |
| last twelve months (six in-sample, six held out) | +31.6% | 18 | 56% | 2.29 | -20.6% | -7.0% |
| training, Jan 2019 to Mar 2026 | +626% | 103 | 61% | 1.89 | -30.7% | -11.5% |
| older history, 2010 to 2018, never used | +318% | 128 | 59% | 1.61 | -27.6% | -9.9% |
| held out at three times the costs | +37.6% | 9 | | 5.24 | | |

- **Per session over the held-out six months:** +$70 on average; in the market 70% of sessions; best +$1,711, worst -$1,564; 10th and 90th percentile sessions -$497 and +$740; 10.2% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$32 a session on average.
- **Average trade** +1.95% of the position over 8.9 sessions in the held-out window; +1.09% over 9.1 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +5%  2011 -1%  2012 +34%  2013 +32%  2014 +35%  2015 -3%  2016 +5%  2017 +54%  2018 +8%  2019 +30%  2020 +90%  2021 +24%  2022 -27%  2023 +99%  2024 +38%  2025 +13%  2026 +47%.
- **Held-out trades:** 04-09 to 04-20 +6.2%; 04-23 to 05-11 +8.2%; 05-14 to 06-04 +3.1%; 06-09 to 06-30 +0.9%; 07-10 to 07-15 -0.5%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-10 to 08-21 -1.8%; 08-28 to 09-18 -0.7%.

Files: `09_calm_trend_z_dip_core.json` (the genome for `evaluate` and `signals`), `09_calm_trend_z_dip_core.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 10. Quiet MACD Trend

*Trend family. Written by Claude as a seed for the second calm-trend island; scored exactly as written.*

**In words.** Long while the MACD histogram is positive, the index is above its 50-day mean and 20-day volatility is under 25%. Out when the histogram turns negative after at least three sessions, or after ten sessions.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `macd_hist > 0 and close > sma50 and vol20 < 0.25`
- SELL when `macd_hist < 0 and bars_held >= 3`
- Risk, checked on the close and filled at the next open: no stop, no target, at most 10 sessions.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +34.7% | 6 | 50% | 6.21 | -8.6% | -3.3% |
| last twelve months (six in-sample, six held out) | +7.5% | 13 | 31% | 1.29 | -21.4% | -7.1% |
| training, Jan 2019 to Mar 2026 | +151% | 81 | 57% | 1.68 | -27.7% | -8.8% |
| older history, 2010 to 2018, never used | +170% | 116 | 53% | 1.62 | -21.0% | -6.4% |
| held out at three times the costs | +34.0% | 6 | | 5.87 | | |

- **Per session over the held-out six months:** +$60 on average; in the market 37% of sessions; best +$1,408, worst -$835; 10th and 90th percentile sessions -$125 and +$425; 1.6% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$9 a session on average.
- **Average trade** +2.69% of the position over 6.8 sessions in the held-out window; +0.64% over 8.0 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +31%  2011 -8%  2012 +17%  2013 +16%  2014 +15%  2015 +1%  2016 +7%  2017 +20%  2018 +11%  2019 +38%  2020 -3%  2021 +15%  2022 +4%  2023 +41%  2024 +22%  2025 +6%  2026 +24%.
- **Held-out trades:** 04-09 to 04-24 +7.8%; 04-27 to 05-12 +7.3%; 05-13 to 05-20 -0.8%; 06-01 to 06-05 -0.0%; 08-12 to 08-25 -1.8%; 09-21 to 09-22 +3.6%.

Files: `10_quiet_macd_trend.json` (the genome for `evaluate` and `signals`), `10_quiet_macd_trend.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 11. Quick Dip, Trend-Assisted

*Quick dip family. Bred in the quick-flush island: generation 24.*

**In words.** One- and two-session trades. It buys a 2% drop above the 200-day mean, a close back over the 50-day, a 5.2% 20-day run while volatility is under 50%, the day after a 1% drop inside a 1.5% five-day dip above the 50-day (or any day more than 15.6% above the 200-day) when the close is not stretched above its 20-day mean, and a close through the upper Bollinger band. It sells after two sessions, on the first 0.5% up day, or on a close 1.8% under the 20-day mean; 3.5% stop.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret1 <= -0.02 and close > sma200 or cross_above(close, sma50)`
- BUY when `mkt_ret20 > 0.052 and mkt_vol20 < 0.5`
- BUY when `(prev(ret1) < -0.01 and ret5 < -0.015 and close > sma50 or dist_sma200 > 0.156) and zscore20 < 0.58`
- BUY when `cross_above(close, bb_upper)`
- SELL when `bars_held >= 2`
- SELL when `ret1 > 0.005`
- SELL when `dist_sma20 < -0.018`
- Risk, checked on the close and filled at the next open: stop 3.50%, no target.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +32.6% | 27 | 74% | 2.18 | -14.6% | -9.7% |
| last twelve months (six in-sample, six held out) | +67.3% | 40 | 80% | 2.90 | -14.6% | -9.7% |
| training, Jan 2019 to Mar 2026 | +442% | 279 | 71% | 1.68 | -24.2% | -11.5% |
| older history, 2010 to 2018, never used | +53% | 252 | 66% | 1.21 | -34.3% | -9.9% |
| held out at three times the costs | +29.2% | 27 | | 2.05 | | |

- **Per session over the held-out six months:** +$59 on average; in the market 56% of sessions; best +$1,898, worst -$2,418; 10th and 90th percentile sessions -$251 and +$537; 3.1% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$53 a session on average.
- **Average trade** +0.56% of the position over 1.6 sessions in the held-out window; +0.33% over 1.8 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 -1%  2011 -28%  2012 +29%  2013 +13%  2014 -14%  2015 +20%  2016 +8%  2017 +19%  2018 +11%  2019 -2%  2020 +111%  2021 +38%  2022 -9%  2023 +32%  2024 -14%  2025 +72%  2026 +42%.
- **Held-out trades:** 04-09 to 04-10 +0.8%; 04-15 to 04-16 +1.4%; 04-17 to 04-20 +0.5%; 04-21 to 04-23 +1.1%; 04-24 to 04-27 +1.5%; 04-28 to 04-30 -0.8%; 05-01 to 05-04 +0.9%; 05-05 to 05-06 +1.7%; 05-07 to 05-11 +2.2%; 05-12 to 05-14 +0.4%; 05-15 to 05-20 -2.6%; 05-21 to 05-27 +2.7%; 05-28 to 05-29 +0.7%; 06-01 to 06-02 +0.4%; 06-03 to 06-08 -6.2%; 06-09 to 06-10 -1.2%; 06-11 to 06-12 +3.5%; 06-24 to 06-25 +1.1%; 06-30 to 07-01 +1.6%; 07-10 to 07-15 -0.5%; 07-30 to 07-31 +4.1%; 08-05 to 08-10 +0.2%; 08-27 to 08-28 +0.4%; 09-04 to 09-10 -0.2%; 09-14 to 09-17 -0.1%; 09-18 to 09-21 +0.7%; 09-22 to 09-22 +0.8%.

Files: `11_quick_dip_trend_assisted.json` (the genome for `evaluate` and `signals`), `11_quick_dip_trend_assisted.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 12. Flush, Washout or Squeeze

*Flush and washout family. Bred in the first quick-trade run: generation 9, a crossover of two leaders.*

**In words.** Buys forced selling and quiet: 1.56 times normal volume near the lower Bollinger band, a volatility squeeze (20-day volatility under 68% of 60-day), an RSI(7) washout under 24, or a 1.2% drop on 1.5 times volume. Sells when RSI(7) recovers past 59, within 1.3% of the 52-week high, or after seven sessions; 3% stop, 3.7% target.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `volume_ratio > 1.56 and bb_pct < 0.2 or vol_ratio_20_60 < 0.68`
- BUY when `rsi7 < 24`
- BUY when `volume_ratio > 1.5 and ret1 < -0.012`
- SELL when `bars_held > 6`
- SELL when `pct_of_52w_high > 0.987`
- SELL when `rsi7 > 59`
- Risk, checked on the close and filled at the next open: stop 3.00%, target 3.70%.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +30.1% | 5 | 80% | 7.45 | -6.0% | -3.8% |
| last twelve months (six in-sample, six held out) | +83.9% | 12 | 92% | 13.70 | -6.0% | -3.8% |
| training, Jan 2019 to Mar 2026 | +788% | 110 | 75% | 3.99 | -19.4% | -10.9% |
| older history, 2010 to 2018, never used | +152% | 190 | 64% | 1.49 | -32.4% | -10.1% |
| held out at three times the costs | +29.5% | 5 | | 7.20 | | |

- **Per session over the held-out six months:** +$54 on average; in the market 21% of sessions; best +$1,898, worst -$958; 10th and 90th percentile sessions +$0 and +$83; 3.9% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$62 a session on average.
- **Average trade** +2.78% of the position over 4.4 sessions in the held-out window; +1.08% over 2.6 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 -1%  2011 -2%  2012 +1%  2013 +28%  2014 +5%  2015 +19%  2016 +44%  2017 +31%  2018 -14%  2019 +4%  2020 +67%  2021 +28%  2022 +36%  2023 +22%  2024 +10%  2025 +100%  2026 +47%.
- **Held-out trades:** 03-30 to 04-02 +4.2%; 06-08 to 06-16 +5.8%; 07-30 to 07-31 +4.1%; 09-01 to 09-14 -1.8%; 09-15 to 09-21 +1.5%.

Files: `12_flush_washout_or_squeeze.json` (the genome for `evaluate` and `signals`), `12_flush_washout_or_squeeze.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 13. Calendar Dips

*Calendar family. Bred in the calendar island: generation 25.*

**In words.** Trades of one or two sessions timed by the calendar. It buys a 1.5% five-day dip after the 10th of the month above the 200-day with the close within 2% of its 20-day mean; a red Friday while less than 50% above the 52-week low; a 1.3% dip between the 13th and the 23rd above the 200-day, or any 14% 20-day run; a MACD bullish cross with RSI(7) under 49, or a close in the top fifth of the Bollinger band. It sells after one session, and sooner in the first five days of a month, on a quiet low-volume day that is not oversold, or on a MACD slide 7.6% under the 200-day; 3% stop, 2.5% target, one-session wait.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `day_of_month >= 11 and ret5 < -0.015 and close > sma200 and dist_sma20 > -0.02`
- BUY when `day_of_week == 4 and ret1 < -0.002 and pct_off_52w_low < 0.5`
- BUY when `day_of_month >= 13 and day_of_month < 24 and ret5 < -0.013 and close > sma200 and dist_sma20 > -0.05 or ret20 > 0.14`
- BUY when `cross_above(macd, macd_signal) and rsi7 < 49 or bb_pct > 0.8`
- SELL when `bars_held >= 1`
- SELL when `macd_hist < -0.4 and dist_sma200 < -0.076`
- SELL when `day_of_month <= 5`
- SELL when `vol_ratio_20_60 < 1.45 and zscore20 > -0.95 and volume_ratio < 1.03`
- Risk, checked on the close and filled at the next open: stop 3.00%, target 2.50%, 1 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +27.6% | 25 | 68% | 2.29 | -8.4% | -6.5% |
| last twelve months (six in-sample, six held out) | +96.2% | 47 | 74% | 3.58 | -8.4% | -6.5% |
| training, Jan 2019 to Mar 2026 | +613% | 303 | 63% | 1.97 | -35.8% | -10.0% |
| older history, 2010 to 2018, never used | +23% | 380 | 62% | 1.08 | -26.5% | -10.0% |
| held out at three times the costs | +24.6% | 25 | | 2.13 | | |

- **Per session over the held-out six months:** +$50 on average; in the market 46% of sessions; best +$1,679, worst -$1,631; 10th and 90th percentile sessions -$93 and +$388; 3.1% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$69 a session on average.
- **Average trade** +0.51% of the position over 1.4 sessions in the held-out window; +0.35% over 1.3 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +0%  2011 -19%  2012 +34%  2013 +11%  2014 +6%  2015 -7%  2016 -1%  2017 +9%  2018 -3%  2019 +10%  2020 +98%  2021 +47%  2022 -22%  2023 +47%  2024 -9%  2025 +91%  2026 +64%.
- **Held-out trades:** 03-30 to 04-01 +3.0%; 04-06 to 04-07 +1.0%; 04-09 to 04-10 +0.8%; 04-14 to 04-15 +1.6%; 04-17 to 04-21 +1.2%; 04-23 to 04-27 +1.2%; 05-01 to 05-04 +0.9%; 05-06 to 05-08 +1.2%; 05-12 to 05-14 +0.4%; 05-18 to 05-20 -0.7%; 05-27 to 05-28 +0.2%; 06-01 to 06-02 +0.4%; 06-04 to 06-05 -0.2%; 06-12 to 06-15 +1.5%; 06-23 to 06-24 -2.9%; 06-29 to 06-30 +2.5%; 07-14 to 07-15 +1.2%; 07-17 to 07-21 -1.4%; 07-23 to 07-27 -2.1%; 08-10 to 08-11 -0.3%; 08-13 to 08-14 +1.3%; 08-21 to 08-24 +0.2%; 08-31 to 09-01 -0.1%; 09-15 to 09-17 -0.8%; 09-21 to 09-22 +2.8%.

Files: `13_calendar_dips.json` (the genome for `evaluate` and `signals`), `13_calendar_dips.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 14. Flush Book

*Flush and washout family. Bred in the volume-flush island: generation 25.*

**In words.** Buys a 1.56-times-volume flush near the lower Bollinger band or a close 12% under the 50-day mean, an RSI(7) washout under 24, a volatility squeeze within 43% of the 52-week low, or a 19% 60-day crash. Sells when RSI(7) recovers past 62, after five sessions, when RSI(14) sinks under 24 (the flush has become a slide), or on a close through the 50-day mean from above the bottom of the band; 4.9% stop, 3.5% target.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `volume_ratio > 1.56 and bb_pct < 0.19 or dist_sma50 < -0.12`
- BUY when `rsi7 < 24`
- BUY when `vol_ratio_20_60 < 0.68 and pct_off_52w_low < 0.43`
- BUY when `ret60 < -0.19`
- SELL when `rsi7 > 62`
- SELL when `bars_held > 4`
- SELL when `rsi14 < 24`
- SELL when `bb_pct > 0.06 and cross_below(close, sma50)`
- Risk, checked on the close and filled at the next open: stop 4.90%, target 3.50%.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +27.3% | 6 | 67% | 8.98 | -2.9% | -2.7% |
| last twelve months (six in-sample, six held out) | +85.0% | 13 | 85% | 18.13 | -2.9% | -2.7% |
| training, Jan 2019 to Mar 2026 | +2444% | 95 | 81% | 9.80 | -11.8% | -10.6% |
| older history, 2010 to 2018, never used | +86% | 156 | 65% | 1.25 | -32.8% | -10.0% |
| held out at three times the costs | +26.5% | 6 | | 8.37 | | |

- **Per session over the held-out six months:** +$49 on average; in the market 17% of sessions; best +$1,898, worst -$671; 10th and 90th percentile sessions +$0 and +$2; 1.6% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$62 a session on average.
- **Average trade** +2.11% of the position over 2.5 sessions in the held-out window; +1.79% over 2.8 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 -1%  2011 +33%  2012 +13%  2013 +23%  2014 +7%  2015 +2%  2016 -7%  2017 +32%  2018 -24%  2019 +9%  2020 +223%  2021 +37%  2022 +87%  2023 +21%  2024 +19%  2025 +84%  2026 +47%.
- **Held-out trades:** 03-30 to 04-02 +4.2%; 07-30 to 07-31 +4.1%; 09-01 to 09-02 -1.3%; 09-03 to 09-11 -0.1%; 09-14 to 09-15 +0.6%; 09-16 to 09-22 +5.2%.

Files: `14_flush_book.json` (the genome for `evaluate` and `signals`), `14_flush_book.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 15. Managed Long

*Trend family. Bred in the second calm-trend island: generation 9, descended from Claude's 'Calm Trend, Managed' seed.*

**In words.** Long almost all the time: the only entry is a day without a volume blow-out, under 2.2 times average, which is nearly every day. The edge is in the exits: out on a close under the 50-day mean that is not oversold (z-score above -0.95), when the 14-day average range passes 4.4% of price, at a 6.4% gain, at a 4.25% loss or after 13 sessions, then back in two sessions later.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `volume_ratio <= 2.2`
- SELL when `close < sma50 and zscore20 > -0.95`
- SELL when `atr_pct > 0.044`
- Risk, checked on the close and filled at the next open: stop 4.25%, target 6.39%, at most 13 sessions, 2 sessions before re-entering.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +26.6% | 16 | 62% | 1.60 | -15.8% | -9.1% |
| last twelve months (six in-sample, six held out) | +60.9% | 27 | 70% | 3.64 | -18.6% | -7.0% |
| training, Jan 2019 to Mar 2026 | +1820% | 187 | 64% | 2.04 | -28.1% | -8.9% |
| older history, 2010 to 2018, never used | +1024% | 215 | 63% | 1.78 | -32.2% | -10.0% |
| held out at three times the costs | +24.6% | 16 | | 1.56 | | |

- **Per session over the held-out six months:** +$53 on average; in the market 76% of sessions; best +$1,768, worst -$2,287; 10th and 90th percentile sessions -$504 and +$730; 10.2% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$52 a session on average.
- **Average trade** +0.90% of the position over 5.1 sessions in the held-out window; +0.90% over 6.4 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +39%  2011 -6%  2012 +29%  2013 +29%  2014 +47%  2015 +32%  2016 +17%  2017 +74%  2018 +33%  2019 +32%  2020 +189%  2021 +47%  2022 +1%  2023 +75%  2024 +48%  2025 +55%  2026 +76%.
- **Held-out trades:** 03-24 to 03-30 -5.0%; 04-02 to 04-03 +0.1%; 04-08 to 04-16 +7.5%; 04-21 to 05-07 +7.0%; 05-12 to 06-02 +3.9%; 06-05 to 06-08 -5.2%; 06-11 to 06-16 +7.3%; 06-19 to 06-29 -4.8%; 07-02 to 07-09 -2.3%; 07-14 to 07-15 +1.2%; 07-20 to 07-22 +1.9%; 07-27 to 08-03 +0.2%; 08-06 to 08-07 -0.2%; 08-12 to 08-21 -1.1%; 08-26 to 08-27 +0.7%; 09-01 to 09-22 +3.2%.

Files: `15_managed_long.json` (the genome for `evaluate` and `signals`), `15_managed_long.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 16. Bull Market, Crash-Day Exit

*Trend family. Written by Claude as a seed for the second calm-trend island, after the first one bred itself into buy-and-hold; scored exactly as written.*

**In words.** Long above the 200-day mean while 20-day volatility is under 30% and the day did not fall 1.5%. It steps out after any 1.5% down day and is back as soon as the conditions hold again; ten sessions at most per trade, no stop.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `close > sma200 and ret1 > -0.015 and vol20 < 0.3`
- SELL when `ret1 < -0.015`
- Risk, checked on the close and filled at the next open: no stop, no target, at most 10 sessions.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +24.2% | 16 | 44% | 1.51 | -27.9% | -9.1% |
| last twelve months (six in-sample, six held out) | -9.2% | 34 | 35% | 0.90 | -29.4% | -9.1% |
| training, Jan 2019 to Mar 2026 | +231% | 151 | 48% | 1.30 | -36.2% | -9.8% |
| older history, 2010 to 2018, never used | +369% | 201 | 51% | 1.40 | -30.9% | -10.0% |
| held out at three times the costs | +22.3% | 16 | | 1.46 | | |

- **Per session over the held-out six months:** +$49 on average; in the market 83% of sessions; best +$1,649, worst -$2,287; 10th and 90th percentile sessions -$539 and +$801; 11.0% of sessions lost more than 2% ($500).
- **Over the last twelve months:** -$4 a session on average.
- **Average trade** +0.84% of the position over 5.6 sessions in the held-out window; +0.50% over 6.9 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +6%  2011 -18%  2012 +13%  2013 +80%  2014 +38%  2015 +22%  2016 +2%  2017 +48%  2018 +4%  2019 +12%  2020 +67%  2021 +13%  2022 -21%  2023 +40%  2024 +43%  2025 +15%  2026 +2%.
- **Held-out trades:** 04-09 to 04-24 +7.8%; 04-27 to 05-12 +7.3%; 05-13 to 05-18 -0.1%; 05-19 to 06-04 +4.6%; 06-05 to 06-08 -5.2%; 06-09 to 06-11 -3.4%; 06-12 to 06-17 +1.9%; 06-18 to 06-24 -1.3%; 07-09 to 07-14 +0.1%; 07-15 to 07-17 -2.1%; 07-21 to 07-24 -0.3%; 07-27 to 07-30 -4.6%; 07-31 to 08-17 +6.5%; 08-18 to 08-19 -1.7%; 08-20 to 09-04 -0.2%; 09-07 to 09-22 +4.0%.

Files: `16_bull_market_crash_day_exit.json` (the genome for `evaluate` and `signals`), `16_bull_market_crash_day_exit.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 17. Quick Dip, Two Legs

*Quick dip family. Written by Claude in round three from the quick-flush leader's dip legs; scored exactly as written.*

**In words.** Buys the day after a 1% drop when the five-day loss is at least 1.9% and the index is above its 50-day mean, or any 2% drop above the 200-day. Out on the first 0.5% up day or after two sessions; 2.6% stop.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `prev(ret1) < -0.01 and ret5 < -0.019 and close > sma50`
- BUY when `ret1 < -0.02 and close > sma200`
- SELL when `bars_held >= 2`
- SELL when `ret1 > 0.005`
- Risk, checked on the close and filled at the next open: stop 2.60%, no target.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +24.0% | 5 | 80% | 94.13 | -1.8% | -1.7% |
| last twelve months (six in-sample, six held out) | +36.3% | 12 | 83% | 8.27 | -4.4% | -2.3% |
| training, Jan 2019 to Mar 2026 | +67% | 76 | 76% | 1.58 | -18.2% | -13.2% |
| older history, 2010 to 2018, never used | +64% | 54 | 76% | 2.06 | -22.3% | -9.6% |
| held out at three times the costs | +23.5% | 5 | | 67.17 | | |

- **Per session over the held-out six months:** +$44 on average; in the market 9% of sessions; best +$1,898, worst -$435; 10th and 90th percentile sessions +$0 and +$0; 0.0% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$32 a session on average.
- **Average trade** +2.22% of the position over 1.2 sessions in the held-out window; +0.38% over 1.8 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +1%  2011 +20%  2012 +15%  2013 +5%  2014 -7%  2015 +12%  2016 +4%  2017 +10%  2018 -6%  2019 -3%  2020 +9%  2021 +42%  2022 -9%  2023 +12%  2024 -8%  2025 +11%  2026 +29%.
- **Held-out trades:** 06-08 to 06-09 +2.0%; 06-11 to 06-12 +3.5%; 06-24 to 06-26 -0.1%; 06-30 to 07-01 +1.6%; 07-30 to 07-31 +4.1%.

Files: `17_quick_dip_two_legs.json` (the genome for `evaluate` and `signals`), `17_quick_dip_two_legs.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 18. Washout or Squeeze, Early Exit

*Flush and washout family. Bred in the first quick-trade run: generation 9, a crossover.*

**In words.** Buys an RSI(7) washout under 24 or any day with 20-day volatility above 57.5% (a crash), a volatility squeeze, or a volume flush at the lower band, and sells early: when RSI(7) is back over 55, or after seven sessions; 3% stop, 3.7% target.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `rsi7 < 24 or vol20 > 0.575`
- BUY when `vol_ratio_20_60 < 0.68`
- BUY when `volume_ratio > 1.56 and bb_pct < 0.19`
- SELL when `bars_held > 6`
- SELL when `rsi7 > 55`
- Risk, checked on the close and filled at the next open: stop 3.00%, target 3.70%.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +23.0% | 5 | 80% | 27.54 | -4.1% | -2.7% |
| last twelve months (six in-sample, six held out) | +69.1% | 12 | 92% | 58.94 | -4.1% | -2.7% |
| training, Jan 2019 to Mar 2026 | +906% | 139 | 71% | 3.74 | -16.7% | -10.6% |
| older history, 2010 to 2018, never used | +269% | 182 | 67% | 1.73 | -25.1% | -10.0% |
| held out at three times the costs | +22.5% | 5 | | 23.78 | | |

- **Per session over the held-out six months:** +$42 on average; in the market 17% of sessions; best +$1,898, worst -$671; 10th and 90th percentile sessions +$0 and +$0; 1.6% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$54 a session on average.
- **Average trade** +2.16% of the position over 3.2 sessions in the held-out window; +0.91% over 2.2 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +19%  2011 +11%  2012 +10%  2013 +17%  2014 +15%  2015 +9%  2016 +28%  2017 +41%  2018 -4%  2019 +7%  2020 +105%  2021 +29%  2022 +36%  2023 +21%  2024 +12%  2025 +90%  2026 +37%.
- **Held-out trades:** 03-30 to 04-02 +4.2%; 07-30 to 07-31 +4.1%; 09-01 to 09-07 +0.0%; 09-09 to 09-18 -0.4%; 09-21 to 09-22 +2.8%.

Files: `18_washout_or_squeeze_early_exit.json` (the genome for `evaluate` and `signals`), `18_washout_or_squeeze_early_exit.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 19. Deep Pullback Book

*Pullback family. Bred in the first swing run: generation 6.*

**In words.** Buys an 8.6% 20-day pullback, a 1.33-sigma dip under the 20-day mean above the 200-day, or a close under yesterday's low above the 50-day. Sells after two sessions, on a MACD bearish cross, or if the index is 22% off its 52-week high; 3.2% stop, 7.3% target.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `ret20 < -0.086`
- BUY when `zscore20 < -1.33 and close > sma200`
- BUY when `close < prev(low) and close > sma50`
- SELL when `bars_held >= 2`
- SELL when `cross_below(macd, macd_signal)`
- SELL when `pct_of_52w_high < 0.78`
- Risk, checked on the close and filled at the next open: stop 3.20%, target 7.30%.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +15.4% | 13 | 46% | 2.13 | -14.8% | -6.3% |
| last twelve months (six in-sample, six held out) | +34.9% | 29 | 59% | 1.95 | -14.8% | -6.7% |
| training, Jan 2019 to Mar 2026 | +1373% | 200 | 58% | 2.84 | -27.1% | -10.9% |
| older history, 2010 to 2018, never used | +47% | 206 | 54% | 1.13 | -31.5% | -10.0% |
| held out at three times the costs | +14.0% | 13 | | 2.00 | | |

- **Per session over the held-out six months:** +$31 on average; in the market 41% of sessions; best +$1,898, worst -$1,585; 10th and 90th percentile sessions -$168 and +$381; 7.1% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$32 a session on average.
- **Average trade** +0.60% of the position over 3.0 sessions in the held-out window; +0.74% over 2.4 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +0%  2011 +19%  2012 +2%  2013 +28%  2014 -5%  2015 +12%  2016 -13%  2017 +17%  2018 -12%  2019 +7%  2020 +39%  2021 +31%  2022 +26%  2023 +100%  2024 +19%  2025 +142%  2026 +29%.
- **Held-out trades:** 04-29 to 05-04 +2.5%; 05-13 to 05-18 -0.1%; 06-08 to 06-11 -1.4%; 06-18 to 06-24 -1.3%; 06-25 to 06-30 -0.3%; 07-03 to 07-09 -0.5%; 07-17 to 07-22 +0.4%; 07-24 to 07-29 -2.6%; 07-30 to 08-04 +6.3%; 08-12 to 08-17 +1.7%; 08-19 to 08-24 -0.6%; 09-02 to 09-07 +1.3%; 09-16 to 09-21 +2.3%.

Files: `19_deep_pullback_book.json` (the genome for `evaluate` and `signals`), `19_deep_pullback_book.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

### 20. Pullback Book, Clean

*Pullback family. Written by Claude in round three as the pullback leader without its junk clauses; scored exactly as written.*

**In words.** Buys a 1.67-sigma dip above the 200-day, an 8.6% 20-day pullback, or a close under yesterday's low above the 50-day. Out after two sessions, on a MACD bearish cross, or 15% off the high; 4.2% target and no stop.

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

- BUY when `zscore20 <= -1.67 and close > sma200`
- BUY when `ret20 < -0.086`
- BUY when `close < prev(low) and close > sma50`
- SELL when `bars_held >= 2`
- SELL when `cross_below(macd, macd_signal)`
- SELL when `pct_of_52w_high < 0.85`
- Risk, checked on the close and filled at the next open: no stop, target 4.20%.
- Size: all of the account's 2x buying power on every entry, one position.

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | +11.5% | 12 | 42% | 1.84 | -13.4% | -6.3% |
| last twelve months (six in-sample, six held out) | +35.8% | 26 | 58% | 2.17 | -13.4% | -6.3% |
| training, Jan 2019 to Mar 2026 | +911% | 198 | 59% | 2.75 | -35.8% | -10.9% |
| older history, 2010 to 2018, never used | +110% | 194 | 55% | 1.27 | -23.9% | -10.0% |
| held out at three times the costs | +10.2% | 12 | | 1.73 | | |

- **Per session over the held-out six months:** +$24 on average; in the market 37% of sessions; best +$1,898, worst -$1,585; 10th and 90th percentile sessions -$168 and +$302; 6.3% of sessions lost more than 2% ($500).
- **Over the last twelve months:** +$33 a session on average.
- **Average trade** +0.50% of the position over 2.9 sessions in the held-out window; +0.65% over 2.2 sessions in training.
- **Year by year at 2x, 2010 to 2026:** 2010 +0%  2011 +27%  2012 +14%  2013 +25%  2014 -2%  2015 +32%  2016 -22%  2017 +18%  2018 -2%  2019 +26%  2020 +44%  2021 +41%  2022 -3%  2023 +85%  2024 +11%  2025 +136%  2026 +19%.
- **Held-out trades:** 04-29 to 05-04 +2.5%; 05-13 to 05-18 -0.1%; 06-08 to 06-11 -1.4%; 06-18 to 06-24 -1.3%; 06-25 to 06-30 -0.3%; 07-03 to 07-09 -0.5%; 07-20 to 07-23 +1.2%; 07-24 to 07-29 -2.6%; 07-30 to 08-03 +5.0%; 08-12 to 08-17 +1.7%; 08-19 to 08-24 -0.6%; 09-16 to 09-21 +2.3%.

Files: `20_pullback_book_clean.json` (the genome for `evaluate` and `signals`), `20_pullback_book_clean.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).

## How they were bred

evotrader's loop backtests a population of agents on the training window,
keeps the best, and breeds the next generation from them. There is no API key
in this environment, so mutation and crossover bred each generation, and
Claude, in this session, did the breeding the loop normally asks Claude for,
by hand, at three points.

| round | what happened | runs | generations |
|---|---|---|---|
| 1 | Two runs seeded with the `nq_2x` style's twenty archetypes (index-sized dips, trends, calendar effects, breakouts): quick holds of about three sessions, and swing holds of about eight | 2 | 24 |
| 2 | Eight islands, each started by Claude from one family (47 genomes: deep pullbacks, volume flushes, calm trends, calendar, momentum, trend plus dip, quick flushes, price patterns) and bred 15 generations | 8 | 120 |
| 3 | Claude read the island leaderboards, training numbers only, and wrote 19 children: ten iterations of the trend-plus-dip leader with its clutter removed, and cleaned-up flush, pullback, calendar and quick-dip books. They were injected into five islands (`evotrader inject`), which were bred 12 more generations. A second calm-trend island started from six structured seeds after the first bred itself into buy-and-hold with a 49% drawdown | 6 | 75 |

That is 11 runs, 219 generations, and 13,620 backtests of about 9,100
distinct agents. Every agent traded at the full 2x, because the `nq_2x` style
fixes the size. Training covered January 2019 to 20 March 2026, with the
fitness weighting the most recent six or twelve training months at 60% to 70%.
Costs were 0.2 bp commission and 1 bp slippage a side, about $15 per MNQ round
trip, several times the real cost.

Then the gauntlet (`strategies/nq2x/gauntlet.py`) scored 179 candidates on
four windows: the top distinct behaviours of every run plus every
hand-written child.

- 153 made money on both the held-out six months and the training window.
- 140 of those also had a profit factor of at least 1.2 held out and 1.1 in
  training; they reduce to 46 distinct behaviours.
- 23, with a cap per family, also made money over 2010 to 2018, survived
  three times the costs, and kept their training drawdown under 40%.

The twenty here drop seven of those 23 as near-duplicates, the same rules
with slightly different thresholds. They add four that cleared every tier but
were over their family's cap. Eleven of the twenty were bred by the evolution.
Nine were written by Claude and scored exactly as written.

Finally the rules were simplified (`strategies/nq2x/simplify.py`). Clauses,
whole rules and risk settings were removed and thresholds rounded one at a
time, and a change was kept only if every trade from bar 260 on, in all three
windows, stayed the same. Every number on this page comes from re-running the
simplified rules.

## Tighter stops: what a 9-point stop does

A stop sized for a daily loss budget, for example 9 points so that three or
four losses fit inside a $1,000 drawdown, was tested on all twenty strategies
as a resting stop order that fills inside the bar, the way a real stop
fills (`strategies/nq2x/stop_study.py`, results in
`reports/stop_study.json`).

Nine points is 0.03% of NQ at 31,000. Over the last six months NQ's median
session range was 514 points, and it traded at least 9 points below the open
on 94% of sessions. With a 9-point stop, 80% to 100% of trades are stopped
out on the day they are entered.

| stop, resting order | profitable in the last six months | profitable on all three windows | median $ per session, last six months | loss per stop-out at 1 MNQ |
|---|---|---|---|---|
| each strategy's own stop, on the close (as published) | 20 of 20 | 20 of 20 | +$60 | $2,600 at the champion's 4.2% |
| 9 points | 12 of 20 | 0 of 20 | +$15 | $18 |
| 25 points | 17 of 20 | 0 of 20 | +$17 | $50 |
| 50 points | 20 of 20 | 12 of 20 | +$30 | $100 |
| 100 points | 19 of 20 | 9 of 20 | +$31 | $200 |
| 150 points | 19 of 20 | 11 of 20 | +$24 | $300 |
| 250 points | 20 of 20 | 15 of 20 | +$51 | $500 |
| 400 points | 20 of 20 | 18 of 20 | +$51 | $800 |

At 9 points the median strategy lost 7% over 2019-2026 and 5% over
2010-2018. The twelve that stayed positive over the last six months did so
because a strong rally carried the few trades that survived the stop. These
are daily-bar strategies that hold one to thirteen sessions; they need room
of a few hundred points. A stop of 100 to 150 points ($200 to $300 a loss on
one MNQ, three to five losses inside $1,000) keeps 9 to 11 of them profitable
on every window, led by Quiet MACD Trend (+$57 a session at 2x with a
100-point stop), Calm Trend, Volume-Checked Dips (+$53), Managed Long (+$45)
and Calendar Dips (+$43). A true 9-point stop belongs to intraday trading,
several trades a day on one- to five-minute bars, which is a different system.

## The data

- NQ1! from TradingView, daily bars since 1999. Each quarterly roll is
  back-adjusted by ratio. The roll gap, about 1% a quarter at recent rates, is
  carry, not profit, and an unadjusted continuous contract books it as a gain.
  Bars are labelled by trading date: a session that opens Sunday 18:00 New
  York is Monday's bar. Checked against the NDX index, daily returns correlate
  0.99. On roll days the adjusted series matches the index, where the raw
  contract shows a phantom +1%.
- Decisions on the daily settlement, fills at the next open (the 18:00
  reopen). Stops and targets are checked on the close, so a gap through a stop
  fills worse than the stop, as it would live.
- 2x: a 1.0 weight holds twice equity in notional, with no financing charge,
  because futures carry is already in the price.

## What the numbers cannot tell you

- Six months is short. The held-out window holds 5 to 27 trades per
  strategy; the training window (76 to 303 trades) and the older window carry
  the statistical weight.
- The ranking is by one regime: a strong, orderly rally. A choppy or falling
  half year reorders it. The last-twelve-months line in each strategy shows
  what that looked like most recently.
- At 2x every strategy has lost 9% to 13% of the account in a single day
  somewhere in its training window, about $2,200 to $3,300 on $25,000. For
  eleven of them that day was 13 September 2022, when NQ fell more than 5% on a
  hot inflation report; for most of the rest it came in the February-March
  2020 crash.

## Reproduce

```bash
# the four windows for every strategy (the numbers on this page)
python strategies/nq2x/gauntlet.py profitable-strategies/nq-2x/all.json
# year by year and the daily profile, 2010-2026, at 2x on $25,000
python -m evotrader.cli evaluate profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --start 2010-01-01 --test-frac 0 --by-year --daily
# buys for the next open, after 17:00 New York
python -m evotrader.cli signals profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --refresh
# the forward test: every session after the freeze
python -m evotrader.cli evaluate profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --test-frac 0 --since 2026-09-23 --refresh
# breed again: an island, Claude's children injected, more generations
python -m evotrader.cli run --config configs/nq_islands/trend_plus_dip.json
python -m evotrader.cli inject RUN_ID strategies/nq2x/children/r3_trend_plus_dip.json
python -m evotrader.cli resume RUN_ID --generations 12
```

The breeding scripts are `strategies/nq2x/run_islands.sh` and
`strategies/nq2x/round3.sh`; the seeds and children are in
`strategies/nq2x/seeds` and `strategies/nq2x/children`; `final_spec.json`
holds the twenty as published, with their origins.
