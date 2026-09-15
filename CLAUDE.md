# CLAUDE.md

Standing instructions for Claude sessions on this repo.

## Who is driving the session

Two people work on this repo: **Charlie** and **Meyer**. Sessions can be started
by either one.

- **Ask which of them it is at the start of every session, before doing any
  work.** Skip the question only when the current session has already made it
  clear.
- Once known, hold it for the rest of the session and attribute the work to
  that person.

### Attributing commits

Commits here are authored by `Claude <noreply@anthropic.com>` against a repo
owned by `meyer-coder`, so git history on its own does **not** say which of the
two asked for a change. Record it explicitly instead:

- Every commit message gets a trailer naming the person who requested the work:

  ```
  Requested-by: Charlie
  ```

- Never infer from git author, committer, or repo owner who wanted a change —
  that field is the same for both of them. Read the `Requested-by:` trailer, and
  when a commit predates this convention or has no trailer, say the requester is
  unknown rather than guessing.
- When summarising history ("who did what"), group by `Requested-by:`, and list
  untrailered commits separately as unattributed.

## Notes on findings

Anything that produces evidence — a backtest, a generation, a run instance —
must leave written notes on what it found. A run whose findings live only in
terminal scrollback is not finished.

- **Runs:** always pass `--note` (or set `note` in the config) describing what
  the run is testing and who asked for it. It is stored in `runs.note`.
- **Generations:** the `generations` table already has `analysis` and `lessons`
  columns. Fill them — an empty `lessons` for a generation that ran is a bug,
  not a blank.
- **Ad-hoc backtests and one-off experiments** run outside the CLI: write the
  findings to `notes/YYYY-MM-DD-<topic>.md` (see `notes/README.md`) and commit
  them alongside any code change they justify.
- Notes say what was tried, what the numbers were, what it means, and what to
  try next — not just that something ran.
