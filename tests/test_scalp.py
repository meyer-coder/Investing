"""The Own-Drop Scalper: its residual reads only closed minutes, a drop the market shares is not
bought, and every trade lasts four minutes inside the session."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))

import owndrop  # noqa: E402
import residbot  # noqa: E402
from evotrader.data import Bars, Universe  # noqa: E402
from evotrader.features import build_features  # noqa: E402
from evotrader.genome import compile_genome  # noqa: E402
from evotrader.runner import run_backtest  # noqa: E402

NAMES = ("AAA", "BBB", "CCC", "DDD")
DAYS = ("2026-09-21", "2026-09-22")          # New York is UTC-4: the 09:30 open is 13:30 UTC


def _stamps():
    out = []
    for d in DAYS:
        t = datetime.strptime(d + " 13:30", "%Y-%m-%d %H:%M")
        out += [(t + timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M") for m in range(390)]
    return out


def _universe(drop=(), at=7):
    """Four names wiggling on their own (a sine a basis point high, each with its own phase),
    and the names in `drop` falling 1% on the second session's minute `at`."""
    stamps = _stamps()
    n = len(stamps)
    event = 390 + at
    bars = {}
    for i, s in enumerate(NAMES):
        r = 1e-4 * np.sin(0.7 * np.arange(n) + i)
        if s in drop:
            r[event] = -0.01
        c = 100.0 * np.cumprod(1.0 + r)
        o = np.concatenate([[100.0], c[:-1]])
        bars[s] = Bars(s, list(stamps), o, np.maximum(o, c) * 1.00005, np.minimum(o, c) * 0.99995, c,
                       np.full(n, 1e5))
    return Universe(bars, list(stamps))


def _features(u):
    f = build_features(u)
    residbot.add_residual(u, f)
    return f


def _trades(u, f):
    r = run_backtest(compile_genome(owndrop.bot(), residbot.ALLOWED), u, f, starting_cash=25_000.0,
                     commission_bps=0.0, slippage_bps=2.0, record_thoughts=False, intrabar_stops=True,
                     leverage=2.0)
    return r.journal.trades


def test_the_residual_reads_only_minutes_already_closed():
    u = _universe(drop=("AAA",))
    before = {s: _features(u).matrix[s]["resid_z"].copy() for s in NAMES}
    k = 390 + 7
    for s in NAMES:                                  # rewrite every minute after k
        b = u.bars[s]
        b.close[k + 1:] *= np.linspace(0.9, 1.1, len(b.close) - k - 1)
    after = {s: _features(u).matrix[s]["resid_z"] for s in NAMES}
    for s in NAMES:
        np.testing.assert_array_equal(before[s][:k + 1], after[s][:k + 1])


def test_a_drop_taken_alone_stands_out_and_one_the_market_shares_does_not():
    k = 390 + 7
    alone = _features(_universe(drop=("AAA",))).matrix
    assert alone["AAA"]["resid_z"][k] < -10
    assert all(alone[s]["resid_z"][k] > 0 for s in NAMES[1:])
    shared = _features(_universe(drop=NAMES)).matrix
    assert all(abs(shared[s]["resid_z"][k]) < 2 for s in NAMES)
    assert all(shared[s]["ret1"][k] < -0.75 * shared[s]["atr_pct"][k] for s in NAMES)


def test_it_buys_the_lone_drop_at_the_next_open_and_sells_four_minutes_later():
    u = _universe(drop=("AAA",))
    trades = _trades(u, _features(u))
    assert [(t.symbol, t.entry_date, t.exit_date) for t in trades] == \
        [("AAA", "2026-09-22 13:38", "2026-09-22 13:42")]            # 09:38 to 09:42 New York
    assert abs(trades[0].shares * trades[0].entry_price - 2 * 25_000.0 / 3) < 50   # a third of 2x buying power


def test_it_leaves_a_drop_the_whole_market_shares_alone():
    u = _universe(drop=NAMES)
    assert _trades(u, _features(u)) == []


def test_it_only_buys_in_the_opening_minutes():
    for at in (3, 20, 200):                          # 09:33, 09:50, 12:50
        u = _universe(drop=("AAA",), at=at)
        assert _trades(u, _features(u)) == []
