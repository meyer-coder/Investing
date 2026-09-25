# I Backtested 10,000 Strategies: Here is the Most Profitable (5 million trades)

| | |
|---|---|
| Channel | Lil Fish (the presenter introduces himself as Luke) |
| URL | https://www.youtube.com/watch?v=XLMG6-SATRk |
| Duration | 30:21 |
| Recorded | 12 Sep 2026 (taskbar clock visible in the screen recording) |
| Watched | 25 Sep 2026 |
| Transcript source | YouTube automatic English captions (track `en-orig`). Rolling caption windows were de-duplicated and grouped into paragraphs at pauses. Timestamps are MM:SS into the video. |
| Screen source | The presenter's local dashboard, "The Million-Trade Study" (`index.html`, `dashboard.html`, `explorer.html`), read from video frames at the timestamps given |

**Caption caveats.** The captions are machine-generated and mis-hear some terms. Read "Claude Code" for "cloud code" (29:53), "prop firms" for "properforms" (17:27), "eval" for "even" (19:36), "ES and NQ" for "ES and then Q" (00:44), and "Fable 5.1 ultracode" for "fable 5.1 ultra code" (29:55). Sound tags such as [snorts] are the caption engine's.

**Data caveats.** Every number in Section 2 was read from a 1024px video frame. Small digits can be misread and the webcam overlay hides the bottom-right of every screen; unreadable values are marked "hidden". Chart bar heights and line values are marked "about". The study's own `results/strategies_ranked.csv` (named on screen at 14:50) is the authoritative table.

## Contents

1. Full transcript
2. Slides and data harvested

---

## 1. Full transcript

**[00:00]** This is something I've never shown on the internet before. This is probably two years old. It is a manual back test I did on Google Sheets. And if you look at the bottom here, there are quite a few of these. Um, and I bring this up because what I'm about to show you is the back test I did with AI where we back tested 10,000 plus strategies and 5 6 million trades. And that's only valuable if you have a point of reference. So this sheet in front of you, every day after school or every day after work, I would come home and I would open Trading View. I would do a split screen with ES and then Q. I would take my strategy. I would test it out. And each one of these [snorts] is

**[00:51]** actually annotated. So, all of these pictures are screenshots I took of Trading View because I annotated the annotated the charts. I took a screenshot. I threw it in. I took some notes on what I saw. I filled in my time of entry, my pair and the result of the trade. And I entered my little formulas so I could understand my gains and my win rates. And this is how I back tested. And this whole sheet probably took 10 to 20 hours because there's a lot of charts here and every single chart is an annotated chart. I was obsessed with learning how to trade and learning what edges would work. And so I dedicated myself to the craft.

**[01:43]** And that same dedication carries into the opportunity we have in AI. And what I'm about to show you is a 5.6 million trade back test with 10,000 strategies. And I'm going to show you the most profitable strategies of anything that's out there. The best strategies to get paid, the best to pass accounts, the best to get payouts, the highest winning, the most money-making, the highest win rates. There's strategies in here with 100% win rates. There's strategies in here with 17R as an average winning trade. And I'm going to dive deep into all of this and explain how we can actually apply this. And before I get too deep, I

**[02:36]** want to take a second and preface this video. If you don't know who I am, my name is Luke. I've been I'm known on the internet as Lil Fish. I've been day trading for over three years. I've been using AI for around four years. I've made over five figures in payouts. And this year, I started using AI to do AI assisted trading. And you'll see why that's important, how that plays with a lot of these strategies. So, that means for me, I wasn't watching the charts. I was getting notifications of valid trade setups, then using my human discretion to decide whether or not to place or skip the trade. That led me to my biggest payouts ever. And now I'm working towards fully automated trading. So Claude designs the

**[03:26]** strategy. Claude places the trades. Claude just this past week passed two funded accounts and placed a winning trade on a funded account for me. The objective here is to have AI do the entire thing and AI to be that magical money printer that we're all that we are all after. But before I kind of go into this, I really want to speak to you because I really want you to win. And if you're here to just be entertained, that's fine. You're going to see a lot of really cool stuff and a lot of interesting information that you can find useful. But information without implementation is just entertainment. And that's fine. If you're here for that, that's fine. But if you actually want to win, this is information that you should be taking notes on and applying to your edges. The only reason I am not is because I already have formulas in place that I

**[04:17]** believe are going to lead me to make more money. I'm testing these. They're in the process of working. They are leading me to pass accounts and make winning trades and getting me very close to payouts. But if you're nowhere around there, if you're totally a beginner, if you've never used AI to back test, take notes on these. These strategies are digital gold, if you will. This information, these edges of what AI was able to find in the weeds is really helpful when it comes to how you should approach algorithmic or even discretionary trading. What is the best approach out there? So, let's get into it because there's a lot of fascinating information here.

**[05:14]** So, 5.6 million trades, 10,000 strategies. This was done over seven years of data on CFD data. CFD because you can get CFD data for free. This includes futures, but just their CFD version. [clears throat] Let's get right into it. Let's let's not hesitate any longer. Here's all the information we're going to look through and then we're going to look into the best strategies out there, the highest winners, and the ones that you should use. To start off, here are the most fascinating things that I find that you can implement right now. Cost divided by stop. So, when you enter

**[06:07]** a trade with a high position and a small stop-loss, you are more likely to eat into your edge because the commissions are so high. And I get a lot of DMs of people saying, "Oh, like I have a profitable edge, but the commissions are eating away. your stop loss is too tight. And this edge, this graph here, represents that. The smaller your stop loss is, the more you're paying in commissions and the better your edge has to be in order to win. So, this is saying that a commission that is less than 3% of the stop cost is more likely to win than anything else. Which market? So, across all the assets tested, NASDAQ is a dramatic winner. And that makes sense because this is one of the most liquid if not probably I don't I haven't looked it up but this is probably the most liquid asset of any to trade.

**[06:59]** That means they're the highest volume and the most points to catch. So NASDAQ is going to be your winner. Which time frame? This is a bit of a killer because there's a lot of people who love the one minute or they love the 3 minute or they love the 302. When I was making most of my money, I never dropped below the 30 minute. The 30 minute was my executionary time frame. And really, I favored the 60 minute. And this proves that system to be true. Depending on what time frame you're using to trade, the higher the time frame, the more winning strategies there are. And that coincides with lower frequency trading because everybody loves to I'm going to trade every single day. That is not the most profitable approach. It just isn't.

**[07:49]** You will make more money if you trade less on the higher time frame. That is something I have experienced. That's how I got my payouts. I was executing on the 30-minut time frame and across 10,500 strategies. This proves that to be true even more. So, which session? Across all the sessions, London has the worst performance, second to worst, second to Asia. And again, that makes sense going along with NASDAQ because these are high volume, high liquidity times of day. And the highest performing strategies, all were New York AM session. This is the market open. This is that liquidity sweep at 9:30 a.m. that we'd love to see. Hopefully, you're already seeing a bit of a pattern here, and that's going to play into some of our best strategies.

**[08:40]** The New York AM session is the best in terms of all of these strategies combined. And I'm going to get into all of these different categories because I did not go out and hand select 10,500 different strategies. That would be ridiculous. How the stop loss is set. I found this one to be interesting because I personally for my biggest payouts was doing structure-based stop- losses. Wick low. That's where it always goes. And this suggests that to not be the best approach. Marginally, fixed stop losses. Fixed meaning no matter where I enter, I'm doing a 15 point, 50 point, 100 point stop loss. nothing else.

**[09:30]** Nothing to do with the candles, nothing to do with the volume, nothing to do with the time. That is the highest performing strategy or approach. Second to this was a surprise to me. Time. No matter when you enter, you just let it ride. Very interesting. You let it ride for 80 minutes straight or 80 candles straight and then you exit no matter what. I found that to be fascinating because that is something you never see because prop firms make it in a way where if you do that you are highly unlikely to be profitable because this strategy, this timebased exit is going to lead to dramatic winners and dramatic losers. And in the prop firm environment, you

**[10:21]** have consistency rules. You have daily loss limits that prevent those huge winners and huge losers from happening. And that appears to be one of the most profitable approaches. How you enter stop, confirm, market, limit, all are around the same with limit entries being the worst performing. These are the 50 different families of strategies. I asked for it to pick the top 50 retail strategies. And what should you immediately see from here? The groups mean cumulative R per variant. Every single one is negative. Every single one of these has a negative expectancy. This is the reason that when I made my

**[11:12]** money and I chose to build an AI assisted system, it was AI assisted and not fully automatic because I knew that from my experience, I have a discretionary edge that when I see a trade setup, I could say hm yes or hm no. And I might not always be able to put into words why I feel that way, but that decision that I make leads to the success I have with the model. Because the model I traded was, let me see if I can find it. Was this liquidity sweep and reclaim C2

**[11:51]** zero survivors with a median trade result of negative.175. This is not profitable. Like any of these, these are not profitable. And these are including the commissions, which is a crucial part of strategy. You can't disregard commissions. The people who disregard commissions and then go to the live markets are why my DMs are filled with my strategy is not profitable when I don't know why. But this is the reason that I built AI assisted. I get the notifications that I make the decision. I'm avoiding all emotional aspects. I'm shortcutting to the only part where I'm valuable, which is that decision. That being said, I am actively in the process of proving myself to be inferior to fully automatic systems built with Claude.

**[12:45]** This is what I find more interesting than anything on this dashboard, and it is how likely it is to pass a 50k eval. So, there's 10,000 strategies. 10. I like imagine that for a second. That screenshot that I showed, that Google sheet that I showed of all the different trades, that was one strategy. This did it 10,000 times. 10,000 times.

**[13:13]** And all of those strategies only.6%

**[13:20]** 60 of 10,000 strategies have greater than a 50% chance of passing. You have a 99.4% 4% chance that if you pick a strategy that is entirely automated, it is less than 50% likely to pass an account. So, choose wisely and make a decision on whether or not you want to keep yourself in the loop or not. This is why I've built systems like discretionary trainers before because I want to get better at my ability to decipher what strategies are winners or what trades are winners and what trades are losers.

**[14:16]** Look at all of these negative strategies. This should alarm you if you trade strictly algorithmic and not in a business prop manner because you need to do your due diligence in using AI or testing other strategies or using your discretion which is what I did. Now for all the strategies we can see that a lot of these have a incredible amount of trades. 11,000 trades for all of these, which is unreal. And I'm going to break down what's interesting to me here and how this plays into the proper game because some of these strategies may look freaking awesome. We're going to see that, especially when we look at average RR and some of these just

**[15:06]** freaking crush it. 31 RR as an average, that kills it. But it's a 7% win rate. You can't pass an eval with a 7% unless you do I don't know what's that's like 13 tries, 14 15 tries to pass one evaluation that has a single day pass and no consistency. So this strategy would actually suck and it only won one time. probably a huge win because the trade count matters. Net R per trade. Man, I don't even know where to start because there's just so much here that I want to I want to talk about and I want

**[15:56]** to look at because you can look at all of these at face value. And this is what's so important. I get DMs all the time of people saying like, "Hey man, I have a 60% win rate and I'm not profitable." 60% win rate alone is not anything to tell me. Like I cannot get anything from you telling me you have an epic win rate because look at all of these 100% win rates, 80% win rate strategies and none of them are profitable. You have an 84% win rate but you're losing 85 but you're losing all of these 80s that are red. 80%. That sounds great, but look at all these losers because average RR and net R per trade are crucially important. And let me really scare you here because look at how many of these are likely to pass an eval 0000.

**[16:46]** They're not even getting to 1%. Most of these 1.6% chance of passing an eval.

**[16:54]** Forget even getting a payout. You're not going to pass the account to begin with. Okay. Best trades, best strategies,

**[17:12]** total net R. These are what I think are some of the best strategies, but they're not going to work on prop firms. And you can probably already see that because properforms are stacked against you already, which trading is already stacked against you. This is even more so. So you might be able to make gains with these in the live market, but it's highly unlikely a proper market. And you can see that immediately from the win rates. Win rates under 50% are almost impossible to make money with in the proper environment because you have consistency rules. Consistency rules have only showed up in the past year or two. The consistency rule is, if you don't know what that is, it means if I make $1,000, I can't have, if I have a 50% consist

**[18:03]** consistency rule, I can't have made over 500 in a single trade. I must have taken two trades to make up that total or three trades. And so when a prop firm has instant day funding but a 20% consistency rule, that means you must have had five $200 winning days. And if you lose and you make more on one day, if you accidentally make 300 on one day, now you have to make 1,500 before you can take a payout. Consistency rules will eat you alive. And so win rates that are low and have big average wins like these, volume spike breakout is the most profitable of any strategy. 10,500 strategies. Volume spike breakout is going to give you the most money and you will not be able to pass an eval and you will not be able to

**[18:54]** get a payout. Look at these statistics. 0% 0%. Look at the P&L chart over time. Very profitable. It's clear you can't win with it in a prop firm because of this number being 14%. And this number being eight because you're making nine times the amount you risk 14% of the time. And that's awesome and that's profitable. But that is not going to comply with what's required of profs. So you can't use this

**[19:34]** Now, let's look at the ones most likely to pass an even. Notice how it's another volume spike breakout. What do we immediately see here? We see high win rate, lower risk-to-reward. Now, unfortunately, this is only 27 trades. So, this is pretty unreliable data. We need much higher trade quantities before we look to use that. But we can see here, I mean, you could set this up to give you a notification when this trade exists. And so the few times a year when this strategy exists, you should take this trade. You're going to get what 27 trades across seven years. It says 0.07 trades a week.

**[20:26]** So, what does that mean? Once every 20 weeks, two to three times a year, you're going to get one of these trade setups, and you should take it then because it's probably going to win, but uh you might have to wait an entire year to get this trade. So, if you want this criteria, here it is. Volume, spike, breakout, the family settings, the directions. How here's your entry, your stop, and your target. Here's your session, your daily flat, your maximum amount of trades per day. So, I know there's only going to be two signals a year, but if for some reason you get two per day, you could take both, but not the third. And you skip Wednesday and Friday, but we want a higher quantity. 121 New York window sweep model. Let's

**[21:18]** take a look at this one. So this this looks great on the outside, but it's been unprofitable for the past two years, and it still is a lower frequency. You're taking one trade every 3 weeks. Here's your criteria. It's in the New York open because that's when we're having most of our volume, most of our liquidity. But it's profitable if you use it in 2024.

**[21:52]** 2026. We're on a hot streak. Random control. I love that. I just clicked on this one. A random strategy with a 150 trades happens to beat 99% of strategies.

**[22:13]** What is this telling you? What information is this giving you about automated strategies? Because I'm using fully automated strategies right now to pass accounts and getting close to payouts. So, why am I getting close to payouts with complete automation when after I did a 5 million trade back test, which I didn't do before, and almost nothing is yielding positive results.

**[22:51]** I can think of two things that this is telling me. Number one, human discretion is an asset and you should use it to your advantage. And number two, I just shared a tool with my community, Ocean AI, this morning. And this tool is to calculate the probabilities of passing evals and getting payouts including the cost of evals and the size of payouts as quick as possible in a business fashion.

**[23:27]** Treating profits like a business. How do we pass and get paid without being profitable? We don't even need to have good edges in the market. We don't even need to have an edge in the market, but we can still win and get paid. The strategies I'm using to pass accounts and make money on funded accounts hardly have an edge at all. In fact, a lot of the strategies that we're looking at perform better, just less frequent.

**[24:05]** Unreal amounts of data. Unreal. Now, I show a lot of this

**[24:14]** to expand your understanding of what you can do with AI because a 5 million trade study

**[24:26]** took me one night to do. And I did smaller ones that are the reason that I'm passing accounts now.

**[24:42]** But you should look at this and you should say, "Wow, look what I can do if I take advantage of the opportunities at hand. Look what I'm able to build with these tools." because I already showed you what I had to do manually and how in an afternoon I can do 5,000x that.

**[25:10]** I hope this is just a testament to use AI to your advantage. I talked about it a lot yesterday

**[25:22]** for the video last week. AI is an enhancer.

**[25:33]** If you are lazy, you can still get these results. And they are more than the results that I who was working hard two years ago was getting. You can beat me from two years ago who is more driven in an afternoon. But I am still the same me and I am still the same driven person. And that is why I am succeeding with AI and making more than I ever have. This year I've made more money trading than I ever have. And I attribute 95% of that to my use of AI and my optimization. eliminating myself from the loop, giving more work to AI to do, and keeping the only part of me that is valuable, which is my taste.

**[26:23]** I would argue I'm working and investing myself more than ever. I was spending hours a day to get 10 trades on a manual back test. I'm still spending hours a day, but instead of 10 trades, I get 5 million. And if you want to reap the rewards that I'm reaping, you need to be that highly highly agentic person, but with the tools at hand. Because I just showed you a whole bunch of information. NASDAQ is the most profitable. New York AM session is the most profitable. Those things are true

**[27:13]** because they have the highest of volume. What does that mean? News events are likely to play into that. Small stop- losses get eaten away by commissions. Every retrail strategy is going to yield, not every 99.4% of retail strategies are going to yield negative expecties. So, do you take those strategies and approach them in the market anyways and figure out the percentages and the RRS you need to still get paid or do you add yourself in the loop and build some sort of automation where you only interact with what's valuable where you only do what gets you paid? You make the final decision all off of your taste. That's how I made most of my money in trading, my taste.

**[28:04]** eliminating the emotion.

**[28:12]** I made an entire video breaking down this back test, not this back test specifically, but back testing with one of my students on how I do this. And in my community, we're doing things like this all the time, back testing crazy amounts of edges and talking directly with students on how do we use the information that we have to get paid because that's our goal. It's fun. It's cool to look at a dashboard with a lot of green and red scare squares, but how do we get paid? How do we take this information, apply it, live test it, not spend any money until we're ready to take that risk and then get paid?

**[28:54]** If you're interested in being a part of that community, there's a link down below to apply. I only take people who are serious about it. I only take people who really want to make something and build something. I really care about my students and I really want to see them win because I've won and I know what that feels like and I want to deliver that to you. That's why I'm making these videos as well because I want to show you I want to break the mindset because so many of you guys are just going to AI and saying like make me profitable bro. [laughter] You don't think everybody else has had the same exact idea? You need to go deeper than that. You need to apply this information and connect the dots. go through phases of

**[29:45]** a systemic approach to actually get paid. This was done with cloud code using fable 5.1 ultra code and it was done in a single night and it's more trades than I could ever hope to back test. I back tested a thousand manually in my lifetime and to look at the screen that says 5.6 six million trades is absolutely unreal. AI is your opportunity to beat everyone around you. It's your competitive edge and you should be taking the absolute most advantage of it that you can.

---

## 2. Slides and data harvested

Everything below was read from the presenter's screen. The dashboard is a local site he calls **The Million-Trade Study** with tabs The sea, Six panels, Families, Does it carry?, Prop lens, Strategy cards, Fact-checker, Explorer and Dashboard. Timestamps say where each screen appears in the video.

### 2.1 Study setup (headline card, 05:04)

Headline: "10,000 strategies. 5.6 million trades. Here is what actually survives."

On-screen description: fifty ways retail trades, each run 200 different ways across eight markets, every trade resolved on 1-minute candles with rule-based fills and assumed costs (spread, slippage, commission), judged by rules written before the run, then examined on six months the strategies never saw, next to 500 strategies that trade at random. The page states that nothing on it is a recommendation.

| Stat | Value |
|---|---|
| Strategies | 10,500 (500 are random controls) |
| Trades resolved | 6,072,792 (5,648,296 training + 424,496 exam) |
| Candles | 21,726,778 one-minute candles, 8 markets, 2019 to 2026 |
| Span | 7.2 years, 2019-01 to 2026-03, then exam |
| Training window | 2019-01-01 to 2026-03-11 (explorer header, 14:38) |
| Out-of-sample window | 2026-03-12 to 2026-09-11 |
| Generated | 2026-09-12 10:51 ET |
| Survivors | 10 of 10,500 passed all gates (headline says "4 gates"; the strategy-card legend and the profile pages say "7 gates") |
| Positive out of sample | 1,065 of 6,449 strategies with 20+ exam trades (16.5%) |
| Markets | NAS100, US30, US2000, US500, XAUUSD, USOIL, XAGUSD, EURUSD (CFD data, per the presenter at 05:20) |
| Cost model | Nasdaq costed "at Micro-futures costs" (Which market panel) |
| Tooling | Presenter says Claude Code, Fable 5.1 "ultracode", one night (29:53) |

### 2.2 Six panels: one design choice each (05:56 to 10:45)

Panel intro text: each panel splits the real strategies by one design choice. Bars are the share of strategies that made money at all. The line is the median net profit per trade. Only non-inverted strategies with 50+ trades are used, 6,421 of the 10,000. The intro states that none of these choices made money on median and none is a recommendation.

Bar heights and line values below are read off the chart axes, so treat them as approximate. Strategy counts are printed on the chart.

**Cost divided by stop** (round-trip cost divided by stop distance, 06:03)

| Bucket | Strategies | % net-positive | Median net R/trade |
|---|---|---|---|
| under 0.03 | 513 | 38% (stated in text) | about -0.01 |
| 0.03 to 0.06 | 811 | about 30% | about -0.05 |
| 0.06 to 0.10 | 1,126 | about 15% | about -0.10 |
| 0.10 to 0.15 | 998 | about 7% | about -0.18 |
| 0.15 to 0.30 | 1,626 | about 4% | about -0.27 |
| over 0.30 | 1,327 | about 1% | about -0.45 |

- What this means: under 0.03 (costs eat under 3% of the stop) 38% of strategies made money; over 0.30, almost none did.
- What it implies: every point of cost is paid on every trade before the market moves. On a tight stop the ticket alone decides the outcome.
- Take away: divide your all-in round-trip cost by your stop distance. Every survivor is under 0.05. Almost half the field (46%) is over 0.15, and 95% of those strategies lost money.

**Which market** (06:41)

| Market | Strategies | % net-positive | Median net R/trade |
|---|---|---|---|
| NAS100 | 2,219 | about 24% | about -0.08 |
| US30 | 473 | about 8% | about -0.17 |
| US2000 | 681 | about 8% | about -0.20 |
| US500 | 1,032 | about 7% | about -0.24 |
| XAUUSD | 736 | about 6% | about -0.27 |
| USOIL | 508 | about 5% | about -0.30 |
| XAGUSD | 256 | about 4% | about -0.33 |
| EURUSD | 349 | about 2% | about -0.40 |

Counts here sum to 6,254, not 6,421, so at least one count label was misread.

- What this means: NAS100 is by far the least bad, and the market order almost exactly follows cost-in-R (round-trip cost divided by stop distance, the share of every stop the broker keeps). Seven of eight markets line up; only silver and crude swap places.
- What it implies: retail stop sizes are large relative to the Nasdaq ticket and tiny relative to the EURUSD ticket. Same setups, different tax.
- Take away: the market where a retail-sized stop was largest relative to the round-trip cost, Nasdaq at Micro-futures costs, lost least. No market was profitable on median.

**Which timeframe** (07:05)

| Timeframe | Strategies | % net-positive | Median net R/trade |
|---|---|---|---|
| 60m | 212 | about 28% | about -0.07 |
| 30m | 607 | about 19% | about -0.10 |
| 15m | 1,581 | about 13% | about -0.14 |
| 5m | 2,084 | about 8% | about -0.19 |
| 3m | 1,039 | about 6% | about -0.22 |
| 1m | 898 | about 3% | about -0.25 |

- What this means: the slower the candle, the less it lost; 1-minute is a graveyard.
- What it implies: faster candles mean smaller stops in points, which means a bigger cost share.
- Take away: 15 to 60-minute candles lost least and hold 9 of the 10 survivors; 1 and 3-minute candles hold none. Slower candles mean wider stops in points, so the ticket takes a smaller share.

**Which session** (08:04)

| Session | Strategies | % net-positive | Median net R/trade |
|---|---|---|---|
| NY am | 1,587 | about 14% | about -0.12 |
| NY pm | 329 | about 11% | about -0.13 |
| Ldn+NY am | 565 | about 11% | about -0.14 |
| NY | 329 | about 10% | about -0.15 |
| all | 2,809 | about 10% | about -0.16 |
| London | 455 | about 4% | about -0.19 |
| Asia | 335 | about 7% | about -0.20 |

- What this means: the New York morning lost least; London-only and Asia lost most; all-day was worse than any single US session.
- What it implies: overnight trades lose more per trade and dilute whatever the US session does.
- Take away: the New York morning (08:30 to 12:00 ET) lost least, by 0.01R over the NY afternoon and 0.08R over Asia. Four of the ten survivors trade it (rest of sentence hidden).

**How the stop is set** (08:54)

| Stop type | Strategies | % net-positive | Median net R/trade |
|---|---|---|---|
| fixed (points) | 1,909 | about 13% | about -0.12 |
| struct (structure) | 1,951 | about 11% | about -0.16 |
| atr | 2,248 | about 10% | about -0.22 |
| time | 313 | about 10% | about -0.29 |

- What this means: fixed-point stops beat ATR and structural stops. The reason is width: their median cost-in-R is 0.063 against 0.136 for (rest hidden).
- What it implies: a "candle low" on a 5-minute chart is a few points away; a few points is where the ticket eats you.
- Take away: a stop of at least 20x your round-trip cost keeps cost-in-R under 0.05. ATR stops under 2x lost most on median (1x about -0.25R, rest hidden).
- Note: the presenter reads time-based exits as the second-best approach (09:41). The chart's median line puts time last of the four; its bar (share net-positive) is level with ATR.

**How you enter** (10:35)

Bars for market, stop and confirmation entries are all near 10 to 11% net-positive. The limit bar is hidden by the webcam. Panel text: market, stop and confirmation entries are within 0.005R of each other; limit entries are worse once fills are honest. A later table on the Dashboard page (25:00) shows two of the entry rows: market, 3,519 strategies, median -0.148R; stop, 1,483 strategies, median -0.141R.

### 2.3 Fifty families, seven groups (10:48 to 12:10)

Chart subtitle: median net R per trade for each family (200 variants each), coloured by group. No family is positive on median. The order says which ideas lost least under these costs; the study did not test whether that order holds out of sample.

Groups in the legend: breakout, smart money, structure stat, trend, price action, mean reversion, vwap volume. A companion chart, "groups: mean cumulative R per variant, 2019 to 2026", shows all seven group lines falling from 0 to somewhere between about -75R and -200R by 2026. Breakout is the least negative line.

Medians and shares stated in the panel text:

| Family | Median net R/trade | % of variants net-positive |
|---|---|---|
| NR7 / inside-day expansion | -0.052R | 35.3% |
| Gap fade to prior RTH close | -0.074R | 24.7% |
| Opening range breakout | -0.078R | 12.9% |
| Gap fill after non-continuation | -0.078R | 17.6% |
| Change of character reversal | -0.092R | 15.9% |
| Liquidity sweep and reclaim (C2) (tooltip, 11:50) | -0.175R | 7.1%, 0 survivors |
| Trendline break (swing fit) (tooltip, 12:20) | -0.178R | 17.1%, 0 survivors |
| MACD cross + histogram filter | -0.190R | |
| Session high/low break and retest | -0.196R | |
| Volume climax reversal | -0.202R | |
| Delta proxy divergence | -0.218R | |
| EMA overextension fade (worst) | -0.227R | |

By group (partly hidden): breakout -0.113R, 16.7% positive; smart money 13.1%; structure stat 14.2%.

Full ranking, least bad to worst, as listed down the chart (family ID in parentheses):

1. NR7 / inside-day expansion (19)
2. Gap fade to prior RTH close (13)
3. Opening range breakout (15)
4. Gap fill after non-continuation (46)
5. Change of character reversal (26)
6. Asian range break at London/NY (16)
7. Anchored VWAP reclaim (38)
8. Displacement candle continuation (28)
9. Supertrend flip (5)
10. Two-candle momentum (36)
11. Previous day high/low break (17)
12. Donchian channel break (18)
13. Volume spike breakout (39)
14. Swing HH/HL break of structure (43)
15. Inside bar break (33)
16. Triple EMA ribbon alignment (2)
17. Breaker block (27)
18. MTF bias alignment (48)
19. Judas swing fade (30)
20. Doji at extremes (35)
21. Z-score reversion (12)
22. ADX trend-strength breakout (4)
23. Time-of-day seasonality (47)
24. Autocorrelation regime switcher (49)
25. Hull/TEMA slope turn (7)
26. Volatility squeeze release (20)
27. Round-number level reaction (50)
28. Order block retest (24)
29. Three-bar reversal (34)
30. NY window sweep model (29)
31. Bollinger touch and reclaim (8)
32. Slow-EMA trend pullback continuation (6)
33. S/R touch-count bounce (45)
34. VWAP sigma-band reversion (10)
35. RSI extreme + candle confirm (9)
36. CVD proxy trend (42)
37. Keltner channel reversion (11)
38. Liquidity sweep and reclaim (C2) (22)
39. Break of structure pullback (25)
40. Trendline break (swing fit) (44)
41. VWAP cross with slope filter (37)
42. Pin bar / rejection wick (32)
43. Engulfing at structure (31)
44. EMA crossover (1)
45. Fair value gap fill (23)
46. MACD cross + histogram filter (3)
47. Session high/low break and retest (21)
48. Volume climax reversal (40)
49. Delta proxy divergence (41)
50. EMA overextension fade (14)

Survivor counts printed beside bars that were legible: Opening range breakout 2, Change of character reversal 1, Asian range break at London/NY 2, Supertrend flip 1, Volatility squeeze release 1, Round-number level reaction 1. The other survivor labels were too small to read.

- What it implies (panel text): the least-bad ideas are daily-scale structure traded intraday, meaning yesterday's range, the opening range, a gap. They trade rarely and their stops are naturally big. The worst are indicator fades and single-candle patterns that fire often on small stops.
- Take away (panel text): if you must pick an idea, the top of this list lost least, and that is all the ranking means. "Smart-money" concepts (1 survivor of 1,800) did not beat plain breakouts (5 of 1,600). Fading the signals did not help either: every family's inverted version is negative on median, because the cost is paid in both directions.

### 2.4 Prop-firm lens (12:45 to 13:45)

Rules of the simulated evaluation (page text plus the Eval Simulator header at 25:00): every strategy with enough trades ran 2,000 simulated $50K evaluations. Reach +$3,000 before the account falls $2,000 below its highest point so far (a trailing drawdown that rises as you make money), never lose more than $1,000 in a day, and no single day may supply more than 30% of the profit. Passes then run a funded stage to a first $1,000 payout. The page notes these are one firm's rules and others differ.

**How likely is a pass?** Histogram of P(pass a $50K eval) with trailing intraday drawdown, share of strategies per bucket:

| P(pass) bucket | Share of strategies |
|---|---|
| 0 to 1% | 65.5% |
| 1 to 5% | 19.3% |
| 5 to 10% | 7.4% |
| 10 to 20% | 4.6% |
| 20 to 30% | 1.2% |
| 30 to 50% | 1.3% |
| 50 to 100% | 0.6% |

What this means (panel text): 85% of strategies would pass fewer than one simulated evaluation in twenty. The ten biggest total-profit winners hit the trailing floor in 97 to 100% of simulations. They are "lottery" curves, where a handful of huge winners carry the whole profit (win rates 12 to 49%, reward:risk 3 to 9), and a trailing floor punishes exactly that shape: every big winner given back ratchets the floor up.

**The ten biggest total-profit winners, and why they fail the evaluation** (random controls excluded from this table):

| # | Strategy | Total R | P(pass) | Why it fails |
|---|---|---|---|---|
| 1 | Volume spike breakout, NAS100 | 300 | 0.0% | drawdown breach 100% |
| 2 | Asian range break at London/NY, NAS100 | 270 | 0.0% | drawdown breach 98% |
| 3 | Triple EMA ribbon alignment, NAS100 | 213 | 0.0% | drawdown breach 100% |
| 4 | Triple EMA ribbon alignment, NAS100 | 204 | 0.3% | drawdown breach 100% |
| 5 | Opening range breakout, NAS100 | 151 | 0.0% | drawdown breach 100% |
| 6 | Judas swing fade, NAS100 | 148 | 0.0% | drawdown breach 100% |
| 7 | VWAP sigma-band reversion, NAS100 | 144 | 0.0% | drawdown breach 97% |
| 8 | Autocorrelation regime switcher, NAS100 | 131 | 0.0% | drawdown breach 100% |
| 9 | Asian range break at London/NY, NAS100 | 128 | 0.0% | drawdown breach 100% |
| 10 | Opening range breakout, NAS100 | 124 | 0.9% | drawdown breach 99% |

What it implies (panel text): among the 60 strategies simulated both ways, the trailing floor roughly halved the pass rate of big-winner, low-win-rate styles (9.9% to 4.5%, 34 strategies) and barely moved high-win-rate, small-target styles (7.9% to 7.2%, 26 strategies). Small samples, so the direction is the finding, not the decimals. Ranking by total profit picks curves that fail the evaluation as reliably as the losers do.

**The trailing-drawdown tax**

| Style | Strategies | Pass with trailing floor | Pass with fixed floor | Drawdown room the trailing floor eats per attempt |
|---|---|---|---|---|
| Big winners, low win rate (R:R at least 2, win rate at most 40%) | 34 | 4.5% | 9.9% | $898 |
| High win rate, small targets (win rate at least 55%, R:R at most 1) | 26 | 7.2% | 7.9% | $588 |

Take away (partly hidden): total profit is the wrong ranking (words hidden). Median P(pass) across survivors is about 10%.

### 2.5 The Field (14:16)

Scatter of every strategy: win rate (x, 0 to 100%) against average reward-to-risk (y, log scale 0.1 to 10), coloured by expectancy per trade from -0.3 to +0.3. Survivors glow. Two dashed break-even curves: gross, and after the median cost-in-R of 0.126. Toggles: NET or GROSS, show or hide controls.

| Stat | Value |
|---|---|
| The field | 10,000 |
| Survivors | 10 |
| Gross-positive | 4,126 |
| Net-positive | 1,0xx (last digits hidden) |

The picture: an orange cloud along and below the break-even curve, with the few green survivors sitting just above the after-cost curve between roughly 35% and 80% win rate.

### 2.6 Regime survival (24:45)

"Where the 2022 winners went, and where the survivors were in 2022."

| Stat | Value |
|---|---|
| 2022 winners | 1,178 |
| Still winning in 2025 to 26 | 216 |
| Dead by 2025 to 26 | 962 |
| Survivors | 10 |
| Survivors that lost in 2022 | 4 |

A Sankey below it routes 2022 losers and 2022 winners into dead 2025 to 26, winning 2025 to 26, non-survivors and survivors. A neighbouring "mean net R per trade by day regime" chart shows negative bars for every regime (labels trend, chop, high vol, low vol). An "Exit Showdown" block on the same page plots median net expectancy by take-profit type, entry type, trailing rule and stop type; every bar is negative, in the -0.1R to -0.2R range.

### 2.7 The Eval Simulator (25:00)

"2,000 block-bootstrapped $50K evaluations per survivor: $3,000 target, $2,000 drawdown, $1,000 daily loss, 30% consistency." Tabs: trailing (intraday), trailing (EOD), static. The chart shows 200 simulated evaluation paths for strategy 20-122 with the median path and the median trailing floor. The median path reaches about $51K while the floor ratchets from $48K to about $49.2K.

| Stat | Value |
|---|---|
| Median P(pass) across survivors, trailing drawdown | 10.1% |
| High R:R, low win rate (R:R at least 2, win rate at most 40%): P(pass) trailing intraday | 4.5% |
| Same group: P(pass) static | 9.9% |
| Same group: trailing-drawdown tax per attempt | $898 |

### 2.8 Strategy cards legend (05:43, 12:20)

Every strategy gets the same card: equity in dollars at $250 risk per trade, the underwater curve, the losing-run histogram, and the stats a prop-firm evaluation tests. Badges: SURVIVOR = passed all 7 gates; POSITIVE, UNPROVEN = made money in training but failed at least one gate; MARGINAL = barely positive; LOTTERY = positive only thanks to its best 5% of trades; GROSS ONLY = positive before costs only; DEAD = lost money; CONTROL = random signals. Sharpe and Sortino are return per unit of swing and per unit of downside swing; profit factor is dollars won divided by dollars lost.

### 2.9 Explorer: sorted views (14:38 to 17:20, 24:10)

The Explorer is a 53-page table of all 10,500 strategies with filters for market, timeframe, group, family, session, entry, stop, target, minimum trades and max trades per week. Columns: ID, family, market, TF, session, trades, per week, win %, avg RR, net R/trade, gross R/trade, total net R, $ at $250 risk, max DD (R), cost-in-R, last 12M net R, out-of-sample 6M, P(pass eval), P(payout), P(DD breach), entry, stop, target, max/day, verdict. Footer: `results/strategies_ranked.csv` has the same table.

**Sorted by trade count** (14:50). The busiest strategies run about 11,000 trades over the window and are all deeply negative.

| ID | Family | Market, TF | Trades | Win % | Net R/trade | Total net R | $ at $250 risk |
|---|---|---|---|---|---|---|---|
| 36-152 | Two-candle momentum | US500 1m | 11,110 | 17% | -0.689R | -7,652 | -$1,892,407 |
| 01-001 | EMA crossover | NAS100 1m | 11,040 | 38% | -0.417R | -4,605 | -$1,133,292 |
| 22-011 | Liquidity sweep and reclaim (C2) | USOIL 5m | 10,857 | 17% | -0.612R | -6,644 | -$1,629,655 |

**Sorted by average R:R** (15:20). The top row is the one the presenter calls out at 15:06.

| ID | Family | Market, TF | Trades | Win % | Avg RR | Net R/trade | Total net R | P(pass) |
|---|---|---|---|---|---|---|---|---|
| 30-159 | Judas swing fade | NAS100 1m | 31 | 7% | 31.48 | +1.349R | 42 | 0.0% |
| 17-058 | Previous day high/low break | NAS100 5m | 71 | 4% | 22.58 | -0.004R | 0 | 0.0% |
| 13-193 | Gap fade to prior RTH close | NAS100 1m | 84 | 5% | 19.88 | -0.008R | -1 | 0.0% |
| 08-081 | Bollinger touch and reclaim | NAS100 1m | 412 | 6% | 17.45 | +0.220R | 91 | 0.0% |
| CTRL-306 | RANDOM control | NAS100 15m | 176 | 7% | 16.10 | +0.198R | 52 | |

**Sorted by net R per trade** (16:00 to 16:50). Every top row is a 100% win rate strategy with one trade (for example EMA crossover, EURUSD 3m, 1 trade, +3.944R). Further down are 80%+ win rates with single-digit trade counts and dollar totals between $56 and $446. The presenter's point at 16:00: a win rate on its own says nothing.

**Sorted by total net R** (17:10), top ten. All NAS100.

| Rank | ID | Family | TF, session | Trades | Per week | Win % | Avg RR | Net R/trade | Total net R | $ at $250 risk | Max DD (R) | Cost-in-R | Last 12M R (trades) | OOS 6M R/trade (trades) | P(pass) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 39-113 | Volume spike breakout | 15m, NY am | 657 | 1.75 | 14% | 8.88 | +0.457R | 300 | $72,047 | 71 | 0.084 | 119.9 (155) | +1.154R (59) | 0.0% |
| 2 | 16-113 | Asian range break at London/NY | 15m, London | 1,110 | 2.96 | 49% | 1.12 | +0.244R | 270 | $71,904 | 184 | 0.084 | -57.5 (151) | -0.350R (75) | 0.0% |
| 3 | 02-154 | Triple EMA ribbon alignment | 3m, NY am | 1,374 | 3.66 | 19% | 5.16 | +0.155R | 213 | $51,044 | 50 | 0.063 | -28.8 (199) | -0.668R (100) | 0.0% |
| 4 | 02-157 | Triple EMA ribbon alignment | 5m, NY am | 1,202 | 3.2 | 25% | 3.7 | +0.169R | 204 | $46,525 | 62 | 0.063 | 21 (163) | -0.306R (83) | 0.3% |
| 5 | CTRL-309 | RANDOM control | 15m, NY am | 396 | 1.06 | 24% | 5.09 | +0.477R | 189 | $45,846 | 26 | 0.122 | -27 (66) | -0.365R (35) | 0.0% |
| 6 | 15-098 | Opening range breakout | 5m, all | 566 | 1.51 | 12% | 9.43 | +0.267R | 151 | $35,880 | 51 | 0.042 | -1.6 (77) | +0.084R (40) | 0.0% |
| 7 | 30-042 | Judas swing fade | 1m, all | 1,076 | 2.87 | 14% | 7.29 | +0.138R | 148 | $34,029 | 74 | 0.102 | 16.8 (74) | +0.038R (81) | 0.0% |
| 8 | 10-195 | VWAP sigma-band reversion | 15m, NY am | 525 | 1.4 | 16% | 6.59 | +0.275R | 144 | $33,739 | 57 | 0.126 | | | |
| 9 | 49-195 | Autocorrelation regime switcher | 15m, Ldn+NY am | 507 | 1.35 | 13% | 8.74 | +0.258R | 131 | $31,344 | 45 | 0.125 | | | |
| 10 | 16-006 | Asian range break at London/NY | 15m, London | 1,773 | 4.72 | 44% | 1.14 | +0.072R | 128 | $30,793 | 84 | 0.063 | | | |

Rows 11 to 21 are four more Opening range breakout variants (5m and 15m, 90 to 124R), Change of character reversal (3m NY pm, 94R), Asian range break 30m (94R), Bollinger touch and reclaim 1m (91R, 6% win, 17.45 RR), two Anchored VWAP reclaim variants (85 to 88R), Displacement candle continuation 30m (86R) and one US500 S/R touch-count bounce 15m (86R).

A random-signal control sits at rank 5 by total profit. The presenter does not point this out; he opens a different control at 21:56.

**Sorted by P(pass eval)** (19:45), top ten. Every row has 20 to 40 trades except the last.

| Rank | ID | Family | Market, TF, session | Trades | Per week | Win % | Avg RR | Net R/trade | Total net R | $ at $250 risk | Max DD (R) | Cost-in-R | P(pass) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 39-169 | Volume spike breakout | NAS100 15m, NY pm | 27 | 0.07 | 78% | 0.86 | +0.481R | 13 | $2,654 | 2 | 0.057 | 100.0% |
| 2 | 12-064 | Z-score reversion | US30 15m, all | 28 | 0.08 | 68% | 1.49 | +0.632R | 18 | $4,112 | 3 | 0.066 | 99.6% |
| 3 | 50-085 | Round-number level reaction | NAS100 60m, all | 39 | 0.1 | 62% | 0.73 | +0.299R | 12 | $2,942 | 3 | 0.038 | 98.4% |
| 4 | 49-112 | Autocorrelation regime switcher | NAS100 15m, all | 26 | 0.06 | 54% | 2.41 | +0.489R | 12 | $2,559 | 6 | 0.028 | 96.7% |
| 5 | 05-069 | Supertrend flip | NAS100 60m, NY am | 23 | 0.06 | 70% | 0.78 | +0.386R | 9 | $2,209 | 4 | 0.019 | 96.6% |
| 6 | 42-127 | CVD proxy trend | US500 15m, NY am | 21 | 0.06 | 52% | 2.29 | +0.668R | 14 | $3,173 | 3 | 0.122 | 96.4% |
| 7 | 42-013 | CVD proxy trend | XAUUSD 15m, NY am | 20 | 0.05 | 65% | 1.45 | +0.447R | 9 | $2,094 | 3 | 0.089 | 93.8% |
| 8 | 13-133 | Gap fade to prior RTH close | US2000 30m, all | 26 | 0.07 | 48% | 1.79 | +0.245R | 6 | $1,267 | 3 | 0.07 | 93.8% |
| 9 | 44-028 | Trendline break (swing fit) | NAS100 15m, all | 25 | 0.07 | 48% | 3.3 | +1.102R | 28 | $6,209 | 5 | 0.043 | |
| 10 | 13-142 | Gap fade to prior RTH close | NAS100 15m, all | 84 | 0.22 | 50% | 2.25 | +0.516R | 43 | $10,548 | 6 | 0.02 | |

By the bottom of page 1 of this sort (24:10) P(pass) has fallen to 26.6 to 28.7%, P(payout) to 15.7 to 23.7%, and the verdict column reads mostly "lottery" with some "positive_unproven" and "control".

### 2.10 Strategy profiles opened in the video

**Volume spike breakout, NAS100 15m, ID 39-113** (18:34). Group vwap volume. Rank 1 of 10,500 by total net R. Verdict: lottery.

| Stat | Value |
|---|---|
| Net per trade | +0.457R |
| Trades | 657 (1.75 per week) |
| Win rate | 14% |
| Avg reward:risk | 8.88 |
| Total net | 300R ($72,047 at $250 risk) |
| Max drawdown | 71R (37 losses in a row) |
| Cost-in-R (round trip divided by stop) | 0.084 |
| Weeks with a trade | 78% (400 min avg hold) |
| P(pass $50K eval) | 0.0% |
| P(first payout) | 0.0% |
| P(drawdown breach) | 100% |
| Gross per trade (before costs) | +0.541R |
| Last 12 months (2025-09-12 to 2026-09-11) | 119.9R, 155 trades, $28,776, 9% win rate |

Rule labels visible: Signal, Family settings, Direction, Entry, Stop, Target, Time stop ("exit after ..."), Session (New York morning). Values are hidden by the webcam.

**Volume spike breakout, NAS100 15m, ID 39-169** (19:34 to 21:10). Group vwap volume. Rank 377 of 10,500 by total net R. Verdict: positive_unproven. This is the "most likely to pass" strategy.

| Stat | Value |
|---|---|
| Net per trade | +0.481R |
| Trades | 27 (0.07 per week) |
| Win rate | 78% |
| Avg reward:risk | 0.86 |
| Total net | 13R ($2,654 at $250 risk) |
| Max drawdown | 2R (2 losses in a row) |
| Cost-in-R | 0.057 |
| Weeks with a trade | 6% (26 min avg hold) |
| P(pass $50K eval) | 100.0% |
| P(first payout) | 100.0% |
| P(drawdown breach) | 0% (24 days to pass) |
| Gross per trade | +0.538R |
| Last 12 months | 6.7R, 9 trades, $1,329, 89% win rate |

Rules in plain English, as printed on the card:

| Rule | Value |
|---|---|
| Signal | Volume-spike breakout: a candle with volume several times its average that also closes above the recent high |
| Family settings | vol_mult = 2.5, vol_n = 50, k = 10 |
| Direction | long and short |
| Entry | Limit order at a 50% pullback into the signal move, cancelled if not filled within 10 candles |
| Stop | 1 x ATR(14) of the trade timeframe |
| Target | 1 x ATR(14) |
| Session | New York afternoon only (12:00 to 16:00 ET) |
| Daily flat | flat by 15:59 ET every day |
| Max trades/day | 2 |
| Filters | skips Wed/Fri |

The equity curve (cumulative net R, weekly) steps up to about 13R over the seven years. The "where the trades ended" row reads 22% / 74% / 4% (stop / target / time, labels partly hidden). The presenter's reading (19:53): 27 trades is unreliable data, roughly one signal every 20 weeks, so use it as an alert rather than a system.

**NY window sweep model, NAS100 5m, ID 29-131** (21:14 to 21:55). Explorer row 91.

| Stat | Value |
|---|---|
| Trades | 121 (0.32 per week) |
| Win rate | 42% |
| Avg reward:risk | 2.62 |
| Net per trade | about +0.34R (41R over 121 trades; the printed cell was hard to read) |
| Gross per trade | +0.386R |
| Total net | 41R |
| Longs / shorts | +0.417R / +0.272R per trade |
| Where trades ended | 22% stop, 21% target, rest hidden |
| Robustness | top-5% share of profit 0.51 |
| Gates | "The seven gates (+ frequency guard)": at least 100 trades, ticked |

Rules on the card:

| Rule | Value |
|---|---|
| Stop | 2 x ATR(14) of the trade timeframe |
| Target | 3R (that multiple of the stop distance) |
| Trailing | exit when a candle closes beyond the 20 EMA against the trade |
| Session | New York (08:30 to 16:00 ET) |
| Daily flat | flat by 15:59 ET every day |
| Max trades/day | 6 |
| Filters | only when volume is at least 1.5x its 20-candle average; only when ADX(14) is above 30 |

Equity by year: roughly flat in 2019, climbing to about 38R by 2024, sagging through 2025, then 41.3R at January 2026 (tooltip). Expectancy-by-year bars: 21 trades in 2019, 17 in 2020, 18 in 2021, 19 in 2022, all positive; the 2025 bar is negative. The presenter's reading (21:22): looks great on the outside but unprofitable for the past two years, one trade every three weeks, on a hot streak in 2026.

**RANDOM control, US2000 15m, ID CTRL-299** (21:56). Rank 140 of 10,500 by total net R. Verdict: control, random-signal control.

| Stat | Value |
|---|---|
| Net per trade | +0.198R |
| Trades | 154 (0.42 per week) |
| Win rate | 70% |
| Avg reward:risk | 0.63 |
| Total net | 30R ($7,326 at $250 risk) |
| Max drawdown | 7R (3 losses in a row) |
| Cost-in-R | 0.119 |
| Weeks with a trade | 28% (66 min avg hold) |
| P(pass $50K eval) | 49.1% |
| P(first payout) | 39.4% |
| P(drawdown breach) | 40% (32 days to pass) |
| Gross per trade | +0.317R |
| Last 12 months | -4.3R, 16 trades, -$932, 56% win rate |

Rule labels visible: Target 2R, Trailing, Partial ("take half ..."), Time stop ("exit after 40 candles"), others hidden. The presenter's reading (22:03): a random strategy with 150 trades beats 99% of strategies.

### 2.11 Presenter's own conclusions (from speech, 22:51 to 30:21)

- Two readings of the result: human discretion is an asset, and prop-firm evals can be treated as a business using pass and payout probabilities plus eval cost, without needing a market edge (22:51 to 23:45).
- He trades AI-assisted (alerts, then his own decision) and says that produced his biggest payouts (03:05, 12:19).
- He is also running fully automated Claude-built strategies that "hardly have an edge at all" and recently passed two funded accounts (03:24, 23:45).
- The study was built with Claude Code in one night; he says he back-tested about a thousand trades by hand in his lifetime (29:53).
