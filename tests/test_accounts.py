"""The owner's accounts (evotrader/accounts.py) agree with the other places that carry the same firm's rules."""
import re
import sys
from pathlib import Path

from evotrader import accounts, prop

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "profitable-strategies" / "futures" / "breakout-bot" / "noise_area_breakout_funded.pine"


def test_fundednext_accounts_match_the_legacy_rules_in_prop():
    for acc, rules, fee in ((accounts.FUNDEDNEXT_25K, prop.LEGACY_25K, "25K"),
                            (accounts.FUNDEDNEXT_50K, prop.LEGACY_50K, "50K")):
        assert (acc.balance, acc.target, acc.max_loss, acc.consistency) == \
            (rules.account, rules.target, rules.max_loss, rules.consistency)
        assert acc.challenge_fee == prop.LEGACY_FEES[fee]
        assert acc.daily_loss == 0.0 and not acc.monthly


def test_topstep_plan_in_the_mnq_studies_is_the_same_account():
    sys.path.insert(0, str(ROOT / "strategies" / "mnq"))
    try:
        import account
    finally:
        sys.path.remove(str(ROOT / "strategies" / "mnq"))
    t, p = accounts.TOPSTEP_100K, account.TOPSTEP_100K
    assert (p.max_loss, p.daily_loss, p.target, p.consistency, p.max_micros) == \
        (t.max_loss, t.daily_loss, t.target, t.consistency, t.max_micros)


def test_the_owner_has_the_two_accounts():
    assert set(accounts.OWNER) == {"FundedNext Legacy 25K", "Topstep 100K"}
    assert accounts.TOPSTEP_100K.consistency == 0.55 and accounts.FUNDEDNEXT_25K.max_loss == 1000.0


def test_the_pine_script_carries_the_same_limits():
    src = PINE.read_text()
    for acc in accounts.ALL.values():
        m = re.search(r'"' + re.escape(acc.name) + r'"\s*=>\s*array\.from\(([^)]*)\)', src)
        assert m, acc.name
        max_loss, daily_loss = (float(x) for x in m.group(1).split(",")[:2])
        assert (max_loss, daily_loss) == (acc.max_loss, acc.daily_loss), acc.name
