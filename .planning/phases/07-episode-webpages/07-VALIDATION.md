---
phase: 7
slug: episode-webpages
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (auto-discovery) |
| **Quick run command** | `pytest tests/test_episode_webpage_generator.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_episode_webpage_generator.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | WEB-01 | unit | `pytest tests/test_episode_webpage_generator.py::TestGenerateHtml::test_transcript_segments_in_html -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | WEB-01 | unit | `pytest tests/test_episode_webpage_generator.py::TestGenerateHtml::test_html_escaping -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | WEB-02 | unit | `pytest tests/test_episode_webpage_generator.py::TestJsonLd::test_jsonld_type_and_fields -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | WEB-03 | unit | `pytest tests/test_episode_webpage_generator.py::TestMetaTags::test_og_tags_present -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | WEB-03 | unit | `pytest tests/test_episode_webpage_generator.py::TestKeywordExtraction::test_keywords_nonempty -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 1 | WEB-04 | unit | `pytest tests/test_episode_webpage_generator.py::TestChapterNav::test_chapter_anchors -x` | ❌ W0 | ⬜ pending |
| 07-01-07 | 01 | 1 | WEB-05 | unit | `pytest tests/test_episode_webpage_generator.py::TestSitemap::test_sitemap_merges_existing_urls -x` | ❌ W0 | ⬜ pending |
| 07-01-08 | 01 | 1 | WEB-05 | unit | `pytest tests/test_episode_webpage_generator.py::TestSitemap::test_sitemap_xml_valid -x` | ❌ W0 | ⬜ pending |
| 07-01-09 | 01 | 1 | WEB-06 | unit | `pytest tests/test_episode_webpage_generator.py::TestDeploy::test_skip_when_no_token -x` | ❌ W0 | ⬜ pending |
| 07-01-10 | 01 | 1 | WEB-06 | unit | `pytest tests/test_episode_webpage_generator.py::TestDeploy::test_upsert_calls_update_for_existing -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_episode_webpage_generator.py` — stubs for WEB-01 through WEB-06
- [ ] `templates/episode.html.j2` — Jinja2 HTML template (needed for WEB-01, WEB-02, WEB-03, WEB-04)

*Existing infrastructure covers framework and conftest. No conftest.py changes needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Page passes Google Rich Results Test | WEB-02 | Requires external Google tool | Run generated HTML through https://search.google.com/test/rich-results |
| Page is publicly accessible on GitHub Pages | WEB-01 | Requires deployed GitHub Pages site | Navigate to the GitHub Pages URL after deploy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
