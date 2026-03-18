---
phase: 07-episode-webpages
plan: 02
subsystem: distribution
tags: [github-pages, pygithub, sitemap, pipeline, episode-webpage]

# Dependency graph
requires:
  - phase: 07-01
    provides: EpisodeWebpageGenerator with generate_html() and generate_sitemap() methods
provides:
  - deploy() and _github_upsert() methods on EpisodeWebpageGenerator for GitHub Pages publishing
  - generate_and_deploy() orchestration method returning public episode URL
  - Step 8.6 in distribute.py — episode webpage deployment after blog post, before search index
  - webpage_generator component registered in pipeline runner (_init_components + run_distribute_only)
affects: [phase-08-compliance, pipeline-runner, distribute-step]

# Tech tracking
tech-stack:
  added: [PyGithub (github package) for GitHub Pages file upsert]
  patterns:
    - components.get('webpage_generator') pattern in distribute.py matching blog_generator pattern
    - Try get_contents/update_file, except create_file for GitHub Pages upsert
    - Graceful skip when GITHUB_TOKEN or GITHUB_PAGES_REPO env vars are absent

key-files:
  created: []
  modified:
    - episode_webpage_generator.py (added deploy, _github_upsert, generate_and_deploy methods)
    - pipeline/runner.py (registered webpage_generator in _init_components and run_distribute_only)
    - pipeline/steps/distribute.py (added Step 8.6 between blog post and search index)
    - tests/test_episode_webpage_generator.py (added TestDeploy class with 6 tests)

key-decisions:
  - "PyGithub upsert pattern: get_contents to retrieve SHA then update_file; on GithubException (404) fall back to create_file"
  - "deploy() returns None gracefully on missing GITHUB_TOKEN or GITHUB_PAGES_REPO — no exception raised"
  - "Sitemap deployed alongside HTML in same deploy() call to keep repo in consistent state"

patterns-established:
  - "GitHub Pages upsert: try get_contents(path, ref=branch) for SHA, except GithubException: create_file()"
  - "Step 8.6 follows identical guard pattern to Step 8.5 (blog_generator): components.get + enabled check + try/except warning"

requirements-completed: [WEB-06]

# Metrics
duration: 10min
completed: 2026-03-18
---

# Phase 7 Plan 02: Episode Webpage GitHub Pages Deployment Summary

**EpisodeWebpageGenerator wired into pipeline as Step 8.6 with PyGithub upsert deploying HTML + sitemap.xml to GitHub Pages, gracefully skipping when credentials are absent**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-18T21:30:00Z
- **Completed:** 2026-03-18T21:43:19Z
- **Tasks:** 2 (1 code task + 1 human-verify checkpoint)
- **Files modified:** 4

## Accomplishments
- Added `deploy()`, `_github_upsert()`, and `generate_and_deploy()` to `EpisodeWebpageGenerator`
- Wired as Step 8.6 in `pipeline/steps/distribute.py` between blog post (8.5) and search index (9)
- Registered `webpage_generator` component in `pipeline/runner.py` (_init_components dry_run + normal paths, and run_distribute_only)
- 6 new deploy tests in `TestDeploy` class covering skip-on-missing-creds, upsert/create branching, and sitemap deployment
- Human-verify checkpoint approved: Step 8.6 visible in dry-run, HTML generation produces valid JSON-LD and chapter nav

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GitHub Pages deployment and wire EpisodeWebpageGenerator into pipeline** - `68c10c5` (feat)
2. **Task 2: Human-verify checkpoint** - approved (no code commit — verification only)

## Files Created/Modified
- `episode_webpage_generator.py` - Added deploy(), _github_upsert(), generate_and_deploy() methods
- `pipeline/runner.py` - Registered webpage_generator component in all init paths
- `pipeline/steps/distribute.py` - Added Step 8.6 between blog post and search index
- `tests/test_episode_webpage_generator.py` - Added TestDeploy class with 6 tests

## Decisions Made
- PyGithub upsert pattern: `get_contents(path, ref=branch)` to get SHA, then `update_file()`; on `GithubException` (404 not found), fall back to `create_file()`.
- `deploy()` returns `None` on missing `GITHUB_TOKEN` or `GITHUB_PAGES_REPO` — no crash, warning logged.
- Sitemap deployed alongside HTML in same `deploy()` call to keep the Pages repo in a consistent state.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
**External services require manual configuration.** The following environment variables must be set before GitHub Pages deployment will execute:
- `GITHUB_TOKEN` — GitHub Personal Access Token with `repo` scope for the Pages repository
- `GITHUB_PAGES_REPO` — Owner/repo name of the GitHub Pages repository (e.g., `fakeproblemspodcast/website`)
- `SITE_BASE_URL` — Your GitHub Pages URL (e.g., `https://fakeproblemspodcast.github.io/website`)

When these are absent, Step 8.6 logs a warning and skips without crashing the pipeline.

## Next Phase Readiness
- Phase 7 complete: EpisodeWebpageGenerator fully implemented (Plan 01) and wired into pipeline (Plan 02)
- WEB-01 through WEB-06 requirements fulfilled
- Phase 8 (Content Compliance) can proceed — no shared code dependencies with Phase 7

---
*Phase: 07-episode-webpages*
*Completed: 2026-03-18*
