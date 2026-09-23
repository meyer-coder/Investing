# Three-bot split account

Picked 2026-09-23. Backtests on daily bars, not advice.

Three bots share one $25,000 account, a third each (about $8,333). Each keeps its own rules and trades only its third, so the account's day is the sum of the three. None trades TSMX. The bots were picked together because their good months cover each other's quiet ones.

## The bots

- **MUU Quick Dip: 2% dip above the 200-day, 2% target, 10% stop, 4 days max.** Buy when `ret1 < -0.02 and close > sma200`; sell when `bars_held >= 4`; stop loss 10%; take profit 2%. On its own with the whole account: $483 a session over the last six months on the real funds.
- **NVDL / AMDL Short-Trend Rider: above a rising 10-day, 20% trailing stop.** Buy when `close > sma10 and sma20_slope > 0 and ret5 > 0`; sell when `close < sma10`; stop loss 10%; trailing stop 20%. On its own with the whole account: $304 a session over the last six months on the real funds.
- **NVDL / AMDL Pullback in Uptrend: 12% five-day pullback above the 200-day.** Buy when `ret5 < -0.12 and close > sma200`; sell when `ret1 > 0.04 or bars_held >= 4`; stop loss 15%. On its own with the whole account: $209 a session over the last six months on the real funds.

## The last six months, month by month

Dollars a session for the whole account. Real funds from 2026-03-23 to 2026-09-22; rebuilt series to 2026-09-21.

| | 04/2026 | 05/2026 | 06/2026 | 07/2026 | 08/2026 | 09/2026 | All six months |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Real funds | $339 | $578 | $256 | $305 | $270 | $223 | $332 |
| Rebuilt series | $316 | $581 | $262 | $280 | $278 | $222 | $326 |

On the real funds: 99% of rolling one-month stretches made money, the worst -$20 a session; the worst drawdown was -15% and the worst day -$3,293.

## Every window (rebuilt series)

| Window | $ a session | Months that made money | Worst month | Worst drawdown |
| --- | --- | --- | --- | --- |
| Last six months | $326 | 100% | $222 | -15% |
| 2019 to March 2026 | $46 | 61% | -$195 | -36% |
| 2012 to 2018 | $30 | 63% | -$423 | -40% |

## Read this before trusting it

- The three strategies' rules were set before the last six months and never fit to them, but the three were chosen from about 200 candidates for how well they covered each other over those months. The months are in-sample for that choice.
- In ordinary years the same account made far less: $46 a session over 2019 to March 2026 and $30 over 2012 to 2018, with drops of 36% and 40%.
- MUU, NVDL and AMDL are 2x funds. The account is a bet that memory and GPU chips keep trending.

## Running it

- Each bot has a Pine script per fund here, set to trade 33% of equity. Put each on a daily chart of its fund. A bot on two funds holds one of them at a time: while it holds one, skip the other's buy.
- The paper trail (`../paper/`) runs it from the September 24 open.
