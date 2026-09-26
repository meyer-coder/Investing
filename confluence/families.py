"""Fifty confluence families and the generator that turns them into strategies.

A family is a trading idea written as legs (see ``components.py``): a bias, a
location and a trigger, sometimes more than one of each.  The generator then
crosses each family with the dimensions a trader actually chooses —

    market x timeframe x session x entry order x stop x target x extra filter

— and samples a balanced set of variants.  Every variant gets an ID in the
``FF-VVV`` form (family, variant) and a descriptive name, e.g.

    07-031  "Hull-Slope VWAP Hold + RSI room · MNQ 5m NY am · stop entry, swing stop, 2R"

Family 50 is the RANDOM control: coin-flip entries run through the same
markets, sessions, stops, targets and costs.  It is the yardstick for luck —
a strategy that does not beat the controls has not shown an edge.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .bars import SESSION_ORDER
from .components import LEGS
from .markets import MARKET_ORDER

TIMEFRAMES = [1, 3, 5, 15, 30, 60]
TF_WEIGHT = {1: 0.07, 3: 0.10, 5: 0.25, 15: 0.25, 30: 0.18, 60: 0.15}
ENTRIES = ["market", "stop", "limit"]
ENTRY_TEXT = {
    "market": "market order at the next bar's open",
    "stop": "buy-stop 1 tick above the signal bar's high, valid 3 bars",
    "limit": "buy-limit at the signal bar's midpoint, valid 3 bars",
}
STOPS = ["ATR 1.0", "ATR 1.5", "swing", "signal bar"]
STOP_TEXT = {
    "ATR 1.0": "1.0 x ATR(14) from entry",
    "ATR 1.5": "1.5 x ATR(14) from entry",
    "swing": "0.1 ATR beyond the 5-bar swing low",
    "signal bar": "0.1 ATR beyond the signal bar's low",
}
TARGETS = ["1R", "1.5R", "2R", "3R", "trail", "session"]
TARGET_TEXT = {
    "1R": "take profit at 1R", "1.5R": "take profit at 1.5R", "2R": "take profit at 2R",
    "3R": "take profit at 3R",
    "trail": "no fixed target; after +1R trail a stop 2 ATR behind the best price",
    "session": "no fixed target; hold to the session exit",
}
GROUPS = ["Trend pullback", "Liquidity sweep", "Breakout", "Mean reversion",
          "Session / ICT", "Momentum", "Control"]


@dataclass(frozen=True)
class Family:
    num: int
    name: str
    group: str
    thesis: str
    legs: Tuple[str, ...]                 # always-on confluences
    extras: Tuple[str, ...] = ()          # optional extra filter, one at most per variant
    sessions: Tuple[str, ...] = tuple(SESSION_ORDER)
    timeframes: Tuple[int, ...] = tuple(TIMEFRAMES)
    targets: Tuple[str, ...] = tuple(TARGETS)

    @property
    def fid(self) -> str:
        return "CTRL" if self.group == "Control" else f"{self.num:02d}"


TREND_X = ("atr_hot", "rsi_room", "adx_up", "strong_close", "not_extended")
REV_X = ("atr_calm", "strong_close", "range_spike", "rsi_room")
BRK_X = ("atr_hot", "adx_up", "strong_close", "range_spike")
NY = ("NY am", "NY pm", "Ldn+NY")
ALL_BUT_ASIA = ("London", "NY am", "NY pm", "Ldn+NY", "all")
INTRA = (1, 3, 5, 15, 30)

FAMILIES: List[Family] = [
    # ---------------------------------------------------------------- trend pullback
    Family(1, "EMA Pullback Engulf", "Trend pullback",
           "In a stacked-EMA uptrend, buy the first engulfing candle after price tags the 20 EMA.",
           ("ema_stack", "pb_ema20", "engulf"), TREND_X),
    Family(2, "VWAP Trend Pullback", "Trend pullback",
           "With the higher timeframe trending, a dip to VWAP that closes back above it and takes out the prior high is the continuation entry.",
           ("htf", "vwap_retest", "prev_high"), TREND_X),
    Family(3, "Triple-Stack Pullback", "Trend pullback",
           "Three independent 'up' reads (HTF trend, above VWAP, 20 EMA held) plus a break of structure.",
           ("htf", "vwap_side", "pb_ema20", "bos"), TREND_X),
    Family(4, "Daily-Bias 50EMA Pin", "Trend pullback",
           "Daily bias and the 200 EMA agree; a pin bar off the 50 EMA marks the end of the pullback.",
           ("daily", "ema200", "pb_ema50", "pin"), TREND_X),
    Family(5, "Supertrend Pullback RSI Reset", "Trend pullback",
           "Supertrend long, price back at the 20 EMA, and RSI regaining 40 shows momentum resuming.",
           ("supertrend", "pb_ema20", "rsi_reset"), TREND_X),
    Family(6, "ADX Trend MACD Pullback", "Trend pullback",
           "A real trend (ADX > 20, above 200 EMA) pulls back to the 20 EMA; the MACD cross is the go signal.",
           ("adx", "ema200", "pb_ema20", "macd_cross"), TREND_X),
    Family(7, "Hull-Slope VWAP Hold", "Trend pullback",
           "Rising Hull MA and a VWAP retest; the Heikin-Ashi flip confirms buyers are back.",
           ("hull", "vwap_retest", "ha_flip"), TREND_X),
    Family(8, "Fib Golden-Pocket Engulf", "Trend pullback",
           "On an up day with the HTF trend, the 50-61.8% pullback of the day's leg plus an engulfing candle.",
           ("day_open", "htf", "fib", "engulf"), TREND_X),
    Family(9, "FVG Retest in Trend", "Trend pullback",
           "Imbalances left by the trend tend to be revisited and defended; buy the defence.",
           ("htf", "fvg", "prev_high"), TREND_X),
    Family(10, "Order-Block Mitigation BOS", "Trend pullback",
           "Above the 200 EMA, price returns to the last down candle before a displacement and breaks structure again.",
           ("ema200", "ob", "bos"), TREND_X),
    Family(11, "Stochastic Trend Dip", "Trend pullback",
           "Stacked EMAs with ADX confirming; a stochastic cross from oversold times the dip.",
           ("ema_stack", "adx", "stoch_cross"), TREND_X),
    Family(12, "MACD Zero-Line 50EMA", "Trend pullback",
           "MACD above zero and price above the 200 EMA; the 50 EMA retest with a MACD cross resumes the trend.",
           ("macd0", "ema200", "pb_ema50", "macd_cross"), TREND_X),
    # ---------------------------------------------------------------- liquidity sweeps
    Family(13, "Prior-Day Low Sweep & Reclaim", "Liquidity sweep",
           "Stops rest under yesterday's low; a sweep and reclaim in the direction of the daily bias traps sellers.",
           ("daily", "pdl_sweep", "prev_high"), REV_X),
    Family(14, "Asia Sweep London Reversal", "Liquidity sweep",
           "London often runs the Asia range's stops before the real move; trade the reclaim with the HTF trend.",
           ("htf", "asia_sweep", "bos"), REV_X, sessions=("London", "Ldn+NY")),
    Family(15, "London Sweep NY Reversal", "Liquidity sweep",
           "NY takes out the London low, then reverses in the direction of the daily bias.",
           ("daily", "london_sweep", "engulf"), REV_X, sessions=NY),
    Family(16, "Overnight Low Sweep VWAP Reclaim", "Liquidity sweep",
           "The cash session sweeps the overnight low and reclaims it while holding above VWAP.",
           ("vwap_side", "on_sweep", "prev_high"), REV_X, sessions=NY),
    Family(17, "Turtle Soup 200EMA", "Liquidity sweep",
           "A false break of the 20-bar low with the 200 EMA below; the pin bar shows the rejection.",
           ("ema200", "turtle", "pin"), REV_X),
    Family(18, "Prior-Week Low Sweep", "Liquidity sweep",
           "Weekly liquidity: sweep of last week's low, reclaimed with a break of structure, with the daily bias.",
           ("daily", "pw_sweep", "bos"), REV_X),
    Family(19, "Double Bottom RSI Divergence", "Liquidity sweep",
           "A retest of a recent low that RSI refuses to confirm.",
           ("dbl", "rsi_div"), REV_X),
    Family(20, "Round-Number Stop Hunt", "Liquidity sweep",
           "Stops cluster at round numbers; a pin bar through one, in the HTF trend direction.",
           ("htf", "round", "pin"), REV_X),
    Family(21, "Judas Swing", "Liquidity sweep",
           "The NY open fakes against the daily bias by sweeping London's low, then displaces back above the midnight open.",
           ("daily", "midnight", "london_sweep", "displacement"), REV_X, sessions=("NY am", "Ldn+NY")),
    # ---------------------------------------------------------------- breakouts
    Family(22, "ORB + VWAP + Trend", "Breakout",
           "Opening-range breakout only when price is above VWAP and the HTF trend agrees.",
           ("htf", "vwap_side", "or_break"), BRK_X, sessions=NY),
    Family(23, "ORB Retest Continuation", "Breakout",
           "Let the opening range break, wait for the retest to hold, then go.",
           ("vwap_side", "or_retest", "prev_high"), BRK_X, sessions=NY),
    Family(24, "Initial Balance Breakout", "Breakout",
           "Break of the first hour's range in the HTF trend direction, on a bar that closes near its extreme.",
           ("htf", "ib_break", "strong_close"), BRK_X, sessions=("NY am", "NY pm", "Ldn+NY")),
    Family(25, "Asia Range London Breakout", "Breakout",
           "London breaks the Asia range in the direction of the HTF trend, closing near the bar's extreme.",
           ("htf", "asia_break", "strong_close"), BRK_X, sessions=("London", "Ldn+NY")),
    Family(26, "Prior-Day High Breakout ADX", "Breakout",
           "A trending market (ADX) takes out yesterday's high with a displacement candle.",
           ("adx", "pdh_break", "displacement"), BRK_X),
    Family(27, "Donchian Breakout HTF ADX", "Breakout",
           "20-bar breakout with the HTF trend and a rising ADX.",
           ("htf", "adx", "donchian_break", "adx_up"), ("atr_hot", "strong_close", "range_spike")),
    Family(28, "Squeeze Release BOS", "Breakout",
           "Volatility compression releases; take the break of structure in the HTF direction.",
           ("htf", "squeeze", "bos"), BRK_X),
    Family(29, "NR7 Trend Expansion", "Breakout",
           "A narrow-range bar inside a Supertrend and 200 EMA uptrend, then a close above its high.",
           ("ema200", "supertrend", "nr7", "prev_high"), BRK_X),
    Family(30, "Inside Bar at VWAP", "Breakout",
           "An inside bar right after a VWAP retest; the break of the inside bar is the entry.",
           ("vwap_retest", "inside_break"), BRK_X),
    Family(31, "Overnight High Break & Go", "Breakout",
           "NY takes out the overnight high while above VWAP.",
           ("vwap_side", "on_break", "prev_high"), BRK_X, sessions=NY),
    Family(32, "Displacement into FVG", "Breakout",
           "HTF trend, a fresh fair-value gap, and a displacement candle out of it.",
           ("htf", "fvg", "displacement"), BRK_X),
    # ---------------------------------------------------------------- mean reversion
    Family(33, "VWAP 2σ Fade", "Mean reversion",
           "In a ranging tape, a pin bar back inside the 2σ VWAP band targets the mean.",
           ("range", "vwap_2sd", "pin"), REV_X),
    Family(34, "Bollinger RSI Range Reversal", "Mean reversion",
           "ADX says range; lower Bollinger tag plus RSI leaving oversold.",
           ("range", "bb_touch", "rsi_os"), REV_X),
    Family(35, "Keltner Snapback Exhaustion", "Mean reversion",
           "Four bars in one direction into the Keltner band, then the first reversal close.",
           ("range", "kc_touch", "exhaustion"), REV_X),
    Family(36, "Bollinger RSI Divergence", "Mean reversion",
           "Band tag with bullish RSI divergence: selling pressure is fading.",
           ("bb_touch", "rsi_div"), REV_X),
    Family(37, "Pivot S1 Bounce RSI", "Mean reversion",
           "Floor pivots in a range: S1 holds and RSI crosses up from oversold.",
           ("range", "pivot", "rsi_os"), REV_X),
    Family(38, "NY Gap Fill", "Mean reversion",
           "Opening gaps in index futures tend to fill; trade toward yesterday's close.",
           ("gap", "prev_high"), REV_X, sessions=("NY am",)),
    Family(39, "Initial Balance Fade", "Mean reversion",
           "In a range regime a failed break of the first hour's range reverses back inside.",
           ("range", "ib_fade", "engulf"), REV_X, sessions=("NY am", "NY pm", "Ldn+NY")),
    Family(40, "Exhaustion at Prior-Day Level", "Mean reversion",
           "Four bars pushing through yesterday's low, then the first bar back up.",
           ("pdl_sweep", "exhaustion"), REV_X),
    # ---------------------------------------------------------------- session / ICT
    Family(41, "Silver Bullet FVG", "Session / ICT",
           "ICT Silver Bullet: in the 10-11 / 14-15 ET windows, an FVG retest with the daily bias.",
           ("daily", "sb_window", "fvg", "prev_high"), TREND_X, sessions=("NY am", "NY pm", "Ldn+NY")),
    Family(42, "Power of Three", "Session / ICT",
           "Asia accumulates, London manipulates past the Asia range, NY distributes back through the midnight open.",
           ("po3", "bos"), TREND_X, sessions=("NY am", "NY pm", "Ldn+NY")),
    Family(43, "Midnight-Open Order Block", "Session / ICT",
           "Daily bias and the midnight-open side agree; enter on an order-block retest.",
           ("daily", "midnight", "ob", "prev_high"), TREND_X),
    Family(44, "London Killzone Continuation", "Session / ICT",
           "HTF trend and an up day; buy the London-session pullback to the 20 EMA on an engulfing candle.",
           ("htf", "day_open", "pb_ema20", "engulf"), TREND_X, sessions=("London", "Ldn+NY")),
    Family(45, "NY Open Drive", "Session / ICT",
           "A displacement candle in the first 30 minutes of NY, above the open and with the HTF trend.",
           ("ny_first30", "ny_open_side", "htf", "displacement"), BRK_X, sessions=("NY am", "Ldn+NY")),
    # ---------------------------------------------------------------- momentum
    Family(46, "EMA 9/21 Cross VWAP ADX", "Momentum",
           "Fast EMA cross, above VWAP, in a trending ADX regime.",
           ("vwap_side", "adx", "ema_cross"), TREND_X),
    Family(47, "Supertrend Flip HTF", "Momentum",
           "Take Supertrend flips only in the direction of the higher-timeframe trend.",
           ("htf", "st_flip"), TREND_X),
    Family(48, "Heikin-Ashi Flip EMA Stack", "Momentum",
           "Heikin-Ashi turns bullish inside a stacked-EMA trend.",
           ("ema_stack", "ha_flip"), TREND_X),
    Family(49, "Three-Bar Push Daily Bias", "Momentum",
           "Three strong bars in the direction of the daily bias, above VWAP.",
           ("daily", "vwap_side", "three_bar"), TREND_X),
    # ---------------------------------------------------------------- control
    Family(50, "RANDOM control", "Control",
           "Coin-flip entries with the same sessions, stops, targets and costs. The luck baseline.",
           (), ()),
]

FAMILY_BY_NUM: Dict[int, Family] = {f.num: f for f in FAMILIES}


@dataclass
class Strategy:
    sid: str
    name: str
    family: int
    market: str
    tf: int
    session: str
    entry: str
    stop: str
    target: str
    legs: Tuple[str, ...]
    extra: Optional[str]
    seed: int = 0

    @property
    def fam(self) -> Family:
        return FAMILY_BY_NUM[self.family]

    @property
    def group(self) -> str:
        return self.fam.group

    @property
    def confluences(self) -> int:
        return len(self.legs)

    def rules(self) -> List[str]:
        """Plain-English rules, long side (shorts mirror them)."""
        if self.fam.group == "Control":
            out = ["enter at random (about one signal every two sessions), long or short on a coin flip"]
        else:
            out = [f"{LEGS[c].kind}: {LEGS[c].text}" for c in self.legs]
        out.append(f"entry: {ENTRY_TEXT[self.entry]}")
        out.append(f"stop: {STOP_TEXT[self.stop]} (never tighter than 0.3 ATR)")
        out.append(f"target: {TARGET_TEXT[self.target]}")
        out.append(f"session: {self.session} entries; flat at the session exit; max 4 trades a day")
        return out

    def to_dict(self) -> dict:
        d = asdict(self)
        d["group"] = self.group
        d["confluences"] = self.confluences
        return d


def _name(fam: Family, extra: Optional[str], market: str, tf: int, session: str,
          entry: str, stop: str, target: str) -> str:
    base = fam.name if extra is None else f"{fam.name} + {LEGS[extra].label}"
    return f"{base} · {market} {tf}m {session} · {entry} entry, {stop} stop, {target}"


def generate(per_family: int = 210, seed: int = 7,
             markets: Sequence[str] = tuple(MARKET_ORDER),
             families: Sequence[Family] = tuple(FAMILIES),
             controls_per_cell: int = 20) -> List[Strategy]:
    """Balanced, deterministic sample of variants for every family.

    Markets are dealt round-robin so each gets the same share of every family;
    timeframes follow ``TF_WEIGHT``; everything else is uniform over what the
    family allows.  Duplicates are rejected, so every ID is a distinct test.

    Controls are laid out on a grid instead — ``controls_per_cell`` for every
    market x target pair — because each real strategy is compared with the
    controls that share its market and exit style.
    """
    out: List[Strategy] = []
    for fam in families:
        rng = random.Random(f"{seed}-{fam.num}")
        seen = set()
        tfs = [t for t in fam.timeframes]
        weights = [TF_WEIGHT[t] for t in tfs]
        extras: List[Optional[str]] = [None, None] + list(fam.extras)   # 'no extra' twice as likely
        control = fam.group == "Control"
        quota = len(markets) * len(fam.targets) * controls_per_cell if control else per_family
        k = 0
        attempts = 0
        while k < quota and attempts < quota * 200:
            attempts += 1
            if control:
                market = markets[k % len(markets)]
                target = fam.targets[(k // len(markets)) % len(fam.targets)]
            else:
                market = markets[k % len(markets)]
                target = None
            tf = rng.choices(tfs, weights)[0]
            session = rng.choice(fam.sessions)
            entry = rng.choice(ENTRIES)
            stop = rng.choice(STOPS)
            target = target or rng.choice(fam.targets)
            extra = rng.choice(extras) if fam.group != "Control" else None
            key = (market, tf, session, entry, stop, target, extra)
            if key in seen:
                continue
            seen.add(key)
            k += 1
            legs = fam.legs + ((extra,) if extra else ())
            sid = f"{fam.fid}-{k:03d}"
            sd = int(hashlib.sha1(sid.encode()).hexdigest()[:8], 16)
            out.append(Strategy(sid, _name(fam, extra, market, tf, session, entry, stop, target),
                                fam.num, market, tf, session, entry, stop, target, legs, extra, sd))
    return out
