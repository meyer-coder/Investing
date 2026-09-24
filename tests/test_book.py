"""The candidate-table book replay (strategies/scalp/book.py)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies" / "scalp"))
import book  # noqa: E402


def _table(rows):
    """rows: (day, name, minute, 3-min return, price)."""
    n = len(rows)
    y = np.full((n, 2, 5), np.nan, dtype=np.float32)
    y[:, 0, 2] = [r[3] for r in rows]
    y[:, 1, 2] = [r[3] / 2 for r in rows]
    return {"day": np.array([r[0] for r in rows]), "name": np.array([r[1] for r in rows]),
            "y": y, "horizons": np.array([1, 2, 3, 4, 5]), "dates": np.array(["2026-01-01", "2026-01-02", "2026-01-05"]),
            "f": {"minute": np.array([r[2] for r in rows], dtype=np.float32), "px": np.array([r[4] for r in rows], dtype=np.float32)}}


def test_slots_names_and_costs():
    # day 1: three names signal at minute 10, one more at 11 (all slots busy until 14), name 0 again at 12
    d = _table([(1, 0, 10, 0.002, 100.0), (1, 1, 10, 0.001, 100.0), (1, 2, 10, -0.001, 100.0),
                (1, 3, 11, 0.005, 100.0), (1, 0, 12, 0.004, 100.0), (1, 3, 14, 0.003, 100.0)])
    mask = np.ones(6, bool)
    prio = np.array([3.0, 2.0, 1.0, 9.0, 9.0, 1.0])
    out = book.replay(d, mask, np.ones(6), prio, hold=3, slots=2, cost="none")
    pnl, n, s = out["2026-01-02"]
    # slots=2: names 0 and 1 at minute 10 (free at 14); minute 11 and 12 are full; minute 14 takes name 3
    assert n == 3
    assert abs(s - (0.002 + 0.001 + 0.003)) < 1e-6
    assert abs(pnl - 25_000 / 2 * s) < 1e-3
    assert out["2026-01-05"] == (0.0, 0, 0.0)
    # base cost: a cent plus 1 bp each way at $100 is 4 bp a round trip
    out = book.replay(d, mask, np.ones(6), prio, hold=3, slots=2, cost="base")
    assert abs(out["2026-01-02"][2] - (0.006 - 3 * 4e-4)) < 1e-6


def test_one_name_at_a_time_and_delay():
    d = _table([(1, 0, 10, 0.002, 50.0), (1, 0, 11, 0.004, 50.0)])
    taken = []
    out = book.replay(d, np.ones(2, bool), np.ones(2), np.zeros(2), hold=3, slots=3, cost="none", taken=taken)
    assert out["2026-01-02"][1] == 1 and taken == [0]
    # a minute late uses the delayed return column
    out = book.replay(d, np.ones(2, bool), np.ones(2), np.zeros(2), hold=3, slots=3, cost="none", delay=1)
    assert abs(out["2026-01-02"][2] - 0.001) < 1e-6


def test_sell_side():
    d = _table([(1, 0, 10, -0.003, 100.0)])
    out = book.replay(d, np.ones(1, bool), -np.ones(1), np.zeros(1), hold=3, slots=1, cost="none")
    assert abs(out["2026-01-02"][2] - 0.003) < 1e-6
