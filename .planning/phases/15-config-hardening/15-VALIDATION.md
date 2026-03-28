---
phase: 15
slug: config-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_client_config.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_client_config.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | CFG-01 | unit | `uv run pytest tests/test_client_config.py::TestLoadClientConfig -x` | Partial | ⬜ pending |
| 15-01-02 | 01 | 1 | CFG-01 | unit | `uv run pytest tests/test_client_config.py::TestLoadClientConfig -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | CFG-02 | unit | `uv run pytest tests/test_client_config.py -x` | Partial | ⬜ pending |
| 15-01-04 | 01 | 1 | CFG-03 | unit | `uv run pytest tests/test_client_config.py::TestValidateClient -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_missing_names_to_remove_raises` (CFG-01)
- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_null_names_to_remove_is_valid` (edge case)
- [ ] `tests/test_client_config.py` — add `TestLoadClientConfig::test_empty_names_to_remove_is_valid` (edge case)
- [ ] `tests/test_client_config.py` — update `test_minimal_config` to include `names_to_remove: []` in MINIMAL_YAML
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_active_podcast_name` (CFG-03)
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_active_names_to_remove` (CFG-03)
- [ ] `tests/test_client_config.py` — add `TestValidateClient::test_validate_prints_voice_persona_or_default` (CFG-03)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Genre YAML voice tone is appropriate | CFG-02 | Subjective quality — voice_persona prompt quality cannot be unit tested | Read generated YAML, verify persona text matches genre conventions |
| `--dry-run` output has no FP references | CFG-01 | Requires pipeline integration with real config activation | Run `uv run main.py --client truecrime --dry-run ep01`, grep output for "Fake Problems", "Evan", "Joey" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
