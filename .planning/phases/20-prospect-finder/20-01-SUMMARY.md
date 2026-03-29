---
phase: 20-prospect-finder
plan: "01"
subsystem: prospect-finder
tags: [itunes-api, rss-parsing, yaml-scaffolding, outreach-tracker, tdd]
dependency_graph:
  requires: [outreach_tracker.py, client_config.py, clients/example-client.yaml]
  provides: [prospect_finder.py, ProspectFinder, GENRE_IDS, GENRE_DEFAULTS]
  affects: [outreach_tracker.py (registers prospects), clients/*.yaml (scaffolds)]
tech_stack:
  added: []
  patterns:
    - "iTunes Search API via requests.get with client-side episode count filtering"
    - "feedparser RSS contact extraction with itunes_owner -> itunes_email -> author_detail fallback chain"
    - "init_client() + yaml.safe_load/dump merge pattern for YAML scaffolding"
key_files:
  created:
    - prospect_finder.py
    - tests/test_prospect_finder.py
  modified: []
decisions:
  - "Used getattr(entry, 'published_parsed', None) instead of entry.get() — feedparser entries support attribute access; .get() on Mock objects returns new Mock not the attribute value"
  - "GENRE_NAME_MAP uses both spaced and hyphenated variants (e.g. 'true crime' and 'true-crime') for robustness"
  - "bozo feed warning logs but continues parsing — partial feed data is better than empty dict for bozo=True feeds that are still parseable"
metrics:
  duration_seconds: 343
  completed_date: "2026-03-28"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
  tests_added: 50
  tests_total: 727
---

# Phase 20 Plan 01: ProspectFinder — iTunes Search, RSS Enrichment, YAML Scaffolding Summary

**One-liner:** ProspectFinder class with iTunes Search API filtering by genre and episode count, RSS contact extraction with itunes_owner/itunes_email/author_detail fallback chain, and YAML scaffolding via init_client() + genre defaults merge into OutreachTracker.

## What Was Built

`prospect_finder.py` — A standalone module following the project's `self.enabled` pattern that wraps three operations:

1. **DISC-01 — iTunes Search:** `search()` calls `requests.get` to `https://itunes.apple.com/search` with `media=podcast`, optional `genreId`, and client-side `trackCount` filtering. Returns at most `limit` results. Returns empty list on any API error.

2. **DISC-02 — RSS Enrichment:** `enrich_from_rss()` parses a feed URL via feedparser. Extracts email with priority chain (itunes_owner.email -> itunes_email -> author_detail.email), regex-scans description for Twitter/Instagram links, returns last_pub_date as ISO string and episode_count from len(feed.entries). Handles bozo feeds by logging warning and continuing.

3. **DISC-03 — Save Prospect:** `save_prospect()` calls `init_client(slug)` if YAML missing, loads the YAML, merges `prospect:` block + `episode_source=rss` + `rss_source.feed_url` + optional genre content defaults (voice_persona, compliance_style, rss.categories from GENRE_DEFAULTS), writes back, then registers in OutreachTracker via `add_prospect()` at `"identified"` status.

**Module constants:**
- `GENRE_IDS`: comedy=1303, true-crime=1488, business=1321, technology=1318, society=1324
- `GENRE_DEFAULTS`: comedy (lenient), true-crime (strict), business (standard) — each with voice_persona, compliance_style, categories
- `_genre_key_from_name()`: maps iTunes primaryGenreName to GENRE_DEFAULTS key

`tests/test_prospect_finder.py` — 50 unit tests across 6 test classes. All external dependencies mocked (requests, feedparser, init_client, OutreachTracker). Real YAML round-trip tests use `tmp_path`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test create_yaml side effect wrote to wrong path**
- **Found during:** GREEN phase — test_save_prospect_calls_init_client_when_yaml_missing failed
- **Issue:** Test's `create_yaml` lambda wrote to `tmp_path/{name}.yaml` but `save_prospect()` reads from `Config.BASE_DIR / "clients" / {name}.yaml` (i.e. `tmp_path/clients/{name}.yaml`)
- **Fix:** Updated `create_yaml` to create `clients/` subdirectory and write to correct path
- **Files modified:** tests/test_prospect_finder.py
- **Commit:** 73c9dfd

**2. [Rule 1 - Bug] Used .get() on feedparser entry for published_parsed**
- **Found during:** GREEN phase — test_enrich_returns_last_pub_date_iso failed
- **Issue:** `entry.get("published_parsed")` on a Mock returns a new Mock (truthy) rather than the attribute value. feedparser entries support attribute access, not dict .get().
- **Fix:** Changed to `getattr(entry, "published_parsed", None)` which works for both real feedparser entries and Mock objects
- **Files modified:** prospect_finder.py
- **Commit:** 73c9dfd

## Tests

| Class | Tests | Coverage |
|-------|-------|----------|
| TestModuleConstants | 9 | GENRE_IDS and GENRE_DEFAULTS values |
| TestProspectFinderInit | 1 | enabled=True default |
| TestProspectFinderSearch | 10 | API calls, filtering, limits, error handling |
| TestEnrichFromRss | 10 | Email chain, social links, dates, bozo, failures |
| TestGenreKeyFromName | 5 | Genre name mappings including edge cases |
| TestSaveProspect | 10 | YAML creation, prospect block, genre defaults, tracker, idempotency |

**Total:** 50 new tests. Full suite: 727 passed (was 570 before this milestone).

## Commits

- `722bbee` — test(20-01): add failing tests for ProspectFinder (RED)
- `73c9dfd` — feat(20-01): implement ProspectFinder — iTunes search, RSS enrichment, YAML scaffolding (GREEN)

## Self-Check: PASSED

- prospect_finder.py: FOUND
- tests/test_prospect_finder.py: FOUND
- commit 722bbee: FOUND
- commit 73c9dfd: FOUND
