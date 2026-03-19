---
phase: 09-analytics-infrastructure
plan: 02
subsystem: distribution
tags: [instagram, tiktok, twitter, uploaders, hashtags, functional-flag]

# Dependency graph
requires:
  - phase: 06-subtitle-clip-generator
    provides: clip_hashtags field on best_clips from analysis JSON
provides:
  - InstagramUploader.functional flag (False when creds missing/placeholder)
  - TikTokUploader.functional flag (False when creds missing/placeholder)
  - TwitterUploader.post_episode_announcement accepts hashtags param
  - dry_run() shows "STUB (not functional)" for non-functional uploaders
  - distribute.py extracts top 2 clip_hashtags and passes to Twitter
affects: [phase-10-engagement-scoring, phase-11-smart-scheduling, pipeline-runner, distribute]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ".functional flag pattern: uploaders set self.functional=True/False in __init__ instead of raising ValueError"
    - "Uploader stub detection: check bool(value) and value != 'placeholder_string'"
    - "Hashtag threading: distribute.py extracts from analysis, passes to uploader method"

key-files:
  created: []
  modified:
    - uploaders/instagram_uploader.py
    - uploaders/tiktok_uploader.py
    - uploaders/twitter_uploader.py
    - pipeline/runner.py
    - pipeline/steps/distribute.py
    - tests/test_instagram_uploader.py
    - tests/test_tiktok_uploader.py
    - tests/test_twitter_uploader.py

key-decisions:
  - "InstagramUploader and TikTokUploader now never raise ValueError — .functional flag replaces raise pattern"
  - "dry_run() checks .functional via getattr with True default to safely handle uploaders without the flag"
  - "Hashtag injection limited to top 2 unique tags from clip_hashtags, preserving tweet character budget"
  - "Old tests expecting ValueError updated to assert .functional is False (behavior change, not bug)"

patterns-established:
  - ".functional flag: set in __init__ before any early returns; guard all public methods with 'if not self.functional: return None'"
  - "Deduplication before slicing: collect all hashtags, deduplicate preserving order, then take [:2]"

requirements-completed: [ANLYT-04, CONTENT-01]

# Metrics
duration: 35min
completed: 2026-03-19
---

# Phase 9 Plan 02: Stub Uploader Detection and Hashtag Injection Summary

**Instagram and TikTok uploaders replaced ValueError raises with .functional flag; Twitter episode announcements now append top 2 clip hashtags as a final tweet line**

## Performance

- **Duration:** 35 min
- **Started:** 2026-03-19T00:21:27Z
- **Completed:** 2026-03-19T00:56:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- InstagramUploader and TikTokUploader now always instantiate without raising, setting .functional=True/False based on credential presence
- pipeline/runner.py always instantiates Instagram and TikTok uploaders, logs [SKIP] warning when not functional
- dry_run() now shows "STUB (not functional)" for uploaders where .functional is False instead of always showing "ready"
- TwitterUploader.post_episode_announcement accepts new `hashtags` parameter and appends "#tag1 #tag2" as final tweet line (within 280 char budget)
- distribute.py extracts top 2 unique clip_hashtags from best_clips and threads them through to Twitter
- 16 new tests added (10 stub detection + 6 hashtag injection); all 56 tests in 3 uploader test files pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Tests for stub detection and hashtag injection** - `d31ff47` (test)
2. **Task 2: Implement stub detection flags, dry run display, and hashtag injection** - `b88b7b6` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 was TDD RED phase; Task 2 was GREEN implementation. Old ValueError-based tests updated as part of Task 2._

## Files Created/Modified

- `uploaders/instagram_uploader.py` - Replaced ValueError raises with .functional flag; guards on upload_reel, upload_reel_from_dropbox, get_account_info
- `uploaders/tiktok_uploader.py` - Replaced ValueError raises with .functional flag; guards on upload_video, get_user_info
- `uploaders/twitter_uploader.py` - Added hashtags parameter to post_episode_announcement; injects top 2 as "\n\n#tag1 #tag2"
- `pipeline/runner.py` - Instagram/TikTok init removed from try/except; logs [SKIP] warning; dry_run checks .functional
- `pipeline/steps/distribute.py` - Extracts unique clip_hashtags, deduplicates, passes top_hashtags to post_episode_announcement
- `tests/test_instagram_uploader.py` - Added TestInstagramFunctionalFlag (3 tests); updated old ValueError tests
- `tests/test_tiktok_uploader.py` - Added TestTikTokFunctionalFlag (3 tests); updated old ValueError tests
- `tests/test_twitter_uploader.py` - Added TestHashtagInjection (4 tests)

## Decisions Made

- Replaced ValueError with .functional flag to allow always-instantiate pattern in runner.py — uploaders can now be in the dict even when unconfigured, simplifying _init_uploaders and enabling dry_run status display
- dry_run uses `getattr(uploader, "functional", True)` so it gracefully handles uploaders (YouTube, Twitter, Spotify) that don't have the flag
- Hashtag injection uses character budget check: if tweet + hashtags > 280, trim tweet to fit rather than skip hashtags

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated old tests that expected ValueError to assert .functional is False**

- **Found during:** Task 2 (implementation)
- **Issue:** Existing tests `test_init_without_access_token` and `test_init_without_account_id` for Instagram, and `test_init_without_client_key` and `test_init_without_access_token` for TikTok used `pytest.raises(ValueError)` — which no longer applies after the functional flag change
- **Fix:** Updated 4 tests to call the uploader and assert `.functional is False`, matching the new behavior. Also added missing credential patches so tests don't fail on other missing creds
- **Files modified:** tests/test_instagram_uploader.py, tests/test_tiktok_uploader.py
- **Verification:** All 56 tests in 3 uploader test files pass
- **Committed in:** b88b7b6 (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed pre-existing lint errors in tests/test_distribute.py**

- **Found during:** Task 1 commit
- **Issue:** tests/test_distribute.py had been staged from a prior plan run and contained unused imports (`pytest`, `pathlib.Path`) that caused ruff lint to fail
- **Fix:** Ran `ruff check --fix tests/test_distribute.py` to remove unused imports
- **Files modified:** tests/test_distribute.py
- **Verification:** Lint passed, commit succeeded
- **Committed in:** d31ff47 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correctness and to unblock commit. No scope creep.

## Issues Encountered

- Pre-commit hook blocked first commit due to unused imports in a pre-staged file (tests/test_distribute.py from 09-01) — fixed inline

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Instagram and TikTok now always in `uploaders` dict (even when not functional) — Phase 10 scheduling logic can check .functional before queuing
- Twitter hashtag injection live — clip_hashtags from LLM analysis now surface on all episode announcements
- Phase 09-03 (analytics collection) can proceed independently

---
*Phase: 09-analytics-infrastructure*
*Completed: 2026-03-19*
