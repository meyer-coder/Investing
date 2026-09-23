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


def special_lines(data: dict) -> str:
    out = []
    by_rank = {v["rank"]: v for v in data["strategies"]}
    extra = {}
    for f in (ALL.parent).glob("9[0-9]_*.json"):
        v = json.loads(f.read_text())
        extra[v["rank"]] = v
    for key, title, target in (("reliable_150", "Most reliable high earner ($150 to $200 a session)", 175),
                               ("low_risk_100", "$100 a session at the lowest risk", 100)):
        sp = data["specials"].get(key)
        if not sp:
            continue
        v = by_rank.get(sp["rank"]) or extra.get(sp["rank"])
        w, sz, c = v["windows"], sp["sized"], sp["three_month_stretches"]
        full_c = v.get("three_month_stretches") or {}
        out += [f"### {title}: {v['name']}", "",
                f"At full size: {money(w['held_out']['usd_per_session'])} a session over the last six months, "
                f"{money(w['last_12m']['usd_per_session'])} over the last 12 months, "
                f"{money(w['train']['usd_per_session'])} over 2019 to March 2026 and "
                f"{money(w['older']['usd_per_session'])} over 2012 to 2018; typical three months "
                f"{money(full_c.get('median_usd_per_session'))}, win rate {w['held_out']['win_rate']:.0%} recently.",
                "",
                f"Sized to {money(target)} a session (the last six months), with {sz['fraction']:.0%} of the account: "
                f"{money(sz['last_12m']['usd_per_session'])} over the last 12 months, "
                f"{money(sz['train']['usd_per_session'])} over 2019 to March 2026, worst drawdowns "
                f"{sz['held_out']['max_drawdown']:.0%} recently, {sz['train']['max_drawdown']:.0%} over 2019 to 2026 "
                f"and {sz['older']['max_drawdown']:.0%} over 2012 to 2018. Its three-month stretches since 2019 made "
                f"money {c['share_profitable']:.0%} of the time; the typical one {money(c['median_usd_per_session'])} "
                f"a session.", ""]
    return "\n".join(out)


def readme(data: dict) -> str:
    n = len(data["strategies"])
    beat = {w: sum(v["windows"][w]["usd_per_session"] > sum(v["buy_and_hold"][w].values()) / len(v["buy_and_hold"][w])
                   for v in data["strategies"]) for w in ("held_out", "train", "older")}
    return "\n".join([
        "# Leveraged tech strategies: top 50", "",
        "As of 2026-09-23. Backtests on daily bars, not advice.", "",
        f"The {n} most profitable different strategies found in a seven-hour grind over 2x and 3x funds on "
        "semiconductors, graphics-card and AI names and big tech. Every one made at least $80 a session over "
        "the last six months (never used for breeding), made money over 2019 to March 2026 and over 2012 to "
        "2018, still made money at 3x slippage, and never fell more than 70%.", "",
        "- **$ a session** is a fixed $25,000 in each trade (cash, no margin, one position at a time), fills at "
        "the next open, 8 bp slippage a side.",
        "- **Real** is the same rules on the real fund (NVDL, AMDL, MUU, TSMX ...) over its own life; single-stock "
        "funds were bred on series rebuilt from their stocks back to 2011.",
        "- **Typical 3 months** is the median of every rolling three-month stretch since 2019: how much of the "
        "recent result is the recent market.",
        "- **Win rate** is the last six months / 2019 to March 2026. **Worst drawdown** is the worst of the three "
        "windows.",
        "- The last six months were extreme for these funds (SOXL +178% with a 69% drop in between, 2x Micron "
        "+284%), so recent dollars are far above what the same rules made in earlier years.",
        f"- Holding the funds made more than most of these: {beat['held_out']} of the {n} beat buying and holding "
        f"their funds over the last six months, {beat['train']} over 2019 to March 2026 and {beat['older']} over "
        "2012 to 2018. What the rules buy is time out of the market: holding these funds fell 81% to 92% in "
        "2022, and none of these fell more than 70%.", "",
        top50(data), "", "## The two picks you asked for", "", special_lines(data),
        "## Running them live", "",
        "- `python strategies/etf/live.py --ranks 1,2,3` runs strategies through the latest close on the real "
        "funds (and, as a check, on the rebuilt series): what each holds, its orders for the next open, and the "
        "closes today that would change them. It writes `live/<date>.md` and `.json`. Paper signals only; it "
        "places no orders.",
        "- In TradingView, add a strategy's `.pine` to a daily chart of its fund, then add an alert on the script "
        "with the condition \"alert() function calls only\". It fires at each daily close with the order for the "
        "next open. A strategy on two funds needs both charts, and holds one position at a time: while one fund "
        "is held, skip the other's buy.", "",
        "## Files", "",
        "- `NN_name.md`: rules, every window, the real-fund check, buy-and-hold and year-by-year results.",
        "- `NN_name.json`: the same as data, with the strategy's rules.",
        "- `NN_name[_fund].pine`: TradingView Pine v6, one per fund, compiled against TradingView.",
        "- `stored/all_profitable.json`: every profitable strategy found, including those under $80 a session.",
        "- `strategies/etf/`: the code that built all of it.", ""])


def main(argv) -> int:
    data = json.loads(ALL.read_text())
    if argv[0] == "top50":
        print(top50(data))
    elif argv[0] == "readme":
        print(readme(data))
    elif argv[0] == "funds":
        store = json.loads((ROOT / "strategies" / "etf" / "store.json").read_text())["strategies"]
        print(funds(data, store))
    else:
        print(json.dumps(data["specials"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
