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
2. Entry is a market order (a sell for a short, a buy for a long).  As soon
   as the position shows up, a protective stop is placed on the other side.  If the stop cannot be placed, the position is
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
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple

from .backtest import size_trade, stop_price, target_price
from .config import BotConfig, RiskParams
from .data import NY, RTH_CLOSE, RTH_OPEN, Session, full_day_bars, to_sessions
from .strategy import DayState, ShortStrategy
from .topstepx import ApiError, BarUnit, OrderType, PositionType, Side, TopstepXClient

Log = Callable[[str], None]


def _minute(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


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

    def last_price(self, now: datetime, since: Optional[float] = None
                   ) -> Optional[Tuple[float, float, float]]:
        """(last price, high, low) from the last two 1-minute bars.  With
        ``since`` (epoch seconds) the high and low only use bars that began at
        or after it, so prices from before an entry never count."""
        rows = self.client.bars(self.contract_id, now - timedelta(minutes=3), now,
                                BarUnit.MINUTE, 1, include_partial=True)
        if not rows:
            return None
        last = rows[-1][4]
        recent = [r for r in rows[-2:] if since is None or r[0] >= since]
        if not recent:
            return last, last, last
        return last, max(r[2] for r in recent), min(r[3] for r in recent)


# ---------------------------------------------------------------------- brokers

class PaperBroker:
    """Dry run: fills at the latest price, one tick worse; nothing is sent anywhere."""

    live = False

    def __init__(self, risk: RiskParams, log: Log):
        self.r, self.log = risk, log
        self.side, self.n, self.stop = 0, 0, 0.0

    def reconcile(self) -> None:
        pass

    def ensure_flat(self) -> bool:
        return True

    def open(self, side: int, n: int, stop_pts: float, ref_price: float) -> Tuple[float, float]:
        slip = self.r.slippage_ticks * self.r.tick_size
        entry = ref_price + side * slip
        self.side, self.n = side, n
        self.stop = stop_price(entry, side, stop_pts, self.r.tick_size)
        return entry, self.stop

    def check_flat(self, high: float, low: float) -> Tuple[bool, Optional[float]]:
        """(position gone?, exit price if known)."""
        if self.n and self.side * ((low if self.side > 0 else high) - self.stop) <= 0:
            self.n = 0
            return True, self.stop - self.side * self.r.slippage_ticks * self.r.tick_size
        return self.n == 0, None

    def close(self, ref_price: float) -> float:
        self.n = 0
        return ref_price - self.side * self.r.slippage_ticks * self.r.tick_size


class TopstepBroker:
    """Real orders on a simulated Topstep account."""

    live = True

    def __init__(self, client: TopstepXClient, account_id: int, feed: TopstepFeed,
                 risk: RiskParams, log: Log, sleep: Callable[[float], None] = time.sleep):
        self.c, self.acct, self.feed, self.r, self.log = client, account_id, feed, risk, log
        self.sleep = sleep
        self.root = f"CON.F.US.{getattr(feed, 'symbol', 'MNQ')}."
        self.side, self.n, self.stop = 0, 0, 0.0
        self.stop_order: Optional[int] = None
        self.opened_at: Optional[datetime] = None

    @property
    def contract(self) -> str:
        return self.feed.contract_id

    def _ours(self, contract_id) -> bool:
        return contract_id == self.contract or str(contract_id).startswith(self.root)

    def _positions(self) -> List[Dict]:
        return [p for p in self.c.open_positions(self.acct)
                if self._ours(p.get("contractId")) and int(p.get("size", 0))]

    def _orders(self) -> List[Dict]:
        return [o for o in self.c.open_orders(self.acct) if self._ours(o.get("contractId"))]

    def _position(self) -> Tuple[int, float]:
        """(signed contracts in the current contract: + long, - short; average price)."""
        for p in self._positions():
            if p.get("contractId") == self.contract:
                sign = -1 if p.get("type") == PositionType.SHORT else 1
                return sign * int(p["size"]), float(p.get("averagePrice") or 0.0)
        return 0, 0.0

    def _cancel_orders(self, tries: int = 3) -> None:
        """Cancel every MNQ order and make sure none is left resting."""
        for _ in range(tries):
            left = self._orders()
            if not left:
                return
            for o in left:
                try:
                    self.c.cancel_order(self.acct, o["id"])
                except ApiError as e:
                    self.log(f"cancel {o['id']} failed: {e}")
            self.sleep(0.5)
        left = self._orders()
        if left:
            raise RuntimeError(f"orders {[o['id'] for o in left]} are still resting after "
                               f"cancelling; cancel them in TopstepX NOW")

    def _wait_flat(self, tries: int = 20) -> bool:
        for _ in range(tries):
            if not self._positions():
                return True
            self.sleep(0.5)
        return False

    def _last_exit_fill(self) -> Optional[float]:
        """Price of the latest fill on the side that closes the position."""
        closing = Side.SELL if self.side > 0 else Side.BUY
        start = self.opened_at or datetime.now(timezone.utc) - timedelta(hours=8)
        fills = [t for t in self.c.trades(self.acct, start)
                 if t.get("contractId") == self.contract and t.get("side") == closing
                 and not t.get("voided")]
        return float(fills[-1]["price"]) if fills else None

    def flatten_everything(self, why: str) -> None:
        """Cancel every MNQ order and close every MNQ position; raise if the
        account cannot be confirmed flat."""
        self.log(f"flattening all MNQ orders and positions: {why}")
        try:
            self._cancel_orders()
        except (ApiError, RuntimeError) as e:
            self.log(f"cancelling failed: {e}")
        for p in self._positions():
            try:
                self.c.close_position(self.acct, p["contractId"])
            except ApiError as e:
                self.log(f"closing {p['contractId']} failed: {e}")
        if not self._wait_flat():
            raise RuntimeError("COULD NOT FLATTEN the account; close it in TopstepX NOW")
        self._cancel_orders()
        self.stop_order, self.n = None, 0

    def reconcile(self) -> None:
        """Start (or end) from a clean slate."""
        if self._positions() or self._orders():
            self.flatten_everything("found MNQ orders or positions left over")
        self.stop_order, self.n = None, 0

    def ensure_flat(self) -> bool:
        """While the bot has no trade: True if the account really is flat.
        Anything found is flattened."""
        if self._positions() or self._orders():
            self.flatten_everything("the account was not flat although the bot had no trade")
            return False
        return True

    def open(self, side: int, n: int, stop_pts: float, ref_price: float) -> Tuple[float, float]:
        self.side = side
        self.opened_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        tag = f"shortbot-{int(time.time() * 1000)}"
        try:
            order = self.c.place_order(self.acct, self.contract, OrderType.MARKET,
                                       Side.BUY if side > 0 else Side.SELL, n, tag=tag)
            size, avg = 0, 0.0
            for _ in range(20):
                size, avg = self._position()
                if side * size >= n:
                    break
                self.sleep(0.5)
            if side * size < n:
                raise RuntimeError(f"entry order {order} not filled after 10 s")
            if abs(size) != n:
                raise RuntimeError(f"ordered {n} contracts but the account shows {size}")
            stop = stop_price(avg, side, stop_pts, self.r.tick_size)
            self.stop_order = self.c.place_order(self.acct, self.contract, OrderType.STOP,
                                                 Side.SELL if side > 0 else Side.BUY, n,
                                                 stop_price=stop, tag=tag + "-SL")
            self.n, self.stop = n, stop
            return avg, stop
        except BaseException as exc:
            self.log(f"entry did not complete ({exc!r})")
            try:
                self.flatten_everything("entry did not complete")
            except Exception as e2:                      # noqa: BLE001 -- report both
                self.log(f"{e2}")
            raise

    def check_flat(self, high: float, low: float) -> Tuple[bool, Optional[float]]:
        """(position gone?, exit price if known).  One empty read is not
        trusted: the position must be gone on two reads a second apart."""
        if self._position()[0] != 0:
            return False, None
        self.sleep(1.0)
        if self._position()[0] != 0:
            return False, None
        self._cancel_orders()                             # the stop filled; tidy up
        self.stop_order, self.n = None, 0
        return True, self._last_exit_fill()

    def close(self, ref_price: float) -> float:
        if self.stop_order is not None:
            try:
                self.c.cancel_order(self.acct, self.stop_order)
            except ApiError as e:
                self.log(f"cancelling the stop failed ({e}); closing anyway")
        try:
            self.c.close_position(self.acct, self.contract)
        except ApiError as e:
            self.log(f"close request failed ({e}); checking the account")
        if not self._wait_flat():
            size, _ = self._position()
            if size:
                try:
                    self.stop_order = self.c.place_order(
                        self.acct, self.contract, OrderType.STOP,
                        Side.BUY if size < 0 else Side.SELL, abs(size), stop_price=self.stop,
                        tag=f"shortbot-{int(time.time() * 1000)}-SL")
                    self.log("the close did not go through; the protective stop is back in place")
                except ApiError as e:
                    self.log(f"COULD NOT PUT THE STOP BACK ({e}); close the position in TopstepX NOW")
            raise RuntimeError("position did not close")
        self._cancel_orders()
        self.stop_order, self.n = None, 0
        return self._last_exit_fill() or ref_price


# ------------------------------------------------------------------------ bot

class LiveBot:
    """Calls the shared strategy on live bars and manages at most one position."""

    def __init__(self, cfg: BotConfig, feed, broker, log: Log, kill_file: str = "STOP",
                 trade_log: str = "runs/shortbot-trades.csv",
                 sleep: Callable[[float], None] = time.sleep):
        self.cfg, self.feed, self.broker, self.log = cfg, feed, broker, log
        self.strat = ShortStrategy(cfg.strategy)
        self.r = cfg.risk
        self.kill_file, self.trade_log, self.sleep = kill_file, trade_log, sleep
        self.date: Optional[str] = None
        self.day = DayState()
        self.prof = None
        self.allowed = False
        self.pos: Optional[Dict] = None
        self.last_bar_end: Optional[int] = None
        self.last_px: Optional[float] = None
        self._load_failures = 0

    # -------------------------------------------------------------- lifecycle

    def _new_day(self, now: datetime, date: str) -> None:
        """Load history for a new session.  ``self.date`` only changes once
        the loading worked, so a failure is retried on the next pass."""
        if hasattr(self.feed, "new_day"):
            self.feed.new_day()
        prior = self.feed.history(now, self.strat.warmup_days() + 3)
        self.date, self.day, self.last_bar_end = date, DayState(), None
        need = self.cfg.strategy.profile_days
        if len(prior) < self.strat.warmup_days():
            self.allowed, self.prof = False, None
            self.log(f"{date}: only {len(prior)} earlier sessions available, need "
                     f"{self.strat.warmup_days()}; not trading today")
            return
        self.prof = self.strat.profile(prior[-need:])
        self.allowed = self.strat.day_allowed(prior)
        mode = "LIVE ORDERS" if self.broker.live else "dry run"
        self.log(f"{date}: new session ({mode}); {len(prior)} earlier sessions loaded; "
                 f"trading {'allowed' if self.allowed else 'skipped by the trend filter'}")

    def shutdown(self, why: str) -> None:
        """Close any position and clean the account, retrying; never raises."""
        for attempt in range(1, 4):
            try:
                now = datetime.now(timezone.utc)
                if self.pos is not None:
                    self._close(self._ref_price(now) or self.pos["entry"],
                                _minute(now.astimezone(NY)), why)
                if self.broker.live:
                    self.broker.reconcile()
                self.log(f"stopped: {why}")
                return
            except Exception as exc:                      # noqa: BLE001 -- retry, then shout
                self.log(f"shutdown attempt {attempt} failed: {exc}")
                self.sleep(2.0)
        self.log("COULD NOT CONFIRM THE ACCOUNT IS FLAT. CHECK TOPSTEPX NOW.")

    # ------------------------------------------------------------------- step

    def step(self, now: datetime) -> bool:
        """One pass: manage the open trade, then act on a newly closed bar.
        Returns False when the bot should stop."""
        ny = now.astimezone(NY)
        minute, date = _minute(ny), ny.strftime("%Y-%m-%d")
        if os.path.exists(self.kill_file):
            self.shutdown(f"kill switch file '{self.kill_file}' found")
            return False

        if self.pos is not None:                     # at any hour: a trade is never forgotten
            if date != self.date:
                self._close(self._ref_price(now) or self.pos["entry"], minute,
                            "left over from an earlier day")
            else:
                self._manage(now, minute)

        if ny.weekday() >= 5 or not (RTH_OPEN - 5 <= minute <= RTH_CLOSE + 5):
            return True
        if date != self.date:
            try:
                self._new_day(now, date)
                self._load_failures = 0
            except Exception as exc:                  # noqa: BLE001 -- retried next pass
                self._load_failures += 1
                if self._load_failures == 1 or self._load_failures % 60 == 0:
                    self.log(f"could not load history for {date} ({exc}); retrying")
                return True

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
        closed_at = ny.replace(hour=bar_end // 60, minute=bar_end % 60, second=0, microsecond=0)
        if (ny - closed_at).total_seconds() > 60:     # stale bar (e.g. just restarted): never act late
            return True
        if self.pos is not None or not self.allowed or self.prof is None or self.day.done:
            return True
        e = self.strat.decide(s, i, self.day, self.prof)
        if e is None:
            return True
        if not self.broker.ensure_flat():
            self.log("the account was not flat; flattened it and stopping for today")
            self.day.done = True
            return True
        n = min(size_trade(e, self.r), self.cfg.account.max_contracts)
        if n == 0:
            self.log(f"skip {e.setup}: a 1-lot stop of {e.stop_pts:.0f} pts is wider than "
                     f"${self.r.max_stop_risk_usd:.0f}")
            return True
        ref = self._ref_price(now) or float(s.close[i])
        try:
            entry, stop = self.broker.open(e.side, n, e.stop_pts, ref)
        except Exception as exc:                     # noqa: BLE001 -- the broker flattened
            self.log(f"entry failed ({exc}); the account was flattened; no more entries today")
            self.day.done = True
            return True
        self.pos = {"side": e.side, "entry": entry, "stop": stop,
                    "target": target_price(entry, e.side, e.target_pts, self.r.tick_size),
                    "n": n, "minute": minute, "deadline": self.strat.deadline(date, minute),
                    "opened_ts": now.timestamp(), "setup": e.setup, "reason": e.reason}
        self.day.in_position = True
        self.day.setups_used[e.setup] = self.day.setups_used.get(e.setup, 0) + 1
        self.log(f"{'LONG' if e.side > 0 else 'SHORT'} {n} MNQ @ {entry:.2f} [{e.setup}] "
                 f"stop {stop:.2f} target {self.pos['target']:.2f} -- {e.reason}")
        return True

    def _ref_price(self, now: datetime) -> Optional[float]:
        try:
            px = self.feed.last_price(now)
        except Exception:                             # noqa: BLE001 -- fall back to the last one
            px = None
        if px:
            self.last_px = px[0]
        return self.last_px

    def _bar_end(self, minute: int) -> int:
        """End of the bar a minute falls in -- how the backtest times exits."""
        b = getattr(self.feed, "bar_minutes", 5)
        return (minute // b + 1) * b

    def _manage(self, now: datetime, minute: int) -> None:
        pos = self.pos
        try:
            px = self.feed.last_price(now, since=pos["opened_ts"])
        except Exception as exc:                      # noqa: BLE001 -- exits below still run
            self.log(f"no price ({exc})")
            px = None
        if px:
            self.last_px = px[0]
        last = px[0] if px else (self.last_px if self.last_px is not None else pos["entry"])
        high, low = (px[1], px[2]) if px else (last, last)
        gone, fill = self.broker.check_flat(high, low)
        if gone:
            self._record(fill if fill is not None else pos["stop"], self._bar_end(minute), "stop")
        elif minute >= pos["deadline"]:
            self._close(last, minute, "flatten")
        elif px and pos["side"] * (last - pos["target"]) >= self.r.tick_size:
            self._close(last, self._bar_end(minute), "target")
        elif minute - pos["minute"] >= self.cfg.strategy.max_hold_minutes:
            self._close(last, self._bar_end(minute), "time")

    def _close(self, ref: float, minute: int, why: str) -> None:
        self._record(self.broker.close(ref), minute, why)

    def _record(self, exit_px: float, minute: int, why: str) -> None:
        pos = self.pos
        pnl = (pos["side"] * (exit_px - pos["entry"]) * self.r.point_value * pos["n"]
               - self.r.commission_rt * pos["n"])
        self.day.record_exit(pnl, minute)
        if self.day.pnl_usd <= -self.r.daily_loss_stop_usd or \
                self.day.pnl_usd >= self.r.daily_profit_stop_usd:
            self.day.done = True
        self.log(f"{'SELL' if pos['side'] > 0 else 'COVER'} {pos['n']} MNQ @ {exit_px:.2f} ({why})"
                 f"  trade ${pnl:+.2f}  "
                 f"day ${self.day.pnl_usd:+.2f}{'  -- done for today' if self.day.done else ''}")
        self._append_trade([self.date, pos["setup"], "long" if pos["side"] > 0 else "short",
                            pos["minute"], minute, pos["entry"], exit_px, pos["n"], round(pnl, 2),
                            why, "live" if self.broker.live else "paper"])
        self.pos = None

    def _append_trade(self, row: List) -> None:
        d = os.path.dirname(self.trade_log)
        if d:
            os.makedirs(d, exist_ok=True)
        new = not os.path.exists(self.trade_log)
        with open(self.trade_log, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "setup", "side", "entry_minute", "exit_minute", "entry", "exit",
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
        if acct.get("simulated") is not True:
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
