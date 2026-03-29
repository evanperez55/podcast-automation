# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- ✅ **v1.1 Discoverability & Short-Form** — Phases 6-8 (shipped 2026-03-18)
- ✅ **v1.2 Engagement & Smart Scheduling** — Phases 9-11 (shipped 2026-03-19)
- ✅ **v1.3 Content Calendar** — Phase 12 (shipped 2026-03-19)
- ✅ **v1.4 Real-World Testing & Sales Readiness** — Phases 15-18 (shipped 2026-03-29)
- 🚧 **v1.5 First Paying Client** — Phases 19-22 (in progress)

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

<details>
<summary>✅ v1.4 Real-World Testing & Sales Readiness (Phases 15-18) — SHIPPED 2026-03-29</summary>

- [x] Phase 15: Config Hardening (2/2 plans) — completed 2026-03-28
- [x] Phase 16: RSS Episode Source (2/2 plans) — completed 2026-03-28
- [x] Phase 17: Integration Testing & Genre Fixes (2/2 plans) — completed 2026-03-28
- [x] Phase 18: Demo Packaging (2/2 plans) — completed 2026-03-29

See: .planning/milestones/v1.4-ROADMAP.md for full details.

</details>

### 🚧 v1.5 First Paying Client (In Progress)

**Milestone Goal:** Find 3-5 real podcast prospects, process a demo episode per prospect, generate personalized outreach copy, and land the first paying client.

- [x] **Phase 19: Outreach Tracker** - SQLite contact log with CLI lifecycle management for prospect tracking (completed 2026-03-29)
- [x] **Phase 20: Prospect Finder** - iTunes API podcast search, RSS contact extraction, and YAML config scaffolding (completed 2026-03-29)
- [ ] **Phase 21: Pitch Generator** - GPT-4o personalized pitch email and DM from demo output and prospect metadata
- [ ] **Phase 22: Outreach Execution** - Consent-gated demo production workflow and manual outreach execution

## Phase Details

### Phase 19: Outreach Tracker
**Goal**: Users can track every prospect through a defined lifecycle from identification to conversion or decline, with no lost leads
**Depends on**: Nothing (first v1.5 phase)
**Requirements**: TRACK-01, TRACK-02
**Success Criteria** (what must be TRUE):
  1. User can add a prospect to the tracker and see it appear in `outreach list`
  2. User can update a prospect's status through each lifecycle stage (identified → contacted → interested → demo_sent → converted/declined)
  3. User can view a summary table of all prospects with current status and last-contact date
  4. Duplicate prospect entries are prevented (add is idempotent on slug)
**Plans:** 1/1 plans complete

Plans:
- [x] 19-01-PLAN.md — OutreachTracker module, tests, and CLI wiring

### Phase 20: Prospect Finder
**Goal**: Users can discover qualified podcast prospects by genre, enrich them with contact info, and create a ready-to-process client YAML in one workflow
**Depends on**: Phase 19
**Requirements**: DISC-01, DISC-02, DISC-03
**Success Criteria** (what must be TRUE):
  1. User can run `find-prospects --genre comedy --min-episodes 20 --max-episodes 500` and receive a ranked list of matching shows
  2. User can enrich a prospect and see host email and social links extracted from their RSS feed
  3. User can save a prospect as a client YAML with genre, voice persona, and compliance style pre-filled based on the selected genre
  4. Saved prospect is automatically registered in the outreach tracker at `identified` status
**Plans:** 2/2 plans complete

Plans:
- [ ] 20-01-PLAN.md — ProspectFinder module TDD (search, enrich, save)
- [ ] 20-02-PLAN.md — CLI wiring (find-prospects command in main.py)

### Phase 21: Pitch Generator
**Goal**: Users can generate a personalized, show-specific outreach message (intro and demo pitch) for each prospect without writing it from scratch
**Depends on**: Phase 20
**Requirements**: PITCH-01, PITCH-02
**Success Criteria** (what must be TRUE):
  1. User can run `gen-pitch <slug>` (pre-demo) and receive a personalized intro message referencing the prospect's show name, genre, and production gaps
  2. User can run `gen-pitch <slug> <ep_id>` (post-demo) and receive a pitch email and DM that reference specific output from the processed episode (LUFS delta, clip count, show note excerpt)
  3. Generated pitch is written to `demo/<slug>/<ep_id>/PITCH.md` alongside the existing demo artifacts
**Plans**: TBD

### Phase 22: Outreach Execution
**Goal**: Users can process a consented prospect's episode and package a demo in one workflow, then execute manual outreach with the generated pitch
**Depends on**: Phase 21
**Requirements**: DEMO-04
**Success Criteria** (what must be TRUE):
  1. User can run a single workflow to process a prospect's episode and produce a packaged demo folder (pipeline + `package-demo`) gated on a consent confirmation prompt
  2. The consent prompt blocks processing unless the user explicitly confirms consent has been obtained from the prospect
  3. At least one real prospect receives a pitch with their own episode's output attached, and the contact log reflects the interaction
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
| 9. Analytics Infrastructure | v1.2 | 3/3 | Complete | 2026-03-19 |
| 10. Engagement Scoring | v1.2 | 2/2 | Complete | 2026-03-19 |
| 11. Smart Scheduling | v1.2 | 2/2 | Complete | 2026-03-19 |
| 12. ContentCalendar Foundation | v1.3 | 2/2 | Complete | 2026-03-19 |
| 15. Config Hardening | v1.4 | 2/2 | Complete | 2026-03-28 |
| 16. RSS Episode Source | v1.4 | 2/2 | Complete | 2026-03-28 |
| 17. Integration Testing & Genre Fixes | v1.4 | 2/2 | Complete | 2026-03-28 |
| 18. Demo Packaging | v1.4 | 2/2 | Complete | 2026-03-29 |
| 19. Outreach Tracker | v1.5 | 1/1 | Complete | 2026-03-29 |
| 20. Prospect Finder | 2/2 | Complete    | 2026-03-29 | - |
| 21. Pitch Generator | v1.5 | 0/TBD | Not started | - |
| 22. Outreach Execution | v1.5 | 0/TBD | Not started | - |
