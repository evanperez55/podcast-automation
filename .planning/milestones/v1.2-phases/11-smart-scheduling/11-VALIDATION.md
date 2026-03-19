---
phase: 11
slug: smart-scheduling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (auto-discovery) |
| **Quick run command** | `pytest tests/test_posting_time_optimizer.py tests/test_scheduler.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_posting_time_optimizer.py tests/test_scheduler.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | SCHED-01 | unit | `pytest tests/test_posting_time_optimizer.py::TestGetOptimalPublishAt -x` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | SCHED-01 | unit | `pytest tests/test_posting_time_optimizer.py::TestNextOccurrence -x` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | SCHED-02 | unit | `pytest tests/test_posting_time_optimizer.py::TestPlatformHours -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 2 | SCHED-03 | unit | `pytest tests/test_scheduler.py::TestGetOptimalPublishAt -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_posting_time_optimizer.py` — new file covering SCHED-01 and SCHED-02
- [ ] New test class in `tests/test_scheduler.py` — covers SCHED-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Optimal time produces real YouTube publish_at | SCHED-03 | Requires actual YouTube upload | Run pipeline on test episode, verify publish_at in schedule |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
