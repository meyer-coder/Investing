"""Every knob the bot has, in one place.

Times are minutes since midnight, New York time (570 = 09:30).  Stops and
targets are measured in *units*: one unit is the normal price range of a
``unit_minutes`` window at that time of day, taken from earlier sessions, so
the same settings size themselves to a quiet lunch hour or a wild open.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List


@dataclass
class StrategyParams:
    """What the bot looks for.  It only ever sells short."""

    # which setups may fire (the first three only sell short)
    orb: bool = True                  # break below the opening range
    momentum: bool = True             # big drop keeps going
    vwap_reject: bool = True          # rally up to VWAP fails on a down day
    basic: bool = False               # react to a run of same-coloured candles, long or short

    # basic: a run of green or red candles over the last ``basic_minutes`` that
    # covers ``basic_k`` x the normal range for that stretch of the day.
    # follow = buy green runs and short red runs; fade = short green, buy red.
    basic_mode: str = "follow"
    basic_minutes: int = 15
    basic_k: float = 1.0

    # opening-range breakdown
    or_minutes: int = 15              # opening range = first 15 minutes after 09:30
    orb_last_minute: int = 11 * 60    # no breakdown entries after 11:00

    # big-drop continuation
    mom_minutes: int = 60             # look at the move over the last hour...
    mom_k: float = 1.5                # ...short when it fell k x the normal range for that hour

    # VWAP rejection
    vr_first_minute: int = 10 * 60
    vr_tolerance: float = 0.1         # how close (in units) the high must get to VWAP

    # exits
    unit_minutes: int = 30
    stop_units: float = 1.0
    target_units: float = 1.5
    max_hold_minutes: int = 90

    # schedule
    first_entry_minute: int = 9 * 60 + 45
    last_entry_minute: int = 15 * 60
    flatten_minute: int = 15 * 60 + 50   # Topstep's hard cutoff is 3:10 PM CT = 16:10 New York

    # day limits
    max_trades_per_day: int = 3
    max_losses_per_day: int = 2
    cooldown_minutes: int = 10
    require_below_vwap: bool = True
    profile_days: int = 10            # sessions used to learn the "normal" range

    # only short on days that open in a downtrend: yesterday's close below the
    # average close of the ``trend_days`` sessions before it
    trend_filter: bool = False
    trend_days: int = 20

    # Fed announcement days: flat before 2 PM, no entries until the dust settles
    skip_fomc: bool = True
    fomc_flat_minute: int = 13 * 60 + 55
    fomc_resume_minute: int = 14 * 60 + 45


@dataclass
class RiskParams:
    """How much the bot risks, and what a contract costs to trade."""

    risk_per_trade_usd: float = 250.0
    max_contracts: int = 3
    max_stop_risk_usd: float = 400.0      # skip a trade whose 1-lot stop is wider than this
    daily_loss_stop_usd: float = 600.0    # stop for the day well before Topstep's $1,000 DLL
    daily_profit_stop_usd: float = 1200.0  # keep days small for the 55% consistency rule
    point_value: float = 2.0              # MNQ
    tick_size: float = 0.25
    commission_rt: float = 1.22           # TopstepX MNQ round turn, per contract
    slippage_ticks: int = 1               # on market entries, stops and time exits


@dataclass
class AccountRules:
    """Topstep 50K Trading Combine with the optional Daily Loss Limit, and the
    Express Funded Account (XFA) that follows it.  Prices are the Standard
    path as of 2026-09-25."""

    name: str = "Topstep 50K Combine"
    start_balance: float = 50_000.0
    profit_target: float = 3_000.0
    max_loss: float = 2_000.0          # trails the end-of-day high, locks at the start balance
    daily_loss: float = 1_000.0        # soft: flattens you for the day; 0 disables
    consistency: float = 0.55          # best day must be <= 55% of total profit
    max_contracts: int = 50            # MNQ
    flat_by_minute: int = 16 * 60 + 10  # 3:10 PM Chicago

    # costs
    monthly_fee: float = 49.0          # Combine subscription; each rebill includes one reset
    reset_fee: float = 49.0
    activation_fee: float = 149.0      # per Express Funded Account
    api_fee: float = 14.50             # TopstepX API, per month

    # Express Funded Account payouts (Standard path)
    payout_cap: float = 2_000.0        # per request; doubled while the DLL-at-purchase offer lasts
    winning_day: float = 150.0         # a day counts toward a payout at +$150 net
    winning_days: int = 5
    payout_split: float = 0.90
    min_payout: float = 125.0
    min_cycle_profit: float = 0.0      # profit needed since the last payout (FundedNext: $500)
    # the trader's choice, not a firm rule: balance to leave in the funded
    # account after a payout (after the first payout the balance is the only
    # cushion), e.g. one or two max losses; 0 takes the most allowed
    payout_keep: float = 0.0

    # "monthly": Topstep's subscription (rebills, reset credits, activation fee);
    # "one_time": a fee per challenge and a reset fee per failure (FundedNext)
    billing: str = "monthly"


TOPSTEP_ACCOUNTS = {
    "50k": AccountRules(),
    "100k": AccountRules(name="Topstep 100K Combine", start_balance=100_000.0,
                         profit_target=6_000.0, max_loss=3_000.0, daily_loss=2_000.0,
                         max_contracts=100, monthly_fee=99.0, reset_fee=99.0, payout_cap=3_000.0),
    "150k": AccountRules(name="Topstep 150K Combine", start_balance=150_000.0,
                         profit_target=9_000.0, max_loss=4_500.0, daily_loss=3_000.0,
                         max_contracts=150, monthly_fee=199.0, reset_fee=199.0, payout_cap=5_000.0),
}

# FundedNext Futures Legacy 25K (fundednext.com/futures and its help center,
# 2026-09-25): $79.99 a challenge, $73.99 a reset, a $1,250 target with no day
# over 40% of the profit, a $1,000 max loss trailing the end-of-day balance and
# locking at the start, no daily limit, 20 micros; funded: 80% to you after 5
# benchmark days of $100+ and $500+ profit since the last payout, at most half
# the profit and $3,000 a payout, $250 minimum.
FUNDEDNEXT_ACCOUNTS = {
    "fn-legacy-25k": AccountRules(
        name="FundedNext Legacy 25K", start_balance=25_000.0, profit_target=1_250.0,
        max_loss=1_000.0, daily_loss=0.0, consistency=0.40, max_contracts=20,
        monthly_fee=79.99, reset_fee=73.99, activation_fee=0.0, api_fee=0.0,
        payout_cap=3_000.0, winning_day=100.0, winning_days=5, payout_split=0.80,
        min_payout=250.0, min_cycle_profit=500.0, billing="one_time"),
}

ACCOUNTS = {**TOPSTEP_ACCOUNTS, **FUNDEDNEXT_ACCOUNTS}


@dataclass
class BotConfig:
    strategy: StrategyParams = field(default_factory=StrategyParams)
    risk: RiskParams = field(default_factory=RiskParams)
    account: AccountRules = field(default_factory=AccountRules)
    symbol: str = "MNQ"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> "BotConfig":
        if self.account.billing not in ("monthly", "one_time"):
            raise ValueError(f"account billing must be 'monthly' or 'one_time', not {self.account.billing!r}")
        if self.strategy.basic_mode not in ("follow", "fade"):
            raise ValueError(f"basic_mode must be 'follow' or 'fade', not {self.strategy.basic_mode!r}")
        return self

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BotConfig":
        def build(kind, raw):
            known = {f.name for f in fields(kind)}
            unknown = set(raw) - known
            if unknown:
                raise ValueError(f"unknown {kind.__name__} settings: {sorted(unknown)}")
            return kind(**raw)
        return cls(strategy=build(StrategyParams, d.get("strategy", {})),
                   risk=build(RiskParams, d.get("risk", {})),
                   account=build(AccountRules, d.get("account", {})),
                   symbol=d.get("symbol", "MNQ")).validate()

    @classmethod
    def load(cls, path: str) -> "BotConfig":
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# FOMC statement days (2 PM New York).  Source: federalreserve.gov meeting
# calendars; add each year's dates as the Fed publishes them.
FOMC_DATES: List[str] = [
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31",
    "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
    "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
    "2026-09-16", "2026-10-28", "2026-12-09",
]
