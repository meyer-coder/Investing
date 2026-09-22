"""Time-of-day, session and VWAP features.

The rest of the feature set is timeless: it would compute the same way on
daily bars as on five-minute ones.  These are the features that only mean
something intraday — what hour it is, how far into the session a bar sits,
where price is against the session's volume-weighted average, and whether the
opening range has been taken out.

Bar timestamps arrive as UTC strings (``"2026-09-21 19:55"``); the exchange
day is what a trader means by "the open", so everything here is derived after
converting to :data:`EXCHANGE_TZ`, which handles daylight saving properly.
A daily or weekly series has no time component, and every feature here is then
NaN rather than a fabricated midnight.

Look-ahead: a session's opening range is NaN *until the range window has
closed*, so a bar inside the first hour can never see the range it is still
forming.  ``session_vwap`` is cumulative from the session open through the
current bar, which is information a trader genuinely has at that bar's close.
"""
from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

import numpy as np

EXCHANGE_TZ = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")

#: Regular US equity trading hours, in exchange-local minutes from midnight.
RTH_OPEN_MIN = 9 * 60 + 30      # 09:30
RTH_CLOSE_MIN = 16 * 60         # 16:00

#: The opening range: how many minutes after the open it is measured over.
OPENING_RANGE_MINUTES = 60

SESSION_FEATURES: List[str] = [
    "hour_et", "minute_of_day", "minutes_since_open", "day_of_week", "day_of_month",
    "is_rth", "is_first_hour", "is_second_hour", "is_power_hour",
    "bars_since_open", "session_bar_count",
    "session_vwap", "dist_session_vwap",
    "opening_range_high", "opening_range_low", "opening_range_pct",
    "dist_or_high", "dist_or_low", "or_broken_up", "or_broken_down",
]

SESSION_FEATURE_DOCS: Dict[str, str] = {
    "hour_et": "hour of the exchange day, 0-23 (9 means 09:00-09:59 New York)",
    "minute_of_day": "minutes since midnight exchange time; 570 = 09:30",
    "minutes_since_open": "minutes since the 09:30 open; negative before it",
    "day_of_week": "0=Monday ... 4=Friday, 5/6 weekend (daily bars too)",
    "day_of_month": "calendar day of the month, 1-31 (daily bars too); 1-3 and 27-31 are the turn of the month",
    "is_rth": "1 during 09:30-16:00 New York, else 0",
    "is_first_hour": "1 during 09:30-10:30, the New York opening hour",
    "is_second_hour": "1 during 10:30-11:30",
    "is_power_hour": "1 during 15:00-16:00, the last hour before the close",
    "bars_since_open": "bars elapsed since this session's first bar",
    "session_bar_count": "bars this session has produced so far",
    "session_vwap": "volume-weighted average price since the session open",
    "dist_session_vwap": "(close/session_vwap)-1, fractional distance from VWAP",
    "opening_range_high": "high of the first 60 minutes; NaN until it completes",
    "opening_range_low": "low of the first 60 minutes; NaN until it completes",
    "opening_range_pct": "opening range width as a fraction of its midpoint",
    "dist_or_high": "(close/opening_range_high)-1; positive means above the range",
    "dist_or_low": "(close/opening_range_low)-1; negative means below the range",
    "or_broken_up": "1 once the session has traded above the opening range high",
    "or_broken_down": "1 once the session has traded below the opening range low",
}


def _parse(stamp: str) -> Optional[_dt.datetime]:
    """UTC bar stamp -> exchange-local datetime, or None for a dateless bar."""
    text = stamp.strip()
    if len(text) <= 10:          # "1999-03-10" — a daily or weekly bar
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            naive = _dt.datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=_UTC).astimezone(EXCHANGE_TZ)
    return None


def _nan(n: int) -> np.ndarray:
    return np.full(n, np.nan, dtype=float)


def session_features(dates: Sequence[str], high: np.ndarray, low: np.ndarray,
                     close: np.ndarray, volume: np.ndarray,
                     *, opening_range_minutes: int = OPENING_RANGE_MINUTES,
                     ) -> Dict[str, np.ndarray]:
    """Compute every feature in :data:`SESSION_FEATURES` for one symbol."""
    n = len(dates)
    out: Dict[str, np.ndarray] = {name: _nan(n) for name in SESSION_FEATURES}
    if n == 0:
        return out

    local = [_parse(d) for d in dates]
    if all(t is None for t in local):
        # Daily bars: only the calendar applies.  Dates are trading dates.
        for i, d in enumerate(dates):
            try:
                day = _dt.date.fromisoformat(d.strip()[:10])
            except ValueError:
                continue
            out["day_of_week"][i] = float(day.weekday())
            out["day_of_month"][i] = float(day.day)
        return out

    # Session state, reset whenever the exchange date changes.
    cur_day: Optional[_dt.date] = None
    pv_sum = 0.0                        # sum of price * volume this session
    v_sum = 0.0
    bars_in = 0
    or_high = or_low = np.nan
    or_done = False
    broke_up = broke_down = 0.0

    for i, t in enumerate(local):
        if t is None:
            continue
        minute = t.hour * 60 + t.minute
        since_open = minute - RTH_OPEN_MIN

        if t.date() != cur_day:
            cur_day = t.date()
            pv_sum = v_sum = 0.0
            bars_in = 0
            or_high = or_low = np.nan
            or_done = False
            broke_up = broke_down = 0.0

        out["hour_et"][i] = float(t.hour)
        out["minute_of_day"][i] = float(minute)
        out["minutes_since_open"][i] = float(since_open)
        out["day_of_week"][i] = float(t.weekday())
        out["day_of_month"][i] = float(t.day)
        out["is_rth"][i] = float(RTH_OPEN_MIN <= minute < RTH_CLOSE_MIN)
        out["is_first_hour"][i] = float(RTH_OPEN_MIN <= minute < RTH_OPEN_MIN + 60)
        out["is_second_hour"][i] = float(RTH_OPEN_MIN + 60 <= minute < RTH_OPEN_MIN + 120)
        out["is_power_hour"][i] = float(15 * 60 <= minute < RTH_CLOSE_MIN)
        out["bars_since_open"][i] = float(bars_in)
        out["session_bar_count"][i] = float(bars_in + 1)

        typical = (high[i] + low[i] + close[i]) / 3.0
        vol = float(volume[i]) if np.isfinite(volume[i]) else 0.0
        pv_sum += typical * vol
        v_sum += vol
        vwap = pv_sum / v_sum if v_sum > 0 else typical
        out["session_vwap"][i] = vwap
        out["dist_session_vwap"][i] = close[i] / vwap - 1.0 if vwap > 0 else 0.0

        # The opening range forms over its window and is only *published* once
        # the window has closed — a bar inside it must not see it.
        in_range_window = 0 <= since_open < opening_range_minutes
        if in_range_window:
            or_high = high[i] if not np.isfinite(or_high) else max(or_high, high[i])
            or_low = low[i] if not np.isfinite(or_low) else min(or_low, low[i])
        elif since_open >= opening_range_minutes and np.isfinite(or_high):
            or_done = True

        if or_done:
            out["opening_range_high"][i] = or_high
            out["opening_range_low"][i] = or_low
            mid = (or_high + or_low) / 2.0
            out["opening_range_pct"][i] = (or_high - or_low) / mid if mid > 0 else 0.0
            out["dist_or_high"][i] = close[i] / or_high - 1.0 if or_high > 0 else 0.0
            out["dist_or_low"][i] = close[i] / or_low - 1.0 if or_low > 0 else 0.0
            if high[i] > or_high:
                broke_up = 1.0
            if low[i] < or_low:
                broke_down = 1.0
            out["or_broken_up"][i] = broke_up
            out["or_broken_down"][i] = broke_down

        bars_in += 1

    return out
