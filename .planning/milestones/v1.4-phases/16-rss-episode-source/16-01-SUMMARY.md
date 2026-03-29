---
phase: 16-rss-episode-source
plan: "01"
subsystem: api
tags: [feedparser, rss, podcast, requests, tqdm, streaming-download]

# Dependency graph
requires: []
provides:
  - RSSEpisodeFetcher class with fetch_latest(), fetch_episode(index), download_audio()
  - EpisodeMeta dataclass (title, audio_url, pub_date, episode_number, duration_seconds, description)
  - extract_episode_number_from_filename() module-level helper function
  - _parse_itunes_duration() helper handling HH:MM:SS, MM:SS, raw seconds
  - feedparser>=6.0.12 dependency in pyproject.toml
affects:
  - 16-rss-episode-source (remaining plans that wire fetcher into pipeline)
  - pipeline/steps/ingest.py (will import RSSEpisodeFetcher)
  - dropbox_handler.py (extract_episode_number extracted as shared function)

# Tech tracking
tech-stack:
  added:
    - feedparser>=6.0.12 (RSS/Atom feed parsing)
    - sgmllib3k==1.0.0 (feedparser transitive dep)
  patterns:
    - TDD — failing tests committed first, then implementation to green
    - Module-level helper function extracted from class method for cross-module reuse
    - self.enabled=True pattern for credential-free modules

key-files:
  created:
    - rss_episode_fetcher.py
    - tests/test_rss_episode_fetcher.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "extract_episode_number_from_filename is a module-level function (not a class method) so both RSS and local-file ingest paths can share it without importing DropboxHandler"
  - "iTunes episode tag takes priority over filename-pattern extraction; filename fallback only when itunes_episode absent or non-numeric"
  - "Entries sorted by published_parsed descending before indexing — handles oldest-first feeds without caller knowing"
  - "Config import removed — RSSEpisodeFetcher needs no config attributes, keeping module lightweight"

patterns-established:
  - "extract_episode_number_from_filename: standalone module-level function pattern for shared regex logic"
  - "_parse_itunes_duration: private module-level helper (not a method) for pure-function converters"

requirements-completed:
  - SRC-01

# Metrics
duration: 4min
completed: 2026-03-28
---

# Phase 16 Plan 01: RSS Episode Fetcher Summary

**feedparser-based RSS episode fetcher with streaming audio download, iTunes tag parsing, and shared episode-number extraction function**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-28T18:24:27Z
- **Completed:** 2026-03-28T18:28:22Z
- **Tasks:** 1 (TDD — 2 commits: test then feat)
- **Files modified:** 4 (rss_episode_fetcher.py, tests/test_rss_episode_fetcher.py, pyproject.toml, uv.lock)

## Accomplishments

- Built `RSSEpisodeFetcher` with `fetch_latest()`, `fetch_episode(index)`, and `download_audio()` methods
- `EpisodeMeta` dataclass surfaces all episode metadata needed by the pipeline (title, URL, number, duration, pub_date, description)
- `extract_episode_number_from_filename()` extracted as a module-level function — reuses DropboxHandler's regex patterns but is importable independently
- 30 tests cover all happy paths, error cases, iTunes duration formats, and edge cases (oldest-first feeds, query-string URLs)
- Full test suite grew from 579 to 609 tests, all green

## Task Commits

1. **Task 1 (RED): Add failing tests** — `e24f811` (test)
2. **Task 1 (GREEN): Implement RSSEpisodeFetcher** — `13363af` (feat)

## Files Created/Modified

- `rss_episode_fetcher.py` — RSSEpisodeFetcher, EpisodeMeta, extract_episode_number_from_filename, _parse_itunes_duration
- `tests/test_rss_episode_fetcher.py` — 30 unit tests across 6 test classes
- `pyproject.toml` — feedparser>=6.0.12 added to dependencies
- `uv.lock` — lockfile updated with feedparser + sgmllib3k

## Decisions Made

- `extract_episode_number_from_filename` is a module-level function so future pipeline steps can import it without coupling to DropboxHandler.
- `Config` import removed — the module requires no env-var configuration, keeping it lightweight and independently testable.
- Entries sorted descending by `published_parsed` before indexing so `index=0` always means "newest" regardless of feed order.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Pre-commit hook caught unused `time` import and unformatted file on first test commit attempt. Fixed before commit.
- Pre-commit hook caught unused `Config` import during implementation commit. Import removed entirely since no Config attributes are used — correct behavior.

## Next Phase Readiness

- `RSSEpisodeFetcher` is independently importable and tested — ready for wiring into pipeline ingest step.
- `extract_episode_number_from_filename` is available for `dropbox_handler.py` to delegate to (de-duplication can happen in a later plan or naturally).
- No blockers.

---
*Phase: 16-rss-episode-source*
*Completed: 2026-03-28*
