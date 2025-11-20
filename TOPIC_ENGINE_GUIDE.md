# Fake Problems Topic Engine

**Automated topic discovery, scoring, and curation system for your podcast.**

## 🎯 What This Does

Transforms your podcast from manual topic tracking to **data-driven content curation**:

### Before Topic Engine:
- ❌ Manually brainstorm 955 topics
- ❌ Forget which topics you've discussed
- ❌ No way to know what will perform well
- ❌ Random topic selection

### After Topic Engine:
- ✅ Automatically finds 100+ fresh topics weekly
- ✅ AI scores each topic (0-10) for viral potential
- ✅ Organized by proven categories
- ✅ Suggests balanced episode structure
- ✅ Tracks discussed topics automatically

## 🧠 How It Works

Based on analyzing your 24 episodes, the system learned what makes your podcast successful:

### Success Formula Discovered:
1. **Shocking News Stories** (20%) - Real incidents with visceral impact
2. **Absurd Hypotheticals** (25%) - Ridiculous but logical scenarios
3. **Personal Anecdotes** (25%) - Your embarrassing/wild stories
4. **Dating/Social Commentary** (15%) - Modern relationship dynamics
5. **Pop Science & Tech** (10%) - Provocative studies/tech skepticism
6. **Cultural Observations** (10%) - Workplace pet peeves, consumer behavior

### AI Scoring System:
Each topic rated 0-10 based on:
- **Shock Value** (0-3 pts): Does it make you say "wait, WHAT?"
- **Relatability** (0-2 pts): Can audience connect?
- **Absurdity** (0-2 pts): How ridiculous is the logic?
- **Title Hook** (0-2 pts): Does it make you want to click?
- **Visual Imagery** (0-1 pt): Can you picture it?

**Topics scoring 6+ are recommended for episodes.**

## 📊 The Complete System

### 4-Step Automated Pipeline:

```
[1] SCRAPE           [2] SCORE           [3] CURATE         [4] PLAN
Reddit + Web    →    Claude AI     →     Google Doc    →    Episode
15 subreddits        Rates 0-10          Organized          Structure
100+ topics          Viral potential     By category        8-12 topics
```

## 🚀 Quick Start

### One-Time Setup (5 minutes)

**1. Install dependencies:**
```bash
pip install praw==7.7.1
```

**2. (Optional) Get Reddit API credentials:**
- Go to https://www.reddit.com/prefs/apps
- Click "Create App" → Choose "script"
- Copy Client ID and Secret to `.env`:
  ```env
  REDDIT_CLIENT_ID=your_client_id
  REDDIT_CLIENT_SECRET=your_secret
  REDDIT_USER_AGENT=FakeProblems:v1.0
  ```

*Note: Works without Reddit auth, but with rate limits*

**3. You're ready!**

### Weekly Usage

**Run the complete pipeline:**
```bash
python weekly_topic_refresh.py
```

This will:
1. Scrape 100+ topics from Reddit/web (2 min)
2. Score each with Claude AI (5 min)
3. Generate organized topic file (1 min)
4. Create suggested episode plan (instant)

**Then:**
1. Open `topic_data/structured_topics.txt`
2. Copy/paste into your Google Doc
3. Use `topic_data/episode_plan_XXX.json` for next episode

## 📖 Detailed Usage

### Step 1: Scrape Topics

**Automatic (recommended):**
```bash
python topic_scraper.py
```

Scrapes from 15 curated subreddits:
- r/nottheonion, r/offbeat (shocking news)
- r/CrazyIdeas, r/Showerthoughts (hypotheticals)
- r/Tinder, r/dating_advice (dating content)
- r/science, r/Futurology (pop science)
- r/mildlyinfuriating, r/antiwork (cultural observations)
- + more

**Output:** `topic_data/scraped_topics_YYYYMMDD_HHMMSS.json`

### Step 2: Score Topics

```bash
python topic_scorer.py
```

Uses Claude AI to:
- Analyze each topic
- Score 0-10 on 5 criteria
- Categorize by type
- Flag high-potential topics

**Output:** `topic_data/scored_topics_YYYYMMDD_HHMMSS.json`

**Example scores:**
```json
{
  "title": "Guy ate 6-9 lbs cheese daily, started oozing cholesterol from hands",
  "total_score": 9.0,
  "shock_value": 3,
  "relatability": 2,
  "absurdity": 2,
  "title_hook": 2,
  "visual_imagery": 0,
  "category": "shocking_news",
  "recommended": true
}
```

### Step 3: Organize Topics

```bash
python topic_curator.py restructure
```

Creates structured topic document with:
- Header with usage instructions
- 6 categorized sections
- Only high-scoring topics (7+)
- Discussed Topics section (for automation)

**Output:** `topic_data/structured_topics.txt`

**Copy this into your Google Doc!**

### Step 4: Plan Episode

```bash
python topic_curator.py plan
```

Suggests balanced episode lineup:
- 2-3 shocking news stories
- 2-3 absurd hypotheticals
- 1-2 dating/social topics
- 1-2 pop science topics
- 1-2 cultural observations
- 1-2 personal anecdotes (you add)

**Output:** `topic_data/episode_plan_YYYYMMDD_HHMMSS.json`

## 🎬 Google Doc Structure

After running curator, your doc will look like:

```
==================================================
FAKE PROBLEMS PODCAST - TOPIC BANK
==================================================

Last Updated: 2025-01-19 14:30
Total Topics: 87
Recommended Topics: 53

HOW TO USE:
1. Pick 8-12 topics for your next episode
2. Mix categories for variety
3. After recording, automation moves discussed topics
4. Run weekly refresh for new topics

IDEAL EPISODE MIX:
- 2-3 Shocking News Stories
- 2-3 Absurd Hypotheticals
- 1-2 Dating/Social Commentary
- 1-2 Pop Science & Tech
- 1-2 Cultural Observations
- 1-2 Personal Anecdotes

==================================================

🔥 SHOCKING NEWS STORIES
(Real-world incidents with visceral impact)
Target per episode: 3 topics

  ⭐ • Guy ate 6-9 lbs cheese daily... [r/nottheonion]
  ✨ • Plane emergency landing due to explosive diarrhea [r/offbeat]
  • Cop parks car on train tracks with woman inside [r/NewsOfTheWeird]

🤔 ABSURD HYPOTHETICALS
(Logical-but-ridiculous thought experiments)
Target per episode: 3 topics

  ⭐ • What if we released all cows into the wild [r/CrazyIdeas]
  ✨ • Gas-powered adult toys before electric ones [r/Showerthoughts]
  • OnlyFans notification for high school classmates [r/hypotheticalsituation]

💔 DATING & SOCIAL COMMENTARY
... continues for all categories ...

==================================================
DISCUSSED TOPICS
==================================================

• cheese addiction - Episode 25 (2025-01-19)
• robot cafes in Japan - Episode 25 (2025-01-19)
```

## 🔄 Integration with Main Automation

The topic tracker is already integrated! After processing each episode:

```bash
python main.py latest
```

**New automated step (3.5):**
```
STEP 3: ANALYZING CONTENT WITH CLAUDE
----------------------------------------------------------
[OK] Content analysis complete

============================================================
UPDATING GOOGLE DOCS TOPIC TRACKER
============================================================
[INFO] Found 87 active topics
[OK] Found 2 discussed topics
[OK] Moved 2 topics to 'Discussed Topics' section
============================================================

STEP 4: APPLYING CENSORSHIP
...
```

Topics mentioned in the episode automatically move to "Discussed Topics" section!

## 📅 Recommended Workflow

### Weekly (Sunday evening):
```bash
python weekly_topic_refresh.py
```
→ Refresh topic bank with latest from Reddit

### Before Recording (Tuesday):
```bash
python topic_curator.py plan
```
→ Get suggested episode structure

### After Recording (Wednesday):
```bash
python main.py latest
```
→ Process episode + auto-update discussed topics

## 🎯 Success Metrics

After implementing this system, you should see:

### Content Quality:
- ✅ Higher average clip scores
- ✅ More viral potential topics
- ✅ Better category balance

### Efficiency:
- ✅ 95% less time brainstorming topics
- ✅ Never repeat topics
- ✅ Always have 50+ quality topics ready

### Growth:
- ✅ More shareable content
- ✅ Better titles for clips
- ✅ Higher engagement on social media

## 🔧 Configuration

### Customize Subreddit Sources

Edit `topic_scraper.py`:

```python
subreddit_config = {
    'nottheonion': {'time_filter': 'week', 'limit': 20},
    'your_subreddit': {'time_filter': 'month', 'limit': 15},
    # Add your own
}
```

### Adjust Scoring Thresholds

Edit `topic_scorer.py`:

```python
# Line ~210 - Confidence threshold
if match.get('discussed', False) and match.get('confidence', 0) > 0.6:
                                                                    ↑
                                                         Change this (0.6 = 60%)
```

### Change Episode Mix

Edit `topic_curator.py`:

```python
CATEGORY_CONFIG = {
    'shocking_news': {
        'target_per_episode': 3,  # ← Adjust this
        ...
    }
}
```

## 📊 Advanced Features

### Filter by Score:
```bash
# Only show topics scoring 8+
python topic_curator.py add --min-score 8.0
```

### Scrape Specific Time Period:
```python
scraper.scrape_reddit_subreddit('nottheonion', time_filter='month', limit=50)
```

### Custom Episode Plan:
```python
curator = TopicCurator()
plan = curator.plan_next_episode(scored_data)
# Customize plan...
```

## 🐛 Troubleshooting

### "No topics found"
→ Reddit API rate limit. Wait 1 hour or add credentials.

### "Scoring failed"
→ Check ANTHROPIC_API_KEY in `.env`

### "Google Docs not connected"
→ Run `python setup_google_docs.py`

### Topics not in Google Doc
→ Manually copy from `topic_data/structured_topics.txt`

## 📈 Performance

### Cost Estimate:
- **Scraping**: Free (Reddit API)
- **Scoring 100 topics**: ~$0.50 in Claude API costs
- **Weekly total**: ~$2/month

### Time Savings:
- **Before**: 2-3 hours brainstorming topics
- **After**: 5 minutes running automation
- **Savings**: ~8-12 hours/month

## 🎓 Understanding the Scores

### 9-10 (Exceptional):
Viral potential, shocking + relatable, perfect for clips

### 7-8 (Great):
Strong episode content, good engagement potential

### 6-7 (Good):
Solid topics, use as variety/filler

### 4-6 (Mediocre):
Skip unless perfect fit

### 0-4 (Poor):
Auto-excluded from recommendations

## 🚀 Next Level

Want to go further?

### Ideas for Expansion:
1. **Twitter trending topics** integration
2. **TikTok viral sounds** as topic inspiration
3. **Audience suggestions** from comments/DMs
4. **Historical data analysis** - track which topics performed best
5. **A/B testing** - try different episode structures

### Analytics Dashboard:
Track which categories get most engagement, optimize mix over time.

## 💡 Pro Tips

1. **Don't be a slave to the scores** - Trust your gut too
2. **Mix in personal stories** - Best clips often combine curated + personal
3. **Refresh weekly** - Topics get stale fast
4. **Review discussed topics** - See patterns in what you actually cover
5. **Adjust categories** - Customize to your style over time

## 📞 Support

Issues? Check:
1. `topic_data/` folder for all outputs
2. Error messages in terminal
3. `.env` configuration
4. Reddit API rate limits

---

**You now have a data-driven topic engine powered by AI!**

Run `python weekly_topic_refresh.py` to get started.
