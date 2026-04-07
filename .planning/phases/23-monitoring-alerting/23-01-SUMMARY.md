---
phase: 23-monitoring-alerting
plan: "01"
subsystem: notifications
tags: [monitoring, discord, pipeline, alerting]
dependency_graph:
  requires: []
  provides: [per-step-discord-alerts, duration-tracking-in-results]
  affects: [pipeline/runner.py, notifications.py]
tech_stack:
  added: []
  patterns: [_run_step wrapper pattern, time.time() duration tracking]
key_files:
  created: []
  modified:
    - pipeline/runner.py
    - notifications.py
    - tests/test_notifications.py
    - tests/test_runner.py
decisions:
  - "_run_step closure inside _run_pipeline: direct components dict access avoids passing notifier through every step call signature"
  - "compliance_check wrapped as inline function _run_compliance_check: enables uniform _run_step wrapping without restructuring the inline block"
  - "Error truncation at 500 chars in notify_failure: implements T-23-01 info disclosure mitigation from threat model"
  - "step='pipeline_setup' in outer run_with_notification catch: distinguishes arg-parsing/init errors from per-step errors"
metrics:
  duration_minutes: 20
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 4
---

# Phase 23 Plan 01: Discord Monitoring and Alerting Summary

Per-step Discord failure alerts and duration tracking wired into the pipeline runner. Every pipeline step now sends a Discord notification when it raises an exception, and successful runs report total duration formatted as "Xm Ys".

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add per-step failure notifications and duration tracking | 4c4cad6 | notifications.py, pipeline/runner.py, tests/test_notifications.py |
| 2 | Add tests for per-step failure notifications and duration tracking | e3eb640 | tests/test_runner.py |

## What Was Built

### notifications.py
- `notify_success`: Duration field added incrementally to fields list. Reads `results.get("duration_seconds")`, formats as `"{m}m {s}s"`. Omits field when key absent (backward compatible).
- `notify_failure`: Error text truncated to 500 chars before embedding in field value and description (T-23-01 info disclosure mitigation).

### pipeline/runner.py
- Added `import time` at module top.
- `_run_step(step_name, fn, *step_args)` closure defined inside `_run_pipeline`. On exception: gets `notifier` from `components`, calls `notify_failure(ep_info, e, step=step_name)`, re-raises.
- All 7 pipeline steps wrapped: `ingest`, `transcribe`, `analysis`, `compliance_check`, `audio_processing`, `video`, `distribute`.
- `compliance_check` block extracted to inner function `_run_compliance_check` to enable uniform wrapping.
- `start_time = time.time()` recorded before first step. `elapsed = time.time() - start_time` computed after last step. `results["duration_seconds"] = elapsed` added to results dict.
- Outer `run_with_notification` catch updated: `step="pipeline_setup"` (was `"process_episode"`) to distinguish init-time errors from per-step errors.

### tests/test_notifications.py
- `TestNotifySuccessDuration` class: 3 tests covering duration present (754s → "12m 34s"), duration absent (no field), zero duration ("0m 0s").

### tests/test_runner.py
- `TestRunPipelineStepNotifications` class: 4 tests covering step failure notifies with correct step name, exception re-raises, disabled notifier skips call without crash, success path includes `duration_seconds` in results.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Truncate error text in notify_failure to 500 chars**
- **Found during:** Task 1 (threat model review — T-23-01)
- **Issue:** Error text passed directly to Discord embed could expose file paths or internal state
- **Fix:** `error_text = str(error)[:500]` applied before embed field and description
- **Files modified:** notifications.py
- **Commit:** 4c4cad6

**2. [Rule 1 - Bug] compliance_check block was inline, not callable**
- **Found during:** Task 1
- **Issue:** The compliance check block was an inline sequence of statements, not a function — it could not be passed to `_run_step`
- **Fix:** Extracted to `_run_compliance_check(ctx, components, state)` inner function defined inline in `_run_pipeline`
- **Files modified:** pipeline/runner.py
- **Commit:** 4c4cad6

## Verification Results

- `uv run pytest tests/test_notifications.py tests/test_runner.py` — 64 passed
- `uv run ruff check notifications.py pipeline/runner.py tests/test_notifications.py tests/test_runner.py` — all checks passed
- `grep "notify_failure.*step=" pipeline/runner.py` — 2 matches (one in _run_step, one in run_with_notification outer catch)
- `grep "_run_step" pipeline/runner.py` — 7 step-wrapping call sites confirmed
- `grep "duration_seconds" notifications.py pipeline/runner.py` — matches in both files
- Full suite: 1374 passed, 4 pre-existing failures in test_website_generator.py (unrelated)

## Known Stubs

None. All changes wire real behavior.

## Threat Flags

None beyond what the plan's threat model already covered (T-23-01 mitigated inline).

## Self-Check: PASSED

- notifications.py modified: confirmed (contains `duration_seconds`, `Duration` field, 500-char truncation)
- pipeline/runner.py modified: confirmed (contains `import time`, `_run_step`, `start_time`, `duration_seconds` in results)
- tests/test_notifications.py: confirmed (contains `test_notify_success_with_duration`, `"12m 34s"`)
- tests/test_runner.py: confirmed (contains `test_step_failure_sends_notification`, `test_pipeline_success_includes_duration`)
- Task 1 commit 4c4cad6: exists
- Task 2 commit e3eb640: exists
