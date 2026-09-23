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
