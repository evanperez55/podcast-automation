---
phase: 16
slug: rss-episode-source
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` (testpaths = ["tests"]) |
| **Quick run command** | `uv run pytest tests/test_rss_episode_fetcher.py tests/test_client_config.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_rss_episode_fetcher.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SRC-01 | unit | `uv run pytest tests/test_rss_episode_fetcher.py -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SRC-01 | unit | `uv run pytest tests/test_rss_episode_fetcher.py -x` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | SRC-02 | unit | `uv run pytest tests/test_client_config.py -x -k rss` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 1 | SRC-02 | unit | `uv run pytest tests/test_rss_episode_fetcher.py tests/test_client_config.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `uv add feedparser` — adds feedparser to pyproject.toml before any import
- [ ] `tests/test_rss_episode_fetcher.py` — new test file covering SRC-01 (fetch, download, error handling)
- [ ] `tests/test_client_config.py` — add RSS-related tests (YAML mapping, validate-client --ping)
- [ ] Add RSS ingest branch tests to relevant pipeline test files — covers SRC-02 runner/ingest changes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RSS download from real feed | SRC-01 | Requires network access to real podcast RSS feed | Run `uv run main.py --client truecrime ep01` with rss_source.feed_url set, verify audio downloads |
| validate-client --ping RSS | SRC-02 | Requires network access | Run `uv run main.py --client truecrime validate-client --ping`, verify RSS feed URL reachability check |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
