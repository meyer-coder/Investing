"""Run the strategy in real time against TopstepX.

The default is a dry run: real TopstepX market data, simulated fills, and
nothing sent to the exchange.  ``--live`` places real orders on a
*simulated* Topstep account (Practice, Trading Combine or Express Funded).
Topstep does not allow the API on a Live Funded account, and requires the
bot to run on your own computer, not a VPS or remote server.

How a live trade is handled
---------------------------
1. When a 5-minute bar closes, the strategy is asked for an entry -- the same
   ``decide`` the backtest uses.
2. Entry is a market sell.  As soon as the short shows up, a buy-stop is
   placed at the stop price.  If the stop cannot be placed, the position is
   closed immediately.
3. The bot watches the price every few seconds and closes the position
   itself at the target, after ``max_hold_minutes``, at the flatten time,
   or when told to stop.  It cancels the stop before closing.
   Only the protective stop ever rests at the exchange, so a crash leaves
   the position protected rather than naked.
4. On start-up, any leftover MNQ position or order on the account is closed
   or cancelled: the bot never inherits a trade it did not open.

Stopping it
-----------
* Create a file named ``STOP`` in the working directory: it flattens and exits.
* Ctrl-C does the same.
"""
from __future__ import annotations

import csv
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple

from .backtest import size_trade
from .config import BotConfig, RiskParams
from .data import NY, RTH_CLOSE, RTH_OPEN, Session, full_day_bars, to_sessions
from .strategy import DayState, ShortStrategy
from .topstepx import ApiError, BarUnit, OrderType, PositionType, Side, TopstepXClient

Log = Callable[[str], None]


def _minute(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _ceil_tick(px: float, tick: float) -> float:
    return math.ceil(px / tick - 1e-9) * tick


# ------------------------------------------------------------------ market data

class TopstepFeed:
    """Bars for the current MNQ front month, as the strategy's Sessions."""

    def __init__(self, client: TopstepXClient, symbol: str = "MNQ", bar_minutes: int = 5):
        self.client, self.symbol, self.bar_minutes = client, symbol, bar_minutes
        self.contract_id = ""
        self.new_day()

    def new_day(self) -> None:
        """Re-resolve the front month each morning so a contract roll is picked up."""
        self.contract_id = self.client.front_month(self.symbol)["id"]

    def history(self, now: datetime, sessions: int) -> List[Session]:
        """Earlier complete regular sessions, oldest first."""
        start = now - timedelta(days=int(sessions * 1.6) + 7)
        rows = self.client.bars(self.contract_id, start, now, BarUnit.MINUTE, self.bar_minutes)
        today = now.astimezone(NY).strftime("%Y-%m-%d")
        done = to_sessions(rows, self.bar_minutes,
                           min_bars=int(0.8 * full_day_bars(self.bar_minutes)))
        return [s for s in done if s.date < today]

    def today(self, now: datetime) -> Optional[Session]:
        """Today's regular-session bars that have fully closed."""
        ny = now.astimezone(NY)
        open_ny = ny.replace(hour=RTH_OPEN // 60, minute=RTH_OPEN % 60, second=0, microsecond=0)
        rows = self.client.bars(self.contract_id, open_ny, now, BarUnit.MINUTE, self.bar_minutes)
        cutoff = now.timestamp()
        rows = [r for r in rows if r[0] + 60 * self.bar_minutes <= cutoff]
        ss = to_sessions(rows, self.bar_minutes)
        return ss[-1] if ss and ss[-1].date == ny.strftime("%Y-%m-%d") else None

    def last_price(self, now: datetime) -> Optional[Tuple[float, float]]:
        """(last price, highest price of the last two minutes) from 1-minute bars."""
        rows = self.client.bars(self.contract_id, now - timedelta(minutes=3), now,
                                BarUnit.MINUTE, 1, include_partial=True)
        if not rows:
            return None
        return rows[-1][4], max(r[2] for r in rows[-2:])


# ---------------------------------------------------------------------- brokers

class PaperBroker:
    """Dry run: fills at the latest price, one tick worse; nothing is sent anywhere."""

    live = False

    def __init__(self, risk: RiskParams, log: Log):
        self.r, self.log = risk, log
        self.n, self.stop = 0, 0.0

    def reconcile(self) -> None:
        pass

    def open_short(self, n: int, stop_pts: float, ref_price: float) -> Tuple[float, float]:
        entry = ref_price - self.r.slippage_ticks * self.r.tick_size
        self.n, self.stop = n, _ceil_tick(entry + stop_pts, self.r.tick_size)
        return entry, self.stop

    def stopped_out(self, high: float) -> Optional[float]:
        if self.n and high >= self.stop:
            self.n = 0
            return self.stop + self.r.slippage_ticks * self.r.tick_size
        return None

    def close(self, ref_price: float) -> float:
        self.n = 0
        return ref_price + self.r.slippage_ticks * self.r.tick_size


class TopstepBroker:
    """Real orders on a simulated Topstep account."""

    live = True

    def __init__(self, client: TopstepXClient, account_id: int, feed: TopstepFeed,
                 risk: RiskParams, log: Log, sleep: Callable[[float], None] = time.sleep):
        self.c, self.acct, self.feed, self.r, self.log = client, account_id, feed, risk, log
        self.sleep = sleep
        self.stop_order: Optional[int] = None
        self.opened_at: Optional[datetime] = None

    @property
    def contract(self) -> str:
        return self.feed.contract_id

    def _short_size(self) -> Tuple[int, float]:
        """(contracts short, average price); a long position is reported as negative."""
        for p in self.c.open_positions(self.acct):
            if p.get("contractId") == self.contract:
                size = int(p.get("size", 0))
                sign = 1 if p.get("type") == PositionType.SHORT else -1
                return sign * size, float(p.get("averagePrice") or 0.0)
        return 0, 0.0

    def _cancel_all(self) -> None:
        for o in self.c.open_orders(self.acct):
            if o.get("contractId") == self.contract:
                try:
                    self.c.cancel_order(self.acct, o["id"])
                except ApiError as e:
                    self.log(f"cancel {o['id']} failed: {e}")

    def _wait_flat(self, tries: int = 20) -> bool:
        for _ in range(tries):
            if self._short_size()[0] == 0:
                return True
            self.sleep(0.5)
        return False

    def _last_buy_fill(self) -> Optional[float]:
        start = self.opened_at or datetime.now(timezone.utc) - timedelta(hours=8)
        fills = [t for t in self.c.trades(self.acct, start)
                 if t.get("contractId") == self.contract and t.get("side") == Side.BUY
                 and not t.get("voided")]
        return float(fills[-1]["price"]) if fills else None

    def reconcile(self) -> None:
        """Start from a clean slate: cancel MNQ orders and close any MNQ position."""
        self._cancel_all()
        size, _ = self._short_size()
        if size != 0:
            self.log(f"found an existing position of {size} (short>0); closing it")
            self.c.close_position(self.acct, self.contract)
            if not self._wait_flat():
                raise RuntimeError("could not flatten the existing position; check TopstepX")
        self.stop_order = None

    def open_short(self, n: int, stop_pts: float, ref_price: float) -> Tuple[float, float]:
        self.opened_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        tag = f"shortbot-{int(time.time() * 1000)}"
        order = self.c.place_order(self.acct, self.contract, OrderType.MARKET, Side.SELL, n,
                                   tag=tag)
        size, avg = 0, 0.0
        for _ in range(20):
            size, avg = self._short_size()
            if size >= n:
                break
            self.sleep(0.5)
        if size < n:
            self.log(f"entry order {order} not filled after 10 s; cancelling")
            try:
                self.c.cancel_order(self.acct, order)
            except ApiError:
                pass
            if size:
                self.c.close_position(self.acct, self.contract)
            raise RuntimeError("entry not filled")
        stop = _ceil_tick(avg + stop_pts, self.r.tick_size)
        try:
            self.stop_order = self.c.place_order(self.acct, self.contract, OrderType.STOP,
                                                 Side.BUY, size, stop_price=stop, tag=tag + "-SL")
        except ApiError as e:
            self.log(f"could not place the protective stop ({e}); closing the position")
            self.c.close_position(self.acct, self.contract)
            self._wait_flat()
            raise
        return avg, stop

    def stopped_out(self, high: float) -> Optional[float]:
        if self._short_size()[0] != 0:
            return None
        # position is gone: the stop filled (or someone closed it by hand)
        self._cancel_all()
        self.stop_order = None
        return self._last_buy_fill()

    def close(self, ref_price: float) -> float:
        if self.stop_order is not None:
            try:
                self.c.cancel_order(self.acct, self.stop_order)
            except ApiError as e:
                self.log(f"cancelling the stop failed ({e}); closing anyway")
        self.c.close_position(self.acct, self.contract)
        flat = self._wait_flat()
        self._cancel_all()
        self.stop_order = None
        if not flat:
            raise RuntimeError("position did not close; flatten it in TopstepX NOW")
        return self._last_buy_fill() or ref_price


# ------------------------------------------------------------------------ bot

class LiveBot:
    """Calls the shared strategy on live bars and manages at most one short."""

    def __init__(self, cfg: BotConfig, feed, broker, log: Log, kill_file: str = "STOP",
                 trade_log: str = "runs/shortbot-trades.csv"):
        self.cfg, self.feed, self.broker, self.log = cfg, feed, broker, log
        self.strat = ShortStrategy(cfg.strategy)
        self.r = cfg.risk
        self.kill_file, self.trade_log = kill_file, trade_log
        self.date: Optional[str] = None
        self.day = DayState()
        self.prof = None
        self.allowed = False
        self.pos: Optional[Dict] = None
        self.last_bar_end: Optional[int] = None

    # -------------------------------------------------------------- lifecycle

    def _new_day(self, now: datetime, date: str) -> None:
        self.date, self.day, self.pos, self.last_bar_end = date, DayState(), None, None
        if hasattr(self.feed, "new_day"):
            self.feed.new_day()
        prior = self.feed.history(now, self.strat.warmup_days() + 3)
        need = self.cfg.strategy.profile_days
        if len(prior) < self.strat.warmup_days():
            self.allowed = False
            self.log(f"{date}: only {len(prior)} earlier sessions available, need "
                     f"{self.strat.warmup_days()}; not trading today")
            return
        self.prof = self.strat.profile(prior[-need:])
        self.allowed = self.strat.day_allowed(prior)
        mode = "LIVE ORDERS" if self.broker.live else "dry run"
        self.log(f"{date}: new session ({mode}); {len(prior)} earlier sessions loaded; "
                 f"trading {'allowed' if self.allowed else 'skipped by the trend filter'}")

    def shutdown(self, why: str) -> None:
        now_min = _minute(datetime.now(timezone.utc).astimezone(NY))
        if self.pos is not None:
            px = self.feed.last_price(datetime.now(timezone.utc))
            self._close(px[0] if px else self.pos["entry"], now_min, why)
        if self.broker.live:
            self.broker.reconcile()
        self.log(f"stopped: {why}")

    # ------------------------------------------------------------------- step

    def step(self, now: datetime) -> bool:
        """One pass: manage the open short, then act on a newly closed bar.
        Returns False when the bot should stop."""
        ny = now.astimezone(NY)
        minute, date = _minute(ny), ny.strftime("%Y-%m-%d")
        if os.path.exists(self.kill_file):
            self.shutdown(f"kill switch file '{self.kill_file}' found")
            return False
        if ny.weekday() >= 5 or not (RTH_OPEN - 5 <= minute <= RTH_CLOSE + 5):
            return True
        if date != self.date:
            self._new_day(now, date)

        if self.pos is not None:
            self._manage(now, minute)

        bar_minutes = getattr(self.feed, "bar_minutes", 5)
        if self.last_bar_end is not None and minute < self.last_bar_end + bar_minutes:
            return True                               # the next bar has not closed yet
        s = self.feed.today(now)
        if s is None or len(s) == 0:
            return True
        i = len(s) - 1
        bar_end = int(s.minute[i]) + s.bar_minutes
        if bar_end == self.last_bar_end:
            return True
        self.last_bar_end = bar_end
        if minute - bar_end > 1:                      # stale bar (e.g. just restarted): never act late
            return True
        if self.pos is not None or not self.allowed or self.prof is None:
            return True
        e = self.strat.decide(s, i, self.day, self.prof)
        if e is None:
            return True
        n = min(size_trade(e, self.r), self.cfg.account.max_contracts)
        if n == 0:
            self.log(f"skip {e.setup}: a 1-lot stop of {e.stop_pts:.0f} pts is wider than "
                     f"${self.r.max_stop_risk_usd:.0f}")
            return True
        px = self.feed.last_price(now)
        ref = px[0] if px else float(s.close[i])
        try:
            entry, stop = self.broker.open_short(n, e.stop_pts, ref)
        except Exception as exc:                     # noqa: BLE001 -- log and keep running flat
            self.log(f"entry failed: {exc}")
            return True
        self.pos = {"entry": entry, "stop": stop, "target": entry - e.target_pts, "n": n,
                    "minute": minute, "setup": e.setup, "reason": e.reason}
        self.day.in_position = True
        self.day.setups_used[e.setup] = self.day.setups_used.get(e.setup, 0) + 1
        self.log(f"SHORT {n} MNQ @ {entry:.2f} [{e.setup}] stop {stop:.2f} "
                 f"target {self.pos['target']:.2f} -- {e.reason}")
        return True

    def _manage(self, now: datetime, minute: int) -> None:
        pos = self.pos
        px = self.feed.last_price(now)
        if px is None:
            return
        last, high = px
        filled = self.broker.stopped_out(high)
        if filled is not None:
            self._record(filled, minute, "stop")
        elif minute >= self.strat.flatten_minute(self.date or ""):
            self._close(last, minute, "flatten")
        elif last <= pos["target"] - self.r.tick_size:
            self._close(last, minute, "target")
        elif minute - pos["minute"] >= self.cfg.strategy.max_hold_minutes:
            self._close(last, minute, "time")

    def _close(self, ref: float, minute: int, why: str) -> None:
        self._record(self.broker.close(ref), minute, why)

    def _record(self, exit_px: Optional[float], minute: int, why: str) -> None:
        pos = self.pos
        exit_px = exit_px if exit_px is not None else pos["stop"]
        pnl = (pos["entry"] - exit_px) * self.r.point_value * pos["n"] - self.r.commission_rt * pos["n"]
        self.day.record_exit(pnl, minute)
        if self.day.pnl_usd <= -self.r.daily_loss_stop_usd or \
                self.day.pnl_usd >= self.r.daily_profit_stop_usd:
            self.day.done = True
        self.log(f"COVER {pos['n']} MNQ @ {exit_px:.2f} ({why})  trade ${pnl:+.2f}  "
                 f"day ${self.day.pnl_usd:+.2f}{'  -- done for today' if self.day.done else ''}")
        self._append_trade([self.date, pos["setup"], pos["minute"], minute, pos["entry"], exit_px,
                            pos["n"], round(pnl, 2), why, "live" if self.broker.live else "paper"])
        self.pos = None

    def _append_trade(self, row: List) -> None:
        d = os.path.dirname(self.trade_log)
        if d:
            os.makedirs(d, exist_ok=True)
        new = not os.path.exists(self.trade_log)
        with open(self.trade_log, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "setup", "entry_minute", "exit_minute", "entry", "exit",
                            "contracts", "pnl_usd", "exit_reason", "mode"])
            w.writerow(row)


# ------------------------------------------------------------------ entry point

def _logger(path: str) -> Log:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

    def log(msg: str) -> None:
        line = f"{datetime.now(NY).strftime('%Y-%m-%d %H:%M:%S')} ET  {msg}"
        print(line, flush=True)
        with open(path, "a") as f:
            f.write(line + "\n")
    return log


def account_risk_problem(cfg: BotConfig) -> Optional[str]:
    """Why these settings could lose the whole account on one trade, or None.
    Checked before placing real orders."""
    r, a = cfg.risk, cfg.account
    # size_trade fills the budget, but always takes at least one contract whose
    # stop can be as wide as max_stop_risk_usd
    worst = min(max(r.risk_per_trade_usd, r.max_stop_risk_usd),
                r.max_stop_risk_usd * r.max_contracts)
    if worst >= a.max_loss:
        return (f"one losing trade can risk up to ${worst:,.0f}, but {a.name} fails at "
                f"-${a.max_loss:,.0f}: a single stop-out would end the account. Lower "
                f"risk.risk_per_trade_usd (or risk.max_contracts), or pass --allow-account-risk.")
    return None


def run_live(cfg: BotConfig, live: bool = False, account_id: Optional[int] = None,
             log_path: str = "runs/shortbot-live.log", poll_seconds: float = 5.0,
             allow_account_risk: bool = False) -> None:
    problem = account_risk_problem(cfg)
    if live and problem and not allow_account_risk:
        raise SystemExit("refusing: " + problem)
    user, key = os.environ.get("TOPSTEPX_USERNAME"), os.environ.get("TOPSTEPX_API_KEY")
    if not user or not key:
        raise SystemExit(
            "Set TOPSTEPX_USERNAME (your TopstepX username, not your email) and TOPSTEPX_API_KEY.\n"
            "API access: subscribe at dashboard.projectx.com ($14.50/mo with code 'topstep'),\n"
            "link it in TopstepX > Settings > API, then create a key there.")
    log = _logger(log_path)
    client = TopstepXClient(user, key)
    client.login()
    accounts = client.accounts()
    for a in accounts:
        log(f"account {a['id']}: {a['name']}  balance ${a.get('balance', 0):,.2f}  "
            f"canTrade={a.get('canTrade')}  simulated={a.get('simulated')}")
    feed = TopstepFeed(client, cfg.symbol)
    log(f"contract: {feed.contract_id}")

    if live:
        acct = next((a for a in accounts if a["id"] == account_id), None)
        if acct is None:
            raise SystemExit("--live needs --account-id set to one of the accounts listed above")
        if not acct.get("canTrade"):
            raise SystemExit(f"account {account_id} cannot trade right now")
        if acct.get("simulated") is False:
            raise SystemExit("refusing: this is not a simulated account, and Topstep does not "
                             "allow the API on Live Funded accounts")
        broker = TopstepBroker(client, account_id, feed, cfg.risk, log)
        broker.reconcile()
        log(f"LIVE ORDERS on account {account_id} ({acct['name']}). Create a file named STOP "
            f"to flatten and exit.")
    else:
        broker = PaperBroker(cfg.risk, log)
        log("dry run: real prices, simulated fills, no orders sent")

    bot = LiveBot(cfg, feed, broker, log)
    errors = 0
    try:
        while True:
            try:
                if not bot.step(datetime.now(timezone.utc)):
                    return
                errors = 0
            except Exception as exc:                  # noqa: BLE001 -- keep the loop alive
                errors += 1
                log(f"error ({errors} in a row): {exc}")
                if errors >= 5 and bot.pos is not None:
                    log("too many errors while in a position; flattening")
                    bot.shutdown("repeated errors")
                    return
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        bot.shutdown("Ctrl-C")
