# Stock scalping with trades held 3 minutes or less

On the night of 2026-09-23 you asked for ten strategies. Each was to make
$200 a day on a $25,000 account, with every trade held three minutes or less.
This page is the answer. Everything here is a backtest; nothing placed an
order.

## The answer: none qualify

None of the ten exists in this data.

On one-minute bars, several books look like they beat $200 a day at 4x
buying power (the day-trading maximum on $25,000). They stop working once the
test uses the prices a bot would actually trade at.

The data is four years (Sep 2022 to Sep 2026) of one-minute bars for 72 large
US stocks. On it, the best book, priced realistically, makes about $8 a day
at 1x in the two years it was not fitted on, and it loses once spreads are
wider than a cent. Every other book is flat or losing.

| Book (3 slots, 3-minute hold) | Minute-bar backtest, 1x | Priced realistically, 1x | Realistic at 4x |
| --- | --- | --- | --- |
| Buy a name's sharp own drop, 09:35-10:00 | +$23 a day | -$1 (1-cent spreads) | -$6 |
| A model picks the drops, all day | +$278 | +$8 (1-cent spreads), -$38 (2 bp spreads) | +$34 / -$154 |
| 576 simple rules: buy or sell, drops or rises, four windows | up to +$23 | best +$1; 1 of 576 positive in both periods | +$4 |
| Buy the drop with a limit order at the bid | - | best +$3 | +$11 |
| Your 10-30 second spike idea, faded or followed (16 names, last year, 10-second bars) | - | best +$5 | +$19 |
| Names gapping 2-7% on news, first hour, with or against the gap | - | best +$3 | +$12 |

Dollars are per day on $25,000, averaged over the test years (Sep 2024 to
Sep 2026). Every rule and the model were chosen on Sep 2022 to Aug 2024 only.
The last row covers the one year the 10-second bars span.

## Why the minute backtests were wrong

The minute backtests bought at the next minute's first price and sold three
minutes later. Three checks show what that misses.

1. **The bars were bid prices only.** When a stock is sold hard for a minute,
   the bid falls and the spread widens. Afterwards the spread narrows again,
   and the bid rises even if the stock's value has not moved.

   The offer side was downloaded to test this. On the opening book's trades,
   the bid gained +5.5 bp over the three minutes, but the midpoint only
   +2.7 bp. On the model's trades the figures were +7.1 bp and +3.6 bp. Each
   gap is exactly half of how much the spread narrowed (from 24.6 to 19.0 bp
   on the data's own quotes).

   A buyer pays the offer and sells at the bid, so none of that "bounce" is
   theirs. On the opening window with 16 names over the last year, the bid
   gained +4.1 bp and the midpoint +0.2 bp.
2. **What is left after a few seconds.** One-second quotes were pulled around
   the books' actual trades from the last year (826 and 492 trades). A bot
   reading minute bars gets its order in 2-3 seconds after the minute closes.
   The midpoint gain it keeps is +3.5 to +4.3 bp: a small bounce that is
   still there a few seconds later.
3. **That bounce is about one spread.** The model's trades cluster in names
   such as MDB, CVNA, SPOT, TEAM, TWLO, ZS, ROKU and SNOW. These have the
   widest quoted spreads in this data. Paying the spread on the way in and
   out costs about as much as the bounce pays, or more. The live spreads
   being measured today (below) will pin down how much more.

   A limit order resting at the bid would avoid paying the spread. But with a
   strict fill rule (filled only if the bid trades below the limit), the
   fills come mostly on drops that keep dropping. The best version made $3 a
   day.

The bounce after a sharp drop is real. It is what market makers are paid for
standing in front of the selling, and taking it needs their queue position
and speed.

The minute-bar results were also flattered by a pricing bug: the Dukascopy
bars are split-adjusted, and the cent of spread was charged on those adjusted
prices. NVDA before its 2024 split was costed as if it cost $40 a share
instead of $400. It is fixed (`splits.py`); the fix made the bid-only results
look better, not worse, and the checks above still sink them.

## What this means for the Own-Drop Scalper

The [Own-Drop Scalper](own-drop/README.md) is the same rule. It showed $146 a
day at 2x on one month of one-minute bars.

Those bars are last-sale prices. A minute of hard selling ends on sales at
the bid, and the next minute opens nearer the offer, which is the same effect
as above. Its paper trail replays the same bars, so it cannot reveal this
either.

Treat its numbers as unproven, and do not put a funded account on it on this
evidence.

## What was tested overnight

About 1,700 books in all. The scripts are in `strategies/scalp/`, each with
its results in a JSON file of the same name.

- Four years of Dukascopy one-minute bars for 72 large US stocks, bid and
  offer, 1,004 sessions (`duka_stocks.py`, `panel.py`).
- Buying and selling sharp drops and rises that one name takes alone, in
  four windows, with 1-3 minute holds (`families.py`, `midfamilies.py`).
- Sector-relative drops, and laggards catching up with a big market minute
  (`families2.py`).
- Only the most volatile names of the moment (`volsubset.py`).
- A LightGBM model fitted on the first two years (`dropmodel.py`).
- Limit-order buying (`passive.py`).
- Names gapping on news in the first hour (`gappers.py`).
- Ten-second bars for 16 names over the last year (`fastdrop.py`,
  `latency.py`).
- One-second quotes around real trades (`onesec.py`).

Every book is a set of slots, one position per name, strongest signal
first, replayed from a table of every sharp one-minute move (`candidates.py`,
`book.py`). `realistic.py` puts the pieces together.

The earlier futures work reached the same place on the Micro Nasdaq
(`strategies/mnq/README.md`). Over six years, no MNQ setup held for 10
seconds to 10 minutes came close. The few that survived costs were small and
rare: going with a big day at 15:00, and the quiet-day afternoon breakout,
which has 66 trades in six years.

## What could change the answer

- **Real spreads, measured.** `spreads.py` sampled Nasdaq's live bid and
  offer for all 72 names from 09:37 to 09:57 on 2026-09-24 (52 quotes each,
  in `spreads.json`). This is probably Nasdaq's own book, so it is an upper
  bound on the best national quote: AAPL showed 7 cents where it usually
  trades a cent wide.
  - Mega caps quoted 1 to 3 bp (NVDA 1.4, AMZN 1.6, AAPL 2.1, MSFT 3.4).
  - The software mid caps the model favored quoted 25 to 45 bp (TWLO 43,
    TEAM 38, MDB 37, WDAY 33, ZS 29, SNOW 27).
  - Both are far more than the 3 to 4 bp midpoint bounce, so the verdict
    stands.
  - At midday (12:31 to 12:46) spreads were about half as wide: a median of
    4.6 bp across the names against 10.2 at the open, with MDB at 14 bp,
    TEAM 15 and TWLO 13. That is still several times the bounce.
- **The volatile names the one-month result came from.** MSTR, COIN, SOXL,
  SMCI, IONQ, RKLB and HOOD are not in the Dukascopy data. A free Alpaca
  account gives years of their minute bars and quotes.

  The key goes in the environment settings as an environment variable (for
  example ALPACA_API_KEY and ALPACA_SECRET_KEY), never in the chat. With it,
  the same mid-price test can be run on them. Expect the same result, since
  their spreads are wider too.
- **Longer holds.** Every edge found in this repository that survives costs
  holds for hours to days: the NQ 2x set, the funded day trades and the
  leveraged-ETF books. At three minutes, the moves a bot can collect are
  smaller than what it pays to trade them.

Backtests, not advice.
