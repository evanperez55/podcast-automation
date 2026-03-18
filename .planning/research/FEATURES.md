# Feature Research

**Domain:** Podcast engagement optimization and smart scheduling for a CLI-driven production pipeline
**Researched:** 2026-03-18
**Milestone:** v1.2 — Engagement & Smart Scheduling
**Confidence:** MEDIUM

---

## Context: What Already Exists (Do Not Re-Build)

These are built and fully integrated. New features must work *with* them, not replace them.

| Module | What It Does | Integration Point for v1.2 |
|--------|--------------|---------------------------|
| `analytics.py` (`AnalyticsCollector`) | Fetches YouTube views/likes/comments and Twitter impressions/engagements/retweets/likes per episode; saves to `topic_data/analytics/ep_N_analytics.json` | Read historical data to derive posting-time patterns and topic-engagement correlation |
| `analytics.py` (`TopicEngagementScorer`) | Computes 0–10 composite score from YouTube+Twitter data; `correlate_topics()` maps episode titles to scores | Already feeds into `topic_scorer.py` as `engagement_bonus`; extend to drive scheduling decisions |
| `scheduler.py` (`UploadScheduler`) | Applies configurable hour-offsets per platform from `.env`; `create_schedule()` writes `upload_schedule.json` with per-platform ISO datetimes | Replace static offsets with data-derived optimal windows |
| `topic_scorer.py` (`TopicScorer`) | LLM-scores topic ideas (shock value, relatability, absurdity, hook, visual) via Ollama/Llama; `engagement_bonus` already a stub field on every score | Backfill `engagement_bonus` with historical topic-performance data |
| `content_editor.py` | Generates episode title, summary, show notes, chapter markers, social captions per platform via GPT-4 | Social captions go directly to uploaders; v1.2 can inject hashtag and timing signals here |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any engagement-aware pipeline should have. Missing them means leaving easy wins on the table.

| Feature | Why Expected | Complexity | Dependency on Existing | Notes |
|---------|--------------|------------|------------------------|-------|
| Platform-specific optimal posting time windows | Every scheduling tool (Buffer, Hootsuite) ships default best-time windows; hardcoded hour-offsets in scheduler.py are the baseline but not data-driven | LOW | Extends `UploadScheduler`; replaces static delays | Industry data: YouTube 5–9 AM or Tue/Wed 6–9 PM; Twitter Tue–Thu 9–11 AM, 12–2 PM; treat as starting defaults until own data accumulates |
| Multi-episode analytics aggregation command | Creators expect `python main.py analytics all` to produce a roll-up view across episodes; the current command only handles single episodes | LOW | Extends `analytics.py`; `python main.py analytics all` stub already exists | Read all `ep_N_analytics.json` files and compute averages, trends, top performers |
| Engagement trend reporting (episodes over time) | Without a trend view, there's no signal for what's improving; this is the most basic analytics feedback | LOW | Reads existing per-episode JSON files from `analytics.py` | Compute engagement score per episode chronologically; output table or CSV |
| Analytics data written back to scheduling decisions | The point of analytics is to inform scheduling; a feedback loop that doesn't close on scheduling is incomplete | MEDIUM | Connects `AnalyticsCollector` output → `UploadScheduler` input | Core of the milestone; replaces `.env` hour-offset defaults with computed windows |
| Topic-to-engagement history lookup | When scoring new topics, knowing that "gas-powered adult toys" scored 8.5 engagement historically is valuable | LOW | `TopicEngagementScorer.correlate_topics()` already exists; just need to accumulate the corpus | Write episode engagement + topic keywords to a persistent `topic_engagement_history.json` after each analytics run |

### Differentiators (Competitive Advantage)

Features beyond the baseline that improve content quality and engagement prediction.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-platform best-time analysis derived from own data | Generic industry best-time data is noise for a specific niche podcast; own historical data wins over industry averages | MEDIUM | Requires accumulating 5–10 episodes of analytics with known post times; parse `collected_at` vs engagement score and find correlation; viable after ~10 episodes | Compute per-platform engagement score vs hour-of-day from historical records; output recommended hour windows |
| Engagement-weighted hashtag recommendations for Twitter | Tweets with 1–2 hashtags get double the engagement; the right hashtags for a dark comedy podcast differ from general podcast hashtags | LOW | Extend `content_editor.py` social caption generation; add hashtag list to config; no new API needed | Maintain a `config.py` list of known-high-performing hashtags for the show; inject top 1–2 into Twitter caption |
| YouTube Shorts vs full-episode engagement split tracking | Tracking which clips perform best (by topic, clip position, duration) informs future `audio_clip_scorer.py` weighting | MEDIUM | Extend `analytics.py` to fetch stats for each uploaded Short's `video_id`; store alongside episode analytics | YouTube Data API v3 `videos.list` already used for full episode; same call works for Shorts |
| Content category engagement correlation | If "shocking news" topics consistently outperform "absurd hypothetical" topics for this audience, the topic scorer should weight accordingly | MEDIUM | Cross-reference `topic_scorer.py` category field with `TopicEngagementScorer` output; needs at least 10 episodes of history | Compute average engagement score per category; write to `topic_data/category_performance.json`; load in `topic_scorer.py` |
| Best-performing clip position report | Does clip 1 (intro of episode) always outperform clip 3? Knowing this helps `audio_clip_scorer.py` preference early high-energy moments | LOW | Analytics already stores `video_id` per episode; extend to store clip index and fetch per-clip stats | Tag each clip Short upload with its clip index (0, 1, 2); track separately in analytics |
| Smart description/show notes optimization hints | YouTube descriptions with timestamps, keywords, and links in the first 200 chars perform better; the pipeline already generates show notes via GPT-4 | LOW | Post-process `show_notes` from `content_editor.py` before YouTube upload; ensure timestamps appear early | Add a description-formatting function that front-loads keywords and timestamps extracted from chapter data |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time audience activity dashboard | "Know when your audience is online" sounds useful | Requires always-on web server; this is a CLI pipeline; real-time requires WebSocket or polling infrastructure; not compatible with `python main.py ep29 --auto-approve` workflow | Compute audience activity windows in batch from historical data; write recommendations to a report file |
| A/B testing different clip thumbnails or captions | Split testing is how SaaS tools differentiate | Requires uploading the same content twice with variants; burns YouTube upload quota; Twitter API rate limits are strict; doubles processing time; introduces state management for variant tracking | Use engagement trend analysis to observe natural variation across episodes; manually vary elements once per release and observe |
| ML engagement prediction model (train-from-scratch) | Predicting future engagement before posting sounds appealing | Requires 50–100+ labeled episodes to train reliably; the show doesn't have that history yet; would produce low-confidence predictions at current scale; BERT models for podcast engagement prediction require 80%+ training accuracy to be useful | Use LLM-based topic scoring (already built) + historical category performance lookup; this delivers actionable signal with < 10 episodes of data |
| Cross-platform analytics dashboard (web UI) | Unified view of all platforms in one place | Building a web UI is a separate project; requires a web framework, hosting, auth; completely out of scope for a CLI pipeline | Output a Markdown or CSV report to `output/analytics_report.md` that can be opened in any editor or spreadsheet |
| Instagram analytics integration | Instagram in scope | Instagram API (Meta Graph API) for analytics requires a Business or Creator account; the Instagram uploader is a stub; analytics can't precede working upload | Defer until Instagram uploader is complete and account is configured; add placeholder in analytics structure |
| TikTok analytics integration | TikTok in scope | TikTok Analytics API is gated behind TikTok for Developers approval; uploader is a stub; same problem as Instagram | Defer until TikTok uploader is complete; same defer rationale |
| Automatic posting time switching mid-schedule | "If engagement is low, reschedule" | Modifying already-created schedules requires re-fetching upload state; the current `upload_schedule.json` model uses `status: pending/uploaded/failed`; mid-run rescheduling creates reconciliation complexity | Apply optimal windows at schedule creation time; don't attempt to adjust after the fact |

---

## Feature Dependencies

```
Engagement Trend Report
    └── requires: multi-episode analytics aggregation (python main.py analytics all)
    └── requires: historical ep_N_analytics.json files (already written by analytics.py)

Optimal Posting Time Windows (data-derived)
    └── requires: engagement trend data with known post timestamps
    └── requires: at least 5-10 episodes of analytics history
    └── enhances: UploadScheduler (replaces static hour-offsets)

Topic-Engagement History Corpus
    └── requires: TopicEngagementScorer.correlate_topics() (already exists)
    └── requires: multi-episode analytics aggregation
    └── enhances: topic_scorer.py engagement_bonus (already a stub field)

Category Performance Lookup
    └── requires: topic-engagement history corpus
    └── requires: topic_scorer.py category field per scored topic
    └── enhances: topic scoring weights for future episodes

Per-Clip Shorts Analytics
    └── requires: clip video_id stored during YouTube upload step
    └── requires: analytics.py YouTube fetch (already works for full episodes)
    └── enhances: audio_clip_scorer.py (informs clip position/duration weighting)

Hashtag Optimization
    └── requires: config.py hashtag list (new config entry)
    └── enhances: content_editor.py social caption generation (Twitter)
    └── independent: can be added without analytics history
```

### Dependency Notes

- **Optimal posting time windows require episode history:** The pipeline processes roughly one episode per week. A meaningful data-derived best-time model needs 5–10 episodes with known post times and resulting engagement. Build the data accumulation infrastructure first (Phase 1), derive recommendations second (Phase 2).
- **Per-clip Shorts analytics require clip video_id tracking:** The YouTube uploader must store the Shorts `video_id` per clip in the episode output (e.g., `episode_data.json`). This is a small addition to the upload step that unlocks clip-level analytics.
- **Hashtag optimization is independent:** It requires only a config list and a text-processing step in `content_editor.py`. Ship it early — zero analytics data dependency, immediate value.
- **Category performance conflicts with small dataset:** With fewer than 10 episodes, category averages are statistically unreliable (1–2 episodes per category). Don't gate topic scoring on this until corpus is large enough.

---

## MVP Definition

### Launch With (v1.2 core)

Minimum viable set that closes the analytics feedback loop without over-engineering.

- [ ] Multi-episode analytics aggregation (`python main.py analytics all`) — reads all saved JSON files, computes engagement trend table, outputs to stdout and `topic_data/analytics_report.md`
- [ ] Topic-engagement history writer — after each `analytics` run, appends episode title + topics + engagement score to `topic_data/topic_engagement_history.json`
- [ ] Platform best-time defaults in config — replace bare hour-offsets with named time windows (e.g., `SCHEDULE_YOUTUBE_WINDOW=tue-wed-18-21`) that encode day-of-week + hour range; keep backward-compatible with bare hour offsets
- [ ] Hashtag config + injection — add `TWITTER_HASHTAGS` to config.py; inject top 1–2 tags into Twitter social caption in `content_editor.py`
- [ ] Clip video_id tracking — store each uploaded Shorts `video_id` in episode output JSON; fetch per-clip stats in `analytics.py`

### Add After Validation (v1.2.x)

Add once 10+ episodes of analytics history are accumulated.

- [ ] Data-derived optimal posting windows — analyze own post-time vs engagement history; output recommended windows per platform; auto-configure scheduler
- [ ] Category performance report — compute average engagement score per topic category; surface in analytics report; feed into topic scorer
- [ ] YouTube description optimization — format show notes to front-load timestamps and keywords in first 200 chars before upload

### Future Consideration (v2+)

Defer until the show has substantial audience data and these features provide clear lift.

- [ ] Per-clip engagement analytics deep-dive — clip position, duration, and topic correlation with Shorts performance
- [ ] Automated best-clip selection using historical engagement signal — replace energy-only scoring in `audio_clip_scorer.py` with hybrid energy + topic engagement model
- [ ] Instagram and TikTok analytics integration — blocked on uploaders being complete and API access approved

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-episode analytics aggregation | HIGH | LOW | P1 |
| Hashtag config + injection | HIGH | LOW | P1 |
| Topic-engagement history writer | HIGH | LOW | P1 |
| Platform best-time defaults (named windows) | MEDIUM | LOW | P1 |
| Clip video_id tracking for Shorts | MEDIUM | LOW | P1 |
| Data-derived posting windows (own data) | HIGH | MEDIUM | P2 |
| Category performance report | MEDIUM | MEDIUM | P2 |
| YouTube description formatting | MEDIUM | LOW | P2 |
| Per-clip analytics deep-dive | LOW | MEDIUM | P3 |
| Hybrid clip scoring (energy + engagement) | MEDIUM | HIGH | P3 |
| Instagram/TikTok analytics | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.2 launch — closes the basic feedback loop
- P2: Should have once 10+ episodes of data exist — requires history to be useful
- P3: Nice to have — future milestone material

---

## Competitor Feature Analysis

This is a single-creator CLI pipeline, not a SaaS competitor. Comparison is against what tools like Buffer, Hootsuite, and Headliner offer — to identify what to replicate at zero cost vs what to skip.

| Feature | Buffer / Hootsuite / Headliner | Our Approach |
|---------|-------------------------------|--------------|
| Best-time scheduling | ML model trained on millions of accounts; per-account audience activity graph | Industry defaults in config; own-data analysis after 10+ episodes; acceptable for indie podcast |
| Cross-platform analytics dashboard | Web UI with charts, comparisons, exports | Markdown/CSV report to file; readable in any editor; zero infra |
| A/B testing content variants | Upload variants, measure winner | Skip — quota and rate-limit risk; use natural variation observation instead |
| Hashtag suggestions | Real-time trending hashtag lookup via API | Static curated list in config; podcast hashtags are stable (not trending-dependent) |
| Clip selection AI | Automated highlight detection | Already built: `audio_clip_scorer.py` energy scoring; enhance with historical topic correlation |
| Engagement prediction | Pre-publish score estimate | LLM topic scoring already does this; add historical category signal as modifier |

---

## Sources

- [Best time to post on YouTube — Sprout Social 2025](https://sproutsocial.com/insights/best-times-to-post-on-youtube/) — MEDIUM confidence (industry aggregate, not account-specific)
- [Best time to post on Twitter/X — Buffer 2026, 1M posts analyzed](https://buffer.com/resources/best-time-to-post-on-twitter-x/) — MEDIUM confidence (industry aggregate)
- [Best times to post on social media — Sprout Social 2025](https://sproutsocial.com/insights/best-times-to-post-on-social-media/) — MEDIUM confidence
- [YouTube Analytics and Reporting APIs — Google for Developers](https://developers.google.com/youtube/analytics) — HIGH confidence (official docs)
- [YouTube Analytics metrics reference — Google for Developers](https://developers.google.com/youtube/analytics/metrics) — HIGH confidence (official docs)
- [Podcast engagement prediction research — ResearchGate (71–81% accuracy with BERT)](https://www.researchgate.net/publication/352397814_Modeling_Language_Usage_and_Listener_Engagement_in_Podcasts) — MEDIUM confidence (academic paper)
- [Hashtag engagement on Twitter — 1–2 hashtags doubles engagement](https://chrismakara.com/tweet-analytics/) — LOW confidence (WebSearch only, treat as directional)
- [Twitter A/B testing overview](https://www.twitter-follower.com/en/blog/twitter-ab-testing-campaign-optimization) — LOW confidence (WebSearch only)
- [Podcast analytics metrics guide — Brand24 2026](https://brand24.com/blog/podcast-metrics/) — MEDIUM confidence (WebSearch)

---
*Feature research for: podcast engagement optimization (v1.2 milestone)*
*Researched: 2026-03-18*
