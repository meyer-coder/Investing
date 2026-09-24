"""The Own-Drop Scalper: the one scalping bot this research kept.

    python strategies/scalp/owndrop.py      # its tests, into profitable-strategies/scalping/own-drop/backtest.json

It watches 47 liquid names (minute.POOL_NAMES).  On any bar from 09:35 to
09:45 New York it buys a name that fell hard on its own that minute: a
one-minute return below -0.75 of its 14-minute average range (ATR as a share
of price), and more than two standard deviations below the other 46 names'
average return that minute, judged against its own last 20 such gaps
(resid_z, residbot.add_residual).  The buy fills at the next minute's open
and the sale at the open four minutes after it.  At most three positions,
each a third of buying power; nothing is held past 15:55, and in practice
every trade is over by 09:50.

A drop the whole market shares is news and tends to run on; one a name takes
alone is usually a seller leaning on the book, and it snaps back.  The two
halves came from different studies: the opening dip (events.py, bot.py) was
found on 17 names and did not carry over to 30 fresh ones; the residual drop
(residual.py) was found on the 17 and did carry over.  Together they kept
both groups of names profitable (residbot.py's grid, then this file).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from events import cost_bp                                                   # noqa: E402
from residbot import ALLOWED, POOL, universe                                 # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

ACCOUNT = 25_000.0
LEVERAGE = 2.0                 # the paper trail's buying power: 2x a $25,000 account
OUT = ROOT / "profitable-strategies" / "scalping" / "own-drop"
NY = ZoneInfo("America/New_York")


def entry(late: bool = False) -> str:
    """The buy rule; `late` acts on the same signal a minute later, to see
    what a slow fill costs."""
    if late:
        return ("prev(ret1) < -0.75 * prev(atr_pct) and prev(resid_z) < -2.0 "
                "and minutes_since_open >= 6 and minutes_since_open <= 16")
    return "ret1 < -0.75 * atr_pct and resid_z < -2.0 and minutes_since_open >= 5 and minutes_since_open <= 15"


def bot(late: bool = False) -> Genome:
    return Genome.from_dict({
        "name": "Own-Drop Scalper",
        "thesis": "a name's own sharp drop in the opening minutes, one the rest of the market does not share, "
                  "snaps back within minutes",
        "entry_rules": [{"when": entry(late), "weight": 1.0}],
        "exit_rules": [{"when": "minute_of_day >= 955"}],
        "risk": {"max_position_pct": 1.0 / 3, "max_positions": 3, "max_gross_exposure": 1.0,
                 "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "trailing_stop_pct": 0.0,
                 "max_hold_bars": 3}})


def et(stamp: str) -> str:
    t = datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return t.astimezone(NY).strftime("%H:%M")


def test(u, f, slip: Dict[str, float], leverage: float = 1.0, mult: float = 1.0, late: bool = False) -> dict:
    """One run over the whole archive: dollars a day on $25,000 (each session
    measured on the account as it stood that morning, scaled to $25,000)."""
    r = run_backtest(compile_genome(bot(late), ALLOWED), u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                     slippage_bps=2.0, record_thoughts=False, intrabar_stops=True, leverage=leverage,
                     slippage_by_symbol={s: v * mult for s, v in slip.items()})
    j = r.journal
    last: Dict[str, float] = {}
    for st, e in zip(j.equity_dates, j.equity):
        last[minute.session_of(st)] = float(e)
    prev, days = ACCOUNT, {}
    for d in sorted(last):
        days[d] = (last[d] / prev - 1.0) * ACCOUNT
        prev = last[d]
    usd = np.array(list(days.values()))
    t = j.trades
    orig = set(minute.SCALP_NAMES)
    names: Dict[str, list] = defaultdict(list)
    for x in t:
        names[x.symbol].append(x.pnl)
    assert all(minute.session_of(x.exit_date) == minute.session_of(x.entry_date) for x in t), "held overnight"
    return {"usd_per_day": round(float(usd.mean()), 1), "median": round(float(np.median(usd)), 1),
            "days_up": round(float((usd > 0).mean()), 3), "days_100_plus": round(float((usd >= 100).mean()), 3),
            "worst_day": round(float(usd.min()), 0), "best_day": round(float(usd.max()), 0),
            "trades_per_day": round(len(t) / len(usd), 1),
            "win_rate": round(float(np.mean([x.pnl > 0 for x in t])), 3) if t else 0.0,
            "avg_trade_bp": round(float(np.mean([x.ret for x in t])) * 1e4, 1) if t else 0.0,
            "avg_hold_min": round(float(np.mean([x.bars_held for x in t])), 2) if t else 0.0,
            "last_exit_et": max((et(x.exit_date) for x in t), default=""),
            "pnl_original_names": round(sum(x.pnl for x in t if x.symbol in orig), 0),
            "pnl_fresh_names": round(sum(x.pnl for x in t if x.symbol not in orig), 0),
            "by_name": {s: {"trades": len(v), "pnl": round(sum(v), 0)}
                        for s, v in sorted(names.items(), key=lambda kv: -sum(kv[1]))},
            "by_day": {d: round(v, 0) for d, v in days.items()}}


def main() -> int:
    days = minute.sessions(POOL)
    u, f = universe(days)
    slip = {s: cost_bp(np.asarray(u.bars[s].close)) for s in POOL}
    out = {"sessions": [days[0], days[-1], len(days)], "account": ACCOUNT, "bot": bot().to_dict(), "runs": {}}
    runs = {f"{lev:g}x": dict(leverage=lev) for lev in (1.0, 1.5, 2.0)}
    runs.update({"1x, costs doubled": dict(mult=2.0), "1x, costs tripled": dict(mult=3.0),
                 "2x, costs doubled": dict(leverage=2.0, mult=2.0),
                 "1x, a minute late": dict(late=True), "2x, a minute late": dict(leverage=2.0, late=True)})
    for key, kw in runs.items():
        r = out["runs"][key] = test(u, f, slip, **kw)
        by = list(r["by_day"].values())
        weeks = [round(float(np.mean(by[a:b])), 0) for a, b in ((0, 7), (7, 14), (14, len(by)))]
        r["weeks"] = weeks
        print(f"{key:20s} ${r['usd_per_day']:5.0f}/day median ${r['median']:5.0f} up {r['days_up']:.0%} "
              f">=$100 {r['days_100_plus']:.0%} worst ${r['worst_day']:5.0f} | weeks {weeks} | "
              f"{r['trades_per_day']} tr/d win {r['win_rate']:.0%} {r['avg_trade_bp']:+.1f}bp hold {r['avg_hold_min']}m "
              f"last exit {r['last_exit_et']} | orig ${r['pnl_original_names']:.0f} fresh ${r['pnl_fresh_names']:.0f}",
              flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    OUT.joinpath("backtest.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
