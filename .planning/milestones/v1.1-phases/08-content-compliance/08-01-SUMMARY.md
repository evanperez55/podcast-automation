---
phase: 08-content-compliance
plan: 01
subsystem: content-compliance
tags: [compliance, gpt4o, youtube, safety-gate, censorship]
dependency_graph:
  requires: [content_editor.py, config.py, openai]
  provides: [ContentComplianceChecker, VIOLATION_CATEGORIES, SEVERITY_MAP]
  affects: [pipeline/runner.py (future step 3.6), pipeline/steps/distribute.py (future upload gate)]
tech_stack:
  added: []
  patterns: [self.enabled env-gated pattern, openai.OpenAI client pattern, JSON report to output dir]
key_files:
  created:
    - content_compliance_checker.py
    - tests/test_content_compliance_checker.py
  modified: []
decisions:
  - "temperature=0.1 for GPT-4o compliance calls (deterministic classification, not creative)"
  - "critical = hate_speech + dangerous_misinformation + self_harm_promotion; warning = graphic_violence + harassment + sexual_content"
  - "save_report() separates flagged (critical) from warnings in JSON output for clear human review"
  - "comedy podcast context instruction included in prompt to prevent over-flagging dark humor"
metrics:
  duration: 5min
  completed: "2026-03-18"
  tasks_completed: 1
  files_changed: 2
---

# Phase 8 Plan 1: ContentComplianceChecker Module Summary

## One-liner

GPT-4o YouTube compliance checker with severity-gated critical flag, JSON report, and censor_timestamps-compatible output.

## What Was Built

`ContentComplianceChecker` — a standalone module that analyzes podcast transcripts against YouTube community guidelines using GPT-4o. It produces a structured compliance report (timestamps, quoted text, violation category) and exposes `get_censor_entries()` for merging flagged segments into the existing censorship pipeline.

### Key behaviors

- `check_transcript()` formats transcript segments as `[HH:MM:SS] text` lines, calls GPT-4o at temperature=0.1, parses the JSON array response, attaches severity from `SEVERITY_MAP`, and sets `critical=True` if any item is severity "critical"
- `save_report()` writes a JSON file to `episode_output_dir/compliance_report_{episode_number}_{timestamp}.json`, creating the directory if it does not exist. Report separates items into `flagged` (critical severity) and `warnings` (warning severity)
- `get_censor_entries()` converts flagged items to `{"start_seconds", "end_seconds", "reason": "Compliance: {category}", "context": text[:100]}` dicts compatible with `AudioProcessor.apply_censorship()`
- `COMPLIANCE_ENABLED=false` returns `{"flagged": [], "critical": False, "report_path": None}` without calling the LLM

### Violation categories

| Category | Severity |
|---|---|
| hate_speech | critical |
| dangerous_misinformation | critical |
| self_harm_promotion | critical |
| graphic_violence | warning |
| harassment | warning |
| sexual_content | warning |

## Tests

21 tests across 6 test classes:

| Class | Covers |
|---|---|
| TestCheckTranscript | GPT-4o call, structured return, empty response, segment formatting |
| TestDisabled | COMPLIANCE_ENABLED=false bypasses LLM |
| TestReportStructure | JSON schema, flagged/warnings separation |
| TestSaveReport | File creation, directory creation, filename pattern |
| TestMergeIntoTimestamps | censor_timestamps format, context truncation, empty case |
| TestSeverityMap | critical/warning classification, category coverage |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `content_compliance_checker.py` exists: FOUND
- `tests/test_content_compliance_checker.py` exists: FOUND
- Commit `89ff71b` exists: FOUND
- 21/21 tests pass, 0 new regressions (2 pre-existing failures unchanged)
