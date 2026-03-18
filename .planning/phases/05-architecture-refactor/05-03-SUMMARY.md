---
phase: 05-architecture-refactor
plan: "03"
subsystem: pipeline
tags: [refactor, runner, cli, thin-shim, orchestration]
dependency_graph:
  requires: ["05-02"]
  provides: ["pipeline.runner orchestration", "slim main.py", "continue_episode removal"]
  affects: ["main.py", "pipeline/runner.py", "pipeline/__init__.py", "tests/test_scheduler.py"]
tech_stack:
  added: []
  patterns: ["module-level functions replacing class", "components dict pattern", "split transcribe/analysis/audio steps"]
key_files:
  created: ["pipeline/runner.py"]
  modified: ["main.py", "pipeline/__init__.py", "tests/test_scheduler.py"]
  deleted: ["continue_episode.py"]
decisions:
  - "Split _run_transcribe + _run_process_audio in runner.py to preserve analysis-between-audio step ordering without modifying Plan 02 audio.py"
  - "Updated test_scheduler.py patch targets from main.* to pipeline.runner.* — mechanical consequence of extraction"
  - "list_episodes_by_number() and list_available_episodes() accept optional components dict to avoid double DropboxHandler init"
metrics:
  duration_seconds: 745
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  files_deleted: 1
requirements: [DEBT-01, DEBT-05]
---

# Phase 5 Plan 3: Runner Extraction and CLI Shim Summary

**One-liner:** main.py shrunk from 1870 to 134 lines by extracting PodcastAutomation class into pipeline/runner.py as module-level functions.

## What Was Built

### pipeline/runner.py (created, ~1100 lines)

Complete orchestration module extracted from main.py's `PodcastAutomation` class and module-level helper functions:

- `_init_components(test_mode, dry_run, auto_approve, resume)` — returns components dict replacing constructor; includes dry_run shortcut for fast init
- `run(args)` — main episode processing entry point; calls step functions in order: ingest → transcribe → analysis → process_audio → video → distribute
- `_run_transcribe(ctx, components, state)` — Step 2 only, sets `ctx.transcript_data`
- `_run_process_audio(ctx, components, state)` — Steps 4+4.5+6: censor, normalize, MP3
- `dry_run(components)` — full pipeline validation with mock data
- `run_with_notification(args, ...)` — wraps run() with Discord notifications
- `run_upload_scheduled()` — scheduled upload executor
- `run_analytics(episode_arg)` — analytics feedback loop
- `run_search(query)` — full-text search across indexed episodes
- `list_episodes_by_number()` / `list_available_episodes()` — Dropbox episode listing

### main.py (rewritten, 134 lines)

Thin CLI shim containing only:
- Flag parsing (`--test`, `--resume`, `--dry-run`, `--auto-approve`)
- Command dispatch (upload-scheduled, analytics, search, list, latest, epN, interactive)
- `if __name__ == "__main__"` block with KeyboardInterrupt/Exception handlers
- All logic delegated to `from pipeline import ...`

### continue_episode.py (deleted)

Its functionality is now available via `pipeline.run_distribute_only()` (implemented in Plan 02).

### tests/test_scheduler.py (updated)

Patch targets updated from `main.UploadScheduler` / `main.YouTubeUploader` / `main.DiscordNotifier` to `pipeline.runner.*`. Function import updated from `from main import _run_upload_scheduled` to `from pipeline.runner import run_upload_scheduled`.

## Step Order Preservation

The critical ordering challenge: analysis (Step 3) must run BETWEEN transcribe (Step 2) and censor (Step 4). Since audio.py's `run_audio` handles all four audio sub-steps atomically, runner.py splits the work:

```
run_ingest → _run_transcribe → run_analysis → _run_process_audio → run_video → run_distribute
```

This matches main.py's original ordering without modifying any Plan 02 step module.

## Test Results

- `test_main_under_150_lines` — RED → GREEN (134 lines)
- `test_continue_episode_deleted` — RED → GREEN (file deleted)
- `test_pipeline_context_fields` — GREEN (unchanged)
- `test_step_modules_importable` — GREEN (unchanged)
- `test_run_distribute_only_exists` — GREEN (unchanged)
- `test_checkpoint_key_names_unchanged` — GREEN (unchanged)
- Full suite: **333 passed**, 2 pre-existing failures (analytics + audiogram enabled defaults, unrelated to this plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scheduler.py patch targets after extraction**
- **Found during:** Task 2 — full test suite run
- **Issue:** `test_scheduler.py::TestRunUploadScheduled` patched `main.UploadScheduler`, `main.YouTubeUploader`, `main.DiscordNotifier` and imported `from main import _run_upload_scheduled`. After extraction, these no longer exist in main.py.
- **Fix:** Updated 3 test methods to patch `pipeline.runner.*` and import `run_upload_scheduled` from `pipeline.runner`
- **Files modified:** `tests/test_scheduler.py`
- **Commit:** 0602de6

**2. [Rule 2 - Missing] Ruff lint fixes in runner.py before commit**
- **Found during:** Task 1 pre-commit hook
- **Issue:** 6 ruff errors: unused `logging` import, unused `run_audio` import, unused `run_distribute_only` import, unused `json as _json` import, two f-string-without-placeholder warnings
- **Fix:** `ruff check --fix && ruff format` resolved all 6 automatically
- **Files modified:** `pipeline/runner.py`
- **Commit:** 9e766a7

## Self-Check: PASSED

- pipeline/runner.py: FOUND
- main.py: FOUND (134 lines, within 150-line limit)
- pipeline/__init__.py: FOUND
- continue_episode.py: CONFIRMED DELETED
- Commit 9e766a7 (Task 1): FOUND
- Commit 0602de6 (Task 2): FOUND
