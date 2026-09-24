# Opening Dip Scalper

**Superseded by the [Own-Drop Scalper](../own-drop/README.md).** This first
version was found on 17 names and did not carry over: on 30 fresh names it
made about $10 a day (+1.5 bp a trade). The own-drop version adds one
condition, that the name falls while the other names do not, and kept both
groups of names profitable. Its paper trail replaced this one before a
session was recorded here. Kept for the record.

One bot. Trades last four minutes, and nothing is ever held past the close:
every trade is over by 09:50 New York. Found 2026-09-23 on one month of
one-minute data. Backtests and paper trading, not advice.

## What it does

It watches 17 liquid, fast-moving names: SOXL, SOXS, MUU, NVDL, SMCI, MSTR,
COIN, MRVL, MU, ARM, PLTR, AMD, META, TSLA, AVGO, NVDA and TQQQ.

- **Buy** when a name's one-minute return, on any bar from 09:35 to 09:45,
  falls more than 0.75 of its 14-minute average range (ATR as a share of
  price). The buy fills at the next minute's open.
- **Sell** at the open four minutes after the buy.
- **At most two positions** at a time, each 62.5% of a $25,000 account: 1.25x
  buying power, which a margin account's day-trading power allows.
- **Never past the close:** a hard exit at 15:55. In practice every position
  is closed by 09:50.

The edge is the snap back after a sharp drop in the opening minutes, when
the tape overshoots. Later in the day the same trade stops working.

## Results

On $25,000 with 1.25x buying power, 21 sessions (2026-08-25 to 2026-09-23):
**$149 a day on average and $121 on a typical day. 86% of days made money,
and the worst day lost $121 (0.5%).** It made about five trades a day, each
held four minutes, and 64% of trades won.

| Check | Result |
| --- | --- |
| Chosen on the first 14 sessions, tested on the last 7 (at 1x) | $124 a day on the first 14, 86% up. $87 a day on the last 7, 71% up |
| Each week on its own (at 1x) | $91, $121 and $87 a day, with 86%, 71% and 71% of days up |
| Costs of a cent plus 1 bp each way, doubled / tripled (at 1x) | $98 / $77 a day, 81% / 71% of days up |
| Filled a full minute late (at 1x) | $92, $156 and $96 a day over the three weeks |
| The same bot on TradingView's single-exchange bars (at 1x) | $93 a day, 47% of days up (Yahoo's fuller bars: $119, 82%) |
| Names | 11 of the 16 it traded made money: MRVL, SOXS, AMD, MUU and MU the most |
| Buying power 1x / 1.25x / 1.5x | $119 / $149 / $179 a day; worst day -0.4% / -0.5% / -0.6% |

How it was found: an event study (`strategies/scalp/events.py`) measured the
net result of one-to-four-minute trades after about 250 setups across the 17
names. Only buying sharp drops in the opening minutes kept its edge in both
halves of the data; chasing moves lost 12-20 bp a trade in the second half.
The engine then tested the dip-buyer as one bot (`bot.py`) with one to four
positions at a time.

## Read this before trusting it

- **One month is short.** Twenty-one sessions in one regime, a strong,
  volatile semiconductor rally. The paper trail from 2026-09-24 is the real
  test, on sessions no choice has seen.
- **The opening minutes are the hardest to fill.** Spreads are wider then than
  the one-cent cost here assumes. Doubling and tripling the costs still left
  $98 and $77 a day, and a full minute's delay still made money.
- **Data feeds disagree at the open.** Yahoo's one-minute bars carry
  consolidated volume; TradingView's free bars come from one exchange and gave
  a noisier result (see the table above).
- **Execution has to be fast:** a market order within seconds of the minute's
  close, and the sale four minutes later.

## Running it

- `opening_dip.pine`: TradingView Pine v6 for a one-minute chart of each name,
  with alerts ("alert() function calls only"). Take at most two signals at
  once.
- `paper.json` and `paper/<date>.md`: the paper trail, replayed each evening
  from that day's one-minute bars (`python strategies/scalp/replay.py`).
- `strategies/scalp/`: the event study, the bot tests and the replay.
