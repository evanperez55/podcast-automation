---
phase: 10
slug: engagement-scoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (auto-discovery) |
| **Quick run command** | `pytest tests/test_engagement_scorer.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_engagement_scorer.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | ENGAGE-01 | unit | `pytest tests/test_engagement_scorer.py::TestGetCategoryRankings -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | ENGAGE-02 | unit | `pytest tests/test_engagement_scorer.py::TestDayOfWeek -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | ENGAGE-03 | unit | `pytest tests/test_engagement_scorer.py::TestComedyConstraint -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | ENGAGE-04 | unit | `pytest tests/test_engagement_scorer.py::TestConfidenceGate -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 2 | CONTENT-02 | unit | `pytest tests/test_content_editor.py::TestBuildAnalysisPrompt -x` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 2 | bug fix | unit | `pytest tests/test_topic_scorer.py::TestTopicScorer::test_engagement_bonus_uses_episode_number -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engagement_scorer.py` — new file covering ENGAGE-01 through ENGAGE-04
- [ ] `tests/test_topic_scorer.py` — new file for episode number bug fix regression test
- [ ] New test methods in `tests/test_content_editor.py` — CONTENT-02 engagement context injection

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Category rankings meaningful with real data | ENGAGE-01 | Requires real engagement_history.json | Run scorer on actual analytics data, review rankings |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
