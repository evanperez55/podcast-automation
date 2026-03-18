# Pitfalls Research

**Domain:** Podcast automation pipeline — engagement optimization and smart scheduling
**Researched:** 2026-03-18
**Confidence:** MEDIUM-HIGH
**Milestone:** v1.2 Engagement & Smart Scheduling

---

## Critical Pitfalls

Mistakes that cause rewrites, gaming violations, or feedback loops that actively harm the show.

---

### Pitfall 1: Cold Start Makes Optimization Meaningless Until You Have Enough Data

**What goes wrong:**
Optimization algorithms trained on fewer than ~20-30 episodes of per-platform analytics data produce recommendations that reflect noise, not signal. The engagement score formula in `analytics.py` (weighted YouTube views/likes/comments + Twitter impressions/engagements) will confidently output numbers regardless of sample size. Routing posting decisions through these scores before sufficient history exists means the system is effectively randomizing with extra steps while appearing data-driven.

**Why it happens:**
Engineers wire up the feedback loop immediately because it is technically possible. The formula produces a number for every episode, so there is no failure signal — it just silently optimizes against noise. Weekly episodes with ~29 historical data points at the start of v1.2 development means the dataset is already at or near the minimum viable size, but confidence intervals are still wide for platform-specific timing decisions.

**Consequences:**
- Posting time recommendations derived from 5-8 data points per platform have wide confidence intervals that make them interchangeable with any other time
- "Shock value" and "absurdity" scoring (from `topic_scorer.py`) that gets tuned against early engagement data will overfit to whatever topics happened to land in episode 1-15, not to enduring show characteristics
- Feedback loop amplifies whatever performed well early, narrowing topic variety over time

**How to avoid:**
- Implement a minimum sample threshold (recommend: 15+ episodes with non-null analytics for a given platform) before trusting any optimization recommendation; below this threshold, fall back to static schedule defaults
- Separate "data collection" mode (run analytics, store data, make no automated changes) from "optimization" mode (actually shift schedules based on data)
- Display confidence intervals alongside recommendations: "Tuesday 7pm shows 12% lift over baseline — based on 8 data points (low confidence)"
- Use a holdout: one episode per quarter posted at a random time to prevent the system from losing its reference point

**Warning signs:**
- Optimization recommendations change drastically week to week (suggests insufficient data, not a real trend)
- All platform recommendations converge on the same day/time window (possible artifact of correlated early data, not a genuine finding)
- Topic recommendations start excluding entire categories that performed poorly in episodes 1-5

**Phase to address:** Phase 1 (data collection infrastructure), before any scheduling automation is enabled.

---

### Pitfall 2: Overfitting the Engagement Score to YouTube at the Expense of Comedy Voice

**What goes wrong:**
The current engagement formula weights YouTube at 70% (7/10 points) and Twitter at 30% (3/10 points). If topic selection and clip strategy are optimized against this score, the show will gradually drift toward whatever YouTube's algorithm rewards for long-form podcast content — which for a comedy podcast is almost certainly not the edgy/dark humor content that defines the show's identity.

YouTube rewards watch time and session extension, which favors moderate, broadly accessible content with no controversial elements. The compliance checker in v1.1 already flags borderline content. An engagement-optimized feedback loop compounds this by deprioritizing the high-shock-value, dark-humor topics that generate the most shares and loyal listeners — even if those topics get slightly fewer YouTube views.

**Why it happens:**
View counts are easy to measure. Audience loyalty, cult following, and word-of-mouth from "I can't believe they said that" moments are not measured by any API. The optimization system will maximize what it can see, which does not include the show's actual growth driver.

**Consequences:**
- Topic scorer's `shock_value` and `absurdity` dimensions get systematically downweighted as the engagement bonus reinforces safe topics
- Clip selection shifts toward informational moments rather than comedy peaks
- The show sounds like a generic podcast within 6-12 months; existing audience stops recommending it to friends
- The ep29 YouTube strike risk (cancer misinformation) creates pressure to avoid anything that could be flagged, which the engagement optimizer will internalize as a signal to avoid controversy entirely

**How to avoid:**
- Treat show voice as a constraint, not a variable. The engagement optimizer should only choose between options that already pass the show's comedy voice criteria — not reweight the criteria themselves
- Add a "comedy signal" metric that captures comments/shares rather than views (comments on comedy content skew toward reactions to edgy moments, not general engagement)
- Regularly review what the optimizer is recommending against what the hosts would actually choose — if they diverge consistently, the model is wrong
- Never automate topic selection; use scores as a ranking hint for hosts to choose from, not as a replacement for host judgment

**Warning signs:**
- Recommended topics become progressively less edgy over time without explicit host feedback
- Clip selection favors factual discussion segments over joke exchanges
- The compliance checker flags an increasing percentage of high-scoring topics (the scorer is recommending content that the safety gate rejects — a sign the two systems are not aligned)

**Phase to address:** Phase 2 (engagement scoring model design). Bake comedy constraints into the scoring model before wiring the feedback loop.

---

### Pitfall 3: Scheduler Optimization Without Accounting for Platform Algorithm Decay

**What goes wrong:**
Scheduling logic in `scheduler.py` currently adds static hour delays from config. Smart scheduling would shift these based on historical engagement data. However, social media algorithms front-load distribution — most of a post's total reach is delivered in the first 1-6 hours after publication. If the scheduler chooses a time when the hosting account has below-average engagement velocity (e.g., a slow Tuesday afternoon), the platform's algorithm interprets weak early signals as a quality signal and throttles reach for the remaining 48 hours.

**Why it happens:**
Developers optimize for "when the audience is online" without accounting for the platform's cold-start detection window. The two are correlated but not identical: the best time to post is when enough active users will engage quickly, not just when the most users are present.

**Consequences:**
- Posting at the "optimal" time derived from historical data produces lower engagement than the historical baseline because the historical data reflects total reach, not early-window engagement velocity
- YouTube Shorts and TikTok are particularly sensitive to first-hour metrics for algorithmic amplification decisions
- Twitter/X's timeline algorithm similarly front-loads distribution; a post that doesn't hit 10+ engagements in 30 minutes gets deprioritized from non-follower feeds

**How to avoid:**
- Distinguish between "follower online time" data (from platform analytics) and "optimal post time" (which requires knowing the platform's cold-start window length)
- For YouTube Shorts, prefer morning posts (6-9am in target timezone) where platform activity is ramping up; avoid late night even if followers are online then (algorithm won't amplify to non-followers at low-activity hours)
- For Twitter, the 15-minute engagement burst matters more than overall daily peak; recommend times adjacent to lunch breaks and commute windows when rapid engagement is likely
- Build in a manual review step before changing post times automatically — this is high-leverage and hard to reverse

**Warning signs:**
- Platform analytics show normal follower reach but below-normal non-follower reach (suggests the algorithm front-loaded but didn't amplify)
- Post-by-post engagement variance increases after enabling smart scheduling (high variance = the optimizer is not actually finding a stable optimum)

**Phase to address:** Phase 3 (smart scheduling). Research each platform's amplification mechanics before implementing timing changes.

---

### Pitfall 4: YouTube Data API v3 Quota Exhaustion from Analytics Collection

**What goes wrong:**
`analytics.py` uses `search().list()` to find episode videos (100 quota units per call) then `videos().list()` to fetch stats (1 unit per call). The default YouTube Data API quota is 10,000 units per day per project. Running analytics collection for 29+ episodes costs 29 * 100 = 2,900 units for the search calls alone — in addition to whatever quota is used by the uploader during the same day. If video upload (1,600 units each), search queries, and analytics collection all run in the same project quota, a single day's pipeline run can exhaust quota before analytics finish.

**Why it happens:**
The analytics module was built before the uploader was operational. Now that uploads happen through the same project credentials, both compete for the same 10,000-unit daily quota. Backfilling analytics for all historical episodes (29+ calls) burns through quota immediately.

**Consequences:**
- Pipeline fails mid-episode with `quotaExceeded` error — this can break the upload step if it runs after analytics
- Retry logic that does not check quota remaining will hammer the API until suspended
- Quota suspension can lock out the channel for 24 hours, blocking episode publication

**How to avoid:**
- Cache analytics results in `topic_data/analytics/ep_N_analytics.json` (already done) and never refetch if the file exists and is less than 7 days old
- Store video IDs after upload (`analytics.py` gets `video_id` from search — this should instead be stored during upload in `schedule.json` and reused for analytics, avoiding the 100-unit search call entirely)
- Separate the analytics collection into a distinct scheduled task (run once per week, not as part of the production pipeline)
- Add quota-aware rate limiting: check current day's quota before running analytics; skip gracefully if under 2,000 units remaining
- Consider using the YouTube Reporting API for batch analytics pulls (much more quota-efficient for aggregate data)

**Warning signs:**
- `analytics.py` returns `None` for multiple episodes in a row (quota exhausted, not actually missing data)
- Pipeline log shows 429 or `quotaExceeded` errors during the upload or analytics step
- YouTube Studio shows the video uploaded successfully but analytics shows no data

**Phase to address:** Phase 1 (analytics infrastructure hardening) before expanding analytics collection scope.

---

### Pitfall 5: Twitter/X API Rate Limits Make Real-Time Analytics Unreliable

**What goes wrong:**
`analytics.py` uses `tweepy.Client.search_recent_tweets()` to find episode mentions. The Twitter API v2 free tier limits this to 500,000 tweets per month total with rate limits of 1 search request per 15 minutes on the basic tier. The current implementation searches `f"Episode {episode_number} {Config.PODCAST_NAME}"` — a query that will return very few results for a small-audience comedy podcast, burning rate limit budget for near-zero data.

Additionally, the free tier only provides `public_metrics` on tweets from the last 7 days. Episodes older than 7 days return no data, so any historical analytics backfill returns null for Twitter data across most of the catalog.

**Why it happens:**
Twitter/X degraded its free API tier in 2023-2024. The existing `fetch_twitter_analytics()` code was written before these restrictions tightened. The `public_metrics` field (`impression_count`) requires at least Basic access ($100/month) — the free tier only provides `reply_count`, `retweet_count`, `like_count`, and `quote_count` without impression data.

**Consequences:**
- `impressions` field always returns 0 on the free tier, making the Twitter score component of `calculate_engagement_score()` systematically undercount
- Rate limit exhaustion from analytics polling blocks the pipeline's own Twitter posting step
- Stale data (7-day window) means the Twitter engagement score reflects only the first week of each episode's life, not its total performance

**How to avoid:**
- Decouple analytics collection from the production pipeline; run it as a separate weekly task
- For Twitter metrics, substitute own-account metrics (use `tweepy.Client.get_users_tweets()` with the show's account ID and look up the episode tweet by URL match — this requires fewer rate limit calls and returns more reliable data for owned tweets)
- Cap Twitter analytics collection to the most recent 3-5 episodes (the ones still within the 7-day recency window)
- Remove `impression_count` from the engagement score or treat it as optional — it is not available on the free tier and returning 0 biases the formula

**Warning signs:**
- `fetch_twitter_analytics()` returns impressions: 0 consistently across all episodes
- Pipeline logs show tweepy rate limit warnings during the distribution step
- Twitter engagement score component is always the minimum (0.0) despite the show having active Twitter presence

**Phase to address:** Phase 1 (analytics infrastructure). Fix the impressions field assumption before building any scoring on top of it.

---

### Pitfall 6: TikTok and Instagram Uploaders Are Stubs — Scheduling Them Will Silently No-Op

**What goes wrong:**
`scheduler.py` schedules TikTok and Instagram uploads based on configurable delays. The `uploaders/` directory contains stub implementations for both platforms. If smart scheduling is added without first verifying which uploaders are functional, the scheduler will queue posts for platforms that can never actually publish them — creating a false sense that distribution is happening.

TikTok's Content Posting API in 2025 additionally requires app audit approval before any content can be posted publicly (unaudited apps post to private accounts only). Instagram's API for feed/Reels posting requires a Meta Business account linked to a Facebook Page and goes through a different OAuth flow than Stories.

**Why it happens:**
The scheduler was built for the eventual state where all uploaders exist. The stub pattern means the pipeline doesn't crash — it silently does nothing and marks the platform as "pending" forever.

**Consequences:**
- Hours optimized for TikTok never actually post
- The engagement feedback loop receives no data from these platforms despite the scheduler reporting "queued"
- When the uploaders are eventually implemented, the scheduler already has stale queued entries that may execute at wrong times

**How to avoid:**
- Add a `is_functional()` method to each uploader that returns `False` for stubs; the scheduler should skip platforms where `is_functional()` is `False` and log a warning
- Do not include TikTok or Instagram in engagement optimization until their uploaders are verified functional end-to-end
- TikTok: factor in the API audit requirement as a prerequisite task — this can take weeks; do not build scheduling logic around an unaudited app
- Document which platforms are functional vs. stub in `PROJECT.md` and update it as each becomes operational

**Warning signs:**
- `upload_schedule.json` shows `status: pending` for TikTok/Instagram entries that are weeks old
- No engagement data exists for these platforms despite the scheduler showing them as queued
- The pipeline marks these as "done" with 0 analytics data, silently skewing cross-platform comparisons

**Phase to address:** Phase 1 (pre-optimization audit). Verify functional uploader list before any scheduling optimization targets platform-specific timing.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `search().list()` to find episode video IDs | No code changes needed to analytics.py | Burns 100 quota units per episode lookup; blocks uploads if quota exhausted | Never — store video ID during upload instead |
| Collecting analytics inside the production pipeline run | Feedback data available immediately after episode | Delays publish, risks quota exhaustion, shares rate limit budget with upload | Never — run analytics collection on a separate schedule |
| Applying engagement scores to all historical episodes at once | Full dataset available sooner | Quota exhaustion on YouTube + Twitter rate limit on first batch run | Never — backfill incrementally (1-2 episodes per day) |
| Using industry-generic "best time to post" defaults | Quick to implement | Ignores actual audience timezone and behavior; often wrong for edgy/niche content | Only as cold-start fallback, never as final answer |
| Letting the engagement optimizer also adjust topic selection | Simpler architecture | Erodes comedy voice without explicit editorial override | Never — keep scoring as a hint, not an automated decision |
| Treating impression_count as 0 on free tier without flagging | No API change needed | Systematically undervalues Twitter in composite score, biasing against Twitter-heavy episodes | Never — mark impressions as `null` (unknown), not 0 |

---

## Integration Gotchas

Common mistakes when connecting to the existing analytics and scheduler infrastructure.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| YouTube Data API analytics | Fetching analytics immediately after upload (data takes 24-48 hours to populate) | Schedule analytics collection 48+ hours after publication; check for null stats before scoring |
| YouTube Data API quota | Running analytics + upload in the same pipeline invocation without quota tracking | Separate analytics into a distinct scheduled task; never share quota budget with upload |
| Twitter public_metrics | Assuming `impression_count` is available on free tier | Only `reply_count`, `retweet_count`, `like_count`, `quote_count` are free; impressions require Basic ($100/month) |
| Existing scheduler.py | Adding time-optimization logic directly to `create_schedule()` | Add a separate `optimize_schedule(base_schedule, analytics_data)` function; keep `create_schedule()` unchanged |
| analytics.py engagement score | Applying raw score as a boost to topic_scorer without normalization | Episodes from 3+ years ago have lower raw counts due to smaller audience; normalize by episode age before comparing |
| topic_scorer.py engagement_bonus | Current code uses `i + 1` (loop index) as episode number — this is a bug | Fix the episode number mapping before using engagement bonus in any optimization |

---

## Performance Traps

Patterns that work at small scale but create problems as episode count grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Scanning all analytics JSON files to compute baseline | Slow analytics report generation | Pre-aggregate baseline statistics into a `analytics_summary.json` file; update incrementally | At ~50 episodes (seconds of lag become minutes) |
| Storing full analytics history in memory during pipeline run | Memory spikes when computing rolling averages | Load only the N most recent episodes needed for the calculation window | At ~100 episodes with large response payloads |
| Re-running `search().list()` on every analytics refresh | Quota exhaustion from repeated lookups | Store video_id in `upload_schedule.json` at upload time; analytics reuses stored ID | At 20+ episodes per batch refresh |
| YouTube Reporting API large report downloads | Timeouts and memory issues | Stream and parse incrementally; don't load entire report into memory | Reports over ~50MB |

---

## Security Mistakes

Domain-specific security issues for analytics and scheduling.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing raw platform API responses (including user data) in analytics JSON | Privacy violation if repo is public or if JSON is accidentally committed | Strip PII from API responses before saving; store only aggregated metrics |
| Using `YOUTUBE_CHANNEL_ID` as public-facing identifier in logs | Channel ID leakage if logs are shared | Treat channel ID as a credential; redact from log output |
| Committing analytics JSON to git | Historical engagement data is private; public repo exposes it | Add `topic_data/analytics/` to `.gitignore`; verify it is not currently tracked |
| Scheduling posts to Instagram/TikTok before OAuth tokens are verified | Tokens expire silently; posts queue forever | Add token validity check before scheduling; alert if token expires within 7 days |

---

## Comedy Content Specific Risks

Pitfalls unique to edgy/dark humor podcasts that don't apply to mainstream content.

### The Compliance-Optimization Contradiction

The v1.1 compliance checker (GPT-4o at temp=0.1) flags content that violates YouTube guidelines. The engagement optimizer rewards content that generates strong reactions. For a comedy podcast, these two systems will systematically conflict: the funniest, most shareable clips are often the ones that brush closest to compliance boundaries.

**Risk:** The compliance gate + engagement optimization creates a filter that progressively narrows the show's range toward content that is "safe but dull." Over time, the hosts notice that the pipeline keeps rejecting or deprioritizing their best material and lose confidence in the automation.

**Prevention:** The compliance checker should remain a binary gate (pass/fail) with clear, documented thresholds — not a continuous scoring dimension that gets factored into the engagement model. High engagement on content that passes compliance is a signal to keep making that content, not a signal to push content toward compliance limits.

### Edgy Comedy Engagement Is Non-Linear

Dark humor content tends to have bimodal engagement: either it lands (high shares, strong comment reactions) or it misses entirely (low engagement, comments criticizing the joke). The engagement score formula uses linear arithmetic (views * 0.001 + likes * 0.1 + comments * 0.5). Comments on a joke that didn't land still count the same as comments on one that did.

**Risk:** The optimizer learns that controversy generates comments and starts optimizing for controversy rather than quality comedy. Episodes that generate angry comments and episodes that generate delighted comments receive similar composite scores.

**Prevention:** If comment sentiment becomes a signal, require sentiment classification (positive vs. negative comments). Without sentiment, exclude comment count from the score for comedy content and weight shares/saves higher (these are unambiguously positive signals). Alternatively, keep comments in the score but require a minimum like-to-comment ratio to filter out "controversy engagement" from "comedy engagement."

### Small Niche Audience Metrics Don't Generalize

Industry benchmarks for podcast engagement (average completion rates, click-through rates, subscriber conversion rates) are derived from mainstream content. A comedy podcast with 500-5,000 listeners that achieves 40% comment-to-listener ratio is performing extraordinarily well — but raw count comparisons to larger shows will make it look like low-engagement content.

**Risk:** Normalizing scores against absolute counts rather than relative audience size makes every metric look bad, leading to false conclusions that content quality is low when distribution reach is simply small.

**Prevention:** Always normalize engagement metrics by subscriber/listener count (engagement rate, not raw engagement). Track growth rate alongside absolute numbers. "Views per subscriber" is more meaningful than "total views" at this stage.

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Analytics collection:** Often appears to work in dry-run but silently fails in production because YouTube stats take 24-48 hours to populate — verify by waiting 48h and re-fetching
- [ ] **Smart scheduling:** Schedule JSON is created correctly, but verify the runner actually reads and applies it at upload time (not just stores it)
- [ ] **Engagement feedback loop:** Score is calculated and stored, but verify it is actually being read back by `topic_scorer.py`'s `engagement_bonus` logic (currently uses loop index as episode number — this is a bug)
- [ ] **Platform-specific timing:** Optimal time recommendations work in the local timezone — verify the pipeline stores and applies times in UTC-consistent format when the deployment timezone differs from audience timezone
- [ ] **TikTok/Instagram scheduling:** Appears queued in `upload_schedule.json` but verify these platforms have functional uploaders before treating scheduled entries as actionable

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| YouTube API quota exhausted mid-pipeline | LOW | Wait until midnight PT for quota reset; resume pipeline with `--resume` flag; add analytics caching immediately |
| Engagement feedback loop has overfit to early episodes | MEDIUM | Delete analytics files for episodes 1-10 (noisy early data); re-run scoring without engagement bonus; add minimum sample threshold gate |
| Scheduler posts at wrong time due to timezone bug | LOW | Re-queue the upload manually; fix timezone handling; add UTC offset test |
| Topic recommendations drifted away from show voice | HIGH | Disable engagement bonus in `topic_scorer.py`; revert topic scoring weights to pre-v1.2 defaults; host editorial review of last 5 scored batches |
| TikTok app unaudited — all posts are private | MEDIUM | Submit TikTok audit request; posts can be manually set to public once audit passes; do not queue more posts until audit approved |
| Twitter rate limit hit during distribution step | LOW | Re-run distribution step for Twitter after 15 minutes; add rate limit detection to analytics collection to prevent future conflicts |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cold start / insufficient data | Phase 1 — add minimum sample threshold before enabling optimization | Run analytics collection for 3+ weeks before enabling smart scheduling |
| Engagement score erodes comedy voice | Phase 2 — design scoring model with comedy constraints baked in | Hosts manually review top 10 optimized recommendations vs. what they would pick |
| Platform algorithm decay window not accounted for | Phase 3 — research platform cold-start mechanics before timing changes | Compare first-hour vs. 48-hour engagement by posting time bucket |
| YouTube quota exhaustion | Phase 1 — cache video IDs at upload time; separate analytics schedule | Verify analytics collection does not trigger quota warnings in pipeline log |
| Twitter free tier impressions gap | Phase 1 — remove or null-guard impressions field | Check engagement score formula returns correct value when impressions is None |
| Stub uploaders silently no-op | Phase 1 — audit functional uploader list | Run uploader `is_functional()` check and confirm TikTok/Instagram are excluded from scheduling targets |
| TikTok audit requirement | Phase 1 (discovery) / Phase 3 (execution) | Confirm audit status before scheduling any TikTok automation |
| Analytics stored in tracked git files | Phase 1 — verify `.gitignore` coverage | Run `git status` after analytics collection run; confirm no JSON files are staged |
| topic_scorer episode number bug (loop index) | Phase 2 — fix engagement_bonus mapping | Add test: verify `get_engagement_bonus(ep_number)` is called with actual episode number, not loop index |

---

## Sources

- [YouTube Data API v3 Quota and Compliance documentation](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits) — HIGH confidence (official Google docs)
- [YouTube Data API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost) — HIGH confidence (official Google docs)
- [Twitter/X API rate limits](https://developer.twitter.com/en/docs/rate-limits) — HIGH confidence (official X developer docs)
- [Twitter API free tier limitations and paid tiers](https://data365.co/guides/twitter-api-limitations-and-pricing) — MEDIUM confidence (verified against official docs)
- [TikTok Content Posting API overview](https://developers.tiktok.com/products/content-posting-api/) — HIGH confidence (official TikTok developer docs)
- [TikTok API audit requirement for public posting](https://developers.tiktok.com/doc/content-sharing-guidelines) — HIGH confidence (official TikTok developer docs)
- [Podcast analytics mistakes — Cohost](https://www.cohostpodcasting.com/resources/podcast-analytics-mistakes) — MEDIUM confidence (industry practitioner source)
- [Stop obsessing over vanity metrics — Podify](https://podify.com/stop-obsessing-over-vanity-metrics-the-podcast-data-that-actually-grows-your-show-in-2025/) — MEDIUM confidence (industry blog)
- [Best time to release a podcast — Lower Street](https://lowerstreet.co/blog/best-day-to-publish-podcast) — MEDIUM confidence, notes that generic benchmarks don't apply to niche audiences
- [Engagement scoring model common mistakes — Accrease](https://accrease.com/articles/building-an-engagement-scoring-model-for-analytics-data-a-step-by-step-guide/) — MEDIUM confidence (technical practitioner)
- [Recency bias in analytics — Amplitude](https://amplitude.com/explore/experiment/recency-bias) — HIGH confidence (analytics platform vendor)
- [YouTube Shorts shadowban and algorithm penalties — Trendly](https://trendly.so/blog/youtube-shorts-shadowban) — MEDIUM confidence (corroborated by multiple sources)
- Direct code reading: `analytics.py`, `scheduler.py`, `topic_scorer.py` — HIGH confidence (source of truth for existing implementation details)

---
*Pitfalls research for: engagement optimization and smart scheduling — Fake Problems Podcast v1.2*
*Researched: 2026-03-18*
