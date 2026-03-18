---
phase: 8
slug: content-compliance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (uses pytest discovery) |
| **Quick run command** | `pytest tests/test_content_compliance_checker.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_content_compliance_checker.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | SAFE-01 | unit | `pytest tests/test_content_compliance_checker.py::TestCheckTranscript -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | SAFE-01 | unit | `pytest tests/test_content_compliance_checker.py::TestDisabled -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | SAFE-02 | unit | `pytest tests/test_content_compliance_checker.py::TestReportStructure -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | SAFE-02 | unit | `pytest tests/test_content_compliance_checker.py::TestSaveReport -x` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | SAFE-03 | unit | `pytest tests/test_content_compliance_checker.py::TestMergeIntoTimestamps -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | SAFE-04 | unit | `pytest tests/test_pipeline_refactor.py::TestComplianceBlock -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | SAFE-04 | unit | `pytest tests/test_pipeline_refactor.py::TestComplianceForce -x` | ❌ W0 | ⬜ pending |
| 08-02-03 | 02 | 2 | SAFE-04 | integration | `pytest tests/test_pipeline_refactor.py::TestForceFlag -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_compliance_checker.py` — stubs for SAFE-01 through SAFE-03
- [ ] Additional test classes in `tests/test_pipeline_refactor.py` — stubs for SAFE-04

*Existing test_pipeline_refactor.py covers runner.py; new test classes added there for SAFE-04.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPT-4o correctly identifies ep29 cancer misinformation | SAFE-01 | Requires real LLM call | Run compliance check on ep29 transcript, verify cancer segment flagged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
