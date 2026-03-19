# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- ✅ **v1.1 Discoverability & Short-Form** — Phases 6-8 (shipped 2026-03-18)
- 🚧 **v1.2 Engagement & Smart Scheduling** — Phases 9-11 (in progress)

## Phases

<details>
<summary>✅ v1.0 Pipeline Upgrade (Phases 1-5) — SHIPPED 2026-03-18</summary>

- [x] Phase 1: Foundations (3/3 plans) — completed 2026-03-17
- [x] Phase 2: Audio Quality (3/3 plans) — completed 2026-03-17
- [x] Phase 3: Content Voice and Clips (3/3 plans) — completed 2026-03-17
- [x] Phase 4: Chapter Markers (2/2 plans) — completed 2026-03-17
- [x] Phase 5: Architecture Refactor (3/3 plans) — completed 2026-03-18

See: .planning/milestones/v1.0-ROADMAP.md for full details.

</details>

<details>
<summary>✅ v1.1 Discoverability & Short-Form (Phases 6-8) — SHIPPED 2026-03-18</summary>

- [x] Phase 6: Subtitle Clip Generator (2/2 plans) — completed 2026-03-18
- [x] Phase 7: Episode Webpages (2/2 plans) — completed 2026-03-18
- [x] Phase 8: Content Compliance (2/2 plans) — completed 2026-03-18

See: .planning/milestones/v1.1-ROADMAP.md for full details.

</details>

### v1.2 Engagement & Smart Scheduling (In Progress)

**Milestone Goal:** Maximize clip and post engagement through reliable analytics collection, data-driven engagement scoring, and automated smart scheduling — without ever blocking the pipeline when history is sparse.

- [x] **Phase 9: Analytics Infrastructure** — Harden data collection so every future episode contributes clean, quota-safe analytics history (completed 2026-03-19)
- [ ] **Phase 10: Engagement Scoring** — Build the cross-episode scoring model that ranks topics and informs AI content generation with historical performance context
- [ ] **Phase 11: Smart Scheduling** — Wire optimal posting times into the scheduler, gated on data confidence so sparse history falls back to research defaults

## Phase Details

### Phase 9: Analytics Infrastructure
**Goal**: Every episode run produces reliable, quota-safe analytics data that accumulates into a cross-episode engagement history file without leaking credentials or exhausting API quotas
**Depends on**: Phase 8 (v1.1 complete)
**Requirements**: ANLYT-01, ANLYT-02, ANLYT-03, ANLYT-04, CONTENT-01
**Success Criteria** (what must be TRUE):
  1. After a YouTube upload, the video_id is stored in the episode output JSON — no search API call needed to retrieve it later
  2. `python main.py analytics all` runs across all existing episodes and produces an aggregated engagement report without exhausting API quota
  3. Each analytics run appends one entry per platform to `topic_data/engagement_history.json` — the file grows episode by episode without manual intervention
  4. TikTok and Instagram platforms are detected as stubs and skipped in scheduling and analytics — no silent no-ops
  5. Twitter analytics handles missing impression_count (free tier returns 0) by treating it as null — engagement score formula is not biased by zero impressions
  6. Twitter posts include 1-2 relevant hashtags auto-injected from a curated config list — no data history required
**Plans:** 3/3 plans complete

Plans:
- [ ] 09-01-PLAN.md — Core analytics hardening: platform ID capture, engagement history, impression null guard
- [ ] 09-02-PLAN.md — Stub uploader detection (.functional flags) and Twitter hashtag injection
- [ ] 09-03-PLAN.md — Backfill-ids CLI command and analytics-to-history wiring

### Phase 10: Engagement Scoring
**Goal**: A scoring model ranks topic categories and informs GPT-4o content generation using accumulated engagement history, with the comedy voice treated as a hard constraint the optimizer cannot override
**Depends on**: Phase 9
**Requirements**: ENGAGE-01, ENGAGE-02, ENGAGE-03, ENGAGE-04, CONTENT-02
**Success Criteria** (what must be TRUE):
  1. `engagement_scorer.py` produces an engagement profile (category rankings, confidence level) from `engagement_history.json` using Pearson/Spearman correlation via scipy
  2. The scorer returns no recommendations when episode history is below the configured minimum threshold (15 episodes) — confidence gating prevents noisy early signal from influencing decisions
  3. The topic_scorer episode number bug is fixed — `get_engagement_bonus()` uses actual episode number, not loop index, verified by a regression test
  4. Comedy voice is a binary constraint in the model — edgy/dark content cannot be scored down by the optimizer; engagement scores are hints for hosts, not autonomous decisions
  5. GPT-4o title and caption generation receives engagement history as context and produces titles/captions optimized for the show's historical performance patterns
**Plans**: TBD

### Phase 11: Smart Scheduling
**Goal**: The scheduler computes optimal posting windows from the show's own engagement history per platform, falling back to research-based defaults when history is sparse, without breaking the existing `python main.py ep29 --auto-approve` workflow
**Depends on**: Phase 10
**Requirements**: SCHED-01, SCHED-02, SCHED-03
**Success Criteria** (what must be TRUE):
  1. `posting_time_optimizer.py` returns an optimal posting datetime per platform when engagement history meets the confidence threshold, or None when below threshold — callers fall through to static delays
  2. Platform-specific scheduling windows are configurable (YouTube and Twitter have different optimal windows) and documented in config.py with research-based defaults
  3. `scheduler.py` accepts computed optimal times from the optimizer via `get_optimal_publish_at()` — the existing fixed-delay config remains the fallback and the pipeline never blocks on missing history
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundations | v1.0 | 3/3 | Complete | 2026-03-17 |
| 2. Audio Quality | v1.0 | 3/3 | Complete | 2026-03-17 |
| 3. Content Voice and Clips | v1.0 | 3/3 | Complete | 2026-03-17 |
| 4. Chapter Markers | v1.0 | 2/2 | Complete | 2026-03-17 |
| 5. Architecture Refactor | v1.0 | 3/3 | Complete | 2026-03-18 |
| 6. Subtitle Clip Generator | v1.1 | 2/2 | Complete | 2026-03-18 |
| 7. Episode Webpages | v1.1 | 2/2 | Complete | 2026-03-18 |
| 8. Content Compliance | v1.1 | 2/2 | Complete | 2026-03-18 |
| 9. Analytics Infrastructure | 3/3 | Complete   | 2026-03-19 | - |
| 10. Engagement Scoring | v1.2 | 0/? | Not started | - |
| 11. Smart Scheduling | v1.2 | 0/? | Not started | - |
