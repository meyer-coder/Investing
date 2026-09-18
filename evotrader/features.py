"""Per-bar feature construction — the 'senses' every agent trades on.

Features are computed once per universe and shared by every genome in every
generation, which is what makes 100 agents x 1000 generations cheap.  The names
defined here are exactly the vocabulary available to the strategy DSL, so a
genome that references an unknown name fails validation instead of silently
evaluating to zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from . import indicators as ind
from .data import Universe

# Classic price/technical features derived from price history alone.
PRICE_FEATURES: List[str] = [
    "open", "high", "low", "close", "volume",
    "ret1", "ret5", "ret20", "ret60",
    "sma10", "sma20", "sma50", "sma200",
    "ema12", "ema26",
    "dist_sma20", "dist_sma50", "dist_sma200", "sma20_slope",
    "rsi7", "rsi14",
    "macd", "macd_signal", "macd_hist",
    "atr14", "atr_pct",
    "vol20", "vol60", "vol_ratio_20_60",
    "bb_upper", "bb_lower", "bb_pct", "zscore20",
    "pct_of_52w_high", "pct_off_52w_low", "volume_ratio",
    "mkt_ret20", "mkt_above_sma200", "mkt_vol20",
]

# Liquidity-sweep and order-flow features.
#
# Daily bars carry no order book and no trade tape, so nothing here claims to be
# real order flow.  What a daily bar does carry is the footprint of one: where
# price went looking for resting liquidity (the highs and lows everyone can see,
# where stops sit), whether it stayed there or was rejected, and how much volume
# it took to move.  These features make that footprint explicit and measurable
# instead of leaving it for a rule to reconstruct out of open/high/low/close.
LIQUIDITY_FEATURES: List[str] = [
    # where the resting liquidity is
    "prior_high_20", "prior_low_20", "prior_high_60", "prior_low_60",
    "dist_prior_high_20", "dist_prior_low_20",
    "equal_highs_20", "equal_lows_20",
    # sweeps: price takes out a level and fails to hold it
    "sweep_high", "sweep_low", "sweep_high_60", "sweep_low_60",
    "sweep_high_depth", "sweep_low_depth",
    "bars_since_sweep_high", "bars_since_sweep_low",
    "breakout_20", "breakdown_20",
    # bar internals: who won the bar
    "clv", "clv_avg5", "upper_wick", "lower_wick", "body_pct",
    "range_atr", "gap_pct", "displacement",
    # order-flow proxies built from signed volume
    "net_flow", "cum_flow_5", "cum_flow_20", "cmf20", "obv_slope",
    "volume_z20", "absorption", "effort_result",
    # where volume actually traded
    "vwap20", "vwap60", "dist_vwap20", "dist_vwap60", "volume_below_pct",
    # imbalances left behind by a fast move
    "fvg_up", "fvg_down", "bars_since_fvg_up", "bars_since_fvg_down",
]

#: Everything computed from market data, in the order the breeder is shown it.
MARKET_FEATURES: List[str] = PRICE_FEATURES + LIQUIDITY_FEATURES

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
    "sma200": "200-bar simple moving average",
    "ema12": "12-bar exponential moving average",
    "ema26": "26-bar exponential moving average",
    "dist_sma20": "(close/sma20)-1, fractional distance above the 20-bar mean",
    "dist_sma50": "(close/sma50)-1",
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
    "prior_high_20": "highest high of the previous 20 bars, excluding this one — the "
                     "sell-side liquidity pool above price",
    "prior_low_20": "lowest low of the previous 20 bars, excluding this one — the "
                    "buy-side liquidity pool below price",
    "prior_high_60": "highest high of the previous 60 bars, excluding this one",
    "prior_low_60": "lowest low of the previous 60 bars, excluding this one",
    "dist_prior_high_20": "(close/prior_high_20)-1; 0 means sitting exactly on the "
                          "20-bar high, negative means below it",
    "dist_prior_low_20": "(close/prior_low_20)-1; positive means holding above the "
                         "20-bar low",
    "equal_highs_20": "how many of the last 20 bars have a high within 0.25 ATR of "
                      "prior_high_20; 3+ is a cluster of equal highs, i.e. a thick "
                      "pool of stops",
    "equal_lows_20": "same count on the low side; a thick pool of sell stops",
    "sweep_high": "1 when this bar traded above prior_high_20 but closed back below "
                  "it — buy stops taken, then rejected (bearish for a long)",
    "sweep_low": "1 when this bar traded below prior_low_20 but closed back above it "
                 "— sell stops taken, then reclaimed (the classic long setup)",
    "sweep_high_60": "same as sweep_high against the 60-bar high — a deeper raid",
    "sweep_low_60": "same as sweep_low against the 60-bar low — a deeper raid",
    "sweep_high_depth": "how far above prior_high_20 the sweep reached, in ATRs "
                        "(0 when there was no sweep)",
    "sweep_low_depth": "how far below prior_low_20 the sweep reached, in ATRs "
                       "(0 when there was no sweep)",
    "bars_since_sweep_high": "bars since the last sweep_high; 0 on the sweep bar, "
                             "999 if it has never happened",
    "bars_since_sweep_low": "bars since the last sweep_low; 0 on the sweep bar, "
                            "999 if it has never happened",
    "breakout_20": "1 when the close is above prior_high_20 — the level was taken "
                   "and accepted, not swept",
    "breakdown_20": "1 when the close is below prior_low_20",
    "clv": "close location value: +1 closing on the high of the bar, -1 on the low, "
           "0 in the middle; the cheapest read on who won the bar",
    "clv_avg5": "5-bar average of clv; positive means closes are persistently strong",
    "upper_wick": "upper shadow as a fraction of the bar's range; large means supply "
                  "rejected higher prices",
    "lower_wick": "lower shadow as a fraction of the bar's range; large means demand "
                  "rejected lower prices",
    "body_pct": "|close-open| as a fraction of the bar's range; near 0 is indecision",
    "range_atr": "this bar's true range divided by atr14; above 1.5 is an expansion bar",
    "gap_pct": "(open/previous close)-1; overnight gaps leave unfilled liquidity behind",
    "displacement": "(close - previous close) / atr14 — the bar's directional thrust "
                    "measured in ATRs",
    "net_flow": "signed volume for this bar: clv * volume / 20-bar average volume. "
                "Positive means volume traded into strength",
    "cum_flow_5": "5-bar average of net_flow — short-term order-flow pressure",
    "cum_flow_20": "20-bar average of net_flow — the persistent side of the flow",
    "cmf20": "Chaikin money flow over 20 bars, roughly -1..1; above 0.05 is "
             "accumulation, below -0.05 distribution",
    "obv_slope": "20-bar change in on-balance volume divided by the volume traded in "
                 "those bars, roughly -1..1",
    "volume_z20": "z-score of volume against its 20-bar mean; 2+ is a genuine surge",
    "absorption": "1 when volume is over 1.5x average but the bar's range is under "
                  "0.8 ATR — heavy trade going nowhere, i.e. someone absorbing it",
    "effort_result": "range_atr divided by the volume ratio: price moved per unit of "
                     "volume. Low means effort without result",
    "vwap20": "20-bar volume-weighted average price",
    "vwap60": "60-bar volume-weighted average price",
    "dist_vwap20": "(close/vwap20)-1; where price sits against the short-term "
                   "volume-weighted average",
    "dist_vwap60": "(close/vwap60)-1",
    "volume_below_pct": "share of the last 60 bars' volume that traded below today's "
                        "close, 0..1; near 1 means price is above almost all recent "
                        "volume (most holders are in profit)",
    "fvg_up": "1 when this bar's low is above the high of two bars ago — a bullish "
              "gap in the auction that was never traded back into",
    "fvg_down": "1 when this bar's high is below the low of two bars ago",
    "bars_since_fvg_up": "bars since the last bullish imbalance (999 if never)",
    "bars_since_fvg_down": "bars since the last bearish imbalance (999 if never)",
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

    def snapshot(self, symbol: str, i: int) -> Dict[str, float]:
        """Market features for one symbol at bar ``i`` (NaN -> 0.0)."""
        out: Dict[str, float] = {}
        for name, series in self.matrix[symbol].items():
            v = series[i]
            out[name] = 0.0 if (v is None or np.isnan(v)) else float(v)
        return out


def _annualised_vol(close: np.ndarray, window: int) -> np.ndarray:
    r = ind.returns(close, 1)
    r = np.where(np.isnan(r), 0.0, r)
    return ind.rolling_std(r, window) * np.sqrt(TRADING_DAYS)


#: Lookback windows for the liquidity features.  20 bars is "the level everyone
#: watching a daily chart can see"; 60 bars is the quarter-scale pool.
SWEEP_WINDOW = 20
DEEP_WINDOW = 60
FLOW_WINDOW = 20
PROFILE_WINDOW = 60


def _liquidity_features(b, atr14: np.ndarray, vol_avg: np.ndarray) -> Dict[str, np.ndarray]:
    """Liquidity-sweep and order-flow features for one symbol.

    Every level is built from *shifted* data, so the bar being tested can never
    contribute to the level it is tested against: a bar cannot sweep its own
    high.  Values are legal to act on at the close of bar ``i``; the runner
    fills the resulting order at bar ``i+1``'s open.
    """
    o, h, l, c, v = b.open, b.high, b.low, b.close, b.volume
    n = c.size
    prev_close = ind.shift(c, 1)
    bar_range = h - l
    tr = ind.true_range(h, l, c)
    typ = (h + l + c) / 3.0

    with np.errstate(divide="ignore", invalid="ignore"):
        # ---- bar internals: how the bar closed relative to its own range
        clv = np.where(bar_range > 0, ((c - l) - (h - c)) / bar_range, 0.0)
        upper_wick = np.where(bar_range > 0, (h - np.maximum(o, c)) / bar_range, 0.0)
        lower_wick = np.where(bar_range > 0, (np.minimum(o, c) - l) / bar_range, 0.0)
        body_pct = np.where(bar_range > 0, np.abs(c - o) / bar_range, 0.0)
        range_atr = np.where(atr14 > 0, tr / atr14, np.nan)
        gap_pct = np.where(prev_close > 0, o / prev_close - 1.0, 0.0)
        displacement = np.where(atr14 > 0, (c - prev_close) / atr14, np.nan)
        volume_ratio = np.where(vol_avg > 0, v / vol_avg, 1.0)

        # ---- liquidity pools: the levels a stop run would target
        prior_high_20 = ind.rolling_max(ind.shift(h, 1), SWEEP_WINDOW)
        prior_low_20 = ind.rolling_min(ind.shift(l, 1), SWEEP_WINDOW)
        prior_high_60 = ind.rolling_max(ind.shift(h, 1), DEEP_WINDOW)
        prior_low_60 = ind.rolling_min(ind.shift(l, 1), DEEP_WINDOW)

        # Equal highs/lows: several bars stalling at the same level means stops
        # have been piling up there, which is what makes the level worth raiding.
        tol = 0.25 * atr14
        equal_highs = np.zeros(n)
        equal_lows = np.zeros(n)
        for k in range(1, SWEEP_WINDOW + 1):
            equal_highs += (np.abs(ind.shift(h, k) - prior_high_20) <= tol).astype(float)
            equal_lows += (np.abs(ind.shift(l, k) - prior_low_20) <= tol).astype(float)

        # ---- the sweep itself: through the level intrabar, back inside by the close
        swept_high = (h > prior_high_20) & (c < prior_high_20)
        swept_low = (l < prior_low_20) & (c > prior_low_20)
        swept_high_60 = (h > prior_high_60) & (c < prior_high_60)
        swept_low_60 = (l < prior_low_60) & (c > prior_low_60)
        sweep_high_depth = np.where(swept_high & (atr14 > 0),
                                    (h - prior_high_20) / atr14, 0.0)
        sweep_low_depth = np.where(swept_low & (atr14 > 0),
                                   (prior_low_20 - l) / atr14, 0.0)

        # ---- order-flow proxies: volume signed by where the bar closed
        money_flow_volume = clv * v
        net_flow = np.where(vol_avg > 0, money_flow_volume / vol_avg, 0.0)
        vol_sum = ind.rolling_sum(v, FLOW_WINDOW)
        cmf20 = np.where(vol_sum > 0,
                         ind.rolling_sum(money_flow_volume, FLOW_WINDOW) / vol_sum, 0.0)
        obv_line = ind.obv(c, v)
        obv_slope = np.where(vol_sum > 0,
                             (obv_line - ind.shift(obv_line, FLOW_WINDOW)) / vol_sum, 0.0)
        absorption = ((volume_ratio > 1.5) & (range_atr < 0.8)).astype(float)
        effort_result = range_atr / np.maximum(volume_ratio, 0.25)

        # ---- volume-weighted reference prices
        vwap20 = np.where(vol_sum > 0, ind.rolling_sum(typ * v, FLOW_WINDOW) / vol_sum, np.nan)
        vol_sum60 = ind.rolling_sum(v, PROFILE_WINDOW)
        vwap60 = np.where(vol_sum60 > 0,
                          ind.rolling_sum(typ * v, PROFILE_WINDOW) / vol_sum60, np.nan)
        dist_vwap20 = c / vwap20 - 1.0
        dist_vwap60 = c / vwap60 - 1.0

        # ---- a poor man's volume profile: how much recent volume is below price
        below = np.zeros(n)
        total = np.zeros(n)
        for k in range(PROFILE_WINDOW):
            tk = ind.shift(typ, k)
            vk = np.nan_to_num(ind.shift(v, k))
            below += np.where(tk < c, vk, 0.0)
            total += vk
        volume_below_pct = np.where(total > 0, below / total, 0.5)
        volume_below_pct[:PROFILE_WINDOW - 1] = np.nan

    # ---- imbalances: a three-bar window the auction jumped straight through
    fvg_up = (l > ind.shift(h, 2)).astype(float)
    fvg_down = (h < ind.shift(l, 2)).astype(float)

    return {
        "prior_high_20": prior_high_20, "prior_low_20": prior_low_20,
        "prior_high_60": prior_high_60, "prior_low_60": prior_low_60,
        "dist_prior_high_20": c / prior_high_20 - 1.0,
        "dist_prior_low_20": c / prior_low_20 - 1.0,
        "equal_highs_20": equal_highs, "equal_lows_20": equal_lows,
        "sweep_high": swept_high.astype(float), "sweep_low": swept_low.astype(float),
        "sweep_high_60": swept_high_60.astype(float),
        "sweep_low_60": swept_low_60.astype(float),
        "sweep_high_depth": sweep_high_depth, "sweep_low_depth": sweep_low_depth,
        "bars_since_sweep_high": ind.bars_since(swept_high.astype(float)),
        "bars_since_sweep_low": ind.bars_since(swept_low.astype(float)),
        "breakout_20": (c > prior_high_20).astype(float),
        "breakdown_20": (c < prior_low_20).astype(float),
        "clv": clv, "clv_avg5": ind.sma(clv, 5),
        "upper_wick": upper_wick, "lower_wick": lower_wick, "body_pct": body_pct,
        "range_atr": range_atr, "gap_pct": gap_pct, "displacement": displacement,
        "net_flow": net_flow,
        "cum_flow_5": ind.sma(net_flow, 5), "cum_flow_20": ind.sma(net_flow, FLOW_WINDOW),
        "cmf20": cmf20, "obv_slope": obv_slope,
        "volume_z20": ind.zscore(v, FLOW_WINDOW),
        "absorption": absorption, "effort_result": effort_result,
        "vwap20": vwap20, "vwap60": vwap60,
        "dist_vwap20": dist_vwap20, "dist_vwap60": dist_vwap60,
        "volume_below_pct": volume_below_pct,
        "fvg_up": fvg_up, "fvg_down": fvg_down,
        "bars_since_fvg_up": ind.bars_since(fvg_up),
        "bars_since_fvg_down": ind.bars_since(fvg_down),
    }


def build_features(universe: Universe) -> FeatureSet:
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
        "mkt_vol20": _annualised_vol(comp, 20),
    }
    mkt["mkt_above_sma200"][:200] = np.nan

    matrix: Dict[str, Dict[str, np.ndarray]] = {}
    for sym in symbols:
        b = universe.bars[sym]
        c, h, l, o, v = b.close, b.high, b.low, b.open, b.volume
        sma20, sma50, sma200 = ind.sma(c, 20), ind.sma(c, 50), ind.sma(c, 200)
        macd_line, macd_sig, macd_hist = ind.macd(c)
        upper, _, lower, bb_pct = ind.bollinger(c, 20, 2.0)
        atr14 = ind.atr(h, l, c, 14)
        vol20, vol60 = _annualised_vol(c, 20), _annualised_vol(c, 60)
        hi52 = ind.rolling_max(c, min(252, n))
        lo52 = ind.rolling_min(c, min(252, n))
        vol_avg = ind.sma(v, 20)
        with np.errstate(divide="ignore", invalid="ignore"):
            f: Dict[str, np.ndarray] = {
                "open": o, "high": h, "low": l, "close": c, "volume": v,
                "ret1": ind.returns(c, 1), "ret5": ind.returns(c, 5),
                "ret20": ind.returns(c, 20), "ret60": ind.returns(c, 60),
                "sma10": ind.sma(c, 10), "sma20": sma20, "sma50": sma50,
                "sma200": sma200, "ema12": ind.ema(c, 12), "ema26": ind.ema(c, 26),
                "dist_sma20": c / sma20 - 1.0,
                "dist_sma50": c / sma50 - 1.0,
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
        f.update(_liquidity_features(b, atr14, vol_avg))
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
