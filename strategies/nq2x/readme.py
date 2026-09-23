"""Write profitable-strategies/nq-2x/README.md from reports/results.json.

    python strategies/nq2x/readme.py OUT_DIR HEAD.md TAIL.md

HEAD.md holds the prose above the ranking (summary, plan), TAIL.md the prose
after the strategies (how they were bred, caveats, reproduction).  Every
number in between is read from results.json, which publish.py wrote by
re-running each published genome.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ACCOUNT = 25_000.0


def usd(x: float) -> str:
    return f"{'-' if x < 0 else '+'}${abs(x):,.0f}"


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:+.{d}f}%"


def pf(x: float) -> str:
    return "no losses" if x >= 99 else f"{x:.2f}"


def rules_block(g: dict) -> str:
    lines = []
    for r in g["entry_rules"]:
        lines.append(f"- BUY when `{r['when']}`")
    for r in g["exit_rules"]:
        lines.append(f"- SELL when `{r['when']}`")
    rk = g["risk"]
    bits = [f"stop {rk['stop_loss_pct'] * 100:.2f}%" if rk.get("stop_loss_pct") else "no stop",
            f"target {rk['take_profit_pct'] * 100:.2f}%" if rk.get("take_profit_pct") else "no target",
            f"trailing stop {rk['trailing_stop_pct'] * 100:.2f}% off the best close" if rk.get("trailing_stop_pct") else "",
            f"at most {rk['max_hold_bars']} sessions" if rk.get("max_hold_bars") else "",
            f"sell rules wait {rk['min_hold_bars']} sessions" if rk.get("min_hold_bars") else "",
            f"{rk['cooldown_bars']} sessions before re-entering" if rk.get("cooldown_bars") else ""]
    lines.append("- Risk, checked on the close and filled at the next open: "
                 + ", ".join(b for b in bits if b) + ".")
    lines.append("- Size: all of the account's 2x buying power on every entry, one position.")
    return "\n".join(lines)


def section(r: dict) -> str:
    g, ho, yr, tr, old = r["genome"], r["held_out"], r["last_12m"], r["train"], r["older"]
    st = r["stress"]
    years = "  ".join(f"{y['year']} {y['return'] * 100:+.0f}%" for y in r["by_year"])
    trades = "; ".join(f"{t['entry'][5:]} to {t['exit'][5:]} {t['ret'] * 100:+.1f}%" for t in ho["trade_list"])
    return f"""### {r['rank']}. {r['name']}

*{r['family'].capitalize()} family. {r['origin']}*

**In words.** {r['words']}

**In values.** NQ E-mini (continuous contract, ratio back-adjusted), daily bars, long only. Decide on the close, fill at the next open.

{rules_block(g)}

**Numbers**, at 2x on $25,000, 0.2 bp commission and 1 bp slippage a side:

| window | return | trades | win | profit factor | max drawdown | worst day |
|---|---|---|---|---|---|---|
| last six months, held out (23 Mar to 22 Sep 2026) | {pct(ho['return'])} | {ho['trades']} | {ho['win_rate'] * 100:.0f}% | {pf(ho['profit_factor'])} | {ho['max_drawdown'] * 100:.1f}% | {ho['worst_day'] * 100:+.1f}% |
| last twelve months (six in-sample, six held out) | {pct(yr['return'])} | {yr['trades']} | {yr['win_rate'] * 100:.0f}% | {pf(yr['profit_factor'])} | {yr['max_drawdown'] * 100:.1f}% | {yr['worst_day'] * 100:+.1f}% |
| training, Jan 2019 to Mar 2026 | {pct(tr['return'], 0)} | {tr['trades']} | {tr['win_rate'] * 100:.0f}% | {pf(tr['profit_factor'])} | {tr['max_drawdown'] * 100:.1f}% | {tr['worst_day'] * 100:+.1f}% |
| older history, 2010 to 2018, never used | {pct(old['return'], 0)} | {old['trades']} | {old['win_rate'] * 100:.0f}% | {pf(old['profit_factor'])} | {old['max_drawdown'] * 100:.1f}% | {old['worst_day'] * 100:+.1f}% |
| held out at three times the costs | {pct(st['held_out']['return'])} | {st['held_out']['trades']} | | {pf(st['held_out']['profit_factor'])} | | |

- **Per session over the held-out six months:** {usd(ho['usd_per_session'])} on average; in the market {ho['sessions_in_market'] * 100:.0f}% of sessions; best {usd(ho['usd_best_day'])}, worst {usd(ho['usd_worst_day'])}; 10th and 90th percentile sessions {usd(ho['p10_day'] * ACCOUNT)} and {usd(ho['p90_day'] * ACCOUNT)}; {ho['sessions_below_2pct'] * 100:.1f}% of sessions lost more than 2% ($500).
- **Over the last twelve months:** {usd(yr['usd_per_session'])} a session on average.
- **Average trade** {ho['avg_trade'] * 100:+.2f}% of the position over {ho['avg_hold']:.1f} sessions in the held-out window; {tr['avg_trade'] * 100:+.2f}% over {tr['avg_hold']:.1f} sessions in training.
- **Year by year at 2x, 2010 to 2026:** {years}.
- **Held-out trades:** {trades}.

Files: `{r['stem']}.json` (the genome for `evaluate` and `signals`), `{r['stem']}.pine` (TradingView strategy with buy and sell alerts; compiles on TradingView's Pine compiler).
"""


def main(argv) -> int:
    out = Path(argv[0])
    head, tail = Path(argv[1]).read_text(), Path(argv[2]).read_text()
    results = json.loads((out / "reports" / "results.json").read_text())
    rows = ["| # | strategy | family | last 6 months, held out | $ per session | trades | profit factor | worst day | training 2019-26 | older 2010-18 | 3x costs |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        ho, tr, old = r["held_out"], r["train"], r["older"]
        rows.append(f"| {r['rank']} | {r['name']} | {r['family']} | {pct(ho['return'])} | {usd(ho['usd_per_session'])} | "
                    f"{ho['trades']} | {pf(ho['profit_factor'])} | {usd(ho['usd_worst_day'])} | {pct(tr['return'], 0)} | "
                    f"{pct(old['return'], 0)} | {'profitable' if r['verdict']['survives_3x_costs'] else 'loses'} |")
    body = [head.rstrip(), "", "## Ranking, most to least profitable", "",
            "By return over the last six months, the window no strategy was selected on. "
            "Dollar figures are on $25,000 at 2x, per trading session, all sessions counted.", "",
            "\n".join(rows), "", "## The strategies", ""]
    body += [section(r) for r in results]
    body += [tail.strip(), ""]
    (out / "README.md").write_text("\n".join(body))
    print(f"wrote {out / 'README.md'} ({len(results)} strategies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
