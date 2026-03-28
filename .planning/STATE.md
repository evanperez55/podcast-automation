---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Real-World Testing & Sales Readiness
status: planning
stopped_at: Completed 16-01-PLAN.md — RSSEpisodeFetcher with feedparser
last_updated: "2026-03-28T18:49:15.905Z"
last_activity: 2026-03-28 — Roadmap created, 4 phases, 12/12 requirements mapped
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 6
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's voice — without manual intervention.
**Current focus:** Phase 15 — Config Hardening

## Current Position

Phase: 15 of 18 (v1.4) — Config Hardening
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-28 — Roadmap created, 4 phases, 12/12 requirements mapped

Progress: [░░░░░░░░░░] 0% (v1.4 phases not yet started)

## Shipped Milestones

- v1.0 Pipeline Upgrade (2026-03-18): 5 phases, 14 plans, 14/14 requirements
- v1.1 Discoverability & Short-Form (2026-03-18): 3 phases, 6 plans, 14/14 requirements
- v1.2 Engagement & Smart Scheduling (2026-03-19): 3 phases, 7 plans, 13/13 requirements
- v1.3 Content Calendar (2026-03-19): 1 phase, 2 plans
- Post-v1.3: Multi-client productization (8 commits, 570 tests)

## Accumulated Context

### Decisions

- [v1.4 scope]: Validation milestone — prove pipeline works for real genres, then package for sales
- [v1.4 demo format]: Self-contained HTML (not PDF — WeasyPrint requires GTK+/MSYS2; wkhtmltopdf archived Jan 2023)
- [v1.4 dep]: `feedparser>=6.0.12` is the only new package needed for RSS ingest
- [v1.4 before/after]: Pipeline must snapshot raw audio before Step 4 censor — not currently done; required for DEMO-02
- [Phase 15-config-hardening]: null and empty list both valid for names_to_remove — field must be present, value need not be non-empty
- [Phase 15-config-hardening]: Active config block in validate_client printed before summary count, after output dir checks
- [Phase 15-config-hardening]: voice_examples conditional on VOICE_PERSONA: FP comedy BAD/GOOD examples only injected when no custom persona set — prevents voice leakage to non-FP clients
- [Phase 15-config-hardening]: genre YAMLs use getattr guard for VOICE_PERSONA — attribute not on Config by default; monkeypatch requires raising=False
- [Phase 16-rss-episode-source]: extract_episode_number_from_filename is module-level (not class method) for cross-module reuse without coupling to DropboxHandler
- [Phase 16-rss-episode-source]: RSS feed entries sorted by published_parsed descending before indexing — index=0 always means newest regardless of feed order

### Blockers/Concerns

- [Phase 15]: `NAMES_TO_REMOVE` silently falls back to Fake Problems host names — must be a validate-client hard error
- [Phase 16]: `DropboxHandler` unconditionally constructed in `runner.py` raises ValueError for every non-Dropbox client — critical blocker
- [Phase 17]: Genre clip scoring + compliance calibration are empirical — cannot be fully specified until real audio runs
- [Active]: `assets/podcast_logo.png` untracked (8.6MB) — needs Git LFS or compression

## Session Continuity

Last session: 2026-03-28T18:49:15.901Z
Stopped at: Completed 16-01-PLAN.md — RSSEpisodeFetcher with feedparser
Resume file: None
