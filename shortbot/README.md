# shortbot: an MNQ day-trading bot for Topstep

The bot trades MNQ within the Topstep Combine rules (see
`docs/prop-firm-accounts.md`), taking at most a few trades a day. Three of
its setups only sell short. A fourth, `basic`, trades both ways.

> **Status: not ready for money.** Nothing here has beaten random trading
> clearly enough to call it an edge (see *Is it better than luck?* below).
> Use it in dry run or on the free Topstep Practice account.

## What it looks for

The bot checks three short setups at the close of every 5-minute bar,
between 09:45 and 15:00 New York time:

| Setup | Fires when | Why |
|---|---|---|
| `momentum` | The last 60 minutes fell 1.5× the normal range for that hour, and price is under VWAP | Research found big hourly drops in NQ tended to keep falling |
| `orb` | The first close below the 15-minute opening range, before 11:00, while under VWAP | Most of the day's sharpest selloff candles come in the first hour |
| `vwap_reject` | On a day trading below its open, a bar rallies up to VWAP, fails, and closes red below it | A classic short on down days |

**Exits.** Stops and targets are measured in *units*: one unit is the normal
30-minute range at that time of day.
- Stop: 1 unit against the entry, rounded to a whole tick away from it.
- Target: 1.5 units in the trade's favour, rounded to the nearest tick.
- Time limit: 90 minutes.
- Everything is flat by 15:50.
- On Fed announcement days, trades opened before 13:55 are closed by 13:55.
  There are no new entries from 13:25 to 14:45, and trading resumes after.

**Sizing.** About $250 of risk per trade, 1–3 MNQ.

**Daily limits.**
- At most 3 trades, or 2 losing trades.
- Stop for the day at −$600, before Topstep's $1,000 daily loss limit.
- Stop for the day at +$1,200, which keeps days inside Topstep's 55% best-day
  rule.

Every number is a setting. `python -m shortbot init-config bot.json` writes
them all to a file you can edit.

## Results (re-run 2026-09-25 after the bug fixes)

**How these numbers were made:**
- **Fills:** one tick worse than the quoted price, with $1.22 commission per
  round trip. Within a bar, the stop is assumed to fill before the target.
- **Data removed:** the week of each quarterly expiry (Yahoo's NQ=F mixes
  two contracts then), plus broken days and today's unfinished session.
  Every backtest prints what it dropped.
- **Coin flips:** "Beats coin flips" ranks the trading P&L against 200 random
  bots with the same trade count, long/short mix, stops, sizing and limits.
- **Whole plan:** "Whole plan" follows Topstep from the first day of the
  data: buy, reset until it passes, trade the funded account until it is
  blown, repeat. Every fee is counted.

**Two years of hourly NQ** (May 2024 – Sep 2026, 545 sessions):

| Preset | Trades | Trading P&L (first 60% / last 40%) | Beats coin flips | Combines passed | Whole plan |
|---|---|---|---|---|---|
| Default: 3 short setups, ~$250 a trade | 251 | −$2,181 (−$2,529 / +$348) | 29% | 0% | −$1,602, no payouts |
| Big-drop short, 50K, ~$1,000 | 63 | +$2,633 (−$596 / +$3,228) | 73% | 29% | −$1,753, no payouts |
| Big-drop short, 100K, ~$1,500 | 63 | +$2,448 (−$1,489 / +$3,937) | 65% | 23% | −$3,101, no payouts |
| Basic follow, ~$1,000 | 251 | −$7,495 (−$8,442 / +$947) | 32% | 19% | +$3,314, 4 payouts |
| Basic fade, ~$1,000 | 255 | **+$8,389 (+$2,991 / +$5,398)** | **84%** | 30% | +$2,466, 4 payouts |

**The last 44 sessions on 5-minute bars** (Jul–Sep 2026; MNQ +7.5%):

| Preset | Trades | Trading P&L | Beats coin flips |
|---|---|---|---|
| Default: 3 short setups | 41 | −$1,861 | 14% |
| Big-drop short, 50K | 6 | −$2,108 | 15% |
| Basic follow | 48 | −$5,881 | 12% |
| Basic fade | 47 | **+$4,887** (+$5,770 / −$883) | **90%** |

**What this says:**
- **Nothing clears the bar.** The bar for an edge is beating about 95% of
  coin flips, in more than one period.
- **Basic fade is now the best lead** on both data sets. That means buying a
  big red run and shorting a big green run, after 10:00. On the 5-minute
  data, though, almost all of its profit came in the first 60%.
- **Big-drop short** is positive on the hourly data, but only in the last 11
  months. Following the Topstep plan with it since May 2024 never produced
  a payout.
- **The hourly test is a coarse stand-in for the 5-minute bot.** On 60-minute
  bars the 30-minute unit becomes 60 minutes, the 15-minute run becomes one
  hourly candle, and the 90-minute hold becomes 120. The backtest prints a
  warning when this happens.
- **Whole-plan results are mostly luck:** basic follow lost $7,495 trading
  yet netted +$3,314 on the plan. Judge ideas on trading P&L against coin
  flips.
- **A "only short in a downtrend" filter** made results worse, so it is off
  by default.

The next real step is several years of 5-minute MNQ data. Pass any CSV with
`--data`.

## Big-drop mode: one big short, only when the drop comes

`configs/shortbot-bigdrop.json` switches the bot to one setup and one trade a
day:
- only the `momentum` setup ("the last hour fell 1.5× its normal range");
- at most one trade a day;
- about $1,000 of risk, around half the Combine's $2,000 max loss;
- target 2.5 units in its favour, exit within 90 minutes.

`configs/shortbot-bigdrop-100k.json` is the same at about $1,500 a trade on
the 100K Combine.

**How big should the one trade be?** Two years of hourly NQ, big-drop only:

| Risk per trade | Trading P&L | Worst trade | 50K Combines passed | Whole plan |
|---|---|---|---|---|
| ~$250 | −$473 | −$234 | none finished (too slow) | −$1,651 |
| ~$500 | +$903 | −$484 | 0% | −$1,553 |
| **~$1,000 (preset)** | +$2,633 | −$994 | **29%**, median 49 days | −$1,753 |
| ~$2,000 | +$5,294 | −$1,998 | 11% | −$2,000 |
| All-in, 50 MNQ | +$68,257 on paper | −$17,511 | 4% | −$1,702 |
| 100K, ~$1,500 | +$2,448 | −$1,508 | 23% | −$3,101 |

**Safety check:** the live bot refuses to trade settings where a single
stop-out could use up the account's whole max loss, unless you pass
`--allow-account-risk`.

## Basic mode: react to the candles, both ways

`configs/shortbot-basic.json` turns off the short setups and uses only
`basic`. The rule: when the last 15 minutes are all green candles, or all
red, and the move is at least the normal size for that time of day, trade
it. It takes at most 3 trades a day, with about $1,000 of risk each.

- `basic_mode: "follow"`: buy after green, short after red. This is the
  preset.
- `basic_mode: "fade"`: buy the red dip, short the green rip.

```bash
python -m shortbot vs-random --data yahoo --config configs/shortbot-basic.json
```

## What was wrong before (fixed 2026-09-25)

Two independent reviews and a second, separately written implementation of
the fill and Topstep rules (`tests/test_shortbot_reference.py`) found the
problems below. The core fill engine and the Topstep Combine and Express
Funded rules were confirmed correct.

**Data**
- Yahoo's NQ=F mixed the December and March contracts on
  2025-12-16/17, and switched contracts inside a bar on 2026-09-14. Expiry
  weeks are now dropped.
- A mid-session refresh could include today's unfinished session. It is now
  dropped.

**Hourly tests**
- The 09:00 hourly bar includes pre-market trading, and it was allowed to
  trigger trades the live bot could never take.
  - Its 82 fade trades lost $9,362; removing them flips fade from −$10,328
    to +$8,389.
  - Follow's 09:00 trades made $3,266.
- Fed-day positions were closed at 14:00, not before.

**Strategy rules**
- Fed-day trading never resumed after 14:45.

**Fees**
- Reset credits were overcounted, which understated fees.

**Random benchmark**
- It traded both directions against short-only presets.

**Earlier figures replaced by this version**
- Big-drop +$4,058 (now +$2,633).
- Basic fade −$13,736 (now +$8,389).
- Basic follow −$873 (now −$7,495).
- The 50K big-drop plan "+$116 with one payout" (now −$1,753 with none).
- "MNQ rose 13%" (it rose 7.5%).

**Live bot**
- 12 safety bugs, including network errors that could leave a position
  without a stop and keep adding contracts. All are fixed, each with a
  failure test (`tests/test_shortbot_live_failures.py`).

## Commands

```bash
python -m shortbot backtest                      # 60 days of 5-minute NQ from Yahoo
python -m shortbot backtest --trades             # ...and list every trade
python -m shortbot backtest --data yahoo-hourly  # two years, hourly (coarse)
python -m shortbot backtest --data mnq_5m.csv    # your own timestamp,open,high,low,close,volume file
python -m shortbot backtest --setups momentum    # test one setup alone
python -m shortbot sweep --data yahoo-hourly     # tune on the first 60%, judge on the last 40%
python -m shortbot vs-random --data yahoo-hourly  # rank the strategy against coin-flip bots
python -m shortbot init-config bot.json          # then: --config bot.json on any command
```

## Running it against TopstepX

**Before you start:**
- Run it on your own computer. Topstep prohibits a VPS, a VPN or a remote
  server for order flow.
- The API is allowed on the Practice, Combine and Express Funded accounts.
  It is not allowed on a Live Funded account.

**Steps:**

1. **Get API access.**
   - Subscribe at dashboard.projectx.com. It costs $29/mo, or $14.50/mo with
     code `topstep`.
   - In TopstepX, go to **Settings > API**: link ProjectX, then create an API
     key.
2. **Set your credentials.**
   ```bash
   export TOPSTEPX_USERNAME=your_topstepx_username   # not your email
   export TOPSTEPX_API_KEY=your_key
   ```
3. **Dry run first.** It uses real prices and places no orders:
   ```bash
   python -m shortbot live
   ```
   It lists your accounts, then logs every `SHORT` and `COVER` it *would* do.
   Logs go to `runs/shortbot-live.log`, and each trade is written to
   `runs/shortbot-trades.csv`. Let it run for a few weeks, then compare its
   trades with `backtest` over the same days.
4. **Then the Practice account.**
   ```bash
   python -m shortbot live --live --account-id <practice account id>
   ```
   - The bot refuses any account that is not simulated.
   - Watch the first trades in TopstepX. Check that the stop order sits
     *above* your short entry and that position sizes are right.

### Safety features

- **Stop straight away.** Every entry gets a protective stop the moment the
  position shows the ordered size.
- **Failed entries.** If any step of an entry fails (an error, a timeout, a
  wrong size), every MNQ order is cancelled, every MNQ position is closed,
  and the bot takes no more entries that day.
- **Checked closes.** The bot cancels the stop, closes the position, then
  checks the account is flat with no orders left. If the close fails, the
  stop is put back before the error is reported.
- **Stop-outs.** A stop-out is only accepted when two reads a second apart
  both show the position gone.
- **Exits without a price.** The flatten and time exits still happen when no
  price can be fetched, and a position is never forgotten outside trading
  hours or overnight.
- **Account check before each trade.** Before every new trade the bot checks
  the account is really flat. Anything unexpected is closed, and it stops
  for the day.
- **Clean start.** On start-up, MNQ orders and positions in any contract
  month are cleaned up.
- **Simulated accounts only.** It refuses any account not explicitly marked
  simulated.
- **Stopping it.** Create a file named `STOP` in the working folder, or press
  Ctrl-C. Either one flattens and exits, retrying and saying loudly if it
  cannot confirm the account is flat.
- **No late entries.** It never acts on a bar that closed more than 60
  seconds ago.

### Check during the dry run (not confirmed from the docs)

- **Bar timestamps.** They are assumed to be bar *start* times. Compare a
  few against the TopstepX chart.
- **Contract rolls.** After a roll, the first days of the new contract may
  have thin history, so the "normal range" can be off for a few days.

## Layout

```
shortbot/
  config.py     every setting, plus Fed announcement dates
  data.py       bars -> New York sessions (Yahoo, CSV, or TopstepX)
  strategy.py   the setups (+ the coin-flip benchmark); decide() is shared by backtest and live
  backtest.py   fills, trade records, Topstep Combine replay, stats
  topstepx.py   TopstepX / ProjectX REST client (standard library only)
  live.py       paper and real brokers, the live loop, safety switches
  cli.py        command line
```

Tests: `python -m pytest tests -k shortbot`.
They cover:
- short profit and loss, fills, and the stop-before-target rule;
- that no decision uses a future bar;
- the Topstep loss limits and consistency rule;
- the API client and order flow against a fake exchange;
- that a day replayed through the live loop takes the same entries, at the
  same prices, as the backtest.
