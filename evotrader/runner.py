"""The backtest engine: run one compiled genome over one universe window.

Sequencing is strict so that results are honest:

    bar t close  ->  features observed  ->  rules evaluated  ->  orders queued
    bar t+1 open ->  orders fill (sells first, then buys)

Nothing a rule can see at bar ``t`` comes from bar ``t+1`` or later.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .broker import PaperBroker, Position
from .data import Bars, Universe
from .features import FeatureSet
from .genome import CompiledGenome, Genome, compile_genome
from .journal import Journal, Thought

NEVER = 9999
MAX_THOUGHTS = 300


@dataclass
class BacktestResult:
    genome_id: str
    journal: Journal
    final_equity: float
    starting_cash: float
    bars: int
    start_bar: int           # first bar the genome was allowed to trade on
    symbols: List[str]
    start_date: str
    end_date: str
    turnover: float          # gross traded / starting cash
    total_costs: float
    exposure: float          # average fraction of equity invested


def _portfolio_context(broker: PaperBroker, prices: Dict[str, float],
                       equity: float) -> Dict[str, float]:
    invested = broker.invested(prices)
    return {
        "cash_pct": broker.cash / equity if equity else 1.0,
        "gross_exposure": invested / equity if equity else 0.0,
        "position_count": float(len(broker.positions)),
        "portfolio_return": equity / broker.starting_cash - 1.0 if broker.starting_cash else 0.0,
        "portfolio_drawdown": broker.drawdown(prices),
    }


def _position_context(broker: PaperBroker, symbol: str, price: float, bar: int,
                      equity: float, last_exit_bar: Dict[str, int]) -> Dict[str, float]:
    pos = broker.positions.get(symbol)
    if pos is None:
        since = last_exit_bar.get(symbol)
        return {
            "in_position": 0.0, "bars_held": 0.0, "position_return": 0.0,
            "position_drawdown": 0.0, "position_weight": 0.0,
            "bars_since_exit": float(NEVER if since is None else bar - since),
        }
    return {
        "in_position": 1.0,
        "bars_held": float(bar - pos.entry_bar),
        "position_return": pos.unrealised_return(price),
        "position_drawdown": pos.drawdown(price),
        "position_weight": pos.value(price) / equity if equity else 0.0,
        "bars_since_exit": float(NEVER),
    }


def _risk_exit(pos, price: float, bar: int, risk) -> Optional[str]:
    """Hard guardrails, checked before the genome's own exit rules."""
    ret = pos.unrealised_return(price)
    if risk.stop_loss_pct > 0 and ret <= -risk.stop_loss_pct:
        return f"stop loss hit ({ret * 100:.1f}% <= -{risk.stop_loss_pct * 100:.1f}%)"
    if risk.take_profit_pct > 0 and ret >= risk.take_profit_pct:
        return f"take profit hit ({ret * 100:.1f}% >= {risk.take_profit_pct * 100:.1f}%)"
    if risk.trailing_stop_pct > 0 and pos.drawdown(price) <= -risk.trailing_stop_pct:
        return f"trailing stop hit ({pos.drawdown(price) * 100:.1f}%)"
    if risk.max_hold_bars > 0 and (bar - pos.entry_bar) >= risk.max_hold_bars:
        return f"max hold reached ({risk.max_hold_bars} bars)"
    return None


def _same_day_exit(pos, bar, i: int, risk) -> Tuple[float, str]:
    """Where a position bought at bar ``i``'s open leaves the market that day.

    Resting orders only: the stop if the day's low reaches it, else the target
    if the high does, else the close.  With both inside the day's range the
    order they traded in is unknown, and the stop is assumed to come first.
    """
    opened = float(bar.open[i])
    if risk.stop_loss_pct > 0:
        stop_px = pos.entry_price * (1.0 - risk.stop_loss_pct)
        if float(bar.low[i]) <= stop_px:
            return (min(stop_px, opened),
                    f"stop order hit intrabar (-{risk.stop_loss_pct * 100:.2f}% from entry)")
    if risk.take_profit_pct > 0:
        target_px = pos.entry_price * (1.0 + risk.take_profit_pct)
        if float(bar.high[i]) >= target_px:
            return (max(target_px, opened),
                    f"target order hit intrabar (+{risk.take_profit_pct * 100:.2f}% from entry)")
    return float(bar.close[i]), "flat at the close: same-day trade"


class _Carried:
    """The strategy's own book in carry mode: the positions it holds across
    days while the account itself is flat every night."""

    def __init__(self) -> None:
        self.positions: Dict[str, Position] = {}
        self.size: Dict[str, float] = {}       # share of buying power, bought back every open


def _run_carried(compiled: CompiledGenome, features: FeatureSet, broker: PaperBroker,
                 px_bars: Dict[str, Bars], first: int, *, leverage: float, day_stop: float,
                 day_stop_exit: bool, record_thoughts: bool) -> float:
    """The ``day_trade`` + ``carry`` loop.  Returns the average exposure of the
    carried book at the close (the account's own is always zero then)."""
    risk = compiled.risk
    symbols = features.symbols
    dates = features.dates
    n = len(dates)
    journal = broker.journal
    book = _Carried()
    last_exit_bar: Dict[str, int] = {}
    prev_snap: Dict[str, Dict[str, float]] = {}
    exposure_sum = 0.0
    exposure_n = 0

    def session(i: int) -> set:
        """Sell what the account bought at this bar's open: at the day's stop, else the close."""
        stopped = set()
        for sym in list(broker.positions):
            bar = px_bars[sym]
            stop_px = broker.positions[sym].entry_price * (1.0 - day_stop)
            if day_stop > 0 and float(bar.low[i]) <= stop_px:
                broker.sell(sym, min(stop_px, float(bar.open[i])), dates[i], i,
                            f"stop order hit intrabar (daily stop -{day_stop * 100:.2f}% from the open)")
                stopped.add(sym)
            else:
                broker.sell(sym, float(bar.close[i]), dates[i], i, "flat at the close: same-day trade")
        return stopped

    for i in range(first, n - 1):
        date = dates[i]
        out_today = set()
        for sym in session(i):
            if not day_stop_exit:
                continue                            # the day is capped; the position carries on
            book.positions.pop(sym, None)
            book.size.pop(sym, None)
            last_exit_bar[sym] = i
            out_today.add(sym)
        prices = {s: float(px_bars[s].close[i]) for s in symbols}
        equity = broker.mark(date, prices)          # flat: nothing is held overnight
        if equity <= 0:
            break
        for sym, vp in book.positions.items():
            vp.peak_price = max(vp.peak_price, prices[sym])
        invested = sum(vp.value(prices[s]) for s, vp in book.positions.items())
        exposure_sum += invested / equity
        exposure_n += 1
        pf = {"cash_pct": max(1.0 - invested / equity, 0.0), "gross_exposure": invested / equity,
              "position_count": float(len(book.positions)),
              "portfolio_return": equity / broker.starting_cash - 1.0 if broker.starting_cash else 0.0,
              "portfolio_drawdown": broker.drawdown(prices)}

        snaps: Dict[str, Dict[str, float]] = {}
        for sym in symbols:
            snap = features.snapshot(sym, i)
            snap.update(pf)
            snap.update(_position_context(book, sym, prices[sym], i, equity, last_exit_bar))
            snaps[sym] = snap

        # ---- the carried book's exits, decided at this close; the account is already flat
        for sym in list(book.positions):
            vp = book.positions[sym]
            cur = snaps[sym]
            prev = prev_snap.get(sym, cur)
            reason = _risk_exit(vp, prices[sym], i, risk)
            if reason is None and (i - vp.entry_bar) >= risk.min_hold_bars:
                for rule in compiled.exits:
                    if rule(cur, prev):
                        reason = f"exit rule: {rule.source}"
                        journal.record_hit(rule.source)
                        break
            if reason:
                del book.positions[sym]
                book.size.pop(sym, None)
                # counted from the bar the exit would have filled on in a
                # multi-day run, so a cooldown holds the same days out
                last_exit_bar[sym] = i + 1
                out_today.add(sym)
                if record_thoughts and len(journal.thoughts) < MAX_THOUGHTS:
                    journal.thoughts.append(Thought(
                        date=date, kind="exit", symbol=sym,
                        text=f"{reason}; the carried position ends at this close",
                        context={k: round(cur.get(k, 0.0), 4)
                                 for k in ("rsi14", "dist_sma200", "position_return", "atr_pct")}))

        # ---- new positions for the carried book: first matching rule wins
        opening: Dict[str, str] = {}
        gross = sum(book.size.values())
        for sym in symbols:
            if sym in book.positions or sym in out_today:
                continue
            if risk.cooldown_bars > 0:
                last = last_exit_bar.get(sym)
                if last is not None and (i - last) < risk.cooldown_bars:
                    continue
            cur = snaps[sym]
            prev = prev_snap.get(sym, cur)
            for rule, weight in compiled.entries:
                if not rule(cur, prev):
                    continue
                journal.record_hit(rule.source)
                frac = min(weight, risk.max_position_pct, risk.max_gross_exposure - gross)
                if len(book.size) >= risk.max_positions or \
                        frac * equity * leverage < broker.min_trade_value:
                    journal.rejected_entries += 1
                    break
                book.size[sym] = frac
                gross += frac
                opening[sym] = f"entry rule: {rule.source}"
                break

        # ---- the account buys the whole carried book at the next open
        j = i + 1
        for sym, frac in list(book.size.items()):
            reason = opening.get(sym, "carried: bought back at the open")
            if not broker.buy(sym, frac * equity * leverage, float(px_bars[sym].open[j]),
                              dates[j], j, reason, context=snaps[sym]):
                journal.rejected_entries += 1
                book.positions.pop(sym, None)
                book.size.pop(sym, None)
                continue
            if sym in opening:
                fill = broker.positions[sym]
                book.positions[sym] = Position(
                    symbol=sym, shares=fill.shares, entry_price=fill.entry_price,
                    entry_date=dates[j], entry_bar=j, entry_reason=reason,
                    peak_price=fill.entry_price)
                if record_thoughts and len(journal.thoughts) < MAX_THOUGHTS:
                    journal.thoughts.append(Thought(
                        date=dates[j], kind="entry", symbol=sym,
                        text=f"{reason}; held open to close each day until the strategy exits",
                        context={k: round(snaps[sym].get(k, 0.0), 4)
                                 for k in ("rsi14", "dist_sma200", "ret20", "atr_pct")}))
        prev_snap = snaps

    last = n - 1
    session(last)
    broker.mark(dates[last], {s: float(px_bars[s].close[last]) for s in symbols})
    return exposure_sum / exposure_n if exposure_n else 0.0


def run_backtest(compiled: CompiledGenome, universe: Universe, features: FeatureSet, *,
                 starting_cash: float = 100_000.0, commission_bps: float = 1.0,
                 slippage_bps: float = 5.0, record_thoughts: bool = True,
                 start_bar: Optional[int] = None, leverage: float = 1.0,
                 intrabar_stops: bool = False, day_trade: bool = False,
                 carry: bool = False, day_stop: float = 0.0, day_stop_exit: bool = True,
                 exec_bars: Optional[Dict[str, Bars]] = None,
                 slippage_by_symbol: Optional[Dict[str, float]] = None,
                 rank_entries_by: Optional[str] = None) -> BacktestResult:
    """Simulate one genome and return its journal plus summary statistics.

    ``leverage`` is the account's, not the genome's: a rule's weight is a share
    of buying power, so on a 2x futures account a 1.0 weight is twice equity in
    notional and a 0.5 weight is one times equity.

    ``intrabar_stops`` turns the stop loss into a resting stop order, as a
    futures trader would place one: it fires during any bar whose low reaches
    the stop, from the entry bar on, and fills at the stop price, or at the
    open when the bar gaps below it.  Off, the stop is checked on the close and
    filled at the next open like every other exit.

    ``day_trade`` makes every trade a same-session trade, as a prop firm that
    forbids holding overnight requires: a position bought at a bar's open is
    sold on that same bar, at its resting stop or target when the bar reaches
    one (see :func:`_same_day_exit`), else at the close.  Nothing is held when
    the rules are evaluated, so exit rules, holding limits and the trailing
    stop have nothing to act on.

    ``carry`` (with ``day_trade``) keeps the strategy's own position across
    days while the account is flat every night: the position is sold at each
    close and bought back at the next open for as long as the strategy would
    still hold it.  Its exit rules, stop, target, trailing stop and holding
    limit then act on that carried position at the close, measured from its
    first entry, and ``day_stop`` is a resting stop under each day's own entry.
    With ``day_stop_exit`` it ends the carried position; without, it only caps
    that day's loss and the position is bought back at the next open if the
    strategy still holds it.  The overnight gap is never held.

    ``exec_bars`` fills, stops and marks on other prices than the ones the
    features were built from, date for date: a futures strategy that reads the
    full Globex bar but trades only the stock market's session.

    ``slippage_by_symbol`` charges a symbol its own slippage instead of
    ``slippage_bps``: a scalper across many names pays each one's spread.

    ``rank_entries_by`` names a feature that decides who gets the risk budget
    when more symbols signal on a bar than it can take: the lowest value is
    bought first ("-name" for the highest).  By default symbols are visited in
    alphabetical order (and always in the carried day-trade mode).  A dip
    buyer ranks by how hard each name fell.
    """
    genome = compiled.genome
    risk = compiled.risk
    symbols = features.symbols
    dates = features.dates
    n = len(dates)
    journal = Journal()
    leverage = max(1.0, float(leverage))
    broker = PaperBroker(starting_cash, commission_bps=commission_bps,
                         slippage_bps=slippage_bps, journal=journal, leverage=leverage,
                         slippage_by_symbol=slippage_by_symbol)
    # A genome trades from the bar its own features are defined, not from the
    # slowest feature in the vocabulary — see FeatureSet.warmup_for.
    first = (features.warmup_for(compiled.feature_names()) if start_bar is None
             else max(start_bar, 1))
    if n - first < 5:
        first = max(n - 5, 1)

    px_bars = exec_bars if exec_bars is not None else universe.bars
    if day_trade and carry:
        exposure = _run_carried(compiled, features, broker, px_bars, first,
                                leverage=leverage, day_stop=day_stop,
                                day_stop_exit=day_stop_exit, record_thoughts=record_thoughts)
        last = n - 1
        return BacktestResult(
            genome_id=genome.id, journal=journal,
            final_equity=broker.equity({s: float(px_bars[s].close[last]) for s in symbols}),
            starting_cash=starting_cash, bars=max(n - first, 0), start_bar=first,
            symbols=list(symbols), start_date=dates[first] if first < n else "",
            end_date=dates[last] if n else "",
            turnover=broker.gross_traded / starting_cash if starting_cash else 0.0,
            total_costs=broker.total_costs, exposure=exposure)

    last_exit_bar: Dict[str, int] = {}
    prev_snap: Dict[str, Dict[str, float]] = {}
    exposure_sum = 0.0
    exposure_n = 0

    for i in range(first, n - 1):
        date = dates[i]
        stopped_now = set()
        if day_trade:
            for sym in list(broker.positions):
                px, why = _same_day_exit(broker.positions[sym], px_bars[sym], i, risk)
                broker.sell(sym, px, date, i, why)
                last_exit_bar[sym] = i
        elif intrabar_stops and risk.stop_loss_pct > 0:
            for sym in list(broker.positions):
                pos = broker.positions[sym]
                stop_px = pos.entry_price * (1.0 - risk.stop_loss_pct)
                bar = px_bars[sym]
                if float(bar.low[i]) <= stop_px:
                    opened = float(bar.open[i])
                    # traded down through the stop, or opened below it
                    px = stop_px if (i == pos.entry_bar or opened > stop_px) else opened
                    broker.sell(sym, px, date, i,
                                f"stop order hit intrabar (-{risk.stop_loss_pct * 100:.2f}% from entry)")
                    last_exit_bar[sym] = i
                    stopped_now.add(sym)
        prices = {s: float(px_bars[s].close[i]) for s in symbols}
        equity = broker.mark(date, prices)
        if equity <= 0:  # wiped out; nothing left to trade
            break
        exposure_sum += broker.invested(prices) / equity
        exposure_n += 1
        pf = _portfolio_context(broker, prices, equity)

        snaps: Dict[str, Dict[str, float]] = {}
        for sym in symbols:
            snap = features.snapshot(sym, i)
            snap.update(pf)
            snap.update(_position_context(broker, sym, prices[sym], i, equity, last_exit_bar))
            snaps[sym] = snap

        sells: List[Tuple[str, str]] = []
        buys: List[Tuple[str, float, str]] = []

        # ---- exits first: they free capital for the same bar's entries
        for sym in symbols:
            pos = broker.positions.get(sym)
            if pos is None:
                continue
            cur = snaps[sym]
            prev = prev_snap.get(sym, cur)
            reason = _risk_exit(pos, prices[sym], i, risk)
            if reason is None and (i - pos.entry_bar) >= risk.min_hold_bars:
                for rule in compiled.exits:
                    if rule(cur, prev):
                        reason = f"exit rule: {rule.source}"
                        journal.record_hit(rule.source)
                        break
            if reason:
                sells.append((sym, reason))

        # ---- entries: first matching rule wins, subject to the risk budget
        open_after_sells = len(broker.positions) - len(sells)
        invested_after = broker.invested(prices) - sum(
            broker.positions[s].value(prices[s]) for s, _ in sells)
        order = symbols
        if rank_entries_by:
            key, sign = rank_entries_by.lstrip("-"), (-1.0 if rank_entries_by.startswith("-") else 1.0)
            order = sorted(symbols, key=lambda s: sign * snaps[s].get(key, 0.0))
        for sym in order:
            if sym in broker.positions and sym not in {s for s, _ in sells}:
                continue
            if sym in {s for s, _ in sells} or sym in stopped_now:
                continue  # never re-enter on the same bar we exit
            if risk.cooldown_bars > 0:
                last = last_exit_bar.get(sym)
                if last is not None and (i - last) < risk.cooldown_bars:
                    continue
            cur = snaps[sym]
            prev = prev_snap.get(sym, cur)
            for rule, weight in compiled.entries:
                if not rule(cur, prev):
                    continue
                journal.record_hit(rule.source)
                if open_after_sells >= risk.max_positions:
                    journal.rejected_entries += 1
                    break
                target = min(weight, risk.max_position_pct) * equity * leverage
                headroom = risk.max_gross_exposure * equity * leverage - invested_after
                target = min(target, headroom)
                if target < broker.min_trade_value:
                    journal.rejected_entries += 1
                    break
                buys.append((sym, target, f"entry rule: {rule.source}"))
                open_after_sells += 1
                invested_after += target
                break

        # ---- execute at the next bar's open
        j = i + 1
        fill_date = dates[j]
        for sym, reason in sells:
            price = float(px_bars[sym].open[j])
            trade = broker.sell(sym, price, fill_date, j, reason, context=snaps[sym])
            if trade and record_thoughts and len(journal.thoughts) < MAX_THOUGHTS:
                journal.thoughts.append(Thought(
                    date=fill_date, kind="exit", symbol=sym,
                    text=f"{reason}; realised {trade.ret * 100:+.1f}% over {trade.bars_held} bars",
                    context={k: round(snaps[sym].get(k, 0.0), 4)
                             for k in ("rsi14", "dist_sma200", "position_return", "atr_pct")},
                ))
            last_exit_bar[sym] = j
        for sym, notional, reason in buys:
            price = float(px_bars[sym].open[j])
            if broker.buy(sym, notional, price, fill_date, j, reason, context=snaps[sym]):
                if record_thoughts and len(journal.thoughts) < MAX_THOUGHTS:
                    journal.thoughts.append(Thought(
                        date=fill_date, kind="entry", symbol=sym,
                        text=f"{reason}; sized {notional / equity:.0%} of equity in notional",
                        context={k: round(snaps[sym].get(k, 0.0), 4)
                                 for k in ("rsi14", "dist_sma200", "ret20", "atr_pct",
                                           "mkt_above_sma200")},
                    ))
            else:
                journal.rejected_entries += 1

        prev_snap = snaps

    # ---- close out at the final bar
    last = n - 1
    if day_trade:
        for sym in list(broker.positions):
            px, why = _same_day_exit(broker.positions[sym], px_bars[sym], last, risk)
            broker.sell(sym, px, dates[last], last, why)
    final_prices = {s: float(px_bars[s].close[last]) for s in symbols}
    broker.liquidate(final_prices, dates[last], last)
    final_equity = broker.mark(dates[last], final_prices)

    return BacktestResult(
        genome_id=genome.id,
        journal=journal,
        final_equity=final_equity,
        starting_cash=starting_cash,
        bars=max(n - first, 0),
        start_bar=first,
        symbols=list(symbols),
        start_date=dates[first] if first < n else "",
        end_date=dates[last] if n else "",
        turnover=broker.gross_traded / starting_cash if starting_cash else 0.0,
        total_costs=broker.total_costs,
        exposure=exposure_sum / exposure_n if exposure_n else 0.0,
    )


def backtest_genome(genome: Genome, universe: Universe, features: FeatureSet,
                    **kwargs) -> BacktestResult:
    """Compile then backtest — convenience wrapper."""
    return run_backtest(compile_genome(genome), universe, features, **kwargs)


def buy_and_hold(universe: Universe, features: FeatureSet, *,
                 starting_cash: float = 100_000.0,
                 start: Optional[int] = None) -> List[float]:
    """Equal-weight buy-and-hold equity curve over the same window, as the
    benchmark every genome is scored against.  ``start`` defaults to the
    global warm-up; pass a genome's own start bar to compare like with like."""
    symbols = features.symbols
    n = len(features.dates)
    start = features.warmup if start is None else max(int(start), 0)
    if start >= n - 1:
        return [starting_cash] * max(n - start, 1)
    per = starting_cash / len(symbols)
    shares = {s: per / float(universe.bars[s].close[start]) for s in symbols}
    return [sum(shares[s] * float(universe.bars[s].close[i]) for s in symbols)
            for i in range(start, n)]
