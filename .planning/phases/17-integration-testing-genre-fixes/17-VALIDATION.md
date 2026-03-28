---
phase: 17
slug: integration-testing-genre-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_content_editor.py tests/test_client_config.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run relevant test file with `-x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | TEST-03 | unit | `uv run pytest tests/test_content_editor.py -x -k "clip_selection"` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | TEST-04 | unit | `uv run pytest tests/test_content_editor.py -x -k "compliance"` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | TEST-01, TEST-02 | integration | Manual: process real episodes | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_editor.py` — add clip_selection_mode tests (content vs energy behavior)
- [ ] `tests/test_content_editor.py` — add compliance_style tests (strict vs permissive behavior)
- [ ] `tests/test_client_config.py` — add tests for new YAML mappings (clip_selection_mode, compliance_style)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| True crime episode tone | TEST-01 | GPT-4o output quality is subjective | Process episode, review show notes + blog for comedy phrasing |
| Business episode tone | TEST-02 | GPT-4o output quality is subjective | Process episode, review show notes + blog for professional tone |
| Clip selection quality | TEST-03 | Requires real audio + subjective review | Listen to selected clips, verify substantive content not just loud moments |
| Compliance sensitivity | TEST-04 | Real content judgment | Review compliance output for genre-appropriate flagging |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
