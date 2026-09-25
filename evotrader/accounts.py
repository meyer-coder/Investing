"""The owner's funded futures accounts, with each firm's rules written in.

Two accounts: a FundedNext Futures Legacy 25K and a Topstep 100K.  A
FundedNext Legacy 50K is kept beside them as the smallest FundedNext account
with a $2,000 limit.  Every replay of a bot on these accounts
(strategies/sweeps/funded.py, strategies/sweeps/sweetspot.py) and the Pine
script (profitable-strategies/futures/breakout-bot/
noise_area_breakout_funded.pine) take their numbers from here.

What all three share, checked on the firms' own pages on 2026-09-25:

* the maximum loss limit trails the highest end-of-day balance, never moves
  down, and locks once it reaches the starting balance;
* it is watched in real time: an open loss that touches it ends the account;
* after the first payout it locks at the starting balance for good;
* positions must be flat by 15:10 Chicago time (the bot is flat by 14:59).

Sources: fundednext.com/futures/legacy and fundednext.com/futures-challenge-terms
(fees, targets, limits, 40% consistency in the challenge only, contract caps,
80% split); helpfutures.fundednext.com (the limit locks at the starting
balance after the first withdrawal); help.topstep.com articles on the Maximum
Loss Limit, the Daily Loss Limit, consistency (55%), the payout policy and
the Express Funded Account; topstep.com/no-activation-fee (prices).  Two
numbers could not be read as text on the firm's own page and come from
third-party guides: Topstep's $6,000 target (Topstep shows it in an image),
and FundedNext's $100 benchmark day for the 25K.  Check both against the
plan bought.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Account:
    name: str
    firm: str
    balance: float                  # starting balance
    max_loss: float                 # trails the best end-of-day balance, locks at the start
    target: float                   # challenge profit target
    consistency: float              # challenge: best day <= this share of the profit (0 = none)
    daily_loss: float               # 0 = none; hitting it ends the day, not the account
    max_micros: int                 # the most micro contracts open at once
    # costs
    challenge_fee: float            # per attempt (FundedNext: one time; Topstep: a month)
    monthly: bool                   # the challenge fee is charged every month while in the challenge
    activation_fee: float           # paid once on passing
    # payouts from the funded account
    split: float                    # the trader's share of a payout
    split_first: float              # Topstep: 100% of the first $10,000 of lifetime payouts
    payout_days: int                # winning days needed since the last payout
    payout_day_min: float           # a winning day is at least this much
    payout_share: float             # the most of the profit one payout may take
    payout_cap: float               # dollar cap per payout (0 = none)


FUNDEDNEXT_25K = Account(
    name="FundedNext Legacy 25K", firm="FundedNext", balance=25_000.0,
    max_loss=1_000.0, target=1_250.0, consistency=0.40, daily_loss=0.0, max_micros=20,
    challenge_fee=79.99, monthly=False, activation_fee=0.0,
    split=0.80, split_first=0.0, payout_days=5, payout_day_min=100.0, payout_share=0.50, payout_cap=0.0)

FUNDEDNEXT_50K = Account(
    name="FundedNext Legacy 50K", firm="FundedNext", balance=50_000.0,
    max_loss=2_000.0, target=3_000.0, consistency=0.40, daily_loss=0.0, max_micros=30,
    challenge_fee=199.99, monthly=False, activation_fee=0.0,
    split=0.80, split_first=0.0, payout_days=5, payout_day_min=100.0, payout_share=0.50, payout_cap=0.0)

TOPSTEP_100K = Account(
    name="Topstep 100K", firm="Topstep", balance=100_000.0,
    max_loss=3_000.0, target=6_000.0, consistency=0.55, daily_loss=2_000.0, max_micros=100,
    challenge_fee=99.0, monthly=True, activation_fee=149.0,
    split=0.90, split_first=10_000.0, payout_days=5, payout_day_min=150.0, payout_share=0.50, payout_cap=5_000.0)

#: the owner's two accounts, and the comparison
OWNER: Dict[str, Account] = {a.name: a for a in (FUNDEDNEXT_25K, TOPSTEP_100K)}
ALL: Dict[str, Account] = {a.name: a for a in (FUNDEDNEXT_25K, FUNDEDNEXT_50K, TOPSTEP_100K)}

SESSIONS_A_MONTH = 21
