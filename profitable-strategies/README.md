# Profitable strategies

**New: [the top five, tested over 10,000+ trades each](top5/README.md).**
Every strategy below was ranked on one footing: dollars a day on $25,000,
2012 to 2026. The five that make the most, $66 to $92 a day, are all swing
trades on leveraged funds from the top-50 list.

- **No timing skill.** Run over 40,000 to 226,000 trades each on 173 funds,
  none of them picks its days much better than random entries on the same
  funds held just as long. The best, 01D4, is ahead by 3.8 bp a trade, gone
  at three times the slippage. Holding the funds made more.
- **Paper bots.** The same holds for paper bot #2 and split bots 1 and 2.
- **The one edge that held.** The Nasdaq-100 breakout: 3,176 trades, t =
  4.2, every year from 2013 positive. On the S&P 500, the Dow and the
  Russell 2000 the same rule is flat or losing.
- **$100 a day.** Adding NQ Managed Long lifts the quick-trade book to about
  $100 a day over 2013-2026. That leg failed the same test and lost $38,000
  on $25,000 through 2001-2002 and 2008.

**New: [quick trades, in and out the same day](quick-trades/README.md).** With
the three-minute cap relaxed, two same-day trades held up in every period and
setting tested:

- the Nasdaq-100 noise-area breakout (QQQ, TQQQ or MNQ);
- a gap breakout on the day's biggest large-cap gappers.

Together they make about $60 to $110 a day on $25,000 at 4x buying power,
with a Sharpe of 1.4 and a worst losing stretch of about $11,000. None reaches
$200 a day reliably; the page shows what leverage would take and the risk it
adds. Pine Scripts are included, and both are paper-traded after every close
from 2026-09-24.

**New: [stock scalping, holds of 3 minutes or less](scalping/README.md).**
The overnight search for ten strategies making $200 a day on $25,000 found
none. It covered about 1,700 books on four years of one-minute bars for 72
large US stocks, plus ten-second and one-second checks.

On bid-only bars, buying a sharp drop looked strong, up to $278 a day at 1x.
With both sides of the quote, most of that bounce turned out to be the
spread settling. Priced the way a bot would trade, the best book makes about
$8 a day at 1x in the years it was not fitted on, and it loses once spreads
are wider than a cent.

**Correction: the [Own-Drop Scalper](scalping/own-drop/README.md)**, listed
here yesterday, is the same rule. Its $146 a day at 2x came from one month of last-sale bars,
which carry the same effect. Treat it as unproven. Its paper trail replays
the same bars and cannot show this.

**New: [leveraged tech top 50](leveraged-etfs/README.md).** A seven-hour grind over
2x and 3x funds on semiconductors, AI and graphics-card names and big tech kept
5,024 profitable strategies, 2,454 of them at $80+ a session on $25,000 over
the last six months. The folder lists the top 50 ($213 to $530 a session
recently, all also profitable over 2019-2026 and 2012-2018), a $150-$200 pick
and a $100 low-risk pick. Recent dollars are mostly this year's semis rally;
each report shows the earlier years too.

**New: [FundedNext day trades](funded/README.md).** FundedNext Futures allows no
overnight holds, so the NQ strategies below cannot run there as written. This
folder has the top 10 reworked to be flat every afternoon with a daily stop, and
three strategies bred for the account's rules. Run together on a Legacy 50K,
the three bred strategies breached 0 to 12% of challenges in every period back
to 2000.

**[NQ E-mini at 2x](nq-2x/README.md).** Twenty strategies for the
Nasdaq-100 E-mini, long only at twice the account in notional, bred over 219
generations. Every one made money over the last six months (held out from
the breeding), over its 2019-2026 training window, over 2010-2018 and at three
times the costs. Five average more than $85 a session on $25,000 over the
held-out six months; the best, Calm Trend Champion, averages $111.

The list below is the earlier set, for the leveraged ETFs.


Fourteen quick-trade strategies for the leveraged funds you trade, ranked
most to least profitable by their return over the last six months on
TQQQ, MUU, RIOX and SOXL, the long funds only, at each file's own sizing.
That is the lens you chose. The other columns are the evidence: the last
twelve months, the whole window since January 2025, and 2010 to 2026 on
the long Nasdaq funds (TQQQ, SOXL, QLD). Every number is a backtest with
1 bp commission and 10 bp slippage a side, the decision taken on the close
and the fill at the next open. Data through the 22 September 2026 close.

Each strategy below has: what it does in words, the exact rules and risk
settings in values, its numbers on every window, its daily and monthly
profile in percent and in dollars on $25,000, the slot size for a 4% daily
loss limit, a JSON genome the tools read, and a Pine Script v6 strategy for
TradingView with a "buy at next open" alert.

## The plan for the next week or so

The week is for the mechanics, not for judging the edge: five sessions
give the primary book one to three signals, and the rare setups may not
fire at all. Judge after four weeks at the earliest, eight is better, on
profit factor and on the worst session against the tables below.

**What to run.** Three books, at the slot sizes for a 4% daily loss
limit: Combo: All Five Setups at 7% slots (about $1,750 a slot on
$25,000) as the primary book, plus Squeeze Days and Two Red Days at 13%
slots (about $3,250) as supplements. The two supplements share the Two
Red Days entry, so when both fire on the same fund take one position. Run
the other eleven on paper in the ledger; they are there to be watched,
and the ranking command below re-ranks them any day.

**Every trading day.**

1. After the close, 4:05 pm New York or later:
   `python -m evotrader.cli signals profitable-strategies/all.json --config configs/quick_names_long.json --refresh`.
   It lists every strategy that wants to buy at the next open, the fund
   and the slot.
2. Place the buys for the next open: a market-on-open order, or a limit a
   few cents above the pre-market indication. The backtest assumes the
   open plus 10 bp.
3. Exits are mechanical and need no signal run. Standard books: sell at
   the open after the first close 3% above your fill, or at the open of
   the third session after entry (two full sessions held), whichever comes
   first; if a close is 8% below the fill, sell at the next open. Squeeze
   Days and Two Red Days: sell at the open after a close up 2% on the day,
   or after two (Squeeze Days) or three (Two Red Days) sessions; 6% stop
   on the close.
4. Write every signal, fill and exit into `forward/ledger.md`, including
   the signals you did not take.

**Every Friday.**
`python -m evotrader.cli evaluate profitable-strategies/all.json --config configs/quick_names_long.json --test-frac 0 --since 2026-09-23 --refresh`
gives the model's own P&L since the freeze for every strategy; compare it
with the ledger. The differences are fills and slippage, and they are the
point of the week.

**Tonight's signal, 22 September close.** Squeeze Days fired on MUU: the
20-day volatility is 59% of the 60-day and the close, 38.92, crossed above
the upper Bollinger band at 37.19. That is a buy at Wednesday's open, 13%
of the account at the funded sizing, out at the open after a close up 2%
on the day or after two sessions, 6% stop on the close. Nothing else
fired.

**Where to trade it.** These are ETFs, so a brokerage account, in
whichever Robinhood account you trade. For a first week on paper, the
Pine scripts run on a TradingView paper account with their alerts, one
chart per fund. The FundedNext futures account cannot hold these funds
and, per `../strategies/intraday/`, has nothing tradeable from this
research yet.

**The stop rule for the whole book.** If the ledger shows a session
worse than the worst day in the tables at your slot size, halve the slots
for the rest of the month. If a strategy's six-month row goes negative on
the ranking command, retire it until it turns.


## Ranking

Return (trades) on the long funds at the file's sizing. "2010 to 2026" is
TQQQ, SOXL and QLD, the funds with that much history.

| # | strategy | last 6 months | last 12 months | since Jan 2025 | 2010 to 2026 | worst day, 6 months | status |
|---|---|---|---|---|---|---|---|
| 1 | Combo: Recent Winners | +28.1% (26) | +67.6% (61) | +77.1% (85) | +160.9%, PF 1.45 (529) | -4.5% | trade small: six-month row is in-sample |
| 2 | Combo: All Five Setups | +26.8% (33) | +67.7% (81) | +79.9% (110) | +294.1%, PF 1.58 (746) | -7.8% | trade: the primary book |
| 3 | Band Break on Volume | +26.7% (9) | +47.4% (17) | +50.1% (32) | -5.9%, PF 0.97 (232) | -3.9% | trade small: regime bet, loses since 2010 |
| 4 | Squeeze Days (evolved) | +18.5% (16) | +32.4% (27) | +38.3% (39) | +95.0%, PF 2.58 (183) | -4.2% | trade |
| 5 | Capitulation Close | +18.5% (16) | +83.2% (38) | +100.7% (54) | +111.4%, PF 1.36 (375) | -6.5% | trade |
| 6 | Pullback Cluster (ungated) | +16.8% (17) | +41.1% (38) | +41.0% (53) | +125.0%, PF 1.87 (319) | -5.3% | trade |
| 7 | Two Red Days (evolved) | +14.6% (13) | +26.0% (23) | +24.2% (28) | +60.0%, PF 3.74 (69) | -4.2% | trade: rare, a supplement |
| 8 | Combo: Capitulation or Oversold | +12.7% (20) | +66.3% (47) | +78.3% (64) | +223.8%, PF 1.65 (529) | -7.2% | hold back until Oversold Dip turns |
| 9 | Red Day Near the Mean | +10.5% (10) | +19.5% (29) | +11.6% (37) | +27.4%, PF 1.26 (176) | -5.7% | supplement |
| 10 | Pullback Cluster (volume-gated) | +9.8% (8) | +17.4% (21) | +12.4% (29) | +62.1%, PF 1.53 (197) | -6.5% | covered by Combo: All Five Setups |
| 11 | Volume Climax | +6.9% (4) | +26.4% (12) | +28.0% (22) | +65.6%, PF 1.69 (139) | -1.6% | trade when it fires |
| 12 | Red Day Above the 50 | +2.2% (19) | +34.8% (54) | +35.6% (65) | +92.7%, PF 1.56 (228) | -9.7% | watch |
| 13 | Prior-Low Break on Volume | +0.4% (9) | +20.5% (35) | +16.0% (47) | +74.8%, PF 1.33 (391) | -5.7% | watch |
| 14 | Oversold Dip Above the 50 | -6.4% (6) | +6.8% (16) | +11.7% (24) | +158.3%, PF 2.09 (252) | -6.6% | watch |

Two readings before the list. First, the six-month gains sit in RIOX, MUU
and SOXL, the three most volatile long funds, in a half-year when they
swung hard; on TQQQ alone every strategy is modest. Second, the inverse
funds (SQQQ, MUD, SOXS) lose in every one of these setups and are not in
this universe. Details and the earlier research are in `../strategies/`.

## The strategies, most to least profitable

### 1. Combo: Recent Winners

**Status:** trade small: six-month row is in-sample.

**In words.** One book that buys on any of the five setups that led the last six months: a volume climax (twice normal volume on a 3% down day), a close under the lower Bollinger band on 1.2x volume, a 4% down day still within 3% of the 20-day mean on 1.2x volume, the volume-gated pullback cluster, and Two Red Days. First match wins, five 20% slots. It buys the next open and sells at the open after the first close 3% above entry or after two sessions, with an 8% stop and a 4% target checked on the close and one session of cooldown. Every entry is a fast flush in a leveraged fund that gets bought back within a day or two. The caveat is that it was assembled after looking at the six-month winners, so its six-month row is in-sample by construction; judge it on the twelve-month row and the 2010-2026 row, both of which hold up. RIOX and SOXL carry it, MUU is barely positive.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 20% of equity when `volume_ratio > 2.0 and ret1 < -0.03`
- BUY 20% of equity when `bb_pct < 0.0 and volume_ratio > 1.2`
- BUY 20% of equity when `ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2`
- BUY 20% of equity when `ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1`
- BUY 20% of equity when `ret1 < 0 and prev(ret1) < -0.028 and close > sma50 and ret5 < -0.078`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 20% of equity, up to 5 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +28.1% | 26 | 62% | 2.42 | +5.07% | -4.5% |
| last 12 months | +67.6% | 61 | 66% | 2.28 | +4.50% | -4.5% |
| since 3 Jan 2025 | +77.1% | 85 | 66% | 1.97 | +3.69% | -8.4% |
| 2010 to 2026, TQQQ/SOXL/QLD | +160.9% | 529 | 62% | 1.45 | +1.00% | -16.6% |

- Per month on the long funds: mean +3.2% (last twelve months +4.8%), 68% of months positive, 4.5 trades a month. On $25,000 that is about $799 a month at the file's sizing.
- Per session over the last six months: in the market 33% of sessions, mean +0.21% (+$52), typical active session -0.01%, best +8.5% (+$2,125), worst -4.5% (-$1,125), 3.2% of sessions below -2%.
- By fund, last six months: RIOX 25t 72% +6.54%  SOXL 21t 71% +4.68%  TQQQ 16t 69% +2.27%  MUU 23t 52% +0.66%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 12% slots instead of 20%, which scales every figure above by about 0.60: roughly $479 a month and a worst session near -$675.

**Files.** `01_combo_recent_winners.json` (the genome, for `evaluate` and `signals`), `01_combo_recent_winners.pine` (TradingView strategy with a "buy at next open" alert).

### 2. Combo: All Five Setups

**Status:** trade: the primary book.

**In words.** The workhorse. Any of the five original setups buys the next open: capitulation close, oversold dip above the 50-day, red day above the 50-day, prior-low break on volume, pullback cluster on volume. Same exits as above: the open after a close 3% above entry or after two sessions, 8% stop, 4% target, one session of cooldown. The most active book here, 110 trades in twenty months, and the broadest evidence, +294% since 2010 on TQQQ, SOXL and QLD across 746 trades, profitable on every window. Its weak spot is the worst day, -7.8% over six months and -16.6% since 2010 at 20% slots, so it wants the smallest slots of the group in an account with a daily limit. SOXL is its best fund at 76% winners.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 20% of equity when `ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3`
- BUY 20% of equity when `rsi7 < 40 and close > sma50`
- BUY 20% of equity when `ret1 < -0.045 and close > sma50 and volume_ratio > 1.0`
- BUY 20% of equity when `close < prev(low) and close > sma50 and volume_ratio > 1.2`
- BUY 20% of equity when `ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 20% of equity, up to 5 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +26.8% | 33 | 58% | 1.95 | +3.91% | -7.8% |
| last 12 months | +67.7% | 81 | 63% | 1.91 | +3.44% | -7.8% |
| since 3 Jan 2025 | +79.9% | 110 | 65% | 1.75 | +2.96% | -9.3% |
| 2010 to 2026, TQQQ/SOXL/QLD | +294.1% | 746 | 62% | 1.58 | +1.01% | -16.6% |

- Per month on the long funds: mean +3.3% (last twelve months +4.4%), 68% of months positive, 5.8 trades a month. On $25,000 that is about $818 a month at the file's sizing.
- Per session over the last six months: in the market 37% of sessions, mean +0.21% (+$52), typical active session +0.03%, best +9.4% (+$2,350), worst -7.8% (-$1,950), 5.6% of sessions below -2%.
- By fund, last six months: SOXL 34t 76% +4.96%  RIOX 28t 57% +2.59%  MUU 27t 56% +2.27%  TQQQ 21t 67% +1.08%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 7% slots instead of 20%, which scales every figure above by about 0.35: roughly $286 a month and a worst session near -$682.

**Files.** `02_combo_all_five.json` (the genome, for `evaluate` and `signals`), `02_combo_all_five.pine` (TradingView strategy with a "buy at next open" alert).

### 3. Band Break on Volume

**Status:** trade small: regime bet, loses since 2010.

**In words.** A close under the lower Bollinger band (20 days, 2 standard deviations) on 1.2x average volume, in any regime. Standard exits: 3% or two sessions, 8% stop, 4% target. The highest per-trade figure of the group over the last year, +9.6% a trade with 82% winners, on very few trades, seventeen in twelve months. It is a bet on the current regime, not a durable edge: since 2010 on the long Nasdaq funds it is -6% with a -49% drawdown, because in a real bear market the band keeps walking down and the strategy keeps buying it. Trade it small, and stop the moment RIOX, MUU and SOXL stop snapping back.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `bb_pct < 0.0 and volume_ratio > 1.2`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +26.7% | 9 | 78% | 7.75 | +11.10% | -3.9% |
| last 12 months | +47.4% | 17 | 82% | 8.68 | +9.60% | -3.9% |
| since 3 Jan 2025 | +50.1% | 32 | 69% | 2.96 | +5.68% | -10.5% |
| 2010 to 2026, TQQQ/SOXL/QLD | -5.9% | 232 | 58% | 0.97 | +0.08% | -20.5% |

- Per month on the long funds: mean +2.0% (last twelve months +3.4%), 43% of months positive, 1.5 trades a month. On $25,000 that is about $504 a month at the file's sizing.
- Per session over the last six months: in the market 9% of sessions, mean +0.20% (+$50), typical active session +1.33%, best +7.5% (+$1,875), worst -3.9% (-$975), 0.8% of sessions below -2%.
- By fund, last six months: SOXL 9t 89% +9.84%  MUU 5t 60% +7.99%  RIOX 7t 71% +6.15%  TQQQ 11t 55% +0.93%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 17% slots instead of 25%, which scales every figure above by about 0.68: roughly $342 a month and a worst session near -$663.

**Files.** `03_band_break_on_volume.json` (the genome, for `evaluate` and `signals`), `03_band_break_on_volume.pine` (TradingView strategy with a "buy at next open" alert).

### 4. Squeeze Days (evolved)

**Status:** trade.

**In words.** Two entries. The first is a breakout after a squeeze: 20-day volatility under 80% of 60-day volatility, then a close crossing above the upper Bollinger band. The second is the Two Red Days setup. Out at the open after a close up 2% on the day or after two sessions, 6% stop, 8% target, no cooldown. Bred by the evolution, and the one momentum entry that works in these names. Quiet numbers on every window: 74% winners, a worst day of -4.2% over six months and -3.6% since 2010, profit factor 2.58 across 183 trades since 2010 on the long Nasdaq funds. Best on SOXL (91% winners) and MUU. It fired on MUU at the 22 September close.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 20% of equity when `vol_ratio_20_60 < 0.8 and cross_above(close, bb_upper)`
- BUY 20% of equity when `(ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078`
- SELL when `ret1 > 0.02`
- SELL when `bars_held >= 3`
- SELL when `bars_held >= 2`
- Risk: slot 20% of equity, up to 4 positions, stop 6%, target 8%, max hold 3 bars, cooldown 0 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +18.5% | 16 | 75% | 2.46 | +5.76% | -4.2% |
| last 12 months | +32.4% | 27 | 74% | 2.55 | +5.55% | -4.2% |
| since 3 Jan 2025 | +38.3% | 39 | 74% | 2.18 | +4.46% | -7.0% |
| 2010 to 2026, TQQQ/SOXL/QLD | +95.0% | 183 | 70% | 2.58 | +1.88% | -3.6% |

- Per month on the long funds: mean +1.9% (last twelve months +2.4%), 47% of months positive, 2.1 trades a month. On $25,000 that is about $468 a month at the file's sizing.
- Per session over the last six months: in the market 16% of sessions, mean +0.14% (+$35), typical active session -0.07%, best +11.6% (+$2,900), worst -4.2% (-$1,050), 0.8% of sessions below -2%.
- By fund, last six months: SOXL 11t 91% +10.33%  MUU 12t 75% +4.01%  TQQQ 8t 75% +1.33%  RIOX 8t 50% +0.19%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 13% slots instead of 20%, which scales every figure above by about 0.65: roughly $304 a month and a worst session near -$683.

**Files.** `04_squeeze_days.json` (the genome, for `evaluate` and `signals`), `04_squeeze_days.pine` (TradingView strategy with a "buy at next open" alert).

### 5. Capitulation Close

**Status:** trade.

**In words.** The purest form of the edge: a 4% down day that closes in the bottom quarter of its range on 1.3x volume, a capitulation print. Buy the next open, sell at the open after the first close 3% up or after two sessions, 8% stop, 4% target. The best twelve months of the group (+83%, profit factor 3.71, 76% winners) and profitable on every window since 2010 (+111%, 375 trades). Its tail is the fat one: the best day is +36%, the worst -11%, and the worst since 2010 is -20% (March 2020). It fires two to three times a month across the four funds and is strongest on RIOX.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +18.5% | 16 | 62% | 2.06 | +4.76% | -6.5% |
| last 12 months | +83.2% | 38 | 76% | 3.71 | +6.73% | -6.5% |
| since 3 Jan 2025 | +100.7% | 54 | 70% | 2.71 | +5.74% | -11.0% |
| 2010 to 2026, TQQQ/SOXL/QLD | +111.4% | 375 | 62% | 1.36 | +0.95% | -20.5% |

- Per month on the long funds: mean +3.5% (last twelve months +5.3%), 62% of months positive, 2.6 trades a month. On $25,000 that is about $873 a month at the file's sizing.
- Per session over the last six months: in the market 21% of sessions, mean +0.15% (+$38), typical active session +0.35%, best +7.5% (+$1,875), worst -6.5% (-$1,625), 3.2% of sessions below -2%.
- By fund, last six months: RIOX 17t 71% +8.60%  SOXL 13t 69% +6.19%  MUU 12t 67% +4.72%  TQQQ 12t 75% +2.22%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 10% slots instead of 25%, which scales every figure above by about 0.40: roughly $349 a month and a worst session near -$650.

**Files.** `05_capitulation_close.json` (the genome, for `evaluate` and `signals`), `05_capitulation_close.pine` (TradingView strategy with a "buy at next open" alert).

### 6. Pullback Cluster (ungated)

**Status:** trade.

**In words.** Two red closes in a row with a 3% loss over five sessions while the close is still above the 50-day mean. Out at the open after the first close up 1% or after three sessions, 10% stop, no target. There is no volume filter, so it fires twice as often as the gated version below and has done better on the long funds on every window (+125% since 2010 against +62%). The volume gate was added for the six-fund basket where the inverse funds were losing; on the long funds it only costs trades.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50`
- SELL when `ret1 > 0.01`
- SELL when `bars_held >= 3`
- Risk: slot 25% of equity, up to 4 positions, stop 10%, no target, max hold 3 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +16.8% | 17 | 76% | 1.89 | +4.09% | -5.3% |
| last 12 months | +41.1% | 38 | 68% | 2.09 | +3.92% | -7.9% |
| since 3 Jan 2025 | +41.0% | 53 | 68% | 1.81 | +2.86% | -8.5% |
| 2010 to 2026, TQQQ/SOXL/QLD | +125.0% | 319 | 70% | 1.87 | +1.11% | -7.8% |

- Per month on the long funds: mean +2.0% (last twelve months +3.0%), 53% of months positive, 2.8 trades a month. On $25,000 that is about $505 a month at the file's sizing.
- Per session over the last six months: in the market 16% of sessions, mean +0.14% (+$35), typical active session -0.27%, best +14.6% (+$3,650), worst -5.3% (-$1,325), 2.4% of sessions below -2%.
- By fund, last six months: SOXL 14t 64% +5.42%  RIOX 13t 69% +3.20%  TQQQ 10t 80% +2.10%  MUU 16t 62% +0.84%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 13% slots instead of 25%, which scales every figure above by about 0.52: roughly $263 a month and a worst session near -$689.

**Files.** `06_pullback_cluster_ungated.json` (the genome, for `evaluate` and `signals`), `06_pullback_cluster_ungated.pine` (TradingView strategy with a "buy at next open" alert).

### 7. Two Red Days (evolved)

**Status:** trade: rare, a supplement.

**In words.** Yesterday down more than 2.8%, today down again, the five-day return under -7.8%, and the close still above the 50-day mean. Out at the open after a close up more than 2% on the day or after three sessions, 6% stop, no target, no cooldown. The evolution's best child and the cleanest record of anything here: 81% winners and profit factor 3.74 since 2010 with a worst day of -3.2% at 20% slots. It is rare, one or two trades a month, so it is a supplement to a book rather than a book. SOXL 86% winners, RIOX only 50%.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 20% of equity when `(ret1 < 0 and prev(ret1) < -0.028 and close > sma50) and ret5 < -0.078`
- SELL when `ret1 > 0.02`
- SELL when `bars_held >= 3`
- Risk: slot 20% of equity, up to 4 positions, stop 6%, no target, max hold 3 bars, cooldown 0 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +14.6% | 13 | 69% | 2.16 | +5.78% | -4.2% |
| last 12 months | +26.0% | 23 | 70% | 2.27 | +5.41% | -4.2% |
| since 3 Jan 2025 | +24.2% | 28 | 68% | 1.82 | +4.26% | -7.0% |
| 2010 to 2026, TQQQ/SOXL/QLD | +60.0% | 69 | 81% | 3.74 | +3.49% | -3.2% |

- Per month on the long funds: mean +1.3% (last twelve months +2.0%), 42% of months positive, 1.5 trades a month. On $25,000 that is about $321 a month at the file's sizing.
- Per session over the last six months: in the market 13% of sessions, mean +0.12% (+$30), typical active session -0.31%, best +11.6% (+$2,900), worst -4.2% (-$1,050), 0.8% of sessions below -2%.
- By fund, last six months: SOXL 7t 86% +11.31%  MUU 10t 70% +3.82%  TQQQ 3t 67% +0.10%  RIOX 8t 50% +0.19%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 13% slots instead of 20%, which scales every figure above by about 0.65: roughly $209 a month and a worst session near -$683.

**Files.** `07_two_red_days.json` (the genome, for `evaluate` and `signals`), `07_two_red_days.pine` (TradingView strategy with a "buy at next open" alert).

### 8. Combo: Capitulation or Oversold

**Status:** hold back until Oversold Dip turns.

**In words.** Capitulation Close and Oversold Dip in one book, five 20% slots, standard exits. Better than Combo: All Five Setups per trade on the twelve-month lens (+66%, profit factor 2.72) and since 2010, but the oversold half has lost every trade since March, which is why it trails on six months. If Oversold Dip turns back on, this is the better combo of the two.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 20% of equity when `ret1 < -0.04 and (close - low) / (high - low + 0.0001) < 0.25 and volume_ratio > 1.3`
- BUY 20% of equity when `rsi7 < 40 and close > sma50`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 20% of equity, up to 5 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +12.7% | 20 | 55% | 1.62 | +3.43% | -7.2% |
| last 12 months | +66.3% | 47 | 72% | 2.72 | +5.72% | -7.2% |
| since 3 Jan 2025 | +78.3% | 64 | 70% | 2.35 | +4.93% | -9.3% |
| 2010 to 2026, TQQQ/SOXL/QLD | +223.8% | 529 | 65% | 1.65 | +1.22% | -16.6% |

- Per month on the long funds: mean +3.2% (last twelve months +4.5%), 63% of months positive, 3.4 trades a month. On $25,000 that is about $805 a month at the file's sizing.
- Per session over the last six months: in the market 27% of sessions, mean +0.11% (+$28), typical active session +0.00%, best +6.0% (+$1,500), worst -7.2% (-$1,800), 4.0% of sessions below -2%.
- By fund, last six months: RIOX 18t 72% +9.10%  SOXL 16t 81% +6.71%  TQQQ 14t 79% +3.27%  MUU 16t 50% -0.09%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 7% slots instead of 20%, which scales every figure above by about 0.35: roughly $282 a month and a worst session near -$630.

**Files.** `08_combo_capitulation_or_oversold.json` (the genome, for `evaluate` and `signals`), `08_combo_capitulation_or_oversold.pine` (TradingView strategy with a "buy at next open" alert).

### 9. Red Day Near the Mean

**Status:** supplement.

**In words.** A 4% down day that closes within 3% of the 20-day mean on 1.2x volume: a sharp drop that has not yet broken the short-term trend. Standard exits. Positive on every window but thin everywhere, +27% since 2010 at profit factor 1.26, ten trades over the last six months at profit factor 2.16. A supplement.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `ret1 < -0.04 and close > sma20 * 0.97 and volume_ratio > 1.2`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +10.5% | 10 | 60% | 2.16 | +4.31% | -5.7% |
| last 12 months | +19.5% | 29 | 62% | 1.69 | +2.67% | -5.7% |
| since 3 Jan 2025 | +11.6% | 37 | 59% | 1.30 | +1.41% | -8.5% |
| 2010 to 2026, TQQQ/SOXL/QLD | +27.4% | 176 | 59% | 1.26 | +0.62% | -9.4% |

- Per month on the long funds: mean +0.6% (last twelve months +1.8%), 40% of months positive, 1.9 trades a month. On $25,000 that is about $161 a month at the file's sizing.
- Per session over the last six months: in the market 19% of sessions, mean +0.09% (+$22), typical active session -0.16%, best +5.7% (+$1,425), worst -5.7% (-$1,425), 1.6% of sessions below -2%.
- By fund, last six months: SOXL 10t 70% +3.04%  RIOX 13t 62% +1.67%  MUU 12t 50% +0.14%  TQQQ 2t 50% -0.74%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 12% slots instead of 25%, which scales every figure above by about 0.48: roughly $77 a month and a worst session near -$684.

**Files.** `09_red_day_near_the_mean.json` (the genome, for `evaluate` and `signals`), `09_red_day_near_the_mean.pine` (TradingView strategy with a "buy at next open" alert).

### 10. Pullback Cluster (volume-gated)

**Status:** covered by Combo: All Five Setups.

**In words.** The pullback cluster with a 1.1x volume gate and the standard exits (3% or two sessions, 8% stop, 4% target). Profitable on every window, with fewer trades and less return than the ungated version on the long funds. It is here because it is one of the five legs of Combo: All Five Setups.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03 and close > sma50 and volume_ratio > 1.1`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +9.8% | 8 | 62% | 2.36 | +5.16% | -6.5% |
| last 12 months | +17.4% | 21 | 62% | 1.83 | +3.36% | -6.5% |
| since 3 Jan 2025 | +12.4% | 29 | 66% | 1.39 | +1.92% | -8.5% |
| 2010 to 2026, TQQQ/SOXL/QLD | +62.1% | 197 | 63% | 1.53 | +1.08% | -6.5% |

- Per month on the long funds: mean +0.8% (last twelve months +1.5%), 32% of months positive, 1.5 trades a month. On $25,000 that is about $195 a month at the file's sizing.
- Per session over the last six months: in the market 9% of sessions, mean +0.08% (+$20), typical active session +0.35%, best +7.5% (+$1,875), worst -6.5% (-$1,625), 1.6% of sessions below -2%.
- By fund, last six months: SOXL 10t 70% +3.99%  TQQQ 7t 71% +1.53%  MUU 7t 57% +0.66%  RIOX 5t 60% +0.09%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 10% slots instead of 25%, which scales every figure above by about 0.40: roughly $78 a month and a worst session near -$650.

**Files.** `10_pullback_cluster_volume_gated.json` (the genome, for `evaluate` and `signals`), `10_pullback_cluster_volume_gated.pine` (TradingView strategy with a "buy at next open" alert).

### 11. Volume Climax

**Status:** trade when it fires.

**In words.** Twice normal volume on a 3% down day, any regime, standard exits. 73% winners over twenty months and +66% since 2010 at profit factor 1.69, but only four trades in the last six months, which is why it ranks this low. When it fires, take it: the twelve-month row is +26% at profit factor 7.46 on twelve trades, and its worst day over six months is -1.6%.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `volume_ratio > 2.0 and ret1 < -0.03`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +6.9% | 4 | 75% | 6.76 | +6.82% | -1.6% |
| last 12 months | +26.4% | 12 | 83% | 7.46 | +8.06% | -2.4% |
| since 3 Jan 2025 | +28.0% | 22 | 73% | 2.38 | +4.81% | -7.8% |
| 2010 to 2026, TQQQ/SOXL/QLD | +65.6% | 139 | 60% | 1.69 | +1.59% | -9.9% |

- Per month on the long funds: mean +1.2% (last twelve months +1.8%), 43% of months positive, 1.0 trades a month. On $25,000 that is about $304 a month at the file's sizing.
- Per session over the last six months: in the market 9% of sessions, mean +0.05% (+$12), typical active session +0.50%, best +3.4% (+$850), worst -1.6% (-$400), 0.0% of sessions below -2%.
- By fund, last six months: SOXL 6t 83% +9.22%  RIOX 5t 60% +4.99%  TQQQ 4t 100% +8.14%  MUU 7t 57% -0.99%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 25% slots instead of 25%, which scales every figure above by about 1.00: roughly $304 a month and a worst session near -$400.

**Files.** `11_volume_climax.json` (the genome, for `evaluate` and `signals`), `11_volume_climax.pine` (TradingView strategy with a "buy at next open" alert).

### 12. Red Day Above the 50

**Status:** watch.

**In words.** A 4.5% down day with the close above the 50-day mean on at least average volume, standard exits. Profitable since 2010 (+93%, profit factor 1.56) and over twelve months (+35%), but 40% winners since March with a -9.7% worst day. On watch, not in the book.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `ret1 < -0.045 and close > sma50 and volume_ratio > 1.0`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +2.2% | 19 | 42% | 1.09 | +0.72% | -9.7% |
| last 12 months | +34.8% | 54 | 59% | 1.54 | +2.44% | -9.7% |
| since 3 Jan 2025 | +35.6% | 65 | 60% | 1.46 | +2.10% | -9.7% |
| 2010 to 2026, TQQQ/SOXL/QLD | +92.7% | 228 | 63% | 1.56 | +1.23% | -9.4% |

- Per month on the long funds: mean +1.8% (last twelve months +2.5%), 47% of months positive, 3.4 trades a month. On $25,000 that is about $445 a month at the file's sizing.
- Per session over the last six months: in the market 23% of sessions, mean +0.04% (+$10), typical active session -0.54%, best +11.3% (+$2,825), worst -9.7% (-$2,425), 5.6% of sessions below -2%.
- By fund, last six months: SOXL 21t 81% +5.16%  MUU 21t 57% +1.22%  RIOX 16t 44% +0.38%  TQQQ 7t 43% -0.51%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 7% slots instead of 25%, which scales every figure above by about 0.28: roughly $125 a month and a worst session near -$679.

**Files.** `12_red_day_above_the_50.json` (the genome, for `evaluate` and `signals`), `12_red_day_above_the_50.pine` (TradingView strategy with a "buy at next open" alert).

### 13. Prior-Low Break on Volume

**Status:** watch.

**In words.** A close below yesterday's low, above the 50-day mean, on 1.2x volume: a one-day shakeout that is usually bought back. +75% since 2010 across 391 trades and +20% over twelve months, flat since March (profit factor 0.87 on ten trades). On watch.

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `close < prev(low) and close > sma50 and volume_ratio > 1.2`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 8%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | +0.4% | 9 | 44% | 1.03 | +0.43% | -5.7% |
| last 12 months | +20.5% | 35 | 63% | 1.59 | +2.39% | -5.7% |
| since 3 Jan 2025 | +16.0% | 47 | 66% | 1.35 | +1.45% | -8.7% |
| 2010 to 2026, TQQQ/SOXL/QLD | +74.8% | 391 | 60% | 1.33 | +0.65% | -9.4% |

- Per month on the long funds: mean +0.9% (last twelve months +1.9%), 37% of months positive, 2.5 trades a month. On $25,000 that is about $232 a month at the file's sizing.
- Per session over the last six months: in the market 14% of sessions, mean +0.01% (+$2), typical active session -0.01%, best +4.9% (+$1,225), worst -5.7% (-$1,425), 2.4% of sessions below -2%.
- By fund, last six months: SOXL 11t 82% +4.95%  RIOX 11t 64% +3.17%  TQQQ 11t 73% +0.24%  MUU 14t 50% -1.71%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 12% slots instead of 25%, which scales every figure above by about 0.48: roughly $111 a month and a worst session near -$684.

**Files.** `13_prior_low_break_on_volume.json` (the genome, for `evaluate` and `signals`), `13_prior_low_break_on_volume.pine` (TradingView strategy with a "buy at next open" alert).

### 14. Oversold Dip Above the 50

**Status:** watch.

**In words.** RSI(7) under 40 with the close above the 50-day mean; standard exits with a 10% stop. The best sixteen-year record of the group (+158%, profit factor 2.09, 72% winners) and one winner in six trades since March. The regime has turned against multi-day dip buying in these names, so wait for the six-month row to turn positive before trading it. MUU is the fund that broke it (20% winners).

**In values.** Universe TQQQ, MUU, RIOX, SOXL, daily bars. Decide on the close, fill at the next open.
- BUY 25% of equity when `rsi7 < 40 and close > sma50`
- SELL when `position_return > 0.03`
- SELL when `bars_held >= 2`
- Risk: slot 25% of equity, up to 4 positions, stop 10%, target 4%, max hold 2 bars, cooldown 1 bar(s). Costs in the backtest: 1 bp commission and 10 bp slippage a side.

**Numbers** (long funds at the file's sizing unless noted):

| window | return | trades | win | PF | avg trade | worst day |
|---|---|---|---|---|---|---|
| last 6 months (22 Mar to 22 Sep 2026) | -6.4% | 6 | 17% | 0.47 | -4.07% | -6.6% |
| last 12 months | +6.8% | 16 | 56% | 1.29 | +1.95% | -6.6% |
| since 3 Jan 2025 | +11.7% | 24 | 62% | 1.42 | +2.07% | -6.6% |
| 2010 to 2026, TQQQ/SOXL/QLD | +158.3% | 252 | 72% | 2.09 | +1.59% | -7.6% |

- Per month on the long funds: mean +0.7% (last twelve months +0.7%), 32% of months positive, 1.3 trades a month. On $25,000 that is about $170 a month at the file's sizing.
- Per session over the last six months: in the market 11% of sessions, mean -0.05% (-$12), typical active session -1.00%, best +3.7% (+$925), worst -6.6% (-$1,650), 2.4% of sessions below -2%.
- By fund, last six months: RIOX 5t 60% +9.32%  SOXL 7t 86% +4.82%  TQQQ 7t 71% +1.99%  MUU 5t 20% -8.91%.
- Sizing for a 4% daily loss limit (worst day inside two-thirds of it): 10% slots instead of 25%, which scales every figure above by about 0.40: roughly $68 a month and a worst session near -$660.

**Files.** `14_oversold_dip_above_the_50.json` (the genome, for `evaluate` and `signals`), `14_oversold_dip_above_the_50.pine` (TradingView strategy with a "buy at next open" alert).

## Reproduce

```bash
# ranking, monthly and daily profiles, on the long funds
python -m evotrader.cli evaluate profitable-strategies/all.json --config configs/quick_names_long.json --test-frac 0 --recent 6m --by-month --daily --since 2026-03-22,2025-09-22
# the sixteen-year record on the long Nasdaq funds
python -m evotrader.cli evaluate profitable-strategies/all.json --config configs/quick_nasdaq.json --symbols TQQQ,SOXL,QLD --test-frac 0 --by-year
# tonight's signals (run after the close)
python -m evotrader.cli signals profitable-strategies/all.json --config configs/quick_names_long.json --refresh
# the forward-test ledger, every bar after the freeze
python -m evotrader.cli evaluate profitable-strategies/all.json --config configs/quick_names_long.json --test-frac 0 --since 2026-09-23 --refresh
```

The full reports those commands produce, with month-by-month and
year-by-year rows for every strategy, are in `reports/`: the long funds
since January 2025 and the long Nasdaq funds since 2010. The forward-test
ledger to fill in is `forward/ledger.md`.
