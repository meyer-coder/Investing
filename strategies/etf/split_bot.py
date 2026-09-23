"""The three-bot split account: three strategies, a third of $25,000 each.

    python strategies/etf/split_bot.py

Picked from the combination search (combos.py) on the held-out six months for
the user's aim: $200-300 a session, reliably, without TSMX.  Each bot keeps its
own rules and trades only its third of the account, so the account's day is
the sum of the three.  Writes profitable-strategies/leveraged-etfs/split-bot/:
README.md (rules, month by month on the real funds and the rebuilt series,
every window), split_bot.json, and a Pine script per bot and fund at 33% of
equity.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from combos import series, stats                                            # noqa: E402
from gauntlet import ACCOUNT, REAL, WINDOWS, load_store                     # noqa: E402
from live import align, latest_bars, run                                    # noqa: E402
from publish_etf import fund_name, pretty                                   # noqa: E402
from evotrader.genome import Genome                                         # noqa: E402
from evotrader.pine import compile_check, genome_to_pine                    # noqa: E402

OUT = ROOT / "profitable-strategies" / "leveraged-etfs" / "split-bot"
MEMBERS = ["47956c8de0", "a1f9abefa6", "1c2ec5357a"]        # store keys, by prefix
SHARE = 1.0 / 3.0
PICKED = "2026-09-23"


def members() -> List[dict]:
    store = load_store()["strategies"]
    out = []
    for prefix in MEMBERS:
        key = next(k for k in store if k.startswith(prefix))
        v = store[key]
        funds = [fund_name(s) for s in v["symbols"]]
        out.append({"key": key, "name": f"{' / '.join(funds)} {pretty(v['genome']['name'])}",
                    "symbols": v["symbols"], "funds": [REAL.get(s, s) for s in v["symbols"]],
                    "genome": v["genome"], "store": v})
    return out


def mixed(parts: List[Dict[str, float]], lo: str, hi: str):
    dates = sorted(d for d in set().union(*(set(p) for p in parts)) if lo <= d <= hi)
    r = np.array([sum(SHARE * p.get(d, 0.0) for p in parts) for d in dates])
    return dates, r


def real_parts(ms: List[dict]):
    cache, parts, last = {}, [], ""
    for m in ms:
        bars = {}
        for f in m["funds"]:
            if f not in cache:
                b, prov = latest_bars(f)
                if prov:                      # a session still trading: leave it out
                    b = b.slice(None, b.dates[-2])
                cache[f] = b
            bars[f] = cache[f]
        u = align(bars)
        res = run({"genome": m["genome"]}, u)
        d, e = res.journal.equity_dates, np.asarray(res.journal.equity, dtype=float)
        parts.append(dict(zip(d[1:], e[1:] / e[:-1] - 1.0)))
        last = max(last, u.calendar[-1])
    return parts, last


def sizing(windows: Dict[str, np.ndarray]) -> List[str]:
    """How big the account can run inside a funded account's loss limits: the
    worst day and drawdown at each share of the balance, per window."""
    def dd(r):
        eq = np.cumprod(1.0 + r)
        return float((eq / np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:] - 1.0).min())
    rows = ["| Share of the balance | Window | $ a session per $100,000 | Worst day | Days worse than -4% | "
            "Worst drawdown |", "| --- | --- | --- | --- | --- | --- |"]
    for f in (1.0, 0.5, 0.33, 0.3, 0.25):
        for name, r in windows.items():
            x = f * r
            rows.append(f"| {f:.0%} | {name} | {money(x.mean() * 100_000)} | {x.min():.1%} | "
                        f"{int((x < -0.04).sum())} | {dd(x):.1%} |")
    return rows


def money(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def main() -> int:
    ms = members()
    rebuilt = [series(m["store"]) for m in ms]
    wins = {}
    for name, (lo, hi) in WINDOWS.items():
        if name == "last_12m":
            continue
        d, r = mixed(rebuilt, lo, hi)
        wins[name] = stats(r, d, held_out=(name == "held_out"))
    parts, last = real_parts(ms)
    lo = WINDOWS["held_out"][0]
    d, r = mixed(parts, lo, last)
    real = stats(r, d, held_out=True)
    solo = [{"rebuilt": round(float(np.mean([p.get(x, 0.0) for x in d])) * ACCOUNT, 1)} for p in rebuilt]
    for s, p in zip(solo, parts):
        s["real"] = round(float(np.mean([p.get(x, 0.0) for x in d]) * ACCOUNT), 1)

    OUT.mkdir(parents=True, exist_ok=True)
    doc = {"name": "Three-bot split account", "picked": PICKED, "share_each": round(SHARE, 4),
           "account": ACCOUNT, "real_window": [lo, last],
           "members": [{k: m[k] for k in ("key", "name", "symbols", "funds", "genome")} for m in ms],
           "windows": wins, "real_held_out": real}
    (OUT / "split_bot.json").write_text(json.dumps(doc, indent=1))

    months = sorted(real["by_month"])
    mrow = " | ".join(f"{m[5:]}/{m[:4]}" for m in months)
    lines = ["# Three-bot split account", "",
             f"Picked {PICKED}. Backtests on daily bars, not advice.", "",
             "Three bots share one $25,000 account, a third each (about $8,333). Each keeps its own rules and trades "
             "only its third, so the account's day is the sum of the three. None trades TSMX. The bots were picked "
             "together because their good months cover each other's quiet ones.", "",
             "## The bots", ""]
    for m, s in zip(ms, solo):
        g = m["genome"]
        lines.append(f"- **{m['name']}.** Buy when `{' or '.join(x['when'] for x in g['entry_rules'])}`; sell when "
                     f"`{' or '.join(x['when'] for x in g['exit_rules'])}`"
                     + "".join(f"; {k.replace('_pct', '').replace('_', ' ')} {v:.0%}" for k, v in g["risk"].items()
                               if k in ("stop_loss_pct", "take_profit_pct", "trailing_stop_pct") and v)
                     + f". On its own with the whole account: {money(s['real'])} a session over the last six months "
                     f"on the real funds.")
    lines += ["", "## The last six months, month by month", "",
              f"Dollars a session for the whole account. Real funds from {lo} to {last}; rebuilt series to "
              f"{WINDOWS['held_out'][1]}.", "",
              f"| | {mrow} | All six months |", "| --- | " + " | ".join("---" for _ in months) + " | --- |",
              f"| Real funds | " + " | ".join(money(real["by_month"][m]) for m in months)
              + f" | {money(real['usd_per_session'])} |",
              f"| Rebuilt series | " + " | ".join(money(wins["held_out"]["by_month"].get(m, 0.0)) for m in months)
              + f" | {money(wins['held_out']['usd_per_session'])} |", "",
              f"On the real funds: {real['month_stretches_up']:.0%} of rolling one-month stretches made money, the "
              f"worst {money(real['worst_month_stretch'])} a session; the worst drawdown was "
              f"{real['max_drawdown']:.0%} and the worst day {money(real['worst_day'])}.", "",
              "## Every window (rebuilt series)", "",
              "| Window | $ a session | Months that made money | Worst month | Worst drawdown |",
              "| --- | --- | --- | --- | --- |"]
    for name, label in (("held_out", "Last six months"), ("train", "2019 to March 2026"), ("older", "2012 to 2018")):
        w = wins[name]
        lines.append(f"| {label} | {money(w['usd_per_session'])} | {w['months_up']:.0%} | {money(w['worst_month'])} | "
                     f"{w['max_drawdown']:.0%} |")
    lines += ["", "## Read this before trusting it", "",
              "- The three strategies' rules were set before the last six months and never fit to them, but the "
              "three were chosen from about 200 candidates for how well they covered each other over those months. "
              "The months are in-sample for that choice.",
              "- In ordinary years the same account made far less: $46 a session over 2019 to March 2026 and $30 over "
              "2012 to 2018, with drops of 36% and 40%.",
              "- MUU, NVDL and AMDL are 2x funds. The account is a bet that memory and GPU chips keep trending.", "",
              "## In a funded account", "",
              "Funded accounts cut a trader off at a daily loss (often 4-5% of the balance) and a total drawdown "
              "(often 6-10%). At full size this account's worst day was far past those, so it has to run at a share "
              "of the balance: each bot trades a third of that share. The dollars scale with the balance.", "",
              *sizing({"Last six months (real funds)": r,
                       "2019 to March 2026": mixed(rebuilt, *WINDOWS["train"])[1],
                       "2012 to 2018": mixed(rebuilt, *WINDOWS["older"])[1]}),
              "", "Check the firm's own rules first: whether it allows 2x single-stock funds and holding overnight, "
              "and whether its drawdown trails the high-water mark.", "",
              "## Running it", "",
              "- Each bot has a Pine script per fund here, set to trade 33% of equity. Put each on a daily chart of its "
              "fund. A bot on two funds holds one of them at a time: while it holds one, skip the other's buy.",
              "- The paper trail (`../paper/`) runs it from the September 23 open.", ""]
    (OUT / "README.md").write_text("\n".join(lines))

    for i, m in enumerate(ms, 1):
        g = Genome.from_dict({**m["genome"], "name": m["name"]})
        for fund in m["funds"]:
            note = [f"Bot {i} of the three-bot split account: this script trades a third of the account "
                    f"(33% of equity). The other two bots run on their own charts."]
            if len(m["funds"]) > 1:
                note.append(f"It trades {', '.join(m['funds'])}, one at a time: while one is held, skip the "
                            f"other's buy.")
            src = genome_to_pine(g, fund=fund, extra_notes=note, qty_pct=33,
                                 source_note="Three-bot split account (strategies/etf/split_bot.py).")
            errs = compile_check(src)
            if errs:
                print(f"pine for bot {i} {fund} does not compile: {errs[:2]}", flush=True)
                continue
            (OUT / f"bot{i}_{fund.lower()}.pine").write_text(src)
    print(json.dumps({"real": {k: real[k] for k in ("usd_per_session", "worst_month", "month_stretches_up",
                                                     "max_drawdown", "by_month")},
                      "rebuilt": {k: {x: wins[k][x] for x in ("usd_per_session", "worst_month", "months_up",
                                                                "max_drawdown")} for k in wins},
                      "solo": solo}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
