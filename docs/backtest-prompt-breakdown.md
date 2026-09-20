# Breakdown: the NQ backtest prompt

An analysis of the prompt that begins *"I want to backseat results of the
strategy given"* — what it does well, why those moves work, and the four places
it breaks. This is not a general critique: I attempted to execute this prompt
before writing the breakdown, so every failure below is one I actually hit, not
one I imagined.

---

## 1. What kind of prompt this is

It is a **delegated research brief**. It does not ask for an answer, it
commissions a piece of work and hands over the judgement calls. That is a much
harder prompt to write than a question, and this one gets most of the hard
parts right. The parts it gets wrong are all the same kind of wrong, which is
useful — it means one habit fixes them.

---

## 2. Anatomy: fourteen moves

| # | The move | What it does |
|---|---|---|
| 1 | "backtest results of the strategy given" | Names the task and its subject |
| 2 | "a pdf and a dashboard html format" | Names the deliverable, as artifacts |
| 3 | "performed on Nasdaq" | Instrument scope |
| 4 | "use the trading view mcp tunnel … then use external resources" | Tool priority order |
| 5 | "five minute timeframe not the 45 seconds" | Negative constraint correcting drift |
| 6 | "databento … if you run out of candlesticks … switch to CFD" | Fallback ladder with a trigger |
| 7 | "all time frames specifically … 9-10am and 10-11am" | Specific focus + exhaustive sweep |
| 8 | "the strategy spec may limit the window … we want around the clock" | Pre-emptive override of the source material |
| 9 | "month to month and … year to year" | Seasonality axis |
| 10 | "identify large historical events … find correlations" | Event study |
| 11 | "creative freedom … develop 500 variations" | Delegated search, quantified |
| 12 | "EMA, VWAP, VOLUME, DAY OF THE WEEK, time frame" | Seed list bounding the search |
| 13 | "all of these on a pnl chart" | One comparative visual |
| 14 | "You are a quantitative backtesting expert. I am lacking in experience… Do not ask for my input… think deeply, take your time" | Role, asymmetry, autonomy, effort |

---

## 3. The six things that make it work

### 3.1 It closes the clarifying-question escape hatch — and earns the right to

"Do not ask for my input" on its own is a bad instruction: it forces guessing.
What makes it work *here* is the sentence before it. "I am lacking in
experience and terminology" tells the model **why** it should not ask, and what
to do instead: stop trying to elicit specifications the user does not have the
vocabulary to give, and supply expert defaults. Those two sentences function as
a unit. Either alone is worse than both together.

### 3.2 The deliverable is named before the work is described

"A pdf and a dashboard html format" appears in the second sentence. This
decides the shape of everything downstream — it rules out an answer that lives
in chat scrollback, and it sets the bar at *two* artifacts with different jobs
(a document to read, a dashboard to explore). Most research briefs describe the
analysis and leave the output format implicit, and then get a wall of text.

### 3.3 The data cascade has an explicit exhaustion trigger

> "databento's free resources for futures NQ data, and **if you run out of
> candlesticks** switch to CFD data for NQ"

This is the strongest single piece of engineering in the prompt. Most data
requests specify one source, and the agent stalls the moment that source fails —
"I couldn't retrieve the data, how would you like to proceed?" — which is
exactly the outcome "do not ask for my input" is trying to prevent. A ranked
ladder plus a named failure condition means the agent can degrade without
stopping and, crucially, **can tell you which rung it landed on**. Preference
order is stated (futures before CFD), so the degradation is legible rather than
silent.

### 3.4 It pre-resolves a conflict it knows is coming

> "The strategy spec may limit the trading window to be only the open, we want
> to test around the clock."

The author anticipated that the source material would contradict the request,
and said which one wins. Without this the agent faces a genuine fork — respect
the spec or respect the brief — and whichever it picks, half the work is wrong.
One sentence removes an entire class of wasted effort. This is the move most
worth copying.

### 3.5 "Creative freedom" is quantified and bounded

"Take creative freedom" alone produces either timidity or randomness. Here it
is pinned between a **count** (500 variations — countable, checkable, and
clearly signalling "industrial sweep, not three ideas") and a **seed list**
(EMA, VWAP, volume, day of week, news days, timeframe). The seed list is the
part people leave out. It converts "be creative" into "vary along these axes
and any others you find", which is a search space rather than a mood.

### 3.6 Everything is framed comparatively

All timeframes, not just the open. Month to month *and* year to year. All 500
variations on one PnL chart. A number with nothing to compare it to is not a
result, and this prompt never asks for one. The 9–10am / 10–11am pairing is the
same instinct at small scale: two adjacent buckets that differ by one hour make
each other interpretable.

---

## 4. Where it breaks

All four failures are the same species: **the prompt refers to things that are
not in it and cannot be verified from inside it.**

### 4.1 The strategy is never specified — and this is the serious one

"The strategy given." Nothing in the message says what the strategy is. No
entry rule, no exit, no risk model, no name.

I recovered it — a liquidity-sweep / stop-run-reclaim family on a branch called
`claude/liquidity-sweeps-order-flow-9yac27` — by listing prior sessions, reading
their summaries, and diffing git branches. That is archaeology, and it worked
here only because the artifacts happened to be reachable. It could as easily
have surfaced the wrong one: there are sixteen branches on this repo and at
least four plausible candidates.

Now combine that with move 14. "Do not ask for my input" + an unstated referent
= **the agent is instructed to guess and forbidden to check**. Those two are
individually reasonable and jointly dangerous: the failure mode is not a stall,
it is hours of confident, well-formatted work on the wrong strategy. Everything
else in the prompt is downstream of this one gap.

The same applies, smaller, to "not the 45 seconds" — a correction to a
parameter from a conversation that is not present. I can honour the instruction
(use 5-minute) without ever knowing what it is correcting, which is fine here
but only by luck.

### 4.2 It assumes an environment it cannot see

"Use the trading view mcp tunnel." **There is no TradingView MCP server
connected to this session.** The servers available are Claude Code Remote,
Claude Docs, Fireflies, Gmail, Google Calendar, Google Drive, Robinhood,
Supabase, Vercel, Webflow and GitHub. The TradingView MCP exists — you built it,
there are three branches for it — but it is not attached here, and a prompt
cannot make a tool appear.

### 4.3 The data ladder has no rung that supports the analysis

This is the finding that actually matters for the work, and I verified each
step:

| Rung | Status |
|---|---|
| TradingView MCP tunnel | Not connected to this session |
| Databento | `401 Not authenticated` — no API key in the environment, and the free tier is a credit allowance, not an open dataset |
| Yahoo (`NQ=F`) 5-minute | Works, but hard-capped: *"The requested range must be within the last 60 days"* — verbatim from the API |
| Robinhood MCP | Connected; equity/index historicals available, intraday depth not verified |
| NQ CFD | No keyless source identified |

So the ladder terminates at roughly **60 days of 5-minute data**. Now price the
request against that:

- 60 days × 276 five-minute bars ≈ **16,560 bars** around the clock (4,680 if
  regular hours only).
- A sweep-and-reclaim setup fires a few times a day at best → order **300–600
  trades total**, across all sessions.
- The requested analysis grid is 500 variations × ~13 hourly buckets × 12
  months = **78,000 cells** — before the year-over-year axis, which needs
  multiple years and cannot be built from 60 days at all.

Three requirements in the prompt — 5-minute granularity, year-over-year
seasonality, and free data — are **mutually unsatisfiable**. Not difficult:
unsatisfiable. The prompt ranks data *sources* but never ranks these three
*requirements*, so there is no stated basis for choosing which to sacrifice.
That ranking is the missing sentence.

### 4.4 It commissions a 500-way search with no defence against finding noise

Searching 500 variations and reporting the best is a multiple-comparisons
problem, and the arithmetic is not subtle. If all 500 variations were pure noise:

- the expected best-of-500 t-statistic is **≈ 3.5**, which reads as
  "p < 0.001, highly significant" to anyone scoring a single strategy;
- a family-wise 5% error rate requires **p < 0.0001** per variation (Bonferroni),
  about z ≈ 3.9.

So a 500-way sweep is *guaranteed* to produce a champion that looks excellent.
The prompt asks for the sweep and the comparison chart, but never for a minimum
trade count, an out-of-sample holdout, a walk-forward split, or a significance
threshold — so nothing in it distinguishes an edge from the luckiest of 500
coin-flipping strategies. Run as written on 60 days of data, the single most
likely outcome is **a beautiful dashboard showing a strategy that does not
exist**.

Worth noting: the breeding prompt in this same repo (`evotrader/prompts.py`)
solves exactly this — held-out window, benchmark in the fitness function,
minimum trade counts, explicit instructions to call out luck. The author of this
prompt already owns the antidote; it just is not in this brief.

---

## 5. The ranked fix list

1. **Paste or link the strategy spec.** Entry, exit, risk, and the session it
   was designed for. One paragraph. Everything else is downstream of this.
2. **Rank the three conflicting requirements.** For example: *"Granularity
   first — if multi-year 5-minute data is unavailable, run 5-minute on whatever
   window exists and run the seasonality axis on hourly or daily bars, and label
   which is which."*
3. **Add statistical guardrails.** Minimum 30 trades per variation; report
   in-sample and out-of-sample separately; rank by the out-of-sample number;
   show the distribution of all 500, not just the top 10.
4. **State the environment instead of assuming it.** "If the TradingView MCP is
   not attached, say so in one line and use the next rung."
5. **Ask for a data-provenance line in both deliverables** — which rung, what
   date range, how many bars, how many trades. Then the PDF is auditable rather
   than just decorative.

---

## 6. Rewritten, in your voice

> Backtest the liquidity-sweep strategy from `claude/liquidity-sweeps-order-flow-9yac27`
> — [paste the entry/exit/risk rules here] — on Nasdaq futures, 5-minute bars,
> not 45-second.
>
> **Data, in order:** TradingView MCP if it is attached to this session; then
> Databento free-tier NQ futures; then NQ CFD. If a rung is unavailable, say so
> in one line and drop to the next — do not stop to ask. Report which rung you
> used, the date range, and the bar count on the first page of both deliverables.
>
> **If multi-year 5-minute data turns out to be unavailable:** run the
> intraday-session analysis on whatever 5-minute window exists, and run the
> month-to-month and year-to-year seasonality on the longest timeframe you *can*
> get. Label both clearly. Do not silently substitute one for the other.
>
> **Sessions:** the strategy spec may restrict trading to the open — ignore that
> and test around the clock. Break results out by hour, with 9–10am and 10–11am
> New York called out separately.
>
> **Seasonality:** month to month, year to year. Identify the large historical
> events that spiked volume over the period and check whether strategy
> performance correlates with them.
>
> **Variations:** build 500 of your own — EMA, VWAP, volume, day of week,
> high-impact news days, timeframe, and anything else you think is worth trying.
>
> **Guardrails, non-negotiable:** minimum 30 trades or the variation is
> reported as "insufficient data", never as a result. Split the data and rank
> variations on the out-of-sample half. Show me the distribution of all 500 —
> if the best one is not clearly outside the pack, say so plainly.
>
> **Deliverables:** a PDF and an HTML dashboard, with every variation's equity
> curve on one comparative PnL chart.
>
> You are a quantitative backtesting expert; I am not, and I will not know the
> right terminology to correct you. Choose sensible defaults, state them, and do
> not ask me to specify things I do not know how to specify. Think deeply and
> take your time.

Three additions: the spec, the requirement ranking, and the guardrails. Every
strength of the original is kept.

---

## 7. The reusable checklist

What this prompt teaches, stripped of the trading:

1. **Name the deliverable before the method.**
2. **Rank your data sources and give the fallback an explicit trigger.**
3. **Pre-resolve conflicts you can foresee** between source material and intent.
4. **Quantify creative freedom and seed the axes.**
5. **Say why you cannot answer questions**, not just that you will not — the
   reason is what licenses good defaults.
6. **Never refer to an artifact you have not attached.** "The strategy given",
   "the 45 seconds", "London strategic" — each is a pointer to something
   outside the message, and pointers plus a no-questions rule is how careful
   work ends up aimed at the wrong target.
7. **If you commission a wide search, commission the significance test with
   it.** Otherwise you have asked for the prettiest noise.
