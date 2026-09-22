import numpy as np
import pytest

from evotrader.data import (Bars, DataError, Universe, holdout_split, load_universe,
                            synthetic_bars, walk_forward_splits)
from evotrader.features import FEATURE_SET, MARKET_FEATURES, build_features


def _universe(n=600):
    return load_universe(["AAA", "BBB"], "2015-01-01", "2030-01-01", offline=True)


def test_synthetic_bars_are_deterministic_and_well_formed():
    a = synthetic_bars("AAA", 300, seed=7)
    b = synthetic_bars("AAA", 300, seed=7)
    assert np.allclose(a.close, b.close)
    assert (a.high >= a.close).all() and (a.low <= a.close).all()
    assert (a.volume > 0).all()


def test_universe_alignment_uses_shared_dates():
    universe = _universe()
    lengths = {len(b) for b in universe.bars.values()}
    assert len(lengths) == 1
    assert len(universe.calendar) == lengths.pop()


def test_holdout_split_is_chronological_and_disjoint():
    universe = _universe()
    train, test = holdout_split(universe, 0.25)
    assert len(train) + len(test) == len(universe)
    assert train.calendar[-1] < test.calendar[0]


def test_walk_forward_folds_never_train_on_their_own_future():
    universe = _universe()
    for split in walk_forward_splits(universe, folds=3):
        assert split.train.calendar[-1] < split.test.calendar[0]


def test_bars_slice_by_date():
    bars = synthetic_bars("AAA", 500, seed=1)
    mid = bars.dates[250]
    tail = bars.slice(start=mid)
    assert tail.dates[0] >= mid and len(tail) < len(bars)


def test_features_cover_the_declared_vocabulary():
    universe = _universe()
    fs = build_features(universe)
    for symbol in fs.symbols:
        assert set(MARKET_FEATURES) <= set(fs.matrix[symbol])
    snapshot = fs.snapshot(fs.symbols[0], len(fs.dates) - 1)
    assert set(snapshot) <= FEATURE_SET
    assert all(np.isfinite(v) for v in snapshot.values())


def test_warmup_skips_undefined_indicator_history():
    fs = build_features(_universe())
    assert fs.warmup >= 199   # sma200 is first defined at index 199
    sma200 = fs.matrix[fs.symbols[0]]["sma200"]
    assert not np.isnan(sma200[fs.warmup])


def test_missing_symbols_raise_a_clear_error():
    with pytest.raises(DataError):
        load_universe([], "2020-01-01", "2021-01-01", offline=True)


def test_cache_extends_backwards_and_a_refresh_never_shrinks_it(tmp_path, monkeypatch):
    from evotrader import data
    monkeypatch.setattr(data, "CACHE_DIR", str(tmp_path))
    calls = []

    def fake_fetch(symbol, start, end, **kwargs):
        calls.append(start)
        return data.synthetic_bars(symbol).slice(start, end)     # 2015-01-01..2020-09-29

    monkeypatch.setattr(data, "fetch_yahoo", fake_fetch)
    short = data.load_symbol("AAA", "2019-01-01", "2020-12-31", refresh=True)
    assert short.dates[0] >= "2019-01-01" and calls == ["2019-01-01"]
    # asking further back must not be served from the truncated cache
    long = data.load_symbol("AAA", "2015-06-01", "2020-12-31")
    assert long.dates[0] <= "2015-06-05" and calls[-1] == "2015-06-01"
    # a refresh from the short config re-downloads from the earliest date ever asked
    data.load_symbol("AAA", "2019-01-01", "2020-12-31", refresh=True)
    assert calls[-1] == "2015-06-01"
    assert data._read_cache("AAA").dates[0] <= "2015-06-05"
    # a symbol that simply started trading after the requested date is fetched once, not every time
    data.load_symbol("AAA", "2010-01-01", "2020-12-31")
    n = len(calls)
    again = data.load_symbol("AAA", "2010-01-01", "2020-12-31")
    assert len(calls) == n and again.dates[0] == "2015-01-01"
