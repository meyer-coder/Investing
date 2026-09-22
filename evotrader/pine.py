"""Translate a genome into a TradingView Pine Script v6 strategy.

The rules are emitted from the parsed rule tree, so every operator keeps the
engine's meaning: ``prev(x)`` is one bar back however deeply it is nested,
``cross_above(a, b)`` compares this bar with the previous one, division by zero
is zero.  Each feature has a Pine definition that reproduces evotrader's own
formula (sample standard deviation for the bands and volatility, Wilder RSI and
ATR, a close-based 52-week range, calendar days from the trading day).  The
order mechanics are the engine's: decide on the close, fill at the next open,
risk exits checked on the close, no re-entry on the bar of an exit, cooldown
counted from the exit fill.

Daily bars only: the intraday session features have no daily definition.
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .dsl import Binary, Call, Const, Name, Node, Unary, parse
from .genome import Genome

# feature -> (Pine definition, features it depends on).  "{x}" is f_x.
_DEFS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "ret1": ("close / close[1] - 1", ()),
    "ret5": ("close / close[5] - 1", ()),
    "ret20": ("close / close[20] - 1", ()),
    "ret60": ("close / close[60] - 1", ()),
    "sma10": ("ta.sma(close, 10)", ()),
    "sma20": ("ta.sma(close, 20)", ()),
    "sma50": ("ta.sma(close, 50)", ()),
    "sma200": ("ta.sma(close, 200)", ()),
    "ema12": ("ta.ema(close, 12)", ()),
    "ema26": ("ta.ema(close, 26)", ()),
    "dist_sma20": ("close / {sma20} - 1", ("sma20",)),
    "dist_sma50": ("close / {sma50} - 1", ("sma50",)),
    "dist_sma200": ("close / {sma200} - 1", ("sma200",)),
    "sma20_slope": ("{sma20} / {sma20}[5] - 1", ("sma20",)),
    "rsi7": ("ta.rsi(close, 7)", ()),
    "rsi14": ("ta.rsi(close, 14)", ()),
    "atr14": ("ta.atr(14)", ()),
    "atr_pct": ("{atr14} / close", ("atr14",)),
    "vol20": ("ta.stdev({ret1}, 20, false) * math.sqrt(252)", ("ret1",)),
    "vol60": ("ta.stdev({ret1}, 60, false) * math.sqrt(252)", ("ret1",)),
    "vol_ratio_20_60": ("{vol60} > 0 ? {vol20} / {vol60} : 1.0", ("vol20", "vol60")),
    "sd20": ("ta.stdev(close, 20, false)", ()),
    "bb_upper": ("{sma20} + 2 * {sd20}", ("sma20", "sd20")),
    "bb_lower": ("{sma20} - 2 * {sd20}", ("sma20", "sd20")),
    "bb_pct": ("{bb_upper} - {bb_lower} > 0 ? (close - {bb_lower}) / ({bb_upper} - {bb_lower}) : 0.5",
               ("bb_upper", "bb_lower")),
    "zscore20": ("{sd20} > 0 ? (close - {sma20}) / {sd20} : 0.0", ("sma20", "sd20")),
    "pct_of_52w_high": ("close / ta.highest(close, 252)", ()),
    "pct_off_52w_low": ("close / ta.lowest(close, 252) - 1", ()),
    "volavg20": ("ta.sma(volume, 20)", ()),
    "volume_ratio": ("{volavg20} > 0 ? volume / {volavg20} : 1.0", ("volavg20",)),
    # one instrument: the "market" is the instrument itself
    "mkt_ret20": ("close / close[20] - 1", ()),
    "mkt_above_sma200": ("close > {sma200} ? 1.0 : 0.0", ("sma200",)),
    "mkt_vol20": ("{vol20}", ("vol20",)),
    # calendar, from the session's trading day (Monday = 0)
    "day_of_week": ("(dayofweek(time_tradingday) + 5) % 7", ()),
    "day_of_month": ("dayofmonth(time_tradingday)", ()),
    # position and account state
    "in_position": ("strategy.position_size > 0 ? 1.0 : 0.0", ()),
    "bars_held": ("strategy.position_size > 0 ? bar_index - strategy.opentrades.entry_bar_index(0) : 0", ()),
    "position_return": ("strategy.position_size > 0 ? close / strategy.position_avg_price - 1 : 0.0", ()),
    "position_drawdown": ("strategy.position_size > 0 ? math.min(close / posPeak - 1, 0.0) : 0.0", ()),
    "position_weight": ("strategy.position_size > 0 ? strategy.position_size * close * syminfo.pointvalue / strategy.equity : 0.0", ()),
    "gross_exposure": ("{position_weight}", ("position_weight",)),
    "cash_pct": ("1 - {position_weight}", ("position_weight",)),
    "position_count": ("strategy.opentrades", ()),
    "bars_since_exit": ("strategy.position_size > 0 ? 9999 : bar_index - lastExitBar", ()),
    "portfolio_return": ("strategy.equity / strategy.initial_capital - 1", ()),
    "portfolio_drawdown": ("math.min(strategy.equity / eqPeak - 1, 0.0)", ()),
}
_MACD = ("macd", "macd_signal", "macd_hist")
_BUILTIN = {"open", "high", "low", "close", "volume"}
_STATEFUL = {"position_drawdown", "bars_since_exit", "portfolio_drawdown"}

#: Bars of history each feature needs before it is defined, for the warm-up guard.
_WARMUP = {"ret1": 1, "ret5": 5, "ret20": 20, "ret60": 60, "sma10": 10, "sma20": 20, "sma50": 50,
           "sma200": 200, "ema12": 12, "ema26": 26, "dist_sma20": 20, "dist_sma50": 50,
           "dist_sma200": 200, "sma20_slope": 25, "rsi7": 8, "rsi14": 15, "macd": 26,
           "macd_signal": 34, "macd_hist": 34, "atr14": 15, "atr_pct": 15, "vol20": 21,
           "vol60": 61, "vol_ratio_20_60": 61, "bb_upper": 20, "bb_lower": 20, "bb_pct": 20,
           "zscore20": 20, "pct_of_52w_high": 252, "pct_off_52w_low": 252, "volume_ratio": 20,
           "mkt_ret20": 20, "mkt_above_sma200": 200, "mkt_vol20": 21}


class PineError(ValueError):
    pass


def _var(name: str) -> str:
    return name if name in _BUILTIN else f"f_{name}"


def _is_bool(node: Node) -> bool:
    if isinstance(node, Binary):
        return node.op in ("and", "or", "<", "<=", ">", ">=", "==", "!=")
    if isinstance(node, Unary):
        return node.op == "not"
    if isinstance(node, Call):
        return node.func in ("cross_above", "cross_below")
    return False


def _num(x: float) -> str:
    if float(x).is_integer() and abs(x) < 1e12:
        return f"{int(x)}.0" if "." not in str(x) else str(float(x))
    return repr(float(x))


class _Emitter:
    def __init__(self) -> None:
        self.names: Set[str] = set()

    def num(self, node: Node, c: int, p: int) -> str:
        s = self.emit(node, c, p)
        return f"({s} ? 1.0 : 0.0)" if _is_bool(node) else s

    def boolean(self, node: Node, c: int, p: int) -> str:
        s = self.emit(node, c, p)
        return s if _is_bool(node) else f"({s} != 0)"

    def emit(self, node: Node, c: int = 0, p: int = 1) -> str:
        if isinstance(node, Const):
            return _num(node.value)
        if isinstance(node, Name):
            self.names.add(node.name)
            base = _var(node.name)
            return base if c == 0 else f"{base}[{c}]"
        if isinstance(node, Unary):
            if node.op == "-":
                return f"(-{self.num(node.operand, c, p)})"
            return f"(not {self.boolean(node.operand, c, p)})"
        if isinstance(node, Binary):
            op = node.op
            if op in ("and", "or"):
                return f"({self.boolean(node.left, c, p)} {op} {self.boolean(node.right, c, p)})"
            a, b = self.num(node.left, c, p), self.num(node.right, c, p)
            if op == "/":
                return f"({b} != 0 ? {a} / {b} : 0.0)"
            if op == "==":
                return f"(math.abs({a} - {b}) <= 1e-9)"
            if op == "!=":
                return f"(math.abs({a} - {b}) > 1e-9)"
            return f"({a} {op} {b})"
        if isinstance(node, Call):
            f, args = node.func, node.args
            if f in ("cross_above", "cross_below"):
                a_c, b_c = self.num(args[0], c, p), self.num(args[1], c, p)
                a_p, b_p = self.num(args[0], p, p), self.num(args[1], p, p)
                if f == "cross_above":
                    return f"({a_c} > {b_c} and {a_p} <= {b_p})"
                return f"({a_c} < {b_c} and {a_p} >= {b_p})"
            if f == "prev":
                return self.emit(args[0], p, p)
            if f == "change":
                return f"({self.num(args[0], c, p)} - {self.num(args[0], p, p)})"
            vals = [self.num(a, c, p) for a in args]
            if f == "abs":
                return f"math.abs({vals[0]})"
            if f == "min":
                return f"math.min({', '.join(vals)})"
            if f == "max":
                return f"math.max({', '.join(vals)})"
            if f == "clamp":
                return f"math.max({vals[1]}, math.min({vals[2]}, {vals[0]}))"
        raise PineError(f"cannot translate {node!r}")


def _definitions(names: Set[str]) -> List[str]:
    """Pine lines defining every feature used, dependencies first."""
    order: List[str] = []

    def visit(n: str) -> None:
        if n in _BUILTIN or n in order or n in _MACD:
            return
        if n not in _DEFS:
            raise PineError(f"feature {n!r} has no daily Pine definition")
        for dep in _DEFS[n][1]:
            visit(dep)
        order.append(n)

    for n in sorted(names):
        visit(n)
    lines: List[str] = []
    if names & set(_MACD):
        lines.append("[f_macd, f_macd_signal, f_macd_hist] = ta.macd(close, 12, 26, 9)")
    for n in order:
        expr = re.sub(r"\{(\w+)\}", lambda m: f"f_{m.group(1)}", _DEFS[n][0])
        lines.append(f"f_{n} = {expr}")
    return lines


def warmup_bars(names: Set[str]) -> int:
    return max([_WARMUP.get(n, 1) for n in names] + [1])


def _comment(text: str, width: int = 78) -> List[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width - 3:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return [f"// {ln}" for ln in lines]


def genome_to_pine(genome: Genome, *, title: str = "", source_note: str = "",
                   account: float = 25_000.0, contracts: int = 1,
                   commission_per_contract: float = 1.0,
                   extra_notes: Sequence[str] = ()) -> str:
    """A complete Pine Script v6 strategy for one genome, on a daily futures chart."""
    em = _Emitter()
    entries = [em.boolean(parse(r.when), 0, 1) for r in genome.entry_rules]
    exits = [em.boolean(parse(r.when), 0, 1) for r in genome.exit_rules]
    names = set(em.names)
    for n in names:
        if n not in _BUILTIN and n not in _DEFS and n not in _MACD:
            raise PineError(f"feature {n!r} has no daily Pine definition")
    rk = genome.risk
    needs_peak = bool(rk.trailing_stop_pct) or "position_drawdown" in names
    needs_exit_bar = bool(rk.cooldown_bars) or "bars_since_exit" in names
    needs_eq_peak = "portfolio_drawdown" in names
    if needs_peak:
        names.add("position_drawdown")
    title = title or genome.name
    warm = warmup_bars(names)
    out: List[str] = ["//@version=6"]
    out.append(f"// {title} — evotrader genome {genome.id}.")
    if source_note:
        out += _comment(source_note)
    out.append("//")
    if genome.thesis:
        out += _comment(genome.thesis)
        out.append("//")
    out.append("// Rules, exactly as the engine runs them:")
    for r in genome.entry_rules:
        out += _comment(f"BUY  when {r.when}")
    for r in genome.exit_rules:
        out += _comment(f"SELL when {r.when}")
    risk_bits = [f"stop {rk.stop_loss_pct:.2%}" if rk.stop_loss_pct else "no stop",
                 f"target {rk.take_profit_pct:.2%}" if rk.take_profit_pct else "no target",
                 f"trailing {rk.trailing_stop_pct:.2%}" if rk.trailing_stop_pct else "no trailing stop",
                 f"max hold {rk.max_hold_bars} bars" if rk.max_hold_bars else "no max hold",
                 f"min hold {rk.min_hold_bars} bars" if rk.min_hold_bars else "",
                 f"cooldown {rk.cooldown_bars} bars" if rk.cooldown_bars else ""]
    out += _comment("Risk (checked on the close, filled at the next open): "
                    + ", ".join(b for b in risk_bits if b) + ".")
    out.append("//")
    out += _comment("Daily bars; the signal is read on the close and fills at the next open. "
                    "Use a MNQ1! (micro) chart with back-adjustment on. The backtests run at twice a "
                    f"${account:,.0f} account in notional, about 0.8 MNQ at NQ 31,000; one MNQ is about "
                    "2.5x, so the default of one contract is a little more than the tested size.")
    for note in extra_notes:
        out += _comment(note)
    out.append(f'strategy("{title[:60]} [evotrader]", overlay=true, pyramiding=0,')
    out.append(f"     initial_capital={int(account)}, default_qty_type=strategy.fixed, default_qty_value={contracts},")
    out.append(f"     commission_type=strategy.commission.cash_per_contract, commission_value={commission_per_contract},")
    out.append("     slippage=1, process_orders_on_close=false)")
    out.append("")
    out.append(f'contracts = input.int({contracts}, "Contracts", minval=1)')
    out.append(f'stopPct   = input.float({rk.stop_loss_pct * 100:.4g}, "Stop, % below entry (0 = off)") / 100')
    out.append(f'targetPct = input.float({rk.take_profit_pct * 100:.4g}, "Target, % above entry (0 = off)") / 100')
    out.append(f'trailPct  = input.float({rk.trailing_stop_pct * 100:.4g}, "Trailing stop, % off the peak close (0 = off)") / 100')
    out.append(f'maxHold   = input.int({rk.max_hold_bars}, "Max bars held (0 = off)")')
    out.append(f'minHold   = input.int({rk.min_hold_bars}, "Min bars before the sell rules apply")')
    out.append(f'cooldown  = input.int({rk.cooldown_bars}, "Bars to wait after an exit")')
    out.append("")
    out.append("// ---- state the rules can read")
    if needs_peak:
        out.append("var float posPeak = na")
        out.append("if strategy.position_size > 0")
        out.append("    posPeak := na(posPeak) or strategy.opentrades.entry_bar_index(0) == bar_index ? "
                   "math.max(strategy.position_avg_price, close) : math.max(posPeak, close)")
        out.append("else")
        out.append("    posPeak := na")
    out.append("var int lastExitBar = -100000")
    out.append("if strategy.closedtrades > 0")
    out.append("    lastExitBar := strategy.closedtrades.exit_bar_index(strategy.closedtrades - 1)")
    if needs_eq_peak:
        out.append("var float eqPeak = strategy.initial_capital")
        out.append("eqPeak := math.max(eqPeak, strategy.equity)")
    out.append("")
    out.append("// ---- features (evotrader's definitions)")
    out += _definitions(names)
    out.append("")
    out.append(f"warm = bar_index >= {warm}")
    out.append("inPos = strategy.position_size > 0")
    out.append("buySignal = " + (" or ".join(f"({e})" for e in entries) if entries else "false"))
    out.append("sellSignal = " + (" or ".join(f"({x})" for x in exits) if exits else "false"))
    out.append("exitNow = false")
    out.append("if inPos")
    out.append("    held = bar_index - strategy.opentrades.entry_bar_index(0)")
    out.append("    posRet = close / strategy.position_avg_price - 1")
    out.append("    riskExit = (stopPct > 0 and posRet <= -stopPct) or (targetPct > 0 and posRet >= targetPct)"
               + (" or (trailPct > 0 and f_position_drawdown <= -trailPct)" if needs_peak else "")
               + " or (maxHold > 0 and held >= maxHold)")
    out.append("    if riskExit or (held >= minHold and sellSignal)")
    out.append('        strategy.close("L", comment="out")')
    out.append("        exitNow := true")
    out.append("canEnter = warm and not inPos and (cooldown <= 0 or bar_index - lastExitBar >= cooldown)")
    out.append("if canEnter and buySignal")
    out.append('    strategy.entry("L", strategy.long, qty=contracts, comment="in")')
    out.append("")
    out.append('plotshape(canEnter and buySignal, title="Buy at next open", style=shape.triangleup, '
               'location=location.belowbar, color=color.new(color.teal, 0), size=size.small)')
    out.append('plotshape(exitNow, title="Sell at next open", style=shape.triangledown, '
               'location=location.abovebar, color=color.new(color.red, 0), size=size.small)')
    out.append(f'alertcondition(canEnter and buySignal, "{title[:40]}: buy at next open", '
               f'"{title[:40]}: buy {{{{ticker}}}} at the next open")')
    out.append(f'alertcondition(exitNow, "{title[:40]}: sell at next open", '
               f'"{title[:40]}: sell {{{{ticker}}}} at the next open")')
    return "\n".join(out) + "\n"


PINE_COMPILE_URL = ("https://pine-facade.tradingview.com/pine-facade/translate_light"
                    "?user_name=Guest&pine_id=00000000-0000-0000-0000-000000000000")


def compile_check(source: str, timeout: float = 30.0) -> List[str]:
    """Ask TradingView's Pine compiler about a script; returns its error messages."""
    import json
    import urllib.parse
    import urllib.request
    req = urllib.request.Request(PINE_COMPILE_URL,
                                 data=urllib.parse.urlencode({"source": source}).encode(),
                                 headers={"User-Agent": "Mozilla/5.0",
                                          "Referer": "https://www.tradingview.com/"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode())
    result = payload.get("result") or {}
    errors = result.get("errors2") or result.get("errors") or []
    msgs = [f"line {e.get('start', {}).get('line')}: {e.get('message')}" for e in errors]
    if not payload.get("success") and not msgs:
        msgs = ["compile failed without a message"]
    return msgs
