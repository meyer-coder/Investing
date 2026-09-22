"""Shrink an evolved genome to the rules that actually matter.

Evolution leaves clutter: clauses that are always true (day_of_month <= 37),
the same condition three times, entries that never fire.  This removes one
piece at a time (a rule, one side of an and/or, a risk setting) and rounds
thresholds, keeping each change only if every trade in the training window,
the held-out six months and the older 2010-2018 history is identical, entry
and exit dates alike.  The result behaves exactly as the evolved genome did.

    python strategies/nq2x/simplify.py IN.json OUT.json
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evotrader.dsl import Binary, Call, Const, Name, Node, Unary, parse   # noqa: E402
from evotrader.genome import Genome, GenomeError, compile_genome           # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gauntlet import COMMISSION, LEVERAGE, SLIPPAGE, Windows              # noqa: E402

_PREC = {"or": 1, "and": 2, "not": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "==": 4, "!=": 4,
         "+": 5, "-": 5, "*": 6, "/": 6}


def to_text(node: Node, parent: int = 0) -> str:
    if isinstance(node, Const):
        v = node.value
        return str(int(v)) if float(v).is_integer() else f"{v:g}"
    if isinstance(node, Name):
        return node.name
    if isinstance(node, Unary):
        inner = to_text(node.operand, 7)
        return f"-{inner}" if node.op == "-" else f"not {inner}"
    if isinstance(node, Call):
        return f"{node.func}({', '.join(to_text(a) for a in node.args)})"
    if isinstance(node, Binary):
        p = _PREC[node.op]
        text = f"{to_text(node.left, p)} {node.op} {to_text(node.right, p + 1)}"
        return f"({text})" if p < parent else text
    raise TypeError(node)


def _rewrites(node: Node) -> Iterator[Node]:
    """Every tree one step simpler: one and/or operand kept, or a sub-tree simplified."""
    if isinstance(node, Binary):
        if node.op in ("and", "or"):
            yield node.left
            yield node.right
        for sub in _rewrites(node.left):
            yield Binary(node.op, sub, node.right)
        for sub in _rewrites(node.right):
            yield Binary(node.op, node.left, sub)
    elif isinstance(node, Unary):
        for sub in _rewrites(node.operand):
            yield Unary(node.op, sub)


def _roundings(node: Node) -> Iterator[Node]:
    if isinstance(node, Const):
        v = node.value
        for digits in (1, 2, 3):
            r = round(v, digits)
            if r != v and r != 0:
                yield Const(r)
        return
    if isinstance(node, Binary):
        for sub in _roundings(node.left):
            yield Binary(node.op, sub, node.right)
        for sub in _roundings(node.right):
            yield Binary(node.op, node.left, sub)
    elif isinstance(node, Unary):
        for sub in _roundings(node.operand):
            yield Unary(node.op, sub)
    elif isinstance(node, Call):
        for i, a in enumerate(node.args):
            for sub in _roundings(a):
                yield Call(node.func, tuple(node.args[:i]) + (sub,) + tuple(node.args[i + 1:]))


class Judge:
    def __init__(self) -> None:
        self.w = Windows()

    def signature(self, g: Genome) -> Tuple:
        c = compile_genome(g)
        kw = dict(starting_cash=25_000.0, commission_bps=COMMISSION, slippage_bps=SLIPPAGE,
                  record_thoughts=False, leverage=LEVERAGE)
        sig = []
        for u, f, start in ((self.w.train, self.w.f_train, None),
                            (self.w.recent, self.w.f_recent,
                             max(self.w.cut, self.w.f_recent.warmup_for(c.feature_names()))),
                            (self.w.older, self.w.f_older, None)):
            r = run_backtest(c, u, f, start_bar=start, **kw)
            sig.append(tuple((t.entry_date, t.exit_date) for t in r.journal.trades))
        return tuple(sig)


def simplify(item: dict, judge: Judge) -> dict:
    best = copy.deepcopy(item)
    target = judge.signature(Genome.from_dict(best))

    def same(candidate: dict) -> bool:
        try:
            return judge.signature(Genome.from_dict(candidate)) == target
        except (GenomeError, ValueError, ZeroDivisionError):
            return False

    changed = True
    while changed:
        changed = False
        for side in ("entry_rules", "exit_rules"):
            rules = best[side]
            for i in range(len(rules)):
                if len(rules) > 1:                       # drop a whole rule
                    cand = copy.deepcopy(best)
                    del cand[side][i]
                    if same(cand):
                        best, changed = cand, True
                        break
                tree = parse(rules[i]["when"])
                for simpler in _rewrites(tree):          # drop half of an and/or
                    cand = copy.deepcopy(best)
                    cand[side][i]["when"] = to_text(simpler)
                    if same(cand):
                        best, changed = cand, True
                        break
                if changed:
                    break
            if changed:
                break
        if not changed:
            for key in ("take_profit_pct", "trailing_stop_pct", "stop_loss_pct",
                        "cooldown_bars", "min_hold_bars", "max_hold_bars"):
                if best["risk"].get(key):
                    cand = copy.deepcopy(best)
                    cand["risk"][key] = 0
                    if same(cand):
                        best, changed = cand, True
                        break
    for side in ("entry_rules", "exit_rules"):     # tidy the numbers last
        for i, rule in enumerate(best[side]):
            tree = parse(rule["when"])
            progress = True
            while progress:
                progress = False
                for rounded in _roundings(tree):
                    cand = copy.deepcopy(best)
                    cand[side][i]["when"] = to_text(rounded)
                    if same(cand):
                        best, tree, progress = cand, rounded, True
                        break
            best[side][i]["when"] = to_text(tree)
    for key in ("stop_loss_pct", "take_profit_pct", "trailing_stop_pct"):
        v = best["risk"].get(key) or 0
        for digits in (2, 3):
            if v and round(v, digits) != v:
                cand = copy.deepcopy(best)
                cand["risk"][key] = round(v, digits)
                if same(cand):
                    best = cand
                    break
    return best


def main(argv: List[str]) -> int:
    src, dst = argv[0], argv[1]
    raw = json.loads(Path(src).read_text())
    items = raw["genomes"] if isinstance(raw, dict) else raw
    judge = Judge()
    out = []
    for item in items:
        slim = simplify(item, judge)
        before = sum(len(r["when"]) for r in item["entry_rules"] + item["exit_rules"])
        after = sum(len(r["when"]) for r in slim["entry_rules"] + slim["exit_rules"])
        print(f"{item['name'][:50]:50} rule text {before:4d} -> {after:4d} chars, "
              f"{len(item['entry_rules'])}+{len(item['exit_rules'])} -> "
              f"{len(slim['entry_rules'])}+{len(slim['exit_rules'])} rules")
        out.append(slim)
    Path(dst).write_text(json.dumps({"genomes": out}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
