"""A small TopstepX (ProjectX Gateway) REST client -- standard library only.

Reference: https://gateway.docs.projectx.com/ and the live Swagger spec at
https://api.topstepx.com/swagger/v1/swagger.json.  Every call is a POST with a
JSON body; business failures come back as HTTP 200 with ``success: false``,
which this client turns into ``ApiError``.

Topstep rules that apply to anything built on this:

* the API works on Practice, Trading Combine and Express Funded accounts
  (all simulated) and is NOT allowed on a Live Funded account;
* order flow must come from your own computer: VPS, VPN and remote servers
  are prohibited;
* high-frequency trading and exploiting simulated fills are prohibited.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

BASE_URL = "https://api.topstepx.com"


class OrderType:
    LIMIT = 1
    MARKET = 2
    STOP = 4
    TRAILING_STOP = 5


class Side:
    BUY = 0     # "Bid"
    SELL = 1    # "Ask"


class OrderStatus:
    OPEN = 1
    FILLED = 2
    CANCELLED = 3
    EXPIRED = 4
    REJECTED = 5
    PENDING = 6
    PENDING_CANCEL = 7
    SUSPENDED = 8


class PositionType:
    LONG = 1
    SHORT = 2


class BarUnit:
    SECOND = 1
    MINUTE = 2
    HOUR = 3
    DAY = 4


class ApiError(RuntimeError):
    def __init__(self, path: str, code: Any, message: Any):
        super().__init__(f"{path} failed: errorCode={code} {message or ''}".strip())
        self.path, self.code, self.message = path, code, message


class _Limiter:
    """Client-side throttle so the bot stays inside the documented limits:
    retrieveBars 50 per 30 s, everything else 200 per 60 s."""

    def __init__(self, calls: int, per_seconds: float):
        self.calls, self.per = calls, per_seconds
        self.stamps: Deque[float] = deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self.stamps and now - self.stamps[0] > self.per:
            self.stamps.popleft()
        if len(self.stamps) >= self.calls:
            time.sleep(self.per - (now - self.stamps[0]) + 0.05)
        self.stamps.append(time.monotonic())


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


class TopstepXClient:
    TOKEN_REFRESH_SECONDS = 20 * 3600       # tokens last 24 h

    def __init__(self, username: str, api_key: str, base_url: str = BASE_URL,
                 timeout: float = 15.0, transport=None):
        self.username, self.api_key = username, api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: Optional[str] = None
        self.token_time = 0.0
        self._history = _Limiter(50, 30.0)
        self._other = _Limiter(200, 60.0)
        # transport(url, body_bytes, headers) -> (status, body_bytes); swappable for tests
        self._transport = transport or self._urllib

    # ---------------------------------------------------------------- plumbing

    def _urllib(self, url: str, data: bytes, headers: Dict[str, str]) -> Tuple[int, bytes]:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read() or b""

    def _post(self, path: str, body: Dict[str, Any], auth: bool = True, _retry: int = 0) -> Dict:
        (self._history if path == "/api/History/retrieveBars" else self._other).wait()
        if auth:
            self._ensure_token()
        headers = {"Content-Type": "application/json", "accept": "application/json, text/plain"}
        if auth:
            headers["Authorization"] = f"Bearer {self.token}"
        status, raw = self._transport(self.base_url + path, json.dumps(body).encode(), headers)
        if status == 401 and auth and _retry == 0:
            self.token = None                       # expired: log in again once
            return self._post(path, body, auth, _retry + 1)
        if status == 429 and _retry < 3:
            time.sleep(2.0 * (_retry + 1))
            return self._post(path, body, auth, _retry + 1)
        if status != 200:
            raise ApiError(path, f"HTTP {status}", raw[:200].decode(errors="replace"))
        out = json.loads(raw.decode() or "{}")
        if not out.get("success", False):
            raise ApiError(path, out.get("errorCode"), out.get("errorMessage"))
        return out

    def _ensure_token(self) -> None:
        if self.token is None:
            self.login()
        elif time.time() - self.token_time > self.TOKEN_REFRESH_SECONDS:
            try:
                out = self._validate()
                self.token = out.get("newToken") or self.token
                self.token_time = time.time()
            except ApiError:
                self.login()

    def _validate(self) -> Dict:
        headers = {"Content-Type": "application/json", "accept": "application/json, text/plain",
                   "Authorization": f"Bearer {self.token}"}
        status, raw = self._transport(self.base_url + "/api/Auth/validate", b"{}", headers)
        out = json.loads(raw.decode() or "{}") if status == 200 else {}
        if not out.get("success"):
            raise ApiError("/api/Auth/validate", out.get("errorCode", f"HTTP {status}"),
                           out.get("errorMessage"))
        return out

    # -------------------------------------------------------------- endpoints

    def login(self) -> None:
        out = self._post("/api/Auth/loginKey",
                         {"userName": self.username, "apiKey": self.api_key}, auth=False)
        if not out.get("token"):
            raise ApiError("/api/Auth/loginKey", out.get("errorCode"), "no token returned")
        self.token, self.token_time = out["token"], time.time()

    def accounts(self, only_active: bool = True) -> List[Dict]:
        return self._post("/api/Account/search", {"onlyActiveAccounts": only_active})["accounts"]

    def front_month(self, symbol: str = "MNQ") -> Dict:
        """The active contract for a root symbol, e.g. CON.F.US.MNQ.Z26."""
        found = self._post("/api/Contract/search", {"searchText": symbol, "live": False})["contracts"]
        active = [c for c in found
                  if c.get("symbolId") == f"F.US.{symbol}" and c.get("activeContract")]
        if not active:
            raise ApiError("/api/Contract/search", "none", f"no active {symbol} contract in {found}")
        return active[0]

    def bars(self, contract_id: str, start: datetime, end: datetime, unit: int = BarUnit.MINUTE,
             unit_number: int = 5, limit: int = 20_000, include_partial: bool = False
             ) -> List[Tuple[int, float, float, float, float, float]]:
        """(epoch, o, h, l, c, v) rows oldest first."""
        out = self._post("/api/History/retrieveBars", {
            "contractId": contract_id, "live": False, "startTime": _iso(start),
            "endTime": _iso(end), "unit": unit, "unitNumber": unit_number, "limit": limit,
            "includePartialBar": include_partial})
        rows = [(_epoch(b["t"]), float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]),
                 float(b.get("v") or 0)) for b in out.get("bars") or []]
        return sorted(rows)

    def place_order(self, account_id: int, contract_id: str, order_type: int, side: int,
                    size: int, limit_price: Optional[float] = None,
                    stop_price: Optional[float] = None, tag: Optional[str] = None) -> int:
        out = self._post("/api/Order/place", {
            "accountId": account_id, "contractId": contract_id, "type": order_type,
            "side": side, "size": int(size), "limitPrice": limit_price,
            "stopPrice": stop_price, "trailPrice": None, "customTag": tag})
        return int(out["orderId"])

    def cancel_order(self, account_id: int, order_id: int) -> None:
        self._post("/api/Order/cancel", {"accountId": account_id, "orderId": int(order_id)})

    def open_orders(self, account_id: int) -> List[Dict]:
        return self._post("/api/Order/searchOpen", {"accountId": account_id})["orders"]

    def open_positions(self, account_id: int) -> List[Dict]:
        return self._post("/api/Position/searchOpen", {"accountId": account_id})["positions"]

    def close_position(self, account_id: int, contract_id: str) -> None:
        self._post("/api/Position/closeContract", {"accountId": account_id,
                                                    "contractId": contract_id})

    def trades(self, account_id: int, start: datetime, end: Optional[datetime] = None) -> List[Dict]:
        body: Dict[str, Any] = {"accountId": account_id, "startTimestamp": _iso(start)}
        if end is not None:
            body["endTimestamp"] = _iso(end)
        return self._post("/api/Trade/search", body)["trades"]
