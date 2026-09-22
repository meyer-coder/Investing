# TradingView versions

Pine Script v6 strategies for the three strategies with the strongest
evidence. They reproduce the Python backtest's mechanics: daily bars, the
signal read on the close, the fill at the next open, stops and targets
checked on the close rather than intrabar, 1 bp commission and one tick of
slippage.

| file | strategy | file sizing |
|---|---|---|
| `capitulation_close.pine` | Capitulation Close | 25% of equity |
| `two_red_days.pine` | Two Red Days (evolved) | 20% |
| `combo_all_five.pine` | Combo: All Five Setups | 20% |

## Setting them up

1. Open a **daily** chart of the fund or index. Pine > New > paste the file,
   Add to chart.
2. On a leveraged fund chart (TQQQ, SOXL, MUU, RIOX) leave *Threshold scale*
   at 1. On **NQ1!, MNQ1!, NDX or QQQ** set it to **0.333**: the rules were
   tuned on 3x funds, so a 4% fund move is a 1.33% index move.
3. On a futures chart, in Properties set the order size in **contracts** (1
   MNQ), not percent of equity; see the sizing note below.
4. Strategy Tester shows the trade list; compare it with
   `evotrader evaluate ... --by-month` on the same symbol and window. Small
   differences come from TradingView's unadjusted prices versus the
   backtest's split- and dividend-adjusted series, and from slippage.
5. To forward-test, add an alert on the strategy's "buy at next open"
   condition, once per bar close. Every alert is a buy at the next open;
   the exits are mechanical (a close 3% above entry, or two bars, or the
   stop), so they can be managed by hand or with a second alert.

## What a chart cannot reproduce

A Pine strategy holds one symbol. The Python backtest runs each strategy as
a book across several funds with several slots, so a chart's equity curve
is one leg of that book. Run one chart per fund and read them together.

## Sizing on a $25,000 futures account

One MNQ is about $2 x the index, roughly $58,000 of Nasdaq exposure at an
index near 29,000: 2.3 times the account. The backtests size a 3x fund at
25% of equity, which is 75% of the account in index exposure, so one MNQ is
about three times the tested size. A tested worst day of -5% becomes -15%,
which breaks a 4% drawdown limit in one session. Either trade the rules on
a larger account, or on a CFD account with fractional index lots, or accept
that a single MNQ carries three times the tested risk.
