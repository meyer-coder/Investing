# I Used AI To Increase My Win-Rate (AI Daytrading Masterclass)

| | |
|---|---|
| Channel | Lil Fish (the presenter introduces himself as Luke at 00:34) |
| URL | https://www.youtube.com/watch?v=fi--3nBHsNg |
| Duration | 56:46 |
| Recorded | Sat 19 Sep 2026 (he says "today is September 19th or 20th" at 48:00 and "it's a Saturday" at 54:34; uploaded 21 Sep 2026) |
| Watched | 25 Sep 2026 |
| Transcript source | YouTube automatic English captions (track `en-orig`). Rolling caption windows were de-duplicated and grouped into paragraphs at pauses. Timestamps are MM:SS into the video. |
| Screen source | A whiteboard the presenter writes on for the whole video. Read from 512px video frames sampled every 13 s (00:00 to 22:15) and every 21 s (22:15 to 56:26). |

**Caption caveats.** The captions are machine-generated and mis-hear some terms. Read "Claude Code" for "cloud code" (07:26), "prop firms" for "profirms" (08:36), "prof firms" (07:01) and "properforms" (54:01), "VWAP" for "VWOP" (26:47, 32:38), "when to test" for "pointed test" (00:47), "Asia session" for "Asia recession" (29:02), "full-port" for "fullport" (18:36), "cat poem" for "cap home" (49:18, 49:22), "evals" for "Eboss" (47:49), "Codex" for "Codeex" (49:50), "Opus 5" for "Oopus 5" (50:49) and "$1,000" for "a,000" (12:54). "Grab your STEMIs" (00:57) is unclear in the audio. Sound tags such as [snorts] are the caption engine's.

**Data caveats.** Everything in Section 2 is hand-written on a whiteboard and was read from 512px frames. Digits written in a hurry are marked "reads as". Where the spoken figure and the board disagree, both are given. The presenter's own arithmetic in the funded-stage consistency example goes wrong on camera and he says so (21:10); those numbers are recorded as written, not corrected.

## Contents

1. Full transcript
2. Slides and data harvested

---

## 1. Full transcript

**[00:14]** You know about AI. You've seen everyone using it. I'm using it for my day trading and it is improving my win rate and is helping me make more money. And that's what this video is for. This is going to be a value dump of loads of information that I've picked up, not only through other people, but through my own experience. If you don't know who I am, my name is Luke. I've been trading for over three years. I've been using AI for over four years, and I have over five figures in day trading payouts. I'm going to go over myths, vocab, reframe, variation searching, pointed test, prop clustering, which AIS to use, and your order of operations to implement everything you've learned. This is going to be a value dump. So, grab your STEMIs, grab your notebook, and get ready to take some notes because I'm going to give you as much value as possible so you can learn, implement, and get paid. That's what I want for you.

**[01:11]** myths. High win rate equals a good strategy. I get DMs all the time of people saying, "I have this win rate. I have a 60% 70% 80% 90% win rate." That does not matter. It's common in the space to see someone come out and say, "Oh, I have this 80 or 90% win rate." But a 90% win rate doesn't mean anything without risk-to-reward. Let me give you a very clear example. Someone might say, "I have a 90% win rate." But 80% of the time

**[01:50]** they go break even, so they make no money, but they call it a win because they didn't lose. 10% of the time they win, and maybe they win a onetoone trade. and then 10% of the time they lose a one to one trade. So actually a 90% win rate strategy that goes break even 80% of the time wins 10% and loses 10% is not profitable at all. On the flip side, if I even have a 55%

**[02:31]** win rate and I win 55% of my trades, not break even, actually winning 55% of the time, a onetoone trade, and I lose 45% of the time, a onetoone trade.

**[02:53]** This is more profitable. So just because you have a high win rate does not mean you have a good strategy. People online will be very foggy about what their win rate actually is because they will classify break even trades as wins because they simply didn't lose. So no, a high win rate does not mean you have a good strategy. Riskto-reward is essential because even if I change this to just one to two now this is better

**[03:24]** AI will find me a profitable strategy. I have in the past two weeks back tested 20,000 different strategies and taken around 17 no sorry 13 million trades. 13 million trades. Yes, there are profitable strategies in there. Some of which I'm implementing starting this week. It can do that for

**[03:54]** More historical data [snorts] is better. No, it's not better. And we'll get more into that on when to test. But if I find a profitable strategy from 2020 and it's profitable for three years straight, but it made no money in 2024, 2025, 2026 when the new regime hit, that means nothing. You can't make money with a strategy that's not making money anymore. So, no, more historical data is not always better. Why are you back testing back to 2010? The market doesn't move like that

**[04:39]** Profitable and back test means profitable and live. No, because again I can have a strategy that is profitable for a series of years in a row. Let's draw this out. Here's our P&L over time. Here's 2026

**[05:01]** and here is we'll say 2016, right? So from 2016 to 2026 we do this. So we made a lot of money up until about 2021 and then we were break even or maybe even on a decline for the past five years. But if you look at simply the average of the decade,

**[05:36]** it looks profitable, but you don't know it's profitable anymore unless you're getting live results. So more and more I'm actually having a strong recency bias. Is it profitable within the last six months? Because if you've looked at the market for more than the month, you know that it's changing quick.

**[06:02]** Strategy is the hardest part. Not anymore. I would argue that it was when we had limited resources and information was guarded and it was protected and you had to buy people's courses to figure out what they were doing and learn like what's your secret sauce but you can find any strategy. Do you really think that I came up personally with 10,000 strategies or did I just go to Claude and say do some research for me? Strategy is no longer the hardest part anymore. We can find good strategies really easily. Tons of my students are killing it. Finding amazing strategies. It is a game of implementation and knowing the game. Because just because you can find a good strategy does not mean you can make money with it, particularly with prop firms. Prof firms are a different game than normal day trading with your live capital because most people don't do that. I traded with my life capital this summer. It was a very different game than it was with prop firms.

**[07:18]** Do I need to learn to code to use AI? Nope. That's the whole point of cloud code. That's the whole point of the barrier to entry being dropped down to zero because you no longer need to know coding languages. You no longer need to know Python or be this coding expert. The barrier to entry is now at zero. What you do need to know is how to clearly communicate your ideas in English so that AI can interpret what you mean. If you cannot clearly communicate what your strategy is or what you want or the right questions to ask, these are the skills of the decade. If you want to get good at using AI, this is prompt engineering. asking the right questions, analyzing the results you get and then moving further. That is the skill.

**[08:12]** You do not need to learn how to code Vocabulary. So, there's a lot of popular terms that get thrown around and a misunderstanding of these is going to leave you lost. And if you don't know what they mean, you're going to be in a lot of trouble. And some of these go into prop firms as well because we need to understand some of this vocabulary because profirms use it all the time. We start with a basic win rate. This is the most common is why you click

**[08:50]** this video. Win rate. How many trades are you winning? 90% means you're winning nine out of 10 trades. 50% means you're winning five out of 10 trades. It is just what percentage of trades you're winning percentage of trades one per sample. Per sample is important because if I test five trades and I won four and I have an 80% win rate. I mean you do technically speaking but your sample size was not enough. You need a bigger sample size to actually trust the data. Riskto-reward RR.

**[09:40]** So if I have a one to two riskto-reward that means I am going to risk $10 to make $20. If I have a two to one risk-to-reward, that means I'm going to risk $20 to make $10. And both of these can work. There is such a strong bias towards, oh, you've got to be at least doing one to two, at least one to three, at least one to 1.5. Negative risk-to-rewards can be so profitable. I know traders who have made their entire brand off of negative risk-to-reward and they kill it in prop firms. They make so much money. This is just as good as this if you have a win rate that corresponds with them. Max loss limit. This is getting into prop firm terminology.

**[10:41]** So, when you see a prop firm say $25,000 account or $50,000 funded account, that's margin. That doesn't matter. Your actual account size is what your max loss limit is. So, when you say a $25,000 funded account, you have a $1,000 max loss limit. It is a $1,000 funded account because that is all the money that you have access to using

**[11:09]** not 25k funded. You have a 1k max loss limit because that is all that you have available. Those are flashy numbers that represent the margin which is rather irrelevant because it's simulated funds. Anyway, this is a big one and this is important [snorts] to know the difference. End of day draw down versus intraday draw down. And I'm actually going to make some space here to make this clear. So these are two different types. And a lot of times with certain profs, you'll see if you just check a box and switch it from end of day to intraday, you get a discount. And you get that discount because intraday sucks. And [clears throat] in my opinion, you should never do intraday. And here's why.

**[12:13]** So at the end of the day, if you made $100 on your funded account or on your evaluation, your max loss limit increases. So let's let's take the example of I have a $1,000 max loss limit. So max loss limit equals

**[12:33]** $1,000. Day one, I make plus $100 for the end of day trailing and the intraday. My max loss limit is going to go from a,000 to 900. So, same thing, right? There's no difference yet. But what if on day two

**[13:11]** I lose $100. Okay. So, our balance I'll make a balance side to keep things clear as well. Our balance after day one is $100 and on the next day it's $0. But in the middle of this trade,

**[13:37]** we actually went up $75 and then we went all the way down to stop loss and the trade yielded negative $100. because we went up $75. Our max loss limit for intraday trailed with it. It kept going. It's calculated every second based off of your unrealized profit and loss. End of day

**[14:06]** is calculated end of day profit and loss. So for this number, it doesn't change because at the end of the day, you lost $100. So for your end of day max loss limit, it's going to be 900. But for your intraday, because you had an unrealized profit and loss of $175, at one point you didn't have to click buy or sell, but at some time during the day, you had $175. This has now trailed to $825. And now you have less room. And that gets a lot scarier the more you size up. So almost never could you ever

**[14:52]** go for intraday draw down especially on fun accounts when you're being more cautious to get payouts. Consistency rules. These have come about in the past one to two years before that. They weren't here and people made a lot of money because they weren't here.

**[15:33]** This is more common on fun accounts, less common on evaluations. You'll see a lot of single day or 50% day evaluations. So, a consistency rule is a rule put in place to stop you from hitting home runs. I always come back to the memecoin example for this because that's how people got rich in the memecoin era because there's no such thing as consistency. First off, people weren't doing funded accounts that people were trading with their own live money, but there was no consistency to stop them. So, their win rates would be 1% or less, but they would hit one home run for a one to 1,000 risk-to-reward and get rich off of a single trade. a consistency rule would stop you. So

**[16:26]** let's take an example for the evaluation stage. Let's say the eval has a 50% consistency rule. 50% consistency means you cannot have a single day that is more than 50% of your profit target. So, if my profit target is $3,000,

**[16:54]** a single day cannot be higher than 1,500 or 50% of this amount. One of my students ran into this problem just the other day before passing his account. So, my student on his Eval had an automated trade get placed and he made $1,600. Now, that doesn't mean they breached the account, but this target all of a sudden moved. So, that 50% consistency still applied. So for this to be half of the profit target, you double this value.

**[17:48]** So when he had a day where he made too much, he did too well, he was hit with this percentage and his profit target moved to $3,200 and he had to make more in order to pass that account. Now, on the funded stage, these consistency rules tend to drop lower. And I'll give you the reasoning behind why that happened because again, it wasn't like this. Most prop firms didn't have consistency rules. So, most are now 40% on the funded stage. And before that,

**[18:31]** you would have traders who would pass the eval get on the funded stage. they would have one day where they fullport the whole account and make $4,000 on a super small funded account. So, they made 4,000 and the payout rules say you have to have three winning days. So, day one

**[18:53]** they made 4,000 and they only need two more winning days before they can withdraw a whole bunch of that money. So on days two and day three, they only make 150 bucks to meet the bare minimum request 2,000 to 2,500, however much, and the eval only costed them 50 bucks. So they take that 2,000, they go and recycle it and get 30 more evals and do the same thing again. But a 40% consistency rule means that your balance must consist of days that do not exist higher than 40% of your target. So now the case is if you have a $4,000 day on a prop firm,

**[19:47]** this can only be worth 40% of your total balance. So, in order to get paid now, you would have to do that again. But if I have my another $150 day, this is only 50% consistency. This doesn't even meet the 40% yet. My math is starting to get challenged here. But what you would really need

**[20:31]** Okay, we're almost there. Math on the spot, baby. Come on. Mechanical engineering degree be getting put to use. All right. 40 45,000. I don't think this is even enough still. We're going to bump this up to 1500.

**[20:54]** Okay, so you understand hopefully by now. The total balance at this point is 10,000 500. [laughter] Double check the math, someone please.

**[21:16]** A consistency rule means your biggest day cannot be worth more than this percentage of your total That is what that means. So, as a general rule, forget my poor math skills. If I have a total balance of $1,000 and I need to meet a 40% consistency rule, no single day

**[21:50]** can be more than $400. It has to be $400 or less. You could do 333 * 3. You could do 350 350

**[22:10]** 300. But it cannot be worth more than 40% of your total balance. So you'll see on some prop firms you can do a straight defunded and you can pay a couple hundred and skip the eval stage. How awesome is that? You can get paid so fast. but they'll throw a 20% consistency rule on there. And that makes it so hard to get paid. 20% consistency means you need five winning days of the exact same.

**[22:45]** And you can't lose a single day because if you lose a single day, you need to win again to make that up and win again. So, you would need six winning days of the same amount, which is an outrageous win rate. And the final vocab that's super important and gets into reframing is profit factor. This matters more than anything else because when we're looking to find our profitable strategies, we're looking at profit factor. and the profit factor combined with different win rate combinations and risk-to-reward combinations is how we decide how we approach our prop firms. So a 1.0

**[23:35]** profit factor means you're break even. 0.5 means you're losing 0.5 of your risk per trade. 1.5 means you are making 1.5 of your risk on average per trade. So if I had $1,000 and I shed it through all of these,

**[24:08]** I would be left with $1,000, $500, and $1,500. This is essentially your multiplier for your starting balance. So, whatever amount of money you're starting with, you multiply by your profit factor and then that's the balance you're left with after your sample size. So, a lot of the strategies that I'm seeing right now and that I'm actually using are only like 1.2 or 1.4. I have this crazy guy in my community who somehow cracked a mechanical 1.9, which is awesome. If you have a profit factor over 1.5 or even at 1.5 and there's over a 100 trades in that back test sample and it's all within a recent amount of time, you're on to something good. Keep going.

**[25:08]** [snorts] So both of these Now we're on to reframing because you clicked on this video because you want to increase your win rate with AI and we can do that but that doesn't mean anything. What we really want to do is we want to increase our profit factor and we have three different levers that we can pull with AI to do that. So win rate up

**[25:38]** is not what we're looking for. It can be depending on what stage of an account you're at, whether you're on a holy whether you're on a funded account or an evaluation. But this doesn't mean very much. What we're really looking for is our

**[25:59]** to increase. This is the best summary of whether or not you have a successful strategy. If this is less than one, you do not. If this is greater than one, then you do. And we want this to increase. And we have a couple different levers we can pull using AI to figure that out.

**[26:24]** Those are number one, filters. So much of finding good trades in a sample size is getting rid of the bad ones. Let's filter out all of the crap and just find the best ones. And that can be a variety of things. Indicators, trend lines, VWOP, EMA, RSI, volume, like you name whatever you want. But we can apply filters to our strategy to determine what leads to a higher profit factor. The next thing that we can do is we can change our entry and our exit. At what point when our criteria for our strategy is met are we entering? Are we doing limit market time? What time frame?

**[27:27]** How far is our take profit? How far is our stop loss? Do we change point values? Should we do timebased? Can you imagine that? How revolutionary is that in the day trading space to imagine entering a trade and then just starting a timer and waiting till the timer's up to exit your trade? That is so unorthodox. But what if you just ask the question in her profit factor increases? Then that's a viable approach.

**[28:00]** Ask more questions to Claude. And the final is when this is volume based as well, but certain strategies are going to do better at certain times. If you have some consolidation strategy that requires really low volume and you're applying it to the New York Open, have you even thought of asking AI to apply it to Asia session open because there's not a lot of volume during that time? What about news events at 8:30 a.m. EST?

**[28:39]** Does that short window allow for massive profit factor strategies? The time of day does play a role. And it plays a role because the volume changes. Not because the market makers are waking up and having their morning coffee, but because you can literally see the volume throughout the day routinely change. Asia recession is low. London's a little bit higher. 8:30 a.m. news, we get massive spikes. New York open, 9:30 a.m. every day, we get a spike. We keep going. 2:00 p.m. on a Wednesday every month, we get a huge spike. And then 2:30 someone talks and we get random spikes. And then at 9:00 p.m. someone tweets on Twitter and then it blows the whole market up bigger than all of those events. These are your three levels levers to pull to increase your profit factor.

**[29:38]** Variation searching. So, when I say I tested 10,000 strategies, which you're going to see in a video in a few days, I did not go and find 10,000 individual strategies. And you saw this on my conversation with Nick's client call posted a week ago.

**[30:04]** What we do is we have a core strategy. So, let's let's take an example. Right. We'll go with an acquaintance who's probably familiar to you. We'll go with this strategy.

**[30:27]** This strategy sucks. I'm just kidding. It's all right. But we want to see how we can increase our profit factor. And to do this, we can start testing variations. So, we can start start testing. We might take this on the one minute time frame. Why don't we test it on literally every time frame that exists? Because you might be taking it on the one minute every time. What if it's more profitable on the two-minut? Because it slices your quantity of trades in half, but every trade is more likely to win. That makes you more money. It's lower frequency. And that can be hard to stomach. a strategy that's lower frequency and a higher profit factor, but if it makes you more money and that's the goal, you're having to resist your gambling urges. That's one of the two secrets to profitability is separating yourself from the desire to make money. If you can separate yourself from that desire and simply follow the math, you're going to make more.

**[31:28]** call this time frame expansion. What if we also test seasonality expansion? There are routines year after year of how the market moves. I believe you can look this up, but I believe it looks something like this. From start to end in the past decade, the average year to year looks like this. So like January, December, you can fact check me looks something like this.

**[32:05]** You can verify whether or not that's true. But seasonality plays a role. So we can test variations month to month or even week day to week day. You'd be amazed how big of a role the day of the week can play.

**[32:35]** Then we can test our filters. ATR, VWOP, EMA, trend line, whatever you want. Add it on there. Ask the question. What else can we test? We can test news There are routine news events like unemployment claims at 8:30 a.m. once a month that will shake the market. You can you can bet on it that this is maybe it's not going to make a massive move, but it's going to inject a lot of volume and volume affect strategy. So for just these five, we can take five different news events, five different filters. We have five weekdays, we have 12 months, we can test out 20 different time frames. So we've just taken one strategy and we can now back test and create 100 plus different strategies around the same core idea.

**[33:33]** So, when I'm saying I'm testing 10,000 strategies, I took 50 core ideas, made 200 variations of each one, ran them through to see the most profitable ones. This is what variation searching is, and then you'll get a list of all these strategies, and then the ones with the highest profit factor, that's where your biggest profitability is going to lie.

**[34:07]** When to test I had a guy the other day message me on Instagram and say he was a little disappointed because he was struggling to find candlestick data from 2010.

**[34:42]** If you have a profitable strategy in 2010 that does nothing over the next 16 years, that is completely unhelpful. I drew the example in the beginning. I'll draw it again. This is technically profitable.

**[35:06]** But if you started any time after 2011, let's just say we started here and we started using this strategy, we have lost money year over year over year over year over year.

**[35:40]** but we want a a higher trade frequency and that's fine. So, this is where it starts to get really dependent on what kind of trading you're doing. And now I'm going to assume that a lot of people in here are doing intraday trading because that's the best approach for And you do want a higher sample size. So if you're only taking 20 trades a year, yeah, you're probably gonna want to go back and look at the last five years because in my personal opinion, in my experience, I want at least 100 trades per sample size before I trust the data that I'm reading. I need a higher frequency. And we'll see that how that affects prop clustering. So when to test, I tested on my multi-million back test, seven years of data. And then what I did is I looked at the most profitable strategies and I looked at a chart like this. So we have our baseline of profitability here.

**[36:36]** And then I started looking year-over-year. What's the performance? And I saw interesting important data. I would see things like this.

**[37:00]** This gives me an important story. This tells me that in 6 54 2023 it was very profitable. 2024 very profitable. 2025 it was not very profitable. Now what could that be from? Maybe we zoom in more and we see that the tariffs that happened in 2025 in April totally bombed this strategy, but we see that a little bit of a smoother market in 2026 led it to do very well.

**[37:31]** All of a sudden, we can rely on this a lot more. So, the two things to keep in mind when you're looking at your amount of historical data to test are trade frequency and a recency bias. Because with a lot of confidence, I can tell you that in another two years when we have a different presidential regime, the market will not be moving in 2029 like it is in 2026. That is a reliable claim to make. And the same is true today. A strategy profitable in 2022 is unlikely to be profitable today. And it's that same drawing again. The only thing we need to be sure of is getting a high frequency because if you take 10 trades a year or if you only test the past week and you got 50 trades, maybe let's test a couple weeks and see how we're doing. I'm taking an approach this coming week on some of my own strategy that I'm testing. And I have all these different charts, right?

**[38:41]** and I'll take you kind of through my decision- making process on these charts to really get this point across. Now, all of these strategies are profitable, tested with AI, they all look great, but I need to make decisions. So we'll take three or so every strategy is ending in profit

**[39:05]** and I'm going to be using them this coming week in automated executions with Claude. I'm not watching the charts But one of the strategies did this over the past six months. Okay, it's profitable. It got there. Stats are great. But in the past two months, we've been kind of rough. And if I'm only looking to squeeze a lot out of it in the next week, maybe I'm not a big fan. Another strategy is something like this. Okay, you're really reliable. I love the way you look. Like, that's that's sweet. That's awesome. Six months. This is beautiful. I love it. Then we have this

**[39:57]** Okay. Interesting. So, we're not making a lot over the past four months, but in the past couple weeks of market conditions, it's been on fire. assuming that things continue on their current path, applying what did well over the past three weeks to the next week in theory should yield better results. And I'm placing a bet on that this coming week because I'm looking for only this next range.

**[40:35]** I'm looking to see what can make the most money right here. And so if this continues its slope, we're going to crush it. If this continues, we'll probably do pretty If this continues, I don't know if we'll make anything. Recency bias is important because the market changes fast and it's changing faster and faster over time. We can see it. It's not a secret. It's not some mystery. We It's literally in front of our faces. We can see it changing. Zoom out on the weekly chart on the S&P 500

**[41:17]** and you'll find that from 2010 to 2016 or to 2026 that the S&P 500 looks like this. Things are [snorts] changing. That's why recency bias on the trades you're taking is more important than ever.

**[41:52]** But it has to be a high trade frequency. You cannot back test 30 trades and say, "Oh, my data set's great. Unless you're looking at a two-year time frame and you're looking to swing trades over a month on stocks, that is unreliable for day trading.

**[42:15]** Prop clustering. Prop clustering. This is for more of those prop farmers, the people who spend a whole bunch on property valuations, blow a whole bunch, get a bunch of payouts really fast. That's what I'm going to do this next week. And the question is, should you copy trade them? So, let's say I have 10 accounts

**[42:45]** and let's let's do an analogy, right? I'm going to flip a coin four times. Okay? My engineering statistics is going to come helpful here. So, I'm going to flip it four times. If I get one, two, three heads and one tails, how shocked would you be? Probably not that surprised. It's such a small sample. I mean, like that can happen. like that's not that's not extremely unlikely to happen. Now, what if I flipped it a 100 times and then instead of 50/50, I got 75 heads and 25 tails. How crazy would that be? Okay, now that's a little alarming. That says to me something's wrong with this coin.

**[43:56]** This isn't playing out the way I would like. This isn't playing out the way I would prefer. This is not probabilistic. It's leading to me leading me to believe something is wrong. So, should we copy trade our evaluations? Should we copy trade our funded accounts? Now, this depends on your approach. Again, a lot of this is dependent. That's why I have a one-on-one mentorship because specific conditions require specific approaches. It's not always a one-sizefitit all, but this is a good generic rule and applies to my case and a degree of other people's cases.

**[44:40]** So, we'll say we'll actually make this 12 accounts. 12 accounts. I'm going to divide them into three groups of four. and I'm going to copy trade four at a time. So, back to the coin flip example. If I have a 50% win rate with a 1.5 risk-to-reward, and I'm trying to pass these in single days, how crazy would it be for me to lose one trade, lose a second trade, and then win the third? Because although I have a 50% win rate, which we know is true, this should be 50%. But it is not insane to see numbers like this if we flip a coin three times. That is bound to happen. And if we do that here, then all of a sudden our 50% just turned into 33% because we were copy trading. That's not unlikely.

**[45:40]** The more samples that we give it, the more flips that we give it, the closer we are going to get to 50%. More flips, the closer we should in theory statistically get to our actual number. And so we if we have a backtested 50% pass rate, we want to flip it as many times as we can because the more flips we do, the closer we get to this number. So instead of doing 4, four, four, we do something like one, one, two, three, four, five, 6, 7, 8, 9, 10, 11, 12.

**[46:22]** Right? So maybe we get that still same playout. loss, loss, win, right? That could happen. And maybe we get another loss and another loss and then we get a win and a win and a win and a win and then another loss and then two more wins or a win and a loss. All of a sudden, since we kept flipping the coin, we got a lot closer to our 50%. because we were flipping it more.

**[46:58]** That's six losses and six wins simply because we kept going and we increased our sample size. So when you're copy trading evaluations and you're trying to pass as many as you can, you want to in a high frequency environment, not be copy trading them. You want to give it more opportunity to reach that 50%. Doing this in a high frequency setup means you're gambling more and you're placing more at stake for no reason other than you're impatient.

**[47:34]** And then the same logic applies to funded accounts. This is again more applicable to high frequency trading. If you're only trading one time a week, you better have a high win rate or a really high profit factor and you're risking less on Eboss.

**[47:54]** Which AI? So, right now, today is September 19th or 20th, I think. Some of our top tier winners are Fable 5.1 and Astra 6. This is Claude.

**[48:22]** This is chat GPT. Now, you can go and you can do your research and you can experiment with these. I'm going to talk based off of my experience, what I'm doing, and how I'm using these. These are awesome. These will get you everything you need and more. In fact, you're probably not even getting the most out of them. They're probably overkill. These are your CEOs, and you're going to eat up your usage when you're using these. You do not want to tell these models to write you a cat poem that is a waste of tokens. You want to tell a model like

**[49:06]** this is still overkill, but it's to make a point. Really, you'd want to tell a model like Haiku, which I think is like in its fourth generation, which is one of Claude's models, that's going to write a good cap home because it's low tokens, it's low usage, and writing a cap home is really easy to do. Now, making judgments based off of complicated strategies and market regimes. Let's use our highest model because why not? But if you're conservative on your usage, this is your these are your CEOs and they're your CEOs because they're really good at judgment and decision- making. And then I'm not too familiar with Codeex because I don't use it frequently, but Opus

**[49:56]** 4.8. Opus 5 is out, but Opus 4.8 is better. And I'll explain why in a moment. Opus 4.8 is your code monkey. And it's your code monkey because it's going to do a really good job at agentic coding for you and getting the point across and completing the task at hand without eating up all of your tokens. and it's going to do almost an identical job as some of these better models. And I say Opus 4.8 and not Opus 5 because of ethical reasons. Opus 5 has been clearly shown and in my experience as well to give far more increased false

**[50:42]** positive rejections. Meaning you are saying hey Opus 5 enter this trade for me and it's saying no. and you're saying, "Oopus 5, build this algorithm that's going to automatically execute or run this back test and then it's feeding back to you. This is a poor choice and I'm not going to do that for you." Whereas Opus 4.8 is nearly it's marginally lower in quality of code, but it's not denying your requests. So, you're going to get a nearly unrecognizable difference in your result, but it's going to finish the job that you want. So, Opus 4.8 is going to be your code monkey. So really my pipeline is I'm asking for prompts from Fable 5.1 and feeding them to my code monkey that does all of it for me with less usage and still really good results that are not denying my requests.

**[51:34]** Same with Astra 6. These your decision makers. They have incredible depth and thinking, highly agentic. We don't need to use them all the time. In fact, in some cases, it's better not to use them because we can get our results faster and then loop our results quicker. So, don't give Fable 5.1 a cat poem.

**[52:16]** The final one.

**[52:39]** Order of operations. So that was a lot of information and a lot of the reason I have my mentorship is not because you are incapable of doing these things. It does take work. It does take investment. It does take time. If you join my community

**[53:03]** and you never show up, you'll never get results. If you join my community and you're asking me questions and you're seeking guidance and you're following my system, you will make progress and get closer to getting paid. That is what I want to happen. If you are interested in personal guidance from me, I work individually personally with every single one of my students. It's not a drop off of all right, go figure it out. It's no, where are you at? Tell me where you're at and let's keep going. But in this free sauce video,

**[53:43]** your order of operations should look [snorts] something like this. You should start with strategy. You should then look into back testing. You should then identify prop firms you want to rules properforms you want to use and rules you want to follow and you should adapt your strategy to those rules. You should then live test until you have the competence and then you should risk the money to get paid. That is the order that you should follow.

**[54:30]** I love this stuff. This stuff is awesome. It's a Saturday and I just came back from the gym. I was going to take a shower and I said, "You know what? No, I want to make this. I want to make this video. I want to provide value because I just love it. I love this stuff. I think about this all day long. I take calls all day long. It was Friday night and I was calling people. 8:00 a.m. that same day I was calling people. I'm so invested in the success of my students because I love them. I I really want to see them win and it is the most rewarding feeling ever. One of my students passed an account the other day with fully automatic executions and I love that. But what I loved even more was he was working hard for it. And I love to see those who work hard and give it their all succeed. It [clears throat] fires me up. I love it so much. And that applies to every realm. The gym, trading, even school, maybe school. If you're working hard, you will reach what you want to reach.

**[55:39]** And I love working with the dogs in there in my community. I have one guy who a few days ago we were on a call and I literally told him to stop working. [laughter] I said, "Dude, literally close Claude. You've built everything you need. It's time to chill out and let the systems run." Because the point of AI automation is to let it be automated. If every time you build an automation, you look for the next thing to be automated, what are you doing it for? I don't watch the choice anymore. I'm enjoying the fruits of my labor. And that's the point of all this. Let's use the new technology to our advantage.

**[56:20]** And it requires work. If you think it doesn't, you're wrong. If you want to work one-on-one with me, I've got a mentorship. It's Ocean Front AI. I love working with my students. We talk all the time. And let me know what you think of the video. Let me know what questions you have, what things I can answer in the future. And uh I hope to see you soon.

---

## 2. Slides and data harvested

### 2.0 Board layout

- Agenda strip along the top edge, present for the whole video, in red: `1 Myths | 2 Vocab | 3 Reframe | 4 Variation Search | 5 When to test | 6 Prop Clustering | 7 Which AI | 8 OOO`. Each item gets a blue check mark as he finishes it (Myths and Vocab checked by 25:12, all eight by 52:39).
- A small hand-written cue line along the bottom edge (starts `1. WR · RR · MLL · EOD/intra · Consistency ...`). Not legible beyond the first few tokens at frame resolution.

### 2.1 Myths (00:00 to 08:12)

Six questions are on the board before he starts; the verdict is added as each is discussed.

| Question on the board | Verdict | Marked by |
|---|---|---|
| A high WR = Good Strategy? | ✗ | 00:13 |
| AI will find me a profitable strategy? | ✓ (the only check) | 00:13 |
| More historical data is better? | ✗ | 04:00 |
| Profitable in backtest means profitable live? | ✗ | 06:14 |
| Strategy is the hardest part? | ✗ | 06:14 |
| I need to learn to code? | ✗ | 07:34 |

Win-rate worked example, written under the questions (01:47 to 03:34):

| Row | As written | Spoken (01:41 to 03:18) |
|---|---|---|
| "90% win rate" trader | `90%  80%–BE  20% 1:1  20% 1:1` (the two small percentages read as 20% at frame resolution) | 80% break-even, 10% win at 1:1, 10% lose at 1:1: not profitable |
| "55% win rate" trader | `55%  55% 1:1  45% 1:1` | 55% win at 1:1, 45% lose at 1:1: more profitable |
| Edit at 03:20 | both rows' `1:1` changed to `1:2` | "even if I change this to just one to two, now this is better" |

Other figures spoken in this section: 20,000 strategies and "13 million trades" backtested in the past two weeks (03:28 to 03:42).

P&L-over-time sketch (04:54 to 05:47): x-axis `2016` to `2026`, red curve rising steeply to about 2021 then sawing downward to 2026. A straight average line is drawn through it at 05:34 to make the point that "the average of the decade looks profitable" while the last five years lose.

### 2.2 Vocab (08:17 to 24:55)

- 08:41 to 09:15: `WR – Percentage of trades won per sample`.
- 09:34 to 10:02: `RR – 1:2  $10 → $20` and `2:1  $20 → $10`. Spoken: negative risk-to-reward is "just as good" if the win rate corresponds (10:12 to 10:30).
- 10:33 to 11:21: `MLL – 25K` (crossed out) `1k Max Loss Limit`. A "$25,000 funded account" with a $1,000 max loss limit is a $1,000 account.
- 11:34 to 14:41: end-of-day vs intraday trailing drawdown, as a table:

| | EOD limit | Intraday limit | Balance |
|---|---|---|---|
| Start: `MLL – $1000` | 1000 | 1000 | 0 |
| Day 1: `+$100` | 900 | 900 | $100 |
| Day 2: `–$100` (the trade ran +$75 unrealized before stopping out, 13:37) | 900 | 825 | $0 |

Spoken: the intraday limit is recomputed "every second" on unrealized P&L, so the $175 unrealized peak ($100 realized plus $75 open) drags it to $825 (14:21 to 14:38). His rule: never take the intraday option, even at a discount (11:55 to 12:01).

- 15:02: `Consistency Rule` heading.
- 16:28 to 17:58, evaluation stage: `Eval. 50%  $3000  $1,500 is cap`. Then `1,600 → $3,200`: a student's automated trade made $1,600 in one day, so under the 50% rule the profit target doubled from $3,000 to $3,200 (17:06 to 18:01).
- 18:15 to 20:55, funded stage: `40%` written under the heading. A "Before" column shows the old payout exploit: `Day 1 $4,000 / Day 2 $150 / Day 3 $150` (three winning days, request a payout, recycle it into 30 more $50 evals; 18:31 to 19:24). He then rewrites the rows to satisfy a 40% rule, trying `Day 1 $4,000 / Day 2 $4,000 / Day 3 $150` (19:48), then `$4,500 / $4,500 / $500`, then `$1,000`, then `$1,500`, with the total `10,500` (20:28 to 21:04). He calls out that the arithmetic is shaky ("Double check the math, someone please", 21:10). As written, $4,500 is still 43% of $10,500.
- 21:35 to 22:15, clean restatement: `$1,000  no single Day ≥ $400`. A 40% rule on a $1,000 balance caps any single day at $400 ("333 times 3, 350 350 300", 21:59 to 22:10).
- Spoken, 22:15 to 22:57: some prop firms sell straight-to-funded accounts but attach a 20% consistency rule, which he reads as needing five equal winning days, six if any day loses.
- 22:57 to 24:55, profit factor: `PF`, then `$1,000 {` and three rows. The rows read at frame resolution as `2.00 → 1,000`, `0.50 → 500`, `1.60 → 1,500`. The spoken values are 1.0 (break-even), 0.5 (losing half of risk per trade) and 1.5 (making 1.5 times risk per trade), and the right-hand column matches the spoken values, so treat the spoken values as authoritative. Spoken thresholds: his live strategies are "1.2 or 1.4"; one community member has a mechanical 1.9; PF at or above 1.5 with 100+ trades in a recent sample means "keep going" (24:30 to 24:55).

### 2.3 Reframe (25:12 to 29:32)

- 25:33 to 26:03: `WR ↗` crossed out in red; `PF ↗` circled in blue.
- 26:24: `1. Filters` (spoken list: indicators, trend lines, VWAP, EMA, RSI, volume).
- 27:04: `2. Entry/Exit` (spoken: limit vs market, timeframe, take-profit and stop distance, point values, time-based exits).
- 28:06: `3. When` (spoken: session and time of day, driven by volume; Asia low, London higher, 8:30 ET news spikes, 9:30 ET open, 2:00 pm on a Wednesday monthly, 2:30 pm speakers, 9:00 pm tweets).

### 2.4 Variation Search (29:38 to 33:51)

- 30:11: `IFVG` circled as the example core strategy (inverse fair value gap; "an acquaintance who's probably familiar to you", 30:14).
- 31:14: `Timeframe Expansion` branch. `Jan` written below the circle for a seasonality sketch, then erased (31:36 to 32:05: he decides against drawing the average year).
- 32:16: `month/month` and `weekday/weekday` branches.
- 32:36: `filters` and `news` branches. Final diagram: IFVG in the middle with five spokes.
- Spoken multiplication (33:11 to 33:41): 5 news events, 5 filters, 5 weekdays, 12 months, 20 timeframes gives "100 plus" variants per core idea; 50 core ideas times 200 variations is the 10,000 strategies.

### 2.5 When to test (34:07 to 42:10)

- 34:41 to 35:22: axis `2010` to `2026`; a curve that spikes in 2010 to 2011 and then runs flat to slightly down to 2026. A second line from the 2011 peak shows anyone starting after 2011 losing "year over year over year" (35:06 to 35:23).
- 36:45 to 37:47: on the same axis, year bars above and below a baseline: two bars up (spoken as 2023 and 2024 very profitable), one bar down (2025, "the tariffs that happened in 2025 in April"), one bar up (2026).
- 38:49 to 40:55: three small six-month equity curves side by side, each with a dot to the right marking "the next range" he wants to trade (40:24 to 40:39):
  1. rises, then dips over the last two months ("it's profitable, it got there, but in the past two months we've been kind of rough", 39:23 to 39:35);
  2. steady rise ("really reliable, six months, this is beautiful", 39:40 to 39:47);
  3. flat for four months, then steep over the last few weeks ("in the past couple weeks of market conditions, it's been on fire", 40:00 to 40:07). He is betting on this one for the coming week.
- 41:12 to 41:36: below them, an S&P 500 weekly sketch from `2010` to `2026`, flat-ish and then steepening ("things are changing").
- Spoken rules: at least 100 trades per sample (36:04); seven years of data on his multi-million-trade backtest, then judged year over year (36:19 to 36:41); 30 backtested trades is not a dataset for day trading (41:55 to 42:10).

### 2.6 Prop Clustering (42:15 to 47:50)

- 42:37: `10 accounts`. 43:03 to 43:47: `Heads |||  Tails |` (4 flips), then `Heads 75  Tails 25` (100 flips).
- 44:40 to 44:52: rewritten as `12 accounts` with `4 / 4 / 4` (three groups of four, copy-traded).
- 44:54 to 45:36: `Heads 2  Tails 1` with `↑ 50%`; the three groups marked `✗ ✗ ✓` (loss, loss, win) and `50%` written next to "12 accounts". Spoken: with a 50% win rate and 1.5 R, a loss-loss-win run turns the group's 50% into 33% (45:31 to 45:36).
- 46:04 to 46:46: `more flips → 50%` and a column of 12 tick rows marked one at a time. Spoken sequence: L L W L L W W W W L, then "a win and a loss", six wins and six losses (46:22 to 47:00).
- Spoken rule: in a high-frequency setup, do not copy-trade evals or funded accounts; give the edge more independent flips (47:02 to 47:26).

### 2.7 Which AI (47:54 to 51:58)

- 48:09 to 48:30: `Fable 5.1 – CLAUDE` and `Astra 6 – ChatGPT`. "Today is September 19th or 20th" (48:00).
- 49:11: `Haiku 4` written below (for cheap tasks, "write a cat poem"), erased by 49:31.
- 49:31: `CEO {` bracket added in front of the Fable/Astra pair.
- 49:52: `Opus 4.8 – Code monkey`.
- 51:15 to 51:36: an arrow drawn from the Fable/Astra pair to Opus 4.8. Spoken pipeline: Fable 5.1 writes the prompts, Opus 4.8 does the agentic coding, "less usage and still really good results".
- Spoken claims (49:56 to 51:16): Opus 5 is out but gives "far more increased false positive rejections" (refusing to place trades or build execution algorithms), so he uses Opus 4.8. He says he is not familiar with Codex. These are the presenter's claims and are not verified here.

### 2.8 Order of Operations (52:16 to 54:20)

- 52:39: `Order of Operations` heading; nothing else written.
- Spoken sequence (53:48 to 54:20): strategy, then backtesting, then identify prop firms and their rules and adapt the strategy to those rules, then live test until confident, then risk the money to get paid.

### 2.9 Outro (54:30 to 56:46)

Nothing new on the board. Mentorship pitch (oceanfrontai.com, 56:31); anecdote about telling a student to "close Claude" and let the automations run (55:43 to 56:04).
