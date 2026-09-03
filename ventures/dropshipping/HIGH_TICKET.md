# Pivot: Active-Cooling Unit at $105 / $165

Supersedes the "passive only" recommendation in [CANDIDATES.md](./CANDIDATES.md).

The change came from the only input that outranks a filter: the operator is a
peptide user, owns a compressor unit, has used passive gel-pack cases, and judges
them not worth selling. That is direct product experience from inside the target
market, and it beats a heuristic calibrated on generic impulse goods.

**Assumed pricing, correct this if wrong:** smaller SKU at **$105**, larger at
**$165**, landed cost around **$60** on the larger unit.

---

## The filter I got wrong

PLAN.md filter #1 says landed cost ≤ ¼ of retail. The $165 unit at $60 landed is
**2.75x**, which fails that test. The filter is wrong here, and it's worth being
precise about why rather than just waiving it.

The 4x rule was never about the ratio. It was a proxy for **"are there enough
absolute dollars in one sale to buy a customer."** At a $35 price point the only
way to clear that bar is a fat multiple. At $165 you clear it on a thin one:

| | Passive case | Active unit |
|---|---|---|
| Retail | $34.99 | $165 |
| Markup | 4.4x | 2.75x |
| **Contribution per order** | **$23.93** | **~$74** |

A worse ratio producing three times the money. The ratio was a shortcut for the
dollars; when you can measure the dollars, the shortcut is noise.

**But the 4x rule was also carrying something real**, and that part still applies:
a thin multiple leaves less room for the thing to go wrong. On a soft case,
"wrong" means a refund. On a $60 unit with a compressor, "wrong" means you eat
$60 of hardware. That risk didn't disappear — it moved from the markup line to
the returns line, where it's modeled explicitly below.

---

## Revised economics

Return rate is set at 8%, which is realistic for imported small appliances and is
**the single number that decides whether this works**. A failed unit costs the
lost sale *plus* the hardware *plus* freight both directions.

### $165 SKU

```
Revenue                                   $165.00
  Landed COGS                             - 60.00
  Outbound shipping (2-3 lb, US 3PL)      - 12.00
  Payment processing (2.9% + $0.30)       -  5.09
                                          --------
Contribution before returns                $87.91

  Adjusted for 8% returns                            $74.16
    (0.92 x 87.91) - (0.08 x [60 COGS + 24 freight])

Breakeven CPA                              $74.16
Target CPA                                 $45.00
Net per order at target                    $29.16
Breakeven ROAS                             2.2x
```

### $105 SKU (landed ~$42)

```
Revenue                                   $105.00
  Landed COGS                             - 42.00
  Outbound shipping                       - 10.00
  Payment processing                      -  3.35
                                          --------
Contribution before returns                $49.65

  Adjusted for 8% returns                            $40.72

Breakeven CPA                              $40.72
Target CPA                                 $25.00
Net per order at target                    $15.72
```

**Both clear the bar the passive case barely reached.** Note what this does to
required volume: at $29 net, five orders a day is ~$4,400/month. The passive unit
needed to move roughly three times the units for the same money, against an
audience that would have been quietly disappointed by it.

### Sensitivity — where it breaks

| Return rate | Contribution, $165 SKU |
|---|---|
| 5% | $79.32 |
| 8% | $74.16 |
| 15% | $62.13 |
| 25% | $44.94 |

The business survives a bad return rate. It does not survive a bad return rate
*combined with* a high CPA — at 25% returns your breakeven CPA drops to $45,
barely above the $45 target CPA, and the margin for error is gone entirely.
**Measure returns early and honestly.**

---

## Why "I'd rather ship something real" is the correct call commercially

This instinct is usually filed under principle. Here it's also the strategy, for
three specific reasons:

1. **Returns scale with disappointment, and disappointment is expensive now.** A
   junk $8 case that underperforms costs you $8 and a refund. A junk $60 unit
   costs you $60, freight both ways, and the sale. High ticket punishes bad
   product in a way cheap dropshipping doesn't.
2. **This audience talks.** Peptide and GLP-1 users are a dense, communicative
   community that shares recommendations constantly. That cuts both ways at high
   velocity, and it is why review quality compounds here more than in a generic
   category.
3. **Medically motivated customers are unforgiving of failure**, correctly. A
   product protecting someone's medication has a different tolerance for "good
   enough" than a fidget toy.

**Your unfair advantage is that you are the customer.** You can film real usage
in a category where nearly every competitor is running stock footage and
affiliate scripts. That is the hardest input in this entire business to fake, and
you have it natively. It also means you already know what's wrong with the unit
you own — and *that* is your product spec and your ad hook. Write down every
annoyance with your current one before you talk to a single supplier.

---

## What changes: this is now an electronics business

The soft-goods filters retire. These replace them, and they are gates rather than
preferences.

### Gate 1 — UN38.3 report, before you order anything

Lithium batteries require a UN38.3 test report under **DOT 49 CFR 173.185**.
Carriers reject non-compliant shipments under IATA/IMDG rules. The report must be
**model-specific** — a generic one for a different cell doesn't cover your unit —
and issued by a qualified third-party lab.

**Ask every supplier for it in the first message.** This is the best
supplier-quality filter available in this category and it costs you nothing: real
manufacturers have it on file and send it over immediately. Traders reselling
unbranded units will stall, send someone else's, or go quiet. That single request
sorts your supplier list faster than any amount of review reading.

### Gate 2 — Is it actually a compressor?

Suppliers routinely describe **thermoelectric (Peltier)** units as "compressor"
cooling. The distinction is not marketing, it's physics:

- **Peltier** achieves a roughly fixed delta below ambient — typically 15–20 °C.
  At 32 °C ambient it bottoms out around 12–17 °C. **It physically cannot hold
  2–8 °C in a hot car**, which is exactly when the customer needs it.
- **A real compressor** holds its setpoint largely independent of ambient.

**The test protocol you already have detects this in one run.** Compare the same
unit at 22 °C and 32 °C ambient: a compressor holds ~5 °C in both; a Peltier's
interior tracks upward with the room. Run `analyze.py` on both conditions and the
`max_c` column tells you immediately which one you bought. This is now the
protocol's most valuable use — it verifies the supplier's central claim rather
than just measuring hold time.

Also confirm the refrigerant. Small sealed systems typically use **R600a
(isobutane)**, which is flammable, and its sealed-appliance shipping exemption
needs to be documented on the paperwork rather than assumed.

### Gate 3 — Warranty terms in writing

Who eats a DOA unit? Get the answer before the first order, in writing, with a
defined replacement window. At $60 a unit this line item is the difference
between the 8% and 25% rows in the sensitivity table.

### Gate 4 — FCC

Electronics with digital circuitry sold in the US need FCC Part 15 compliance
(typically Supplier's Declaration of Conformity). Ask for the documentation
alongside UN38.3.

---

## The capital problem, and the way around it

**Lithium batteries don't move through casual dropship air channels.** UN38.3
paperwork, flammable-refrigerant documentation, and carrier restrictions mean you
will most likely need to **stock inventory in a US 3PL** rather than ship
per-order from China. That removes the "test with zero inventory" property that
made Model A attractive, and it front-loads $1,500–3,000 of capital into a
product nobody has proven demand for yet.

**Sequence around it instead, using the advantage you already have:**

1. **Film with the unit you own.** You have the product in hand today. Make
   content now — before suppliers, before inventory, before a store.
2. **Run organic content against a waitlist or pre-order** with an explicitly
   stated ship date. This validates real demand at $165 for the cost of your
   time, not $3,000 of stock.
3. **Buy inventory only once the waitlist converts.** Then you're buying against
   measured demand rather than a hypothesis.

**If you take pre-orders, the FTC Mail Order Rule applies:** ship within the time
you stated (or within 30 days if you stated none), or offer the buyer a delay
notice and the option of a full refund. This is entirely workable — it just has
to be honest and dated. Do not take pre-order money against a ship date you
haven't confirmed with a supplier.

---

## Revised budget

| Item | Before (passive) | Now (active) |
|---|---|---|
| LLC + registered agent | $150–500 | $150–500 |
| Samples | $150 | **$200–250** (3 units at $60–80) |
| Data loggers | $80–100 | $80–100 |
| Store, 3 months | $120–320 | $120–320 |
| Initial inventory | $0 | **$1,500–3,000** (25–50 units, after waitlist) |
| Ad testing | $1,500–2,500 | $1,500–2,500 |
| Buffer | $500 | **$750** (hardware returns) |
| **Total** | **$2,500–4,000** | **$4,300–7,400** |

Meaningfully more capital. The pre-order sequencing above is what lets you defer
the largest line until demand is real, so the money genuinely at risk before
validation is closer to **$1,200–1,800**.

---

## Two SKUs: launch one

The $105 / $165 ladder is good structure — an anchor plus a step-up reliably
raises average order value even when most buyers take the lower option. But it
doubles sample cost, inventory capital, SKU management, and content.

**Launch the one you personally use**, because that's the one you can film
honestly and speak about without reaching. Add the second within 60 days of
proving the first. The ladder's benefit is real but it's an optimization, and
optimizations come after product-market fit, not before it.

---

## Revised channel thinking

$165 is a **considered purchase**, not an impulse one, and that shifts the plan:

- **TikTok Shop is weaker than assumed here.** It skews toward cheap impulse
  buying, and high-ticket conversion on it is materially worse than at $30.
- **But the affiliate math gets better.** 15% of $165 is $24.75 per sale, which
  is a genuinely attractive commission — far more motivating to a creator than
  $5 on a passive case. Creator affiliates may work well *despite* the price point.
- **Model A gains ground.** Your own store with retargeting suits a considered
  purchase, and your organic content does the demand creation.
- **Know what you're up against.** You bought yours on Amazon, which means
  established brands — 4AllFamily, DISON and others — are already capturing this
  demand through search, with review counts you won't match. Your play is
  *creating* demand on TikTok rather than competing for existing search intent.
  That's coherent, and it's what TikTok is actually good at. Just don't expect to
  win a price-and-reviews fight on Amazon's turf.

---

## Immediate next steps

1. **Write down every annoyance** with the unit you own. That list is your
   product spec, your differentiation, and your ad angles.
2. **Message 5+ suppliers asking for the UN38.3 report and FCC documentation
   first.** Watch who answers. Cost: nothing.
3. **Start filming now** with the unit you already have.
4. **Order 3 samples** ($200–250) from whoever passed step 2.
5. **Run the test protocol** at both ambients — primarily to catch Peltier units
   sold as compressors.
6. **File the LLC** while samples ship, to start the TikTok Shop 60-day clock.

---

## Sources

- [4AllFamily Pioneer PRO — portable medical fridge for insulin and GLP-1](https://4allfamily.com/products/travel-refrigerator-for-insulin-refrigerated-drugs)
- [DISON portable insulin cooler / travel refrigerator](https://disoncare.com/en-us/products/disoncare-large-capacity-insulin-cooler-box-medicine-fridge-refrigerator)
- [UN 38.3 Requirements for Lithium Batteries: A Practical Guide](https://www.compliancegate.com/un-38-3-guide/)
- [UN38.3 Testing: What It Is and Why It's Necessary](https://blog.epectec.com/what-is-un38-3-testing-and-why-is-it-necessary)
- [UN/DOT 38.3 Transportation Testing — TÜV SÜD](https://www.tuvsud.com/en-us/industries/mobility-and-automotive/automotive-and-oem/automotive-testing-solutions/battery-testing/un-dot-38-3)
