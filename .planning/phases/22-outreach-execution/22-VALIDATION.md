---
phase: 22
slug: outreach-execution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_demo_packager.py -x` |
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
| 22-01-01 | 01 | 1 | DEMO-04 | unit | `uv run pytest tests/test_demo_packager.py -x -k "consent"` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 2 | DEMO-04 | integration | Manual: real prospect outreach | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_demo_packager.py` — add consent gate tests to existing file

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real prospect receives pitch | DEMO-04 | Requires human outreach | Find prospect, get consent, process episode, send pitch |
| Tracker reflects interaction | DEMO-04 | Requires real data | Check `outreach list` shows the prospect at correct status |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
