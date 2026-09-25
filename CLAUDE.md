# Working in this repo

This branch, `claude/robinhood-trades-breakdown-1d7ev0`, holds four days of
trading research and paper bots built for the owner (Meyer), 2026-09-22 to
2026-09-25. **Read `handoff.md` first.** It covers:

- what we're doing now and the open questions for the owner;
- what runs on its own;
- everything that was found.

## Rules (keep them)

- **Paper only.** The owner: "I don't want to place my orders of my own money.
  That's not what we're doing. These are bots that were created to plug in to
  funded accounts."
  - Never place, preview or cancel real orders.
  - Never change anything in a broker account.
  - The Robinhood tools are connected; use only the read tools.
  - The Robinhood "Agentic" account (••••7873) is agent-tradable: never trade
    it, and keep the number masked.
- **No TSMX / TSM** ("it's affected by Asian politics deeply").
- **Keys:** never ask the owner to paste a token or API key into chat. Keys go
  in the environment settings as variables.
- **Git:**
  - Work on `claude/robinhood-trades-breakdown-1d7ev0`.
  - Push with `git push -u origin <branch>`, retrying at 2, 4, 8 and 16
    seconds on network errors.
  - Then mirror: `git branch -f profitable-strategies HEAD && git push origin
    profitable-strategies`.
  - Verify with `git ls-remote`. The git proxy refuses tags.
  - No pull request unless asked.
  - The repo is public: no model names in any file, and nothing private.
- **The owner's email** is for identifying them only.

## How the owner works

- Messages are short and typed fast; read for intent.
- They want a straight answer first: does it work, how much a day on $25k,
  what's the catch. The details go in the READMEs.
- They like short holds and active trading, not sitting in a position.
- Long unattended runs are normal ("I'm going to bed, don't stop"). Commit as
  you go and report an honest count at the end, even if it is zero.

## How results are reported here

- Choose rules on one span and show them on another, usually 2013-2019
  against 2020-2026.
- Show the losing stretches, not just the dollars.
- Say plainly when something doesn't work.

## In a fresh container

- `.claude/hooks/session-start.sh` installs the packages
  (`requirements-research.txt`) when a cloud session starts.
- Tests: `python -m pytest tests -q`. 408 pass, in about 100 seconds.
- The paper runs need no local data. The breakout bot's studies
  (`strategies/sweeps/`) need `bash scripts/rebuild-bot-data.sh` first. It
  takes about an hour and resumes if interrupted.
- Two routines run the paper trading on weekdays: morning levels at 12:50
  UTC and the after-close run at 21:30 UTC. They fire into one session;
  `handoff.md` section 6 says which one and how to move them.
