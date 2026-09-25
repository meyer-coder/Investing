# Handoff

Written 2026-09-25, about 06:00 UTC, at the end of a four-day working
session (2026-09-22 16:38 UTC to now). It covers:

- how to pick it up in a fresh container;
- what we're doing at the moment;
- the rules to follow;
- everything that was built and found;
- what runs on its own;
- what is still open.

Backtests and paper trading only; nothing here is advice.

- Repo: `meyer-coder/Investing` (public).
- Work branch: `claude/robinhood-trades-breakdown-1d7ev0`.
- Mirror branch: `profitable-strategies`.
- Last research commit: `19e952d`. This file, `CLAUDE.md` and the
  fresh-container setup came after.
- The session: https://claude.ai/code/session_016VSdEquxejKXcwEiNQPzaX

---

## 0. Picking this up in a fresh container

A new cloud session gets the repo and nothing else. The old container's
packages, data caches, scratch files and conversation don't come with it.

**Checked on 2026-09-25** with a clean checkout, no data and a freshly
installed Python:

- all the tests passed (408 then; 414 with the funded-rule tests added since);
- all six scripts of the after-close routine ran cleanly with no local data;
- the bot's minute data re-downloaded from nothing matched the original
  files exactly (91 months of the Nasdaq, 2013 to mid-2020; see section 8).

**What to do:**

1. **Start the session on this branch.** The repo's default branch
   (`claude/investing-ai-trading-omun18`) has none of this work, and
   `CLAUDE.md` only loads when it is in the checkout.
2. **Packages install themselves.** `.claude/hooks/session-start.sh` runs
   `pip install -r requirements-research.txt` when a cloud session starts.
   By hand, run the same command.
3. **Tests:** `python -m pytest tests -q` (414 pass).
4. **Data:**
   - The paper runs need none. They read `data/intraday/` and
     `data/levels/`, which are in git, and fetch the rest live.
   - The breakout bot's studies need `bash scripts/rebuild-bot-data.sh`:
     about an hour and 85 MB, resumable.
   - Other studies' caches are rebuilt, when needed, by the commands in
     each script's docstring.
5. **Routines** fire into one named session. Section 6 says how to move
   them.

**What doesn't carry over, and doesn't need to:**

- the conversation itself (this file and the READMEs are the record);
- the old container's scratch files (logs and one-off checks);
- its task list. The one open task is the options-level forward test, and
  the routines keep it running;
- `runs/evotrader.sqlite`, the breeding-run database behind the evotrader
  MCP tools. It is git-ignored; the published strategies are all in
  `profitable-strategies/`;
- 2.6 GB of research caches (above).

---

## 1. Where we are right now

**The active thread:** a futures bot that trades NQ breakouts, sized so it
survives the owner's funded-account loss limits.

1. **The ask.** The owner asked for "a bot that trades nq1 and es1 breakout
   and liquidity sweeps on large leverage". It is built and tested:
   `profitable-strategies/futures/breakout-bot/README.md`, code in
   `strategies/sweeps/`.
   - **Liquidity sweeps lost money.** About 190 versions an index,
     including ICT-style confirmation. Left out.
   - **ES added nothing.** It lost money over the last three years. Left
     out.
   - **The bot is two NQ breakouts:**
     - Bot A, the noise-area breakout: +$21 a session per MNQ since 2013,
       Sharpe 1.17;
     - Bot B, a break of the 07:00-09:29 pre-market range held to the
       close: +$11 per MNQ.
2. **The pushback.** The owner then said: "I can't lose more than 2000 on
   the 25k acc and 3 on the 100k, so these fail and wipe out instantly".
   They were right. At 1 MNQ from day one, 34-41% of funded 25K accounts
   were lost within a year.
3. **The fix** (`strategies/sweeps/funded.py`, section "Your accounts" of
   the bot README). Keep Bot A's 0.30% stop. Size each morning off the room
   above the loss limit:
   - start the 25K on NQ's signal traded in **1 MES**;
   - start the 100K on **1 MNQ**;
   - move up or down a size from the table as the room changes;
   - no Bot B on these accounts;
   - Pine: `noise_area_breakout_funded.pine` trades NQ's signal on an MES,
     MYM or MNQ chart.

   Results, on accounts started 2013-19 / 2020-25:

   | | Lost in first 3 months | Lost within a year | Challenge passed / lost | Funded $ a session |
   | --- | --- | --- | --- | --- |
   | 25K ($2,000 limit) | none | 4% / 15% | 51% / 4%, 59% / 15% | $9-13 |
   | 100K ($3,000 limit) | none | 2% / 5% | 32% / 2%, 44% / 5% | $31-38 |

   A $1,000 limit is not workable: 27-56% lost within a year, even at 1 MYM.

**Open questions for the owner.** Ask before building more on this.

- **What is the 25K's real loss limit?** The owner said $2,000.
  FundedNext's published Legacy 25K limit is $1,000 (checked on
  fundednext.com on 2026-09-22; recorded in `evotrader/prop.py`). $2,000 is
  FundedNext's 50K limit. If the account really has $1,000, the answer
  changes to "don't run this bot there".
- **Which firm and plan is each account?** Earlier the owner talked about
  FundedNext Legacy and about buying a Topstep 100K (about $130).
  - The replay assumes FundedNext's rules: the limit trails the best
    end-of-day balance and stops rising at the starting balance, and an
    intraday touch ends the account.
  - Topstep adds a daily loss limit and different consistency rules.
  - A static (non-trailing) limit would make the odds better.
- **Have the accounts been bought yet?**

**Offered to the owner, not yet answered** (don't do them without a yes):

- put Bot B (pre-market break) on the nightly paper run next to Bot A;
- paper-trade the funded-sized version (NQ signal in MES/MNQ, sized off
  the room);
- earlier offers:
  - add FBB5 (the one leveraged-fund rule with a real edge) on MUU/SOXL as
    a paper bot;
  - size the three Micron bots as one book;
  - add a crypto trend bot (BTC, BNB, AAVE, INJ, MSTR on the 50-day trend).

**Nothing heavy is running in the background.** Only the local MCP servers
(`evotrader mcp`, `evotrader tv-mcp`) are up. The full test suite result is
in section 8 (414 passed).

---

## 2. Rules to follow

Security-relevant; keep them.

- **Paper only.** The owner, verbatim: "I don't want to place my orders of
  my own money. That's not what we're doing. These are bots that were
  created to plug in to funded accounts."
  - Never place, preview or cancel real orders.
  - Never change anything in a broker account.
  - Robinhood tools are connected to this environment; don't use the order
    tools.
  - The Robinhood "Agentic" account (••••7873) is agent-tradable; never
    trade it, and keep the number masked.
- **No TSMX / TSM.** The owner: "I'd rather not ... it's affected by Asian
  politics deeply".
- **Keys and tokens.** Never ask the owner to paste a token or API key into
  chat. Keys go in the environment settings as variables (e.g. an Alpaca or
  Databento key).
- **Git:**
  - Work on `claude/robinhood-trades-breakdown-1d7ev0`.
  - Push with `git push -u origin <branch>`, retrying at 2, 4, 8 and 16
    seconds on network errors.
  - Then mirror: `git branch -f profitable-strategies HEAD && git push
    origin profitable-strategies` (the owner asked for that branch).
  - Verify pushes with `git ls-remote`; piping push output through `tail`
    hides failures.
  - The git proxy refuses tag pushes.
  - No pull request unless asked.
  - Commit messages end with the attribution trailers the harness supplies.
  - Keep model names out of every file in the repo.
- **The owner's email** is for identifying them only.
- **Reporting habits the owner has come to rely on:**
  - choose rules on one period and show them on another (usually 2013-2019
    vs 2020-2026);
  - show the losing stretches, not just the dollars;
  - say plainly when something doesn't work.

---

## 3. The owner and how they work

- **Who they are.** Meyer trades leveraged funds (MUU, RIOX, SOXL, TQQQ and
  leveraged big caps) and wants bots to run funded futures accounts (MNQ,
  MES and the like).
- **What they measure.** Dollars a day (or a session) on a $25,000 account.
- **Style.** Short holds, active trading, and leverage.
  - "Trading Micron is fine, holding it isn't."
  - They dislike strategies that mostly sit in a position.
- **How they write.** Messages are short, often dictated or typed fast
  with typos. Read for intent.
- **How they work with Claude.** They often ask for long unattended runs
  ("don't stop till ...", "I'm going to bed"). In those runs, keep working,
  commit as you go, and report an honest count at the end, even if it is
  zero.
- **What they want back.** A straight answer first: "does it work, how
  much, what's the catch". The details go in the READMEs.

---

## 4. What we did, in order

Every result below is in the repo; the folder is in brackets.

**Sep 22 (UTC)**

1. **Robinhood recap.** Broke down the owner's recent Robinhood trades
   (read-only).
2. **Quick-trade strategies for leveraged funds** (1-3 day holds, biased
   to the last six months).
   - Engine: a per-genome warm-up and trading styles.
   - Commands: `evaluate` (`--since`, `--recent`, `--daily`, by year or
     month) and `signals`.
   - Result: 14 strategies with rules, numbers and Pine
     [`profitable-strategies/` top level, `strategies/README.md`].
   - Findings:
     - the edge is in long funds after big down days;
     - inverse funds lose;
     - recent gains came from RIOX, MUU and SOXL.
   - FundedNext Futures can't trade ETFs.
3. **NQ E-mini at 2x.**
   - Built: ratio-adjusted NQ1! futures data, account leverage and island
     breeding.
   - Result: 20 strategies over 219 generations. Five average more than $85
     a session on $25k over the held-out six months; the best is Calm Trend
     Champion at $111 [`profitable-strategies/nq-2x/`].
   - The owner's 9-point stop idea was tested: 0 of 20 stayed profitable.

**Sep 23**

4. **FundedNext rule simulator** [`evotrader/prop.py`, `tests/test_prop.py`].
   - Pass and breach odds for the 20 NQ strategies: none was robustly safe.
   - Same-day engine mode (flat every afternoon, as FundedNext requires).
   - Top 10 reworked with daily stops, plus three strategies bred for the
     rules: 2 MYM + 1 MES on a Legacy 50K breached 0-12% of challenges in
     every period since 2000 [`profitable-strategies/funded/`, doc
     "FundedNext NQ Findings"].
5. **Seven-hour leveraged tech ETF grind.**
   - Real funds plus synthetic 2x/3x funds back to 2012 (`strategies/etf/`).
   - Kept 5,024 profitable strategies, 2,454 at $80+ a session.
   - Published a top 50 [`profitable-strategies/leveraged-etfs/`, doc
     "Leveraged Tech Strategies: Top 50"].
   - The recent dollars are mostly the 2026 semis rally.
6. **Paper trading.**
   - The top 3 went on paper from the Sep 23 open, with Pine alerts.
   - A three-bot split account was added (no TSMX).
   - The paper ledger and the journal doc started
     (`strategies/etf/live.py`, `strategies/etf/paper.py`).
7. **Short-hold bots.**
   - Three 1-minute SOXL bots: weak, about $26 a day together.
   - An opening-dip scalper, then the Own-Drop Scalper: $146 a day at 2x on
     one month of data [`profitable-strategies/scalping/`].
   - The Own-Drop result was later shown to be a bid-quote artifact; treat
     it as unproven.

**Sep 24**

8. **MNQ short-term research** [`strategies/mnq/`].
   - Data: six years of Nasdaq minutes and 10-second bars (Dukascopy).
   - Scanned from 10 seconds to 10 minutes: 1,074 setups, a LightGBM model,
     brackets, 08:30 releases, bursts, "wait for the bounce", round strikes,
     win-rate filters, two-bot long/short.
   - No edge anywhere.
   - Started a forward paper test of options levels (GEX walls, gamma flip)
     and a quiet-day afternoon breakout
     [`profitable-strategies/futures/options-levels/`, task still open].
9. **Overnight stock scalping** (the owner asked for 10 strategies at $200
   a day, holds of 3 minutes or less).
   - Data: four years of 1-minute bars for 72 large caps.
   - Checks: mid prices, 1-second latency and measured spreads.
   - Result: 0 of 10. The minute-bar "bounce" was the quote spread settling
     [`profitable-strategies/scalping/README.md`].
10. **Quick trades, flat every close** [`profitable-strategies/quick-trades/`].
    - Two edges held up:
      - the Nasdaq-100 noise-area breakout;
      - a gap breakout on large caps (cost-sensitive).
    - Together: $60-110 a day at 4x buying power.
    - Paper from Sep 24.
    - Also tested on 34 funds and stocks:
      - TQQQ is the Nasdaq rule times 3;
      - SOXL is weak;
      - MSTR and COIN are positive but regime-dependent.
11. **"Push the daily earnings as high as possible."**
    - Added a 0.30% resting stop to the breakout, chosen on 2013-2019:
      Sharpe 0.92 to 1.19, 13 of 14 years up.
    - Fixed sizes: TQQQ at 2x buying power is about $50 a day with a 55%
      worst stretch.
    - Optimizer-fitted sizes fail: $320 a day fitted became $15.5 on unseen
      data (`strategies/quick/maximize.py`, kept as the lesson).
12. **Top five by dollars a day, tested over 10,000+ trades each**
    [`profitable-strategies/top5/`].
    - The top five were swing trades on leveraged funds (CB51, D609, CBE3,
      852D, 01D4). None picks its days better than random entries.
    - Holding the funds did better.
    - Two edges did hold:
      - FBB5 (MUU/SOXL Uptrend Dip): +14.7 bp a trade over 41,791 trades,
        p = 0.002;
      - the Nasdaq breakout: t = 4.2 over 3,176 trades, NQ only.

**Sep 25**

13. **The last three years and the owner's pick.**
    - The last three years were led by the Micron funds: D609 $275 a day,
      CB51 $188, CBE3 $182.
    - The owner's top three are D609 (#2), CB51 (#25) and CBE3 (#18). They
      replaced the split bots on paper from Sep 25.
    - A misread ("no Micron") was corrected: trading Micron is fine.
14. **Crypto** [`profitable-strategies/crypto/`].
    - Trend and breakout rules have a real edge on 29 coins.
    - Our Micron rules don't carry over.
    - AAVE, BNB, BTC, INJ and MSTR on the 50-day trend, $5k each: $38 a day
      since 2021. They correlate only +0.16 with the Micron bots.
15. **The NQ/ES breakout and sweep bot, then the funded-limit sizing.** See
    section 1 [`profitable-strategies/futures/breakout-bot/`,
    `strategies/sweeps/`].

---

## 5. What we know

Use this to steer new work.

**What works:**

- **The Nasdaq-100 noise-area breakout.** The one intraday edge that
  survived everything (Zarattini and Aziz 2023).
  - The rule: checks every 30 minutes; out on the band or VWAP; a 0.30%
    stop; flat at the close.
  - Evidence: t = 4.2 over 13 years; found on 2020-2023 and confirmed on
    2013-2019 and 2024-2026.
  - It works on NQ only. It does nothing on ES, the Dow, the Russell, oil,
    gold, bonds or the euro.
  - Its current slump: down $5,678 per MNQ from April 2025 to February
    2026, and still $1,796 below its high.
- **FBB5 (MUU/SOXL Uptrend Dip).** The one evolved leveraged-fund rule that
  beats random timing.
- **Crypto trend and breakout rules.** Positive on 93-100% of 29 coins.
  They mostly avoid the bear markets rather than beat a bull.
- **The gap breakout** (Zarattini, Barbon and Aziz).
  - The rule: the top 3 two-percent gappers by opening-range ratio.
  - Positive, but cost-sensitive: $9-28 a day at half the measured spreads.
- **The NQ pre-market range break held to the close.**
  - Positive in both halves, but weaker (t about 1.2 before 2020).
  - It only works when held to the close; fixed 1R-3R targets lose.

**What doesn't:**

- **Liquidity sweeps**, with or without ICT confirmation, on NQ and ES.
- **Short-term MNQ** (10 seconds to 10 minutes) and **stock scalping under
  3 minutes** once priced like a bot trades.
- **Machine learning on minutes, 08:30 releases, round strikes and the
  9-point stop.**
- **Evolved leveraged-fund timing in general.** It is no better than
  random entries, except FBB5.
- **Optimizer-fitted sizes.** They look great in-sample and fail out of
  sample.

**Sizing truths:**

- **Doubling contracts doubles the dollars and the losing stretches.**
- **Growth peaks, then falls.** For the two-bot NQ book, growth peaks at
  about 5 MNQ a bot per $25k, and at that size the account falls 88% along
  the way. At 20 MNQ it is wiped out.
- **On funded evaluations, the smallest size passes most often.** Size off
  the room above the limit.

---

## 6. What runs on its own

**Routines** (Claude Code remote triggers). Both fire into one named session,
the one that has this work; `list_triggers` shows it as
`persistent_session_id`.

- **Since 2026-09-25** they fire into `session_01FUrenVPRS1PvGzMh1bieWj`,
  the fresh container. It made its own copies of both at 06:07 UTC.
- The first session's two (`trig_01TpuTXooCwvybHwDVinqUrJ`,
  `trig_01GYcmGp55fXd6oGeHtHDvK5`) are disabled, not deleted.

To move them to another session:

1. read their prompts with `get_trigger` (they are also copied verbatim in
   the appendix);
2. create the same routines bound to the new session;
3. disable the old two. Don't delete them; disabling is reversible.
   Check `list_triggers` afterwards: exactly one of each should be enabled,
   or the paper run happens twice.

| Routine | Id | When (UTC, weekdays) | What it does |
| --- | --- | --- | --- |
| Paper trading: after-close run | `trig_01SjzjqTBRXNvSqAGHuxMBpf` | 21:30 | See the list below. |
| MNQ options levels: morning snapshot | `trig_018GNJEegHjY6ZNP6cZ9kC33` | 12:50 | `strategies/mnq/levels.py --save`; commits `data/levels/`; replies with the levels |

What the after-close run does, in order:

1. `strategies/soxl/minute.py` (the day's 1-minute bars);
2. `strategies/scalp/replay.py` (the Own-Drop record);
3. `strategies/mnq/levelbot.py` and `strategies/mnq/levels.py --save`
   (the options-level test);
4. `strategies/quick/paper.py` (the quick trades);
5. `strategies/etf/paper.py` (the three fund bots);
6. updates the journal doc;
7. commits and pushes both branches;
8. replies in 2-3 lines.

Its first run with the new roster is 2026-09-25 21:30 UTC.

**The paper roster:**

- **The leveraged-fund bots.** Ledger:
  `profitable-strategies/leveraged-etfs/paper/ledger.json`. $25,000 each,
  fills at the open ±8 bp.
  - #2 D609 (MUU Trend Breakout):
    - holding MUU since the Sep 23 open at $39.23;
    - $24,034 at the Sep 24 close (−$966);
    - sells if MUU closes at or below $33.39.
  - #25 CB51 and #18 CBE3 (MUU / SOXL Uptrend Dip): start at the Sep 25
    open. The evening run books their first fills.
  - Retired, kept in the ledger: top1, top3, pick150, lowrisk100, split1-3
    and fbb5.
- **Quick trades.** `profitable-strategies/quick-trades/paper.json`, from
  Sep 24.
  - The Nasdaq breakout is booked as 2 MNQ, QQQ at 4x and TQQQ at 2x.
  - The gap breakout now uses the tested rule.
  - Sep 24: no Nasdaq trade.
  - Sep 24 gap trade: −$339 under the old biggest-gap rule; the tested
    rule would have made −$240.
- **Own-Drop Scalper.** Record only; unproven. Sep 24: −$245.
- **Options-level test on MNQ.** Sep 24: +$875 (one trade, 10 MNQ). One
  session tells us nothing yet.

**Claude Docs** (load the docs skill before editing; replacing whole blocks
needs an `ifRev` guard):

- **Paper Trading Journal: Leveraged Tech Bots.**
  https://claude.ai/artifact/ApYFTLDSqU3gNjY5iJqGvX (project
  `4f857690-324a-4367-8cef-b8f4863ab3ec`). The evening routine updates it.
  - Accounts table, orders, daily log with an AI summary and trade log.
  - Quick trades, Own-Drop and options-level tables.
- **Leveraged Tech Strategies: Top 50.**
  https://claude.ai/artifact/MAc4gzPxfVoTJDKDSV3bws
- **FundedNext NQ Findings.**
  https://claude.ai/artifact/3Pmz22ZxKnuWDf9o9feYXy

---

## 7. Repo map

**`evotrader/`**, the engine. Rule genomes are bred by an LLM; decisions
are made on the close and filled at the next open.

Added this session:

- account leverage and resting stops;
- same-day mode;
- per-symbol slippage;
- ranking of same-bar entries;
- ratio-adjusted futures from TradingView;
- `prop.py` (FundedNext replay);
- `pine.py` (genome to Pine);
- `evaluate` / `signals` commands;
- recency fitness and styles.

**`strategies/`**, the research code. Each file's docstring says how to run
it.

| Folder | What it holds |
| --- | --- |
| `quick_leveraged.json`, `recent_regime.json`, `search/`, `reports/`, `pine/` | The first ETF quick-trade set |
| `nq2x/` | The NQ 2x breeding, gauntlet, stop study and funded study |
| `funded/` | FundedNext day trades, bred sets, sessions study |
| `etf/` | The leveraged-ETF grind (`synth.py`, `islands.py`, `gauntlet.py`, `grind.py`, `publish_etf.py`), `live.py`, `paper.py` |
| `soxl/` | 1-minute SOXL bots and `minute.py` (Yahoo 1-minute archive) |
| `scalp/` | Stock scalping (Dukascopy stock minutes, panel, families, realism checks), Own-Drop |
| `mnq/` | Short-term MNQ studies, `duka.py` (Nasdaq minutes), `levels.py` / `levelbot.py` (options levels) |
| `quick/` | Index and stock quick trades: `index.py`, `indexes.py`, `trend.py` (noise-area breakout + Topstep replay), `books.py`, `paper.py`, `live.py`, `stock_orb.py`, `funds.py`, `crypto.py`, `maximize.py` |
| `top5/` | The ranking and 10,000-trade rigor tests (`rank.py`, `rigor.py`, `rigor_ndx.py`, `book.py`, `years.py`, `top3.py`) |
| `crypto/` | `study.py`, the five coins and 29-coin rules |
| `sweeps/` | The NQ/ES bot: `data.py`, `sweeps.py`, `bot.py`, `funded.py` |

**`profitable-strategies/`**, the published results, one README per area.
The top-level README lists each with its headline numbers.

- Areas: `nq-2x/`, `funded/`, `leveraged-etfs/` (with `paper/`),
  `scalping/`, `quick-trades/`, `top5/`, `crypto/`, `futures/`.
- `futures/` holds `options-levels/` and `breakout-bot/`.

**`tests/`**: pytest, run with `python -m pytest tests -q`.

**Setup:**

- `CLAUDE.md`, the rules every session here loads;
- `.claude/hooks/session-start.sh`, which installs `requirements-research.txt`;
- `scripts/rebuild-bot-data.sh`, the breakout bot's data.

---

## 8. Data (mostly not in git) and how to rebuild it

About 2.6 GB of caches sit under `data/cache/` and are git-ignored. A fresh
container has none of them.

What the current work needs is rebuilt by `bash scripts/rebuild-bot-data.sh`:

- **The Nasdaq-100 CFD, one-minute:**
  - to August 2020, `python strategies/quick/indexes.py 2013-01-01 2020-08-31 USATECH`,
    into `data/cache/duka/idx/`;
  - from September 2020, `python strategies/mnq/duka.py 2020-09-01 <today>`,
    into `data/cache/duka/months_wide/`.
- **The S&P 500 and Dow CFDs, one-minute, 2013 on:**
  `python strategies/quick/indexes.py 2013-01-01 <today> USA500 USA30`, into
  `data/cache/duka/idx/`.
- **The breakout bot's arrays:** `strategies/sweeps/data.py`'s `load()`
  builds `data/cache/quick/sweep_<NQ|ES|YM>.npz` from those.

Sources and their quirks:

- **Dukascopy's free chart service.**
  - Needs a browser User-Agent and a `Referer: https://freeserv.dukascopy.com/`
    header.
  - Returns bid prices, stamped in UTC.
  - The CFDs track the futures minute for minute, but they are not the
    futures.
  - ES is missing much of 2014 and 2017.
- **Yahoo.**
  - 1-minute bars for 30 days, 5-minute for 60 days, hourly for 2 years.
  - Today's daily bar can carry a stale open early in the session, so
    `live.py` uses the 09:30 minute.
  - Yahoo sometimes blanks the last session's daily row.
- **Nasdaq's option chain API** feeds the options levels. CBOE's delayed
  file was stale.

In git:

- `data/intraday/` (Yahoo 1-minute archive, 47 names plus NQ/MNQ);
- `data/levels/` (daily options levels).

**Rebuilt from nothing on 2026-09-25:** the Nasdaq's first 91 months came
back identical to the files the published results used, at about 7
seconds a month. The whole rebuild is about 500 months, so about an hour.

**Tests at handoff:** `python -m pytest tests -q`: 414 passed (2026-09-25, about 100 seconds), with or without the data caches.

---

## 9. Gotchas learned the hard way

- **Harness:**
  - A foreground `sleep` is blocked; use background tasks or an
    until-loop.
  - The Bash tool times out at 10 minutes.
  - `pkill -f <pattern>` can kill its own shell (exit 144); find the PID
    with `pgrep` and kill that.
- **Futures data:**
  - TradingView's continuous futures are additively back-adjusted. Convert
    to ratio adjustment before using percentages (done in
    `evotrader/data.py`).
  - Label daily bars by trading date; a session completes at 17:00 New
    York.
- **Bad data:**
  - The first AAVE and ICP bars on Yahoo aren't real prices.
  - SHIB has hundreds of zero-priced days.
  - JNPR, BK and MMC fail to fetch.
  - Dukascopy bond minutes skip unchanged minutes; fill them forward.
- **Backtest traps:**
  - A stop hit on its entry bar must be booked at the stop, not the bar's
    extreme. This was a bug in `funded.py`, fixed before its results were
    published.
  - Pre-split share prices overcharge per-share costs (`scalp/splits.py`).
  - Bid-only minute bars fake a mean-reversion edge.
  - Choosing sizes or settings on the same data you report on overfits.
    The owner has seen `maximize.py`'s $320 turn into $15.
- **Pine:**
  - The scripts have not been compiled on TradingView lately; that
    connection was down.
  - `noise_area_breakout_funded.pine` uses `request.security` to follow NQ
    from an MES, MYM or MNQ chart. Compile and paper-run it before trusting
    it.
- **Docs:** replacing whole blocks is refused with `missing_guard` unless
  the payload carries `ifRev` (the current revision).
- **A new container's first session:**
  - The evotrader MCP servers (`.mcp.json`) need numpy. They can start
    before the startup hook has installed it, and then stay down until the
    next start.
  - Optional fix: put `pip install -r requirements-research.txt` in the
    environment's setup script (environment menu, then Edit, then Setup
    script).

---

## 10. Suggested next steps

1. **Settle the account rules with the owner.** Section 1 lists the
   questions: the 25K's limit, the firm, trailing vs static. Rerun
   `strategies/sweeps/funded.py` with the real numbers; its accounts are in
   `ACCOUNTS` at the top.
2. **If they say yes:**
   - put the funded-sized Bot A on the nightly paper run, with a "room"
     column in the journal;
   - optionally add Bot B on its own account.
3. **Watch Bot A's recovery** from its April 2025 to February 2026 slump
   on the paper trail before anyone funds it.
4. **Compile and paper-run the Pine scripts:**
   - `profitable-strategies/futures/breakout-bot/noise_area_breakout_funded.pine`;
   - `pm_range_break.pine`;
   - the quick-trade scripts.
5. **Let the options-level forward test run** for weeks before judging it.
   It has one session so far.
6. **Revisit the paper roster** (#2, #25, #18) after four to eight weeks,
   not days.

---

## Appendix: the routine prompts, verbatim

Copied from `get_trigger` on 2026-09-25 (the fresh container's copies), in case the routines are ever lost.

**Paper trading: after-close run** (cron `30 21 * * 1-5`, UTC):

~~~text
After-close paper trading run for the leveraged-fund bots (the owner's top three, from 2026-09-25: #2 MUU Trend Breakout D609, #25 MUU / SOXL Uptrend Dip CB51 and #18 MUU / SOXL Uptrend Dip CBE3, each on its own $25,000), the quick trades (the Nasdaq-100 breakout and the gap breakout), the Own-Drop Scalper (kept as a record; see its caveat) and the MNQ options-level test. Paper only: never place real orders or touch any broker account.

1. In /home/user/Investing, be on branch claude/robinhood-trades-breakdown-1d7ev0 with the latest commits (git fetch origin claude/robinhood-trades-breakdown-1d7ev0; check it out and pull if needed). If `python -c "import numpy"` fails (a fresh container), run `pip install -q -e ".[dev]"` first.
2. Run `python strategies/soxl/minute.py` (adds the day's one-minute bars for the scalper's 47 names to data/intraday/; Yahoo keeps them 30 days only), then `python strategies/scalp/replay.py` (the Own-Drop Scalper's paper record in profitable-strategies/scalping/own-drop/), then `python strategies/mnq/levelbot.py` (archives MNQ=F and NQ=F minutes and replays each finished session with saved levels into profitable-strategies/futures/options-levels/), then `python strategies/mnq/levels.py --save` (after the close this writes the next session's levels to data/levels/ from the closing option chain; the morning routine keeps it if its own pre-market pull is thin), then `python strategies/quick/paper.py` (the quick trades: the Nasdaq-100 noise-area breakout on NQ=F with its 0.30% stop, booked as 2 MNQ, QQQ at 4x and TQQQ at 2x; and the gap breakout on the three large caps that opened 2% or more away whose first five minutes were widest against their own recent first five minutes, the tested rule; ledger profitable-strategies/quick-trades/paper.json, notes in profitable-strategies/quick-trades/paper/<date>.md), then `python strategies/etf/paper.py` (the three leveraged-fund bots; the split bots are retired and stay only in the ledger's "retired" list). If the ledger's updated_after_close did not move to a new session (a market holiday, or the session was still trading), commit data/intraday and data/levels if they changed and stop without messaging anyone.
3. Update the doc "Paper Trading Journal: Leveraged Tech Bots" (Claude Docs, container project 4f857690-324a-4367-8cef-b8f4863ab3ec; load the docs skill and read the doc first): replace the Accounts table and its "As of" line with `python strategies/etf/paper.py --print accounts`; replace the list under "Orders for the next open" (and its date) with `--print orders`, in plain English; replace the table under "Quick trades (paper)" with one row per recorded session from profitable-strategies/quick-trades/paper.json (session; Nasdaq trades; 2 MNQ $; TQQQ at 2x $ (tqqq_2x_usd, $0 on a day with no Nasdaq trade); gap trades as name and side; gap book $; TQQQ 2x + gap $; running total of that column); replace the table under "Own-Drop Scalper (four-minute trades)" with one row per recorded session from profitable-strategies/scalping/own-drop/paper.json (session, trades, P&L, running total); replace the table under "Options levels on MNQ (paper)" the same way from profitable-strategies/futures/options-levels/paper.json; insert a new entry at the top of the Daily log, right after its intro paragraph: "### <Day Mon D> close", then an **AI summary** of 3 to 5 sentences (what each of the three bots, the quick trades, the scalper and the level test did and why, the day's P&L, the funds' moves, what to watch at the next close), then each bot's fills and where it stands from the "Where each bot stands" part of profitable-strategies/leveraged-etfs/paper/<date>.md, the quick trades from profitable-strategies/quick-trades/paper/<date>.md, the scalper's trades from profitable-strategies/scalping/own-drop/paper/<date>.md and the level trades from profitable-strategies/futures/options-levels/paper/<date>.md; replace the Trade log body with `--print trades` once there are closed trades. Keep every other section as the user left it.
4. Commit profitable-strategies/leveraged-etfs/paper/, profitable-strategies/quick-trades/, profitable-strategies/scalping/own-drop/, profitable-strategies/futures/options-levels/, data/levels/ and data/intraday/ and push to claude/robinhood-trades-breakdown-1d7ev0, then `git branch -f profitable-strategies HEAD` and push profitable-strategies. Verify both pushes with `git ls-remote origin`.
5. Reply to the user in two or three lines: the day's paper P&L for the three bots (#2, #25, #18), the quick trades (Nasdaq breakout at TQQQ 2x and gap breakout), the scalper and the level test, and the orders for the next open.
~~~

**MNQ options levels: morning snapshot** (cron `50 12 * * 1-5`, UTC):

~~~text
Morning levels for the MNQ options-level paper test. Paper only: never place real orders or touch any broker account.

1. In /home/user/Investing, be on branch claude/robinhood-trades-breakdown-1d7ev0 with the latest commits (git fetch origin claude/robinhood-trades-breakdown-1d7ev0; check it out and pull if needed). If `python -c "import numpy"` fails (a fresh container), run `pip install -q -e ".[dev]"` first.
2. Run `python strategies/mnq/levels.py --save` (today's call wall, put wall, gamma flip and max pain from nasdaq.com's delayed QQQ option chain, in NQ points; writes data/levels/<today>.json). If it fails, retry once after a minute; if the market is closed today (a holiday or weekend), stop without messaging anyone.
3. Commit data/levels/ and push to claude/robinhood-trades-breakdown-1d7ev0, then `git branch -f profitable-strategies HEAD` and push profitable-strategies. Verify both pushes with `git ls-remote origin`.
4. Reply to the user in one or two lines: today's levels in NQ points (call wall, put wall, gamma flip, max pain) and NQ's last close, for the Pine script's inputs.
~~~
