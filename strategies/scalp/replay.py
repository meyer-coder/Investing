"""Paper-trade the opening dip scalper forward: each finished session replayed
minute by minute from the archive, every trade written once to a ledger.

    python strategies/scalp/replay.py            # replay the sessions since the last one recorded

The scalper is fixed here, as tested (bot.py): buy a name whose one-minute
return falls more than 0.75 of its 14-minute average range as a share of price,
from the 09:35 bar to the 09:45 bar New York, at the next minute's open; sell
four minutes later at the open; at most two positions, each 62.5% of a $25,000
account (1.25x buying power, as a margin account's day-trading power allows);
flat by the 15:55 bar in any case.  Costs: a cent plus 1 bp each way, at each
name's price that day.

The session before each one is replayed too, only so the 14-minute range is
defined at 09:35.  Each session starts at $25,000: the ledger's dollars a day
are that account's.  Writes profitable-strategies/scalping/opening-dip/paper.json
and paper/<date>.md.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from bot import bot                                                          # noqa: E402
from events import NAMES, cost_bp                                           # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import compile_genome                                 # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

GO_LIVE = "2026-09-24"
ACCOUNT, LEVERAGE = 25_000.0, 1.25
PARAMS = (0.75, 15, "", 4, 2)                 # drop in ranges, window minutes, filter, hold minutes, slots
OUT = ROOT / "profitable-strategies" / "scalping" / "opening-dip"
LEDGER = OUT / "paper.json"
NY = ZoneInfo("America/New_York")


def et(stamp: str) -> str:
    t = datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return t.astimezone(NY).strftime("%H:%M")


def replay(day: str, before: str) -> dict:
    u = minute.universe(NAMES, [before, day])
    f = build_features(u)
    idx = [i for i, t in enumerate(u.calendar) if minute.session_of(t) == day]
    slip = {s: cost_bp(np.asarray(u.bars[s].close)[idx]) for s in NAMES}
    r = run_backtest(compile_genome(bot(*PARAMS)), u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                     slippage_bps=2.0, record_thoughts=False, intrabar_stops=True,
                     slippage_by_symbol=slip, leverage=LEVERAGE, start_bar=idx[0] - 30)
    trades = [t for t in r.journal.trades if minute.session_of(t.entry_date) == day]
    assert all(minute.session_of(t.exit_date) == day for t in trades), "a position crossed the close"
    rows = [{"name": t.symbol, "in": et(t.entry_date), "out": et(t.exit_date), "entry": round(t.entry_price, 4),
             "exit": round(t.exit_price, 4), "shares": round(t.shares, 2),
             "size": round(t.shares * t.entry_price, 0), "pnl": round(t.pnl, 2), "ret_bp": round(t.ret * 1e4, 1),
             "minutes": t.bars_held} for t in trades]
    return {"pnl": round(sum(x["pnl"] for x in rows), 2), "trades": rows}


def main() -> int:
    minute.update(NAMES)
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
        "bot": bot(*PARAMS).to_dict(), "go_live": GO_LIVE, "account": ACCOUNT, "leverage": LEVERAGE,
        "sessions": {}}
    days = minute.sessions(NAMES)
    new = [d for d in days if d >= GO_LIVE and d not in ledger["sessions"]]
    OUT.joinpath("paper").mkdir(parents=True, exist_ok=True)
    for d in new:
        before = days[days.index(d) - 1]
        res = replay(d, before)
        ledger["sessions"][d] = res
        lines = [f"# Opening dip scalper, {d}", "",
                 f"Paper, $25,000 at {LEVERAGE:g}x buying power. P&L {res['pnl']:+,.2f} over "
                 f"{len(res['trades'])} trades.", ""]
        if res["trades"]:
            lines += ["| Name | In (ET) | Out (ET) | Entry | Exit | Size | P&L | bp |",
                      "| --- | --- | --- | --- | --- | --- | --- | --- |"]
            lines += [f"| {x['name']} | {x['in']} | {x['out']} | ${x['entry']:,.2f} | ${x['exit']:,.2f} | "
                      f"${x['size']:,.0f} | {x['pnl']:+,.2f} | {x['ret_bp']:+.1f} |" for x in res["trades"]]
        OUT.joinpath("paper", f"{d}.md").write_text("\n".join(lines) + "\n")
        print(f"{d}: {res['pnl']:+.2f} over {len(res['trades'])} trades", flush=True)
    pnl = [v["pnl"] for v in ledger["sessions"].values()]
    ledger["summary"] = {"sessions": len(pnl), "total": round(sum(pnl), 2),
                         "per_day": round(float(np.mean(pnl)), 2) if pnl else 0.0,
                         "days_up": round(float(np.mean([p > 0 for p in pnl])), 3) if pnl else 0.0,
                         "worst_day": min(pnl) if pnl else 0.0}
    LEDGER.write_text(json.dumps(ledger, indent=1))
    print(json.dumps(ledger["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
