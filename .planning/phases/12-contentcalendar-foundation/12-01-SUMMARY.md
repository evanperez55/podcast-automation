---
phase: 12-contentcalendar-foundation
plan: "01"
subsystem: content-calendar
tags: [content-calendar, scheduling, distribution, persistence]
dependency_graph:
  requires: [config.py, posting_time_optimizer.py]
  provides: [ContentCalendar class, content_calendar.py]
  affects: [topic_data/content_calendar.json]
tech_stack:
  added: []
  patterns: [atomic-json-write, self-enabled-pattern, tdd, unittest-mock]
key_files:
  created:
    - content_calendar.py
    - tests/test_content_calendar.py
  modified:
    - config.py
decisions:
  - "Clip slots cap at 3 (D+2, D+4, D+6) matching plan spec; plan_episode uses video_clip_paths count to decide how many clip slots to generate"
  - "Teaser slot requires best_clips[0].hook_caption to be non-empty; empty list or missing key skips teaser"
  - "PostingTimeOptimizer instantiated once in __init__ and reused; falls back to Config.SCHEDULE_*_POSTING_HOUR when optimizer returns None"
metrics:
  duration: "6m"
  completed_date: "2026-03-19"
  tasks_completed: 1
  tasks_total: 1
  files_created: 2
  files_modified: 1
---

# Phase 12 Plan 01: ContentCalendar Foundation Summary

**One-liner:** ContentCalendar module generating D-1/D0/D+2/D+4/D+6 distribution slot plans persisted atomically to topic_data/content_calendar.json with PostingTimeOptimizer integration.

## What Was Built

`content_calendar.py` — new top-level module implementing `ContentCalendar` class that replaces same-day upload dumps with a deliberate weekly spread. The module:

- Generates per-episode slot plans: teaser (D-1, twitter), episode (D0, youtube+twitter), up to 3 clip slots (D+2/+4/+6, youtube+twitter)
- Skips teaser slot when analysis has no best_clips with hook_caption
- Caps clip slots at 3 regardless of paths provided
- Is fully idempotent — second call for same episode returns existing entry
- Persists state atomically via `.tmp` + `Path.replace()` (matches scheduler.py pattern)
- Queries pending slots by status + scheduled_at <= now
- Marks slots as uploaded (with results) or failed (with error)
- Uses PostingTimeOptimizer hour when available; falls back to Config.SCHEDULE_*_POSTING_HOUR

`config.py` additions (2 lines):
- `CONTENT_CALENDAR_ENABLED = os.getenv("CONTENT_CALENDAR_ENABLED", "true") == "true"`
- `TOPIC_DATA_DIR = Path("topic_data")`

`tests/test_content_calendar.py` — 19 tests across 5 test classes covering all behaviors.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Add failing tests | b9d863d | tests/test_content_calendar.py |
| GREEN | Implement ContentCalendar | d744db1 | content_calendar.py, config.py |

## Verification Results

- `pytest tests/test_content_calendar.py -v`: 19/19 passed
- `pytest` full suite: 506 passed, 2 pre-existing failures (analytics + audiogram enabled defaults)
- `ruff check content_calendar.py tests/test_content_calendar.py`: no issues
- `ruff format --check`: all formatted

## Must-Haves Verified

| Truth | Status |
|-------|--------|
| plan_episode() generates exactly 4 slots (teaser D-1, episode D0, clip_1 D+2, clip_2 D+4) when 2+ clips available | PASS |
| Clip slot count matches available video_clip_paths (0=0 slots, 1=1 slot, cap at 3) | PASS |
| No two slots share the same day_offset | PASS |
| plan_episode() is idempotent — second call returns existing entry | PASS |
| content_calendar.json is written atomically via .tmp + replace pattern | PASS |
| PostingTimeOptimizer provides slot hours with Config fallback when optimizer returns None | PASS |

## Artifacts Verified

| Artifact | Min Lines | Actual | Key Exports |
|----------|-----------|--------|-------------|
| content_calendar.py | 120 | 374 | ContentCalendar |
| tests/test_content_calendar.py | 150 | 530 | 19 tests |
| config.py | — | modified | CONTENT_CALENDAR_ENABLED, TOPIC_DATA_DIR |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- content_calendar.py exists: FOUND
- tests/test_content_calendar.py exists: FOUND
- config.py has CONTENT_CALENDAR_ENABLED: FOUND
- Commit b9d863d (test): FOUND
- Commit d744db1 (feat): FOUND
