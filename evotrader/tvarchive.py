"""Deep futures history, assembled from expired contracts.

TradingView hands out roughly five to seven thousand bars of any one series and
no more, so a continuous symbol like ``CME_MINI:NQ1!`` reaches back weeks, not
years.  But a futures root is not one series: every quarterly contract —
NQH2016, NQM2016, NQU2016, NQZ2016 — is its own symbol with its own window,
ending at its own expiry.  Pull forty of them and forty windows come back,
scattered through a decade.

What that buys, stated plainly, because it is easy to mistake for something
bigger: at 5-minute resolution each contract yields about nineteen sessions
near its expiry, so a quarter of roughly sixty-three trading days arrives
about a third covered.  At 1-minute it is four or five sessions a quarter.
This is a decade of *islands*, not a decade of bars.

Two consequences the data will not announce:

* **Gaps.**  Between islands lie months with nothing in them.  An indicator
  run over the concatenation averages across the hole as though June followed
  March.  :func:`coverage` measures this and :func:`stitch` records where the
  holes are, so a caller can refuse rather than quietly compute nonsense.
* **Roll basis.**  Contracts trade at different levels, so splicing them
  leaves a price jump at every boundary that no one traded.  Back-adjustment
  (the default) shifts older contracts onto the newest one's scale, which
  makes returns continuous and absolute prices historical fiction — the usual
  bargain, and the right one for testing a strategy.

    from evotrader import tvarchive
    tvarchive.build("CME_MINI", "NQ", "5", since_year=2018)
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import tvcache
from .data import Bars, DataError
from .tvdata import TradingViewError, fetch_bars, interval_seconds, normalise_timeframe

#: March, June, September, December — the quarterly cycle equity futures use.
QUARTER_CODES = {"H": 3, "M": 6, "U": 9, "Z": 12}

ARCHIVE_SUFFIX = "#ARCHIVE"


def third_friday(year: int, month: int) -> date:
    """Expiry for the quarterly equity-index contracts."""
    first = date(year, month, 15)
    return first + timedelta(days=(4 - first.weekday()) % 7)


def contracts(root: str, since_year: int, *, today: Optional[date] = None,
              ahead_days: int = 200) -> List[Tuple[str, date]]:
    """Quarterly contract codes, oldest first.

    Contracts expiring far in the future barely trade, so the list stops a
    couple of quarters out.
    """
    today = today or date.today()
    out: List[Tuple[str, date]] = []
    for year in range(since_year, today.year + 2):
        for code, month in sorted(QUARTER_CODES.items(), key=lambda kv: kv[1]):
            expiry = third_friday(year, month)
            if expiry <= today + timedelta(days=ahead_days):
                out.append((f"{root}{code}{year}", expiry))
    return sorted(out, key=lambda pair: pair[1])


def session_date(stamp: str) -> str:
    """The trading day a bar belongs to.

    CME equity futures open the evening before, so an 18:00 bar is the next
    session's.  Dates are stored UTC, where that boundary sits at 22:00.
    """
    if len(stamp) <= 10:
        return stamp
    moment = datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    return (moment + timedelta(hours=2)).date().isoformat()


def coverage(bars: Bars) -> Dict[str, object]:
    """How much of the span is actually present, and where the worst hole is."""
    if len(bars) == 0:
        return {"sessions": 0, "span_days": 0, "covered": 0.0,
                "largest_gap_days": 0, "start": "", "end": ""}
    sessions = sorted({session_date(d) for d in bars.dates})
    first = date.fromisoformat(sessions[0])
    last = date.fromisoformat(sessions[-1])
    span = (last - first).days or 1
    # Weekdays is the honest denominator: weekends were never on offer.
    weekdays = sum(1 for i in range(span + 1)
                   if (first + timedelta(days=i)).weekday() < 5)
    largest = 0
    for a, b in zip(sessions, sessions[1:]):
        gap = (date.fromisoformat(b) - date.fromisoformat(a)).days
        largest = max(largest, gap)
    return {"sessions": len(sessions), "span_days": span,
            "weekdays": weekdays,
            "covered": round(len(sessions) / max(weekdays, 1), 4),
            "largest_gap_days": largest,
            "start": sessions[0], "end": sessions[-1]}


def _basis(old: Bars, new: Bars) -> Optional[float]:
    """Price difference between two contracts where their bars overlap."""
    shared = set(old.dates) & set(new.dates)
    if not shared:
        return None
    old_by = {d: old.close[i] for i, d in enumerate(old.dates)}
    new_by = {d: new.close[i] for i, d in enumerate(new.dates)}
    diffs = [float(new_by[d] - old_by[d]) for d in shared]
    return float(np.median(diffs))


def stitch(series: Sequence[Tuple[str, Bars]], *, back_adjust: bool = True,
           daily: Optional[Dict[str, Bars]] = None
           ) -> Tuple[Bars, List[Dict[str, object]]]:
    """Splice contracts newest-last into one series.

    Each timestamp is taken from the newest contract that has it — the front
    month, by the time anyone cares — and older contracts are shifted onto its
    price scale when ``back_adjust``.

    The intraday windows rarely overlap: each ends at its own expiry, three
    months apart.  ``daily`` supplies each contract's daily series, which spans
    its whole life and overlaps the next one by months, and that is where the
    roll basis is actually measurable.
    """
    ordered = [(name, bars) for name, bars in series if len(bars)]
    if not ordered:
        raise DataError("nothing to stitch")
    ordered.sort(key=lambda pair: pair[1].dates[-1])

    offsets = [0.0] * len(ordered)
    notes: List[Dict[str, object]] = []
    if back_adjust:
        # Walk backwards from the newest, accumulating each roll's basis.
        running = 0.0
        for i in range(len(ordered) - 2, -1, -1):
            older, newer = ordered[i][0], ordered[i + 1][0]
            gap = _basis(ordered[i][1], ordered[i + 1][1])
            overlap = len(set(ordered[i][1].dates) & set(ordered[i + 1][1].dates))
            measured_on = "intraday" if gap is not None else ""
            if gap is None and daily:
                old_day, new_day = daily.get(older), daily.get(newer)
                if old_day is not None and new_day is not None:
                    gap = _basis(old_day, new_day)
                    if gap is not None:
                        overlap = len(set(old_day.dates) & set(new_day.dates))
                        measured_on = "daily"
            notes.append({"from": older, "to": newer,
                          "basis": None if gap is None else round(gap, 4),
                          "overlapping_bars": overlap,
                          "measured_on": measured_on})
            if gap is None:
                continue        # no overlap: leave this boundary unadjusted
            running += gap
            offsets[i] = running

    rows: Dict[str, Tuple[float, float, float, float, float, str]] = {}
    for (name, bars), offset in zip(ordered, offsets):
        for i, stamp in enumerate(bars.dates):
            rows[stamp] = (float(bars.open[i]) + offset, float(bars.high[i]) + offset,
                           float(bars.low[i]) + offset, float(bars.close[i]) + offset,
                           float(bars.volume[i]), name)
    dates = sorted(rows)
    cols = list(zip(*(rows[d][:5] for d in dates)))
    stitched = Bars(ordered[-1][0].split(ARCHIVE_SUFFIX)[0], dates,
                    *[np.asarray(c, dtype=float) for c in cols])
    stitched.sources = [rows[d][5] for d in dates]      # type: ignore[attr-defined]
    return stitched, list(reversed(notes))


def build(exchange: str = "CME_MINI", root: str = "NQ", timeframe: str = "5",
          *, since_year: int = 2015, bars: int = 20_000,
          back_adjust: bool = True, pause: float = 0.5,
          fetch=fetch_bars, today: Optional[date] = None,
          progress: Optional[Callable[[str, int], None]] = None
          ) -> Dict[str, object]:
    """Pull every quarterly contract plus the continuous series, and stitch.

    Each contract is cached under its own symbol, so a second run re-fetches
    only what has moved and merges the rest.
    """
    resolution = normalise_timeframe(timeframe)
    collected: List[Tuple[str, Bars]] = []
    failures: List[str] = []

    jobs = [f"{exchange}:{root}1!"]
    jobs += [f"{exchange}:{code}" for code, _ in
             contracts(root, since_year, today=today)]

    daily: Dict[str, Bars] = {}
    want_daily = back_adjust and resolution != "1D"
    for symbol in jobs:
        try:
            series = tvcache.cached_bars(symbol, resolution, bars, force=True,
                                         fetch=fetch)
        except (TradingViewError, DataError) as exc:
            failures.append(f"{symbol}: {str(exc)[:60]}")
            continue
        if len(series):
            collected.append((symbol, series))
        if want_daily:
            # A contract's daily series spans its whole life, so consecutive
            # contracts overlap by months — the only place the roll basis can
            # be measured.
            try:
                daily[symbol] = tvcache.cached_bars(symbol, "1D", 5_000,
                                                    force=True, fetch=fetch)
            except (TradingViewError, DataError):
                pass
        if progress is not None:
            progress(symbol, len(series))
        if pause:
            time.sleep(pause)

    if not collected:
        raise TradingViewError("no contract returned any bars. "
                               + "; ".join(failures[:3]))

    stitched, rolls = stitch(collected, back_adjust=back_adjust,
                             daily=daily or None)
    tvcache.write_cache(Bars(f"{exchange}:{root}{ARCHIVE_SUFFIX}", stitched.dates,
                             stitched.open, stitched.high, stitched.low,
                             stitched.close, stitched.volume), resolution)
    report = coverage(stitched)
    report.update({
        "symbol": f"{exchange}:{root}{ARCHIVE_SUFFIX}",
        "timeframe": resolution,
        "bars": len(stitched),
        "contracts": len(collected),
        "back_adjusted": back_adjust,
        "rolls": rolls,
        "failures": failures,
        "bars_per_session": round(len(stitched) / max(report["sessions"], 1), 1),
    })
    return report


def describe(report: Dict[str, object]) -> str:
    """The report as prose, including what the gaps mean."""
    covered = float(report.get("covered", 0.0)) * 100
    lines = [
        f"{report['symbol']} {report['timeframe']}: {report['bars']:,} bars from "
        f"{report['contracts']} contracts",
        f"  {report['start']} .. {report['end']}  ·  {report['sessions']:,} sessions "
        f"of {report.get('weekdays', 0):,} weekdays  ·  {covered:.0f}% covered",
        f"  largest hole: {report['largest_gap_days']} days  ·  "
        f"{report['bars_per_session']} bars per session present",
    ]
    if report.get("back_adjusted"):
        rolls = report.get("rolls", [])
        unadjusted = [r for r in rolls if r.get("basis") is None]
        on_daily = [r for r in rolls if r.get("measured_on") == "daily"]
        lines.append(f"  back-adjusted across {len(rolls)} rolls"
                     + (f" ({len(on_daily)} measured on daily overlap)" if on_daily else "")
                     + (f", {len(unadjusted)} with no overlap to measure"
                        if unadjusted else ""))
    if covered < 90:
        lines.append(f"  this is {covered:.0f}% of sessions, not a continuous "
                     f"history — indicators run across the holes will average "
                     f"over months that are not there")
    for failure in report.get("failures", [])[:3]:
        lines.append(f"  missing: {failure}")
    return "\n".join(lines)
