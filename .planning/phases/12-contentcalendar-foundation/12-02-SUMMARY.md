---
phase: 12-contentcalendar-foundation
plan: 02
subsystem: distribution
tags: [content-calendar, pipeline, upload-scheduled, dry-run, scheduling]

# Dependency graph
requires:
  - phase: 12-01
    provides: ContentCalendar class with plan_episode(), get_pending_slots(), mark_slot_uploaded(), mark_slot_failed(), get_calendar_display()
provides:
  - Step 8.7 in distribute pipeline calls ContentCalendar.plan_episode() after each episode run
  - _dispatch_calendar_slot() helper maps calendar slot content to uploader method calls
  - run_upload_scheduled() scans content_calendar.json and dispatches past-due slots
  - dry_run() shows 5-slot calendar spread with dates/times/platforms
  - 8 new integration tests covering all wiring paths
affects: [phase-13, phase-14, pipeline-distribute, upload-scheduled, dry-run]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Late import pattern: ContentCalendar imported inside try/except blocks (not top-level) to keep it optional/non-breaking"
    - "_dispatch_calendar_slot: platform-branching function that maps slot content fields to uploader method signatures"
    - "Calendar scan after upload_schedule.json loop: shared dispatch dict used by both paths"

key-files:
  created: []
  modified:
    - pipeline/steps/distribute.py
    - pipeline/runner.py
    - content_calendar.py
    - tests/test_content_calendar.py

key-decisions:
  - "Late import (inside try/except) for ContentCalendar in distribute.py and runner.py keeps it optional — failures don't break the pipeline"
  - "Shared dispatch dict moved above for loop in run_upload_scheduled so it's available for both upload_schedule.json and calendar slots"
  - "get_calendar_display() fixed to return dt as datetime object (was ISO string) for dry-run .strftime() formatting"
  - "Patch target for ContentCalendar in integration tests is content_calendar.ContentCalendar (source module) not pipeline.steps.distribute.ContentCalendar (local import)"

patterns-established:
  - "Calendar wiring pattern: import inside try/except, check .enabled, call method, log result"
  - "Slot dispatch pattern: _dispatch_calendar_slot branches on platform and slot_type, maps content keys to uploader args"

requirements-completed: [CAL-03, CAL-04]

# Metrics
duration: 15min
completed: 2026-03-19
---

# Phase 12 Plan 02: ContentCalendar Pipeline Wiring Summary

**ContentCalendar wired end-to-end: Step 8.7 in distribute generates slots per episode, run_upload_scheduled dispatches past-due calendar slots per platform, dry_run displays the 5-slot D-1/D0/D+2/D+4/D+6 spread with dates and times**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-19
- **Completed:** 2026-03-19
- **Tasks:** 1 (+ 1 checkpoint human-verify)
- **Files modified:** 4

## Accomplishments
- Step 8.7 added to distribute.py: calls ContentCalendar.plan_episode() after webpage deployment, before search indexing; wrapped in try/except (non-critical)
- _dispatch_calendar_slot() helper added to runner.py: routes episode/clip/teaser slots to correct uploader methods per platform
- run_upload_scheduled() extended: after existing upload_schedule.json loop, scans content_calendar.json for all episodes and dispatches past-due pending slots
- dry_run() now prints content calendar preview with 5 slots showing D-1/D0/D+2/D+4/D+6 dates, times, platform assignments
- 8 new integration tests added (27 total in test_content_calendar.py), full suite 514 passing

## Task Commits

1. **Task 1: Wire calendar into distribute, upload-scheduled, and dry-run** - `481b0c7` (feat)

## Files Created/Modified
- `pipeline/steps/distribute.py` - Added Step 8.7 block that calls ContentCalendar.plan_episode()
- `pipeline/runner.py` - Added _dispatch_calendar_slot() helper and calendar slot scan in run_upload_scheduled(); added calendar preview in dry_run()
- `content_calendar.py` - Fixed get_calendar_display() to return dt as datetime object (was ISO string)
- `tests/test_content_calendar.py` - Added TestDryRunDisplay, TestDistributeIntegration, TestUploadScheduledIntegration classes

## Decisions Made
- Late import pattern (inside try/except) for ContentCalendar in both distribute.py and runner.py — keeps calendar optional, failures don't break pipeline
- Shared dispatch dict moved above the for loop in run_upload_scheduled so it's available for both upload_schedule.json and calendar dispatch paths
- Patch target for ContentCalendar integration tests must be `content_calendar.ContentCalendar` (source module) not the local import path — because the import happens inside the function body

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed get_calendar_display() returning dt as ISO string instead of datetime**
- **Found during:** Task 1 (writing TestDryRunDisplay tests)
- **Issue:** The interface spec says `dt: datetime` but implementation returned `dt: dt.isoformat()` (a string). The dry_run() display code calls `slot['dt'].strftime(...)` which requires a datetime object.
- **Fix:** Changed `"dt": dt.isoformat()` to `"dt": dt` in content_calendar.py get_calendar_display()
- **Files modified:** content_calendar.py
- **Verification:** TestDryRunDisplay.test_get_calendar_display_returns_slots_with_labels passes; dry_run shows formatted dates
- **Committed in:** 481b0c7 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for dry_run() to format dates correctly. No scope creep.

## Issues Encountered
- Patching `pipeline.steps.distribute.ContentCalendar` fails because ContentCalendar is imported inside a function body with `from content_calendar import ContentCalendar`. Solution: patch `content_calendar.ContentCalendar` at the source module instead.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ContentCalendar fully integrated into pipeline: generates during episode runs, dispatches via upload-scheduled, visible in dry-run
- Phase 12 complete — ready for Phase 13 (CI/CD) or Phase 14 (whatever is next)
- CAL-03 and CAL-04 requirements fulfilled

---
*Phase: 12-contentcalendar-foundation*
*Completed: 2026-03-19*
