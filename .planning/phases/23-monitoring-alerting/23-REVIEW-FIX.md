---
phase: 23-monitoring-alerting
fixed_at: 2026-04-06T00:00:00Z
review_path: .planning/phases/23-monitoring-alerting/23-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 23: Code Review Fix Report

**Fixed at:** 2026-04-06
**Source review:** .planning/phases/23-monitoring-alerting/23-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01 through WR-04; IN-01 and IN-02 excluded by fix_scope: critical_warning)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `duration_seconds` in results dict is pipeline wall-clock time, not episode duration

**Files modified:** `pipeline/runner.py`
**Commit:** 95a2703
**Applied fix:** In `_run_pipeline` around line 610, split the single `duration_seconds` key into two: `pipeline_duration_seconds` holds the wall-clock elapsed time (`elapsed`), and `duration_seconds` now holds the episode's actual playback duration via `ctx.transcript_data.get("duration") if ctx.transcript_data else None`. The Discord success notification will now display the episode playback length rather than pipeline runtime.

---

### WR-02: Double Discord notification for mid-pipeline failures in `run_with_notification`

**Files modified:** `pipeline/runner.py`
**Commit:** 5436d90
**Applied fix:** Two-part sentinel flag approach. In `_run_step`, after calling `notifier.notify_failure`, the exception is tagged with `e._step_notified = True` before re-raising. In `run_with_notification`'s outer `except` block, the notification is now guarded by `if not getattr(e, "_step_notified", False)`, so setup-phase failures still trigger a notification but mid-pipeline step failures (already notified by `_run_step`) do not generate a duplicate.

---

### WR-03: Non-atomic lock file check-then-write race condition (Windows)

**Files modified:** `pipeline/runner.py`
**Commit:** fed0bd9
**Applied fix:** Added a `_pid_is_running(pid)` module-level helper that uses `ctypes.windll.kernel32.OpenProcess` on Windows (since `os.kill(pid, 0)` always raises `OSError` on Windows) and `os.kill(pid, 0)` on POSIX. `_acquire_pipeline_lock` now calls `_pid_is_running(old_pid)` instead of the bare `os.kill` try/except, correctly returning `False` (locked) on Windows when the process is genuinely running.

---

### WR-04: `_do_upload` closure defined inside `for item in pending` loop with `@retry_with_backoff` decorator

**Files modified:** `pipeline/runner.py`
**Commit:** 5a815f9
**Applied fix:** Extracted the decorated inner function to a module-level `_execute_scheduled_upload(uploader_instance, upload_item, platform)` function placed just before `run_upload_scheduled`. The `@retry_with_backoff` decorator is applied once at definition time. The loop body now calls `_execute_scheduled_upload(uploader_instance, item, platform)` with `platform` as an explicit argument, eliminating both the per-iteration redecoration and the closure reference.

---

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-04-06_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
