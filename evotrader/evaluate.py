"""Score hand-written strategies: a JSON file of genomes over a config's windows.

The evolutionary loop writes genomes; this is the other direction — you (or
Claude, reading a leaderboard) write a genome by hand and ask how it would
have done on the training window, the held-out window, any other symbol set,
and year by year.  ``evotrader evaluate`` is the command-line face of it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .config import EvolutionConfig
from .data import Universe, date_cut, holdout_split, load_universe
from .evolution import Context, score_genome
from .features import build_features
from .fitness import Metrics, compute_metrics
from .genome import Genome, GenomeError, compile_genome
from .journal import Trade
from .runner import buy_and_hold, run_backtest


@dataclass
class WindowResult:
    label: str
    start: str
    end: str
    metrics: Metrics
    score: float

    @property
    def verdict(self) -> str:
        m = self.metrics
        if m.trades < 10:
            return f"too few trades ({m.trades})"
        return "profitable" if (m.total_return > 0 and m.profit_factor > 1.0) else "not profitable"

    @property
    def profitable(self) -> bool:
        return self.verdict == "profitable"


@dataclass
class YearRow:
    year: str
    ret: float          # equity at year end / equity at prior year end - 1
    trades: int
    win_rate: float
    pnl: float


@dataclass
class PeriodRow:
    """Stats over a trailing window of the full backtest, e.g. the last six months."""

    label: str
    start: str
    end: str
    metrics: Metrics


@dataclass
class DailyProfile:
    """The distribution of daily equity changes: what a funded account lives on."""

    label: str
    days: int
    active_share: float        # share of days with any P&L
    mean: float                # mean daily return over all days
    median_active: float       # median of days with P&L
    p10: float
    p90: float
    best: float
    worst: float
    share_below_2: float       # share of days worse than -2%
    share_below_4: float       # share of days worse than -4%


def daily_profile(equity: Sequence[float], label: str) -> Optional[DailyProfile]:
    import numpy as np
    e = np.asarray(equity, dtype=float)
    if e.size < 3:
        return None
    r = e[1:] / e[:-1] - 1.0
    active = r[np.abs(r) > 1e-9]
    return DailyProfile(
        label=label, days=int(r.size), active_share=float(active.size / r.size),
        mean=float(r.mean()), median_active=float(np.median(active)) if active.size else 0.0,
        p10=float(np.percentile(r, 10)), p90=float(np.percentile(r, 90)),
        best=float(r.max()), worst=float(r.min()),
        share_below_2=float((r < -0.02).mean()), share_below_4=float((r < -0.04).mean()))


@dataclass
class SymbolRow:
    symbol: str
    trades: int
    win_rate: float
    pnl: float
    avg_ret: float


@dataclass
class StrategyReport:
    genome: Genome
    windows: List[WindowResult] = field(default_factory=list)
    years: List[YearRow] = field(default_factory=list)
    best: List[Trade] = field(default_factory=list)     # over the full window
    worst: List[Trade] = field(default_factory=list)
    symbols: List[SymbolRow] = field(default_factory=list)
    periods: List[PeriodRow] = field(default_factory=list)  # --since windows
    empty_periods: List[str] = field(default_factory=list)  # --since dates with no bars yet
    daily: List[DailyProfile] = field(default_factory=list)  # --daily: full window, then recent
    recent: Optional[PeriodRow] = None                       # --recent window
    error: str = ""

    RECENT_MIN_TRADES = 5

    @property
    def profitable(self) -> bool:
        """With a recent window: positive with a profit factor above 1 there.
        Otherwise: positive with a profit factor above 1 on every window."""
        if self.error:
            return False
        if self.recent is not None:
            m = self.recent.metrics
            return (m.trades >= self.RECENT_MIN_TRADES and m.total_return > 0
                    and m.profit_factor > 1.0)
        return bool(self.windows) and all(w.profitable for w in self.windows)

    @property
    def verdict(self) -> str:
        if self.error:
            return "error"
        if self.recent is not None:
            m = self.recent.metrics
            span = f"over the {self.recent.label} ({self.recent.start}..{self.recent.end})"
            if m.trades < self.RECENT_MIN_TRADES:
                return f"too few trades {span}: {m.trades}"
            return ("PROFITABLE " if self.profitable else "not profitable ") + span
        return "PROFITABLE on every window" if self.profitable else "not profitable"



def load_genomes(path: str) -> List[Genome]:
    """A JSON list of genome objects, or an object with a ``genomes`` list."""
    with open(path) as fh:
        raw = json.load(fh)
    items = raw.get("genomes", []) if isinstance(raw, dict) else raw
    out: List[Genome] = []
    for item in items:
        g = Genome.from_dict(item)
        compile_genome(g)          # fail loudly on a bad rule, before any backtest
        out.append(g)
    return out


def _context(universe: Universe, cfg: EvolutionConfig) -> Context:
    features = build_features(universe)
    return Context(train=universe, train_features=features,
                   train_benchmark=buy_and_hold(universe, features,
                                                starting_cash=cfg.starting_cash),
                   test=None, test_features=None, test_benchmark=None,
                   starting_cash=cfg.starting_cash, commission_bps=cfg.commission_bps,
                   slippage_bps=cfg.slippage_bps, fitness=cfg.fitness,
                   leverage=cfg.leverage)


def _held_out_context(universe: Universe, cut: int, cfg: EvolutionConfig) -> Context:
    """The whole series, traded from ``cut``: warm indicators on the first day."""
    features = build_features(universe)
    return Context(train=universe, train_features=features, train_benchmark=[],
                   test=universe, test_features=features,
                   test_benchmark=buy_and_hold(universe, features,
                                               starting_cash=cfg.starting_cash, start=cut),
                   starting_cash=cfg.starting_cash, commission_bps=cfg.commission_bps,
                   slippage_bps=cfg.slippage_bps, fitness=cfg.fitness,
                   leverage=cfg.leverage, test_start_bar=cut)


def _period(journal, start: str, cfg: EvolutionConfig) -> Optional[PeriodRow]:
    """Metrics from the equity curve and trades on or after ``start``."""
    dates = journal.equity_dates
    idx = [i for i, d in enumerate(dates) if d >= start]
    if len(idx) < 2:
        return None
    first = max(idx[0] - 1, 0)                     # the bar before, so the first return counts
    equity = journal.equity[first:]
    trades = [t for t in journal.trades if t.exit_date >= start]
    m = compute_metrics(equity, trades, exposure=0.0)
    return PeriodRow(f"since {start}", dates[first], dates[-1], m)


def _by_year(genome: Genome, ctx: Context, report: StrategyReport,
             since: Sequence[str] = (), recent_bars: int = 0,
             monthly: bool = False, daily: bool = False) -> List[YearRow]:
    """One full-window backtest, then calendar-year buckets from the equity
    curve (returns) and the trade list (counts, by exit date).  Also records
    the best and worst trades, so gap risk is visible."""
    result = run_backtest(compile_genome(genome), ctx.train, ctx.train_features,
                          starting_cash=ctx.starting_cash, commission_bps=ctx.commission_bps,
                          slippage_bps=ctx.slippage_bps, record_thoughts=False,
                          leverage=ctx.leverage)
    journal = result.journal
    report.best = journal.best_trades(3)
    report.worst = journal.worst_trades(3)
    by_symbol: Dict[str, List[Trade]] = {}
    for t in journal.trades:
        by_symbol.setdefault(t.symbol, []).append(t)
    report.symbols = [
        SymbolRow(sym, len(ts), sum(1 for t in ts if t.ret > 0) / len(ts),
                  sum(t.pnl for t in ts), sum(t.ret for t in ts) / len(ts))
        for sym, ts in sorted(by_symbol.items(), key=lambda kv: -sum(t.pnl for t in kv[1]))]
    if not journal.equity:
        return []
    for start in since:
        row = _period(journal, start, ctx_cfg(ctx))
        if row is not None:
            report.periods.append(row)
        else:
            report.empty_periods.append(start)
    if recent_bars > 0:
        dates = journal.equity_dates
        start = dates[-recent_bars] if len(dates) > recent_bars else dates[0]
        row = _period(journal, start, ctx_cfg(ctx))
        if row is not None:
            row.label = f"last {recent_bars} bars"
            report.recent = row
    if daily:
        full = daily_profile(journal.equity, "full window")
        if full is not None:
            report.daily.append(full)
        if recent_bars > 0 and len(journal.equity) > recent_bars + 1:
            tail = daily_profile(journal.equity[-recent_bars - 1:], f"last {recent_bars} bars")
            if tail is not None:
                report.daily.append(tail)
    width = 7 if monthly else 4                  # YYYY-MM or YYYY
    last_of_year: Dict[str, float] = {}
    order: List[str] = []
    for date, eq in zip(journal.equity_dates, journal.equity):
        year = date[:width]
        if year not in last_of_year:
            order.append(year)
        last_of_year[year] = eq
    rows: List[YearRow] = []
    prev = journal.equity[0]
    for year in order:
        trades = [t for t in journal.trades if t.exit_date[:width] == year]
        wins = sum(1 for t in trades if t.ret > 0)
        rows.append(YearRow(year=year, ret=last_of_year[year] / prev - 1.0 if prev else 0.0,
                            trades=len(trades), win_rate=wins / len(trades) if trades else 0.0,
                            pnl=sum(t.pnl for t in trades)))
        prev = last_of_year[year]
    return rows


def ctx_cfg(ctx: Context) -> EvolutionConfig:
    """The parts of a Context that period stats might need (costs)."""
    return EvolutionConfig(starting_cash=ctx.starting_cash, commission_bps=ctx.commission_bps,
                           slippage_bps=ctx.slippage_bps)


def evaluate(genomes: Sequence[Genome], cfg: EvolutionConfig, *,
             by_year: bool = False, since: Sequence[str] = (),
             recent_bars: int = 0, by_month: bool = False,
             daily: bool = False) -> List[StrategyReport]:
    """Score each genome on the config's training and held-out windows.
    ``since`` dates add trailing-window rows (return, trades, worst day...)
    from one full-window backtest.  ``recent_bars`` adds the trailing window
    that the verdict and the ranking are then based on: the last six months
    rather than the whole history."""
    universe = load_universe(cfg.symbols, cfg.start, cfg.end, offline=cfg.offline,
                             refresh=cfg.refresh_data)
    # (label, context, window): "train" windows are scored as a whole,
    # "test" windows from the context's test_start_bar on.
    contexts: List[tuple] = []
    if cfg.test_start:
        cut = date_cut(universe, cfg.test_start)
        if cut > 60:
            contexts.append(("train", _context(universe.slice(0, cut), cfg), "train"))
        if len(universe) - cut > 5:
            contexts.append(("held-out", _held_out_context(universe, cut, cfg), "test"))
    elif cfg.test_frac > 0:
        train, test = holdout_split(universe, cfg.test_frac)
        contexts.append(("train", _context(train, cfg), "train"))
        if len(test) > 60:
            contexts.append(("held-out", _context(test, cfg), "train"))
    else:
        contexts.append(("full", _context(universe, cfg), "train"))
    full_ctx = _context(universe, cfg) if (by_year or by_month or since or recent_bars > 0
                                          or daily) else None

    reports: List[StrategyReport] = []
    for genome in genomes:
        report = StrategyReport(genome=genome)
        try:
            for label, ctx, window in contexts:
                out = score_genome(genome, ctx, window=window)
                if out.error:
                    raise GenomeError(out.error)
                if window == "test" and ctx.test_start_bar is not None:
                    a, b = ctx.test.calendar[ctx.test_start_bar], ctx.test.calendar[-1]
                else:
                    a, b = ctx.train.date_range()
                report.windows.append(WindowResult(label, a, b, out.metrics, out.score))
            if full_ctx is not None:
                years = _by_year(genome, full_ctx, report, since=since, recent_bars=recent_bars,
                                 monthly=by_month, daily=daily)
                report.years = years if (by_year or by_month) else []
        except (GenomeError, ValueError) as exc:
            report.error = str(exc)
        reports.append(report)
    if recent_bars > 0:
        # rank by the recent window: what works now comes first, and a strategy
        # that barely traded there goes last whatever its return says
        def key(r):
            m = r.recent.metrics if r.recent else None
            thin = m is None or m.trades < StrategyReport.RECENT_MIN_TRADES
            return (r.recent is None, thin, -(m.total_return if m else 0.0))
        reports.sort(key=key)
    return reports


def parse_recent(text: str) -> int:
    """'6m' -> 126 bars, '3m' -> 63, '1y' -> 252, '2w' -> 10, '90' -> 90."""
    t = text.strip().lower()
    if t.isdigit():
        return int(t)
    units = {"w": 5, "m": 21, "y": 252}
    if t and t[-1] in units and t[:-1].isdigit():
        return int(t[:-1]) * units[t[-1]]
    raise ValueError(f"cannot parse a bar count from {text!r}; use e.g. 6m, 3m, 1y or 126")


# ------------------------------------------------------------------- signals

@dataclass
class Signal:
    """An entry rule that is true on the latest bar: a buy at the next open."""

    genome: str
    symbol: str
    date: str
    rule: str
    weight: float
    context: Dict[str, float]
    notional: float = 0.0      # weight x account leverage: notional per unit of equity
    price: float = 0.0         # the signal bar's close


_FLAT = {"in_position": 0.0, "bars_held": 0.0, "position_return": 0.0,
         "position_drawdown": 0.0, "position_weight": 0.0, "cash_pct": 1.0,
         "gross_exposure": 0.0, "position_count": 0.0, "bars_since_exit": 9999.0,
         "portfolio_return": 0.0, "portfolio_drawdown": 0.0}


def latest_signals(genomes: Sequence[Genome], cfg: EvolutionConfig
                   ) -> tuple:
    """Evaluate every genome's entry rules on the last bar of the universe,
    as if flat.  Returns ``(date, signals, skipped)`` where ``skipped`` names
    genomes whose features are not yet defined on that bar."""
    universe = load_universe(cfg.symbols, cfg.start, cfg.end, offline=cfg.offline,
                             refresh=cfg.refresh_data)
    features = build_features(universe)
    i = len(features.dates) - 1
    date = features.dates[i]
    signals: List[Signal] = []
    skipped: List[str] = []
    for genome in genomes:
        compiled = compile_genome(genome)
        names = compiled.feature_names()
        if i < 1 or not features.defined_at(names, i):
            skipped.append(f"{genome.name}: its features are not yet defined on {date}")
            continue
        for sym in features.symbols:
            cur = features.snapshot(sym, i)
            cur.update(_FLAT)
            prev = features.snapshot(sym, i - 1)
            prev.update(_FLAT)
            for rule, weight in compiled.entries:
                if rule(cur, prev):
                    context = {k: round(cur[k], 4) for k in sorted(rule.features) if k in cur}
                    # the broker caps a rule's weight at the genome's position limit
                    size = min(weight, compiled.risk.max_position_pct)
                    signals.append(Signal(genome.name, sym, date, rule.source, size, context,
                                          notional=size * cfg.leverage,
                                          price=float(universe.bars[sym].close[i])))
                    break
    return date, signals, skipped


#: Dollars per index point for micro and full-size contracts, by futures root.
CONTRACT_POINT_VALUE: Dict[str, tuple] = {
    "NQ": (("MNQ", 2.0), ("NQ", 20.0)), "MNQ": (("MNQ", 2.0), ("NQ", 20.0)),
    "ES": (("MES", 5.0), ("ES", 50.0)), "MES": (("MES", 5.0), ("ES", 50.0)),
    "RTY": (("M2K", 5.0), ("RTY", 50.0)), "M2K": (("M2K", 5.0), ("RTY", 50.0)),
    "YM": (("MYM", 0.5), ("YM", 5.0)), "MYM": (("MYM", 0.5), ("YM", 5.0)),
}


def contracts_for(symbol: str, notional: float, price: float) -> str:
    """'1.61 MNQ (0.16 NQ)' for a futures symbol, '' otherwise."""
    root = symbol.upper().split(":")[-1].rstrip("!").rstrip("0123456789")
    sizes = CONTRACT_POINT_VALUE.get(root)
    if not sizes or price <= 0 or notional <= 0:
        return ""
    return " (".join(f"{notional / (price * mult):.2f} {name}" for name, mult in sizes) + ")"


def format_signals(date: str, signals: Sequence[Signal], skipped: Sequence[str],
                   genomes: Sequence[Genome], symbols: Sequence[str], *,
                   account: float = 0.0) -> str:
    lines = [f"latest bar {date} across {', '.join(symbols)}",
             "(a signal is a buy at the NEXT open; if this bar is today's, it is "
             "incomplete until the close)", ""]
    by_genome: Dict[str, List[Signal]] = {}
    for s in signals:
        by_genome.setdefault(s.genome, []).append(s)
    for g in genomes:
        hits = by_genome.get(g.name, [])
        if hits:
            lines.append(f"{g.name}:")
            for s in hits:
                ctx = " ".join(f"{k}={v:g}" for k, v in s.context.items())
                size = f"{s.weight:.0%} of equity"
                if s.notional and abs(s.notional - s.weight) > 1e-9:
                    size = f"{s.weight:.0%} of buying power = {s.notional:.2f}x equity in notional"
                if account > 0:
                    held = contracts_for(s.symbol, s.notional * account, s.price)
                    if held:
                        size += f", {held} on ${account:,.0f}"
                lines.append(f"  BUY {s.symbol:<6} {size}   [{s.rule}]   {ctx}")
        else:
            lines.append(f"{g.name}: no signal")
    for note in skipped:
        lines.append(f"skipped {note}")
    return "\n".join(lines)


# ------------------------------------------------------------------ formatting

def _row(w: WindowResult) -> str:
    m = w.metrics
    return (f"{w.label:<9} {w.start}..{w.end}  ret {m.total_return * 100:+7.1f}%  "
            f"bh {m.benchmark_return * 100:+7.1f}%  sharpe {m.sharpe:5.2f}  "
            f"mdd {m.max_drawdown * 100:6.1f}%  trades {m.trades:4d}  win {m.win_rate * 100:3.0f}%  "
            f"pf {m.profit_factor:4.2f}  avg {m.avg_trade_return * 100:+5.2f}%/t  "
            f"hold {m.avg_bars_held:4.1f}b  worst day {m.worst_day * 100:5.1f}%  score {w.score:+.3f}"
            f"{'' if w.profitable else '  <-- ' + w.verdict}")


def _usd(frac: float, account: float) -> str:
    v = frac * account
    return f"{'-' if v < 0 else '+'}${abs(v):,.0f}"


def format_text(reports: Sequence[StrategyReport], *, account: float = 0.0) -> str:
    """``account``: show the daily profile in dollars on an account this size."""
    lines: List[str] = []
    for r in reports:
        lines.append(r.genome.describe())
        if r.error:
            lines.append(f"  error: {r.error}")
        for w in r.windows:
            lines.append("  " + _row(w))
        if r.years:
            label = "by month" if len(r.years[0].year) == 7 else "by year"
            lines.append(f"  {label}: " + "  ".join(
                f"{y.year} {y.ret * 100:+.1f}%/{y.trades}t" for y in r.years))
        for p in ([r.recent] if r.recent else []) + list(r.periods):
            m = p.metrics
            lines.append(f"  {p.label} ({p.start}..{p.end}): ret {m.total_return * 100:+6.1f}%  "
                         f"trades {m.trades:3d}  win {m.win_rate * 100:3.0f}%  pf {m.profit_factor:4.2f}  "
                         f"avg {m.avg_trade_return * 100:+5.2f}%/t  mdd {m.max_drawdown * 100:5.1f}%  "
                         f"worst day {m.worst_day * 100:5.1f}%")
        for d in r.daily:
            usd = (f" = {_usd(d.mean, account)}/day on ${account:,.0f} "
                   f"(best {_usd(d.best, account)}, worst {_usd(d.worst, account)})"
                   if account > 0 else "")
            lines.append(f"  daily ({d.label}): {d.days} days, {d.active_share * 100:.0f}% with P&L; "
                         f"mean {d.mean * 100:+.2f}%/day; median active day {d.median_active * 100:+.2f}%; "
                         f"p10 {d.p10 * 100:+.2f}% p90 {d.p90 * 100:+.2f}%; best {d.best * 100:+.1f}% "
                         f"worst {d.worst * 100:+.1f}%; days below -2%: {d.share_below_2 * 100:.1f}%, "
                         f"below -4%: {d.share_below_4 * 100:.1f}%{usd}")
        for start in r.empty_periods:
            lines.append(f"  since {start}: no completed bars on or after this date yet "
                         f"(data ends {r.windows[-1].end if r.windows else '?'}); nothing out of sample so far")
        if r.symbols:
            lines.append("  by symbol: " + "  ".join(
                f"{s.symbol} {s.trades}t {s.win_rate * 100:.0f}% {s.avg_ret * 100:+.2f}%"
                for s in r.symbols))
        lines.append(f"  verdict: {r.verdict}")
        lines.append("")
    n_ok = sum(1 for r in reports if r.profitable)
    recent = next((r.recent for r in reports if r.recent is not None), None)
    where = f"over the {recent.label}" if recent is not None else "on every window"
    lines.append(f"{n_ok} of {len(reports)} strategies profitable {where}")
    return "\n".join(lines)


def format_markdown(reports: Sequence[StrategyReport], *, title: str = "Strategies",
                    cfg: Optional[EvolutionConfig] = None) -> str:
    out: List[str] = [f"# {title}", ""]
    if cfg is not None:
        held = (f"held out from {cfg.test_start}" if cfg.test_start
                else f"held-out tail {cfg.test_frac:.0%}")
        lev = f"; account leverage {cfg.leverage:g}x" if cfg.leverage != 1.0 else ""
        out += [f"Universe: {', '.join(cfg.symbols)}; {cfg.start} to {cfg.end}; "
                f"{held}; commission {cfg.commission_bps:g} bp, "
                f"slippage {cfg.slippage_bps:g} bp per side; fills at the next open{lev}; "
                f"starting equity ${cfg.starting_cash:,.0f}.", ""]
    for r in reports:
        g = r.genome
        out.append(f"## {g.name}")
        out.append("")
        if g.thesis:
            out.append(f"*{g.thesis}*")
            out.append("")
        out.append("```")
        out.append(g.describe())
        out.append("```")
        out.append("")
        if r.error:
            out.append(f"Error: {r.error}")
            out.append("")
            continue
        out.append("| window | dates | return | buy & hold | sharpe | max dd | worst day | trades | win | profit factor | avg trade | avg hold | score |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for w in r.windows:
            m = w.metrics
            out.append(f"| {w.label} | {w.start} to {w.end} | {m.total_return * 100:+.1f}% | "
                       f"{m.benchmark_return * 100:+.1f}% | {m.sharpe:.2f} | "
                       f"{m.max_drawdown * 100:.1f}% | {m.worst_day * 100:.1f}% | {m.trades} | "
                       f"{m.win_rate * 100:.0f}% | "
                       f"{m.profit_factor:.2f} | {m.avg_trade_return * 100:+.2f}% | "
                       f"{m.avg_bars_held:.1f} bars | {w.score:+.2f} |")
        out.append("")
        periods = ([r.recent] if r.recent else []) + list(r.periods)
        if periods:
            out.append("| period | dates | return | trades | win | profit factor | avg trade | max dd | worst day |")
            out.append("|---|---|---|---|---|---|---|---|---|")
            for p in periods:
                m = p.metrics
                out.append(f"| {p.label} | {p.start} to {p.end} | {m.total_return * 100:+.1f}% | "
                           f"{m.trades} | {m.win_rate * 100:.0f}% | {m.profit_factor:.2f} | "
                           f"{m.avg_trade_return * 100:+.2f}% | {m.max_drawdown * 100:.1f}% | "
                           f"{m.worst_day * 100:.1f}% |")
            out.append("")
        if r.years:
            out.append("| period | return | trades | win |")
            out.append("|---|---|---|---|")
            for y in r.years:
                out.append(f"| {y.year} | {y.ret * 100:+.1f}% | {y.trades} | {y.win_rate * 100:.0f}% |")
            out.append("")
        if r.symbols:
            out.append("| symbol | trades | win | avg trade | P&L |")
            out.append("|---|---|---|---|---|")
            for s in r.symbols:
                out.append(f"| {s.symbol} | {s.trades} | {s.win_rate * 100:.0f}% | "
                           f"{s.avg_ret * 100:+.2f}% | {s.pnl:+,.0f} |")
            out.append("")
        if r.daily:
            acct = cfg.starting_cash if cfg is not None else 0.0
            usd_head = f" | mean day on ${acct:,.0f}" if acct else ""
            out.append("| daily profile | days | with P&L | mean day | median active day | p10 | p90 | best | worst | days below -2% | below -4%" + usd_head + " |")
            out.append("|---|---|---|---|---|---|---|---|---|---|---|" + ("---|" if acct else ""))
            for d in r.daily:
                usd_cell = f" | {_usd(d.mean, acct)}" if acct else ""
                out.append(f"| {d.label} | {d.days} | {d.active_share * 100:.0f}% | {d.mean * 100:+.2f}% | "
                           f"{d.median_active * 100:+.2f}% | {d.p10 * 100:+.2f}% | {d.p90 * 100:+.2f}% | "
                           f"{d.best * 100:+.1f}% | {d.worst * 100:+.1f}% | {d.share_below_2 * 100:.1f}% | "
                           f"{d.share_below_4 * 100:.1f}%{usd_cell} |")
            out.append("")
        for start in r.empty_periods:
            out.append(f"Since {start}: no completed bars on or after this date yet; nothing out of sample so far.")
            out.append("")
        if r.worst:
            out.append("Worst trades over the full window, then best:")
            out.append("")
            for t in r.worst + r.best:
                out.append(f"- {t.symbol} {t.entry_date} to {t.exit_date}, {t.bars_held} bars, "
                           f"{t.ret * 100:+.1f}%: {t.exit_reason}")
            out.append("")
        out.append(f"Verdict: **{r.verdict}**")
        out.append("")
    return "\n".join(out)
