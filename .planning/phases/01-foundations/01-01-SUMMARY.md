---
phase: 01-foundations
plan: 01
subsystem: testing
tags: [openai, content-editor, scheduler, config, import-hygiene]

# Dependency graph
requires: []
provides:
  - openai SDK declared in requirements.txt
  - _parse_llm_response as canonical method name in content_editor.py
  - scheduler.py reads all delay config exclusively from Config attributes
  - main.py has single top-level import re with no inline duplicates
affects: [02-audio-quality, 03-content-voice, 04-distribution]

# Tech tracking
tech-stack:
  added: [openai>=1.0.0]
  patterns: [Config-sourced config (no raw os.getenv in module code)]

key-files:
  created: []
  modified:
    - requirements.txt
    - content_editor.py
    - scheduler.py
    - main.py
    - tests/test_scheduler.py
    - tests/test_content_editor.py

key-decisions:
  - "All scheduler delay config reads through Config class, not raw os.getenv — single source of truth for env vars"
  - "Tests for Config-backed attributes use @patch.object(Config, attr) not @patch.dict(os.environ) — avoids import-time resolution ordering issues"

patterns-established:
  - "Config pattern: module code reads Config.ATTR, tests patch Config attributes directly"
  - "Method naming: LLM-agnostic names (_parse_llm_response not _parse_claude_response)"

requirements-completed: [DEBT-02, DEBT-03]

# Metrics
duration: 15min
completed: 2026-03-16
---

# Phase 1 Plan 1: Dependency and Naming Hygiene Summary

**openai SDK added to requirements.txt, _parse_claude_response renamed to _parse_llm_response, scheduler reads Config attributes instead of os.getenv, and three inline re imports consolidated to main.py module top**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-17T01:24:00Z
- **Completed:** 2026-03-17T01:39:21Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added `openai>=1.0.0` to requirements.txt so `import openai` succeeds after `pip install -r requirements.txt`
- Renamed `_parse_claude_response` to `_parse_llm_response` in content_editor.py (definition + call site + 2 test call sites)
- Replaced 4 `int(os.getenv("SCHEDULE_*_DELAY_HOURS"))` calls in scheduler.__init__ with `Config.SCHEDULE_*_DELAY_HOURS` attribute reads; removed unused `import os`
- Updated 8 test decorators in test_scheduler.py from `@patch.dict("os.environ", ...)` to `@patch.object(Config, ...)` style
- Removed 3 inline `import re` / `import re as _re` statements from main.py function bodies; added single `import re` at module top

## Task Commits

Each task was committed atomically:

1. **Task 1: Add openai SDK and fix naming artifacts** - `979e479` (feat)
2. **Task 2: Move inline re imports to main.py module top** - `557c831` (feat)

## Files Created/Modified
- `requirements.txt` - Added `openai>=1.0.0` in AI/ML section
- `content_editor.py` - Renamed `_parse_claude_response` -> `_parse_llm_response` (line 61 call site, line 263 definition)
- `scheduler.py` - Replaced os.getenv calls with Config attributes in __init__; removed `import os`
- `tests/test_scheduler.py` - Updated 8 test decorators to `@patch.object(Config, ...)` style across 6 test methods
- `tests/test_content_editor.py` - Updated 2 test call sites from `_parse_claude_response` to `_parse_llm_response`
- `main.py` - Added `import re` at line 3; removed 3 inline import statements from function bodies

## Decisions Made
- Used `@patch.object(Config, attr, value)` for scheduler tests rather than patching os.environ, because Config class attributes are evaluated at import time — patching os.environ after import has no effect on already-evaluated class attributes.
- Kept `import os` removal in scheduler.py since no other uses of `os` remained after replacing the four getenv calls.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_content_editor.py calling renamed method**
- **Found during:** Task 1 (rename _parse_claude_response)
- **Issue:** Two test methods in TestChapterParsing called `content_editor._parse_claude_response()` directly, which caused AttributeError after the rename
- **Fix:** Updated both call sites in test_content_editor.py to `_parse_llm_response`
- **Files modified:** `tests/test_content_editor.py`
- **Verification:** `pytest tests/test_content_editor.py` passes (all tests green)
- **Committed in:** `979e479` (part of Task 1 commit)

**2. [Rule 1 - Bug] Updated all TestIsSchedulingEnabled and TestCreateSchedule and TestSaveAndLoadSchedule and TestGetYoutubePublishAt tests to use patch.object**
- **Found during:** Task 1 (scheduler.py Config migration)
- **Issue:** Beyond the two TestUploadSchedulerInit methods called out in the plan, 6 additional test methods in other test classes also used `@patch.dict("os.environ", {"SCHEDULE_*": "..."})` to control delay values — these all broke after the Config migration
- **Fix:** Updated all 6 additional decorators to `@patch.object(Config, ...)` style
- **Files modified:** `tests/test_scheduler.py`
- **Verification:** `pytest tests/test_scheduler.py` - all 23 tests pass
- **Committed in:** `979e479` (part of Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs caused by the plan's own rename/migration changes)
**Impact on plan:** Both fixes are direct consequences of the planned renames — not scope creep. Plan's interface section noted the TestUploadSchedulerInit test update but didn't enumerate all other test classes that also used os.environ patching.

## Issues Encountered
- Pre-existing test failures in `TestRunUploadScheduled` (3 tests) and `TestAnalyticsCollectorInit`, `TestInitDefaults` (2 tests) were present before this plan and remain — these are out of scope for this plan's debt items.

## Next Phase Readiness
- openai SDK is now declared: content_editor.py's OpenAI usage has its dependency tracked
- Config is the single source of truth for all delay values: scheduler tests correctly use @patch.object
- main.py imports are clean: no function-body import statements remain
- Ready for Phase 1 Plan 2 and Plan 3 (audio quality, credential migration)

---
*Phase: 01-foundations*
*Completed: 2026-03-16*
