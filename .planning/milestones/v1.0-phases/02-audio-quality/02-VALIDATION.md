---
phase: 2
slug: audio-quality
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_audio_processor.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_audio_processor.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | AUDIO-01 | unit | `pytest tests/test_audio_processor.py -x -k "duck"` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | AUDIO-02 | unit | `pytest tests/test_audio_processor.py -x -k "lufs or normalize"` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | AUDIO-03 | unit | `pytest tests/test_audio_processor.py -x -k "metadata or log"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_audio_processor.py` — new TestAudioDucking class with ducking tests
- [ ] `tests/test_audio_processor.py` — rewritten TestNormalizeAudio for subprocess-based LUFS

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ducked audio sounds smooth, not jarring | AUDIO-01 | Subjective audio quality | Process a test episode, listen to censored segments — should hear gradual volume dip, not abrupt cut |
| Episode measures -15 to -17 LUFS | AUDIO-02 | Requires audio analysis tool | Run processed MP3 through ffmpeg loudnorm measure or online LUFS meter |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
