---
phase: 07-episode-webpages
plan: "01"
subsystem: content-generation
tags: [seo, html, jinja2, json-ld, sitemap, yake, episode-pages]
dependency_graph:
  requires: []
  provides: [episode_webpage_generator.EpisodeWebpageGenerator]
  affects: [pipeline/steps]
tech_stack:
  added: [yake==0.7.3, PyGithub==2.8.1]
  patterns: [jinja2-autoescape, xml-etree-sitemap, self-enabled-env-pattern]
key_files:
  created:
    - episode_webpage_generator.py
    - templates/episode.html.j2
    - tests/test_episode_webpage_generator.py
  modified:
    - requirements.txt
decisions:
  - "Jinja2 autoescape=True used for XSS protection — apostrophes become &#39; in HTML output (test assertions updated accordingly)"
  - "YAKE keyword extraction uses show_notes or episode_summary, NOT raw transcript — avoids noisy filler words per research pitfall #3"
  - "ET.register_namespace ensures sitemap XML uses clean default namespace prefix"
metrics:
  duration: 15min
  completed_date: "2026-03-18"
  tasks_completed: 1
  files_created: 3
  files_modified: 1
---

# Phase 7 Plan 1: EpisodeWebpageGenerator Core Module Summary

SEO-optimized HTML episode page generator using Jinja2 templates, JSON-LD PodcastEpisode structured data, YAKE keyword extraction, and XML sitemap merging.

## What Was Built

### episode_webpage_generator.py (205 lines)

`EpisodeWebpageGenerator` class with:
- `self.enabled` pattern gated by `PAGES_ENABLED` env var
- `generate_html(episode_number, analysis, transcript_data, audio_url, thumbnail_url)` — renders Jinja2 template with full transcript, JSON-LD, OG/Twitter meta tags, chapter nav
- `extract_keywords(text, n=10)` — YAKE extraction from show_notes/summary text; returns `[]` on empty or error
- `generate_sitemap(existing_xml, new_url)` — ET-based sitemap XML merger; no duplicates
- `_build_episode_url(episode_number)` — constructs `{SITE_BASE_URL}/episodes/ep{N}.html`

### templates/episode.html.j2 (86 lines)

Complete Jinja2 template with:
- JSON-LD `PodcastEpisode` structured data with `partOfSeries`
- Open Graph (`og:title`, `og:description`, `og:url`, `og:site_name`) and Twitter Card meta tags
- `meta name="keywords"` from YAKE-extracted keyphrases
- Chapter navigation: `a href="#t-{start_seconds}"` links
- Transcript body: `span id="t-{start_int}"` anchors per segment
- Readable CSS (max-width 800px, highlight on `:target`)

### tests/test_episode_webpage_generator.py (351 lines, 23 tests)

| Class | Tests | Requirement |
|---|---|---|
| TestGenerateHtml | 4 | WEB-01 |
| TestJsonLd | 3 | WEB-02 |
| TestMetaTags | 3 | WEB-03 |
| TestKeywordExtraction | 4 | WEB-03 |
| TestChapterNav | 3 | WEB-04 |
| TestSitemap | 5 | WEB-05 |
| TestBuildEpisodeUrl | 1 | helper |

## Verification Results

```
pytest tests/test_episode_webpage_generator.py -v
23 passed in 0.84s

pytest (full suite)
387 passed, 2 failed (pre-existing analytics + audiogram enabled-defaults)

ruff check episode_webpage_generator.py tests/test_episode_webpage_generator.py
All checks passed!
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion used raw apostrophe in HTML-escaped output**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test `test_transcript_segments_in_html` asserted `"Lobsters don't age like we do."` but Jinja2 `autoescape=True` converts `'` to `&#39;`, so the raw string never appears in HTML
- **Fix:** Updated test assertions to use `&#39;` form for segments with apostrophes; matches actual HTML output and correctly validates the escaping behavior
- **Files modified:** tests/test_episode_webpage_generator.py
- **Commit:** 051cf2a

## Self-Check: PASSED
