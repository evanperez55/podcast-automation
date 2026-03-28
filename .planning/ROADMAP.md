# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- ✅ **v1.1 Discoverability & Short-Form** — Phases 6-8 (shipped 2026-03-18)
- ✅ **v1.2 Engagement & Smart Scheduling** — Phases 9-11 (shipped 2026-03-19)
- ✅ **v1.3 Content Calendar** — Phase 12 (shipped 2026-03-19)
- 🚧 **v1.4 Real-World Testing & Sales Readiness** — Phases 15-18 (in progress)

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

<details>
<summary>✅ v1.2 Engagement & Smart Scheduling (Phases 9-11) — SHIPPED 2026-03-19</summary>

- [x] Phase 9: Analytics Infrastructure (3/3 plans) — completed 2026-03-19
- [x] Phase 10: Engagement Scoring (2/2 plans) — completed 2026-03-19
- [x] Phase 11: Smart Scheduling (2/2 plans) — completed 2026-03-19

See: .planning/milestones/v1.2-ROADMAP.md for full details.

</details>

<details>
<summary>✅ v1.3 Content Calendar (Phase 12) — SHIPPED 2026-03-19</summary>

- [x] Phase 12: ContentCalendar Foundation (2/2 plans) — completed 2026-03-19

See: Phase 12 details below.

</details>

### 🚧 v1.4 Real-World Testing & Sales Readiness (In Progress)

**Milestone Goal:** Prove the multi-client pipeline works with real non-Fake-Problems podcasts in different genres, fix what breaks, and package the output as a sales demo for prospective clients.

- [x] **Phase 15: Config Hardening** — Eliminate Fake Problems default leakage; author 2-3 real genre client YAMLs (completed 2026-03-28)
- [x] **Phase 16: RSS Episode Source** — Add RSS ingest path to unblock non-Dropbox clients (completed 2026-03-28)
- [x] **Phase 17: Integration Testing & Genre Fixes** — Process real episodes per genre; fix what breaks (completed 2026-03-28)
- [ ] **Phase 18: Demo Packaging** — Assemble pipeline output into a presentable sales demo per client

## Phase Details

### Phase 12: ContentCalendar Foundation
**Goal**: Users can generate and inspect a per-episode content calendar that spreads clip uploads across the week instead of dumping everything on release day
**Depends on**: Phase 11 (existing scheduler/optimizer infrastructure)
**Requirements**: CAL-01, CAL-02, CAL-03, CAL-04
**Plans**: 2/2 complete

---

### Phase 15: Config Hardening
**Goal**: No Fake Problems defaults can leak into any real client's pipeline output; 2-3 real genre client YAMLs exist and pass validate-client
**Depends on**: Phase 12 (multi-client YAML infrastructure shipped post-v1.3)
**Requirements**: CFG-01, CFG-02, CFG-03
**Success Criteria** (what must be TRUE):
  1. Running `uv run main.py --client truecrime validate-client` prints the active voice persona, names_to_remove, and podcast name — all sourced from the YAML with no Fake Problems values visible
  2. Running `uv run main.py --client truecrime --dry-run ep01` completes without any reference to "Fake Problems", "Evan", or "Joey" in the dry-run output
  3. A client YAML that omits `names_to_remove` causes validate-client to print a clear error, not silently fall back to Fake Problems host names
  4. At least 2 real genre client YAMLs (true crime + business/interview) exist with genre-appropriate voice_persona, blog_voice, and scoring_profile fields populated
**Plans**: 2 plans
Plans:
- [ ] 15-01-PLAN.md — Harden load_client_config validation + active config printout in validate-client
- [ ] 15-02-PLAN.md — Conditional voice examples + real genre client YAMLs

### Phase 16: RSS Episode Source
**Goal**: Users can point the pipeline at a public RSS feed URL to download and process an episode — no Dropbox credentials required
**Depends on**: Phase 15
**Requirements**: SRC-01, SRC-02
**Success Criteria** (what must be TRUE):
  1. Running `uv run main.py --client truecrime ep01` with `episode_source: rss` in the client YAML downloads the audio enclosure from the RSS feed and begins transcription without touching Dropbox
  2. A client with no Dropbox credentials configured completes ingest without raising a ValueError or printing any Dropbox error
  3. `feedparser` resolves the latest episode URL and title from a real public podcast RSS feed (iTunes-tagged)
  4. `uv run main.py --client truecrime validate-client --ping` confirms the RSS feed URL is reachable
**Plans**: 2 plans
Plans:
- [ ] 16-01-PLAN.md — RSSEpisodeFetcher module with feedparser + streaming download + tests
- [ ] 16-02-PLAN.md — Wire RSS into pipeline: conditional Dropbox, ingest branching, client YAML config

### Phase 17: Integration Testing & Genre Fixes
**Goal**: A real true crime episode and a real business/interview episode each run end-to-end through the pipeline producing genre-appropriate output with no Fake Problems contamination
**Depends on**: Phase 16
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):
  1. A real true crime episode processes from RSS download through blog post and social captions with tone matching the genre (no comedy phrasing, no comedy voice examples in show notes)
  2. A real business/interview episode processes from RSS download through blog post and social captions with professional tone appropriate to the genre
  3. The 3 selected clips from an interview episode are the moments with the most substantive insight, not the highest audio energy peaks (flat-energy interview audio does not fool the scorer)
  4. The compliance checker applies genre-appropriate sensitivity — a true crime episode flagged for genuine dangerous content is blocked; a comedy episode with profanity is not blocked
**Plans**: 2 plans
Plans:
- [ ] 17-01-PLAN.md — Genre-aware clip selection + compliance code fixes with TDD tests
- [ ] 17-02-PLAN.md — Update genre YAMLs with RSS + process real episodes (human checkpoint)

### Phase 18: Demo Packaging
**Goal**: Running one command per client produces a self-contained demo folder that a prospect can evaluate in a 30-minute meeting without the pipeline present
**Depends on**: Phase 17
**Requirements**: DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):
  1. Running `uv run main.py --client truecrime package-demo ep01` produces a `demo/truecrime/ep01/` folder containing the processed MP3, captioned clips, thumbnail, show notes, social captions, and a self-contained HTML summary page
  2. The demo folder contains a 60-second before/after audio comparison clip (raw vs. normalized + censored) that demonstrates audio quality improvement without requiring technical explanation
  3. A DEMO.md exists per client in the demo folder stating what was automated, estimated time saved, cost per episode in OpenAI tokens, LUFS before/after, and clip selection rationale
**Plans**: TBD
Plans:
- [ ] TBD

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
| 9. Analytics Infrastructure | v1.2 | 3/3 | Complete | 2026-03-19 |
| 10. Engagement Scoring | v1.2 | 2/2 | Complete | 2026-03-19 |
| 11. Smart Scheduling | v1.2 | 2/2 | Complete | 2026-03-19 |
| 12. ContentCalendar Foundation | v1.3 | 2/2 | Complete | 2026-03-19 |
| 15. Config Hardening | v1.4 | 2/2 | Complete | 2026-03-28 |
| 16. RSS Episode Source | v1.4 | 2/2 | Complete | 2026-03-28 |
| 17. Integration Testing & Genre Fixes | 2/2 | Complete   | 2026-03-28 | - |
| 18. Demo Packaging | v1.4 | 0/TBD | Not started | - |
