---
phase: 16-rss-episode-source
plan: 02
subsystem: pipeline
tags: [rss, episode-source, dropbox, ingest, client-config, config, pipeline]

# Dependency graph
requires:
  - phase: 16-01
    provides: RSSEpisodeFetcher class with fetch_episode, download_audio, extract_episode_number_from_filename

provides:
  - Config.EPISODE_SOURCE, RSS_FEED_URL, RSS_EPISODE_INDEX attributes with env var defaults
  - client YAML episode_source and rss_source field mapping to Config attributes
  - validate-client gates Dropbox check behind episode_source, adds RSS Feed URL check
  - _ping_rss_feed() for --ping support on RSS clients
  - pipeline/runner.py conditionally constructs RSSEpisodeFetcher vs DropboxHandler
  - pipeline/steps/ingest.py three-branch ingest: local-file, rss, dropbox
  - Local-file and dropbox branches use extract_episode_number_from_filename (no Dropbox coupling)

affects: [pipeline, ingest, client-config, runner, rss-ingest]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "episode_source gate: EPISODE_SOURCE env var/config key guards which source module is constructed"
    - "three-branch ingest pattern: local-file | rss | dropbox in run_ingest"
    - "validate-client source-specific checks: episode_source determines which credential block is validated"

key-files:
  created:
    - .planning/phases/16-rss-episode-source/16-02-SUMMARY.md
  modified:
    - config.py
    - client_config.py
    - pipeline/runner.py
    - pipeline/steps/ingest.py
    - clients/example-client.yaml
    - tests/test_client_config.py
    - tests/test_pipeline_refactor.py

key-decisions:
  - "EPISODE_SOURCE defaults to 'dropbox' — backward compatible; existing clients unaffected"
  - "Use 'rss_source' key (not 'rss') to avoid collision with existing RSS output metadata mappings"
  - "extract_episode_number_from_filename replaces DropboxHandler.extract_episode_number in dropbox+local branches"
  - "rss_fetcher key excluded from components when episode_source=dropbox; dropbox key excluded when episode_source=rss"

patterns-established:
  - "episode_source gating: read getattr(Config, 'EPISODE_SOURCE', 'dropbox') before constructing source-specific component"

requirements-completed:
  - SRC-02

# Metrics
duration: 8min
completed: 2026-03-28
---

# Phase 16 Plan 02: Wire RSS Episode Source Summary

**RSS ingest wired into pipeline: DropboxHandler gated behind EPISODE_SOURCE, three-branch ingest.py, client YAML mappings and validate-client RSS support**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T18:50:39Z
- **Completed:** 2026-03-28T18:58:10Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Config gains EPISODE_SOURCE, RSS_FEED_URL, RSS_EPISODE_INDEX attributes gated by env vars
- Client YAML episode_source and rss_source fields map to Config via load_client_config
- validate_client correctly gates Dropbox vs RSS checks by episode_source; _ping_rss_feed added
- pipeline/runner.py constructs RSSEpisodeFetcher instead of DropboxHandler when EPISODE_SOURCE=rss
- pipeline/steps/ingest.py has three clean source branches; local-file and dropbox no longer use Dropbox for episode number extraction
- 19 new tests (12 in test_client_config.py, 8 in test_pipeline_refactor.py); 627 total passing

## Task Commits

1. **Task 1: Config defaults and YAML mapping for episode_source/rss_source** - `e642cef` (feat)
2. **Task 2: Gate DropboxHandler, add RSS ingest branch** - `dedf606` (feat)

## Files Created/Modified

- `config.py` - Added EPISODE_SOURCE, RSS_FEED_URL, RSS_EPISODE_INDEX class attributes
- `client_config.py` - Added YAML-to-Config mappings, RSS_EPISODE_INDEX int coercion, _ping_rss_feed, validate_client RSS branch
- `pipeline/runner.py` - Conditional RSSEpisodeFetcher/DropboxHandler in _init_components and dry_run branch
- `pipeline/steps/ingest.py` - Three-branch ingest: local-file, rss, dropbox; removed Dropbox episode-number dependency
- `clients/example-client.yaml` - Documented episode_source and rss_source fields
- `tests/test_client_config.py` - Added TestEpisodeSourceYAMLMapping, TestValidateClientRSS, TestPingRSSFeed
- `tests/test_pipeline_refactor.py` - Added TestInitComponentsRSS, TestInitComponentsDryRunRSS, TestRunIngestRSS, TestRunIngestLocalNoDropbox, TestRunIngestDropboxPreserved

## Decisions Made

- EPISODE_SOURCE defaults to "dropbox" so all existing clients are unaffected — backward compatible
- "rss_source" chosen (not "rss") to avoid collision with existing RSS output metadata mappings in _YAML_TO_CONFIG
- extract_episode_number_from_filename replaces DropboxHandler.extract_episode_number in all branches — removes Dropbox coupling for a pure utility operation
- When episode_source=rss, "dropbox" key is absent from components dict (not set to None) — prevents accidental KeyError masking on unexpected access

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - both tasks implemented cleanly following the plan's action steps.

## User Setup Required

None - no external service configuration required. RSS clients need RSS_FEED_URL set in their YAML (episode_source: rss, rss_source.feed_url).

## Next Phase Readiness

- SRC-02 complete: pipeline runs without Dropbox credentials when episode_source=rss
- RSSEpisodeFetcher (16-01) + pipeline wiring (16-02) together enable full RSS-based episode ingest
- Phase 16 plan 03 (if any) or next phase can now use RSS clients end-to-end

## Self-Check: PASSED

All files present, all commits verified.

---
*Phase: 16-rss-episode-source*
*Completed: 2026-03-28*
