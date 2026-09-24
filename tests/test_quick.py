"""The quick-trade rules (strategies/quick): the noise-area breakout on made-up days, and the Topstep replay."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strategies" / "quick"))
import trend  # noqa: E402

T = 390


def _days(n_quiet: int, today: np.ndarray) -> dict:
    """n_quiet flat-ish days that each drift 0.1% from the open, then `today` (closes, one per minute)."""
    rows = []
    for k in range(n_quiet):
        c = 100.0 * (1 + 0.001 * np.linspace(0, 1, T) * (1 if k % 2 else -1))
        rows.append(c)
    rows.append(today)
    C = np.array(rows)
    O = np.concatenate([C[:, :1], C[:, :-1]], axis=1)
    H = np.maximum(O, C) + 0.001
    L = np.minimum(O, C) - 0.001
    pc = np.concatenate([[np.nan], C[:-1, -1]])
    return {"O": O, "H": H, "L": L, "C": C, "pc": pc, "dates": np.array([f"2025-01-{i + 1:02d}" for i in range(len(C))])}


def test_trend_day_is_bought_at_ten_and_held_to_the_close():
    today = 100.0 * (1 + 0.05 * np.linspace(0, 1, T))                       # up 5% steadily: far outside a 0.1% band
    D = _days(20, today)
    r, lo, n, m = trend.noise_days(D, cost=0.0)
    assert n[-1] == 1
    entry, close = D["O"][-1, 30], D["C"][-1, -1]                           # bought at 10:00's open, held to 15:59
    assert abs(r[-1] - (close / entry - 1.0)) < 1e-12
    assert lo[-1] <= 0.0


def test_quiet_day_does_not_trade():
    today = 100.0 * (1 + 0.0002 * np.sin(np.linspace(0, 6, T)))              # well inside the band all day
    D = _days(20, today)
    r, lo, n, m = trend.noise_days(D, cost=0.0)
    assert n[-1] == 0 and r[-1] == 0.0


def test_hard_stop_caps_a_reversal():
    up = np.linspace(100.0, 101.5, 30)                                       # bought at 10:00 ...
    crash = np.linspace(101.5, 98.5, 30)                                     # ... then down 3% before the next look
    D = _days(20, np.concatenate([up, crash, np.full(T - 60, 98.5)]))
    free, _, _, _ = trend.noise_days(D, cost=0.0)
    stopped, _, _, _ = trend.noise_days(D, cost=0.0, hard_stop=0.0025)
    assert stopped[-1] > free[-1]
    assert stopped[-1] >= -0.0025 - 0.002                                    # the stop, less at most a gap through it


def test_topstep_breach_and_pass():
    dates = [f"d{i}" for i in range(40)]
    losing = np.full(40, -800.0)
    res = trend.topstep(dates, losing, losing, every=40)
    assert res["breach"] == 1.0
    winning = np.full(40, 400.0)
    res = trend.topstep(dates, winning, np.zeros(40), every=40)
    assert res["pass"] == 1.0 and res["median_days_to_pass"] == 15
