---
phase: 17-integration-testing-genre-fixes
plan: 01
subsystem: analysis
tags: [openai, gpt4o, content-editor, compliance, multi-client, genre-aware]

# Dependency graph
requires:
  - phase: 15-config-hardening
    provides: "VOICE_PERSONA conditional injection pattern (getattr guard with raising=False)"
  - phase: 16-rss-episode-source
    provides: "client_config._YAML_TO_CONFIG extension pattern"
provides:
  - "Genre-aware clip selection criteria (comedy vs. content-quality) based on VOICE_PERSONA"
  - "Energy suppression via CLIP_SELECTION_MODE=content config"
  - "Genre-aware compliance prompt via _build_compliance_prompt() and COMPLIANCE_STYLE"
  - "YAML mappings content.clip_selection_mode and content.compliance_style"
affects: [content_editor, content_compliance_checker, client_config, pipeline analysis step]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "getattr(Config, 'ATTR', default) guard for dynamically-set client config attributes"
    - "Module-level _build_X_prompt() function pattern for genre-conditional prompt construction"
    - "_CONTEXTS dict keyed by style string with getattr fallback to default key"

key-files:
  created: []
  modified:
    - content_editor.py
    - content_compliance_checker.py
    - client_config.py
    - tests/test_content_editor.py
    - tests/test_content_compliance_checker.py
    - tests/test_client_config.py

key-decisions:
  - "clip_criteria variable in _build_analysis_prompt switches on VOICE_PERSONA presence (None = comedy, set = content-quality)"
  - "energy suppression added between AudioClipScorer call and _build_analysis_prompt call in analyze_content()"
  - "COMPLIANCE_PROMPT renamed to COMPLIANCE_PROMPT_TEMPLATE with {context} placeholder; backward compat via default 'permissive'"
  - "Unknown COMPLIANCE_STYLE values fall back to permissive context (safe default)"

patterns-established:
  - "Genre branching: check getattr(Config, 'VOICE_PERSONA', None) to detect non-FP clients"
  - "New YAML fields: add to _YAML_TO_CONFIG for scalar values; use special handling block for non-scalar"

requirements-completed: [TEST-03, TEST-04]

# Metrics
duration: 5min
completed: 2026-03-28
---

# Phase 17 Plan 01: Genre-Aware Clip Selection and Compliance Summary

**Clip criteria and compliance prompt now branch on VOICE_PERSONA/CLIP_SELECTION_MODE/COMPLIANCE_STYLE so non-comedy clients get appropriate GPT-4o guidance instead of hardcoded comedy context**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T16:23:02Z
- **Completed:** 2026-03-28T16:28:02Z
- **Tasks:** 2 (TDD)
- **Files modified:** 6

## Accomplishments

- Clip criteria in `_build_analysis_prompt` now conditional: no VOICE_PERSONA -> comedy criteria ("Funny or entertaining", "fake problems"), VOICE_PERSONA set -> content-quality criteria ("quotable insight", "narrative hooks")
- Energy candidates suppressed when `CLIP_SELECTION_MODE=content` — prevents irrelevant audio-energy hints for flat-audio genres (true crime, interview)
- `_build_compliance_prompt()` function replaces hardcoded `COMPLIANCE_PROMPT.format()` call; reads `COMPLIANCE_STYLE` from Config and injects appropriate context (permissive/strict/standard)
- Two new YAML keys added to `_YAML_TO_CONFIG`: `content.clip_selection_mode` and `content.compliance_style`
- 639 tests passing (570 pre-existing + 13 new), no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Genre-aware clip selection and energy suppression** - `176c333` (feat)
2. **Task 2: Genre-aware compliance prompt** - `5cdf4af` (feat)

_Note: TDD tasks — tests written first (RED), then implementation (GREEN), both in same task commit_

## Files Created/Modified

- `content_editor.py` - `_build_analysis_prompt` clip_criteria conditional block; energy suppression in `analyze_content`
- `content_compliance_checker.py` - `COMPLIANCE_PROMPT_TEMPLATE` with `{context}` placeholder, `_COMPLIANCE_CONTEXTS` dict, `_build_compliance_prompt()` function
- `client_config.py` - Added `content.clip_selection_mode` and `content.compliance_style` to `_YAML_TO_CONFIG`
- `tests/test_content_editor.py` - `TestGenreAwareClipSelection` class (4 tests)
- `tests/test_content_compliance_checker.py` - `TestComplianceStylePrompt` class (6 tests); added `_build_compliance_prompt` to imports
- `tests/test_client_config.py` - `TestNewYamlMappings` class (2 tests: clip_selection_mode + compliance_style)

## Decisions Made

- Used `VOICE_PERSONA` presence as the genre signal for clip criteria (no new config key needed — VOICE_PERSONA already implies custom genre)
- Kept `COMPLIANCE_PROMPT` module-level name removed in favor of `COMPLIANCE_PROMPT_TEMPLATE` to avoid breaking any external direct references
- Default `COMPLIANCE_STYLE` is "permissive" to preserve exact backward compatibility for Fake Problems
- Unknown `COMPLIANCE_STYLE` values silently fall back to "permissive" via `dict.get(style, contexts["permissive"])`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Spurious `delattr(Config, "_YOUTUBE_TOKEN_PICKLE")` appeared in my `test_compliance_style_mapping` test method (Rule 1 auto-fix: copy-paste artifact from adjacent test). Removed the stray line — all 639 tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Genre-conditional prompt building is complete and tested
- `CLIP_SELECTION_MODE` and `COMPLIANCE_STYLE` can be set in client YAML files immediately
- Pipeline will automatically use appropriate clip criteria and compliance context per client
- Ready for integration testing with real non-comedy audio (Phase 17 remaining plans)

## Self-Check: PASSED

All files verified present. Both task commits (176c333, 5cdf4af) confirmed in git log.

---
*Phase: 17-integration-testing-genre-fixes*
*Completed: 2026-03-28*
