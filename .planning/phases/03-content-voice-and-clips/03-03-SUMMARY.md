---
phase: 03-content-voice-and-clips
plan: "03"
subsystem: audio
tags: [pydub, rms, energy-scoring, clip-selection, openai]

# Dependency graph
requires:
  - phase: 03-02
    provides: _build_analysis_prompt() with energy_candidates=None parameter already wired
provides:
  - AudioClipScorer class with score_segments() pydub RMS windowing
  - analyze_content() audio_path parameter for energy-guided clip selection
  - Config.CLIP_AUDIO_TOP_N env var for tuning top-N segments passed to prompt
affects:
  - 03-04 (any further clip selection improvements can build on energy scoring)
  - main.py (pipeline caller of analyze_content — can now pass audio_path)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AudioClipScorer: stateless scorer class, score_segments() returns input unchanged on error"
    - "Energy normalization: (mean_rms - min_rms) / rms_range gives 0.0-1.0 relative score"
    - "Empty segments short-circuit: check segments before loading audio file"

key-files:
  created:
    - audio_clip_scorer.py
  modified:
    - content_editor.py
    - config.py

key-decisions:
  - "Short-circuit on empty segments list before loading audio — avoids MagicMock comparison error in tests"
  - "AudioClipScorer mock patch target is audio_clip_scorer.AudioSegment (module-level import)"

patterns-established:
  - "Graceful degradation: AudioClipScorer returns input unchanged on any Exception from from_file"
  - "Energy candidates are sorted descending by score and sliced to CLIP_AUDIO_TOP_N before prompt injection"

requirements-completed:
  - VOICE-02

# Metrics
duration: 7min
completed: "2026-03-17"
---

# Phase 03 Plan 03: Audio Energy Scoring for Clip Selection Summary

**AudioClipScorer with pydub RMS windowing biases GPT-4o clip selection toward high-energy moments, injected via analyze_content(audio_path) and configurable CLIP_AUDIO_TOP_N**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T03:28:38Z
- **Completed:** 2026-03-17T03:35:59Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- New `audio_clip_scorer.py` with `AudioClipScorer` class — pydub RMS windowing scores each transcript segment 0.0-1.0 relative to episode energy range
- `analyze_content()` updated to accept `audio_path=None`; when provided, scores all segments and passes top-N as `energy_candidates` to the GPT-4o prompt
- `Config.CLIP_AUDIO_TOP_N` added to config.py (default 10, reads from `CLIP_AUDIO_TOP_N` env var)
- All 7 new AudioClipScorer tests pass; 314 total tests pass with no new regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create audio_clip_scorer.py** - `7455399` (feat)
2. **Task 2: Wire AudioClipScorer into analyze_content() with CLIP_AUDIO_TOP_N** - `8bf5a29` (feat)

**Plan metadata:** (docs commit below)

_Note: TDD tasks — both RED (test file pre-existed from plan 02) and GREEN phases executed._

## Files Created/Modified
- `audio_clip_scorer.py` - AudioClipScorer class with score_segments() using pydub RMS windowing
- `content_editor.py` - analyze_content() signature extended with audio_path=None; scoring block and energy_candidates wired to _build_analysis_prompt()
- `config.py` - CLIP_AUDIO_TOP_N config var added to Clip Settings section

## Decisions Made
- Short-circuited on empty segments before loading audio — the test mocked AudioSegment without setting up RMS values on chunks, causing MagicMock comparison errors in `max()`. Adding the early return on empty segments was the minimal correct fix.
- AudioClipScorer mock patch target confirmed as `audio_clip_scorer.AudioSegment` per STATE.md accumulated decisions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Empty segments early return added**
- **Found during:** Task 1 (GREEN phase, test_empty_segments_returns_empty_list)
- **Issue:** With empty segments, code still built energy_map using MagicMock audio chunks; `max(energy_map.values())` failed with TypeError on MagicMock comparison
- **Fix:** Added `if not segments: return segments` before audio loading
- **Files modified:** audio_clip_scorer.py
- **Verification:** All 7 tests pass including test_empty_segments_returns_empty_list
- **Committed in:** 7455399 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Minimal — one-line guard that improves correctness on empty input.

## Issues Encountered
- 2 pre-existing test failures found in full suite (`test_analytics.py::test_collector_init_disabled`, `test_audiogram_generator.py::test_disabled_and_default_colors`) — both confirmed pre-existing before plan 03 changes, out of scope, logged to deferred items.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- VOICE-02 complete: AudioClipScorer is ready for use
- main.py pipeline caller can now pass `audio_path` to `analyze_content()` when available
- CLIP_AUDIO_TOP_N is tunable via env var if default of 10 needs adjustment

---
*Phase: 03-content-voice-and-clips*
*Completed: 2026-03-17*
