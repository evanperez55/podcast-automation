# Debug Findings — Pipeline Bug Hunt

**Date:** 2026-04-02
**Scope:** All .py files in root + uploaders/
**Iterations:** 25 (bounded)

## Summary

- **Bugs found:** 11 (0 Critical, 3 High, 7 Medium, 1 Low)
- **Hypotheses tested:** 25 (11 confirmed, 14 disproven)
- **Files investigated:** 28 / ~40 in scope

## HIGH Severity

### Bug 1: Calendar save crashes on non-serializable upload results
- **Location:** `content_calendar.py:230` → `save()` at line 342
- **Evidence:** `content_calendar.json` clip_3 has `"error": "Object of type MagicMock is not JSON serializable"` in production data
- **Root cause:** `save()` uses `json.dumps(data, indent=2)` without `default=str` fallback
- **Impact:** Calendar corruption, slots stuck in limbo
- **Fix:** Add `default=str` to `json.dumps` in `save()`, or sanitize results before storing

### Bug 3: Timezone mismatch in content calendar scheduling
- **Location:** `content_calendar.py:294`
- **Root cause:** `datetime.now()` returns local time (ET locally, UTC in CI). Calendar stores naive timestamps in ET.
- **Impact:** GitHub Actions (UTC) fires scheduled posts 4-5 hours early
- **Fix:** Use timezone-aware datetimes or store/compare in UTC

### Bug 10: Windows absolute paths in content calendar break CI
- **Location:** `content_calendar.py` + `topic_data/content_calendar.json`
- **Evidence:** `"C:\\Users\\evanp\\..."` paths in calendar JSON
- **Impact:** Quote card images and file-dependent content never posts from GitHub Actions (Linux)
- **Fix:** Store relative paths, resolve at runtime

## MEDIUM Severity

### Bug 2: FFmpeg subprocess calls missing stdin=DEVNULL
- **Location:** `video_converter.py:116,239` + 8 more in `video_utils.py`, `audiogram_generator.py`, `subtitle_clip_generator.py`, `compilation_generator.py`
- **Impact:** FFmpeg can hang waiting for stdin, blocked until timeout (up to 2 hours)
- **Fix:** Add `stdin=subprocess.DEVNULL` to all subprocess.run FFmpeg calls

### Bug 4: YouTube privacy failure silently ignored
- **Location:** `post_scheduled_content.py:83-86`
- **Impact:** Slot marked "uploaded" but YouTube Short stays private
- **Fix:** Record failure result when `set_video_privacy` returns `False`

### Bug 5: Test isolation leak — thumbnail mocks corrupt PIL
- **Location:** `tests/test_thumbnail_generator.py:14-19`
- **Impact:** 6 spurious test failures in full suite
- **Fix:** Don't use `sys.modules.setdefault` for PIL; use proper fixture cleanup

### Bug 6: video_converter.py missing NVENC fallback
- **Location:** `video_converter.py:116-131,239-250`
- **Impact:** Full episode video creation fails on NVENC session limit instead of falling back to libx264
- **Fix:** Add NVENC error detection + fallback like `video_utils.py:321-348`

### Bug 7: Twitter URL truncation
- **Location:** `post_scheduled_content.py:105-107`
- **Impact:** If text+URL exceeds 280 chars, URL gets cut mid-string producing broken link
- **Fix:** Truncate text to `280 - len(url) - 2` before appending URL

### Bug 8: Scheduler inconsistent timezone handling
- **Location:** `scheduler.py:56` (naive) vs `scheduler.py:254` (UTC-aware)
- **Impact:** Upload times may be hours off depending on code path

### Bug 9: Dropbox download no integrity verification
- **Location:** `dropbox_handler.py:118-123`
- **Impact:** Partial downloads could silently corrupt pipeline input
- **Fix:** Compare `local_path.stat().st_size` with `metadata.size` after download

## LOW Severity

### Bug 11: 18 f-string logger calls
- **Location:** `audiogram_generator.py` + others (18 instances)
- **Impact:** Minor perf — f-string evaluated even when log level suppressed
- **Fix:** Use `logger.info("msg: %s", var)` instead of `logger.info(f"msg: {var}")`

## Debug Score

```
debug_score = 11 * 15 + 25 * 3 + (28/40) * 40 + (4/7) * 10
            = 165 + 75 + 28 + 5.7
            = 273.7
```
