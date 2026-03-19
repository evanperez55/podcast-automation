---
phase: 09-analytics-infrastructure
plan: "03"
subsystem: analytics
tags: [analytics, youtube, backfill, platform-ids, engagement-history, tdd]

requires:
  - phase: 09-analytics-infrastructure/09-01
    provides: [_load_platform_ids, append_to_engagement_history, _build_youtube_client via fetch_youtube_analytics refactor]
provides:
  - backfill-ids CLI command in main.py
  - run_backfill_ids() in pipeline/runner.py
  - _collect_episode_analytics uses stored video_id (no search API calls)
  - _collect_episode_analytics calls append_to_engagement_history after each episode
  - _load_episode_topics() helper for clip titles from analysis JSON
  - collect_analytics() accepts optional video_id param
  - _build_youtube_client() extracted from fetch_youtube_analytics for reuse
affects: [Phase 10 — topic correlation scoring uses engagement_history.json]

tech-stack:
  added: []
  patterns: [tdd-red-green, _build_youtube_client-extracted-auth, optional-video_id-pass-through]

key-files:
  created: []
  modified:
    - analytics.py
    - pipeline/runner.py
    - pipeline/__init__.py
    - main.py
    - tests/test_analytics.py

key-decisions:
  - "_build_youtube_client() extracted from fetch_youtube_analytics to avoid duplicating pickle auth in backfill command"
  - "collect_analytics() updated with optional video_id param to propagate through to fetch_youtube_analytics"
  - "post_timestamp for engagement_history derived from platform_ids.json file mtime — accurate to within seconds of upload time"
  - "Topics extracted via _load_episode_topics() from *_analysis.json glob in episode output dir, same pattern as correlate_topics()"

requirements-completed: [ANLYT-01, ANLYT-03]

duration: 12min
completed: "2026-03-19"
---

# Phase 9 Plan 03: Backfill-IDs Command and Analytics Wiring Summary

**`python main.py backfill-ids` one-time backfill for ep1-29 plus analytics runs now use stored video IDs and accumulate engagement_history.json via TDD**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-19T00:40:09Z
- **Completed:** 2026-03-19T00:52:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments

- `python main.py backfill-ids` iterates output/ep_* dirs, searches YouTube for each episode without platform_ids.json, writes {"youtube": video_id, "twitter": None}, rate-limits at 1.5s/request, skips existing files (idempotent)
- `python main.py analytics all` now loads stored video_id from platform_ids.json and passes it to collect_analytics() — skips 100-quota YouTube search API call per episode
- Each analytics run calls append_to_engagement_history() to accumulate cross-episode engagement_history.json for Phase 10 correlation scoring
- Extracted `_build_youtube_client()` from `fetch_youtube_analytics()` so backfill can reuse the pickle-based auth without duplication

## Task Commits

Each task was committed atomically:

1. **Task 1: Tests for backfill command and analytics wiring (RED)** - `64e8d84` (test)
2. **Task 2: Implement backfill-ids and wire analytics** - `7dd5ffb` (feat)

_TDD: 6 tests added in RED phase, all pass GREEN after implementation._

## Files Created/Modified

- `analytics.py` - Added `_build_youtube_client()` method; updated `collect_analytics()` with optional `video_id` param
- `pipeline/runner.py` - Added `import time`; updated `_collect_episode_analytics()` to use platform_ids and call `append_to_engagement_history()`; added `_load_episode_topics()` helper; added `run_backfill_ids()` function
- `pipeline/__init__.py` - Exported `run_backfill_ids`
- `main.py` - Imported `run_backfill_ids`; added `backfill-ids` CLI branch
- `tests/test_analytics.py` - Added `TestRunBackfillIds` (4 tests) and `TestRunAnalyticsWiring` (2 tests)

## Decisions Made

- **_build_youtube_client() extraction:** Factored pickle-based OAuth auth out of fetch_youtube_analytics() into a reusable method so run_backfill_ids() doesn't duplicate the credential loading logic.
- **collect_analytics() video_id param:** Added optional video_id kwarg that passes through to fetch_youtube_analytics() — the cleanest API surface for callers that have platform_ids loaded.
- **post_timestamp from file mtime:** platform_ids.json is written at upload time; its mtime is an accurate proxy for post timestamp without requiring a new data field.
- **_load_episode_topics() from glob:** Uses *_analysis.json glob rather than assuming filename format — compatible with old episodes (1-28) whose output dirs may have different naming conventions.

## Deviations from Plan

None - plan executed exactly as written, plus one minor auto-refactor (extracting `_build_youtube_client()`) that enabled the backfill command to reuse auth code without duplication (Rule 2 - missing critical reuse).

## Issues Encountered

None. The pre-existing `test_collector_init_disabled` failure (ANALYTICS_ENABLED env var defaulting to "true") is a pre-existing issue unrelated to this plan.

## Next Phase Readiness

- Phase 9 complete: all 5 requirements delivered (ANLYT-01 through ANLYT-04, CONTENT-01)
- Phase 10 (topic correlation scoring) can now read engagement_history.json for cross-episode Pearson/Spearman correlation
- Backfill command ready to run on real episode data once YouTube credentials are verified

---
*Phase: 09-analytics-infrastructure*
*Completed: 2026-03-19*
