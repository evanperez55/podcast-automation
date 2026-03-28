---
phase: 15-config-hardening
plan: 01
subsystem: config
tags: [client-config, yaml-validation, multi-client, censorship, podcast-identity]

# Dependency graph
requires: []
provides:
  - "Required field check for content.names_to_remove in load_client_config() — raises ValueError on missing field"
  - "Active content configuration print block in validate_client() showing live Config values"
affects: [pipeline, runner, multi-client, validate-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "content.names_to_remove required in all client YAML configs — explicit presence prevents host-name leakage"
    - "monkeypatch.setattr(Config, 'NAMES_TO_REMOVE', ...) needed in all tests calling activate_client() for isolation"

key-files:
  created: []
  modified:
    - "client_config.py"
    - "tests/test_client_config.py"

key-decisions:
  - "null and empty list are both valid for names_to_remove (field must be present, not necessarily non-empty)"
  - "Active config block printed before summary count line, after output dir checks"
  - "VOICE_PERSONA cleanup in test needs monkeypatch.delattr raising=False at test start, not just at teardown"

patterns-established:
  - "Config isolation in tests: any test that calls activate_client() must monkeypatch NAMES_TO_REMOVE (and VOICE_PERSONA if applicable) to prevent state leakage"

requirements-completed:
  - CFG-01
  - CFG-03

# Metrics
duration: 25min
completed: 2026-03-28
---

# Phase 15 Plan 01: Config Hardening — Required Field Validation and Active Config Audit Summary

**load_client_config() raises ValueError when content.names_to_remove is absent, and validate-client now prints a live Config audit showing podcast name, voice persona, names_to_remove, words_to_censor, blog_voice, and scoring_profile**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-28T18:00:00Z
- **Completed:** 2026-03-28T18:23:47Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 2

## Accomplishments

- `load_client_config()` now raises `ValueError` if `content.names_to_remove` is absent, preventing Fake Problems host names from silently leaking into non-FP client output (CFG-01)
- `validate-client` prints an "Active content configuration" section showing live `Config` values after `activate_client()` runs, enabling users to audit what GPT-4o will actually receive (CFG-03)
- Fixed test isolation bug: all tests that call `activate_client()` now register `NAMES_TO_REMOVE` with monkeypatch so teardown properly restores the default Fake Problems host names
- Test count: 570 → 579 (9 new tests: 3 for required-field validation, 3 for active config output, 3 fix isolation)

## Task Commits

1. **Task 1: Add required-field check for names_to_remove** - `dc20a97` (feat)
2. **Task 2: Add active config print block to validate_client** - `f9eb222` (feat)

## Files Created/Modified

- `client_config.py` — Added required-field check in `load_client_config()` (lines 105-113); added "Active content configuration" print block in `validate_client()` (lines 422-460)
- `tests/test_client_config.py` — Updated `MINIMAL_YAML` to include `content.names_to_remove: []`; updated all inline YAMLs; added `monkeypatch` guards for `NAMES_TO_REMOVE` in 9 test methods; added 6 new test methods

## Decisions Made

- null and empty list are both valid values for `names_to_remove` — the requirement is that the field be PRESENT in the YAML, not that it be non-empty. This allows clients who genuinely have no host names to censor to set `[]` explicitly.
- Active config block is printed before the summary count line, after the output dir checks — users see infrastructure status then content configuration.
- `test_validate_prints_voice_persona_or_default` handles cleanup by calling `monkeypatch.delattr(Config, "VOICE_PERSONA", raising=False)` at test start, then manually calling `delattr` between sub-tests (a) and (b).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added NAMES_TO_REMOVE monkeypatch guards to existing tests**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** After adding the required-field check, `activate_client()` calls `apply_client_config()` which sets `Config.NAMES_TO_REMOVE = []` directly. Existing tests that called `activate_client()` without registering NAMES_TO_REMOVE with monkeypatch leaked `[]` into subsequent tests, causing `TestBackwardCompatibility.test_defaults_unchanged_without_client` to fail.
- **Fix:** Added `monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)` to 9 test methods: `test_output_dirs_auto_derived`, `test_activate_sets_config_and_output_dirs`, `test_validate_shows_config_status`, `test_validate_no_ping_by_default`, `test_status_with_episodes`, `test_status_no_output_dir`, `test_unknown_platform`, `test_youtube_missing_credentials`, `test_dropbox_prints_instructions`
- **Files modified:** tests/test_client_config.py
- **Verification:** All 33 test_client_config.py tests pass; full suite 579 green
- **Committed in:** dc20a97 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical test isolation)
**Impact on plan:** Required for test isolation correctness. No scope creep.

## Issues Encountered

- ruff auto-format triggered between Edit calls and reverted the `client_config.py` active config block; had to re-apply. Fixed by using proper if/else structure instead of conditional expressions in print statements.
- `test_validate_prints_active_podcast_name` initially asserted `"Fake Problems" not in output` — but the "(built-in Fake Problems default)" voice persona line contains that string. Updated assertion to `"Podcast name:    Cold Case Chronicles" in output` instead.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-01 and CFG-03 requirements complete
- All 579 tests green
- Phase 15 plan 02 (`DropboxHandler` optional construction) can proceed

---
*Phase: 15-config-hardening*
*Completed: 2026-03-28*

## Self-Check: PASSED

- client_config.py: FOUND
- tests/test_client_config.py: FOUND
- 15-01-SUMMARY.md: FOUND
- Commit dc20a97: FOUND
- Commit f9eb222: FOUND
