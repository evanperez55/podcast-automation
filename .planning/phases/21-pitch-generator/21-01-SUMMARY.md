---
phase: 21-pitch-generator
plan: "01"
subsystem: pitch-generator
tags: [pitch, openai, outreach, cli]
dependency_graph:
  requires: [clients/<slug>.yaml, demo/<slug>/<ep_id>/DEMO.md, output/<ep_id>/*_analysis.json]
  provides: [demo/<slug>/PITCH.md, demo/<slug>/<ep_id>/PITCH.md]
  affects: [main.py, CLAUDE.md]
tech_stack:
  added: []
  patterns: [self.enabled gated on OPENAI_API_KEY, _call_openai_with_retry with exponential backoff, ### SUBJECT/EMAIL/DM delimiter parsing, run_gen_pitch_cli thin CLI dispatcher]
key_files:
  created: [pitch_generator.py, tests/test_pitch_generator.py]
  modified: [main.py, CLAUDE.md]
decisions:
  - "run_gen_pitch_cli extracted to pitch_generator.py to keep main.py under 280-line limit (same pattern as run_find_prospects_cli)"
  - "GPT-4o output parsed via ### SUBJECT/### EMAIL/### DM delimiters rather than JSON mode — avoids escaping errors with conversational prose"
  - "generate_intro_pitch checks self.enabled before any file I/O — disabled state returns None immediately"
  - "Test file names corrected to match *_analysis.json glob pattern (ep25_20260101_analysis.json not ep25_analysis_old.json)"
metrics:
  duration_minutes: 7
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_changed: 4
---

# Phase 21 Plan 01: PitchGenerator Module Summary

**One-liner:** GPT-4o pitch generator with two modes — pre-consent intro from YAML metadata and post-consent demo referencing LUFS/clip/episode metrics, using ### delimiter parsing and exponential backoff retry.

## What Was Built

`pitch_generator.py` implements `PitchGenerator` with two public methods and a standalone CLI dispatcher:

- `generate_intro_pitch(client_slug)` — reads `clients/<slug>.yaml` prospect: block, builds cold outreach context (genre, episode count, value prop), calls GPT-4o, writes `demo/<slug>/PITCH.md`
- `generate_demo_pitch(client_slug, episode_id)` — reads YAML + `demo/<slug>/<ep_id>/DEMO.md` + newest `*_analysis.json`, builds demo-specific context (episode title, summary excerpt, LUFS/clip data), calls GPT-4o, writes `demo/<slug>/<ep_id>/PITCH.md`
- `_call_openai_with_retry` — exact exponential backoff pattern from `content_editor.py` (RateLimitError, APIError, APIConnectionError, APITimeoutError; max 3 retries, 2x backoff capped at 60s)
- `_parse_pitch_response` — streams GPT-4o output line by line, collects buffers per `### SUBJECT` / `### EMAIL` / `### DM` section headers
- `run_gen_pitch_cli(argv)` — thin CLI dispatcher; `gen-pitch <slug>` routes to intro, `gen-pitch <slug> <ep_id>` routes to demo

`main.py` gained one `elif cmd == "gen-pitch"` block (3 lines) dispatching to `run_gen_pitch_cli`. `CLAUDE.md` updated with command reference.

## Tests

30 tests across 8 test classes:
- `TestPitchGeneratorInit` — enabled/disabled flag, no client when disabled
- `TestGenerateIntroPitch` — disabled returns None, missing YAML raises, reads YAML + GPT call, correct path, PITCH.md sections
- `TestGenerateDemoPitch` — disabled returns None, missing DEMO.md returns None, missing analysis returns None, success dict, correct path
- `TestParsePitchResponse` — three sections, subject content, missing sections, empty response
- `TestLoadAnalysis` — newest by mtime, raises on missing
- `TestWritePitchMd` — parent dirs created, returns path, sections present
- `TestCallOpenaiWithRetry` — retries on RateLimitError, raises after max retries, succeeds first attempt
- `TestRunGenPitchCli` — intro dispatch, demo dispatch, usage message, prints path, prints error on None

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test file names didn't match *_analysis.json glob**
- **Found during:** Task 1, GREEN phase
- **Issue:** Test `test_returns_newest_analysis_by_mtime` created `ep25_analysis_old.json` and `ep25_analysis_new.json`. The glob pattern `*_analysis.json` requires filenames to end with `_analysis.json` exactly — `_analysis_old.json` and `_analysis_new.json` do not match.
- **Fix:** Renamed test files to `ep25_20260101_120000_analysis.json` and `ep25_20260201_120000_analysis.json` — matches real pipeline naming convention and the glob pattern.
- **Files modified:** `tests/test_pitch_generator.py`
- **Commit:** cafed7a (test file fix bundled with implementation commit)

## Self-Check: PASSED

- `pitch_generator.py` exists: FOUND
- `tests/test_pitch_generator.py` exists: FOUND
- `main.py` contains `gen-pitch`: FOUND
- Commits 9ffae4a (RED), cafed7a (GREEN), 6056af1 (CLI wire): FOUND
- 757 tests passing, lint clean, main.py at 277 lines
