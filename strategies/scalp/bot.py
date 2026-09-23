"""The opening dip-buyer: one bot, one-to-four-minute trades, never past the close.

    python strategies/scalp/bot.py

Across 17 liquid, fast-moving names it buys a sharp one-minute drop in the
first minutes after 09:35 New York and sells a few minutes later, betting on
the snap back that the event study (events.py) found in both halves of the
data.  Variants differ in how big the drop must be, how long the morning
window stays open, a filter, and how many positions run at once (each slot
gets an equal share of the account).

Every run: $25,000, decisions on each minute's close, fills at the next
minute's open, each name's own cost (a cent plus 1 bp each way), nothing held
after 15:55.  Chosen on the first 14 sessions, tested on the last 7.

Writes strategies/scalp/bot.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from events import NAMES, cost_bp                                           # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

ACCOUNT = 25_000.0
OUT = ROOT / "strategies" / "scalp" / "bot.json"
FLAT = "minute_of_day >= 955"


def bot(k: float, window: int, filt: str, hold: int, slots: int, stop: float = 0.0,
        target: float = 0.0) -> Genome:
    cond = f"ret1 < -{k} * atr_pct and minutes_since_open >= 5 and minutes_since_open <= {window}"
    if filt:
        cond += f" and {filt}"
    return Genome.from_dict({
        "name": f"Opening Dip {k}atr/{window}m/{filt or 'none'}/hold {hold}m/{slots} slots"
                + (f"/stop {stop}" if stop else "") + (f"/target {target}" if target else ""),
        "thesis": "sharp one-minute drops in the opening minutes snap back",
        "entry_rules": [{"when": cond, "weight": 1.0}],
        "exit_rules": [{"when": FLAT}],
        # the engine exits after max_hold_bars bars at the next open: hold - 1 bars is a hold of `hold` minutes
        "risk": {"max_position_pct": 1.0 / slots, "max_positions": slots, "max_gross_exposure": 1.0,
                 "stop_loss_pct": stop, "take_profit_pct": target, "trailing_stop_pct": 0.0,
                 "max_hold_bars": hold - 1}})


def run(g: Genome, u, f, slip: Dict[str, float], mult: float = 1.0) -> dict:
    r = run_backtest(compile_genome(g), u, f, starting_cash=ACCOUNT, commission_bps=0.0, slippage_bps=2.0,
                     record_thoughts=False, intrabar_stops=True,
                     slippage_by_symbol={s: v * mult for s, v in slip.items()})
    j = r.journal
    last: Dict[str, float] = {}
    for stamp, e in zip(j.equity_dates, j.equity):
        last[minute.session_of(stamp)] = float(e)
    prev, days = ACCOUNT, {}
    for d in sorted(last):
        days[d] = (last[d] / prev - 1.0) * ACCOUNT
        prev = last[d]
    usd = np.array(list(days.values()))
    t = j.trades
    wins = [x for x in t if x.pnl > 0]
    by_name: Dict[str, float] = {}
    for x in t:
        by_name[x.symbol] = by_name.get(x.symbol, 0.0) + x.pnl
    eq = np.concatenate([[ACCOUNT], np.asarray(j.equity, dtype=float)])
    return {"usd_per_day": round(float(usd.mean()), 1), "days_up": round(float((usd > 0).mean()), 3),
            "worst_day": round(float(usd.min()), 0), "best_day": round(float(usd.max()), 0),
            "trades_per_day": round(len(t) / len(usd), 1), "win_rate": round(len(wins) / len(t), 3) if t else 0,
            "avg_hold_min": round(float(np.mean([x.bars_held for x in t])), 2) if t else 0,
            "avg_trade_bp": round(float(np.mean([x.ret for x in t])) * 1e4, 1) if t else 0,
            "max_drawdown": round(float((eq / np.maximum.accumulate(eq) - 1).min()), 4),
            "names_up": sum(1 for v in by_name.values() if v > 0), "names_traded": len(by_name),
            "by_day": {d: round(v, 0) for d, v in days.items()}}


_W: dict = {}


def _init() -> None:
    days = minute.sessions(NAMES)
    ud = minute.universe(NAMES, days[:14])
    _W.update(u=ud, f=build_features(ud), slip={s: cost_bp(np.asarray(ud.bars[s].close)) for s in NAMES})


def _dev(params) -> dict:
    g = bot(*params)
    return {"name": g.name, "genome": g.to_dict(), "dev": run(g, _W["u"], _W["f"], _W["slip"])}


def main() -> int:
    from multiprocessing import Pool
    days = minute.sessions(NAMES)
    dev, test = days[:14], days[14:]
    ud, ut = minute.universe(NAMES, dev), minute.universe(NAMES, test)
    ft = build_features(ut)
    slip = {s: cost_bp(np.asarray(ud.bars[s].close)) for s in NAMES}
    grid = list(itertools.product((0.5, 0.75, 1.0), (15, 20, 30), ("", "sma20_slope > 0", "dist_session_vwap < 0"),
                                  (3, 4), (1, 2, 4)))
    with Pool(4, initializer=_init) as pool:
        rows = []
        for x in pool.imap_unordered(_dev, grid):
            rows.append(x)
            d = x["dev"]
            print(f"{x['name'][:62]:62s} dev ${d['usd_per_day']:6.0f}/day up {d['days_up']:.0%} "
                  f"{d['trades_per_day']:5.1f} tr/d {d['avg_trade_bp']:+5.1f}bp", flush=True)
    rows.sort(key=lambda x: x["dev"]["usd_per_day"], reverse=True)
    for x in rows[:15]:
        g = Genome.from_dict(x["genome"])
        x["test"] = run(g, ut, ft, slip)
        x["test_2x_cost"] = run(g, ut, ft, slip, mult=2.0)["usd_per_day"]
    OUT.write_text(json.dumps({"sessions": {"dev": dev, "test": test}, "slippage_bp": slip, "bots": rows},
                              indent=1))
    print("\nBest 15 by the first 14 sessions, and their last 7:")
    for x in rows[:15]:
        d, t = x["dev"], x["test"]
        print(f"  {x['name'][:60]:60s} dev ${d['usd_per_day']:5.0f} up {d['days_up']:.0%} worst ${d['worst_day']:5.0f} | "
              f"test ${t['usd_per_day']:5.0f} up {t['days_up']:.0%} worst ${t['worst_day']:5.0f} "
              f"{t['trades_per_day']:4.1f} tr/d win {t['win_rate']:.0%} {t['avg_trade_bp']:+5.1f}bp hold {t['avg_hold_min']:.1f}m "
              f"names+ {t['names_up']}/{t['names_traded']} | 2x cost ${x['test_2x_cost']:5.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
