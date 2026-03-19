# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- ✅ **v1.1 Discoverability & Short-Form** — Phases 6-8 (shipped 2026-03-18)
- ✅ **v1.2 Engagement & Smart Scheduling** — Phases 9-11 (shipped 2026-03-19)
- 🚧 **v1.3 Content Calendar & CI/CD** — Phases 12-14 (in progress)

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

### 🚧 v1.3 Content Calendar & CI/CD (In Progress)

**Milestone Goal:** Automate the entire bi-weekly release cycle — a content calendar spreads clip distribution across the week, and GitHub Actions runs the pipeline without manual intervention (with a human review gate before any social uploads).

- [ ] **Phase 12: ContentCalendar Foundation** - Content calendar module with spread scheduling, JSON state, and dry-run display
- [ ] **Phase 13: CI/CD Automation** - GitHub Actions workflows with self-hosted runner, Dropbox polling, and human review gate
- [ ] **Phase 14: Security & Reliability Hardening** - Secrets management, concurrency control, SHA pinning, and pre-flight validation

## Phase Details

### Phase 12: ContentCalendar Foundation
**Goal**: Users can generate and inspect a per-episode content calendar that spreads clip uploads across the week instead of dumping everything on release day
**Depends on**: Phase 11 (existing scheduler/optimizer infrastructure)
**Requirements**: CAL-01, CAL-02, CAL-03, CAL-04
**Success Criteria** (what must be TRUE):
  1. Running `python main.py ep29 --dry-run` prints the full 5-slot calendar plan with dates, times, and platform assignments without performing any uploads
  2. After a real episode run, `topic_data/content_calendar.json` contains a record for that episode with D0/D+2/D+4 slot entries and per-slot upload status
  3. Running `python main.py upload-scheduled` fires only the clip slots whose scheduled datetime has passed, leaving future slots untouched
  4. The calendar correctly spreads clips: episode on D0, clip 1 on D+2, clip 2 on D+4 — no two clips land on the same day
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md — ContentCalendar module with slot generation, atomic JSON persistence, and unit tests
- [ ] 12-02-PLAN.md — Pipeline integration: distribute calls plan_episode, upload-scheduled dispatches calendar slots, dry-run display

### Phase 13: CI/CD Automation
**Goal**: The pipeline runs automatically when a new episode appears in Dropbox, stops for human approval before any social uploads, and can also be triggered manually
**Depends on**: Phase 12 (ContentCalendar for episode deduplication in poll.py)
**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05
**Success Criteria** (what must be TRUE):
  1. Dropping a new episode WAV into the Dropbox folder causes the pipeline to start within 6 hours with no manual action
  2. The pipeline workflow runs steps 1-6 (download through MP3/blog), then pauses and sends a Discord notification before any YouTube or social upload executes
  3. A named reviewer can approve or cancel the distribution step from GitHub Actions without touching the local machine
  4. `workflow_dispatch` lets the user trigger processing of a specific episode immediately from the GitHub Actions UI
  5. The self-hosted runner survives a Windows reboot and resumes handling workflow jobs automatically
**Plans**: TBD

Plans:
- [ ] 13-01: Self-hosted runner setup (Windows service install, GPU labels, reboot resilience) and ci/poll.py (filename/size/age/dedup guards, exit codes for workflow conditional)
- [ ] 13-02: GitHub Actions workflows (.github/workflows/poll.yml cron, .github/workflows/manual.yml dispatch, environment production gate, Discord notification with approve/cancel link)

### Phase 14: Security & Reliability Hardening
**Goal**: The automated pipeline cannot be compromised by leaked secrets, concurrent duplicate runs, or silent credential failures — and all third-party CI actions are supply-chain safe
**Depends on**: Phase 13 (workflows must exist to be hardened)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04
**Success Criteria** (what must be TRUE):
  1. All OAuth tokens and API keys are stored as individual scalar GitHub Secrets (not JSON blobs), and workflow logs contain no credential values
  2. Dispatching the pipeline twice for the same episode causes the second run to queue rather than run in parallel, preventing duplicate uploads
  3. Every `uses:` reference in all workflow YAML files points to a full 40-character commit SHA, not a mutable tag
  4. If any required secret is missing or returns a 401 at job start, the workflow exits with a clear error before any upload or processing step runs
**Plans**: TBD

Plans:
- [ ] 14-01: Secrets migration (split all OAuth JSON blobs into scalar secrets, config.py env var mapping, verify no secrets appear in workflow logs)
- [ ] 14-02: Reliability hardening (concurrency groups in all workflows, SHA-pin all third-party actions, pre-flight credential check script)

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
| 12. ContentCalendar Foundation | v1.3 | 0/2 | Not started | - |
| 13. CI/CD Automation | v1.3 | 0/2 | Not started | - |
| 14. Security & Reliability Hardening | v1.3 | 0/2 | Not started | - |
