"""Paper trading for the leveraged-ETF bots: every fill written once to a
ledger, every account marked at every close, the orders for the next open.

    python strategies/etf/paper.py                 # bring every account up to the latest close
    python strategies/etf/paper.py --print accounts|orders|trades
    python strategies/etf/paper.py --retire top2 --why "..."                    # take a bot off the roster
    python strategies/etf/paper.py --restore top2                               # and put it back where it left off
    python strategies/etf/paper.py --add fbb5 --rank 9 --funds SOXL,TQQQ,TECL --label "FBB5 dip buyer" \
        --name "Uptrend Dip (bred FBB5) on SOXL / TQQQ / TECL" --start 2026-09-25   # list #9 on other funds

Each bot has its own $25,000 paper account and trades one fund at a time with
its share of the account.  Its orders are the engine's, as in live.py: decided
on a close and filled at the next open, at that open plus 8 bp slippage (minus
8 bp for a sale).  A position the strategy already held going into the go-live
session is bought at that session's open and marked synced.  A bot's rules are
copied into the ledger when its account opens, so a later re-ranking of the
published strategies cannot change the bot, and fills already in the ledger
are never recomputed.  A session still trading is left for the next run.

Writes profitable-strategies/leveraged-etfs/paper/ledger.json and
paper/<date>.md, the notes for the run after that close.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import date as Date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import REAL, SLIP                                             # noqa: E402
from live import (END_REASON, PUBLISHED, align, extend, latest_bars, levels,  # noqa: E402
                  load_items, next_session, run)
from evotrader.data import Bars, Universe                                   # noqa: E402

GO_LIVE = "2026-09-23"
START_CASH = 25_000.0
PAPER = PUBLISHED / "paper"
LEDGER = PAPER / "ledger.json"


def bot_list() -> List[dict]:
    """The top three at full size, and the two picks at their sizes."""
    sp = json.loads((PUBLISHED / "all.json").read_text())["specials"]
    out = [{"id": f"top{r}", "rank": r, "size": 1.0, "label": f"#{r}"} for r in (1, 2, 3)]
    out.append({"id": "pick150", "rank": sp["reliable_150"]["rank"],
                "size": sp["reliable_150"]["sized"]["fraction"], "label": "$150-200 pick"})
    out.append({"id": "lowrisk100", "rank": sp["low_risk_100"]["rank"],
                "size": sp["low_risk_100"]["sized"]["fraction"], "label": "$100 low-risk pick"})
    return out


def open_account(bot: dict, item: dict) -> dict:
    return {"id": bot["id"], "label": bot["label"], "rank": item["rank"], "name": item["name"],
            "symbols": item["symbols"], "funds": [REAL.get(s, s) for s in item["symbols"]],
            "size": bot["size"], "genome": item["genome"], "start": GO_LIVE, "start_cash": START_CASH,
            "cash": START_CASH, "position": None, "fills": [], "closed": [], "marks": [],
            "orders": {}, "levels": {}, "last_date": None}


def retire(ledger: dict, ids: List[str], why: str, day: str) -> None:
    """Take bots off the roster; the ledger keeps what they did and why they left."""
    keep = []
    for a in ledger["accounts"]:
        if a["id"] not in ids:
            keep.append(a)
            continue
        ledger.setdefault("retired", []).append({**a, "retired": day, "why_retired": why})
    ledger["accounts"] = keep


def restore(ledger: dict, ids: List[str]) -> None:
    """Put retired bots back on the roster where they left off (their fills, marks and position unchanged)."""
    back = [a for a in ledger.get("retired", []) if a["id"] in ids]
    ledger["retired"] = [a for a in ledger.get("retired", []) if a["id"] not in ids]
    for a in back:
        a.pop("retired", None)
        a.pop("why_retired", None)
        ledger["accounts"].append(a)


def add_bot(ledger: dict, bot_id: str, rank: int, funds: List[str], label: str, start: str, name: str = "") -> None:
    """Open a $25,000 account for the published strategy ranked `rank`, on `funds` instead of its own when
    given (the rule unchanged), under `name` when given."""
    if any(a["id"] == bot_id for a in ledger["accounts"]):
        return
    item = load_items([rank])[0]
    if funds:
        item = {**item, "symbols": list(funds)}
    if name:
        item = {**item, "name": name}
    acct = open_account({"id": bot_id, "label": label, "size": 1.0}, item)
    acct["start"] = start
    ledger["accounts"].append(acct)


def add_split(ledger: dict, start: str) -> None:
    """The three-bot split account (split_bot.py): each bot a third of $25,000."""
    doc = json.loads((PUBLISHED / "split-bot" / "split_bot.json").read_text())
    n = len(doc["members"])
    for i, m in enumerate(doc["members"], 1):
        if any(a["id"] == f"split{i}" for a in ledger["accounts"]):
            continue
        acct = open_account({"id": f"split{i}", "label": f"Split bot {i}/{n}", "size": 1.0},
                            {"rank": None, "name": m["name"], "symbols": m["symbols"], "genome": m["genome"]})
        acct.update({"group": "Three-bot split account", "start": start,
                     "start_cash": round(START_CASH / n, 2), "cash": round(START_CASH / n, 2)})
        ledger["accounts"].append(acct)


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"go_live": GO_LIVE, "accounts": []}


def equity(acct: dict, prices: Dict[str, float]) -> float:
    p = acct["position"]
    return acct["cash"] + (p["shares"] * prices[p["fund"]] if p else 0.0)


def _held_into(trades, day: str, placeholder: str) -> Optional[object]:
    """The strategy's position going into ``day``'s open and not sold there."""
    for t in trades:
        if t.entry_date < day and (day < t.exit_date or (t.exit_date == placeholder == day
                                                         and t.exit_reason == END_REASON)):
            return t
    return None


def advance(acct: dict, u: Universe, with_levels: bool = True) -> List[dict]:
    """Apply every finished session after the account's last one; returns the new fills."""
    last = u.calendar[-1]
    nxt = next_session(last)
    trades = run(acct, extend(u, nxt)).journal.trades
    s = SLIP / 1e4
    new: List[dict] = []

    def fill(day: str, side: str, fund: str, px: float, shares: float, why: str, **extra) -> None:
        f = {"date": day, "side": side, "fund": fund, "price": round(px, 4), "shares": round(shares, 4),
             "value": round(px * shares, 2), "why": why, **extra}
        acct["fills"].append(f)
        new.append(f)

    for i, day in enumerate(u.calendar):
        if day < acct["start"] or (acct["last_date"] and day <= acct["last_date"]):
            continue
        opens = {f: float(u.bars[f].open[i]) for f in u.symbols}
        closes = {f: float(u.bars[f].close[i]) for f in u.symbols}
        sells = [t for t in trades if t.exit_date == day and t.exit_reason != END_REASON]
        buys = [(t.symbol, t.entry_reason, False, t.entry_date) for t in trades if t.entry_date == day]
        if day == acct["start"] and acct["position"] is None and not buys:
            t = _held_into(trades, day, nxt)
            if t is not None:
                buys = [(t.symbol, f"synced at go-live: the strategy has held {t.symbol} since "
                                   f"{t.entry_date} ({t.entry_reason})", True, t.entry_date)]
        for t in sells:
            p = acct["position"]
            if not p or p["fund"] != t.symbol:
                continue
            px = opens[t.symbol] * (1 - s)
            acct["cash"] += p["shares"] * px
            pnl = p["shares"] * (px - p["entry_price"])
            fill(day, "sell", t.symbol, px, p["shares"], t.exit_reason)
            acct["closed"].append({"fund": t.symbol, "bought": p["entry_date"], "entry": round(p["entry_price"], 4),
                                   "sold": day, "exit": round(px, 4), "shares": round(p["shares"], 4),
                                   "pnl": round(pnl, 2), "ret": round(px / p["entry_price"] - 1, 4),
                                   "why_in": p["why"], "why_out": t.exit_reason, "synced": p.get("synced", False)})
            acct["position"] = None
        p = acct["position"]
        if p and p["entry_date"] < day and not any(
                x.symbol == p["fund"] and x.entry_date < day and day < x.exit_date for x in trades):
            # a price revision undid the strategy's position: follow it out
            px = opens[p["fund"]] * (1 - s)
            acct["cash"] += p["shares"] * px
            why = "the strategy no longer holds it after a price revision"
            fill(day, "sell", p["fund"], px, p["shares"], why)
            acct["closed"].append({"fund": p["fund"], "bought": p["entry_date"], "entry": round(p["entry_price"], 4),
                                   "sold": day, "exit": round(px, 4), "shares": round(p["shares"], 4),
                                   "pnl": round(p["shares"] * (px - p["entry_price"]), 2),
                                   "ret": round(px / p["entry_price"] - 1, 4), "why_in": p["why"],
                                   "why_out": why, "synced": p.get("synced", False)})
            acct["position"] = None
        for fund, why, synced, _ in buys:
            if acct["position"] is not None:
                continue
            px = opens[fund] * (1 + s)
            shares = acct["size"] * acct["cash"] / px
            acct["cash"] -= shares * px
            acct["position"] = {"fund": fund, "shares": shares, "entry_date": day, "entry_price": px,
                                "why": why, "synced": synced}
            fill(day, "buy", fund, px, shares, why, synced=synced)
        eq = equity(acct, closes)
        prev = acct["marks"][-1]["equity"] if acct["marks"] else acct["start_cash"]
        p = acct["position"]
        acct["marks"].append({"date": day, "equity": round(eq, 2), "day_pnl": round(eq - prev, 2),
                              "cash": round(acct["cash"], 2), "fund": p["fund"] if p else None,
                              "close": round(closes[p["fund"]], 4) if p else None})
        acct["last_date"] = day

    # ---- the orders for the next open, as this paper account holds
    p = acct["position"]
    o_sells = [{"fund": t.symbol, "why": t.exit_reason} for t in trades
               if t.exit_date == nxt and t.exit_reason != END_REASON and p and p["fund"] == t.symbol]
    o_buys = [{"fund": t.symbol, "why": t.entry_reason, "synced": False} for t in trades if t.entry_date == nxt]
    if nxt == acct["start"] and p is None and not o_buys:
        t = _held_into(trades, nxt, nxt)
        if t is not None:
            o_buys = [{"fund": t.symbol, "synced": True,
                       "why": f"synced at go-live: the strategy has held {t.symbol} since {t.entry_date} "
                              f"({t.entry_reason})"}]
    if p is not None and not o_sells:
        o_buys = []
    if nxt < acct["start"]:
        o_sells, o_buys = [], []          # not trading yet
    acct["orders"] = {"after_close": last, "for_open": nxt, "sells": o_sells, "buys": o_buys}
    if with_levels:
        acct["levels"] = {"after_close": last, "funds": levels(acct, u)}
    return new


def universe_for(acct: dict, cache: Dict[str, Tuple[Bars, bool]], keep_provisional: bool = False) -> Universe:
    for f in acct["funds"]:
        if f not in cache:
            cache[f] = latest_bars(f)
    u = align({f: cache[f][0] for f in acct["funds"]})
    if any(cache[f][1] for f in acct["funds"]) and not keep_provisional:
        u = u.slice(0, len(u) - 1)       # the session is still trading: next run
    return u


# ------------------------------------------------------------------ markdown
def money(x: float, sign: bool = False) -> str:
    s = f"${abs(x):,.0f}"
    if x < 0:
        return "-" + s
    return ("+" + s) if sign else s


def day_name(d: str) -> str:
    return Date.fromisoformat(d).strftime("%a %b %-d")


def bot_title(a: dict) -> str:
    name = a["name"]
    if ": " in name:            # a grid strategy's settings: keep the shape, the rank says the rest
        name = name.split(": ")[0] + (f" (#{a['rank']})" if a.get("rank") else "")
    return f"{a['label']} {name}" if a["label"].startswith("#") else f"{a['label']}: {name}"


def accounts_md(ledger: dict) -> str:
    rows = ["| Bot | Size | Equity | Since its start | Last session | Position |",
            "| --- | --- | --- | --- | --- | --- |"]
    groups: Dict[str, List[float]] = {}
    for a in ledger["accounts"]:
        m = a["marks"][-1] if a["marks"] else None
        eq = m["equity"] if m else a["start_cash"]
        p = a["position"]
        if p:
            px = m["close"] if m and m["fund"] == p["fund"] else p["entry_price"]
            pos = (f"{p['fund']} since {day_name(p['entry_date'])} at ${p['entry_price']:,.2f}, "
                   f"{(px / p['entry_price'] - 1) * 100:+.1f}%")
        else:
            pos = "cash"
        size = f"{a['size']:.0%}" if not a.get("group") else f"a third ({money(a['start_cash'])})"
        started = money(m["day_pnl"], True) if m else f"starts {day_name(a['start'])}"
        rows.append(f"| {bot_title(a)} | {size} | {money(eq)} | {money(eq - a['start_cash'], True)} "
                    f"({(eq / a['start_cash'] - 1) * 100:+.1f}%) | {started} | {pos} |")
        if a.get("group"):
            g = groups.setdefault(a["group"], [0.0, 0.0, 0.0])
            g[0] += eq
            g[1] += a["start_cash"]
            g[2] += m["day_pnl"] if m else 0.0
    for name, (eq, start, day) in groups.items():
        rows.append(f"| **{name}, total** | $25,000 | **{money(eq)}** | **{money(eq - start, True)}** "
                    f"({(eq / start - 1) * 100:+.1f}%) | {money(day, True)} | |")
    return "\n".join(rows)


def _why(text: str) -> str:
    return text.replace("entry rule: ", "rule ").replace("exit rule: ", "rule ")


def orders_md(ledger: dict) -> str:
    lines = []
    for a in ledger["accounts"]:
        o, lv = a["orders"], (a.get("levels") or {}).get("funds", {})
        if not o:
            lines.append(f"- **{bot_title(a)}.** Starts at the {day_name(a['start'])} open; its orders are set by "
                         f"the first run after a close.")
            continue
        acts = [f"**sell {x['fund']}** ({_why(x['why'])})" for x in o.get("sells", [])]
        share = f"its third ({money(a['start_cash'])})" if a.get("group") else f"{a['size']:.0%} of the account"
        acts += [f"**buy {x['fund']}**{' (synced)' if x.get('synced') else ''} with {share}"
                 for x in o.get("buys", [])]
        p = a["position"]
        now = ("; ".join(acts) if acts else
               (f"hold {p['fund']}" if p else "nothing, stays in cash"))
        if o["for_open"] < a["start"]:
            lines.append(f"- **{bot_title(a)}.** Starts at the {day_name(a['start'])} open; its first orders "
                         f"are set after the {day_name(o['for_open'])} close.")
            continue
        lines.append(f"- **{bot_title(a)}.** At the {day_name(o['for_open'])} open: {now}.")
        for fund, ranges in lv.items():
            if len(ranges) < 2:
                continue
            parts = []
            for k, r in enumerate(ranges):
                if k == 0:
                    where = f"at or below ${r['price_to']:,.2f}"
                elif k == len(ranges) - 1:
                    where = f"above ${ranges[k - 1]['price_to']:,.2f}"
                else:
                    where = f"above ${ranges[k - 1]['price_to']:,.2f} up to ${r['price_to']:,.2f}"
                parts.append(f"{where}: {r['action']}")
            lines.append(f"  - If {fund} closes " + "; ".join(parts) + ".")
    return "\n".join(lines)


def trades_md(ledger: dict) -> str:
    rows = ["| Bot | Fund | Bought | Sold | P&L | Return | Why it sold |", "| --- | --- | --- | --- | --- | --- | --- |"]
    n = 0
    for a in ledger["accounts"]:
        for t in a["closed"]:
            n += 1
            rows.append(f"| {a['label']} | {t['fund']} | {day_name(t['bought'])} at ${t['entry']:,.2f} | "
                        f"{day_name(t['sold'])} at ${t['exit']:,.2f} | {money(t['pnl'], True)} | "
                        f"{t['ret'] * 100:+.1f}% | {_why(t['why_out'])} |")
    return "\n".join(rows) if n else "No closed trades yet."


def day_md(ledger: dict, fills: Dict[str, List[dict]]) -> str:
    """The notes for one run: each bot's fills, where it stands, its orders."""
    lines = []
    for a in ledger["accounts"]:
        m = a["marks"][-1] if a["marks"] else None
        bits = []
        for f in fills.get(a["id"], []):
            bits.append(f"{'bought' if f['side'] == 'buy' else 'sold'} {f['shares']:,.1f} {f['fund']} at "
                        f"${f['price']:,.2f} on the {day_name(f['date'])} open ({_why(f['why'])})")
        p = a["position"]
        if m:
            where = (f"holding {p['fund']} at the ${m['close']:,.2f} close, {(m['close'] / p['entry_price'] - 1) * 100:+.1f}% "
                     f"on the position" if p else "in cash")
            bits.append(f"{where}; equity {money(m['equity'])} ({money(m['day_pnl'], True)} on the day, "
                        f"{money(m['equity'] - a['start_cash'], True)} since {day_name(a['start'])[4:]})")
        lines.append(f"- **{bot_title(a)}:** " + ("; ".join(bits) if bits else "not started") + ".")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="show", choices=["accounts", "orders", "trades"])
    ap.add_argument("--no-levels", action="store_true")
    ap.add_argument("--retire", default="", help="bot ids to take off the roster, comma separated")
    ap.add_argument("--why", default="")
    ap.add_argument("--restore", default="", help="retired bot ids to put back on the roster, comma separated")
    ap.add_argument("--add-split", action="store_true", help="open the three-bot split account")
    ap.add_argument("--add", default="", help="id of a bot to open for the published strategy --rank")
    ap.add_argument("--rank", type=int, default=0)
    ap.add_argument("--funds", default="", help="funds to run it on instead of its own, comma separated")
    ap.add_argument("--label", default="")
    ap.add_argument("--name", default="", help="the added bot's name, when its funds are not the strategy's own")
    ap.add_argument("--start", default="", help="first session for bots added now")
    ap.add_argument("--snapshot", action="store_true",
                    help="mark every account at the latest prices, the session still trading included; "
                         "nothing is recorded")
    args = ap.parse_args(argv)
    ledger = load_ledger()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if args.retire:
        retire(ledger, args.retire.split(","), args.why, today)
    if args.restore:
        restore(ledger, args.restore.split(","))
    if args.add_split:
        add_split(ledger, args.start or today)
    if args.add:
        add_bot(ledger, args.add, args.rank, [f for f in args.funds.split(",") if f], args.label or args.add,
                args.start or today, args.name)
    if args.retire or args.restore or args.add_split or args.add:
        PAPER.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=1))        # a roster change stands on its own
    if args.show:
        print({"accounts": accounts_md, "orders": orders_md, "trades": trades_md}[args.show](ledger))
        return 0
    if not ledger["accounts"]:
        bots = bot_list()
        items = {v["rank"]: v for v in load_items([b["rank"] for b in bots])}
        ledger["accounts"] = [open_account(b, items[b["rank"]]) for b in bots]
    cache: Dict[str, Tuple[Bars, bool]] = {}
    fills: Dict[str, List[dict]] = {}
    if args.snapshot:
        view = copy.deepcopy(ledger)
        for a in view["accounts"]:
            fills[a["id"]] = advance(a, universe_for(a, cache, keep_provisional=True), with_levels=False)
        live = any(prov for _, prov in cache.values())
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"# Snapshot at {stamp}{' (the session is still trading: marks are provisional)' if live else ''}",
              "", day_md(view, fills), "", accounts_md(view), sep="\n")
        return 0
    last = ""
    for a in ledger["accounts"]:
        u = universe_for(a, cache)
        fills[a["id"]] = advance(a, u, with_levels=not args.no_levels)
        last = max(last, u.calendar[-1])
        print(f"{a['id']}: {len(fills[a['id']])} fills, orders {a['orders']['sells']} {a['orders']['buys']}",
              flush=True)
    ledger["updated_after_close"] = last
    PAPER.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1))
    notes = "\n".join([f"# Paper trail after the {last} close", "", "## Where each bot stands", "",
                       day_md(ledger, fills), "", "## Accounts", "", accounts_md(ledger), "",
                       "## Orders for the next open", "", orders_md(ledger), "", "## Closed trades", "",
                       trades_md(ledger), ""])
    (PAPER / f"{last}.md").write_text(notes)
    print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
