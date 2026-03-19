---
phase: 09-analytics-infrastructure
plan: "01"
subsystem: analytics
tags: [analytics, platform-ids, engagement-history, twitter, youtube, tdd]
dependency_graph:
  requires: []
  provides: [platform_ids_json, engagement_history_json, impression_null_sentinel, video_id_param]
  affects: [analytics.py, pipeline/steps/distribute.py]
tech_stack:
  added: []
  patterns: [upsert-by-episode-number, null-sentinel-for-missing-data, optional-param-for-api-cost-reduction]
key_files:
  created: [tests/test_distribute.py]
  modified: [analytics.py, pipeline/steps/distribute.py, tests/test_analytics.py]
decisions:
  - impression_count=0 treated as None sentinel (not zero) to distinguish free-tier limitation from actual zero impressions
  - platform_ids.json written as separate file in episode_output_dir (not merged into existing results JSON)
  - _engagement_history_path() exposed as method to allow test patching via patch.object
  - engagement_history upsert keyed on episode_number to prevent duplicate records on re-runs
metrics:
  duration_minutes: 13
  tasks_completed: 2
  files_modified: 4
  completed_date: "2026-03-19"
---

# Phase 9 Plan 01: Analytics Infrastructure — Platform IDs, Engagement History, and Impression Null Guard Summary

**One-liner:** Platform ID persistence at upload time, cross-episode engagement_history.json accumulator with upsert, and Twitter free-tier impression null sentinel using TDD.

## What Was Built

### ANLYT-01: Platform ID Capture at Upload Time

`_upload_to_social_media()` in `pipeline/steps/distribute.py` now accepts an `episode_output_dir` parameter. After YouTube and Twitter uploads complete, it writes `platform_ids.json` to that directory containing the `video_id` and `tweet_id`. This eliminates expensive YouTube search API calls (100 quota units) during analytics runs — future analytics can pass `video_id` directly to `fetch_youtube_analytics()`.

`fetch_youtube_analytics()` in `analytics.py` now accepts an optional `video_id: Optional[str] = None` parameter. When provided, the search API call is skipped entirely and it goes directly to `videos().list(id=video_id)` (1 quota unit vs 100).

`run_distribute()` passes `episode_output_dir` to `_upload_to_social_media()`.

### ANLYT-02: Twitter Impression Null Guard

`fetch_twitter_analytics()` now tracks `impression_data_available = False`. Only when a tweet returns a non-zero `impression_count` is the flag set True and the value accumulated. The returned dict uses `None` as the impressions value when all tweets return zero or absent `impression_count` — distinguishing "API didn't provide data" from "genuinely zero impressions."

`calculate_engagement_score()` now guards against `None` impressions with `tw_impressions = tw.get("impressions") or 0` before multiplying, preventing `TypeError`.

### ANLYT-03: Engagement History Accumulation

`AnalyticsCollector` has two new methods:

- `_engagement_history_path()` — returns `Config.BASE_DIR / "topic_data" / "engagement_history.json"`. Exposed as a method (not hardcoded) so tests can patch it via `patch.object`.
- `append_to_engagement_history(episode_number, analytics_data, platform_ids, topics, post_timestamp)` — loads existing history (or starts empty list), builds a record matching the schema from RESEARCH.md, upserts by `episode_number`, and writes back with `indent=2`. Twitter impressions stored as-is (None when null).
- `_load_platform_ids(episode_number)` — reads `output/ep_{N}/platform_ids.json` for analytics callers.

## Verification

```
pytest tests/test_distribute.py tests/test_analytics.py -k "platform_ids or impression or engagement_history or video_id"
# 11 passed

pytest tests/test_distribute.py tests/test_analytics.py
# 26 passed, 1 pre-existing failure (TestAnalyticsCollectorInit::test_collector_init_disabled)

pytest
# 443 passed, 2 pre-existing failures (analytics init + audiogram enabled defaults)

ruff check analytics.py pipeline/steps/distribute.py tests/test_distribute.py tests/test_analytics.py
# All checks passed
```

## Decisions Made

1. **None as impression sentinel** — `impression_count=0` on free tier is treated as `None` (not zero). This prevents Phase 10 from scoring a free-tier API limitation as "zero engagement performance."
2. **Separate `platform_ids.json`** — Written as a new file alongside existing output JSON rather than merging into the existing `*_results.json`. Avoids risk of corrupting files written earlier in the pipeline.
3. **`_engagement_history_path()` as method** — Allows test isolation via `patch.object(collector, '_engagement_history_path', return_value=tmp_path/...)` without patching global Config.
4. **Upsert by episode_number** — Re-running `python main.py analytics` for the same episode updates the existing record rather than duplicating it.

## Deviations from Plan

### Commit Attribution Note

The implementation files (`analytics.py` and `pipeline/steps/distribute.py`) were committed as part of commit `b88b7b6` (labeled as 09-02) due to git staging overlap during the stash/unstash cycle used to verify pre-existing test failures. The code changes are correct and all tests pass — the commit label is the only deviation.

## Self-Check: PASSED

All files found on disk. All commits confirmed in git log:
- `d31ff47` — test(09-01): failing tests (RED phase)
- `b88b7b6` — implementation (GREEN phase, included in 09-02 commit label)
