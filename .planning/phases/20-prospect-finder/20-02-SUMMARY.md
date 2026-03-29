---
phase: 20-prospect-finder
plan: 02
subsystem: cli
tags: [itunes, rss, prospect-finder, cli, yaml]

# Dependency graph
requires:
  - phase: 20-01
    provides: ProspectFinder class with search(), enrich_from_rss(), save_prospect()
  - phase: 19-outreach-tracker
    provides: OutreachTracker for prospect registration on save
provides:
  - find-prospects CLI command in main.py
  - run_find_prospects_cli(argv) in prospect_finder.py for thin-shim dispatch
  - Interactive save flow: select result, enrich from RSS, scaffold YAML, register in tracker
affects: [main.py, prospect_finder.py, CLAUDE.md]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CLI logic extracted to source module (run_find_prospects_cli) to keep main.py under 280-line test limit"
    - "Lazy import ProspectFinder inside CLI dispatch branch"

key-files:
  created: []
  modified:
    - main.py
    - prospect_finder.py
    - CLAUDE.md

key-decisions:
  - "Moved run_find_prospects_cli() into prospect_finder.py rather than main.py to respect 280-line test limit on main.py"
  - "save_flag condition always prompts when results exist (save_flag or results), not just when --save is explicitly set"

patterns-established:
  - "CLI handlers too large for main.py go in the source module as run_*_cli(argv) functions"

requirements-completed: [DISC-01, DISC-02, DISC-03]

# Metrics
duration: 15min
completed: 2026-03-28
---

# Phase 20 Plan 02: Prospect Finder CLI Summary

**find-prospects CLI command wiring iTunes search, ranked table output, and interactive RSS-enriched YAML save into main.py dispatch**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-28T00:00:00Z
- **Completed:** 2026-03-28T00:00:00Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Wired `find-prospects` branch in `_handle_client_command()` with lazy import of `run_find_prospects_cli`
- Implemented `run_find_prospects_cli(argv)` in `prospect_finder.py`: flag parsing, iTunes search, ranked table print, interactive save prompt
- Save flow: slug generation, RSS enrichment via `enrich_from_rss()`, `save_prospect()` for YAML scaffold + tracker registration, contact email display
- Updated CLAUDE.md with command reference
- All 727 tests pass, ruff clean, main.py at 273 lines (under 280-line test limit)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire find-prospects CLI command into main.py** - `30794a1` (feat)

**Plan metadata:** (to be added after final commit)

## Files Created/Modified
- `main.py` - Added `elif cmd == "find-prospects"` branch with lazy import of `run_find_prospects_cli`
- `prospect_finder.py` - Added `run_find_prospects_cli(argv)` module-level function with full CLI logic
- `CLAUDE.md` - Added find-prospects command reference to Commands section

## Decisions Made
- Extracted CLI logic into `prospect_finder.py` as `run_find_prospects_cli(argv)` instead of keeping it in main.py. A `TestMainLineCount` test enforces a 280-line ceiling on main.py; the full implementation would have pushed it to 353 lines. Keeping the logic in the source module it uses follows the existing thin-shim pattern.
- The save prompt fires whenever results are non-empty (not only when `--save` is passed), matching the plan spec: "If --save flag present OR results returned."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extracted find-prospects logic to prospect_finder.py to satisfy 280-line test**
- **Found during:** Task 1 (Wire find-prospects CLI command)
- **Issue:** Inline implementation in main.py pushed line count to 353; `TestMainLineCount.test_main_under_200_lines` asserts `<= 280`, causing test failure
- **Fix:** Moved full CLI logic into `run_find_prospects_cli(argv)` in `prospect_finder.py`; main.py branch becomes 3 lines
- **Files modified:** main.py, prospect_finder.py
- **Verification:** `pytest tests/test_pipeline_refactor.py::TestMainLineCount` passes; all 727 tests green
- **Committed in:** 30794a1 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - line count constraint)
**Impact on plan:** No scope creep. Logic placement is better anyway — CLI handler lives with the module it orchestrates.

## Issues Encountered
- main.py 280-line ceiling enforced by existing test — handled as Rule 1 auto-fix by relocating implementation to prospect_finder.py.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 complete: ProspectFinder built (plan 01) and wired to CLI (plan 02)
- Users can run `uv run main.py find-prospects --genre comedy` to discover, inspect, and save podcast prospects
- Outreach tracker is pre-populated at "identified" status on save
- Ready for Phase 21: pitch generation and outreach workflow

---
*Phase: 20-prospect-finder*
*Completed: 2026-03-28*
