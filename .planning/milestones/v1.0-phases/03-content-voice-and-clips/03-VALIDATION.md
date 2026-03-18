---
phase: 3
slug: content-voice-and-clips
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_content_editor.py tests/test_blog_generator.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_content_editor.py tests/test_blog_generator.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | VOICE-01 | unit | `pytest tests/test_content_editor.py -x -k "voice or persona"` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | VOICE-02 | unit | `pytest tests/test_audio_clip_scorer.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | VOICE-03 | unit | `pytest tests/test_content_editor.py -x -k "hook or caption"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content_editor.py` — new tests for persona system message and hook caption style
- [ ] `tests/test_audio_clip_scorer.py` — new test file for AudioClipScorer
- [ ] `tests/test_blog_generator.py` — new tests for blog voice persona

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generated text reads as edgy comedy | VOICE-01 | Subjective tone assessment | Run pipeline on a test episode, read generated titles/descriptions/social posts — should sound like the hosts wrote them, not a marketing team |
| At least one clip is a punchline | VOICE-02 | Requires listening | Listen to selected clips from a test run — at least one should be an obvious funny moment |
| Hook captions match show humor | VOICE-03 | Subjective style | Review generated hook captions — should be provocative/funny, not neutral summaries |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
