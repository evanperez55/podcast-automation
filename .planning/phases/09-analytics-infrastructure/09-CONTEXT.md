# Phase 9: Analytics Infrastructure - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden analytics data collection so every episode produces reliable, quota-safe metrics that accumulate into a cross-episode engagement history file. Also: hashtag injection into Twitter posts (immediate value, zero data dependency) and stub platform detection. This phase does NOT build the scoring model or scheduling optimizer — those are Phases 10 and 11.

</domain>

<decisions>
## Implementation Decisions

### Engagement History Format
- Per-episode granularity (not per-clip) — one entry per episode per analytics run
- Store ALL available metrics from both APIs (views, likes, comments, impressions, engagements, retweets) plus post_timestamp and episode topics
- Keep everything forever — no rolling window. ~30 episodes/year keeps file tiny
- Collection happens during `python main.py analytics` command, NOT during pipeline run (metrics don't exist at upload time)
- File location: `topic_data/engagement_history.json`

### Hashtag Strategy
- AI-generated per episode using clip_hashtags from content_editor.py's existing GPT-4o output
- 2 hashtags per Twitter post (top 2 from clip_hashtags)
- Twitter only for now (Instagram uploader is a stub)
- Appended as separate line at bottom of tweet, not inline

### Stub Detection Behavior
- Log warning + skip: `[SKIP] Instagram: uploader not functional`
- Detection at init time via .functional flag on each uploader
- Dry run shows stub status: `[MOCK] Instagram: STUB (not functional)`
- Matches existing graceful-skip patterns (like webpage deploy without GITHUB_TOKEN)

### Video ID Persistence
- Store in episode output JSON (output/epN/) — natural location, already written during pipeline
- Store ALL platform IDs: YouTube video_id + Twitter tweet_id
- One-time backfill command `python main.py backfill-ids` for existing episodes (ep1-29) using YouTube search API
- After backfill, analytics never needs search API again — direct video ID lookups only

### Claude's Discretion
- Exact engagement_history.json schema structure
- How to detect stub vs functional uploader (method signature check, config flag, or try/catch)
- Backfill command implementation details (batch size, rate limiting)
- Twitter free-tier impression_count null handling approach (null vs exclude from score)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `uploaders/youtube_uploader.py`: Already returns `{"video_id": video_id, ...}` in upload response (line 215)
- `content_editor.py`: Already generates `clip_hashtags` per clip via GPT-4o (line 309)
- `analytics.py`: `AnalyticsCollector` with `fetch_youtube_analytics()` and `fetch_twitter_analytics()` — foundation for history accumulation
- `analytics.py`: `EngagementScorer.calculate_engagement_score()` — existing formula uses impressions (line 246)

### Established Patterns
- `self.enabled` env-var gating on all modules — stub detection should follow this pattern
- Episode output stored in `output/epN/` directory with JSON data files
- Graceful skip pattern: check condition, log warning, return None (used by webpage deploy, compliance checker)
- `topic_data/` directory used for analytics JSON files

### Integration Points
- `pipeline/steps/distribute.py`: Upload results available after each platform upload — video_id can be captured here
- `analytics.py`: `fetch_youtube_analytics()` and `fetch_twitter_analytics()` — extend to write engagement_history.json
- `scheduler.py`: `create_schedule()` — stub detection should prevent creating schedule entries for non-functional platforms
- `pipeline/runner.py`: `_init_components()` — stub detection flags set here

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches following existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-analytics-infrastructure*
*Context gathered: 2026-03-18*
