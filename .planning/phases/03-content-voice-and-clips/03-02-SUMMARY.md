---
phase: 03-content-voice-and-clips
plan: 02
subsystem: content
tags: [openai, gpt4o, prompt-engineering, voice-persona, content_editor, blog_generator]

# Dependency graph
requires:
  - phase: 03-01
    provides: failing VOICE-01 and VOICE-03 tests for voice persona injection
provides:
  - VOICE_PERSONA constant in content_editor.py (importable by other modules)
  - analyze_content() sends system role message with show persona, temperature=0.7
  - _build_analysis_prompt() with VOICE EXAMPLES block, show-specific hook guidance, energy_candidates stub
  - generate_blog_post() sends system role message on OpenAI path
  - _build_prompt() in blog_generator includes irreverent persona intro and BAD/GOOD examples
affects: 03-03

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "VOICE_PERSONA constant at module top, imported by sibling modules"
    - "OpenAI calls always include system role message before user message"
    - "BAD/GOOD labelled voice examples in LLM prompts to establish show tone"

key-files:
  created: []
  modified:
    - content_editor.py
    - blog_generator.py

key-decisions:
  - "Import VOICE_PERSONA from content_editor into blog_generator rather than duplicating — single source of truth"
  - "temperature raised from 0.3 to 0.7 in analyze_content() — creative voice output needs more variability"
  - "energy_candidates=None added to _build_analysis_prompt() signature now (backward-compatible) to prevent Plan 03 signature conflicts"

patterns-established:
  - "Voice persona: system message pattern — always inject VOICE_PERSONA as first message in messages list"
  - "Voice examples: BAD/GOOD labelled pairs in prompt body prevent corporate-generic drift"

requirements-completed: [VOICE-01, VOICE-03]

# Metrics
duration: 15min
completed: 2026-03-16
---

# Phase 3 Plan 02: Voice Persona Injection Summary

**VOICE_PERSONA constant + system message injection + BAD/GOOD few-shot examples in content_editor and blog_generator to produce show-specific irreverent comedy voice**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-16T22:15:00Z
- **Completed:** 2026-03-16T22:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Defined VOICE_PERSONA constant in content_editor.py (importable module-level)
- Updated analyze_content() to send system message + temperature=0.7 for show voice
- Added VOICE EXAMPLES block (BAD/GOOD pairs) and show-specific hook_caption guidance to _build_analysis_prompt()
- Added energy_candidates=None stub parameter to _build_analysis_prompt() (Plan 03 forward-compatibility)
- Added per-platform tone reminders (YouTube moderated, Twitter/X punchy) to prompt
- Imported VOICE_PERSONA into blog_generator and added it as system message
- Added blog_voice_intro with BAD/GOOD examples to _build_prompt()
- All 10 new VOICE-01 and VOICE-03 tests now pass (67 total across both test files)

## Task Commits

Each task was committed atomically:

1. **Task 1: Inject voice persona and few-shot examples into content_editor** - `9c4a18c` (feat)
2. **Task 2: Inject voice persona into blog_generator** - `5207a7e` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks executed as GREEN phase — tests were written in Plan 01 (RED phase)_

## Files Created/Modified
- `content_editor.py` - Added VOICE_PERSONA constant, system message in analyze_content(), VOICE EXAMPLES block + energy section + hook guidance in _build_analysis_prompt()
- `blog_generator.py` - Imported VOICE_PERSONA, added system message in generate_blog_post(), added blog_voice_intro with BAD/GOOD pairs in _build_prompt()

## Decisions Made
- Imported VOICE_PERSONA from content_editor rather than duplicating it in blog_generator — single source of truth for the show's persona description
- temperature raised from 0.3 to 0.7 in analyze_content() as specified — creative text generation benefits from more variability
- energy_candidates=None stub added now (Plan 03 will fill it) to avoid function signature conflicts when Plan 03 tests run

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - both tasks were straightforward prompt engineering changes. The pre-existing test failures in test_analytics.py and test_audiogram_generator.py are unrelated to this plan (pre-existing, out of scope).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Voice persona injection complete for content_editor and blog_generator
- VOICE_PERSONA constant is importable — Plan 03 can reuse it for AudioClipScorer prompts if needed
- energy_candidates parameter stub is in place — Plan 03 implementation just needs to call _build_analysis_prompt(energy_candidates=...) and the section will populate automatically

## Self-Check: PASSED

- content_editor.py: FOUND
- blog_generator.py: FOUND
- Commit 9c4a18c (Task 1): FOUND
- Commit 5207a7e (Task 2): FOUND

---
*Phase: 03-content-voice-and-clips*
*Completed: 2026-03-16*
