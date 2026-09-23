"""Hand-bred families on every fund, through the same gauntlet as the islands.

    python strategies/etf/handbred.py [--funds SOXL,TQQQ]

Seven trade shapes a discretionary trader of leveraged tech funds would use,
each on a small grid of thresholds, on every fund: a short-trend rider, a
momentum burst, a 52-week-high breakout, a dip in a strong trend, a calm
uptrend, a washed-out RSI bounce and the turn of the month.  Profitable ones
go into strategies/etf/store.json like any island's.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import consider, load_store, save_store                     # noqa: E402
from evotrader.genome import Genome                                         # noqa: E402

FUNDS = ["SOXL", "TQQQ", "TECL", "USD", "ROM", "QLD", "FTEC.3X", "FTEC.2X", "NVDA.2X", "AMD.2X", "AVGO.2X",
         "TSM.2X", "MU.2X", "META.2X", "GOOGL.2X", "MSFT.2X", "AMZN.2X", "AAPL.2X", "TSLA.2X", "SMCI.2X",
         "ORCL.2X", "PLTR.2X", "FNGO"]


def g(name, entry, exits, **risk):
    return Genome.from_dict({"name": name, "thesis": name, "entry_rules": [{"when": entry, "weight": 1.0}],
                             "exit_rules": [{"when": x} for x in exits],
                             "risk": {"max_position_pct": 1.0, "max_positions": 1, "max_gross_exposure": 1.0,
                                      **risk}})


def families():
    for ma, trail in itertools.product((10, 20), (0.0, 0.12, 0.2)):
        yield g(f"Short-Trend Rider {ma}/{trail}", f"close > sma{ma} and sma20_slope > 0 and ret5 > 0",
                [f"close < sma{ma}"], trailing_stop_pct=trail)
    for r20, ma in itertools.product((0.15, 0.25, 0.4), (10, 20)):
        yield g(f"Momentum Burst {r20}/{ma}", f"ret20 > {r20} and close > sma{ma}", [f"close < sma{ma}"],
                trailing_stop_pct=0.15)
    for hi, trail in itertools.product((0.93, 0.97), (0.1, 0.15, 0.25)):
        yield g(f"52-Week High {hi}/{trail}", f"pct_of_52w_high > {hi} and close > sma50",
                ["pct_of_52w_high < 0.85"], trailing_stop_pct=trail)
    for drop, r20, hold in itertools.product((0.04, 0.06, 0.08), (0.1, 0.2), (2, 4)):
        yield g(f"Dip in a Strong Trend {drop}/{r20}/{hold}", f"ret1 < -{drop} and ret20 > {r20}",
                [f"bars_held >= {hold}", "ret1 > 0.05"], stop_loss_pct=0.15)
    for v, out in itertools.product((0.4, 0.6, 0.8), (1.0, 1.3)):
        yield g(f"Calm Uptrend {v}/{out}", f"vol20 < {v} and close > sma50 and sma50 > sma200",
                ["close < sma50", f"vol20 > {v * out}"], trailing_stop_pct=0.2)
    for lvl, ex in itertools.product((10, 15, 20), (50, 65)):
        yield g(f"Washed-Out RSI {lvl}/{ex}", f"rsi7 < {lvl} and close > sma200", [f"rsi7 > {ex}", "bars_held >= 6"],
                stop_loss_pct=0.15)
    for first, hold in itertools.product((25, 27), (3, 5)):
        yield g(f"Month Turn {first}/{hold}", f"day_of_month >= {first} and close > sma50",
                [f"bars_held >= {hold}"], stop_loss_pct=0.1)


def families2():
    """Second pass: faster trends, one-day bounces, and high-win-rate quick targets."""
    for fast, slow in ((12, 26), (10, 20), (10, 50)):
        a = f"ema{fast}" if fast == 12 else f"sma{fast}"
        b = f"ema{slow}" if slow == 26 else f"sma{slow}"
        yield g(f"Fast Trend {fast}/{slow}", f"close > {a} and {a} > {b}", [f"close < {b}"], trailing_stop_pct=0.15)
    for ma in (10, 20):
        yield g(f"Band Breakout {ma}", "close > bb_upper and volume_ratio > 1.2", [f"close < sma{ma}"],
                trailing_stop_pct=0.15)
    for ratio, jump in itertools.product((0.7, 0.85), (0.03, 0.05)):
        yield g(f"Squeeze Breakout {ratio}/{jump}", f"vol_ratio_20_60 < {ratio} and ret1 > {jump}",
                ["close < sma10"], trailing_stop_pct=0.12)
    for drop in (0.05, 0.07, 0.09):
        yield g(f"One-Day Bounce {drop}", f"ret1 < -{drop} and close > sma200", ["bars_held >= 1"],
                stop_loss_pct=0.12)
    for pull, ma in itertools.product((0.08, 0.12), (50, 200)):
        yield g(f"Pullback in Uptrend {pull}/{ma}", f"ret5 < -{pull} and close > sma{ma}",
                ["ret1 > 0.04", "bars_held >= 4"], stop_loss_pct=0.15)
    for drop, tp, sl in itertools.product((0.03, 0.05), (0.03, 0.05), (0.08, 0.12)):
        yield g(f"Dip, Quick Target {drop}/{tp}/{sl}", f"ret1 < -{drop} and close > sma50",
                ["bars_held >= 5"], take_profit_pct=tp, stop_loss_pct=sl)
    for lo in (0.0, 0.05):
        yield g(f"Band Floor {lo}", f"bb_pct < {lo} and close > sma200", ["bb_pct > 0.5", "bars_held >= 6"],
                stop_loss_pct=0.15)
    for jump in (0.05, 0.08):
        yield g(f"Strong Close Follow {jump}", f"ret1 > {jump} and (close - low) / (high - low + 0.0001) > 0.8",
                ["bars_held >= 2"], stop_loss_pct=0.08)


def families3():
    """Third pass: the semis rotation's idea, on any fund or basket: momentum on
    volume while the lead fund holds its 200-day, out on a slip under the 20-day."""
    for above, vol, out in itertools.product((0.0, 0.01, 0.03), (1.0, 1.2, 1.5), (0.02, 0.04)):
        yield g(f"Volume Momentum in a Bull Regime {above}/{vol}/{out}",
                f"mkt_above_sma200 == 1 and dist_sma20 > {above} and volume_ratio > {vol}",
                [f"dist_sma20 < -{out}", "mkt_above_sma200 == 0"], stop_loss_pct=0.12, cooldown_bars=5)


def g2(name, entries, exits, **risk):
    return Genome.from_dict({"name": name, "thesis": name,
                             "entry_rules": [{"when": e, "weight": 1.0} for e in entries],
                             "exit_rules": [{"when": x} for x in exits],
                             "risk": {"max_position_pct": 1.0, "max_positions": 1, "max_gross_exposure": 1.0,
                                      **risk}})


def families5():
    """Fifth pass: two doors in one strategy, a momentum entry and a dip entry,
    out on a slip under the 20-day average, as the best semis rotation does."""
    moms = {"volume momentum": "mkt_above_sma200 == 1 and dist_sma20 > 0.01 and volume_ratio > 1.2",
            "20-day burst": "ret20 > 0.2 and close > sma10",
            "fast trend": "close > ema12 and ema12 > ema26 and close > sma50"}
    dips = {"deep dip": "pct_of_52w_high < 0.75 and ret1 < -0.02",
            "uptrend flush": "ret1 < -0.05 and close > sma50",
            "oversold": "rsi7 < 20 and close > sma200"}
    for (mn, m), (dn, d), out in itertools.product(moms.items(), dips.items(), (0.02, 0.04)):
        yield g2(f"{mn.title()} or {dn.title()} {out}", [m, d], [f"dist_sma20 < -{out}"],
                 stop_loss_pct=0.12, cooldown_bars=3)


def families6():
    """Sixth pass, for a high win rate: small dips inside a trend, a quick
    target, a tight stop and a short hold."""
    for drop, tp, sl, ma, hold in itertools.product((0.02, 0.03, 0.04, 0.06), (0.02, 0.03, 0.04),
                                                     (0.04, 0.06, 0.1), (20, 50, 200), (2, 4)):
        yield g(f"Quick Dip {drop}/{tp}/{sl}/{ma}/{hold}", f"ret1 < -{drop} and close > sma{ma}",
                [f"bars_held >= {hold}"], take_profit_pct=tp, stop_loss_pct=sl)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--funds", default=",".join(FUNDS))
    ap.add_argument("--pass", dest="which", type=int, default=1)
    ap.add_argument("--baskets", default="", help="funds traded together: A,B;C,D,E")
    args = ap.parse_args(argv)
    fam = {1: families, 2: families2, 3: lambda: itertools.chain(families(), families2()),
           4: families3, 5: families5, 6: families6}[args.which]
    kept = shown = 0
    groups = ([b.split(",") for b in args.baskets.split(";")] if args.baskets
              else [[f] for f in args.funds.split(",")])
    for symbols in groups:
        fund = ",".join(symbols)
        store = load_store()
        for genome in fam():
            try:
                res = consider(store, genome, symbols, "handbred")
            except Exception as exc:  # noqa: BLE001
                print(f"skip {fund} {genome.name}: {exc}", flush=True)
                continue
            if res and res["verdict"]["profitable"]:
                kept += 1
                shown += res["verdict"]["shown"]
        save_store(store)
        print(f"{fund}: kept so far {kept}, at $80+ {shown}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
