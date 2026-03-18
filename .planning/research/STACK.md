# Technology Stack

**Project:** Podcast Automation — v1.2 Engagement & Smart Scheduling
**Researched:** 2026-03-18
**Confidence:** HIGH (core recommendations), MEDIUM (ML prediction), LOW (Twitter time-of-day via API)

---

## Existing Stack (Do Not Replace)

These are validated, working dependencies. Not candidates for replacement or re-research.

| Technology | Version (pinned) | Role |
|------------|-----------------|------|
| Python | 3.12+ | Language |
| FFmpeg binary | C:\ffmpeg\bin\ffmpeg.exe | Media processing engine |
| openai | >=1.0.0 | GPT-4o for content optimization |
| tweepy | 4.14.0 | Twitter API v2 — already fetches public_metrics |
| google-api-python-client | 2.116.0 | YouTube Data API + YouTube Analytics API v2 |
| praw | 7.7.1 | Reddit topic research |
| analytics.py | — | Existing: collects YouTube views/likes/comments, Twitter impressions/engagements |
| scheduler.py | — | Existing: stores publish_at timestamps per platform, executes uploads |

---

## New Stack Additions (v1.2 Only)

### 1. Time-Series Statistics: pandas + numpy + scipy

**Recommended:**
- `pandas>=2.0.0,<3.0.0` (use 2.x for now — pandas 3.0 dropped Python 3.11 support and has breaking changes; stay on 2.x until torch compatibility is verified)
- `numpy>=1.26.4,<2.0.0` (torch 2.1.0 in requirements.txt requires numpy < 2.0 — do not upgrade to numpy 2.x yet)
- `scipy>=1.11.0,<2.0.0` (for `scipy.stats` — chi-square tests, t-tests for A/B significance)

**Why:** The engagement optimization work requires:
1. Loading all saved `topic_data/analytics/ep_*_analytics.json` files into a single DataFrame for cross-episode analysis
2. Grouping analytics by episode metadata (topic category, day of week posted, time posted) to find patterns
3. Running statistical significance tests when comparing two posting time slots (scipy.stats.ttest_ind or chi2_contingency)

pandas provides the DataFrame model that makes this trivial — `df.groupby('day_of_week').agg({'views': 'mean'})` vs writing nested dicts manually. scipy.stats provides the t-test and chi-square tests needed to determine if an engagement difference is real or noise.

**Why not statsmodels for full ARIMA/time-series forecasting:** The project has ~30 episodes max of historical data. ARIMA requires at minimum 50 data points for meaningful forecasting. statsmodels adds ~10MB, pulls in patsy, and provides capabilities far beyond what's needed. Simple mean/percentile analysis per day-of-week bucket is appropriate for this data volume.

**Why not scikit-learn:** sklearn's LinearRegression would fit neatly for "predict engagement from features" but the dataset is too small (30 data points) for ML predictions that aren't overfit. scipy.stats correlation coefficients (Pearson, Spearman) are statistically honest at this scale.

**Version compatibility note:** `torch==2.1.0` (already pinned) requires `numpy>=1.21,<2`. pandas 2.x works with numpy 1.26.x. pandas 3.0.1 (released January 2026) requires Python 3.11+ and has breaking changes from 2.x. Stay on pandas 2.x to avoid requirements conflict risk.

```bash
pip install "pandas>=2.0.0,<3.0.0" "numpy>=1.26.4,<2.0.0" "scipy>=1.11.0,<2.0.0"
```

**Confidence:** HIGH for pandas 2.x + numpy 1.26.x compatibility with torch 2.1.0. MEDIUM for scipy version range (no known conflicts found, but not explicitly verified against all existing deps).

---

### 2. YouTube Analytics API v2 (youtubeanalytics/v2)

**Recommended:** No new package. Use existing `google-api-python-client==2.116.0`.

**Why:** The YouTube Analytics API v2 is a separate service from the YouTube Data API v3 but uses the same `googleapiclient.discovery.build()` pattern already used in `analytics.py`. The only addition is building a second service:

```python
youtube_analytics = build("youtubeAnalytics", "v2", credentials=creds)
```

**What this unlocks:** `reports.query()` with `metrics=views,estimatedMinutesWatched,averageViewDuration` grouped by `dimensions=day`. This gives daily performance data per video — the existing `analytics.py` only fetches total-lifetime stats via the Data API, not date-segmented analytics. Date-segmented data enables: "videos posted on Tuesday get 23% more views in first 7 days than videos posted Thursday."

**Critical limitation discovered:** The YouTube Analytics API does NOT have an hourly dimension or day-of-week dimension. Available time dimensions are only `day` and `month`. The "when your viewers are on YouTube" heatmap in YouTube Studio is NOT accessible via API — it is a Studio-only visualization. There is no `audienceActivity` or `viewerHour` metric available programmatically (verified against official dimensions reference at developers.google.com/youtube/analytics/dimsmets/dims).

**Implication for architecture:** Optimal posting time for YouTube must be derived by:
1. Fetching 7-day rolling view data per posted video using `dimensions=day`
2. Calculating "first-7-day views" for each episode grouped by day_of_week_posted
3. Using published research as a baseline (Tuesday 2-4 PM, Sunday 10 AM - 12 PM consistently cited in Buffer/Sprout Social 2025-2026 data)
4. Blending own historical data with research defaults when sample size < 10

No new package needed.

**Confidence:** HIGH for API capability scope. HIGH for limitation (verified against official dimension reference). MEDIUM for the research-based time defaults (Buffer 2026 data based on millions of posts, but may not match a niche comedy podcast audience).

---

### 3. Posting Time Heuristics: Built-in statistics module

**Recommended:** Python stdlib `statistics` module — no new package.

**Why:** For computing optimal posting windows from historical data, Python's built-in `statistics.mean()`, `statistics.median()`, and `statistics.stdev()` are sufficient alongside the pandas groupby aggregation. No new package needed.

The posting time optimizer logic is:
1. Load all episode analytics JSONs (views + date posted)
2. Group by day_of_week: `{monday: [views_list], tuesday: [views_list], ...}`
3. `statistics.mean()` per group → ranking
4. Blend with research defaults (weighted average: own data gets weight proportional to sample count, research defaults fill the gaps)

```python
from statistics import mean, stdev
```

This is intentionally kept stdlib-only because at 30 episodes, pandas groupby or scipy is sufficient for the cross-platform analysis, and the time-slot recommendation itself is simple arithmetic.

**Confidence:** HIGH — stdlib, no versioning concern.

---

### 4. Engagement Prediction: scipy.stats (already included above)

**Recommended:** `scipy.stats.pearsonr`, `scipy.stats.spearmanr` — included in scipy package above.

**Why this instead of scikit-learn:** Engagement prediction at this scale is "which topic categories have correlated with higher engagement historically?" The right tool is correlation analysis, not ML regression. With 30 data points, a LinearRegression model will overfit. Pearson/Spearman correlation between `topic_category_encoded` and `engagement_score` (already computed in analytics.py) reveals the direction and strength of the relationship without overfitting risk.

For future milestone (when 50+ episodes exist): scikit-learn LinearRegression or GradientBoosting becomes appropriate. Flag this for v1.3.

**Feature inputs available right now:**
- `topic_category` from topic_scorer.py (`shocking_news`, `absurd_hypothetical`, etc.)
- `engagement_score` from TopicEngagementScorer.calculate_engagement_score()
- `day_of_week` posted (derivable from analytics JSON `collected_at`)
- `clip_count` (episodes with more clips get more Twitter posts)

**Confidence:** MEDIUM — correlations at n=30 have wide confidence intervals. The pipeline should present findings with honest caveats ("based on 30 episodes, Tuesday posts average 18% higher views — recommend more data before treating as definitive").

---

### 5. Content/Subject Optimization: OpenAI GPT-4o (already in stack)

**Recommended:** Existing `openai>=1.0.0`. No new package.

**Why:** Content optimization — rewriting titles, captions, and thumbnails to improve engagement — is a natural language task. GPT-4o already powers content_editor.py for show notes and captions. Extending it to "suggest three alternative video titles ranked by predicted click-through" requires zero new libraries: just a new prompt in `content_editor.py`.

The engagement prediction output (which categories perform best) feeds back as context into the GPT-4o prompt: "Previous shocking_news episodes averaged engagement score 7.2. The current episode is shocking_news. Suggest titles that emphasize the shocking angle."

**Confidence:** HIGH — already integrated, zero new dependency risk.

---

### 6. A/B Test Significance: scipy.stats (already included above)

**Recommended:** `scipy.stats.ttest_ind` and `scipy.stats.chi2_contingency` — already in scipy package.

**Why:** If the pipeline tests two different thumbnail styles or caption formats across episodes, statistical significance testing determines if the difference is real. For view counts (continuous): `ttest_ind`. For engagement rate (proportion): `chi2_contingency`. Both are in scipy.stats.

**Important constraint:** True A/B testing requires randomized assignment and control of confounders — hard to achieve with weekly episodic content. The realistic implementation is "A/B" across time: old approach vs. new approach, measured across comparable episodes. scipy.stats ttest provides the p-value, but the codebase should document this limitation clearly.

**Confidence:** HIGH for scipy tools. LOW for statistical validity of A/B results in this context (n is small, confounders exist).

---

## Packages Evaluated and Rejected (v1.2)

| Package | Use Case | Decision | Reason |
|---------|----------|----------|--------|
| `statsmodels>=0.14.6` | ARIMA/time-series forecasting | Rejected | Overkill for n<50 episodes. Simple mean-by-group analysis is statistically honest at this scale. Adds 10MB+ and patsy dependency |
| `scikit-learn>=1.8.0` | ML engagement prediction | Rejected for v1.2 | n=30 is too small for ML regression without severe overfitting. scipy correlation is appropriate now. Flag for v1.3 when n>50 |
| `prophet` (Meta) | Time-series forecasting | Rejected | Requires PyStan + heavy C++ compilation. Overkill for weekly podcast data at n<50 |
| `APScheduler>=3.11` | Cron-based scheduling | Rejected | Scheduler.py already handles `publish_at` timestamps. APScheduler adds a daemon/background process, which conflicts with the project's CLI-run-and-exit execution model |
| `celery` | Task queue for scheduled uploads | Rejected | Requires Redis/RabbitMQ broker. Massively overengineered for a single-user local CLI pipeline |
| `tweepy_analytics` (third-party) | Twitter engagement timing | Rejected | Not a real package. Twitter API v2 via existing tweepy already provides `public_metrics` |
| `buffer` / `hootsuite` API | Social media management | Rejected | Paid APIs. Project constraint: no new paid APIs |
| `pandas>=3.0.0` | Data analysis | Rejected for now | Breaking changes from 2.x; requires Python 3.11+ minimum; compatibility with torch 2.1.0 needs verification |
| `numpy>=2.0.0` | Numerical computing | Rejected | torch 2.1.0 requires numpy<2.0 |

---

## Full Dependency Delta (v1.2 additions)

Libraries to add to `requirements.txt`:

```
# Engagement analytics — time-series stats and significance testing
pandas>=2.0.0,<3.0.0
numpy>=1.26.4,<2.0.0   # Constrained by torch==2.1.0 compatibility
scipy>=1.11.0,<2.0.0
```

Everything else for v1.2 uses existing packages:
- YouTube Analytics API v2: existing `google-api-python-client==2.116.0`
- Content optimization prompts: existing `openai>=1.0.0`
- Posting time heuristics: Python stdlib `statistics`
- Topic correlation: `scipy.stats` (added above)

---

## Integration Points with Existing Code

| New Component | Integrates With | What Changes |
|--------------|----------------|--------------|
| `engagement_optimizer.py` (new) | `analytics.py` — reads existing analytics JSONs | Adds cross-episode DataFrame analysis on top of existing per-episode collection |
| `posting_time_advisor.py` (new) | `scheduler.py` — replaces hardcoded `SCHEDULE_*_DELAY_HOURS` config with computed optimal windows | `create_schedule()` receives `optimal_times` dict instead of fixed delays |
| `content_optimizer.py` (new) | `content_editor.py` — adds engagement-informed title/caption rewriting | New method on existing class or standalone module with same GPT-4o client |
| YouTube Analytics API v2 | `analytics.py` — add `fetch_youtube_video_performance()` method | Queries `youtubeanalytics/v2` for 7-day segmented view data per video |
| `TopicEngagementScorer` | `topic_scorer.py` — already exists, already adds engagement_bonus | Extend to use correlation output from engagement_optimizer.py |

---

## Architecture Note: Data Flow for Optimal Posting Time

The YouTube Analytics API does not expose hour-of-day viewer activity. The "When your viewers are on YouTube" heatmap in YouTube Studio has no API equivalent. The posting time recommendation must therefore be derived from:

1. **Own historical data** (available): day_of_week each episode was posted + 7-day view performance from Analytics API v2
2. **Research-based defaults** (embedded as constants): Tuesday/Wednesday 2-4 PM for YouTube; Tuesday 9 AM for Twitter/X; weekday evenings for Instagram; weekday mornings for TikTok (Buffer 2026 data, 7M+ posts analyzed)
3. **Blending rule**: Weight own data by `min(1.0, episodes_posted_on_this_day / 5)`. Under 5 episodes posted on a given day, research defaults dominate.

This approach is honest about data limitations and avoids overfitting to a small sample.

---

## Version Compatibility Matrix

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| pandas | >=2.0.0,<3.0.0 | numpy 1.26.x, Python 3.12 | pandas 3.x breaks compat with numpy 1.x |
| numpy | >=1.26.4,<2.0.0 | torch==2.1.0 | torch 2.1 breaks with numpy>=2.0 |
| scipy | >=1.11.0,<2.0.0 | numpy 1.26.x | scipy 1.17.1 is latest (Jan 2026); 1.11+ safe lower bound |
| google-api-python-client | 2.116.0 | youtubeanalytics/v2 | Same client builds both youtube/v3 and youtubeAnalytics/v2 |

---

## Sources

- [YouTube Analytics API Dimensions Reference](https://developers.google.com/youtube/analytics/dimsmets/dims) — confirmed no hourly or day-of-week dimension exists (only `day` and `month`)
- [YouTube Analytics API Reports Query](https://developers.google.com/youtube/analytics/reference/reports/query) — query structure for date-segmented video stats
- [Buffer 2026 Best Times to Post on Social Media](https://buffer.com/resources/best-time-to-post-social-media/) — research defaults for posting windows (millions of posts analyzed)
- [Buffer Best Time to Post on Twitter/X 2026](https://buffer.com/resources/best-time-to-post-on-twitter-x/) — 1 million posts analyzed
- [Buffer Best Time to Post on TikTok 2026](https://buffer.com/resources/best-time-to-post-on-tiktok/) — 7 million posts analyzed
- [pandas PyPI](https://pypi.org/project/pandas/) — 3.0.1 latest (Jan 2026), 2.x LTS available
- [numpy PyPI](https://pypi.org/project/numpy/) — 2.4.3 latest (Mar 2026), 1.26.x still maintained
- [scipy releases](https://docs.scipy.org/doc/scipy/release.html) — 1.17.1 latest (Feb 2026)
- [scikit-learn PyPI](https://pypi.org/project/scikit-learn/) — 1.8.0 latest; rejected for v1.2 due to sample size
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — 3.11.2 latest; rejected (daemon model conflicts with CLI pipeline)
- [PyTorch Python 3.12 compatibility](https://discuss.pytorch.org/t/compatibility-of-python-3-12-with-py-torch/219215) — torch 2.1 + Python 3.12 works; numpy<2.0 required

---

*Stack research for: Engagement optimization and smart scheduling additions to podcast-automation pipeline*
*Researched: 2026-03-18*
