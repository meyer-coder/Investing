"""Three one-minute SOXL bots: one long, one short, one that fades snaps.

    python strategies/soxl/bots.py

* **Long** trades SOXL up: bursts on volume above the session VWAP, dips in a
  rising tape, the opening-range breakout.
* **Short** trades SOXL down by buying SOXS, the 3x inverse fund, with the
  same shapes; SOXS rises when SOXL falls.
* **Snapback** fades a sharp one- or two-minute move either way: it buys
  SOXL after a flush and SOXS after a spike, betting on the snap back.

Every trade is intraday: entries from 09:35 to 15:45 New York, out by the
15:55 close of the bar at the latest, and a hold capped at four minutes.  The
engine decides on each minute's close and fills at the next minute's open,
with slippage of 2 bp a side on SOXL and 3 bp on SOXS (a cent is 0.7 bp of
SOXL's price and 3 bp of SOXS's).  Settings are chosen on the first 14
sessions of the archive and tested on the rest, which the choice never saw.

Writes strategies/soxl/bots.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
import minute                                                                # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

ACCOUNT = 25_000.0
SLIP = {"SOXL": 2.0, "SOXS": 3.0, "SOXL.SHORT": 2.0}
OUT = ROOT / "strategies" / "soxl" / "bots.json"
WINDOW = "minutes_since_open >= 5 and minute_of_day < 945"      # 09:35 to 15:45
FLAT = "minute_of_day >= 955"                                    # out by the 15:55 bar


def g(name: str, entries: Sequence[str], exits: Sequence[str] = (), **risk) -> Genome:
    return Genome.from_dict({
        "name": name, "thesis": name,
        "entry_rules": [{"when": f"({e}) and {WINDOW}", "weight": 1.0} for e in entries],
        "exit_rules": [{"when": x} for x in (*exits, FLAT)],
        "risk": {"max_position_pct": 1.0, "max_positions": 1, "max_gross_exposure": 1.0,
                 "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "trailing_stop_pct": 0.0,
                 "max_hold_bars": 4, **risk}})


def trend_shapes(tag: str) -> Iterable[Genome]:
    """Shapes for a fund that should rise: SOXL for the long bot, SOXS for the short."""
    for b, v, h, tp, sl in itertools.product((0.002, 0.003, 0.005), (1.5, 2.5), (1, 2, 4),
                                             (0.003, 0.006), (0.003, 0.006)):
        yield g(f"{tag} Burst {b}/{v}/{h}/{tp}/{sl}",
                [f"ret1 > {b} and volume_ratio > {v} and dist_session_vwap > 0"],
                max_hold_bars=h, take_profit_pct=tp, stop_loss_pct=sl)
    for d, h, sl in itertools.product((0.002, 0.003, 0.005), (2, 4), (0.004, 0.008)):
        yield g(f"{tag} Rising-Tape Dip {d}/{h}/{sl}",
                [f"ret1 < -{d} and dist_session_vwap > 0 and sma20_slope > 0"], ["ret1 > 0"],
                max_hold_bars=h, stop_loss_pct=sl)
    for v, h, tp, sl in itertools.product((1.2, 2.0), (2, 4), (0.004, 0.008), (0.004, 0.008)):
        yield g(f"{tag} VWAP Reclaim {v}/{h}/{tp}/{sl}",
                [f"cross_above(close, session_vwap) and volume_ratio > {v}"],
                max_hold_bars=h, take_profit_pct=tp, stop_loss_pct=sl)
    for h, tp, sl in itertools.product((2, 4), (0.004, 0.008), (0.004, 0.008)):
        yield g(f"{tag} Range Break {h}/{tp}/{sl}",
                ["cross_above(close, opening_range_high)"],
                max_hold_bars=h, take_profit_pct=tp, stop_loss_pct=sl)


def snap_shapes() -> Iterable[Genome]:
    for k, z, h, sl in itertools.product((0.006, 0.01, 0.015), (1.5, 2.5), (1, 2, 4), (0.005, 0.01)):
        yield g(f"Snapback Flush {k}/{z}/{h}/{sl}",
                [f"ret1 + prev(ret1) < -{k} and zscore20 < -{z}"],
                max_hold_bars=h, stop_loss_pct=sl)
    for r, dv, h in itertools.product((10, 20), (0.005, 0.01), (2, 4)):
        yield g(f"Snapback Oversold {r}/{dv}/{h}",
                [f"rsi7 < {r} and dist_session_vwap < -{dv}"], ["rsi7 > 50"],
                max_hold_bars=h, stop_loss_pct=0.01)


def snap_shapes_wide() -> Iterable[Genome]:
    """Second pass: fade one- and two-minute snaps across more thresholds,
    with a quick target, at any hour or in the first two hours only."""
    hours = {"all day": "minute_of_day > 0", "first two hours": "minute_of_day < 690"}
    for (hn, hw), k, z, h, sl, tp in itertools.product(hours.items(), (0.004, 0.005, 0.008), (2.0, 3.0),
                                                        (2, 4), (0.005, 0.01), (0.0, 0.003)):
        yield g(f"Snapback 2m {hn} {k}/{z}/{h}/{sl}/{tp}",
                [f"ret1 + prev(ret1) < -{k} and zscore20 < -{z} and {hw}"],
                max_hold_bars=h, stop_loss_pct=sl, take_profit_pct=tp)
    for (hn, hw), k, h, sl in itertools.product(hours.items(), (0.004, 0.006, 0.01), (1, 2, 4), (0.005, 0.01)):
        yield g(f"Snapback 1m {hn} {k}/{h}/{sl}",
                [f"ret1 < -{k} and {hw}"], max_hold_bars=h, stop_loss_pct=sl)


def drive_shapes(tag: str) -> Iterable[Genome]:
    """The opening drive: a strong first move after 09:31, ridden one to four minutes."""
    for b, h, tp, sl in itertools.product((0.003, 0.005, 0.008), (1, 2, 4), (0.0, 0.005), (0.004, 0.008)):
        yield Genome.from_dict({
            "name": f"{tag} Opening Drive {b}/{h}/{tp}/{sl}", "thesis": "opening drive",
            "entry_rules": [{"when": f"ret1 > {b} and minutes_since_open >= 1 and minutes_since_open <= 30",
                             "weight": 1.0}],
            "exit_rules": [{"when": FLAT}],
            "risk": {"max_position_pct": 1.0, "max_positions": 1, "max_gross_exposure": 1.0,
                     "stop_loss_pct": sl, "take_profit_pct": tp, "trailing_stop_pct": 0.0, "max_hold_bars": h}})


BOTS = {
    "long": (["SOXL"], lambda: itertools.chain(trend_shapes("Long"), drive_shapes("Long"))),
    "short": (["SOXS"], lambda: itertools.chain(trend_shapes("Short"), drive_shapes("Short"))),
    "short_direct": (["SOXL.SHORT"], lambda: itertools.chain(trend_shapes("Short SOXL"),
                                                             drive_shapes("Short SOXL"))),
    "snapback": (["SOXL", "SOXS"], lambda: itertools.chain(snap_shapes(), snap_shapes_wide())),
}


def evaluate(genome: Genome, u, f, slip: float) -> dict:
    r = run_backtest(compile_genome(genome), u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                     slippage_bps=slip, record_thoughts=False, intrabar_stops=True)
    j = r.journal
    eq = np.asarray(j.equity, dtype=float)
    by_day: Dict[str, float] = {}
    prev = ACCOUNT
    last_eq: Dict[str, float] = {}
    for stamp, e in zip(j.equity_dates, eq):
        last_eq[minute.session_of(stamp)] = float(e)
    days = sorted(last_eq)
    for d in days:
        by_day[d] = (last_eq[d] / prev - 1.0) * ACCOUNT
        prev = last_eq[d]
    trades = j.trades
    wins = [t for t in trades if t.pnl > 0]
    loss = [t for t in trades if t.pnl <= 0]
    day_usd = np.array(list(by_day.values())) if by_day else np.zeros(1)
    run_eq = np.concatenate([[ACCOUNT], eq])
    return {"usd_per_day": round(float(day_usd.mean()), 1), "days": len(by_day),
            "days_up": round(float((day_usd > 0).mean()), 3), "worst_day": round(float(day_usd.min()), 0),
            "best_day": round(float(day_usd.max()), 0),
            "max_drawdown": round(float((run_eq / np.maximum.accumulate(run_eq) - 1).min()), 4),
            "trades": len(trades), "trades_per_day": round(len(trades) / max(len(by_day), 1), 1),
            "win_rate": round(len(wins) / len(trades), 3) if trades else 0.0,
            "avg_win": round(float(np.mean([t.ret for t in wins])), 5) if wins else 0.0,
            "avg_loss": round(float(np.mean([t.ret for t in loss])), 5) if loss else 0.0,
            "avg_hold_min": round(float(np.mean([t.bars_held for t in trades])), 2) if trades else 0.0,
            "profit_factor": round(sum(t.pnl for t in wins) / max(-sum(t.pnl for t in loss), 1e-9), 2)
            if trades else 0.0,
            "by_day": {d: round(v, 0) for d, v in by_day.items()}}


def main() -> int:
    days = minute.sessions()
    dev, test = days[:14], days[14:]
    print(f"{len(days)} sessions: choose on {dev[0]}..{dev[-1]}, test on {test[0]}..{test[-1]}", flush=True)
    out = {"sessions": {"dev": dev, "test": test}, "bots": {}}
    for bot, (symbols, shapes) in BOTS.items():
        slip = max(SLIP[s] for s in symbols)
        ud, ut = minute.universe(symbols, dev), minute.universe(symbols, test)
        fd, ft = build_features(ud), build_features(ut)
        rows = []
        for genome in shapes():
            d = evaluate(genome, ud, fd, slip)
            if d["trades"] < 20:
                continue
            rows.append({"name": genome.name, "genome": genome.to_dict(), "dev": d})
        rows.sort(key=lambda x: x["dev"]["usd_per_day"], reverse=True)
        for x in rows[:12]:
            x["test"] = evaluate(Genome.from_dict(x["genome"]), ut, ft, slip)
            x["test_2x_cost"] = evaluate(Genome.from_dict(x["genome"]), ut, ft, 2 * slip)["usd_per_day"]
        out["bots"][bot] = rows
        print(f"\n== {bot} ({', '.join(symbols)}, {slip:g} bp a side): {len(rows)} shapes with 20+ trades")
        for x in rows[:12]:
            d, t = x["dev"], x["test"]
            print(f"  {x['name'][:40]:40s} dev ${d['usd_per_day']:6.0f}/day {d['trades_per_day']:5.1f} tr/day "
                  f"win {d['win_rate']:.0%} hold {d['avg_hold_min']:.1f}m | test ${t['usd_per_day']:6.0f}/day "
                  f"up {t['days_up']:.0%} worst ${t['worst_day']:6.0f} win {t['win_rate']:.0%} "
                  f"pf {t['profit_factor']:.2f} | 2x cost ${x['test_2x_cost']:6.0f}")
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
