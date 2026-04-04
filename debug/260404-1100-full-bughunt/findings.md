# Bug Hunt Findings — 2026-04-04

**Scope:** Entire codebase | **Iterations:** 30 | **Technique:** Binary search, direct inspection, trace, pattern search

## Summary

| Severity | Count |
|----------|-------|
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 3 |
| **Total** | **10** |

---

## HIGH Severity

### 1. [HIGH] Staggered Instagram Reels can't post from CI — clip files are local-only
- **Location:** `post_scheduled_content.py:148-162`, `content_calendar.py:122-142`
- **Evidence:** Calendar slots store local Windows paths (`C:\Users\evanp\...`) for `clip_path`. GitHub Actions runner doesn't have these files. Instagram posting requires re-uploading the video to Dropbox first, but the file doesn't exist on CI.
- **Impact:** ALL staggered Instagram Reel posts from the scheduled-content workflow will silently fail with "Clip file not found".
- **Root cause:** The pipeline uploads clips to Dropbox for immediate Instagram posts, but doesn't store the Dropbox URLs in the calendar for deferred posts.
- **Suggested fix:** During initial pipeline run, upload ALL clips to Dropbox (not just the immediate 2), store Dropbox shared URLs in calendar slot content. The scheduled poster should use the stored URL directly instead of re-uploading from local file.

### 2. [HIGH] Instagram token auto-refresh runs unconditionally on every init
- **Location:** `uploaders/instagram_uploader.py:37-88`
- **Evidence:** `_refresh_token_if_needed()` makes 2 API calls (validate + refresh) on every `InstagramUploader()` instantiation. The `REFRESH_THRESHOLD` constant (7 days) is defined but never checked against `expires_in`. Token is refreshed even when it has 59 days left.
- **Impact:** Wasted API quota, slower init (~2 extra HTTP calls per invocation), unnecessary token churn.
- **Root cause:** The method always calls the refresh endpoint instead of first checking if the token is within the threshold.
- **Suggested fix:** After getting `expires_in` from the refresh response, only update the token if `expires_in < REFRESH_THRESHOLD`.

### 3. [HIGH] Token refresh in CI is wasted — new token can't be persisted
- **Location:** `uploaders/instagram_uploader.py:90-110`
- **Evidence:** `_persist_token()` writes to `.env` which doesn't exist in CI. The refreshed token is used for that single run, then discarded. Next CI run starts with the old token from GitHub Secrets.
- **Impact:** Every CI run refreshes the token for nothing. More critically, if the token approaches expiration, CI can't auto-renew it — it'll break after 60 days.
- **Root cause:** Token persistence assumes local `.env` file exists. No mechanism to update GitHub Secrets.
- **Suggested fix:** Skip refresh in CI (check for env var like `CI=true`). Document that token must be manually refreshed locally and GitHub Secret updated before 60-day expiry.

---

## MEDIUM Severity

### 4. [MEDIUM] Test suite has 16 failures from Config class pollution between test files
- **Location:** `tests/test_config.py` + `tests/test_content_calendar.py` → `tests/test_demo_packager.py`
- **Evidence:** Running `test_config.py` and `test_content_calendar.py` together before `test_demo_packager.py` causes `Config.OUTPUT_DIR` to resolve to the real output directory instead of the monkeypatched tmp_path. All 16 demo_packager failures and 3 content_editor failures are caused by this.
- **Impact:** 19 of the 26 test failures are false negatives from test pollution, not real bugs.
- **Suggested fix:** Ensure all tests that modify Config class attributes do so via `monkeypatch.setattr(Config, ...)` which auto-restores, not direct assignment. May need a conftest fixture that saves/restores Config state.

### 5. [MEDIUM] Hardcoded `@fakeproblemspodcast` YouTube handle in 3 files
- **Location:** `pipeline/steps/distribute.py:353`, `uploaders/youtube_uploader.py:597`, `post_scheduled_content.py:212`
- **Evidence:** Fallback YouTube channel handle is hardcoded as `@fakeproblemspodcast`. When onboarding clients, their captions would reference the wrong channel.
- **Impact:** Client clips would point viewers to Fake Problems' channel instead of their own.
- **Suggested fix:** Add `YOUTUBE_CHANNEL_HANDLE` to Config, use it in all 3 locations.

### 6. [MEDIUM] daily_content_generator.py hardcodes "Fake Problems Podcast" in AI prompt
- **Location:** `daily_content_generator.py:139`
- **Evidence:** The AI system prompt says "You are a comedy writer for the Fake Problems Podcast" regardless of which client is active.
- **Impact:** If a client ran the daily content workflow, it would generate Fake Problems-branded content.
- **Suggested fix:** Use `Config.PODCAST_NAME` and a configurable voice persona.

### 7. [MEDIUM] test_distribute_step.py::TestUploadInstagram::test_videos_ready expects old stub behavior
- **Location:** `tests/test_distribute_step.py:242-253`
- **Evidence:** Test expects `result["status"] == "videos_ready"` but refactored `_upload_instagram` now requires Dropbox in components and returns `"no_dropbox"` when missing.
- **Impact:** 1 test failure.
- **Suggested fix:** Update test to provide a mock Dropbox in components, or test the new behavior.

---

## LOW Severity

### 8. [LOW] main.py exceeds 310-line guard rail (317 lines)
- **Location:** `tests/test_pipeline_refactor.py:87`
- **Evidence:** Adding test-upload route pushed main.py to 317 lines, exceeding the 310-line assertion.
- **Suggested fix:** Bump the assertion limit or move the test-upload route to pipeline/.

### 9. [LOW] 13 lint errors across scripts and experimental test files
- **Location:** `scripts/setup_instagram_oauth.py` (7 errors), `tests/test_compilation_generator.py` (1), `tests/test_daily_content_generator.py` (1), `tests/test_dropbox_handler.py` (4)
- **Evidence:** Unused imports, unnecessary f-strings, unused variables.
- **Suggested fix:** `uv run ruff check --fix .`

### 10. [LOW] content_calendar display method missing Instagram in platform list
- **Location:** `content_calendar.py:370-383`
- **Evidence:** `_schedule_display` shows only primary platform per slot (e.g. "youtube" for clips) but doesn't show Instagram.
- **Impact:** Display-only — no functional impact.
- **Suggested fix:** Update display to show all platforms, or leave as primary-only.

---

## Not Bugs (Disproven)

- Dropbox delete_file safety guard too restrictive — intentionally limited to /test_upload/ paths
- thumbnail_generator.py hardcoded font path — has proper fallback chain
- Bluesky clip posting with empty youtube_results — safe with `or {}` guard
- Instagram caption length overflow — already truncated by upload_reel
- YouTube Shorts upload race condition — sequential loop, no concurrency
- Pipeline RSS test failures — test pollution, not real bugs
