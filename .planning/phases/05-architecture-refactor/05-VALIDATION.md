---
phase: 5
slug: architecture-refactor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (current project standard) |
| **Config file** | none (pytest auto-discovers tests/) |
| **Quick run command** | `pytest tests/test_pipeline_refactor.py tests/test_pipeline_checkpoint_keys.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pipeline_refactor.py tests/test_pipeline_checkpoint_keys.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DEBT-01 | unit | `pytest tests/test_pipeline_refactor.py::test_main_under_150_lines -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | DEBT-01 | unit | `pytest tests/test_pipeline_refactor.py::test_step_modules_importable -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | DEBT-01 | unit | `pytest tests/test_pipeline_refactor.py::test_pipeline_context_fields -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | DEBT-01 | unit | `pytest tests/test_pipeline_steps_audio.py -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | DEBT-01 | unit | `pytest tests/test_pipeline_steps_distribute.py -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | DEBT-05 | unit | `pytest tests/test_pipeline_refactor.py::test_run_distribute_only_exists -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | DEBT-05 | unit | `pytest tests/test_pipeline_steps_distribute.py::test_run_distribute_only -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 2 | DEBT-01+05 | regression | `pytest tests/test_pipeline_checkpoint_keys.py -x` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 2 | Both | smoke | `pytest tests/test_pipeline_smoke.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pipeline_refactor.py` — structural assertions (line count, importability, PipelineContext fields, run_distribute_only)
- [ ] `tests/test_pipeline_checkpoint_keys.py` — checkpoint key regression test
- [ ] `tests/test_pipeline_steps_audio.py` — audio step function stubs
- [ ] `tests/test_pipeline_steps_distribute.py` — distribute step function stubs
- [ ] `tests/test_pipeline_smoke.py` — end-to-end smoke test (mock all I/O)

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `python main.py ep29 --auto-approve` produces identical output | DEBT-01 | Requires real audio files and API credentials | Run against a real episode in dry-run mode and compare output structure |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
