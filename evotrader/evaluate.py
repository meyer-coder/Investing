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
from .data import Universe, holdout_split, load_universe
from .evolution import Context, score_genome
from .features import build_features
from .fitness import Metrics
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
    def profitable(self) -> bool:
        m = self.metrics
        return m.trades >= 10 and m.total_return > 0 and m.profit_factor > 1.0


@dataclass
class YearRow:
    year: str
    ret: float          # equity at year end / equity at prior year end - 1
    trades: int
    win_rate: float
    pnl: float


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
    error: str = ""

    @property
    def profitable(self) -> bool:
        """Positive net return and a profit factor above 1 on every window."""
        return not self.error and bool(self.windows) and all(w.profitable for w in self.windows)


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
                   slippage_bps=cfg.slippage_bps, fitness=cfg.fitness)


def _by_year(genome: Genome, ctx: Context, report: StrategyReport) -> List[YearRow]:
    """One full-window backtest, then calendar-year buckets from the equity
    curve (returns) and the trade list (counts, by exit date).  Also records
    the best and worst trades, so gap risk is visible."""
    result = run_backtest(compile_genome(genome), ctx.train, ctx.train_features,
                          starting_cash=ctx.starting_cash, commission_bps=ctx.commission_bps,
                          slippage_bps=ctx.slippage_bps, record_thoughts=False)
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
    last_of_year: Dict[str, float] = {}
    order: List[str] = []
    for date, eq in zip(journal.equity_dates, journal.equity):
        year = date[:4]
        if year not in last_of_year:
            order.append(year)
        last_of_year[year] = eq
    rows: List[YearRow] = []
    prev = journal.equity[0]
    for year in order:
        trades = [t for t in journal.trades if t.exit_date[:4] == year]
        wins = sum(1 for t in trades if t.ret > 0)
        rows.append(YearRow(year=year, ret=last_of_year[year] / prev - 1.0 if prev else 0.0,
                            trades=len(trades), win_rate=wins / len(trades) if trades else 0.0,
                            pnl=sum(t.pnl for t in trades)))
        prev = last_of_year[year]
    return rows


def evaluate(genomes: Sequence[Genome], cfg: EvolutionConfig, *,
             by_year: bool = False) -> List[StrategyReport]:
    """Score each genome on the config's training and held-out windows."""
    universe = load_universe(cfg.symbols, cfg.start, cfg.end, offline=cfg.offline,
                             refresh=cfg.refresh_data)
    windows: List[tuple] = []
    if cfg.test_frac > 0:
        train, test = holdout_split(universe, cfg.test_frac)
        windows.append(("train", train))
        if len(test) > 60:
            windows.append(("held-out", test))
    else:
        windows.append(("full", universe))
    contexts = [(label, _context(u, cfg)) for label, u in windows]
    full_ctx = _context(universe, cfg) if by_year else None

    reports: List[StrategyReport] = []
    for genome in genomes:
        report = StrategyReport(genome=genome)
        try:
            for label, ctx in contexts:
                out = score_genome(genome, ctx)
                if out.error:
                    raise GenomeError(out.error)
                a, b = ctx.train.date_range()
                report.windows.append(WindowResult(label, a, b, out.metrics, out.score))
            if full_ctx is not None:
                report.years = _by_year(genome, full_ctx, report)
        except (GenomeError, ValueError) as exc:
            report.error = str(exc)
        reports.append(report)
    return reports


# ------------------------------------------------------------------ formatting

def _row(w: WindowResult) -> str:
    m = w.metrics
    return (f"{w.label:<9} {w.start}..{w.end}  ret {m.total_return * 100:+7.1f}%  "
            f"bh {m.benchmark_return * 100:+7.1f}%  sharpe {m.sharpe:5.2f}  "
            f"mdd {m.max_drawdown * 100:6.1f}%  trades {m.trades:4d}  win {m.win_rate * 100:3.0f}%  "
            f"pf {m.profit_factor:4.2f}  avg {m.avg_trade_return * 100:+5.2f}%/t  "
            f"hold {m.avg_bars_held:4.1f}b  score {w.score:+.3f}"
            f"{'' if w.profitable else '  <-- not profitable'}")


def format_text(reports: Sequence[StrategyReport]) -> str:
    lines: List[str] = []
    for r in reports:
        lines.append(r.genome.describe())
        if r.error:
            lines.append(f"  error: {r.error}")
        for w in r.windows:
            lines.append("  " + _row(w))
        if r.years:
            lines.append("  by year: " + "  ".join(
                f"{y.year} {y.ret * 100:+.0f}%/{y.trades}t" for y in r.years))
        if r.symbols:
            lines.append("  by symbol: " + "  ".join(
                f"{s.symbol} {s.trades}t {s.win_rate * 100:.0f}% {s.avg_ret * 100:+.2f}%"
                for s in r.symbols))
        lines.append(f"  verdict: {'PROFITABLE on every window' if r.profitable else 'not profitable'}")
        lines.append("")
    n_ok = sum(1 for r in reports if r.profitable)
    lines.append(f"{n_ok} of {len(reports)} strategies profitable on every window")
    return "\n".join(lines)


def format_markdown(reports: Sequence[StrategyReport], *, title: str = "Strategies",
                    cfg: Optional[EvolutionConfig] = None) -> str:
    out: List[str] = [f"# {title}", ""]
    if cfg is not None:
        out += [f"Universe: {', '.join(cfg.symbols)}; {cfg.start} to {cfg.end}; "
                f"held-out tail {cfg.test_frac:.0%}; commission {cfg.commission_bps:g} bp, "
                f"slippage {cfg.slippage_bps:g} bp per side; fills at the next open.", ""]
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
        out.append("| window | dates | return | buy & hold | sharpe | max dd | trades | win | profit factor | avg trade | avg hold | score |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for w in r.windows:
            m = w.metrics
            out.append(f"| {w.label} | {w.start} to {w.end} | {m.total_return * 100:+.1f}% | "
                       f"{m.benchmark_return * 100:+.1f}% | {m.sharpe:.2f} | "
                       f"{m.max_drawdown * 100:.1f}% | {m.trades} | {m.win_rate * 100:.0f}% | "
                       f"{m.profit_factor:.2f} | {m.avg_trade_return * 100:+.2f}% | "
                       f"{m.avg_bars_held:.1f} bars | {w.score:+.2f} |")
        out.append("")
        if r.years:
            out.append("| year | return | trades | win |")
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
        if r.worst:
            out.append("Worst trades over the full window, then best:")
            out.append("")
            for t in r.worst + r.best:
                out.append(f"- {t.symbol} {t.entry_date} to {t.exit_date}, {t.bars_held} bars, "
                           f"{t.ret * 100:+.1f}%: {t.exit_reason}")
            out.append("")
        out.append(f"Verdict: **{'profitable on every window' if r.profitable else 'not profitable'}**")
        out.append("")
    return "\n".join(out)
