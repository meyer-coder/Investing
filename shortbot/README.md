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
- Stop: 1 unit above the entry.
- Target: 1.5 units below the entry.
- Time limit: 90 minutes.
- Everything is flat by 15:50, and flat before 2 PM on Fed announcement days.

**Sizing.** About $250 of risk per trade, 1–3 MNQ.

**Daily limits.**
- At most 3 trades, or 2 losing trades.
- Stop for the day at −$600, before Topstep's $1,000 daily loss limit.
- Stop for the day at +$1,200, which keeps days inside Topstep's 55% best-day
  rule.

Every number is a setting. `python -m shortbot init-config bot.json` writes
them all to a file you can edit.

## Results so far (2026-09-25)

Fills were modelled one tick worse than the quoted price, with $1.22
commission per round trip. Within a bar, the stop is assumed to fill before
the target.

| Data | Trades | Net | Topstep 50K Combine |
|---|---|---|---|
| 5-minute NQ, 39 sessions (Jul–Sep 2026) | 45 (1.2/day) | **−$1,507** | 0 passed, 15 failed |
| Hourly NQ, 577 sessions (May 2024 – Sep 2026) | 272 (0.5/day) | +$234 (about break-even) | 33% passed; median 178 days to pass |

- On the two hourly years, `momentum` was the only setup with a positive
  total (+$1,112). It lost $1,030 in the first 17 months and made $2,141 in
  the last 11.
- On the 5-minute sample, every setup lost money or roughly broke even.
- The settings sweep does not prove anything: even the untuned defaults made
  money in the period it tested on, because that period happened to suit
  shorts.
- A "only short in a downtrend" filter made results worse, so it is off by
  default.

**Why the results are weak:**
- MNQ rose about 13% during the 5-minute sample, which is hard for a
  short-only bot.
- 39 sessions is far too few to judge anything.
- The hourly test is coarse: entries only on the hour, and no `orb` setup.

The next real step is several years of 5-minute MNQ data. Pass any CSV with
`--data`.

## Big-drop mode: one big short, only when the drop comes

`configs/shortbot-bigdrop.json` switches the bot to one setup and one trade a
day:
- only the `momentum` setup ("the last hour fell 1.5× its normal range");
- at most one trade a day;
- about $1,000 of risk, around half the Combine's $2,000 max loss;
- target 2.5 units below the entry, exit within 90 minutes.

```bash
python -m shortbot backtest --data yahoo-hourly --config configs/shortbot-bigdrop.json
python -m shortbot live --config configs/shortbot-bigdrop.json     # dry run
```

**How big should the one trade be?** Two years of hourly NQ, big-drop setup
only, one trade a day at most:

| Risk per trade | Topstep 50K Combines passed | Notes |
|---|---|---|
| ~$250 (normal) | 0% | Too slow: the trailing $2,000 limit catches it first |
| **~$1,000 (this preset)** | **26%, median 50 days** | Total +$4,058 over 77 trades, all of it in the last 11 months |
| ~$2,000 | 16% | Blows up in about 21 days |
| All-in, 50 MNQ | 0% (495 of 495 failed) | +$30,958 on paper, but one trade lost $26,161; the account dies at −$2,000 |

**What to expect:**
- **Frequency:** the setup fires about once every 7–8 trading days, not
  every day.
- **Swings:** in an account with no loss limit, the preset's worst drawdown
  over the two years was −$9,650.
- **Recent 5-minute sample:** its last 6 trades lost $1,979.
- **Bigger account:** the 150K Combine passes at the same rate (26%) and
  costs $199/month instead of $49.

**Safety check:** the live bot refuses to trade settings where a single
stop-out could use up the account's whole max loss, unless you pass
`--allow-account-risk`.

### 50K or 100K? Follow the whole plan, fees and payouts included

Every backtest now also replays the whole plan:
1. Buy a Combine and reset until it passes.
2. Trade the Express Funded account until it is blown, taking each payout
   as soon as it is allowed.
3. Buy again.

Fees count subscriptions, resets, the $149 activation and the $14.50/mo API.
`--account 50k|100k|150k` switches the rules and prices.

| Two years of hourly NQ, May 2024 – Sep 2026 | 50K, ~$1,000 a trade | 100K, ~$1,500 a trade |
|---|---|---|
| Straight losses that end a Combine | 2 | 2 |
| Combines passed | 26% | 26% |
| First funded account | blown, no payout | blown, no payout |
| Second funded account | one payout: $1,800 to you | one payout: $2,692 to you |
| Fees over the whole period | $1,684 | $2,684 |
| **Net** | **+$116** | **+$8** |

Both are about break-even: the one payout roughly covers the fees.
Starting on a different day gives +$8 to +$1,519. Those runs share most of
their trades, so they are one history seen from different doors, not
hundreds of independent trials.

```bash
python -m shortbot backtest --data yahoo-hourly --config configs/shortbot-bigdrop-100k.json
```

## Basic mode: react to the candles, both ways

`configs/shortbot-basic.json` turns off the short setups and uses only
`basic`. The rule: when the last 15 minutes are all green candles, or all
red, and the move is at least the normal size for that time of day, trade
it. It takes at most 3 trades a day, with about $1,000 of risk each.

- `basic_mode: "follow"`: buy after green, short after red. This is the
  preset.
- `basic_mode: "fade"`: buy the red dip, short the green rip.

## Is it better than luck?

Topstep's structure can make pure luck look good: a blown account only
costs the fee, while lucky upswings get paid out. So every idea should be
ranked against coin-flip bots. These take the same number of trades, with
the same stops, targets, sizing and limits, but enter at random times in a
random direction.

```bash
python -m shortbot vs-random --data yahoo-hourly --config configs/shortbot-basic.json
```

| Two years of hourly NQ, ~$1,000 a trade | Trading P&L | Beats this % of 200 coin-flip bots |
|---|---|---|
| Big-drop short (`shortbot-bigdrop.json`) | +$4,058 | **80%**, the best so far |
| Basic follow (buy green, short red) | −$873 | 62%, about random |
| Basic fade (buy dips, short rips) | −$13,736 | 16%, worse than random |
| Basic follow, 5-minute data, last 49 days | −$4,135 | 21% |

**How to read it:**
- Only the trading P&L ranking says anything about skill.
- The whole-plan result is mostly luck. Fade did worse than most coin
  flips on its trades, yet its whole-plan result beat 96% of them.
- **The bar for calling something an edge is beating about 95% of coin
  flips, in more than one period.** Nothing here does yet.

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

- **One protective stop.** A buy-stop is placed as soon as a short fills. If
  it can't be placed, the short is closed immediately.
- **Crash-safe.** Only the stop rests at the exchange. The target, time exit
  and flatten are done by the bot, so a crash leaves you protected, not
  exposed.
- **Clean start.** On start-up, any MNQ position or order left on the
  account is closed or cancelled.
- **Stopping it.** Create a file named `STOP` in the working folder, or
  press Ctrl-C. Either one flattens and exits.
- **Error guard.** After 5 errors in a row while holding a position, the bot
  flattens.
- **No late entries.** It never acts on a bar that closed more than a minute
  ago, for example after a restart.

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

Tests: `python -m pytest tests/test_shortbot.py tests/test_shortbot_live.py`.
They cover:
- short profit and loss, fills, and the stop-before-target rule;
- that no decision uses a future bar;
- the Topstep loss limits and consistency rule;
- the API client and order flow against a fake exchange;
- that a day replayed through the live loop takes the same entries, at the
  same prices, as the backtest.
