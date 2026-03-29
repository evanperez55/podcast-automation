---
phase: 19
slug: outreach-tracker
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_outreach_tracker.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_outreach_tracker.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | TRACK-01, TRACK-02 | unit | `uv run pytest tests/test_outreach_tracker.py -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | TRACK-01 | unit | `uv run pytest tests/test_outreach_tracker.py -x && uv run ruff check main.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_outreach_tracker.py` — new test file for OutreachTracker module

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI output formatting | TRACK-02 | Table layout is visual | Run `uv run main.py outreach list`, verify table renders cleanly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
