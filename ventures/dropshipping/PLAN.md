# One-Product Dropshipping — Operating Plan

A plan for the thing described: find one AliExpress product, build a store around
it, drive traffic with TikTok. Written to be executed, not admired.

Everything below is a model, not a promise. The numbers are illustrative
placeholders you replace with your real quotes and your real ad costs.

---

## The one thing that breaks the plan as stated

**You cannot ship direct from AliExpress and sell on TikTok Shop.**

TikTok Shop requires orders to be handed to a valid carrier fast and delivered
inside roughly **six business days**. AliExpress standard shipping is **15–30
days**, in AliExpress-branded packaging. Doing this gets listings pulled and the
account suspended — not "maybe," it is the single most common way new TikTok
Shop sellers get killed.

So the plan forks. Pick one deliberately, because they are different businesses
with different cost structures:

### Model A — Your own store, TikTok as *marketing* (not TikTok Shop)

Traffic comes from organic TikTok content and TikTok/Meta ads, checkout happens
on your site. You control the shipping promise, so you can honestly say "ships
in 10–14 days" and still be compliant, because the only rules are your own and
the FTC's.

- **Pro:** start this week, near-zero fulfillment infrastructure, highest margin
  per order, no marketplace fees.
- **Con:** you pay for every visitor. Long shipping raises refunds and chargebacks.
  No marketplace trust halo.
- **Best for:** testing whether a product has any pull at all, cheaply.

### Model B — TikTok Shop, with the supply chain to back it

Same product, but sourced through an agent who **stocks it in a US warehouse**
(or ships plain-packaged from a fast-lane facility). You get TikTok Shop's native
checkout, the affiliate/creator army, and the algorithm actively pushing shoppable
video.

- **Pro:** dramatically cheaper customer acquisition — creators sell for you on
  commission instead of you paying CPMs. This is where the actual money is in 2026.
- **Con:** requires inventory capital, a 3PL, a real business entity, and TikTok
  wants the company to be **60+ days old** with a business license valid 90+ days.
  Sole proprietorships are not supported for US/UK.
- **Best for:** the second phase, once a product has proven itself in Model A.

**Recommendation: run A to validate, then move the winner to B.** Do not start
with B. Model B asks you to buy inventory of a product nobody has proven anyone
wants.

---

## Phase 0 — Decisions to make before spending anything

| Decision | Default answer | Why |
|---|---|---|
| Entity | LLC, registered now | Starts the 60-day TikTok Shop clock immediately, and it is the thing standing between a chargeback dispute and your personal bank account. Cheap. Do it week one. |
| Bank | Separate business checking | Non-negotiable for sanity at tax time and for TikTok Shop verification. |
| Payments | Stripe + Shop Pay / PayPal | PayPal presence measurably lifts conversion on unknown stores. Expect a rolling reserve as a new high-risk-category merchant. |
| Store platform | See platform section below | |
| Budget ceiling | Set it now, in writing | See kill criteria. |

---

## Product selection — the part that decides the outcome

Store quality is worth maybe 20% of the result. Ad creative is worth 30%.
**Product choice is worth the other 50%.** Almost everyone inverts this and
spends three weeks on a logo.

### Hard filters — a candidate fails if any is false

1. **Landed cost ≤ 1/4 of intended retail.** Below 4x markup there is no room for
   ad spend, refunds, and a mistake. 5x is comfortable.
2. **Retail price $25–$60.** Under $25 there is not enough gross profit to pay for
   a customer. Over $60 impulse buying collapses and you need retargeting funnels
   you do not yet know how to build.
3. **It demonstrates visually in under 3 seconds.** If you cannot film someone
   using it and have a stranger instantly understand *why they want it*, it cannot
   work on TikTok. This filter alone removes ~80% of AliExpress.
4. **Not available in a nearby Target / Walmart.** You are asking for a price
   premium over commodity. Earn it with unavailability.
5. **Ships under 1 lb and is not fragile.** Weight is margin. Glass is chargebacks.
6. **Zero regulatory surface.** No ingestibles, supplements, skincare with active
   claims, electronics touching mains power, batteries above small cells, anything
   for infants, anything medical-adjacent. A single FDA/CPSC-flavored problem ends
   the company.
7. **No visible brand marks or patented design.** Counterfeits get you banned and
   sued, in that order.

### Soft signals — what a winner actually looks like

- Solves a small, specific, *annoying* problem people can name in one sentence.
- Has an existing organic TikTok footprint — other people's videos about it are
  already getting views — but no dominant branded seller owning the search term.
  Zero footprint means no demand. One big branded player means you are late.
- Slight visual weirdness. Things that make someone stop scrolling and go "wait,
  what is that." Perfectly normal products do not go viral.
- Has a natural bundle or upsell (a 2-pack, refills, an accessory) so AOV can be
  raised later without new customers.

### Where to look

Search TikTok itself for the category plus "amazon finds," "tiktok made me buy it,"
sort recent. Watch what is climbing, not what already peaked. Cross-reference
against AliExpress order counts and review dates — a supplier with 5,000+ orders
and reviews from the last 60 days is real; one with 40 orders is a gamble on a
factory that may vanish.

**Shortlist 5 candidates. Do not fall in love with #1.**

---

## Unit economics — do this math before ordering anything

Model A, illustrative, at a $34.99 price point:

```
Revenue                                  $34.99
  Landed COGS (product + shipping)       - 8.00
  Payment processing (2.9% + $0.30)      - 1.31
  Refund / chargeback reserve (5%)       - 1.75
                                         -------
Contribution before advertising          $23.93

Breakeven CPA                            $23.93   <- you lose money above this
Target CPA                               $12.00
Net per order at target                  $11.93
Breakeven ROAS                           1.46x
Target ROAS                              2.5x+
```

Model B, same product, on TikTok Shop:

```
Revenue                                  $34.99
  TikTok referral fee (~8%)              - 2.80
  Affiliate commission (~15%)            - 5.25
  Landed COGS (US 3PL stock)             - 8.00
  Outbound shipping + pick/pack          - 4.00
  Refund reserve (5%)                    - 1.75
                                         -------
Contribution per order                   $13.19   <- with $0 paid ads
```

Note what Model B actually buys you: the affiliate commission *replaces* ad
spend, and it is paid only on sales that happen. That is the entire reason
TikTok Shop is interesting.

**Fill this table in with real quotes before you spend a dollar on ads.** If
contribution before advertising is under $15 in Model A, the product cannot
support paid acquisition and you should discard it.

---

## Sourcing and fulfillment

**Do not order to customers from AliExpress checkout directly, in either model.**
Even in Model A it means AliExpress-branded packaging, unpredictable transit, and
no recourse when a factory ghosts you.

Progression, in order:

1. **Samples first, always.** Order the shortlist from 2–3 suppliers each, to
   yourself. You need to hold it, and you need it for filming. Budget ~$150 and
   2 weeks. This step is skipped by nearly everyone and is the cheapest insurance
   in the whole plan.
2. **Get a sourcing agent once you have any volume** (roughly 10+ orders/day).
   An agent gives you plain or custom packaging, consolidated shipping, faster
   lanes, consistent stock, and one accountable human. This is the step that turns
   a dropshipping hustle into something resembling a company.
3. **US 3PL stock for Model B.** Required for the six-day window. Start with a
   small buy — 100–300 units of a *proven* product, never a hypothesis.

Set shipping expectations honestly and prominently in Model A. Stated transit
times reduce refunds far more than they reduce conversion; hidden ones produce
chargebacks, and chargebacks over ~1% of volume put your payment processing at
risk, which is a company-ending event.

---

## Store platform

You mentioned **Amboras** — the AI-native store builder that has been circulating
on TikTok. Honest read:

**What it is.** A Y Combinator-backed (S26) AI-native ecommerce platform that
builds a working storefront from a prompt — copy, layout, products, checkout —
with an AI assistant on every admin page that can take real actions like issuing
refunds, and automatic A/B testing of headlines, imagery, pricing, and bundles.
Pricing runs roughly $39 / $105 / $399 per month by tier, no platform transaction
fee beyond Stripe's.

**Where it genuinely fits your plan.** Your use case — one product, many landing
page variants, fast iteration, no developer — is close to the best-case scenario
for a tool like this. Automatic A/B testing on a single-product store is real
leverage, and spinning up a new offer variant per ad angle in minutes is exactly
the loop that wins.

**The honest risk.** It is a young company. Every "went from 1% to 3.2% conversion"
number you have seen is a self-reported testimonial from a promotional video,
frequently posted by affiliates. Treat those as marketing, not evidence. A
platform this new carries real risk of pricing changes, feature gaps you discover
at the worst moment, and migration pain if you outgrow it or it folds.

**Recommendation:** either choice is defensible.

- **Shopify** if you want the boring, survivable answer — every integration, every
  3PL, every TikTok Shop connector works, and every problem you hit has already
  been answered by someone. Costs more in app fees. This is the lower-variance pick.
- **Amboras** if speed of iteration matters more to you than ecosystem depth, and
  you are willing to be an early adopter. Start on the $39 tier.

Either way: **export your customer list and order data monthly.** That data is the
only asset in this business that is genuinely yours, and it is the only thing that
survives a platform change.

Do not spend more than **two days** on the store. A clean single-product page with
good photography, honest shipping terms, visible reviews, and a fast mobile load
converts. Design perfectionism here is procrastination wearing a costume.

---

## The TikTok content engine — the actual bottleneck

This is where the business is won or lost, and it is the part the tooling cannot
do for you.

**The rule: volume of creative attempts beats quality of any single attempt.**
Plan on 3–5 videos per day, every day. Most get 200 views. That is normal and not
a signal. You are buying lottery tickets, and the only variable you control is how
many you buy.

**Structure that works:**
- **0–3 seconds:** the hook. Visual, not verbal. Show the problem or the weird
  thing. Almost all failure happens here.
- **3–15 seconds:** demonstrate. Real hands, real use, one specific benefit.
- **15–25 seconds:** proof or reaction, then a soft CTA.

Shoot vertical, natural light, phone camera, no logos on screen, no polish. Ads
that look like ads get scrolled. Native trumps produced, consistently.

**Angles to rotate** (same product, different framing): the problem, the
before/after, the "I was skeptical," the gift, the POV, the unboxing, the
"things I wish I knew," the reply-to-a-comment. When one angle hits, make ten
variations of *that* angle immediately.

**Organic before paid.** Post organically for 2–3 weeks first. It costs nothing
but time and it tells you which hook works before you pay for impressions. Then
put money behind the videos that already earned attention on their own — never
behind an untested creative.

**Model B's real unlock is creator affiliates.** Once on TikTok Shop, open an
affiliate program at 15–20% commission and send free samples to 50–100 small
creators. Ten percent will post. One of those posts can carry a month. This
scales far better than your own ad account and you pay only on results.

---

## Budget

Minimum for a fair test — under this, you are not testing, you are donating:

| Item | Amount |
|---|---|
| LLC + registered agent | $150–500 |
| Samples (5 candidates, 2–3 suppliers) | $150 |
| Store platform, 3 months | $120–320 |
| Domain | $15 |
| Ad testing budget | $1,500–2,500 |
| Buffer for refunds / chaos | $500 |
| **Total** | **$2,500–4,000** |

Ad budget is the line that matters. Under ~$1,500 you cannot gather enough data
to distinguish a bad product from bad creative, and you will kill a winner by
mistake or nurse a loser out of hope.

**Money you should be willing to lose entirely.** Most first products fail. That
is the base rate, and it is not a reflection of effort.

---

## 8-week sequence

| Week | Focus | Done means |
|---|---|---|
| 1 | LLC filed, bank opened, shortlist of 5, samples ordered | Clock started, money committed to samples only |
| 2 | Store built on chosen platform. Unit economics table filled in with real quotes | Store live, math proven on paper |
| 3 | Samples arrive. Film 20+ videos across all 5 candidates | A content backlog exists |
| 4 | Post organically, 3–5/day. No ad spend | Real view and engagement data per product |
| 5 | Kill 4 candidates. Commit to the one with traction. Begin paid testing at ~$50/day | One product, one focus |
| 6 | Scale what works, kill what does not. Iterate creative daily | CPA trending toward target |
| 7 | If profitable: contact sourcing agents, get pricing at volume | A path off AliExpress checkout |
| 8 | Decision point: scale into Model B, or stop | An honest verdict |

---

## Kill criteria — write these down now, while you are unattached

Set these before you have money and ego in the game. Their entire purpose is to
make the decision for you at the moment you will most want to rationalize.

- **Product-level:** $300 spent on a single product with no sale at a viable CPA → kill it, move to the next candidate. No exceptions, no "one more creative."
- **Creative-level:** an angle with 10+ videos and no video over 5,000 views → the angle is dead, not the product.
- **Business-level:** the full ad budget spent across all 5 candidates with nothing reaching target CPA → stop. The thesis was wrong. That outcome cost you ~$3,000 and eight weeks, and it is a *cheap* answer to a real question.
- **Compliance-level:** any account warning, IP complaint, or chargeback rate approaching 1% → stop selling that product immediately. Payment processing is the one thing you cannot get back.

---

## Things that quietly kill these businesses

- **Chargebacks.** Long shipping plus surprised customers. Mitigate with explicit
  shipping terms, a real support email answered within 24 hours, and instant
  refunds on anything contested. A refunded order costs you $8. A chargeback costs
  you $15 plus your processor's patience.
- **Sales tax.** Economic nexus is per-state and triggers on volume, not presence.
  Once revenue is real, get an accountant. This is not a first-week problem, but
  it is a real one.
- **Supplier disappearance.** A factory going dark mid-scale is common. Have a
  second supplier qualified before you need them.
- **Single-platform dependency.** The whole business currently rests on one
  algorithm's goodwill. Collect emails from day one — it is the only channel you
  own outright.
- **Sunk cost.** By far the most expensive item on this list. The kill criteria
  above exist specifically to defend against it.

---

## What good looks like at week 8

Not "quit your job" money. A product with a repeatable CPA meaningfully under
contribution margin, 5–15 orders a day, a supplier who answers messages, and a
creative process that produces one usable video per day without agony. That is a
real foundation, and it is a realistic ceiling for eight weeks and $3,000.

The far more likely outcome is that all five products fail and you learn what a
hook is. That is a legitimate result. Just make sure it costs $3,000 and not
$15,000 — which is entirely a matter of whether you honor the kill criteria.

---

## Sources

- [What Is Amboras? Features and Setup Guide](https://www.leap.site/en/ec-guide/store-setup/amboras-ai-ecommerce/)
- [Amboras Pricing Plans Explained](https://www.leap.site/en/ec-guide/store-setup/amboras-pricing-guide/)
- [Putting Amboras to the Test: Third-Party Reviews](https://www.leap.site/en/ec-guide/store-setup/amboras-ai-ecommerce-review/)
- [Amboras on Y Combinator](https://www.ycombinator.com/companies/amboras)
- [TikTok Shop Dropshipping Policy 2026](https://www.lzdropshipping.com/tiktok-shop-dropshipping-policy-2026-what-ecommerce-sellers-must-know/)
- [2026 TikTok Shop Requirements: Seller Eligibility & Setup](https://www.bebolddigital.com/blog/tiktok-shop-requirements)
- [TikTok Shop Eligibility 2026: Requirements and Fees](https://canopymanagement.com/tiktok-shop-eligibility-what-you-need-to-get-started/)
- [Best Dropshipping Suppliers for TikTok Shop](https://dodropshipping.com/best-dropshipping-suppliers-for-tiktok-shop/)
