---
phase: 12
slug: contentcalendar-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (auto-discovery) |
| **Quick run command** | `pytest tests/test_content_calendar.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_content_calendar.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | CAL-01 | unit | `pytest tests/test_content_calendar.py::TestPlanEpisode -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | CAL-02 | unit | `pytest tests/test_content_calendar.py::TestSaveLoad -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | CAL-03 | unit | `pytest tests/test_content_calendar.py::TestGetPendingSlots -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | CAL-03 | unit | `pytest tests/test_content_calendar.py::TestMarkSlot -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | CAL-03 | unit | `pytest tests/test_scheduler.py::TestRunUploadScheduled -x` | ✅ extend | ⬜ pending |
| 12-02-02 | 02 | 2 | CAL-04 | unit | `pytest tests/test_content_calendar.py::TestDryRunDisplay -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_calendar.py` — new file covering CAL-01 through CAL-04
- [ ] Extend `tests/test_scheduler.py` — new class for calendar slot dispatch

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar displays correctly in dry-run output | CAL-04 | Visual formatting check | Run `python main.py ep29 --dry-run`, review calendar table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
