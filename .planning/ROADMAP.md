# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- ✅ **v1.1 Discoverability & Short-Form** — Phases 6-8 (shipped 2026-03-18)
- ✅ **v1.2 Engagement & Smart Scheduling** — Phases 9-11 (shipped 2026-03-19)
- ✅ **v1.3 Content Calendar** — Phase 12 (shipped 2026-03-19)
- ✅ **v1.4 Real-World Testing & Sales Readiness** — Phases 15-18 (shipped 2026-03-29)
- ✅ **v1.5 First Paying Client** — Phases 19-22 (shipped 2026-04-06)
- 🚧 **v1.6 Production Quality & Operations** — Phases 23-27 (in progress)

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

<details>
<summary>✅ v1.5 First Paying Client (Phases 19-22) — SHIPPED 2026-04-06</summary>

- [x] Phase 19: Outreach Tracker (1/1 plans) — completed 2026-03-29
- [x] Phase 20: Prospect Finder (2/2 plans) — completed 2026-03-29
- [x] Phase 21: Pitch Generator (1/1 plans) — completed 2026-03-29
- [x] Phase 22: Outreach Execution (2/2 plans) — completed 2026-04-06

See: .planning/milestones/v1.5-ROADMAP.md for full details.

</details>

### 🚧 v1.6 Production Quality & Operations (In Progress)

**Milestone Goal:** Make the pipeline operationally ready for paying clients — add failure visibility, reduce onboarding friction, polish demo output quality, and optimize clip selection using engagement data.

- [x] **Phase 23: Monitoring & Alerting** - Discord notifications for pipeline failures and successful run summaries (completed 2026-04-07)
- [ ] **Phase 24: Client Onboarding Docs** - ONBOARDING.md checklist and annotated client YAML template
- [ ] **Phase 25: Composite Clip Scoring** - Multi-signal clip ranking and tunable AudioClipScorer weights
- [ ] **Phase 26: Demo Output Optimization** - Autoresearch-driven subtitle styling and thumbnail contrast tuning
- [ ] **Phase 27: Clip Weight Optimization** - Autoresearch-driven AudioClipScorer weight tuning against engagement data

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
- [x] 20-01-PLAN.md — ProspectFinder module TDD (search, enrich, save)
- [x] 20-02-PLAN.md — CLI wiring (find-prospects command in main.py)

### Phase 21: Pitch Generator
**Goal**: Users can generate a personalized, show-specific outreach message (intro and demo pitch) for each prospect without writing it from scratch
**Depends on**: Phase 20
**Requirements**: PITCH-01, PITCH-02
**Success Criteria** (what must be TRUE):
  1. User can run `gen-pitch <slug>` (pre-demo) and receive a personalized intro message referencing the prospect's show name, genre, and production gaps
  2. User can run `gen-pitch <slug> <ep_id>` (post-demo) and receive a pitch email and DM that reference specific output from the processed episode (LUFS delta, clip count, show note excerpt)
  3. Generated pitch is written to `demo/<slug>/<ep_id>/PITCH.md` alongside the existing demo artifacts
**Plans:** 1/1 plans complete

Plans:
- [x] 21-01-PLAN.md — PitchGenerator module (intro + demo modes), tests, CLI wiring

### Phase 22: Outreach Execution
**Goal**: Users can process a consented prospect's episode and package a demo in one workflow, then execute manual outreach with the generated pitch
**Depends on**: Phase 21
**Requirements**: DEMO-04
**Success Criteria** (what must be TRUE):
  1. User can run a single workflow to process a prospect's episode and produce a packaged demo folder (pipeline + `package-demo`) gated on a consent confirmation prompt
  2. The consent prompt blocks processing unless the user explicitly confirms consent has been obtained from the prospect
  3. At least one real prospect receives a pitch with their own episode's output attached, and the contact log reflects the interaction
**Plans:** 2/2 plans complete

Plans:
- [x] 22-01-PLAN.md — Consent-gated demo workflow command (demo_packager.py + main.py CLI wiring + tests)
- [x] 22-02-PLAN.md — Real prospect outreach execution (human checkpoint)

### Phase 23: Monitoring & Alerting
**Goal**: Pipeline failures and successes surface immediately in Discord so no client run goes unobserved
**Depends on**: Phase 22
**Requirements**: MON-01, MON-02
**Success Criteria** (what must be TRUE):
  1. When any pipeline step raises an unhandled exception, a Discord message is sent with the episode name, step name, and error text before the process exits
  2. When a pipeline run completes successfully, a Discord summary message shows episode name, total duration, number of clips produced, and which platforms received uploads
  3. Alerts fire for all clients (multi-client runs each send their own notification)
  4. When DISCORD_WEBHOOK_URL is not set, both alert behaviors disable silently without affecting pipeline execution
**Plans**: 1 plans

Plans:
- [x] 23-01-PLAN.md — Per-step failure alerts, success summaries with duration, and tests

### Phase 24: Client Onboarding Docs
**Goal**: A new client can be onboarded without the developer needing to explain anything verbally — all required info is documented
**Depends on**: Phase 23
**Requirements**: ONBOARD-01, ONBOARD-02
**Success Criteria** (what must be TRUE):
  1. ONBOARDING.md exists and lists every piece of client-supplied information required (show name, RSS feed, genre, voice persona, censorship words, social credentials) with field-level descriptions
  2. A client YAML template file exists with inline comments on every field, including valid options for enum fields (genre, compliance_style, clip_mode)
  3. A developer can hand ONBOARDING.md and the YAML template to a new client and set them up without a call
**Plans**: 1 plans

Plans:
- [ ] 24-01-PLAN.md — ONBOARDING.md checklist and annotated client-template.yaml

### Phase 25: Composite Clip Scoring
**Goal**: Clips are ranked by a multi-signal quality score and the scorer's weights are tunable per client without code changes
**Depends on**: Phase 22
**Requirements**: DEMO-05, CLIP-05
**Success Criteria** (what must be TRUE):
  1. AudioClipScorer computes a composite score combining audio energy, content relevance (GPT-4o hook strength), and hook strength signals — not energy alone
  2. The three scoring weights (energy_weight, content_weight, hook_weight) can be set in a client's YAML config and override the defaults
  3. When weights are omitted from YAML, the scorer uses hardcoded defaults that produce the same behavior as before this phase
  4. Running `python main.py ep29 --auto-approve` with a modified client YAML selects clips in a different order reflecting the new weights
**Plans**: 1 plans

Plans:
- [ ] 24-01-PLAN.md — ONBOARDING.md checklist and annotated client-template.yaml
**UI hint**: no

### Phase 26: Demo Output Optimization
**Goal**: Subtitle clip styling and thumbnail appearance are tuned for each genre to maximize visual appeal in demo materials
**Depends on**: Phase 25
**Requirements**: DEMO-06, DEMO-07
**Success Criteria** (what must be TRUE):
  1. Subtitle clips use a genre-specific style profile (font size, stroke weight, animation timing, color) that differs visibly between comedy, true crime, and business genres
  2. Thumbnails use a color palette and text placement rule appropriate to the client's genre (verified by visual inspection of packaged demo output)
  3. Style parameters for subtitles and thumbnails are defined in one place (config or per-genre defaults) and can be overridden per client YAML
  4. Autoresearch optimization runs produce measurably different style configurations and a record of which iteration scored highest
**Plans**: 1 plans

Plans:
- [ ] 24-01-PLAN.md — ONBOARDING.md checklist and annotated client-template.yaml
**UI hint**: yes

### Phase 27: Clip Weight Optimization
**Goal**: AudioClipScorer weights for each client are tuned to select clips that historically correlate with higher engagement
**Depends on**: Phase 25
**Requirements**: CLIP-06
**Success Criteria** (what must be TRUE):
  1. For clients with sufficient engagement history (15+ episodes), autoresearch iterations produce a recommended weight configuration (energy_weight, content_weight, hook_weight) that improves the correlation between clip scores and engagement metrics
  2. The optimized weights are written to the client YAML (or a companion override file) so future pipeline runs use the tuned configuration automatically
  3. A run log documents the baseline score, each iteration's score, and the final accepted configuration
**Plans**: 1 plans

Plans:
- [ ] 24-01-PLAN.md — ONBOARDING.md checklist and annotated client-template.yaml
**UI hint**: no

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
| 20. Prospect Finder | v1.5 | 2/2 | Complete | 2026-03-29 |
| 21. Pitch Generator | v1.5 | 1/1 | Complete | 2026-03-29 |
| 22. Outreach Execution | v1.5 | 2/2 | Complete | 2026-04-06 |
| 23. Monitoring & Alerting | v1.6 | 1/1 | Complete    | 2026-04-07 |
| 24. Client Onboarding Docs | v1.6 | 0/? | Not started | - |
| 25. Composite Clip Scoring | v1.6 | 0/? | Not started | - |
| 26. Demo Output Optimization | v1.6 | 0/? | Not started | - |
| 27. Clip Weight Optimization | v1.6 | 0/? | Not started | - |
