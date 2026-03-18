---
phase: 02-audio-quality
plan: 01
subsystem: testing
tags: [pytest, pydub, ffmpeg, subprocess, tdd, lufs, audio-ducking, normalization]

# Dependency graph
requires:
  - phase: 01-foundations
    provides: "Stable audio_processor.py baseline with passing tests"
provides:
  - "TestAudioDucking class (5 tests, all RED) defining ducking API contract"
  - "TestNormalizeAudio class (7 tests, all RED) defining two-pass FFmpeg LUFS normalization API"
  - "subprocess import + _parse_loudnorm_json stub in audio_processor.py for patch resolution"
affects:
  - 02-02-PLAN (implements ducking against these tests)
  - 02-03-PLAN (implements LUFS normalization against these tests)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@patch('audio_processor.subprocess.run') pattern for mocking FFmpeg subprocess calls"
    - "caplog fixture for asserting WARNING/INFO log output in tests"
    - "Class-level JSON string constants for reusable FFmpeg stderr mock data"

key-files:
  created: []
  modified:
    - tests/test_audio_processor.py
    - audio_processor.py

key-decisions:
  - "Added subprocess import with noqa to audio_processor.py so patch target resolves before implementation — the import is intentional scaffolding, not a premature feature"
  - "Added _parse_loudnorm_json as a NotImplementedError stub so @patch('audio_processor.AudioProcessor._parse_loudnorm_json') resolves in tests that test downstream AGC warning behavior in isolation"
  - "test_normalize_raises_on_missing_file passes GREEN in RED phase — this tests pre-existing FileNotFoundError behavior that must be preserved through the rewrite; all other 11 tests fail RED as required"

patterns-established:
  - "TDD RED scaffold: tests use @patch('audio_processor.subprocess.run') not @patch('subprocess.run') — module-level patch ensures tests are isolated from real FFmpeg"
  - "FIRST_PASS_JSON and SECOND_PASS_JSON as class constants on TestNormalizeAudio for reuse across tests"

requirements-completed: []  # RED phase — requirements fulfilled when GREEN in Plan 02 and 03

# Metrics
duration: 4min
completed: 2026-03-16
---

# Phase 02 Plan 01: Audio Quality Test Scaffold Summary

**12 failing RED tests defining the exact API contract for audio ducking (pydub gain+fade) and two-pass FFmpeg LUFS normalization before any production code changes**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-16T21:17:31Z
- **Completed:** 2026-03-16T21:21:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Created TestAudioDucking (5 tests) asserting that apply_censorship uses volume reduction + fade instead of beep splicing
- Rewrote TestNormalizeAudio (7 tests) with subprocess mocking to specify two-pass FFmpeg loudnorm, LUFS target from Config, AGC fallback warning, metadata logging, and stdin=DEVNULL
- Added subprocess import stub and _parse_loudnorm_json NotImplementedError placeholder to audio_processor.py so patch targets resolve correctly in test collection

## Task Commits

1. **Task 1: TDD RED scaffold** - `397d123` (test)

## Files Created/Modified
- `tests/test_audio_processor.py` - Added TestAudioDucking (5 tests) + rewrote TestNormalizeAudio (7 tests); all 21 pre-existing tests remain GREEN
- `audio_processor.py` - Added `import subprocess` (noqa) and `_parse_loudnorm_json` stub for patch resolution

## Decisions Made
- Added `import subprocess  # noqa: F401` to audio_processor.py rather than using `importlib` trickery — ruff lint would reject an unused import without the noqa, but the import is genuinely needed as the patch target for tests
- `_parse_loudnorm_json` added as a `NotImplementedError` stub (not removed) to allow `test_normalize_warns_on_agc_fallback` to patch the method independently and test only the warning logic in isolation
- `test_normalize_raises_on_missing_file` intentionally passes GREEN: it tests the FileNotFoundError guard that existed before the rewrite and must survive the Phase 2 Plan 02 implementation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added subprocess import to audio_processor.py for patch target**
- **Found during:** Task 1 (running tests after writing them)
- **Issue:** `@patch("audio_processor.subprocess.run")` raised AttributeError because audio_processor.py did not import subprocess; patch path could not be resolved
- **Fix:** Added `import subprocess  # noqa: F401` at module level; added `_parse_loudnorm_json` NotImplementedError stub as method so the class-level patch resolves
- **Files modified:** audio_processor.py
- **Verification:** All subprocess-patching tests now fail with proper AssertionError (RED) instead of AttributeError
- **Committed in:** 397d123

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal — two-line addition to production file enables correct patch behavior. No production logic changed.

## Issues Encountered
- The `@patch("audio_processor.subprocess.run")` decorator silently failed collection until `import subprocess` was added to audio_processor.py. Resolved immediately as Rule 3.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 12 new tests are RED and define the exact behavior for Plans 02 and 03
- Plan 02 must implement `_apply_duck_segment` in `apply_censorship` — tests will go GREEN
- Plan 03 must rewrite `normalize_audio` with two-pass subprocess FFmpeg — 6 tests will go GREEN
- `_parse_loudnorm_json` stub is ready to be filled in during Plan 02 or 03

---
*Phase: 02-audio-quality*
*Completed: 2026-03-16*
