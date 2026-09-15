"""Per-bar feature construction — the 'senses' every agent trades on.

Features are computed once per universe and shared by every genome in every
generation, which is what makes 100 agents x 1000 generations cheap.  The names
defined here are exactly the vocabulary available to the strategy DSL, so a
genome that references an unknown name fails validation instead of silently
evaluating to zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from . import indicators as ind
from .data import Universe

# Features derived from price history alone.
MARKET_FEATURES: List[str] = [
    "open", "high", "low", "close", "volume",
    "ret1", "ret5", "ret20", "ret60",
    "sma10", "sma20", "sma50", "sma100", "sma200",
    "ema12", "ema26",
    "dist_sma20", "dist_sma50", "dist_sma100", "dist_sma200", "sma20_slope",
    "rsi7", "rsi14",
    "macd", "macd_signal", "macd_hist",
    "atr14", "atr_pct",
    "vol20", "vol60", "vol_ratio_20_60",
    "bb_upper", "bb_lower", "bb_pct", "zscore20",
    "pct_of_52w_high", "pct_off_52w_low", "volume_ratio",
    "mkt_ret20", "mkt_above_sma200", "mkt_vol20",
]

# Features injected by the backtest runner, describing the portfolio's own state.
PORTFOLIO_FEATURES: List[str] = [
    "in_position", "bars_held", "position_return", "position_drawdown",
    "position_weight", "cash_pct", "gross_exposure", "position_count",
    "bars_since_exit", "portfolio_return", "portfolio_drawdown",
]

FEATURE_NAMES: List[str] = MARKET_FEATURES + PORTFOLIO_FEATURES
FEATURE_SET = frozenset(FEATURE_NAMES)

#: Short human descriptions, handed to Claude so it can write valid rules.
FEATURE_DOCS: Dict[str, str] = {
    "open": "opening price of the current bar",
    "high": "high of the current bar",
    "low": "low of the current bar",
    "close": "latest close price",
    "volume": "shares traded on the current bar",
    "ret1": "1-bar return, e.g. 0.012 = +1.2%",
    "ret5": "5-bar return",
    "ret20": "20-bar (about one month) return",
    "ret60": "60-bar (about one quarter) return",
    "sma10": "10-bar simple moving average of close",
    "sma20": "20-bar simple moving average",
    "sma50": "50-bar simple moving average",
    "sma100": "100-bar simple moving average",
    "sma200": "200-bar simple moving average",
    "ema12": "12-bar exponential moving average",
    "ema26": "26-bar exponential moving average",
    "dist_sma20": "(close/sma20)-1, fractional distance above the 20-bar mean",
    "dist_sma50": "(close/sma50)-1",
    "dist_sma100": "(close/sma100)-1",
    "dist_sma200": "(close/sma200)-1",
    "sma20_slope": "5-bar rate of change of sma20",
    "rsi7": "7-bar RSI, 0-100",
    "rsi14": "14-bar RSI, 0-100 (below 30 oversold, above 70 overbought)",
    "macd": "MACD line (ema12-ema26)",
    "macd_signal": "9-bar EMA of the MACD line",
    "macd_hist": "MACD minus signal",
    "atr14": "14-bar average true range, in price units",
    "atr_pct": "atr14/close, volatility as a fraction of price",
    "vol20": "annualised realised volatility over 20 bars",
    "vol60": "annualised realised volatility over 60 bars",
    "vol_ratio_20_60": "vol20/vol60; above 1 means volatility is expanding",
    "bb_upper": "upper Bollinger band (20, 2sd)",
    "bb_lower": "lower Bollinger band (20, 2sd)",
    "bb_pct": "position inside the Bollinger band, 0=lower 1=upper",
    "zscore20": "z-score of close against its 20-bar mean",
    "pct_of_52w_high": "close divided by the 252-bar high, 1.0 = at the high",
    "pct_off_52w_low": "(close/252-bar low)-1",
    "volume_ratio": "volume divided by its 20-bar average",
    "mkt_ret20": "20-bar return of the equal-weighted universe (market regime)",
    "mkt_above_sma200": "1 when the equal-weighted universe is above its 200-bar mean, else 0",
    "mkt_vol20": "annualised 20-bar volatility of the equal-weighted universe",
    "in_position": "1 when this symbol is currently held, else 0",
    "bars_held": "bars the current position has been open (0 when flat)",
    "position_return": "unrealised return of the open position, e.g. -0.04",
    "position_drawdown": "drop from the position's peak value, always <= 0",
    "position_weight": "position value divided by total equity",
    "cash_pct": "cash divided by total equity",
    "gross_exposure": "invested value divided by total equity",
    "position_count": "number of open positions",
    "bars_since_exit": "bars since this symbol was last sold (999 if never)",
    "portfolio_return": "total return of the portfolio so far",
    "portfolio_drawdown": "portfolio drop from its equity peak, always <= 0",
}

TRADING_DAYS = 252.0


@dataclass
class FeatureSet:
    """Precomputed market features: ``matrix[symbol][feature] -> np.ndarray``."""

    symbols: List[str]
    dates: List[str]
    matrix: Dict[str, Dict[str, np.ndarray]]
    warmup: int
    #: Lazily built NaN-free Python lists, keyed symbol -> feature.  Indexing a
    #: list of floats is far cheaper per bar than pulling a numpy scalar and
    #: testing it for NaN, and a backtest does that once per bar per symbol.
    _clean: Dict[str, Dict[str, List[float]]] = field(
        default_factory=dict, repr=False, compare=False)

    def __getstate__(self) -> Dict[str, Any]:
        """Drop the derived cache when crossing a process boundary."""
        state = dict(self.__dict__)
        state["_clean"] = {}
        return state

    def _series(self, symbol: str, name: str) -> List[float]:
        cache = self._clean.setdefault(symbol, {})
        series = cache.get(name)
        if series is None:
            series = [0.0 if v is None or np.isnan(v) else float(v)
                      for v in self.matrix[symbol][name]]
            cache[name] = series
        return series

    def index_slice(self, lo: int, hi: int) -> "FeatureSet":
        """A window of the same features, without recomputing them.

        Every feature here is causal — each bar is derived only from bars at
        or before it — so a slice carries no information from outside the
        window, and the indicators arrive already warmed up.  Rebuilding on
        the slice instead would throw away the first ~200 bars to warmup,
        which is most of a short validation fold.
        """
        lo = max(0, lo)
        hi = min(hi, len(self.dates))
        return FeatureSet(
            list(self.symbols),
            self.dates[lo:hi],
            {sym: {name: series[lo:hi] for name, series in feats.items()}
             for sym, feats in self.matrix.items()},
            max(0, self.warmup - lo),
        )   # the clean cache is per-window, so the slice starts without one

    def series_view(self, symbols: Iterable[str], names: Iterable[str]
                    ) -> Dict[str, Dict[str, List[float]]]:
        """Resolve feature series once, for a loop that will index them per bar.

        The backtester walks thousands of bars; looking the same lists up
        again on every one is pure overhead.
        """
        wanted = list(names)
        return {symbol: {name: self._series(symbol, name)
                         for name in wanted if name in self.matrix[symbol]}
                for symbol in symbols}

    def snapshot(self, symbol: str, i: int,
                 names: Optional[Iterable[str]] = None) -> Dict[str, float]:
        """Market features for one symbol at bar ``i`` (NaN -> 0.0).

        ``names`` restricts the result to the features a caller actually reads.
        A rule typically references three or four of the forty-odd available,
        and building the rest is the single largest cost in a backtest.
        """
        available = self.matrix[symbol]
        wanted = available.keys() if names is None else names
        return {name: self._series(symbol, name)[i]
                for name in wanted if name in available}


def _annualised_vol(close: np.ndarray, window: int,
                    periods_per_year: float = TRADING_DAYS) -> np.ndarray:
    r = ind.returns(close, 1)
    r = np.where(np.isnan(r), 0.0, r)
    return ind.rolling_std(r, window) * np.sqrt(periods_per_year)


def build_features(universe: Universe,
                   periods_per_year: float = TRADING_DAYS) -> FeatureSet:
    """Compute every market feature for every symbol on the shared calendar."""
    symbols = universe.symbols
    n = len(universe)
    # Equal-weighted market composite used for the regime features.
    comp = np.zeros(n, dtype=float)
    for sym in symbols:
        c = universe.bars[sym].close
        comp += c / c[0]
    comp /= max(len(symbols), 1)
    mkt = {
        "mkt_ret20": ind.returns(comp, 20),
        "mkt_above_sma200": (comp > ind.sma(comp, 200)).astype(float),
        "mkt_vol20": _annualised_vol(comp, 20, periods_per_year),
    }
    mkt["mkt_above_sma200"][:200] = np.nan

    matrix: Dict[str, Dict[str, np.ndarray]] = {}
    for sym in symbols:
        b = universe.bars[sym]
        c, h, l, o, v = b.close, b.high, b.low, b.open, b.volume
        sma20, sma50 = ind.sma(c, 20), ind.sma(c, 50)
        sma100, sma200 = ind.sma(c, 100), ind.sma(c, 200)
        macd_line, macd_sig, macd_hist = ind.macd(c)
        upper, _, lower, bb_pct = ind.bollinger(c, 20, 2.0)
        atr14 = ind.atr(h, l, c, 14)
        vol20 = _annualised_vol(c, 20, periods_per_year)
        vol60 = _annualised_vol(c, 60, periods_per_year)
        hi52 = ind.rolling_max(c, min(252, n))
        lo52 = ind.rolling_min(c, min(252, n))
        vol_avg = ind.sma(v, 20)
        with np.errstate(divide="ignore", invalid="ignore"):
            f: Dict[str, np.ndarray] = {
                "open": o, "high": h, "low": l, "close": c, "volume": v,
                "ret1": ind.returns(c, 1), "ret5": ind.returns(c, 5),
                "ret20": ind.returns(c, 20), "ret60": ind.returns(c, 60),
                "sma10": ind.sma(c, 10), "sma20": sma20, "sma50": sma50,
                "sma100": sma100, "sma200": sma200,
                "ema12": ind.ema(c, 12), "ema26": ind.ema(c, 26),
                "dist_sma20": c / sma20 - 1.0,
                "dist_sma50": c / sma50 - 1.0,
                "dist_sma100": c / sma100 - 1.0,
                "dist_sma200": c / sma200 - 1.0,
                "sma20_slope": ind.returns(sma20, 5),
                "rsi7": ind.rsi(c, 7), "rsi14": ind.rsi(c, 14),
                "macd": macd_line, "macd_signal": macd_sig, "macd_hist": macd_hist,
                "atr14": atr14, "atr_pct": atr14 / c,
                "vol20": vol20, "vol60": vol60,
                "vol_ratio_20_60": np.where(vol60 > 0, vol20 / vol60, 1.0),
                "bb_upper": upper, "bb_lower": lower, "bb_pct": bb_pct,
                "zscore20": ind.zscore(c, 20),
                "pct_of_52w_high": c / hi52,
                "pct_off_52w_low": c / lo52 - 1.0,
                "volume_ratio": np.where(vol_avg > 0, v / vol_avg, 1.0),
            }
        f.update({k: val.copy() for k, val in mkt.items()})
        missing = set(MARKET_FEATURES) - set(f)
        if missing:  # pragma: no cover - guards against a rename going unnoticed
            raise RuntimeError(f"feature builder missing {sorted(missing)}")
        matrix[sym] = f

    # Warm-up: the first bar at which the slowest indicator is defined for all
    # symbols.  Trading before this point would be trading on NaN-filled zeros.
    warmup = 0
    for sym in symbols:
        for name in ("sma200", "vol60", "rsi14", "macd_signal"):
            series = matrix[sym][name]
            valid = np.flatnonzero(~np.isnan(series))
            warmup = max(warmup, int(valid[0]) if valid.size else n)
    warmup = min(warmup, max(n - 30, 0))
    return FeatureSet(symbols, list(universe.calendar), matrix, warmup)
