---
phase: 02-audio-quality
plan: 02
subsystem: audio
tags: [pydub, audio-ducking, censorship, gain-reduction, fade, tdd]

# Dependency graph
requires:
  - phase: 02-audio-quality
    plan: 01
    provides: "TestAudioDucking (5 RED tests) defining ducking API contract"
provides:
  - "_apply_duck_segment() private method: extracts segment, applies -40dB gain, 50ms fade-in/out, splices back"
  - "apply_censorship() rewritten to use volume ducking instead of beep-tone replacement"
affects:
  - 02-03-PLAN (normalize_audio rewrite; audio_processor.py changes do not affect that task)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pydub gain+fade ducking pattern: segment.apply_gain(-40).fade_in(ms).fade_out(ms)"
    - "Fade-cap pattern: min(FADE_MS, segment_len // 2) prevents overrun on short segments"
    - "MagicMock required for spec=AudioSegment mocks that test dunder methods (__add__, __getitem__, __mul__)"

key-files:
  created: []
  modified:
    - audio_processor.py
    - tests/test_audio_processor.py

key-decisions:
  - "Fade-cap logic (min(50, segment_len//2)) implemented in _apply_duck_segment to handle <100ms segments gracefully without pydub errors"
  - "test_censorship_handles_long_words updated from beep-repetition assertion to ducking assertion — the old test documented replaced behavior"
  - "TestAudioDucking tests required MagicMock (not Mock) for beep/segment mocks because Python magic methods (__add__, __getitem__, __mul__) are only interceptable on MagicMock instances with spec"

patterns-established:
  - "Audio segment tests: use MagicMock(spec=AudioSegment) when test needs to track or call dunder operators (__add__, __getitem__)"
  - "Duck-splice chain: audio[:start] + ducked + audio[end:] — two add operations on prefix+ducked and (prefix+ducked)+suffix"

requirements-completed: [AUDIO-01]

# Metrics
duration: 12min
completed: 2026-03-16
---

# Phase 02 Plan 02: Audio Ducking Implementation Summary

**`_apply_duck_segment()` added to AudioProcessor using pydub -40dB gain reduction + 50ms fade-in/out; `apply_censorship()` rewritten to use smooth radio-style volume dip instead of audible beep-tone splicing**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-16T21:27:00Z
- **Completed:** 2026-03-16T21:39:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Implemented `_apply_duck_segment()` with DUCK_GAIN_DB=-40, FADE_MS=50, and fade-cap for short segments
- Replaced beep-splice loop in `apply_censorship()` with `_apply_duck_segment()` call per censored segment
- All 5 `TestAudioDucking` tests pass GREEN; 26 total non-RED tests pass
- `self.beep_sound` kept in `__init__` with TODO backward-compat comment

## Task Commits

1. **Task 1: Add _apply_duck_segment() and rewrite apply_censorship()** - `93bce34` (feat)

## Files Created/Modified
- `audio_processor.py` - Added `_apply_duck_segment()` after `_get_beep_sound()`; rewrote beep-splice loop to call `_apply_duck_segment()`; added TODO comment on `self.beep_sound`
- `tests/test_audio_processor.py` - Added `MagicMock` import; updated 4 TestAudioDucking tests + `test_censorship_handles_long_words` to use `MagicMock` so dunder magic methods are trackable

## Decisions Made
- Fade cap: `min(FADE_MS, segment_len // 2)` protects against pydub errors on segments shorter than 2 * FADE_MS; tested with 100ms segment (actual_fade = 50ms → capped to 50ms)
- `self.beep_sound` retained to avoid breaking any callers that may directly access the attribute; added TODO comment noting it's no longer used by `apply_censorship`
- Tests required `MagicMock` instead of `Mock` for any mock that needs `+` or `[]` to work at the Python operator level — this is a fundamental Python/unittest.mock constraint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestAudioDucking tests used Mock instead of MagicMock for beep/segment mocks**
- **Found during:** Task 1 (GREEN phase execution)
- **Issue:** Tests called `mock_beep.__getitem__.assert_not_called()` and `mock_segment + ducked` on `Mock(spec=AudioSegment)` instances; Python magic dunder methods require `MagicMock` to be interceptable and callable as operators
- **Fix:** Added `MagicMock` to imports; changed `mock_beep` in `test_duck_no_beep_sound_used` to `MagicMock`; changed `mock_audio` and `mock_segment` in the four remaining TestAudioDucking tests to `MagicMock`; updated `test_duck_preserves_audio_before_and_after` assertion to correctly verify the two-add splice chain
- **Files modified:** tests/test_audio_processor.py
- **Verification:** All 5 TestAudioDucking tests pass GREEN
- **Committed in:** 93bce34

**2. [Rule 1 - Bug] test_censorship_handles_long_words asserted old beep-repetition behavior**
- **Found during:** Task 1 (full test suite run after implementation)
- **Issue:** `test_censorship_handles_long_words` in `TestCensoringTimestampAccuracy` asserted `beep_sound.__mul__.assert_called()` — the beep-repetition behavior that was just replaced by ducking
- **Fix:** Rewrote test to use MagicMock mocks and assert `mock_segment.apply_gain.assert_called_once()` instead — verifying ducking is applied for long words
- **Files modified:** tests/test_audio_processor.py
- **Verification:** Test passes GREEN; still correctly tests that long-word censorship works
- **Committed in:** 93bce34

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Both fixes were in test infrastructure, not production code. The first fixed a Mock/MagicMock mismatch in the tests written in plan 02-01. The second updated an outdated assertion about replaced behavior. No scope creep.

## Issues Encountered
- `Mock(spec=AudioSegment).__getitem__` raises `AttributeError` even though `AudioSegment` supports slicing — this is because `Mock` (non-Magic) does not auto-create dunder method descriptors; `MagicMock` is required. Fixed immediately as Rule 1.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Audio ducking complete; `apply_censorship()` produces smooth radio-style volume dip instead of beep
- Plan 02-03 can now implement `normalize_audio()` two-pass FFmpeg LUFS rewrite against the 6 RED `TestNormalizeAudio` tests
- `_parse_loudnorm_json` stub is in place for plan 02-03

---
*Phase: 02-audio-quality*
*Completed: 2026-03-16*
