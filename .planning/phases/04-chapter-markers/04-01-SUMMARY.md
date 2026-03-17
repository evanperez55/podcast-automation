---
phase: 04-chapter-markers
plan: "01"
subsystem: testing
tags: [mutagen, id3, chapters, rss, podcasting20, tdd, red-phase]

# Dependency graph
requires: []
provides:
  - "Failing test scaffold for ChapterGenerator.embed_id3_chapters (ID3 CHAP+CTOC frames)"
  - "Failing test scaffold for ChapterGenerator.generate_chapters_json (Podcasting 2.0 JSON)"
  - "Failing test scaffold for RSSFeedGenerator podcast:chapters RSS tag"
  - "mutagen==1.47.0 declared in requirements.txt"
affects:
  - "04-chapter-markers plan 02 (implementation — turns these tests GREEN)"

# Tech tracking
tech-stack:
  added:
    - "mutagen==1.47.0 — ID3 tag reading/writing for MP3 chapter frames"
  patterns:
    - "TDD RED phase: import-time failure (ModuleNotFoundError) for non-existent module"
    - "TDD RED phase: TypeError for missing keyword args on existing module"
    - "Mock mutagen at chapter_generator.mutagen.* patch paths for future implementation"

key-files:
  created:
    - "tests/test_chapter_generator.py — 10 tests covering embed_id3_chapters and generate_chapters_json"
    - "tests/test_rss_feed_generator.py — 3 tests covering podcast:chapters RSS tag support"
  modified:
    - "requirements.txt — added mutagen==1.47.0 in Audio processing section"

key-decisions:
  - "Patch paths use chapter_generator.mutagen.* namespace so tests remain stable as module is created"
  - "test_rss_feed_generator.py imports RSSFeedGenerator directly (module exists) — RED via TypeError not ImportError"
  - "pytest.fixture tmp_path used for generate_chapters_json file write tests — no manual cleanup needed"

patterns-established:
  - "RED phase test files: import non-existent module at top-level so all tests fail at collection"
  - "Edge case for ID3NoHeaderError: mock ID3 side_effect list with Exception first, MagicMock second/third"

requirements-completed:
  - VOICE-04
  - VOICE-05

# Metrics
duration: 6min
completed: 2026-03-16
---

# Phase 4 Plan 01: Chapter Markers Test Scaffold Summary

**RED-phase test scaffold for ID3 CHAP/CTOC frame writing and Podcasting 2.0 JSON chapter generation using mutagen**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-16T03:22:56Z
- **Completed:** 2026-03-16T03:29:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created 10-test RED scaffold for ChapterGenerator covering CHAP+CTOC ID3 frame generation, title truncation, delall ordering, edge cases (empty list, ID3NoHeaderError), and Podcasting 2.0 JSON output
- Created 3-test RED scaffold for RSSFeedGenerator chapters_url keyword arg and xmlns:podcast namespace
- Added mutagen==1.47.0 to requirements.txt and confirmed pip installability

## Task Commits

1. **Task 1: Add mutagen to requirements.txt + ChapterGenerator tests** - `a862e34` (test)
2. **Task 2: Write failing tests for RSS podcast:chapters support** - `ac5677a` (test)

## Files Created/Modified

- `tests/test_chapter_generator.py` - 10 tests for ChapterGenerator (VOICE-04, VOICE-05 JSON)
- `tests/test_rss_feed_generator.py` - 3 tests for RSSFeedGenerator chapter tag support (VOICE-05 RSS)
- `requirements.txt` - mutagen==1.47.0 added under Audio processing section

## Decisions Made

- Patch paths use `chapter_generator.mutagen.*` namespace: when chapter_generator.py is created, it will `import mutagen` and these patch paths will resolve correctly without changing tests
- test_rss_feed_generator.py intentionally uses `TypeError` as RED signal (not ImportError) because `rss_feed_generator.py` already exists — only the `chapters_url` kwarg is missing

## Deviations from Plan

None - plan executed exactly as written.

Minor: ruff lint required removing unused imports (`ET`, `call`, `pytest`) and reformatting — these were auto-fixed before commit per pre-commit hook requirements.

## Issues Encountered

Pre-commit hook (ruff lint + format) caught unused imports in both test files on first commit attempt. Fixed inline before committing — not a deviation, standard hygiene.

Two pre-existing test failures in test_analytics.py and test_audiogram_generator.py were present before this plan and remain unrelated to chapter markers work.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED tests in place for all VOICE-04 and VOICE-05 contracts
- Plan 02 (implementation) can now create chapter_generator.py and extend rss_feed_generator.py to turn these tests GREEN
- mutagen installed and available in environment

---
*Phase: 04-chapter-markers*
*Completed: 2026-03-16*
