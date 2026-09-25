# Prop firm accounts: Topstep vs FundedNext (for automated MNQ day trading, long and short)

Researched 2026-09-25 from the firms' own sites and help centers. Both firms
changed rules several times in 2026, so re-check the numbers on the official
pages before buying anything.

## Recommendation

**Topstep 50K Trading Combine, Standard path ($49/month), with the Daily Loss
Limit added at purchase.**

| Why | Detail |
|---|---|
| Cheapest per attempt | $49/month, and each monthly rebill includes a reset credit. Extra resets cost $49. You pay $149 once, when you pass. FundedNext's cheapest attempt is $70–78, and the others cost $160–200. |
| Best for a bot | Topstep has an official API (TopstepX/ProjectX) that Python can drive directly, at $14.50/month with code `topstep`. It is allowed in the Combine and Express Funded accounts. You also get a free Practice account to test the bot. |
| Loosest consistency rule | Your best day must be ≤55% of total profit, versus 40% at FundedNext. Breaking it only raises the target; it does not fail you. |
| Best ratio of target to drawdown | The 50K needs a $3,000 target on a $2,000 drawdown, a ratio of 1.5. The 100K and 150K are both 2.0, which is worse. |
| No limit on the number of payouts | FundedNext Flex and Rapid accounts close after 5 payouts. |
| The DLL add-on is free on the Standard path | It adds a $1,000 daily circuit breaker, a soft pause rather than a rule breach, so a misbehaving bot cannot lose the whole $2,000 in one day. It currently also doubles the payout cap per request from $2,000 to $4,000 (a limited-time offer since 2026-06-02). |

**Choose the Standard path, not "No Activation Fee".** Standard costs
$49 × months + $149, and No Activation Fee costs $95 × months. Standard is
cheaper for anyone who takes longer than about 3 months to pass, and much
cheaper for anyone who never passes.

**Runner-up: FundedNext Futures Flex 50K** ($69.99 one-time with code FNFLEX).
Choose it if you would rather pay once than monthly, or you want to use
NinjaTrader. Its drawbacks:
- Tighter drawdown: $1,500.
- Payouts capped at $1,500 each.
- The account closes after 5 payouts.
- No first-party API, so a bot would be NinjaScript (C#) or go through a
  third-party TradingView-webhook bridge.

### Constraints the bot must live with at Topstep

- **Platform:** TopstepX is the only platform for new accounts.
- **Where the bot runs:** VPS, VPN and remote servers are prohibited, so the
  bot runs on your own computer.
- **Live Funded:** automation and the API are **not allowed** in the Live
  Funded Account. The bot earns through Express Funded accounts, which are
  simulated and allow up to 5 at once. Topstep reports that 0.71% of Express
  Funded traders were called up to Live in 2025.
- **Banned:** high-frequency trading, SIM-fill exploitation (e.g. hundreds of
  rapid trades) and hedging across accounts.
- **News:** no new mini positions (ES, NQ, etc.) from 5 minutes before to
  5 minutes after CPI. Micros are capped at 3/6/9 in that window. Never trade
  your full max size into major scheduled news.

## What the numbers mean for MNQ

MNQ pays $2 per Nasdaq point. Over the 50 sessions to 2026-09-23 (MNQ ~30,800):

| | Points | $ per MNQ contract |
|---|---|---|
| Median daily high-low range | 464 | ~$930 |
| 90th-percentile range | 850 | ~$1,700 |
| Largest range | 1,205 | ~$2,400 |

A $2,000 trailing drawdown is roughly two median days of full range on a
single contract. **The contract limits (30–50 micros) will never be the binding
constraint. The trailing drawdown is.** Realistic size is 1–3 MNQ with hard
stops.

## Futures: every account currently sold

### Topstep (monthly subscription; TopstepX; flat by 3:10 PM CT)

| | 50K | 100K | 150K |
|---|---|---|---|
| Standard path | $49/mo + $149 on pass | $99/mo + $149 | $199/mo + $149 |
| No Activation Fee path | $95/mo | $149/mo | $229/mo |
| Reset | $49 | $99 | $199 |
| Profit target | $3,000 | $6,000 | $9,000 |
| Max Loss Limit (EOD trailing, real-time enforced, locks at start balance) | $2,000 | $3,000 | $4,500 |
| Optional Daily Loss Limit (soft pause) | $1,000 | $2,000 | $3,000 |
| Max contracts | 5 mini / 50 micro | 10 / 100 | 15 / 150 |
| Consistency | Best day ≤55% of total profit (raises the target, does not fail you) | same | same |

**Express Funded Account (after you pass).**

Drawdown and sizing:
- Balance starts at $0, with a Max Loss Limit of −$2K/−$3K/−$4.5K trailing
  end-of-day.
- After the first payout the Max Loss Limit sits at $0 for good, so from then
  on your balance is your only cushion.
- A scaling plan caps size until the balance grows. On the 50K: under
  $1.5K = 2 lots, $1.5K–$2K = 3 lots, over $2K = 5 lots.

Payouts:
- Standard path: 5 winning days of $150+, then up to 50% of balance, capped
  at $2K/$3K/$5K per request, or $4K/$6K/$10K with the DLL offer.
- Consistency path: at least 3 trading days with best day ≤40%, then caps of
  $3K/$4K/$6K.
- Split is 90/10.
- There is no limit on the number of payouts, and up to 5 Express Funded
  accounts can run at once.

**Other Topstep products.**
- **Back2Funded:** revives an Express Funded account lost before its first
  payout. Costs $599–$829.
- **Topstep Labs:** limited one-off drops such as a $25K Static Combine and
  $1.5K/$3K/$6K challenges. They give no path to Live, and the Labs page lists
  every drop so far as past, so availability is unclear.

### FundedNext Futures (one-time fee, no activation, no monthly; NinjaTrader / Tradovate / TradingView; flat by 3:10 PM CT)

| Program | Size | Price (promo) | Reset | Target | Max loss (EOD trailing) | DLL | Contracts | Eval consistency | Funded payouts | Split |
|---|---|---|---|---|---|---|---|---|---|---|
| Flex | 50K | $69.99 (FNFLEX; list $133.99) | $77.99 | $2,500 | $1,500 | none | 3 / 30 | 40% | 5 days ≥$200, ≤50% of profit, cap $1,500; closes after 5 payouts | 95% |
| Flex | 100K | $139.99 | ~$145–148 | $5,000 | $2,500 | none | 5 / 50 | 40% | cap $2,500; 5 payouts | 95% |
| Flex | 150K | $249.99 | $278.99 | $8,000 | $4,000 | none | 8 / 80 | 40% | cap $4,000; 5 payouts | 95% |
| Legacy | 25K | $79.99 | $73.99 | $1,250 | $1,000 | none | 2/20 → 3/30 funded | 40% | 5 days ≥$100; cap $3K until 30 benchmark days, then uncapped | 80% |
| Legacy | 50K | $199.99 | $183.99 | $3,000 | $2,000 | none | 3/30 → 5/50 funded | 40% | 5 days ≥$200; cap $6K, then uncapped | 80% |
| Legacy | 100K | $239.99 | $220.79 | $6,000 | $3,000 | none | 5/50 → 7/70 funded | 40% | same, cap $6K | 80% |
| Rapid (Pro / Daily) | 25K | $79.99 (RAPID) | $85–90 | $1,500 | $1,000 | Pro optional $500 / Daily $500 | 2 / 20 | none | Pro: every 3 days, 40% consistency; Daily: daily. Cap $800; closes after 5 payouts | 90% |
| Rapid (Pro / Daily) | 50K | $159.99–169.99 | $175–190 | $3,000 | $2,000 | $1,000 | 4 / 40 | none | cap $1,200; 5 payouts | 90% |
| Rapid (Pro / Daily) | 100K | $279.99 | $299.99 | $5,000 | $2,500 | $1,250 | 6 / 60 | none | cap $2,500; 5 payouts | 90% |

**Rules for all FundedNext Futures accounts:**
- **Allowed:** bots and EAs in both challenge and funded accounts, and news
  trading without restriction.
- **Micro-scalping rule:** trades held under 10 seconds may make up at most
  30–40% of profit.
- **Banned:** hedging with correlated instruments, grid trading and tick
  scalping.
- **Account limits:** 5 funded accounts at once.
- **Discontinued:** Bolt and the original Rapid, since 2026-07-10.

## Why the CFD / forex accounts are out

FundedNext's CFD programs are Stellar 1-Step, 2-Step, Lite and Instant.
They are not a fit for this project:
- They do not trade CME MNQ. The closest is a NAS100 CFD.
- EAs are allowed only on accounts under $50K, only on MT4/MT5, and only
  for an extra fee. Accounts of $50K and up must be traded by hand.
- US traders get Match-Trader only, which is manual-only.
- Topstep has no CFD offering.

## Rules the strategy simulator must enforce (Topstep 50K + DLL)

1. **Trailing drawdown.** The Max Loss Limit is $2,000 below the highest
   end-of-day balance. It is checked in real time against unrealized P&L and
   stops trailing at the $50,000 starting balance. Touching it fails the
   attempt.
2. **Daily loss limit.** At −$1,000 on the day, the account is flattened and
   trading stops until the next session. This is a pause, not a failure.
3. **Flat by 3:10 PM CT.** No overnight or weekend positions. The session
   opens at 5 PM CT.
4. **Size.** Maximum 50 MNQ in the Combine. In the Express Funded account the
   scaling plan applies (2/3/5 lots by balance).
5. **Target and consistency.** The target is +$3,000, and the best day must be
   ≤55% of total profit. Otherwise the target becomes best day ÷ 0.55.
6. **Costs.** Commission is about $1.22 round turn per MNQ (TopstepX), plus
   slippage.
7. **CPI window.** No new trades from 5 minutes before to 5 minutes after the
   release.
8. **Direction.** Long **and short** entries.

## Unconfirmed or conflicting items

- **Labs consistency:** the Topstep Labs page says 50%, but the help center
  says 55% for the standard Combine.
- **Live Funded floor at Topstep:** $1,000 in the newer articles, $0 in an
  older overview.
- **DLL payout-cap offer:** Topstep calls the doubled cap "limited time" and
  gives no end date.
- **FundedNext Rapid 50K:** official pages list $159.99 and $169.99, and
  conflicting reset prices.
- **FundedNext Legacy funded contract limits:** the product page and the
  help center disagree.

## Main sources

- **Topstep pricing:** https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions
- **Topstep Combine:**
  - Parameters: https://help.topstep.com/en/articles/8284197-trading-combine-parameters
  - Max Loss Limit: https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit
  - Daily Loss Limit: https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account
  - Consistency: https://help.topstep.com/en/articles/8284208-consistency-at-topstep
- **Topstep Express Funded and payouts:**
  - Parameters: https://help.topstep.com/en/articles/8284215-express-funded-account-parameters
  - Payout policy: https://help.topstep.com/en/articles/8284233-topstep-payout-policy
  - Scaling plan: https://help.topstep.com/en/articles/8284223-what-is-the-scaling-plan
- **Topstep API and prohibited strategies:**
  - API: https://help.topstep.com/en/articles/11187768-topstepx-api-access
  - Prohibited strategies: https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep
  - High-volatility risk adjustments: https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility
- **Topstep Live Funded:**
  - Rules: https://www.topstep.com/live-funded-account-rules
  - Parameters: https://help.topstep.com/en/articles/10657969-live-funded-account-parameters
- **FundedNext Futures plans:** https://fundednext.com/futures
- **FundedNext Futures help (Flex, automation, news, prohibited):**
  - Flex parameters: https://helpfutures.fundednext.com/en/articles/14878751
  - Automated trading: https://helpfutures.fundednext.com/en/articles/14298560
  - News trading: https://helpfutures.fundednext.com/en/articles/14298245
  - Prohibited strategies: https://helpfutures.fundednext.com/en/articles/14298337
- **FundedNext CFD EA policy:** https://help.fundednext.com/en/articles/8020763
