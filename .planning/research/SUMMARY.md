# Project Research Summary

**Project:** Podcast Automation — v1.2 Engagement & Smart Scheduling
**Domain:** Analytics feedback loop and data-driven scheduling for CLI-driven podcast production pipeline
**Researched:** 2026-03-18
**Confidence:** HIGH (architecture and stack), MEDIUM (features and pitfalls)

## Executive Summary

v1.2 adds an engagement feedback loop and smart scheduling layer on top of a mature, fully-functional production pipeline. The core challenge is not building new infrastructure — it is closing the loop between what gets posted and what actually performs, then feeding that signal back into clip selection, topic scoring, and upload timing. Research confirms this is achievable with minimal new dependencies (pandas 2.x, numpy 1.26.x, scipy) and two new standalone modules wired into existing pipeline integration points. The architecture is well-understood from direct code inspection and the approach is clear: build incrementally, gate on data availability, and never block the pipeline on missing history.

The single most important finding is a data cold-start constraint: the show has ~29 historical episodes, which is at the low edge of meaningful optimization. The correct sequence is (1) harden analytics collection infrastructure, (2) build the cross-episode history file and engagement scoring model, and (3) only then wire the optimizer into scheduling and clip selection. Any reversal of this order wastes implementation effort because the optimizer will have no data to act on. Industry-standard posting-time defaults (Tuesday/Wednesday for YouTube, Tuesday morning for Twitter) should function as fallbacks until the show's own data crosses the 5-episode-per-platform threshold.

The primary risks are not technical. The engagement score formula weights YouTube at 70%, which can erode the show's dark-comedy voice over time if optimization pressure is allowed to narrow topic variety. A second risk is the YouTube Data API v3 quota: running analytics alongside uploads in a shared project can exhaust the 10,000 daily units. Both risks have clear mitigations documented in the pitfalls research, and both must be addressed in Phase 1 before any feedback loop is activated.

## Key Findings

### Recommended Stack

The v1.2 stack additions are deliberately minimal. Three packages are added: `pandas>=2.0.0,<3.0.0` for cross-episode DataFrame analysis, `numpy>=1.26.4,<2.0.0` (constrained by torch 2.1.0 compatibility), and `scipy>=1.11.0,<2.0.0` for statistical significance testing. Everything else — YouTube Analytics API v2, posting time heuristics, content optimization, A/B significance testing — uses existing packages already in requirements.txt. scikit-learn and statsmodels were evaluated and rejected: the dataset (n≈30 episodes) is too small for ML regression without severe overfitting, and simple correlation analysis via scipy.stats is statistically honest at this scale. Flag scikit-learn for v1.3 when episode count exceeds 50.

**Core technologies:**
- `pandas>=2.0.0,<3.0.0`: Cross-episode DataFrame analysis — only statistically honest tool for groupby aggregation at this scale without over-engineering
- `numpy>=1.26.4,<2.0.0`: Constrained by torch 2.1.0 — do not upgrade to 2.x until torch compatibility is verified
- `scipy>=1.11.0,<2.0.0`: Pearson/Spearman correlation for topic-engagement relationships; t-test/chi-square for A/B significance
- `google-api-python-client==2.116.0` (existing): Builds `youtubeAnalytics/v2` service alongside existing `youtube/v3` — no new package needed
- `openai>=1.0.0` (existing): GPT-4o content optimization already integrated; extend with engagement-informed prompts
- Python stdlib `statistics`: Posting-time recommendation arithmetic — no new package

### Expected Features

The feature set divides cleanly on data availability: P1 features deliver value with zero episodes of history; P2 features require 10+ episodes of accumulated analytics; P3 features are v2+ material.

**Must have (table stakes — P1, v1.2 launch):**
- Multi-episode analytics aggregation (`python main.py analytics all`) — baseline feedback mechanism; reads all existing ep_N_analytics.json files
- Topic-engagement history writer — persists episode+topic+score to `topic_data/topic_engagement_history.json` after each analytics run; foundation for all optimization
- Platform best-time defaults in config — replace bare `SCHEDULE_X_DELAY_HOURS` with named windows (`tue-wed-18-21`); backward-compatible with existing offset values
- Hashtag config + injection — `TWITTER_HASHTAGS` in config.py; inject top 1-2 tags in Twitter captions from `content_editor.py`; zero data dependency, immediate value
- Clip video_id tracking — store Shorts `video_id` in episode output JSON during YouTube upload; enables per-clip analytics retrieval

**Should have (data-derived — P2, after 10+ episode history):**
- Data-derived optimal posting windows — own-data analysis per platform; auto-configure scheduler once 10+ episodes exist
- Category performance report — average engagement per topic category; feeds into topic scorer
- YouTube description formatting — front-load timestamps and keywords in first 200 chars before upload

**Defer (v2+):**
- Per-clip engagement analytics deep-dive — clip position, duration, topic correlation with Shorts performance
- Automated best-clip selection using historical engagement signal — replace energy-only scoring with hybrid model
- Instagram and TikTok analytics integration — blocked on uploaders being functional and API access approved

### Architecture Approach

Two new standalone modules (`engagement_scorer.py`, `posting_time_optimizer.py`) are injected into existing pipeline steps at the same integration points already used for `topic_context` and `UploadScheduler`. Both modules read from a new shared file `topic_data/engagement_history.json` (one entry per episode per platform, accumulated via `run_analytics()`). The optimizer injects into `distribute.py` via an optional parameter on `UploadScheduler.create_schedule()`; the scorer injects into `analysis.py` alongside the existing topic_context mechanism. No new pipeline steps are numbered. No existing module signatures break — all new parameters are `Optional` with `None` defaults that preserve current behavior exactly.

**Major components:**
1. `engagement_scorer.py` — reads `ep_N_analytics.json` files and `engagement_history.json`; produces `engagement_profile` dict (high-performing categories, keywords, confidence level) for AI clip selection; appends new outcomes to history via `record_outcome()`
2. `posting_time_optimizer.py` — reads `engagement_history.json`; returns optimal posting datetime or `None` if below minimum episode threshold; consumed by `UploadScheduler.get_optimal_publish_at()`
3. `topic_data/engagement_history.json` — shared rolling JSON file (capped at 104 entries); atomic `.tmp`-rename write to match existing scheduler.py safe-write pattern; zero-dependency on all callers when absent

### Critical Pitfalls

1. **Cold start produces noise recommendations** — Enforce `ENGAGEMENT_HISTORY_MIN_EPISODES=5` threshold before `suggest_time()` returns anything other than `None`. Below threshold, log "Insufficient history for platform X — using fixed offset" and fall through to static delays. Phase 1 must build data collection before Phase 3 enables optimization.

2. **Engagement score erodes comedy voice** — YouTube's 70% weight in the composite score will systematically favor broadly accessible content over dark comedy. Treat comedy voice as a constraint (binary editorial override), not a variable. Never automate topic selection; engagement scores are ranking hints for hosts, not decisions. Phase 2 must bake this constraint into the scoring model design.

3. **YouTube API quota exhaustion** — `search().list()` costs 100 quota units per episode lookup. Fix during Phase 1: store `video_id` at upload time in `upload_schedule.json` (avoids the search call entirely). Run analytics collection as a separate scheduled task, never inside the production pipeline run.

4. **Twitter free-tier impressions gap** — `impression_count` is not available on the free tier; it returns 0. This biases the composite engagement score. Fix: treat impressions as `null` (unknown) not `0`; null-guard the formula before building any scoring on top of it.

5. **topic_scorer episode number bug** — `get_engagement_bonus()` uses loop index (`i + 1`) instead of actual episode number, silently mapping bonuses to wrong episodes. Fix in Phase 2 before the engagement feedback loop is wired; add a regression test.

## Implications for Roadmap

Based on combined research, the dependency graph drives a clear three-phase structure. Phase 1 must precede Phases 2 and 3 because all optimization work depends on clean analytics data. Phase 2 precedes Phase 3 because the engagement profile feeds into the scheduler's content signal.

### Phase 1: Analytics Infrastructure Hardening

**Rationale:** All optimization work depends on clean, reliable, quota-safe analytics data. Four distinct infrastructure problems must be fixed before any feedback loop is activated: quota exhaustion, Twitter impressions gap, stub uploader detection, and gitignore coverage of analytics files. Building the cross-episode history accumulator also belongs here — it has zero dependencies and starts collecting data that Phase 2 consumes.

**Delivers:** Reliable per-episode analytics; `engagement_history.json` accumulator; `python main.py analytics all` aggregation report; video_id stored at upload time; Twitter impressions null-guarded; TikTok/Instagram excluded from scheduling targets; `topic_data/analytics/` in .gitignore.

**Addresses:** Multi-episode analytics aggregation (P1), topic-engagement history writer (P1), clip video_id tracking (P1), platform best-time defaults in config (P1), hashtag injection (P1 — zero data dependency, implement here for immediate value)

**Avoids:** YouTube quota exhaustion (Pitfall 4), Twitter free-tier impressions gap (Pitfall 5), stub uploaders silently no-op (Pitfall 6), analytics data committed to git (security)

**Research flag:** Standard patterns — direct code inspection complete; well-understood extension of existing analytics.py; no additional research needed.

### Phase 2: Engagement Scoring Model

**Rationale:** With history accumulation in place from Phase 1, the scoring model can be built and tested with real data. The episode number bug in topic_scorer must be fixed here before the feedback loop is wired. The comedy voice constraint must be baked into the model design — not added as a post-hoc patch.

**Delivers:** `engagement_scorer.py` with `get_engagement_profile()` and `record_outcome()`; `pipeline/context.py` engagement_profile field; analysis step injection; category performance report; topic_scorer episode number bug fixed; `test_engagement_scorer.py`.

**Uses:** pandas 2.x, scipy.stats Pearson/Spearman correlation

**Implements:** Pattern 2 (Engagement Profile Injected into AI Clip Selection from ARCHITECTURE.md)

**Avoids:** Comedy voice erosion (Pitfall 2), false confidence from small samples (Pitfall 1), topic_scorer episode number bug

**Research flag:** Needs research-phase attention — comedy engagement scoring is domain-specific; confidence interval documentation for n=30; how to prevent engagement bias from narrowing topic variety without explicit editorial structure.

### Phase 3: Smart Scheduling

**Rationale:** The optimizer can only produce meaningful recommendations after Phase 1 has been accumulating data for multiple weeks. Phase 3 wires the optimizer into the scheduler with the confidence gate established in architecture research. Platform algorithm cold-start mechanics must be understood before timing changes go live.

**Delivers:** `posting_time_optimizer.py`; `scheduler.py` `get_optimal_publish_at()` method; distribute step integration; `runner.py` component initialization; `SMART_SCHEDULING_ENABLED` and `ENGAGEMENT_HISTORY_MIN_EPISODES` config env vars; `test_posting_time_optimizer.py`.

**Uses:** Python stdlib statistics, engagement_history.json from Phase 1

**Implements:** Pattern 3 (Smart Schedule as Optional Extension) and Pattern 4 (Confidence-Gated Optimization from ARCHITECTURE.md)

**Avoids:** Scheduler optimization without accounting for platform algorithm decay (Pitfall 3), scheduler signature breakage (Anti-Pattern 3), false confidence from small samples (Pitfall 1)

**Research flag:** Needs research-phase attention for platform cold-start window mechanics — YouTube Shorts and Twitter first-hour amplification behavior should be documented per-platform before timing changes are deployed. Twitter 15-minute engagement burst threshold and YouTube Shorts first-hour algorithm behavior are not confirmed in current research.

### Phase Ordering Rationale

- Phase 1 is a prerequisite for both Phases 2 and 3: quota-safe analytics and the engagement_history.json schema must exist before any scoring or optimization logic is built.
- Phase 2 before Phase 3: `engagement_scorer.py` produces the `engagement_profile` that eventually informs the optimizer's content signal; fixing the episode number bug before Phase 3 prevents corrupt data in the feedback loop.
- P1 features with zero data dependency (hashtag injection, best-time config defaults) belong in Phase 1 for early wins — they do not need to wait for analytics history.
- P2 features (data-derived posting windows, category performance) require Phase 1 to have run for 2-4 weeks before they deliver meaningful signal.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2:** Comedy-specific engagement scoring — how to prevent feedback loop from narrowing topic variety; confidence interval documentation for n=30; comedy engagement non-linearity (bimodal distribution of "lands vs misses")
- **Phase 3:** Per-platform cold-start mechanics — YouTube Shorts first-hour amplification threshold; Twitter 15-minute engagement burst mechanics; whether "when audience is online" differs materially from "optimal algorithm amplification window"

Phases with standard patterns (skip research-phase):
- **Phase 1:** Direct code inspection complete; quota limits documented in official Google/Twitter developer docs; extension patterns are well-established in existing codebase

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Version constraints verified against pinned deps (torch 2.1.0 forces numpy<2.0); YouTube Analytics API v2 confirmed against official dimension reference; scikit-learn rejection is well-reasoned |
| Features | MEDIUM | Industry best-time defaults from Buffer/Sprout Social (millions of posts) but niche comedy podcast may diverge; hashtag engagement data is directional only (LOW confidence source) |
| Architecture | HIGH | Derived from direct code inspection of all integration modules; patterns mirror existing codebase conventions; concrete interface signatures provided |
| Pitfalls | MEDIUM-HIGH | YouTube/Twitter quota limits from official docs (HIGH); comedy voice erosion and cold-start thresholds from practitioner sources (MEDIUM); platform algorithm cold-start mechanics unconfirmed |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Twitter impressions availability:** Free tier does not provide `impression_count`. Before Phase 1 is complete, verify what the show's current Twitter API tier actually returns and whether upgrading to Basic ($100/month) is justified. The engagement score formula is biased if impressions silently returns 0.

- **YouTube Analytics API v2 OAuth scope:** The existing YouTube OAuth credentials may not include `https://www.googleapis.com/auth/yt-analytics.readonly`. Building the `youtubeAnalytics/v2` service may require a credentials update and re-authorization before Phase 1 analytics work can be tested end-to-end.

- **pandas already in requirements.txt:** Check whether pandas is already present as a transitive dependency before adding it. If present at a conflicting version, the version constraint update may require a full `pip install -r requirements.txt` rebuild.

- **TikTok audit status:** TikTok Content Posting API requires app audit approval before posts are public. Phase 1 should document the current audit status; if unaudited, exclude TikTok from all scheduling work and do not queue posts until audit is complete.

- **Engagement history bootstrap:** ~29 historical episodes already exist. Backfilling `engagement_history.json` would accelerate the optimizer's learning. However, backfilling YouTube analytics via search costs 100 quota units per episode. The video_id storage fix (Phase 1) must be in place before any backfill is attempted to avoid quota exhaustion.

## Sources

### Primary (HIGH confidence)
- YouTube Analytics API Dimensions Reference (developers.google.com/youtube/analytics/dimsmets/dims) — confirmed no hourly/day-of-week dimension; only `day` and `month` available
- YouTube Analytics API Reports Query (developers.google.com/youtube/analytics/reference/reports/query) — query structure for date-segmented video stats
- YouTube Data API v3 Quota documentation (developers.google.com/youtube/v3/determine_quota_cost) — quota unit costs per operation
- Twitter/X API rate limits (developer.twitter.com/en/docs/rate-limits) — free tier restrictions
- TikTok Content Posting API documentation (developers.tiktok.com/products/content-posting-api/) — audit requirement for public posts
- Direct code inspection: analytics.py, scheduler.py, pipeline/runner.py, pipeline/steps/, topic_scorer.py, audio_clip_scorer.py, pipeline/context.py

### Secondary (MEDIUM confidence)
- Buffer 2026 Best Times to Post on Social Media (7M+ posts analyzed) — posting time defaults
- Buffer 2026 Best Time to Post on Twitter/X (1M posts analyzed) — Twitter timing defaults
- Sprout Social 2025 Best Times to Post on YouTube — YouTube timing defaults
- Engagement scoring model common mistakes — Accrease practitioner guide
- Best time to release a podcast — Lower Street (notes generic benchmarks don't apply to niche audiences)
- Recency bias in analytics — Amplitude (analytics platform vendor)

### Tertiary (LOW confidence)
- Hashtag engagement data (1-2 hashtags doubles engagement) — directional signal only; single source; treat as hypothesis to test with own data
- YouTube Shorts shadowban and algorithm penalties — corroborated by multiple sources but no official confirmation of specific threshold mechanics

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
