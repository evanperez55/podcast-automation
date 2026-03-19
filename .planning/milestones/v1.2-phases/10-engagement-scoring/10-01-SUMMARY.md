---
phase: 10-engagement-scoring
plan: "01"
subsystem: analytics
tags: [scipy, spearman, engagement-scoring, topic-scoring, correlation]

# Dependency graph
requires:
  - phase: 09-analytics-infrastructure
    provides: engagement_history.json records written by analytics.py

provides:
  - EngagementScorer class with Spearman category ranking (engagement_scorer.py)
  - Confidence gate: returns insufficient_data below 15 episodes
  - Day-of-week per-platform engagement averages
  - Comedy-protected category floor (correlation >= 0.0)
  - topic_scorer bug fix: uses actual episode_number, not loop index

affects:
  - 10-02 (CONTENT-02 wiring — will consume EngagementScorer.get_category_rankings())
  - Phase 11 (smart scheduling will use day-of-week analysis)

# Tech tracking
tech-stack:
  added: [scipy.stats.spearmanr]
  patterns:
    - TDD (RED test → GREEN implementation) for all new modules
    - EngagementScorer accepts optional history_path arg for testability (no singleton)
    - Constant-presence detection before calling spearmanr (avoids NaN/ConstantInputWarning paths)

key-files:
  created:
    - engagement_scorer.py
    - tests/test_engagement_scorer.py
    - tests/test_topic_scorer.py
  modified:
    - topic_scorer.py

key-decisions:
  - "EngagementScorer takes optional history_path constructor arg — enables clean unit testing without mocking Config"
  - "Constant category presence returns skipped=no_variance entry (not silently dropped) so callers can distinguish no-data from no-signal"
  - "topic_scorer engagement bonus skipped entirely when episode_number is absent — scraped future topics cannot accidentally inherit index-based bonuses"
  - "Comedy constraint applied post-correlation, pre-sort — preserves natural ordering while enforcing editorial floor"

patterns-established:
  - "Pattern 1: Scoring modules accept optional file path in constructor for testability without Config mocking"
  - "Pattern 2: Statistical skip guard — check variance before calling scipy to avoid NaN-producing correlation"

requirements-completed: [ENGAGE-01, ENGAGE-02, ENGAGE-03, ENGAGE-04]

# Metrics
duration: 30min
completed: 2026-03-19
---

# Phase 10 Plan 01: EngagementScorer Summary

**Spearman correlation ranker for topic categories with comedy-protected floor, day-of-week analysis, and 15-episode confidence gate — plus topic_scorer episode-number bug fix**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-19T01:05:00Z
- **Completed:** 2026-03-19T01:33:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Built `EngagementScorer` class (~175 lines) with full Spearman correlation pipeline
- Confidence gate gates all output at 15 episodes; returns structured insufficient_data response below threshold
- Day-of-week analysis produces per-platform (YouTube/Twitter) weekday averages
- Comedy constraint clamps shocking_news and absurd_hypothetical correlation to >= 0.0 with `comedy_protected=True` flag
- Fixed topic_scorer bug where loop index `i+1` was passed to `get_engagement_bonus()` instead of `topic["episode_number"]`
- 13 new tests (11 engagement scorer + 2 regression) — all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EngagementScorer with tests** - `79f046f` (feat)
2. **Task 2: Fix topic_scorer episode number bug + regression test** - `e0ca2c2` (fix)

## Files Created/Modified

- `engagement_scorer.py` — EngagementScorer class with get_category_rankings(), _correlate_category(), _analyze_day_of_week(), _apply_comedy_constraint()
- `tests/test_engagement_scorer.py` — 11 unit tests across TestConfidenceGate, TestGetCategoryRankings, TestDayOfWeek, TestComedyConstraint
- `topic_scorer.py` — Bug fix: `actual_ep = topic.get("episode_number")` replaces `i + 1`; bonus skipped when episode_number absent
- `tests/test_topic_scorer.py` — 2 regression tests confirming episode_number used correctly

## Decisions Made

- `EngagementScorer` accepts optional `history_path` constructor arg for testability — avoids need to mock Config in tests
- Constant category presence (all episodes have the category) returns `skipped=no_variance` entry rather than being silently dropped, so downstream callers can distinguish "no data" from "no signal"
- Comedy constraint clamping applied after correlation, before sort — preserves natural ordering while enforcing editorial floor
- Engagement bonus in topic_scorer now skipped entirely when `episode_number` absent — scraped future topics cannot accidentally inherit bonuses

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `test_uses_spearman` initially failed because all 15 mock records had the same topic (constant presence), so `spearmanr` was never called. Fixed by using alternating topic patterns in that test's fixture data.
- `patch("engagement_scorer.math")` required `math` to be a module-level import (not inline import inside function). Moved `import math` to module top.

## Next Phase Readiness

- `EngagementScorer.get_category_rankings()` is ready for Plan 02 (CONTENT-02 wiring into topic_scorer/topic_curator pipeline)
- Day-of-week analysis data is available for Phase 11 smart scheduling
- No blockers

## Self-Check: PASSED

- `engagement_scorer.py` — FOUND
- `tests/test_engagement_scorer.py` — FOUND
- `tests/test_topic_scorer.py` — FOUND
- commit `79f046f` — FOUND
- commit `e0ca2c2` — FOUND

---
*Phase: 10-engagement-scoring*
*Completed: 2026-03-19*
