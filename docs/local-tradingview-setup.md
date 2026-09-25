# Running your own TradingView tunnel on macOS

Five steps per machine. Identical on the Mac mini and the MacBook Air.

The hosted `claude.ai TradingView` connector is account-level — it already
works on every machine you log into, and needs no install. This local server
exists for the things that one cannot do: raise the 1000-bar cap, use your own
TradingView plan, include pre/post-market, and remove the remote host that
returned a 502.

---

## Step 1 — install the dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install mcp pandas
python3 -m pip install --upgrade --no-cache-dir \
  git+https://github.com/rongardF/tvdatafeed.git
```

`tvdatafeed` is not on PyPI, which is why it installs from GitHub.

If `python3` is missing, install Homebrew from https://brew.sh then `brew install python`.

## Step 2 — get the server file

```bash
cd ~
git clone https://github.com/meyer-coder/Investing.git
cd Investing
git checkout claude/hopeful-euler-ffpye9
```

The server is `scripts/tradingview_mcp_server.py`. If you already have the repo,
`git pull` instead.

## Step 3 — add your TradingView login

This is the step that matters most. Without it the server connects anonymously
and gets the free tier's 5,000-bar cap no matter what you pay TradingView.

```bash
cat >> ~/.zshrc <<'EOS'
export TV_USERNAME="your_tradingview_username"
export TV_PASSWORD="your_tradingview_password"
EOS
source ~/.zshrc
```

`~/.zshrc` is a local file and is never committed. Keep credentials out of the
repository.

## Step 4 — register it with Claude Code

```bash
claude mcp add tradingview-local -- python3 ~/Investing/scripts/tradingview_mcp_server.py
```

Use the real absolute path if you cloned somewhere else. Add `--scope user` to
make it available in every project on that machine rather than just this one.

## Step 5 — restart and test

Quit Claude Code completely, reopen it, then:

```
/mcp
```

`tradingview-local` should be listed as connected. Then ask Claude to run the
`status` tool. It reports whether the login took effect and what the limits are.

Then a real test:

> pull 5000 5-minute bars of CME_MINI:NQ1!

Roughly 18 trading days means it worked. Roughly 4 days means you are still on
1000 somewhere. If the reply says you got fewer bars than requested, that is
your TradingView plan's ceiling, and the server says so explicitly.

---

## Doing the second machine

Repeat steps 1-5. Nothing is shared between machines — each needs its own
install, its own credentials in its own `~/.zshrc`, and its own `claude mcp add`.

The one thing that IS shared is the hosted `claude.ai TradingView` connector,
which follows your account automatically.

## What you end up with

Both servers, side by side, and that is fine:

| | Hosted `claude.ai TradingView` | `tradingview-local` |
|---|---|---|
| Setup | none, follows your account | 5 steps per machine |
| Max bars | 1000 | 5000, or your plan's cap |
| Pre/post-market equities | no | yes |
| Uses your TV plan | apparently not | yes, once step 3 is done |
| Can 502 | yes, it did | no, it runs locally |
| Screener, quotes, technicals | yes | no — bars and search only |

Keep both. Use the hosted one for screening and live quotes; use the local one
for pulling bars.

## Limits worth stating plainly

Fixing the cap does not make this a deep-history source. TradingView limits bars
by plan — Basic 5,000, Essential 10,000, Plus 10,000, Premium 20,000, Ultimate
40,000 — and at 5m that is 18 to 145 trading days of NQ. Ten years of 5-minute
NQ is ~695,000 bars, so even the top plan reaches under 6% of it.

Use this for recent intraday context and 4 years of daily bars. Use Databento
files for deep history (`scripts/fetch_databento.py`).

## If it breaks

`tvdatafeed` works by talking to TradingView's chart feed, which changes without
notice. If it stops working, reinstall it first:

```bash
python3 -m pip install --upgrade --no-cache-dir --force-reinstall \
  git+https://github.com/rongardF/tvdatafeed.git
```

To remove the server entirely: `claude mcp remove tradingview-local`
