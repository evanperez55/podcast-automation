---
phase: 18
slug: demo-packaging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 18 — Validation Strategy

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
| 18-01-01 | 01 | 1 | DEMO-02 | unit | `uv run pytest tests/test_audio_processor.py -x -k "raw_snapshot"` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | DEMO-01 | unit | `uv run pytest tests/test_demo_packager.py -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 2 | DEMO-03 | unit | `uv run pytest tests/test_demo_packager.py -x -k "demo_md"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_demo_packager.py` — new test file for DemoPackager module
- [ ] `tests/test_audio_processor.py` — add raw snapshot tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Demo folder looks presentable | DEMO-01 | Subjective visual quality | Open demo/<client>/ep_N/ folder, verify artifacts organized and HTML renders |
| Before/after audio audible difference | DEMO-02 | Requires human listening | Play both clips, verify censored/normalized version sounds cleaner |
| DEMO.md narrative reads well | DEMO-03 | Subjective writing quality | Read DEMO.md, verify it makes sense to a non-technical prospect |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
