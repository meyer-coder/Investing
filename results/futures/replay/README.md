# Replaying 36-221 and 21-155 by hand (FX Replay, TradingView bar replay)

`36-221_trades.csv` and `21-155_trades.csv` list every trade the backtest took,
26 Sep 2018 → 25 Sep 2026. Regenerate them, or export any other strategy, with

```bash
python -m confluence.cli futures-trades 36-221 21-155 --risk 500
```

| column | meaning |
|---|---|
| `date` | trading day of the entry (New York) |
| `signal_bar_close` | New York time the signal bar closed; the setup is complete on this bar |
| `entry_time`, `entry` | fill time and price |
| `stop`, `risk_points` | initial stop and its distance in NQ points (MNQ = $2 a point, NQ = $20) |
| `exit_time`, `exit`, `exit_reason` | stop, trailing stop or session exit |
| `net_r` | result in R after commission and 2 ticks of slippage |
| `worst_open_r` | the worst open loss during the trade, in R |
| `usd_at_risk` | `net_r` in dollars when $500 is risked per trade |

## Setting up FX Replay

* Symbol: **NQ** (Nasdaq-100 futures). Chart timezone: **New York**.
* 36-221 on the **15-minute** chart, 21-155 on the **60-minute** chart.
* Indicators: ATR(14). For 36-221 also a 100-period SMA of ATR(14).
* **Prices:** the backtest used the Dukascopy Nasdaq-100 CFD, which moves with NQ
  (5-minute return correlation 0.99) but sits about 0.2–0.5% below the future. At
  30,000 that is roughly 100 points, and the gap changes at each quarterly roll.
  Match trades by **time** and by `risk_points`, not by price. On any day, the
  difference between one FX Replay bar and the CSV gives that day's offset.
* 553 and 2,890 trades is a lot to replay by hand. The last 6 months hold 40
  (36-221) and 179 (21-155) trades, and that window weighs most in the ranking.
  A random 50 from the rest is enough to check the rules.

## 36-221 Swing Support Engulf + ATR calm · NQ 15m

Long rules. Shorts mirror every rule: swing highs, bearish engulfing, sell-stop.

1. **Swing lows.** A low counts as a swing low once price has rallied 3 × ATR(14)
   from it. Keep the last four confirmed swing lows.
2. **Location.** The signal bar's low comes within 0.25 × ATR of one of those
   swing lows, and the bar closes above that level.
3. **Trigger.** A bullish engulfing bar: the previous bar is red, this bar is
   green, it opens at or below the previous close and closes at or above the
   previous open.
4. **Filter.** ATR(14) is below its 100-bar average (quiet market).
5. **Session.** The signal bar closes between 02:00 and 11:30 New York. At most
   4 trades a day.
6. **Entry.** A buy-stop 1 tick above the signal bar's high, valid for the next
   3 bars.
7. **Stop.** 1.5 × ATR(14) below the entry price.
8. **Exit.** No target. Hold until 16:00 New York unless stopped out.

Expect about 1.3 trades a week and a 17% win rate. The average winner is about
6 times the average loser. The worst losing run was 39 trades.

## 21-155 Inverse FVG Retest + strong close · NQ 60m

Long rules. Shorts mirror every rule, using a bullish gap that price closed below.

1. **Bearish gap.** Within the last 20 bars a bearish fair-value gap formed: a
   bar's high sits below the low of the bar two before it by at least 0.1 × ATR.
   The gap runs from that high (bottom) up to that low (top).
2. **Inversion.** Within the last 10 bars, price closed above the gap's top.
3. **Retest.** The signal bar trades down to the gap's top (low at or below it)
   and closes above it.
4. **Trigger.** The signal bar is green and closes above the previous bar's high.
5. **Filter.** The signal bar closes in the top 30% of its range.
6. **Session.** The signal bar closes between 18:05 and 15:30 New York. At most
   4 trades a day.
7. **Entry.** Market order at the next bar's open.
8. **Stop.** 1.0 × ATR(14) from entry.
9. **Exit.** Once the trade is +1R, trail the stop 2 × ATR(14) behind the best
   price, updated at each bar close. Flat at 16:05 New York.

Expect about 7 trades a week and a 33% win rate. About half the weeks are green.
The worst losing run was 20 trades.

## Both

* A stop is never tighter than 0.3 × ATR or 4 × the round-trip cost (4.4 NQ
  points). This rarely matters on these timeframes.
* Prop firms require you to be flat by 3:10 PM Chicago (4:10 PM New York);
  both exits are before that.
