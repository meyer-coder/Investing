"""The live bot when things go wrong: every failure must end with the account
flat, or the position still protected by its stop -- never a naked or
growing position.  Each test reproduces a bug found in review."""
import json
import urllib.error
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from shortbot.config import BotConfig
from shortbot.data import NY
from shortbot.live import LiveBot, PaperBroker, TopstepBroker
from shortbot.topstepx import ApiError, OrderType, Side, TopstepXClient, _epoch
from test_shortbot_live import FakeExchange, Feed, ReplayFeed, make_session

NET = ApiError("/api/x", "network", "timed out")


class FlakyExchange(FakeExchange):
    """FakeExchange that can fail chosen calls, answer empty position reads,
    or fill an entry late."""

    def __init__(self, price=20000.0):
        super().__init__(price)
        self.fail = {}              # call name -> list of exceptions for the next calls
        self.empty_reads = 0        # next N position reads come back empty
        self.late_fill = 0          # a market entry shows up only after N position reads
        self._pending = None

    def _hit(self, name):
        queue = self.fail.get(name)
        if queue:
            raise queue.pop(0)

    def place_order(self, acct, contract, order_type, side, size, limit_price=None,
                    stop_price=None, tag=None):
        self._hit("stop" if order_type == OrderType.STOP else "market")
        if order_type == OrderType.MARKET and self.late_fill:
            oid, self.next_id = self.next_id, self.next_id + 1
            self._pending = (side, size, self.late_fill)
            self.orders[oid] = {"id": oid, "contractId": contract, "type": order_type, "side": side,
                                "size": size, "stopPrice": None, "status": 1}
            return oid
        return super().place_order(acct, contract, order_type, side, size, limit_price,
                                   stop_price, tag)

    def open_positions(self, acct):
        self._hit("positions")
        if self._pending:
            side, size, left = self._pending
            if left <= 1:
                self._pending = None
                self.pos += size if side == Side.SELL else -size
                self.avg = self.price
                for o in self.orders.values():
                    if o["type"] == OrderType.MARKET:
                        o["status"] = 2
            else:
                self._pending = (side, size, left - 1)
        if self.empty_reads:
            self.empty_reads -= 1
            return []
        return super().open_positions(acct)

    def cancel_order(self, acct, oid):
        self._hit("cancel")
        super().cancel_order(acct, oid)

    def close_position(self, acct, contract):
        self._hit("close")
        super().close_position(acct, contract)


def broker(ex):
    return TopstepBroker(ex, 1, Feed(), BotConfig().risk, lambda m: None, sleep=lambda s: None)


# --------------------------------------------------------------- entry failures

@pytest.mark.parametrize("where", ["stop", "positions"])
def test_a_failure_during_entry_leaves_the_account_flat(where):
    ex = FlakyExchange()
    ex.fail[where] = [NET]
    with pytest.raises(ApiError):
        broker(ex).open(-1, 2, 40, ref_price=20000.0)
    assert ex.pos == 0 and ex.open_orders(1) == []


def test_a_non_api_error_during_entry_also_flattens():
    ex = FlakyExchange()
    ex.fail["stop"] = [TimeoutError("socket timed out")]
    with pytest.raises(TimeoutError):
        broker(ex).open(-1, 1, 40, ref_price=20000.0)
    assert ex.pos == 0 and ex.open_orders(1) == []


def test_a_late_fill_is_closed_not_left_unprotected():
    ex = FlakyExchange()
    ex.late_fill = 25                       # shows up after the 20 checks the bot waits for
    with pytest.raises(RuntimeError, match="not filled"):
        broker(ex).open(-1, 2, 40, ref_price=20000.0)
    for _ in range(10):                     # whenever it lands, flatten_everything closed it
        ex.open_positions(1)
    b = broker(ex)
    assert b.ensure_flat() is False         # the next check before a trade catches and closes it
    assert ex.pos == 0 and ex.open_orders(1) == []


def test_an_existing_position_never_makes_the_bot_add_more():
    ex = FlakyExchange()
    ex.place_order(1, ex.CONTRACT, OrderType.MARKET, Side.SELL, 3)   # untracked leftover
    with pytest.raises(RuntimeError, match="ordered 2"):
        broker(ex).open(-1, 2, 40, ref_price=20000.0)
    assert ex.pos == 0 and ex.open_orders(1) == []


# --------------------------------------------------------------- close failures

def test_if_the_close_fails_the_stop_is_put_back():
    ex = FlakyExchange()
    b = broker(ex)
    b.open(-1, 1, 40, ref_price=20000.0)
    ex.fail["close"] = [NET]
    with pytest.raises(RuntimeError, match="did not close"):
        b.close(20000.0)
    assert ex.pos == 1
    (stop,) = ex.open_orders(1)
    assert stop["type"] == OrderType.STOP and stop["side"] == Side.BUY and stop["stopPrice"] == 20040.0


def test_a_stop_that_cannot_be_cancelled_is_reported_loudly():
    ex = FlakyExchange()
    b = broker(ex)
    b.open(-1, 1, 40, ref_price=20000.0)
    ex.fail["cancel"] = [NET] * 10
    with pytest.raises(RuntimeError, match="still resting"):
        b.close(20000.0)
    assert ex.pos == 0


# ------------------------------------------------------------- stop detection

def test_one_empty_position_read_does_not_cancel_the_stop():
    ex = FlakyExchange()
    b = broker(ex)
    b.open(-1, 1, 40, ref_price=20000.0)
    ex.empty_reads = 1
    assert b.check_flat(20000.0, 20000.0) == (False, None)
    assert len(ex.open_orders(1)) == 1 and ex.pos == 1


def test_flat_without_a_visible_fill_is_still_flat():
    ex = FlakyExchange()
    b = broker(ex)
    b.open(-1, 1, 40, ref_price=20000.0)
    ex.pos = 0                                   # stop filled, but Trade/search is behind
    ex.fills.clear()
    assert b.check_flat(20000.0, 20000.0) == (True, None)
    assert ex.open_orders(1) == []


# ------------------------------------------------------------------ the loop

def _prior():
    rng = np.random.default_rng(1)
    return [make_session(f"2026-03-{d:02d}", 20000 + np.cumsum(rng.normal(0, 8, 78)))
            for d in (2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 16, 17)]


def _bot(tmp_path, feed, brk=None, logs=None):
    cfg = BotConfig()
    cfg.strategy.skip_fomc = False
    logs = [] if logs is None else logs
    return LiveBot(cfg, feed, brk or PaperBroker(cfg.risk, logs.append), logs.append,
                   kill_file=str(tmp_path / "STOP"), trade_log=str(tmp_path / "t.csv"),
                   sleep=lambda s: None), logs


def at(h, m, s=5):
    return datetime(2026, 3, 18, h, m, s, tzinfo=NY).astimezone(timezone.utc)


class NoPrice(ReplayFeed):
    def last_price(self, now, since=None):
        return None


def test_flatten_happens_even_without_a_price(tmp_path):
    feed = NoPrice(_prior(), make_session("2026-03-18", np.full(78, 20000.0)))
    bot, logs = _bot(tmp_path, feed)
    bot.date = "2026-03-18"
    bot.pos = {"side": -1, "entry": 20010.0, "stop": 20050.0, "target": 19950.0, "n": 1,
               "minute": 900, "deadline": 950, "opened_ts": 0.0, "setup": "t", "reason": ""}
    bot.broker.side, bot.broker.n, bot.broker.stop = -1, 1, 20050.0
    bot.step(at(15, 51))
    assert bot.pos is None and any("(flatten)" in l for l in logs)


def test_a_position_is_closed_even_after_hours(tmp_path):
    feed = ReplayFeed(_prior(), make_session("2026-03-18", np.full(78, 20000.0)))
    bot, logs = _bot(tmp_path, feed)
    bot.date = "2026-03-18"
    bot.pos = {"side": -1, "entry": 20010.0, "stop": 20050.0, "target": 19950.0, "n": 1,
               "minute": 900, "deadline": 950, "opened_ts": 0.0, "setup": "t", "reason": ""}
    bot.broker.side, bot.broker.n, bot.broker.stop = -1, 1, 20050.0
    bot.step(at(16, 30))                         # outside the trading window
    assert bot.pos is None


def test_history_that_fails_to_load_is_retried(tmp_path):
    class Failing(ReplayFeed):
        calls = 0

        def history(self, now, sessions):
            Failing.calls += 1
            if Failing.calls == 1:
                raise ApiError("/api/History/retrieveBars", "network", "timeout")
            return super().history(now, sessions)

    feed = Failing(_prior(), make_session("2026-03-18", np.full(78, 20000.0)))
    bot, logs = _bot(tmp_path, feed)
    bot.step(at(9, 26))
    assert bot.date is None and any("retrying" in l for l in logs)
    bot.step(at(9, 27))
    assert bot.date == "2026-03-18" and bot.prof is not None


def test_an_entry_failure_stops_new_entries_for_the_day(tmp_path):
    class Refuses(PaperBroker):
        def open(self, *a, **k):
            raise ApiError("/api/Order/place", 2, "rejected")

    closes = np.concatenate([np.full(20, 20000.0), 20000 - 12 * np.arange(1, 25),
                             20000 - 12 * 24 + 6 * np.sin(np.arange(34))])
    feed = ReplayFeed(_prior(), make_session("2026-03-18", closes))
    cfg = BotConfig()
    bot, logs = _bot(tmp_path, feed, Refuses(cfg.risk, lambda m: None))
    t = at(9, 20)
    while t <= at(16, 0):
        bot.step(t)
        t += timedelta(minutes=1)
    assert sum("entry failed" in l for l in logs) == 1 and bot.day.done


def test_an_untracked_position_is_flattened_before_any_new_trade(tmp_path):
    ex = FlakyExchange()
    ex.place_order(1, ex.CONTRACT, OrderType.MARKET, Side.SELL, 4)   # someone else's position
    closes = np.concatenate([np.full(20, 20000.0), 20000 - 12 * np.arange(1, 25),
                             20000 - 12 * 24 + 6 * np.sin(np.arange(34))])
    feed = ReplayFeed(_prior(), make_session("2026-03-18", closes))
    feed.contract_id = ex.CONTRACT
    cfg = BotConfig()
    brk = TopstepBroker(ex, 1, feed, cfg.risk, lambda m: None, sleep=lambda s: None)
    bot, logs = _bot(tmp_path, feed, brk)
    t = at(9, 20)
    while t <= at(12, 0) and not bot.day.done:
        bot.step(t)
        t += timedelta(minutes=1)
    assert bot.day.done and ex.pos == 0 and bot.pos is None
    assert any("not flat" in l for l in logs)


def test_a_bar_that_closed_almost_two_minutes_ago_is_stale(tmp_path):
    closes = np.linspace(20000, 19000, 78)
    feed = ReplayFeed(_prior(), make_session("2026-03-18", closes))
    bot, logs = _bot(tmp_path, feed)
    bot.step(at(11, 46, 59))                     # the last closed bar ended at 11:45
    assert not any(l.startswith(("SHORT", "LONG")) for l in logs)


def test_live_refuses_accounts_not_marked_simulated(monkeypatch):
    import shortbot.live as live

    class Client:
        def __init__(self, *a, **k):
            pass

        def login(self):
            pass

        def accounts(self):
            return [{"id": 7, "name": "X", "balance": 0, "canTrade": True}]   # no 'simulated'

        def front_month(self, symbol):
            return {"id": "CON.F.US.MNQ.Z26"}

    monkeypatch.setenv("TOPSTEPX_USERNAME", "u")
    monkeypatch.setenv("TOPSTEPX_API_KEY", "k")
    monkeypatch.setattr(live, "TopstepXClient", Client)
    with pytest.raises(SystemExit, match="not a simulated account"):
        live.run_live(BotConfig(), live=True, account_id=7, log_path="/dev/null")


# --------------------------------------------------------------- API client

def test_network_errors_and_garbage_become_api_errors():
    def boom(url, data, headers):
        raise urllib.error.URLError("connection reset")

    c = TopstepXClient("u", "k", transport=boom)
    with pytest.raises(ApiError, match="network"):
        c.login()

    replies = [(200, json.dumps({"success": True, "token": "t"}).encode()), (200, b"<html>")]
    c = TopstepXClient("u", "k", transport=lambda url, data, headers: replies.pop(0))
    with pytest.raises(ApiError, match="bad reply"):
        c.accounts()


def test_timestamps_without_a_zone_are_utc():
    assert _epoch("2026-09-24T14:30:00") == _epoch("2026-09-24T14:30:00+00:00")
