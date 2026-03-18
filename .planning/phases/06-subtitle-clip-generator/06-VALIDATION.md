---
phase: 6
slug: subtitle-clip-generator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, 333 tests passing) |
| **Config file** | none — pytest discovers tests/ directory |
| **Quick run command** | `pytest tests/test_subtitle_clip_generator.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_subtitle_clip_generator.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CLIP-01 | unit | `pytest tests/test_subtitle_clip_generator.py::TestCreateSubtitleClips -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | CLIP-01 | unit | `pytest tests/test_subtitle_clip_generator.py::TestBuildFfmpegCommand -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | CLIP-02 | unit | `pytest tests/test_subtitle_clip_generator.py::TestGenerateAssFile -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | CLIP-03 | unit | `pytest tests/test_subtitle_clip_generator.py::TestNormalizeWordTimestamps -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | CLIP-03 | unit | `pytest tests/test_subtitle_clip_generator.py::TestEscapeFilterPath -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | CLIP-04 | integration | `pytest tests/test_subtitle_clip_generator.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_subtitle_clip_generator.py` — covers CLIP-01 through CLIP-04 unit tests
- [ ] `assets/fonts/Anton-Regular.ttf` — font file for libass (download from Google Fonts)

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual caption quality on 9:16 video | CLIP-01 | FFmpeg burn-in results vary by font/size/resolution | Render a test clip and visually inspect captions are bold, readable, centered |
| Accent highlight is visible and distinct | CLIP-02 | Color perception is subjective | Watch a clip and confirm the active word pops visually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
