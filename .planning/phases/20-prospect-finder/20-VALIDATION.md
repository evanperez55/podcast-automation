---
phase: 20
slug: prospect-finder
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_prospect_finder.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_prospect_finder.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | DISC-01, DISC-02, DISC-03 | unit | `uv run pytest tests/test_prospect_finder.py -x` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | DISC-01 | unit | `uv run ruff check main.py && uv run pytest -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_prospect_finder.py` — new test file for ProspectFinder module

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| iTunes API returns real results | DISC-01 | Requires network access | Run `uv run main.py find-prospects --genre comedy --min-episodes 20 --max-episodes 200` |
| RSS enrichment finds real contact | DISC-02 | Requires network + real feed | Run enrichment on a known podcast with itunes:email |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
