---
phase: 15-config-hardening
plan: "02"
subsystem: content_editor
tags: [voice-persona, genre-config, prompt-engineering, client-isolation]
dependency_graph:
  requires: [15-01]
  provides: [conditional-voice-examples, genre-yaml-configs]
  affects: [content_editor.py, clients/]
tech_stack:
  added: []
  patterns: [conditional-prompt-injection, getattr-guard-pattern]
key_files:
  created:
    - clients/true-crime-client.yaml
    - clients/business-interview-client.yaml
  modified:
    - content_editor.py
    - tests/test_content_editor.py
decisions:
  - "Use getattr(Config, 'VOICE_PERSONA', None) guard — attribute may not exist on Config class by default"
  - "monkeypatch with raising=False needed because VOICE_PERSONA is not a default Config attribute"
metrics:
  duration: "~20 minutes"
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_changed: 4
---

# Phase 15 Plan 02: Conditional Voice Examples and Genre Client YAMLs Summary

Conditional voice examples injection in `_build_analysis_prompt()` — FP-specific comedy BAD/GOOD examples are now only injected when no custom `voice_persona` is configured, preventing voice leakage into non-FP clients. Two real genre client YAML files created for true crime and business interview formats.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Make voice_examples conditional in content_editor.py | bd7b809 | content_editor.py, tests/test_content_editor.py |
| 2 | Create true-crime and business-interview client YAML configs | d9bed14 | clients/true-crime-client.yaml, clients/business-interview-client.yaml |

## What Was Built

**Task 1 — Conditional voice examples (TDD):**
- In `content_editor._build_analysis_prompt()`, replaced unconditional `voice_examples` string assignment with a check: `custom_persona = getattr(Config, "VOICE_PERSONA", None)`
- When `custom_persona` is truthy: `voice_examples = ""` (no FP examples injected)
- When `custom_persona` is falsy/None: full FP voice examples block injected (existing behavior preserved)
- Added `TestVoiceExamplesConditional` class with 3 tests covering: excluded with custom persona, included without persona, included when persona is explicitly None

**Task 2 — Genre YAML files:**
- `clients/true-crime-client.yaml`: "Cold Case Chronicles" with serious investigative `voice_persona`, evidence-based `blog_voice`, and 4-criteria `scoring_profile` (case_significance, new_evidence, victim_centered, accessible)
- `clients/business-interview-client.yaml`: "Founders in the Field" with direct professional `voice_persona`, substantive operator-focused `blog_voice`, and 4-criteria `scoring_profile` (actionable_insight, contrarian, specific, broadly_relevant)
- Both have `names_to_remove: []` (required by Plan 15-01 validation) and all credential sections with null values

## Decisions Made

- Used `getattr(Config, "VOICE_PERSONA", None)` guard in the conditional — `VOICE_PERSONA` is not defined as a class attribute on `Config` by default; it's set dynamically by `activate_client()`. Using `getattr` with a default avoids AttributeError.
- Test monkeypatching required `raising=False` because `VOICE_PERSONA` doesn't exist on `Config` by default — standard `monkeypatch.setattr` would raise AttributeError otherwise.
- Did NOT modify line 85 (`voice = getattr(Config, "VOICE_PERSONA", None) or VOICE_PERSONA`) — that line correctly handles the system-message persona. Only the user-message `voice_examples` block needed the conditional.

## Verification Results

- `uv run pytest tests/test_content_editor.py -x -v -k "voice_examples"` — 4 passed
- `uv run pytest` — 579 passed, 0 failed
- `uv run ruff check content_editor.py` — all checks passed
- Both YAML files parse correctly and contain all required fields (voice_persona, blog_voice, scoring_profile, names_to_remove)

## Deviations from Plan

**1. [Rule 2 - Auto-fix] Carried forward uncommitted CFG-03 test additions**
- Found during: Task 2 commit
- Issue: The git stash pop (from stash created to diagnose test failures) re-applied uncommitted test_client_config.py changes from Plan 15-01's CFG-03 work that were saved but not committed
- Fix: These test additions were already committed as part of the stash pop result (commit f9eb222); no action needed
- Files modified: tests/test_client_config.py (via stash pop, not direct modification)
- Impact: 3 new TestValidateClient tests added (test_validate_prints_active_podcast_name, test_validate_prints_active_names_to_remove, test_validate_prints_voice_persona_or_default) — all pass

None from plan specification — plan executed as designed.

## Self-Check: PASSED

- content_editor.py: FOUND
- clients/true-crime-client.yaml: FOUND
- clients/business-interview-client.yaml: FOUND
- .planning/phases/15-config-hardening/15-02-SUMMARY.md: FOUND
- Commit bd7b809 (voice examples conditional): FOUND
- Commit d9bed14 (genre YAMLs): FOUND
- Full test suite: 579 passed, 0 failed
