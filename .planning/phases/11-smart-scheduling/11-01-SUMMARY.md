---
phase: 11-smart-scheduling
plan: "01"
subsystem: scheduling
tags: [posting-time, engagement, scheduling, per-platform]
dependency_graph:
  requires:
    - engagement_scorer.py (EngagementScorer.get_category_rankings)
    - config.py (SCHEDULE_*_POSTING_HOUR)
  provides:
    - PostingTimeOptimizer.get_optimal_publish_at(platform) -> Optional[datetime]
  affects:
    - scheduler.py (plan 11-02 will consume PostingTimeOptimizer)
tech_stack:
  added: []
  patterns:
    - Module-level helper functions (_best_weekday, _next_occurrence, _posting_hour_for)
    - Delegation to EngagementScorer for all data access
    - Return None on insufficient data (no exceptions)
key_files:
  created:
    - posting_time_optimizer.py
    - tests/test_posting_time_optimizer.py
  modified:
    - config.py
decisions:
  - "PostingTimeOptimizer returns None naturally on insufficient data — no exceptions, no enabled gate"
  - "Module-level helpers (_best_weekday, _next_occurrence, _posting_hour_for) are public for direct unit testing"
  - "history_path constructor arg forwarded to EngagementScorer — enables clean testing without mocking Config"
metrics:
  duration: "6 minutes"
  completed: "2026-03-19"
  tasks_completed: 1
  files_changed: 3
---

# Phase 11 Plan 01: PostingTimeOptimizer Summary

**One-liner:** PostingTimeOptimizer computes next best publish datetime per platform from EngagementScorer day-of-week data, with research-based defaults (YouTube=14h, Twitter=10h) configurable via env vars.

## What Was Built

### posting_time_optimizer.py

New leaf module (~80 lines) with:

- `PostingTimeOptimizer` class with `get_optimal_publish_at(platform: str) -> Optional[datetime]`
  - Delegates to `EngagementScorer.get_category_rankings()` for all data
  - Returns `None` when status is `"insufficient_data"` (< 15 episodes)
  - Returns `None` when platform has no day-of-week data (all None scores)
  - Calls `_best_weekday` + `_next_occurrence` + `_posting_hour_for` internally

- Module-level helpers (public, directly testable):
  - `_best_weekday(day_scores: dict) -> Optional[str]` — filters Nones, returns weekday key with max score
  - `_next_occurrence(weekday_name: str, hour: int) -> datetime` — computes next future datetime; if today is the target day but posting hour has passed, advances one week
  - `_posting_hour_for(platform: str) -> int` — reads `Config.SCHEDULE_{PLATFORM}_POSTING_HOUR`, defaults to 12

### config.py additions

Four new env-var-backed class attributes after the `SCHEDULE_*_DELAY_HOURS` block:

```python
SCHEDULE_YOUTUBE_POSTING_HOUR = int(os.getenv("SCHEDULE_YOUTUBE_POSTING_HOUR", "14"))
SCHEDULE_TWITTER_POSTING_HOUR = int(os.getenv("SCHEDULE_TWITTER_POSTING_HOUR", "10"))
SCHEDULE_INSTAGRAM_POSTING_HOUR = int(os.getenv("SCHEDULE_INSTAGRAM_POSTING_HOUR", "12"))
SCHEDULE_TIKTOK_POSTING_HOUR = int(os.getenv("SCHEDULE_TIKTOK_POSTING_HOUR", "12"))
```

### tests/test_posting_time_optimizer.py

17 tests across 4 test classes:

- `TestBestWeekday` (4 tests) — filters None, returns max, single non-None, empty
- `TestNextOccurrence` (4 tests) — today before hour, today past hour, different weekday, always-future guarantee
- `TestPlatformHours` (4 tests) — YouTube=14, Twitter=10, different from each other, unknown platform=12
- `TestGetOptimalPublishAt` (5 tests) — returns datetime when ok, None on insufficient_data, None when all platform scores None, YouTube/Twitter at different hours, history_path forwarded to scorer

## Verification Results

- `pytest tests/test_posting_time_optimizer.py -x -v`: 17/17 passed
- `ruff check posting_time_optimizer.py config.py`: no errors
- `pytest` (full suite): 482 passed, 2 pre-existing failures (analytics + audiogram enabled defaults)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- posting_time_optimizer.py: FOUND
- tests/test_posting_time_optimizer.py: FOUND
- 11-01-SUMMARY.md: FOUND
- commit a2ab14e (test RED): FOUND
- commit 8e885da (feat GREEN): FOUND
