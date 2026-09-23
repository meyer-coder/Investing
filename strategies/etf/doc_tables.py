"""Markdown for the findings doc, from profitable-strategies/leveraged-etfs/all.json.

    python strategies/etf/doc_tables.py top50|specials|funds
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALL = ROOT / "profitable-strategies" / "leveraged-etfs" / "all.json"


def money(x) -> str:
    return "n/a" if x is None else (f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}")


def top50(data: dict) -> str:
    rows = ["| # | Strategy | Last 6 months | Last 12 months | 2019 to Mar 2026 | 2012 to 2018 | "
            "Typical 3 months | Win rate | Worst drawdown |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for v in data["strategies"]:
        w, c = v["windows"], v.get("three_month_stretches") or {}
        real = ((v.get("real") or {}).get("held_out") or {}).get("usd_per_session")
        recent = money(w["held_out"]["usd_per_session"]) + (f" ({money(real)} real)" if real is not None else "")
        dd = min(w[k]["max_drawdown"] for k in ("older", "train", "held_out"))
        rows.append(f"| {v['rank']} | {v['name']} | {recent} | {money(w['last_12m']['usd_per_session'])} | "
                    f"{money(w['train']['usd_per_session'])} | {money(w['older']['usd_per_session'])} | "
                    f"{money(c.get('median_usd_per_session'))} | {w['held_out']['win_rate']:.0%} / "
                    f"{w['train']['win_rate']:.0%} | {dd:.0%} |")
    return "\n".join(rows)


def funds(data: dict, store: dict) -> str:
    agg = defaultdict(lambda: [0, 0, 0])
    for v in store.values():
        k = ", ".join(v["symbols"])
        agg[k][0] += 1
        agg[k][1] += v["verdict"]["shown"]
    for v in data["strategies"]:
        agg[", ".join(v["symbols"])][2] += 1
    rows = ["| Funds | Profitable | At $80+ | In the top 50 |", "| --- | --- | --- | --- |"]
    for k, (a, b, c) in sorted(agg.items(), key=lambda x: (-x[1][2], -x[1][1])):
        rows.append(f"| {k} | {a} | {b} | {c} |")
    return "\n".join(rows)


def main(argv) -> int:
    data = json.loads(ALL.read_text())
    if argv[0] == "top50":
        print(top50(data))
    elif argv[0] == "funds":
        store = json.loads((ROOT / "strategies" / "etf" / "store.json").read_text())["strategies"]
        print(funds(data, store))
    else:
        print(json.dumps(data["specials"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
