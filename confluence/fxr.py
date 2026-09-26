"""FX Replay (FXR Script) versions of chosen strategies.

FX Replay replays charts for manual backtesting; its scripting language, FXR
Script (JavaScript with ``init`` / ``onTick`` and bar accessors such as
``high(n)``), draws indicators and signals.  ``render`` fills
``templates/fxr_strategy.js`` for one strategy.  The script then marks every
setup, simulates the trade (entry, stop, trailing stop, session exit) bar by
bar, and keeps a running tally, so the rules can be replayed, and traded by
hand, on FX Replay's own NQ data.

Only strategies whose setup has been ported to JavaScript are supported
(``CONFIGS``).  ``tests/fxr_harness.js`` runs a script outside FX Replay with
a mock of its API, and the tests check that it takes the same trades as the
Python engine.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

TEMPLATE = os.path.join(os.path.dirname(__file__), "templates", "fxr_strategy.js")

# Sessions as New York hh*60+mm for the script (see bars.PROP_SESSIONS).
CONFIGS: Dict[str, dict] = {
    "36-221": dict(TITLE="36-221 Swing Support Engulf + ATR calm · NQ 15m · London + New York", TF="15",
                   SIGNAL="swingEngulf", ENTRY="stop", STOPATR="1.5", TRAIL="false",
                   SESFROM="2 * 60", SESTO="11 * 60 + 30", FLAT="16 * 60"),
    "21-155": dict(TITLE="21-155 Inverse FVG Retest + strong close · NQ 60m · all sessions", TF="60",
                   SIGNAL="ifvgRetest", ENTRY="market", STOPATR="1.0", TRAIL="true",
                   SESFROM="18 * 60 + 5", SESTO="15 * 60 + 30", FLAT="16 * 60 + 5"),
}


def render(sid: str, stats: Optional[dict] = None) -> str:
    """The FXR Script for one supported strategy; ``stats`` = backtest trades / win / net_r."""
    if sid not in CONFIGS:
        raise KeyError(f"{sid}: no FXR Script port (supported: {', '.join(CONFIGS)})")
    with open(TEMPLATE, encoding="utf-8") as fh:
        out = fh.read()
    st = "see the explorer."
    if stats:
        st = (f"{stats['trades']:,} trades, {100 * stats['win']:.0f}% win rate, "
              f"{stats['net_r']:+.2f}R per trade after costs.")
    for k, v in dict(CONFIGS[sid], SID=sid, STATS=st).items():
        out = out.replace(f"__{k}__", v)
    return out
