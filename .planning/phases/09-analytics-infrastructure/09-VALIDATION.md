---
phase: 9
slug: analytics-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (auto-discovery) |
| **Quick run command** | `pytest tests/test_analytics.py tests/test_twitter_uploader.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_analytics.py tests/test_twitter_uploader.py tests/test_instagram_uploader.py tests/test_tiktok_uploader.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | ANLYT-01 | unit | `pytest tests/test_distribute.py -k "platform_ids" -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | ANLYT-01 | unit | `pytest tests/test_analytics.py -k "video_id" -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | ANLYT-02 | unit | `pytest tests/test_analytics.py -k "impression" -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | ANLYT-02 | unit | `pytest tests/test_analytics.py -k "null_impression" -x` | ❌ W0 | ⬜ pending |
| 09-01-05 | 01 | 1 | ANLYT-03 | unit | `pytest tests/test_analytics.py -k "engagement_history" -x` | ❌ W0 | ⬜ pending |
| 09-01-06 | 01 | 1 | ANLYT-03 | unit | `pytest tests/test_analytics.py -k "upsert" -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | ANLYT-04 | unit | `pytest tests/test_instagram_uploader.py -k "functional" -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | ANLYT-04 | unit | `pytest tests/test_tiktok_uploader.py -k "functional" -x` | ❌ W0 | ⬜ pending |
| 09-02-03 | 02 | 2 | CONTENT-01 | unit | `pytest tests/test_twitter_uploader.py -k "hashtag" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test methods in `tests/test_analytics.py` — ANLYT-01 video_id, ANLYT-02 impressions, ANLYT-03 engagement history
- [ ] New test methods in `tests/test_twitter_uploader.py` — CONTENT-01 hashtag injection
- [ ] New test methods in `tests/test_instagram_uploader.py` — ANLYT-04 functional flag
- [ ] New test methods in `tests/test_tiktok_uploader.py` — ANLYT-04 functional flag
- [ ] Tests for distribute.py platform_ids capture

*Existing test infrastructure covers all needs. No new fixtures required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| YouTube API quota not exhausted during `analytics all` | ANLYT-01 | Requires real API calls | Run `python main.py analytics all` and verify no quota errors |
| Backfill command populates IDs for existing episodes | ANLYT-01 | Requires real YouTube search | Run `python main.py backfill-ids` on a few episodes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
