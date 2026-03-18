---
phase: 02-audio-quality
plan: 03
subsystem: audio_processor
tags: [normalization, lufs, ebu-r128, ffmpeg, subprocess, loudnorm]
dependency_graph:
  requires: [02-02]
  provides: [normalize_audio two-pass LUFS, _parse_loudnorm_json helper]
  affects: [pipeline step 4.5 Normalize]
tech_stack:
  added: [subprocess, json, re (stdlib only)]
  patterns: [two-pass FFmpeg loudnorm, module-level helper function, TDD red-green]
key_files:
  modified:
    - audio_processor.py
decisions:
  - "_parse_loudnorm_json added as module-level function (not method) so tests can patch audio_processor._parse_loudnorm_json independently of the class method"
  - "Class method _parse_loudnorm_json kept as a thin wrapper delegating to module-level function — test patching targets the method via audio_processor.AudioProcessor._parse_loudnorm_json"
  - "Pass-2 output measurement failure falls back gracefully: output_lufs = Config.LUFS_TARGET, output_lra = input_lra — no exception propagation on missing pass-2 JSON"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-17"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
  files_created: 0
---

# Phase 02 Plan 03: Two-Pass FFmpeg LUFS Normalization Summary

Two-pass EBU R128 loudnorm via FFmpeg subprocess replacing pydub dBFS normalization, with AGC fallback warning and per-episode LUFS/gain logging.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add _parse_loudnorm_json() and rewrite normalize_audio() | b6e7d7e | audio_processor.py |

## What Was Built

`normalize_audio()` in `audio_processor.py` was fully replaced. The old implementation used `AudioSegment.from_file()` + `audio.dBFS` + `audio.apply_gain()` — a simple dBFS adjustment that does not account for perceived loudness. The new implementation runs two FFmpeg subprocess calls with the `loudnorm` filter:

**Pass 1 (measurement):** FFmpeg reads the input and outputs JSON to stderr with measured input LUFS (`input_i`), true peak (`input_tp`), LRA, threshold, and normalization type. The `_parse_loudnorm_json()` helper scans stderr for the first `{...}` block using `re.search`.

**Pass 2 (apply):** FFmpeg re-encodes the audio using `linear=true` and all measured values from pass 1, targeting `-16 LUFS / LRA 11 / TP -1.5`. Output is 44100 Hz WAV.

A `_parse_loudnorm_json()` module-level function was added to extract JSON from FFmpeg's mixed stderr output. The class method delegates to it.

## Decisions Made

- `_parse_loudnorm_json` exists at both module level (for logic) and as a class method wrapper (for testability via `audio_processor.AudioProcessor._parse_loudnorm_json`).
- AGC/dynamic mode emits `logger.warning()` (no exception) — audio is still usable, just dynamically compressed.
- Pass-2 JSON parse failure falls back to `output_lufs = Config.LUFS_TARGET` and `output_lra = input_lra` rather than raising, since pass-2 measurement absence is non-fatal.
- All subprocess calls include `stdin=subprocess.DEVNULL` to prevent hangs on systems that inherit a console stdin.

## Verification

- `pytest tests/test_audio_processor.py::TestNormalizeAudio`: 7/7 PASSED
- `pytest tests/test_audio_processor.py`: 32/32 PASSED
- `ruff check audio_processor.py`: all checks passed
- `ruff format audio_processor.py`: formatted (minor style changes)

## Deviations from Plan

None — plan executed exactly as written. The `_parse_loudnorm_json` stub (instance method raising `NotImplementedError`) was present from Plan 02; it was replaced with a thin wrapper delegating to the new module-level function, satisfying both the plan spec and the test's patch target.

## Self-Check: PASSED

- audio_processor.py: FOUND
- 02-03-SUMMARY.md: FOUND
- commit b6e7d7e: FOUND
