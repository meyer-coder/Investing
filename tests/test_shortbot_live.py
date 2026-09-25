"""shortbot live path, against fakes: the API client, the order handling, and
that the live loop takes the same trades the backtest does."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from shortbot import backtest as bt
from shortbot.config import BotConfig, StrategyParams
from shortbot.data import NY, Session, session_from_bars
from shortbot.live import LiveBot, PaperBroker, TopstepBroker
from shortbot.topstepx import ApiError, OrderType, PositionType, Side, TopstepXClient


# ------------------------------------------------------------------ API client

class FakeTransport:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, url, data, headers):
        self.calls.append((url.rsplit("/api/", 1)[-1], json.loads(data or b"{}"), dict(headers)))
        status, body = self.replies.pop(0)
        return status, json.dumps(body).encode()


OK = {"success": True, "errorCode": 0, "errorMessage": None}


def test_client_logs_in_and_sends_bearer_token():
    t = FakeTransport([(200, {**OK, "token": "abc"}), (200, {**OK, "accounts": [{"id": 7}]})])
    c = TopstepXClient("jane", "key", transport=t)
    assert c.accounts() == [{"id": 7}]
    assert t.calls[0][0] == "Auth/loginKey" and t.calls[0][1] == {"userName": "jane", "apiKey": "key"}
    assert t.calls[1][2]["Authorization"] == "Bearer abc"
    assert t.calls[1][1] == {"onlyActiveAccounts": True}


def test_client_raises_on_business_failure():
    t = FakeTransport([(200, {**OK, "token": "abc"}),
                       (200, {"success": False, "errorCode": 2, "errorMessage": "rejected"})])
    c = TopstepXClient("jane", "key", transport=t)
    with pytest.raises(ApiError) as e:
        c.place_order(1, "CON.F.US.MNQ.Z26", OrderType.MARKET, Side.SELL, 1)
    assert e.value.code == 2


def test_client_logs_in_again_after_401():
    t = FakeTransport([(200, {**OK, "token": "old"}), (401, {}),
                       (200, {**OK, "token": "new"}), (200, {**OK, "positions": []})])
    c = TopstepXClient("jane", "key", transport=t)
    assert c.open_positions(1) == []
    assert t.calls[-1][2]["Authorization"] == "Bearer new"


def test_bars_come_back_oldest_first_and_front_month_is_the_active_mnq():
    bars = {**OK, "bars": [{"t": "2026-09-24T14:35:00+00:00", "o": 2, "h": 3, "l": 1, "c": 2, "v": 5},
                           {"t": "2026-09-24T14:30:00+00:00", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 4}]}
    contracts = {**OK, "contracts": [
        {"id": "CON.F.US.MNQ.U26", "symbolId": "F.US.MNQ", "activeContract": False},
        {"id": "CON.F.US.MNQ.Z26", "symbolId": "F.US.MNQ", "activeContract": True},
        {"id": "CON.F.US.MNQM.Z26", "symbolId": "F.US.MNQM", "activeContract": True}]}
    t = FakeTransport([(200, {**OK, "token": "x"}), (200, bars), (200, contracts)])
    c = TopstepXClient("jane", "key", transport=t)
    rows = c.bars("CON.F.US.MNQ.Z26", datetime(2026, 9, 24, tzinfo=timezone.utc),
                  datetime(2026, 9, 25, tzinfo=timezone.utc))
    assert [r[0] for r in rows] == sorted(r[0] for r in rows)
    assert t.calls[1][1]["contractId"] == "CON.F.US.MNQ.Z26" and t.calls[1][1]["live"] is False
    assert c.front_month("MNQ")["id"] == "CON.F.US.MNQ.Z26"


# ----------------------------------------------------------------- order flow

class FakeExchange:
    """In-memory TopstepX account holding at most one MNQ position."""

    CONTRACT = "CON.F.US.MNQ.Z26"

    def __init__(self, price=20000.0):
        self.price, self.pos, self.avg = price, 0, 0.0        # pos > 0 means short
        self.orders, self.fills, self.next_id = {}, [], 1
        self.fail_stop = False

    def place_order(self, acct, contract, order_type, side, size, limit_price=None,
                    stop_price=None, tag=None):
        oid, self.next_id = self.next_id, self.next_id + 1
        if order_type == OrderType.STOP and self.fail_stop:
            raise ApiError("/api/Order/place", 2, "rejected")
        self.orders[oid] = {"id": oid, "contractId": contract, "type": order_type, "side": side,
                            "size": size, "stopPrice": stop_price, "status": 1}
        if order_type == OrderType.MARKET:
            self.orders[oid]["status"] = 2
            self.pos += size if side == Side.SELL else -size
            self.avg = self.price
            self.fills.append({"contractId": contract, "side": side, "price": self.price})
        return oid

    def cancel_order(self, acct, oid):
        self.orders[oid]["status"] = 3

    def open_orders(self, acct):
        return [o for o in self.orders.values() if o["status"] == 1]

    def open_positions(self, acct):
        if self.pos == 0:
            return []
        return [{"contractId": self.CONTRACT, "size": abs(self.pos), "averagePrice": self.avg,
                 "type": PositionType.SHORT if self.pos > 0 else PositionType.LONG}]

    def close_position(self, acct, contract):
        if self.pos:
            self.fills.append({"contractId": contract, "price": self.price,
                               "side": Side.BUY if self.pos > 0 else Side.SELL})
            self.pos = 0

    def trades(self, acct, start, end=None):
        return self.fills

    def trigger_stops(self):
        for o in self.open_orders(1):
            if o["type"] == OrderType.STOP and self.price >= o["stopPrice"]:
                o["status"] = 2
                self.close_position(1, o["contractId"])


class Feed:
    contract_id = FakeExchange.CONTRACT


def broker(ex):
    return TopstepBroker(ex, 1, Feed(), BotConfig().risk, lambda m: None, sleep=lambda s: None)


def test_entry_is_a_market_sell_followed_by_a_protective_buy_stop():
    ex = FakeExchange(price=20000.0)
    entry, stop = broker(ex).open_short(2, 40.1, ref_price=20000.0)
    assert entry == 20000.0 and ex.pos == 2
    (stop_order,) = ex.open_orders(1)
    assert stop_order["side"] == Side.BUY and stop_order["type"] == OrderType.STOP
    assert stop_order["size"] == 2 and stop_order["stopPrice"] == stop == 20040.25   # rounded up a tick


def test_a_short_that_cannot_get_its_stop_is_closed_at_once():
    ex = FakeExchange()
    ex.fail_stop = True
    with pytest.raises(ApiError):
        broker(ex).open_short(1, 40, ref_price=20000.0)
    assert ex.pos == 0


def test_closing_cancels_the_stop_first_and_leaves_nothing_behind():
    ex = FakeExchange(price=20000.0)
    b = broker(ex)
    b.open_short(1, 40, ref_price=20000.0)
    ex.price = 19950.0
    assert b.close(19950.0) == 19950.0
    assert ex.pos == 0 and ex.open_orders(1) == []


def test_stop_fill_is_detected_and_reported():
    ex = FakeExchange(price=20000.0)
    b = broker(ex)
    b.open_short(1, 40, ref_price=20000.0)
    assert b.stopped_out(high=20010.0) is None
    ex.price = 20041.0
    ex.trigger_stops()
    assert b.stopped_out(high=20041.0) == 20041.0
    assert ex.open_orders(1) == []


def test_reconcile_flattens_leftovers_from_an_earlier_run():
    ex = FakeExchange()
    ex.place_order(1, ex.CONTRACT, OrderType.MARKET, Side.SELL, 3)
    ex.place_order(1, ex.CONTRACT, OrderType.STOP, Side.BUY, 3, stop_price=20100)
    broker(ex).reconcile()
    assert ex.pos == 0 and ex.open_orders(1) == []


# -------------------------------------------------------------- the live loop

def make_session(date, closes, wick=2.0):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    rows = [(570 + 5 * k, o, max(o, c) + wick, min(o, c) - wick, c, 100.0)
            for k, (o, c) in enumerate(zip(opens, closes))]
    return session_from_bars(date, 5, rows)


class ReplayFeed:
    """Serves a finished day bar by bar as if it were happening now."""

    bar_minutes = 5

    def __init__(self, prior, today):
        self.prior, self.full = prior, today

    def history(self, now, sessions):
        return self.prior

    def today(self, now):
        m = now.astimezone(NY).hour * 60 + now.astimezone(NY).minute
        k = int(np.sum(self.full.minute + 5 <= m))
        if k == 0:
            return None
        f = self.full
        return Session(f.date, 5, f.minute[:k], f.open[:k], f.high[:k], f.low[:k],
                       f.close[:k], f.volume[:k])

    def last_price(self, now):
        m = now.astimezone(NY).hour * 60 + now.astimezone(NY).minute
        j = int(np.searchsorted(self.full.minute, m, side="right")) - 1
        if j < 0:
            return None
        if self.full.minute[j] == m:          # a bar just opened
            return float(self.full.open[j]), float(self.full.open[j])
        return float(self.full.close[j]), float(self.full.high[j])


def replay_day(tmp_path, cfg):
    rng = np.random.default_rng(11)
    prior = [make_session(f"2026-03-{d:02d}", 20000 + np.cumsum(rng.normal(0, 8, 78)))
             for d in (2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 16, 17)]
    closes = np.concatenate([np.full(20, 20000.0), 20000 - 12 * np.arange(1, 25),
                             20000 - 12 * 24 + 6 * np.sin(np.arange(34))])
    today = make_session("2026-03-18", closes)
    feed = ReplayFeed(prior, today)
    logs = []
    bot = LiveBot(cfg, feed, PaperBroker(cfg.risk, logs.append), logs.append,
                  kill_file=str(tmp_path / "STOP"), trade_log=str(tmp_path / "trades.csv"))
    t = datetime(2026, 3, 18, 9, 20, tzinfo=NY)
    while t <= datetime(2026, 3, 18, 16, 5, tzinfo=NY):
        bot.step((t + timedelta(seconds=5)).astimezone(timezone.utc))
        t += timedelta(minutes=1)
    return bot, prior, today, logs


def test_live_loop_takes_the_same_entries_as_the_backtest(tmp_path):
    cfg = BotConfig()
    cfg.strategy = replace(cfg.strategy, skip_fomc=False, profile_days=10)
    bot, prior, today, logs = replay_day(tmp_path, cfg)
    tested = bt.run(prior + [today], cfg)
    tested = [t for t in tested if t.date == today.date]
    shorts = [l for l in logs if l.startswith("SHORT")]
    assert tested, "the synthetic selloff should trigger the strategy"
    assert len(shorts) == len(tested)
    for line, t in zip(shorts, tested):
        assert f"[{t.setup}]" in line
        assert f"@ {t.entry:.2f}" in line          # next bar's open, one tick worse, in both
    assert bot.pos is None                          # flat by the end of the day
    rows = (tmp_path / "trades.csv").read_text().strip().splitlines()
    assert len(rows) == len(tested) + 1


def test_kill_switch_flattens_and_stops(tmp_path):
    cfg = BotConfig()
    cfg.strategy = replace(cfg.strategy, skip_fomc=False)
    feed = ReplayFeed([], make_session("2026-03-18", np.full(78, 20000.0)))
    logs = []
    bot = LiveBot(cfg, feed, PaperBroker(cfg.risk, logs.append), logs.append,
                  kill_file=str(tmp_path / "STOP"), trade_log=str(tmp_path / "t.csv"))
    bot.pos = {"entry": 20010.0, "stop": 20050.0, "target": 19950.0, "n": 1, "minute": 600,
               "setup": "test", "reason": ""}
    bot.date = "2026-03-18"
    (tmp_path / "STOP").write_text("")
    assert bot.step(datetime(2026, 3, 18, 11, 0, 5, tzinfo=NY).astimezone(timezone.utc)) is False
    assert bot.pos is None and any("kill switch" in l for l in logs)


def test_never_acts_on_a_stale_bar_after_a_restart(tmp_path):
    cfg = BotConfig()
    cfg.strategy = replace(cfg.strategy, skip_fomc=False)
    logs = []
    feed = ReplayFeed([make_session(f"2026-03-{d:02d}", np.full(78, 20000.0) + (np.arange(78) % 3))
                       for d in range(2, 14)],
                      make_session("2026-03-18", np.linspace(20000, 19000, 78)))
    bot = LiveBot(cfg, feed, PaperBroker(cfg.risk, logs.append), logs.append,
                 kill_file=str(tmp_path / "STOP"), trade_log=str(tmp_path / "t.csv"))
    # start at 11:03:30 -- the last closed bar ended at 11:00, more than a minute ago
    bot.step(datetime(2026, 3, 18, 11, 3, 30, tzinfo=NY).astimezone(timezone.utc))
    assert not any(l.startswith("SHORT") for l in logs)


def test_live_refuses_settings_that_can_lose_the_account_on_one_trade():
    from shortbot.live import account_risk_problem, run_live
    cfg = BotConfig()
    assert account_risk_problem(cfg) is None                       # default: ~$250 a trade
    cfg.risk = replace(cfg.risk, risk_per_trade_usd=1e9, max_contracts=50, max_stop_risk_usd=1e9)
    assert "single stop-out" in account_risk_problem(cfg)         # all-in: 50 MNQ
    cfg.risk = replace(BotConfig().risk, risk_per_trade_usd=250, max_stop_risk_usd=2500)
    assert account_risk_problem(cfg) is not None                   # one wide 1-lot stop
    with pytest.raises(SystemExit, match="refusing"):
        run_live(cfg, live=True, account_id=1)                     # stops before any network call


def test_big_drop_preset_is_one_trade_a_day_and_survives_a_stop():
    from shortbot.live import account_risk_problem
    cfg = BotConfig.load("configs/shortbot-bigdrop.json")
    s = cfg.strategy
    assert (s.momentum, s.orb, s.vwap_reject, s.max_trades_per_day) == (True, False, False, 1)
    assert account_risk_problem(cfg) is None
