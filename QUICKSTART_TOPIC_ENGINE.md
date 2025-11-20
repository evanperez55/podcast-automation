# Topic Engine - Quick Start

Get AI-powered topic curation in **5 minutes**!

## What You Get

- 🤖 **100+ topics/week** scraped from Reddit
- 🎯 **AI scoring** (0-10) for viral potential
- 📊 **Organized by category** (shocking news, hypotheticals, etc.)
- 📝 **Episode plans** with balanced topic mix
- ✅ **Auto-tracking** of discussed topics

## 5-Minute Setup

### 1. Install Reddit API Package (1 min)

```bash
pip install praw==7.7.1
```

### 2. (Optional) Get Reddit Credentials (3 min)

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" → Choose "script"
3. Add to `.env`:
   ```env
   REDDIT_CLIENT_ID=your_id
   REDDIT_CLIENT_SECRET=your_secret
   ```

*Works without this, but slower*

### 3. Run First Refresh (1 min)

```bash
python weekly_topic_refresh.py
```

Done! Check `topic_data/` for results.

## How to Use

### Weekly Workflow:

```bash
# 1. Get fresh topics (run Sundays)
python weekly_topic_refresh.py

# 2. Review topics
open topic_data/structured_topics.txt

# 3. Copy to Google Doc (manual for now)
# Paste the structured topics into your doc

# 4. Before recording, get episode plan
python topic_curator.py plan

# 5. Record episode with suggested topics

# 6. Process episode (auto-tracks discussed topics)
python main.py latest
```

### Your Google Doc Will Look Like:

```
==================================================
FAKE PROBLEMS PODCAST - TOPIC BANK
==================================================

🔥 SHOCKING NEWS STORIES (Target: 2-3 per episode)
  ⭐ Guy ate 6-9 lbs cheese daily, started oozing cholesterol
  ✨ Plane emergency landing due to explosive diarrhea
  • Cop parks car on train tracks with woman inside

🤔 ABSURD HYPOTHETICALS (Target: 2-3 per episode)
  ⭐ What if we released all cows into the wild
  ✨ Gas-powered adult toys before electric ones

💔 DATING & SOCIAL (Target: 1-2 per episode)
  • OnlyFans notification for high school classmates
  • Morning dating app messages as red flags

... etc for all 6 categories ...

==================================================
DISCUSSED TOPICS (Auto-populated)
==================================================
• cheese addiction - Episode 25 (2025-01-19)
```

## What Each Score Means

- **9-10** ⭐ Viral potential! Must use
- **7-8** ✨ Great content
- **6-7** Good filler
- **<6** Skip

## Commands Cheat Sheet

```bash
# Full weekly refresh (all steps)
python weekly_topic_refresh.py

# Just scrape new topics
python topic_scraper.py

# Just score topics
python topic_scorer.py

# Plan next episode
python topic_curator.py plan

# Process episode (auto-tracks topics)
python main.py latest
```

## Files You'll Use

```
topic_data/
├── scraped_topics_*.json      ← Raw topics from Reddit
├── scored_topics_*.json        ← AI-scored topics
├── structured_topics.txt       ← Copy this to Google Doc!
└── episode_plan_*.json         ← Suggested episode structure
```

## Scoring Criteria (What Claude Looks For)

Each topic rated 0-10 on:

1. **Shock Value** (0-3): Does it make you say "WHAT?!"
2. **Relatability** (0-2): Can audience connect?
3. **Absurdity** (0-2): How ridiculous?
4. **Title Hook** (0-2): Makes you want to click?
5. **Visual Imagery** (0-1): Can you picture it?

**6+ = Recommended for episodes**

## Ideal Episode Mix

Based on analyzing your 24 episodes:

- 2-3 Shocking News Stories (train crashes, poop emergencies)
- 2-3 Absurd Hypotheticals (gas-powered dildos, cow liberation)
- 1-2 Dating/Social Topics (OnlyFans economics, persistent dating)
- 1-2 Pop Science (penis size evolution, Neurolink skepticism)
- 1-2 Cultural Observations (Amazon reviews, quarter-zips)
- 1-2 Personal Anecdotes (your stories - you add these)

= **8-12 topics per episode**

## Where Topics Come From

**15 curated subreddits:**

Shocking News:
- r/nottheonion
- r/offbeat
- r/NewsOfTheWeird

Hypotheticals:
- r/CrazyIdeas
- r/Showerthoughts
- r/hypotheticalsituation

Dating/Social:
- r/Tinder
- r/dating_advice
- r/socialskills

Science/Tech:
- r/science
- r/technology
- r/Futurology

Cultural:
- r/mildlyinfuriating
- r/antiwork
- r/firstworldproblems

## Troubleshooting

**"No topics found"**
→ Reddit rate limit. Add API credentials or wait 1 hour.

**"Scoring failed"**
→ Check `ANTHROPIC_API_KEY` in `.env`

**Topics not auto-updating in doc**
→ Currently manual (copy from structured_topics.txt)
→ Auto-sync coming soon!

## Cost

- Reddit API: **Free**
- Claude scoring 100 topics: **~$0.50**
- Weekly total: **~$2/month**

## Time Saved

- Before: 2-3 hours brainstorming
- After: 5 minutes running script
- Savings: **8-12 hours/month**

## Success Metrics

After using this system:

✅ Never run out of topics
✅ Know what will perform well (AI-scored)
✅ Balanced, structured episodes
✅ Auto-track what you've discussed
✅ More viral clips

## Next Steps

1. Run `python weekly_topic_refresh.py` NOW
2. Open `topic_data/structured_topics.txt`
3. Copy into your Google Doc
4. Record your next episode with suggested topics!

**Full guide:** See `TOPIC_ENGINE_GUIDE.md`

---

**Your podcast just got smarter.** 🧠
