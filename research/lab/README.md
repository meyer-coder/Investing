# Strategy lab

Build strategies from a fixed card, test them on 13 years of one-minute
data, and log every one.

- The code is in [`stratlab/`](../../stratlab).
- Results are in [`findings.md`](findings.md).
- The full ranked list is in [`leaderboard.md`](leaderboard.md).

```bash
python -m stratlab families                                   # the signals and filters available
python -m stratlab batch research/lab/batches/02-confluence-nas100.json
python -m stratlab board --top 30                             # the leaderboard
python -m stratlab show L0391                                 # one card, in words, with its results
```

## The card

Every strategy is written as the same card:

| Field | Options |
|---|---|
| Signal family + settings | `volume_spike_breakout`, `range_spike_breakout`, `donchian_break`, `ema_cross`, `ema_ribbon`, `macd_cross`, `zscore_reversion`, `bollinger_reclaim`, `vwap_band_reversion`, `sweep_reclaim`, `opening_range_breakout`, `asian_range_break`, `round_number`, `gap_fade`, `noise_breakout`, `random_control` |
| Market | NAS100, US500, US30, US2000, XAUUSD, USOIL, NATGAS, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USTBOND |
| Timeframe | 1, 3, 5, 15, 30 or 60 minutes |
| Session | `asia`, `london`, `ny_am`, `ny_pm`, `ny`, `ldn_ny_am`, `all` |
| Direction | `both`, `long`, `short` |
| Entry | `market`; `limit_pullback` (frac, cancel_bars); `stop` (ticks, cancel_bars) |
| Stop | `atr` (mult, n); `signal_bar` (ticks); `pct` |
| Target | `r` (mult); `atr` (mult, n); `level` (the family's own level); `none` |
| Trailing | `none`; `breakeven` (at_r); `atr` (mult, n, after_r) |
| Partial | `none`; `take` (frac, at_r) |
| Time stop | `time_stop_bars` (a number of candles) |
| Max trades a day | `max_trades_day` |
| Filters (confluences) | `trend_ema`, `vwap_side`, `atr_regime`, `rel_volume`, `prior_day`, `weekday`, `time_window` |
| Daily flat | `flat`, at 16:10 ET or earlier (Topstep's rule) |

A batch file sets the fields shared by all its cards (`base`), lists
`variants`, and gives a `grid` to cross them with. See
[`batches/`](batches).

## How a card is tested

**The log comes first.** Every card is written to `log.jsonl` before it
runs. The log is therefore also the count of everything ever tried, and
that count is what "would pass by luck" is measured against. A card that is
already in the log keeps its ID. If its results came from an older engine
version, it is tested again but not counted twice.

**Random controls.** Every batch includes random-control cards: a coin
decides when and which way to trade. They share the batch's market,
candles, session, entry and exits, trade about as often as the batch's
median card, and are ranked alongside the real cards. Controls matter
because backtests have biases that have nothing to do with the signal (see
Fills below), and the controls carry the same biases.

**Three periods, fixed in advance:**

1. **Search, 2013-2019.** A card passes with all of the following:
   - 100+ trades;
   - net R a trade above zero;
   - t ≥ 2;
   - beats 95% of its random controls.
2. **Confirm, 2020-2022.** A card is confirmed if it:
   - stays above zero;
   - beats 90% of 2,000 random sign flips of its own trades;
   - beats 90% of its controls again.
3. **Final, 2023-2026.** Reported, never used to choose.

**Fills,** worked on one-minute bars:
- **Signals:** known at the candle's close.
- **Market entry:** fills at the next minute's open.
- **Limit and stop entries:** fill when a minute trades through the price.
  If the order is already marketable when placed, it fills at that open.
- **Favourable fills are never better than the order's price.** This covers
  limit entries, targets and partials.
- **A stop that is gapped fills at the open,** which is worse.
- **A minute that touches both the stop and the target counts as the stop.**
  After a limit or stop fill, only the stop is checked for the rest of that
  minute.
- **No stop is closer than 4 ticks.**
- **Costs:** the micro contract's commission plus a tick of slippage each
  way.

**Checks on the engine** (`tests/test_stratlab.py`):
- the fill rules;
- trailing stops, partials, time stops and daily limits;
- random entries on a random walk break even before costs, with both market
  and limit orders. This check caught two fill bugs while the lab was being
  built.

## Data checks

The prices are Dukascopy's one-minute CFDs. Three checks were added after
random entries showed losses that could not be real.

1. **Stale overnight quotes.** On some days the 09:30 open is more than 10
   bp from the 09:29 close. The Nasdaq CFD did this on 12% of 2013 days: it
   held still overnight and jumped at the cash open. Those days are skipped.
2. **Frozen day-session prices.** Some days have 10+ minutes in a row of an
   unchanged price inside 09:30-16:00. The index CFDs did this on most 2013
   days and half of 2014. Those days are skipped.
3. **Frozen overnight prices.** The same check is applied to 18:00-09:30,
   but only for strategies that trade before 09:30.

What the data can't do:
- **Volume** is the CFD's quote activity, not exchange volume.
- **Crude and gas** are back-adjusted for contract rolls.
