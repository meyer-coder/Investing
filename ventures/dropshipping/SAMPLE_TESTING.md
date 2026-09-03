# Sample Testing Protocol — Passive Medication Coolers

The purpose of this test is narrow and specific: produce **one honest number you
can put in ad copy** and defend, plus a ranking across three suppliers.

Everything else in this business is reversible. A temperature claim about a
container holding someone's medication is the one place where being wrong costs
more than money, so this is worth two days of doing properly.

---

## What you're actually measuring

Refrigerated medications — GLP-1 pens, insulin, reconstituted peptides — are
stored at **2–8 °C (36–46 °F)**. That range has two edges and **both of them
matter**:

- **Above 8 °C** the product degrades. This is the failure everyone thinks about.
- **Below 0 °C the product is destroyed**, and unlike warm exposure it is often
  invisible. This is the failure almost nobody tests for, and it is the one your
  cooler is most likely to cause.

That second point is the single most valuable thing in this document. A gel pack
straight out of a home freezer is around **−18 °C**. Sealed in a small insulated
case pressed against a vial, it can easily drive the contents below freezing in
the first hour. **A cooler that freezes the medication is worse than no cooler at
all**, because the customer doesn't know it happened.

So you are measuring three things, in priority order:

1. **Hold time** — hours until the payload first exceeds 8 °C. This is your headline number.
2. **Freeze excursion** — whether the payload ever drops below 0 °C, and for how long.
3. **Time in window** — the fraction of the run spent inside 2–8 °C.

> Confirm the storage range against the labeling for the specific products your
> customers use. Don't take the numbers above — or anything a supplier tells you
> — as the spec for your copy.

---

## Equipment

| Item | Qty | Approx. cost | Notes |
|---|---|---|---|
| USB temperature data logger, external probe, ±0.5 °C | 4 | $80–100 | One per cooler, one for ambient. Elitech RC-5+ or similar cold-chain logger. |
| Dummy vials (3 mL, water-filled) | 6–9 | ~$10 | Never test with real medication. |
| Insulated cooler / styrofoam box | 1 | — | For the hot-ambient run. |
| Kitchen thermometer or second logger | 1 | — | Ambient reference. |
| Painter's tape, permanent marker | — | — | Label everything. |

**Do not use ±1 °C loggers.** Your entire decision window is 6 °C wide. A logger
with ±1 °C error can't distinguish "held for 14 hours" from "held for 20," and
you're about to print that number on a website.

### Calibrate before you trust anything

Ice-bath check, costs nothing, takes ten minutes, and catches the one bad logger
in four that would otherwise silently corrupt a whole run:

1. Fill a glass with crushed ice, add just enough water to fill the gaps.
2. Stir, wait 3 minutes.
3. Submerge all four probes. A properly made ice bath is **0.0 °C**.
4. Record each logger's reading. Anything off by more than 0.5 °C gets returned,
   or gets a written offset you apply to every reading from it.

Do this again after all testing finishes. If a logger drifted, its runs are void.

---

## Test matrix

Three coolers × two ambient conditions × two repeats = **12 runs**.

| Condition | Ambient | Represents |
|---|---|---|
| **A — Indoor** | 22 °C / 72 °F | Baseline. Best case. Do not advertise this number. |
| **B — Hot travel** | 32 °C / 90 °F | Car, summer, airport. **This is the number you advertise.** |

For condition B, you don't need a lab. A closed styrofoam box with a small heat
source in a warm room, or a shaded car on a hot day, gets you close enough —
what matters is that the **ambient logger records what actually happened**, so
your result is anchored to a real measured temperature rather than an assumed one.

**Two repeats minimum per cell.** A single run is an anecdote. Gel pack
conditioning varies, seals seat differently, ambient drifts. If your two repeats
disagree by more than 20%, run a third and find out why before trusting either.

---

## Procedure

Run all three coolers **simultaneously in the same ambient**, so a drifting room
affects them equally and the comparison stays fair.

1. **Precondition gel packs.** Freeze all packs together, same freezer, ≥ 8 hours.
   Note the freezer temperature.
2. **Rest the packs.** Remove and leave at room temperature for a set interval.
   **Test this interval as a variable** — 0 min, 10 min, 20 min. It is very likely
   the difference between "freezes the medication" and "works correctly," and if
   so it becomes a printed instruction card in your packaging and a genuine
   differentiator.
3. **Load dummy vials**, water-filled, matching the real payload count and mass.
   An empty cooler has almost no thermal mass and will give you a number that
   flatters the product and misleads customers.
4. **Place the probe taped against a dummy vial**, in the position most exposed to
   ambient — typically the vial furthest from the gel pack, nearest the zipper.
   You care about the temperature of the *medication*, not the air, and you care
   about the *worst* vial, not the average one.
5. **Seal, start logging at 1-minute intervals**, place the ambient logger beside
   the coolers, and start the run.
6. **Run 48 hours** or until the payload is within 2 °C of ambient, whichever comes
   first. Don't open it to check. Opening it ends the run.
7. **Export CSVs**, name them `{supplier}_{condition}_{run}.csv`, and analyze.

---

## Analysis

```
python3 ventures/dropshipping/cooler_test/analyze.py logs/*.csv
```

The script reports hold time, freeze excursions, time in window, and min/max per
run, and flags any run where the payload went below 0 °C. Use `--fahrenheit` if
your logger exports °F, and `--help` for column overrides.

Pass all twelve runs together to compare suppliers. But when you're deriving the
number that goes on the website, pass **only the winning supplier's condition-B
runs** — the "defensible claim" line reports the worst hold among whatever you
give it, so mixing suppliers hands you the loser's number.

---

## Turning results into ad copy

**The rule:**

```
Advertised hold time = worst observed hold time in condition B (32 °C)
                       rounded DOWN to the nearest 2 hours
                       × 0.8 safety margin
```

Then state the ambient alongside it. "Keeps cold up to 12 hours at 90 °F" is a
claim you can defend with a spreadsheet. "Keeps cold 36 hours" — the number the
supplier will hand you — is a claim you cannot, and it is the one that generates
the refund, the review, and eventually the complaint.

The conservative number also converts better than you'd expect. Specificity plus
a stated condition reads as competence; a big round number reads as marketing.

**Never repeat the supplier's figure.** They tested empty, at room temperature,
measuring air. You are testing loaded, hot, measuring the vial. Those are
different numbers and only one of them describes your customer's trip.

---

## Non-thermal checks

Do these while the runs are going. Record in `scorecard.csv`.

| Check | Method | Fails if |
|---|---|---|
| Zipper cycles | Open/close 200× | Snags, splits, or pull detaches |
| Seam integrity | Tug seams, inspect lining | Stitching gaps, lining separates |
| Gel pack leak | Freeze/thaw 5×, then squeeze firmly | Any weep or seam split |
| Drop test | 1 m onto hard floor, loaded, 3× | Contents shift loose, shell cracks, closure pops |
| Odor | Open after 24 h sealed | Strong plastic or chemical smell — a top refund driver |
| Fit | Load real vial/pen count | Won't close when full, or vials rattle loose |
| Closure security | Invert and shake, loaded | Opens |

Odor and fit look trivial next to thermal performance and generate more refunds
than either. A case that smells of solvent, or that won't zip with four pens in
it, comes straight back regardless of how well it holds temperature.

---

## Choosing the winner

Weight the decision like this:

| Factor | Weight | Why |
|---|---|---|
| Hold time at 32 °C | 35% | The product's actual job |
| No freeze excursion | 25% | Pass/fail — a unit that freezes the payload is disqualified outright, whatever else it scores |
| Build quality (non-thermal) | 20% | Drives refunds and reviews |
| Landed cost | 15% | Must still clear the 4× markup filter |
| Supplier responsiveness | 5% | Reply speed, willingness to do plain packaging — matters more at scale |

**Freeze excursion is a veto, not a deduction.** A cooler that puts the payload
below 0 °C fails no matter how long it holds cold afterward, unless a gel-pack
resting interval reliably eliminates it — in which case that interval becomes a
mandatory instruction card in every box.

If no unit clears the bar, that is a real and useful result: it means the passive
category can't support an honest claim at your price point, and you move to the
next candidate having spent $60 instead of $3,000.

---

## Files

- `cooler_test/analyze.py` — log analyzer
- `cooler_test/scorecard.csv` — results template, one row per supplier
