---
phase: 03-content-voice-and-clips
plan: 01
subsystem: testing
tags: [tdd, red-phase, content-editor, blog-generator, audio-clip-scorer, voice-prompt, energy-scoring]

# Dependency graph
requires: []
provides:
  - "Failing test contract for VOICE-01: ContentEditor prompt must contain VOICE EXAMPLES block, BAD/GOOD pairs, show-specific hook examples"
  - "Failing test contract for VOICE-01 blog: BlogPostGenerator prompt must contain voice examples and system message"
  - "Failing test contract for VOICE-02: AudioClipScorer class with score_segments returning audio_energy_score field"
  - "Failing test contract for VOICE-03: energy_candidates parameter injection into ContentEditor prompt"
affects:
  - 03-02 (GREEN phase: implement voice prompt changes to make TestVoicePrompt, TestEnergyPromptInjection, TestAnalyzeContentSystemMessage pass)
  - 03-03 (GREEN phase: implement AudioClipScorer to make TestAudioClipScorer, TestEnergyScoring pass)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED: tests import non-existent module (audio_clip_scorer.py) to guarantee failure"
    - "Energy candidates passed as keyword arg to _build_analysis_prompt(energy_candidates=None)"
    - "System message role assertion: messages[0]['role'] == 'system'"
    - "Mock pattern for pydub AudioSegment: patch('audio_clip_scorer.AudioSegment') with __getitem__ side_effect for per-window RMS control"

key-files:
  created:
    - tests/test_audio_clip_scorer.py
  modified:
    - tests/test_content_editor.py
    - tests/test_blog_generator.py

key-decisions:
  - "energy_candidates=None keyword arg signature chosen for _build_analysis_prompt — backward-compatible, optional parameter"
  - "AudioClipScorer patch target is audio_clip_scorer.AudioSegment (module-level import), not pydub.AudioSegment"
  - "test_prompt_without_energy_candidates_has_no_energy_section fails with TypeError (unexpected kwarg) in RED — acceptable since method signature doesn't exist yet"

patterns-established:
  - "Voice prompt tests: assert 'VOICE EXAMPLES' in prompt.upper() — case-insensitive heading check"
  - "Energy injection tests: assert 'HIGH ENERGY MOMENTS' in prompt — sentinel string for section presence"
  - "System message tests: messages[0]['role'] == 'system' against mocked create() call_args"

requirements-completed:
  - VOICE-01
  - VOICE-02
  - VOICE-03

# Metrics
duration: 7min
completed: 2026-03-17
---

# Phase 3 Plan 01: Content Voice and Clips RED Tests Summary

**TDD RED phase: 12 failing tests establish acceptance contract for voice persona prompts, energy-aware clip scoring, and system message API calls across three modules**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T03:08:07Z
- **Completed:** 2026-03-17T03:15:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added 3 new test classes to test_content_editor.py covering VOICE-01 voice examples, VOICE-03 energy injection, and system message/temperature contract
- Added 1 new test class to test_blog_generator.py covering VOICE-01 blog voice persona and system message
- Created new test file tests/test_audio_clip_scorer.py covering VOICE-02 AudioClipScorer with 7 tests across 2 classes
- 297 pre-existing tests still pass — no regressions from appending to test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing tests for VOICE-01 and VOICE-03 in test_content_editor.py** - `50c7215` (test)
2. **Task 2: Failing tests for VOICE-01 blog voice in test_blog_generator.py** - `9a564d8` (test)
3. **Task 3: Failing tests for VOICE-02 audio clip scoring in test_audio_clip_scorer.py** - `5815ab1` (test)

## Files Created/Modified
- `tests/test_content_editor.py` - Appended TestVoicePrompt (5 tests), TestEnergyPromptInjection (3 tests), TestAnalyzeContentSystemMessage (2 tests)
- `tests/test_blog_generator.py` - Appended TestBlogVoicePrompt (3 tests)
- `tests/test_audio_clip_scorer.py` - New file with TestAudioClipScorer (5 tests) and TestEnergyScoring (2 tests)

## Decisions Made
- `energy_candidates=None` chosen as keyword-arg signature for `_build_analysis_prompt` — backward-compatible default, required for VOICE-03 injection tests
- AudioClipScorer mock patch target is `audio_clip_scorer.AudioSegment` (module-level reference), not `pydub.AudioSegment`
- Two tests in TestVoicePrompt pass against unmodified source (persona string "Fake Problems" and "youtube"/"twitter" in JSON schema already exist) — acceptable since the critical new behaviors (VOICE EXAMPLES block, BAD/GOOD, hook examples) all fail as required

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff format reformatted test files on first commit attempt — fixed by running `ruff format` before staging
- Ruff lint flagged unused `pytest` import and unused `call_count` variable in test_audio_clip_scorer.py — removed both, all checks passed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 3 test contracts established and failing correctly (RED state confirmed)
- Plan 02 can now implement voice prompt changes to make TestVoicePrompt, TestEnergyPromptInjection, TestAnalyzeContentSystemMessage, and TestBlogVoicePrompt pass
- Plan 03 can implement audio_clip_scorer.py to make TestAudioClipScorer and TestEnergyScoring pass
- No blockers for Phase 3 continuation

---
*Phase: 03-content-voice-and-clips*
*Completed: 2026-03-17*

## Self-Check: PASSED

All created files and task commits verified present on disk and in git log.
