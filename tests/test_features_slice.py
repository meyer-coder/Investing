import numpy as np
import pytest

from evotrader.data import load_universe
from evotrader.features import (FEATURE_SET, MARKET_FEATURES, TRADING_DAYS,
                                build_features)


@pytest.fixture(scope="module")
def universe():
    return load_universe(["AAA", "BBB"], "2015-01-01", "2030-01-01", offline=True)


@pytest.fixture(scope="module")
def features(universe):
    return build_features(universe)


def test_sma100_and_its_distance_are_real_features():
    """Two seed archetypes referenced these; without them they never compiled."""
    assert "sma100" in FEATURE_SET
    assert "dist_sma100" in FEATURE_SET
    assert "sma100" in MARKET_FEATURES


def test_sma100_sits_between_the_50_and_200_bar_averages(features):
    symbol = features.symbols[0]
    m = features.matrix[symbol]
    i = len(features.dates) - 1
    assert not np.isnan(m["sma100"][i])
    lo, hi = sorted((m["sma50"][i], m["sma200"][i]))
    assert lo - abs(lo) * 0.5 <= m["sma100"][i] <= hi + abs(hi) * 0.5


def test_slice_equals_the_same_bars_of_the_whole_series(features):
    """The guarantee that makes slicing leak-free: a sliced feature is bit-for-bit
    the full-history feature, so no bar is derived from outside the window."""
    window = features.index_slice(400, 700)
    for symbol in features.symbols:
        for name in features.matrix[symbol]:
            full = features.matrix[symbol][name][400:700]
            got = window.matrix[symbol][name]
            assert np.array_equal(full, got, equal_nan=True), name


def test_slice_reports_the_right_dates_and_length(features):
    window = features.index_slice(400, 700)
    assert window.dates == features.dates[400:700]
    assert len(window.dates) == 300


def test_slice_consumes_warmup_it_has_already_passed(features):
    assert features.index_slice(0, 500).warmup == features.warmup
    assert features.index_slice(features.warmup + 10, 900).warmup == 0


def test_slice_clamps_out_of_range_bounds(features):
    window = features.index_slice(-50, len(features.dates) + 50)
    assert len(window.dates) == len(features.dates)


def test_volatility_annualisation_follows_the_bar_size(universe):
    """vol20 is annualised, so an hourly series must not be scaled as daily."""
    daily = build_features(universe)
    hourly = build_features(universe, TRADING_DAYS * 6.5)
    symbol = daily.symbols[0]
    i = len(daily.dates) - 1
    ratio = hourly.matrix[symbol]["vol20"][i] / daily.matrix[symbol]["vol20"][i]
    assert ratio == pytest.approx(np.sqrt(6.5), rel=1e-6)


def test_restricted_snapshot_matches_the_full_one(features):
    """The speed optimisation must not change a single value."""
    symbol = features.symbols[0]
    full = features.snapshot(symbol, 500)
    wanted = ["rsi14", "close", "sma200"]
    restricted = features.snapshot(symbol, 500, wanted)
    assert set(restricted) == set(wanted)
    for name in wanted:
        assert restricted[name] == full[name]


def test_snapshot_ignores_names_it_does_not_have(features):
    """Rules also reference portfolio features, which the runner supplies."""
    got = features.snapshot(features.symbols[0], 500, ["close", "bars_held"])
    assert set(got) == {"close"}


def test_series_view_returns_the_same_values_as_snapshot(features):
    symbol = features.symbols[0]
    view = features.series_view([symbol], ["rsi14", "close"])
    snap = features.snapshot(symbol, 400, ["rsi14", "close"])
    assert {n: s[400] for n, s in view[symbol].items()} == snap


def test_nans_become_zero_before_warmup(features):
    """Rules must never see NaN; sma200 is undefined on the first bars."""
    assert features.snapshot(features.symbols[0], 0, ["sma200"])["sma200"] == 0.0


def test_clean_cache_does_not_cross_a_process_boundary(features):
    import pickle
    features.snapshot(features.symbols[0], 10, ["close"])
    assert features._clean, "cache should be populated"
    assert pickle.loads(pickle.dumps(features))._clean == {}


def test_pickled_features_still_produce_the_same_values(features):
    import pickle
    symbol = features.symbols[0]
    revived = pickle.loads(pickle.dumps(features))
    assert revived.snapshot(symbol, 300) == features.snapshot(symbol, 300)
