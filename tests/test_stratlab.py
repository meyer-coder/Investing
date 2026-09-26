"""stratlab engine checks on hand-built minute data with known answers."""
import numpy as np
import pytest

from stratlab import data as sd
from stratlab import engine, indicators, signals, spec as sp
from stratlab.data import DAY_START, Minutes, make_bars

TD = 20000                                     # a trading day: 18:00 on day TD to 16:00 on TD + 1


def minutes_for(price, days=1, start_tday=TD):
    """Flat minutes from 18:00 to 16:00 for each trading day, prices from price(i) (i = row)."""
    L = np.concatenate([np.arange(td * 1440 + DAY_START, td * 1440 + DAY_START + 22 * 60)
                        for td in range(start_tday, start_tday + days)])
    p = np.array([price(i) for i in range(len(L))], float)
    o, c = p.copy(), p.copy()
    h, lo = p + 0.25, p - 0.25
    tday = (L - DAY_START) // 1440
    tmin = (L - DAY_START) % 1440
    return Minutes(L, o, h, lo, c, np.ones(len(L)), tday, tmin, {int(d): True for d in np.unique(tday)})


def row_at(M, td, hhmm):
    t = td * 1440 + DAY_START + sd.parse_clock(hhmm)
    return int(np.searchsorted(M.L, t))


@pytest.fixture
def fire_at(monkeypatch):
    """A family that fires at chosen bar-close times: {('HH:MM', side)}."""
    def make(events):
        def fam(B):
            side = np.zeros(len(B.c), int)
            for hhmm, s in events:
                close = sd.parse_clock(hhmm)
                side[(B.tmin + B.tf) == close] = s
            return side, None
        monkeypatch.setitem(signals.FAMILIES, "test_fire", (fam, "test"))
    return make


def card(**kw):
    base = {"family": "test_fire", "market": "NAS100", "tf": 15, "session": "ny",
            "stop": {"type": "pct", "pct": 1.0}, "target": {"type": "r", "mult": 1.0}, "max_trades_day": 5}
    base.update(kw)
    return base


def run(M, c):
    return engine.run(c, B=make_bars(M, c.get("tf", 15)), M=M)


def test_bars_line_up_on_the_clock():
    M = minutes_for(lambda i: 100 + i * 0.01)
    B = make_bars(M, 15)
    assert B.tmin[0] == 0 and B.tmin[1] == 15
    k = int(np.flatnonzero(B.tmin == 930)[0])
    r0, r1 = B.row0[k], B.row1[k]
    assert r1 - r0 == 15
    assert B.o[k] == M.o[r0] and B.c[k] == M.c[r1 - 1]
    assert B.h[k] == M.h[r0:r1].max() and B.l[k] == M.l[r0:r1].min()


def test_rolling_max_matches_a_plain_loop():
    x = np.random.default_rng(1).normal(size=500)
    for w in (1, 3, 7, 50):
        got = indicators.rolling_max(x, w)
        want = np.array([x[i - w + 1:i + 1].max() if i >= w - 1 else np.nan for i in range(len(x))])
        np.testing.assert_allclose(got[w - 1:], want[w - 1:])
        assert np.isnan(got[:w - 1]).all()


def test_roll_gap_at_the_reopen_is_removed():
    # two trading days; the second reopens 2% higher (a contract roll)
    t0 = 1_699_988_400                          # 2023-11-14 14:00 New York
    L_days = []
    for d, (lvl, n) in enumerate(((100.0, 60), (102.0, 60))):
        base = t0 + d * 86400
        L_days += [(base + 60 * j, lvl, lvl, lvl, lvl, 1.0) for j in range(n)]
    a = np.array(L_days)
    M = sd.from_rows(a, rolls=True)
    assert len(np.unique(M.tday)) == 2
    first_new = int(np.flatnonzero(np.diff(M.tday))[0]) + 1
    assert M.c[first_new - 1] == pytest.approx(M.o[first_new])      # no gap left
    assert M.c[-1] == 102.0                                          # the latest prices are untouched


def test_market_entry_hits_target_at_1r(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    r = row_at(M, TD, "10:00")
    M.o[r:] = 100.0
    M.h[r + 5], M.c[r + 5] = 101.5, 101.0                          # +1% reached 5 minutes in
    tr = run(M, card())
    assert len(tr) == 1
    t = tr[0]
    assert t.entry == 100.0 and t.why == "target"
    assert t.r_gross == pytest.approx(1.0)
    assert t.r_net == pytest.approx(1.0 - t.r_cost)
    assert t.exit_time == M.L[r + 5]


def test_stop_first_when_a_minute_touches_both(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    r = row_at(M, TD, "10:00")
    M.h[r + 3], M.l[r + 3] = 101.5, 98.5
    t = run(M, card())[0]
    assert t.why == "stop" and t.r_gross == pytest.approx(-1.0)


def test_limit_pullback_fills_only_when_traded_through_and_cancels(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    k0 = row_at(M, TD, "09:45")
    M.h[k0:k0 + 15], M.l[k0:k0 + 15] = 102.0, 100.0                # signal candle 100-102, 50% = 101
    c = card(entry={"type": "limit_pullback", "frac": 0.5, "cancel_bars": 2}, stop={"type": "signal_bar", "ticks": 0},
             target={"type": "none"})
    M.o[:] = 101.5
    M.c[:] = 101.5
    M.h[:] = np.maximum(M.h, 101.75)
    M.l[:] = 101.25
    M.l[k0:k0 + 15] = 100.0
    M.h[k0:k0 + 15] = 102.0
    M.l[row_at(M, TD, "10:05")] = 101.0                             # touches 101 but does not trade through
    assert run(M, c) == []                                          # never traded below 101 within 2 candles
    M.l[row_at(M, TD, "10:20")] = 100.9                             # trades through at 10:20
    tr = run(M, c)
    assert len(tr) == 1 and tr[0].entry == 101.0 and tr[0].entry_time == M.L[row_at(M, TD, "10:20")]
    M.l[row_at(M, TD, "10:20")] = 101.25
    M.l[row_at(M, TD, "10:31")] = 100.9                             # after the 2-candle cancel: no fill
    assert run(M, c) == []


def test_time_stop_and_flat(fire_at):
    fire_at([("10:00", -1)])
    M = minutes_for(lambda i: 100.0)
    t = run(M, card(target={"type": "none"}, time_stop_bars=2))[0]
    assert t.why == "time" and t.exit_time == M.L[row_at(M, TD, "10:30")] - 1
    t = run(M, card(target={"type": "none"}))[0]
    assert t.why == "flat" and t.exit_time == M.L[row_at(M, TD, "15:55")] - 1


def test_breakeven_trailing_and_partial(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    r = row_at(M, TD, "10:00")
    M.h[r + 2] = 101.0                                               # +1R
    M.l[r + 4] = 99.9                                                # back below entry
    t = run(M, card(target={"type": "r", "mult": 3.0}, trailing={"type": "breakeven", "at_r": 1.0}))[0]
    assert t.why == "trail" and t.r_gross == pytest.approx(0.0)
    t = run(M, card(target={"type": "r", "mult": 3.0}, partial={"type": "take", "frac": 0.5, "at_r": 1.0},
                    trailing={"type": "breakeven", "at_r": 1.0}))[0]
    assert t.r_gross == pytest.approx(0.5)                           # half at +1R, half at breakeven


def test_max_trades_direction_session_and_one_position_at_a_time(fire_at):
    fire_at([("10:00", 1), ("10:15", -1), ("11:00", 1), ("13:00", -1)])
    M = minutes_for(lambda i: 100.0)
    tr = run(M, card(target={"type": "none"}, time_stop_bars=1, max_trades_day=2))
    assert [t.side for t in tr] == [1, -1]
    tr = run(M, card(target={"type": "none"}, time_stop_bars=1, direction="short"))
    assert [t.side for t in tr] == [-1, -1]
    tr = run(M, card(target={"type": "none"}, time_stop_bars=1, session="ny_pm"))
    assert [t.side for t in tr] == [-1]
    tr = run(M, card(target={"type": "none"}))                      # held to the flat: later signals ignored
    assert len(tr) == 1


def test_card_validation_and_words():
    with pytest.raises(ValueError):
        sp.normalize({"family": "volume_spike_breakout", "stop": {"type": "nope"}})
    with pytest.raises(ValueError):
        sp.normalize({"family": "volume_spike_breakout", "flat": "17:00"})
    rows = dict(sp.card({"family": "volume_spike_breakout", "settings": {"vol_mult": 2.5, "vol_n": 50, "k": 10},
                         "session": "ny_pm", "entry": {"type": "limit_pullback"},
                         "filters": [{"type": "weekday", "skip": ["Wed", "Fri"]}]}))
    assert "2.5x its 50-candle average" in rows["Signal"]
    assert rows["Filters"] == "skips Wed/Fri"
    assert "cancelled if not filled within 10 candles" in rows["Entry"]


def test_stop_is_never_closer_than_four_ticks(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    t = run(M, card(stop={"type": "pct", "pct": 0.0001}, target={"type": "none"}))[0]
    tick = sd.market("NAS100").tick / sd.market("NAS100").price
    assert t.risk == pytest.approx(engine.MIN_STOP_TICKS * tick * 100.0)


def test_a_limit_already_marketable_fills_at_the_open(fire_at):
    fire_at([("10:00", 1)])
    M = minutes_for(lambda i: 100.0)
    k0 = row_at(M, TD, "09:45")
    M.h[k0:k0 + 15], M.l[k0:k0 + 15] = 102.0, 99.75                # 50% level = 100.875, above the market
    t = run(M, card(entry={"type": "limit_pullback", "frac": 0.5, "cancel_bars": 2}, target={"type": "none"}))[0]
    assert t.entry == 100.0 and t.entry_time == M.L[row_at(M, TD, "10:00")]


def test_random_entries_break_even_before_costs_on_a_random_walk(monkeypatch):
    """No signal, symmetric bracket, driftless prices: gross R should be about zero for
    market and limit entries alike (catches fill rules that tilt results)."""
    rng = np.random.default_rng(5)
    steps = rng.normal(0, 0.05, 30 * 22 * 60)
    M = minutes_for(lambda i: 100.0 + steps[:i + 1].sum(), days=30)
    M.o[1:] = M.c[:-1]
    # wicks stand in for the path inside each minute (a price that moves through levels, not jumps)
    M.h[:] = np.maximum(M.o, M.c) + np.abs(rng.normal(0, 0.03, len(M.L)))
    M.l[:] = np.minimum(M.o, M.c) - np.abs(rng.normal(0, 0.03, len(M.L)))
    B = make_bars(M, 5)
    for entry in ({"type": "market"}, {"type": "limit_pullback", "frac": 0.5, "cancel_bars": 3}):
        g = []
        for seed in range(40):
            c = card(family="random_control", settings={"rate": 0.2, "seed": seed}, tf=5, session="all",
                     entry=entry, stop={"type": "atr", "mult": 1.0, "n": 14},
                     target={"type": "atr", "mult": 1.0, "n": 14})
            g += [t.r_gross for t in engine.run(c, B=B, M=M)]
        assert len(g) > 1500
        assert abs(np.mean(g)) < 0.05, (entry["type"], np.mean(g))
