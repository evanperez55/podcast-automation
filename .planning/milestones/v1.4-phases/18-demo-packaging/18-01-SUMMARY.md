---
phase: 18-demo-packaging
plan: 01
subsystem: audio
tags: [ffmpeg, subprocess, pipeline, snapshot, demo]

# Dependency graph
requires:
  - phase: 17-integration-testing-genre-fixes
    provides: pipeline runner and audio step as baseline
provides:
  - raw_snapshot_path field on PipelineContext
  - 60-second raw audio WAV snapshot captured before Step 4 censorship
  - Snapshot path persisted in censor checkpoint outputs for downstream discovery
affects: [18-demo-packaging]

# Tech tracking
tech-stack:
  added: []
  patterns: [subprocess FFmpeg extraction for large audio files (avoids pydub memory load)]

key-files:
  created: []
  modified:
    - pipeline/context.py
    - pipeline/steps/audio.py
    - tests/test_audio_processor.py

key-decisions:
  - "Snapshot uses subprocess FFmpeg -ss/-to (not pydub) to avoid loading 1GB+ audio into memory"
  - "Snapshot start time derived from best_clips[0].start_seconds, defaulting to 60.0 if no clips"
  - "raw_snapshot_path stored in censor checkpoint outputs so resume path recovers it without re-extraction"

patterns-established:
  - "Step 3.9 pattern: side-effect data capture before destructive step, stored in that step's checkpoint"

requirements-completed: [DEMO-02]

# Metrics
duration: 18min
completed: 2026-03-28
---

# Phase 18 Plan 01: Raw Audio Snapshot Summary

**60-second raw audio WAV snapshot captured via FFmpeg subprocess before censorship, enabling before/after audio comparison in the demo package**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-28T00:00:00Z
- **Completed:** 2026-03-28T00:18:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Added `raw_snapshot_path: Optional[Path] = None` field to `PipelineContext`
- Step 3.9 captures a 60-second WAV segment before censorship using FFmpeg subprocess (avoids loading 1GB+ audio into pydub)
- Snapshot start defaults to `best_clips[0].start_seconds` (or 60.0 if no clips), end is start + 60s
- `ctx.raw_snapshot_path` set on context; path stored in censor checkpoint for resume recovery
- On resume (censor already complete), snapshot creation is skipped and path restored from checkpoint
- 6 new tests in `TestRawSnapshot` class; all 646 suite tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add raw_snapshot_path to PipelineContext and write snapshot tests (RED)** - `45649be` (test)
2. **Task 2: Implement raw audio snapshot in pipeline/steps/audio.py (GREEN)** - `a3b9d36` (feat)

_Note: TDD task has two commits (test RED → feat GREEN)_

## Files Created/Modified
- `pipeline/context.py` - Added `raw_snapshot_path: Optional[Path] = None` field after `censored_audio`
- `pipeline/steps/audio.py` - Added `import subprocess`, Step 3.9 snapshot block, updated censor checkpoint to include `raw_snapshot_path`
- `tests/test_audio_processor.py` - Added `TestRawSnapshot` class with 7 tests; added imports for `PipelineContext`, `run_audio`, `Path`

## Decisions Made
- subprocess FFmpeg used instead of pydub to avoid loading entire 1GB+ raw audio file into memory
- Snapshot start time derived from `best_clips[0].start_seconds` with 60.0 default — captures a meaningful segment the AI already identified as good content
- Snapshot stored in censor checkpoint (not a separate checkpoint) since it is logically tied to the pre-censor state

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Pre-commit hook caught unused `call` import and unformatted files — fixed before each commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `ctx.raw_snapshot_path` and `raw_snapshot_path` in censor checkpoint outputs are ready for the demo packager (18-02) to discover and include in the before/after audio comparison
- No blockers

---
*Phase: 18-demo-packaging*
*Completed: 2026-03-28*
