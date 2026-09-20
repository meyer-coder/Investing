# Why the breeding prompt works

A teardown of the prompt in [`evotrader/prompts.py`](../evotrader/prompts.py) — the
one Claude call that stands between one generation of trading agents and the
next. Everything else in this repo is deterministic; this prompt is the only
place where judgement enters the loop, so it is worth understanding part by
part.

The short version: the prompt works because it never asks Claude to *predict
the market*. It asks Claude to **explain a backtest that already happened** and
then to **write code-like objects that a compiler will check**. Both halves are
tasks with ground truth attached, and the surrounding machinery makes a wrong
answer cheap.

---

## 1. Anatomy

One breeding call is assembled from five blocks, in this order.

| Block | Built by | Static? | Job |
|---|---|---|---|
| Role + task contract | `SYSTEM_PROMPT` (`prompts.py:18`) | yes (cached) | Who you are, the two-part job, the hard physics |
| Rule language | `_rule_reference()` (`prompts.py:50`) | yes | The exact vocabulary the output must compile against |
| Genome fields | `_genome_schema_text()` (`prompts.py:77`) | yes | Field-by-field meaning and ranges |
| The evidence | `elite_report()`, `population_summary()`, `history_summary()` | no | What actually happened this generation |
| The task | tail of `build_breeding_prompt()` (`prompts.py:262`) | mostly | Count, diversity requirement, output ordering |

The reply is constrained by `GENOME_JSON_SCHEMA` (`prompts.py:94`) and passed to
`LLMBreeder._materialise()` (`breeder.py:129`), which compiles every offspring
and throws away whatever does not build.

---

## 2. The nine mechanisms that actually carry the weight

### 2.1 The task is retrospective, not predictive

> "Work out *why* the top agents did well and where they were fragile."

Asking a language model "what will outperform?" invites confident
pattern-matching on financial folklore. Asking "here are 100 backtests, which
of these results are repeatable?" is a reasoning task over data in the context
window, with the evidence sitting right there. The prompt only ever asks the
second question. This is the single largest reason it produces usable output.

### 2.2 The output is checked by a compiler, not by a reader

The rule language section is not documentation, it is a **grammar contract**:
operators enumerated, "no Python, no function definitions, no lookups", the
feature list generated from `FEATURE_DOCS` so the prompt can never drift out of
sync with the runtime. Then `compile_genome()` enforces it for real. A
hallucinated feature name is not a subtly wrong strategy that quietly loses
money for 400 generations — it is a `GenomeError` at `breeder.py:141` and a
dropped offspring. The prompt is allowed to be ambitious precisely because the
validator is unforgiving.

### 2.3 Failure is shown, not just success

`population_summary()` deliberately includes the bottom five and the count of
agents that never traded at all. Most "show the model the winners" designs omit
this, and the model then has no way to tell a discriminating rule from a rule
that simply fired more often. Negative evidence is what makes the contrast
informative.

### 2.4 Journals give causal texture, not just scores

`elite_report()` ships best trades, worst trades, per-rule fire counts, signals
blocked by risk limits, and sample entry reasoning. This converts "score +1.41"
into something explainable: *this agent's exit rule fired twice, both times near
the top, and its stop never triggered*. A score alone supports only
hill-climbing on parameters; a journal supports transferring a **reason**, which
is what the LLM is there to do that mutation cannot.

### 2.5 Explicit anti-overfitting instructions with a numeric handle

> "a rule that fired three times in one bull year is noise; an edge that shows
> up across many trades, symbols and regimes is a signal"

This works because the prompt also hands over the numbers that make the
judgement checkable: trade counts, turnover, exposure, profit factor, and a
held-out window. An instruction to "avoid overfitting" without those fields
would be decoration. The instruction to "say plainly when a result looks like a
beta bet dressed up as a strategy" targets the specific failure mode of this
domain — long-only agents in a bull market look brilliant until you print
`bh +43.0%` next to them, which `Metrics.summary()` always does.

### 2.6 Diversity is a requirement, not a hope

> "at least a couple of genuinely different hypotheses, so the population does
> not collapse onto one lineage" … "the set as a whole must cover more than one
> hypothesis"

Left alone, an LLM breeder converges: it reads the winner, writes six variants
of the winner, and by generation 30 the population is one idea with different
thresholds. The prompt fights this at three levels — the instruction above, the
`parents` field that makes lineage explicit and visible, and `HybridBreeder`
(`breeder.py:151`), which reserves half the population for mutation and random
immigrants that Claude does not author at all.

### 2.7 The physics is stated up front and enforced anyway

> "Orders decided on a bar fill at the NEXT bar's open, with commission and
> slippage charged. A rule that only works with same-bar fills will not work."

Lookahead bias is the classic way a generated strategy gets a fantastic
backtest and zero real edge. Stating it prevents the model from *designing*
toward same-bar fills; "applied by the runtime whatever you write" tells it the
constraint is not negotiable, so it does not waste attempts. The pairing matters
— a constraint that is stated but not enforced is a suggestion, and one that is
enforced but not stated wastes a generation of offspring discovering it.

### 2.8 Scale calibration

> "rsi14 is 0-100; dist_sma200 is a fraction like 0.05; ret20 is a fraction like
> -0.08"

Three examples, and they kill the most common mechanical error in generated
rules: `dist_sma200 < -5` when the feature is a fraction, producing a rule that
never fires. Note that this failure would otherwise be *silent* — it compiles
fine and simply scores badly, which is the worst kind of bug in an evolutionary
loop because it wastes a slot without explaining itself. Also note where the
antidote appears: in the system prompt, next to the constraint it defends
against, not buried in the feature list.

### 2.9 Reasoning is forced before commitment

`analysis` and `lessons` are required fields, and the task block adds: "Before
the genomes, write the `analysis`". Because the reply streams in order, an
analysis written first is genuinely in the context the genomes are generated
from — the schema turns "think before you answer" into a structural
requirement rather than a polite request. The `lessons` array then carries
claims forward: `LLMBreeder.breed()` accumulates them (`breeder.py:124`) and
`build_breeding_prompt()` re-injects the last twelve. That is the loop's
**memory**, and it is the mechanism that lets generation 200 know something that
was learned in generation 40 without the intervening 160 prompts in context.

---

## 3. What each part is defending against

| Remove this | And you get |
|---|---|
| Rule grammar + `compile_genome` | Plausible-looking rules referencing features that do not exist |
| Worst performers | No contrast; the model cannot tell signal from frequency |
| Journals | Parameter tweaking; the LLM reduces to an expensive mutation operator |
| Held-out window | Overfitting that nobody, model or operator, can see |
| Benchmark (`bh`) in every summary | A bull-market beta bet declared a winning strategy |
| Diversity clause + `HybridBreeder` | Monoculture by generation ~30 |
| Scale examples | Silent never-firing rules |
| `lessons` | Amnesia; each generation re-derives the same conclusions |
| Fill/cost physics | Lookahead bias with a beautiful equity curve |

---

## 4. Where it is weaker than it looks

Four honest criticisms, roughly in order of how much they would cost a long run.

**The held-out window is being selected on.** `elite_report()` prints
`held-out window: ...` every generation, and the model breeds from what it sees.
Across 1000 generations that set is no longer held out in any meaningful sense —
it has been laundered into the training signal, one selection decision at a
time. Genuinely clean options: hide it from the prompt and use it only for the
operator's final read, or rotate the window.

**Rejected offspring teach nobody anything.** `_materialise()` drops invalid
genomes and prints a reason to stdout. The next prompt never sees it. There is
already an `extra` parameter on `build_breeding_prompt()` — feeding last
generation's rejection reasons through it would close the loop and turn a wasted
slot into a correction. Cheap change, direct win.

**Lessons accumulate but are never retired.** They are appended, deduped by
exact string, and truncated to the last 24. Nothing marks a lesson as
*contradicted by later evidence*, so a confident wrong claim from generation 12
keeps riding along. Attaching a generation stamp and asking the analysis step to
explicitly confirm or retire prior lessons would make the memory self-correcting
instead of merely persistent.

**Only the static half of the prompt is cached.** `llm.py:170` puts a cache
breakpoint on `SYSTEM_PROMPT`, but `_rule_reference()` and
`_genome_schema_text()` are equally static and are rebuilt into the *user*
message every call, so they are re-charged as fresh input tokens every
generation. Moving both into the cached system block is a pure cost saving with
no behavioural change.

Smaller notes: `Genome.fingerprint()` exists but duplicate offspring are not
surfaced back to the model; the population summary reports distribution but no
measure of diversity, so "the population has collapsed onto one lineage" is
something the prompt asks the model to prevent without ever telling it that it
is happening.

---

## 5. The transferable pattern

Strip out the trading and what remains is a template for putting an LLM inside a
loop that runs thousands of times:

1. **Call it rarely, on aggregates.** Once per generation over 100 backtests, not
   once per decision. (The README's cost table is this point in dollars.)
2. **Give it evidence with outcomes attached, including the failures.**
3. **Constrain the output to something a machine can reject** — schema for shape,
   compiler for semantics.
4. **Make a bad answer cost one slot, never the run.** Every failure path here
   degrades to mutation; `available == False` degrades the whole system to a
   plain genetic algorithm rather than crashing.
5. **Carry forward conclusions, not transcripts.** `lessons` is a handful of
   strings, not a growing conversation.
6. **Cap the spend** (`BudgetExceeded`) so an unattended 1000-generation run
   cannot surprise you.

Points 3 and 4 are the ones most often missing elsewhere, and they are what let
the prompt ask for something ambitious — *write a novel trading hypothesis* —
without the ambition being dangerous.
