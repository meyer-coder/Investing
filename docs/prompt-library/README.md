# Prompt library — day-trading agent research briefs

Eight ready-to-paste briefs, one per market, each built on
`00-master-template.md` and each carrying a **different strategy family**. They
are not ticker swaps: a mean-reversion brief for ES and a momentum brief for NQ
are different research programmes, because the instruments behave differently.

## How these markets were chosen

Ranked on what actually determines whether a day-trading agent can earn money,
rather than on how exciting the market looks:

| Criterion | Why it decides the outcome |
|---|---|
| **Cost per unit of range** | The only ratio that matters. Spread + commission divided by average move. A market can be wildly volatile and still untradeable. |
| **Data availability** | You cannot evolve agents on data you cannot get. This is the #1 practical filter and the reason crypto ranks first. |
| **Realized intraday volatility** | Sets the size of the available edge. |
| **Session structure** | Repeatable daily catalysts (opens, releases, settlements) create repeatable setups. Structureless markets offer fewer. |
| **Strategy diversity** | How many genuinely distinct edges coexist. Determines how large an agent fleet can be before agents are just correlated copies. |
| **Capital efficiency** | Leverage and minimum contract size decide whether a small account can act on the edge. |
| **Parallelism** | 24/7 markets let a fleet work continuously; session markets idle most of the day. |

## The ranking

| # | Market | File | Strategy family | Why it earns a slot |
|---|---|---|---|---|
| 1 | **Crypto perps** | `04-crypto-perps.md` | Momentum + funding carry + liquidation fade | Best data on earth (free, complete, tick-level, from the exchange itself), 24/7, no roll, no session gaps, native short. The single best environment for an agent fleet. |
| 2 | **NQ futures** | `01-nq-futures.md` | Opening-range / momentum continuation | Highest ATR% of the major index futures. Strong, repeatable open. Your original market. |
| 3 | **ES futures** | `02-es-futures.md` | VWAP mean reversion | Deepest book in the world, 1-tick spread almost always. Behaves *differently* from NQ — more mean-reverting — so it diversifies a fleet rather than duplicating it. |
| 4 | **CL crude oil** | `03-cl-crude.md` | Scheduled-event reaction | Highest ATR% of the liquid futures, plus a hard weekly catalyst (EIA, Wed 10:30 ET) that creates a genuinely repeatable event edge. |
| 5 | **FX majors** | `05-fx-london.md` | Session-boundary breakout | Lowest friction of any market, 24/5, and the cleanest session structure that exists (Asian range → London open → NY overlap). |
| 6 | **Gold** | `06-gold.md` | Macro-release reaction | Reacts violently and quickly to CPI/FOMC/NFP. A pure event-reaction fleet with low correlation to equity-index agents. |
| 7 | **Small-cap equities** | `07-smallcap-gap.md` | Cross-sectional gap-and-go | By far the largest per-trade moves (20–200% days) and a screener that supplies fresh candidates daily. Hardest data and hardest execution — high ceiling, high difficulty. |
| 8 | **SPX 0DTE options** | `08-spx-0dte.md` | Defined-risk premium selling | The most *distinct* family here — the edge is structural (theta, variance risk premium), not directional. Lowest correlation to everything else in the fleet. |

## Deliberately excluded

- **Low-float pre-IPO / OTC** — unbacktestable fills, no borrow, no reliable data.
- **Exotic FX crosses** — spread consumes the extra volatility.
- **Single-stock options below mega-cap** — spreads too wide for intraday round trips.
- **Anything with < 2 years of obtainable intraday data** — cannot be validated.

## Build order, if you are building a fleet

1. **Crypto perps** first. Free complete data means you can debug the whole
   pipeline — acquisition, variant search, walk-forward, reporting — with no
   data cost and no roll logic. Get the machinery right here.
2. **ES or NQ** second. Introduces roll handling, session gating and futures
   cost modelling, on top of a pipeline you already trust.
3. **CL or Gold** third. Introduces the event calendar.
4. **Small caps / 0DTE** last. Both need infrastructure the first three build.

Run agents from at least three different files before allocating real capital.
Ten agents on one market are one position, not a portfolio — see §13 of the
master template.
