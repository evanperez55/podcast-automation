---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Real-World Testing & Sales Readiness
status: executing
stopped_at: Completed 18-02-PLAN.md — DemoPackager module and package-demo CLI command
last_updated: "2026-03-29T00:36:05.840Z"
last_activity: "2026-03-28 — Completed 18-01: raw audio snapshot before censorship"
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 10
  completed_plans: 10
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's voice — without manual intervention.
**Current focus:** Phase 15 — Config Hardening

## Current Position

Phase: 18 of 18 (v1.4) — Demo Packaging
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-03-28 — Completed 18-01: raw audio snapshot before censorship

Progress: [██░░░░░░░░] 20% (18-01 complete)

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
- [Phase 16-rss-episode-source]: EPISODE_SOURCE defaults to 'dropbox' for backward compatibility; 'rss_source' key avoids collision with RSS output metadata; extract_episode_number_from_filename replaces Dropbox episode number extraction in all branches
- [Phase 17-01]: clip_criteria conditional on VOICE_PERSONA presence: None = comedy criteria, set = content-quality criteria
- [Phase 17-01]: COMPLIANCE_PROMPT renamed to COMPLIANCE_PROMPT_TEMPLATE with {context} placeholder; _build_compliance_prompt() reads COMPLIANCE_STYLE with permissive default for FP backward compat
- [Phase 17-integration-testing-genre-fixes]: True crime client uses Casefile Acast feed URL (original Simplecast returns 403)
- [Phase 17-integration-testing-genre-fixes]: Non-Dropbox clients skip ALL uploaders in distribute.py to prevent FP credential leakage
- [Phase 17-integration-testing-genre-fixes]: normalize_audio uses temp file + rename to avoid FFmpeg in-place write crash
- [Phase 18-01]: Snapshot uses subprocess FFmpeg -ss/-to (not pydub) to avoid loading 1GB+ audio into memory
- [Phase 18-01]: Snapshot start derived from best_clips[0].start_seconds with 60.0 default; stored in censor checkpoint for resume recovery
- [Phase 18-demo-packaging]: PipelineState artifact discovery takes priority; glob fallback handles partial runs (business-interview-client has no state file)
- [Phase 18-demo-packaging]: LUFS measured at package time via FFmpeg loudnorm pass 1 — avoids brittle log parsing
- [Phase 18-demo-packaging]: main.py line-count limit bumped 210→220 to accommodate package-demo command

### Blockers/Concerns

- [Phase 15]: `NAMES_TO_REMOVE` silently falls back to Fake Problems host names — must be a validate-client hard error
- [Phase 16]: `DropboxHandler` unconditionally constructed in `runner.py` raises ValueError for every non-Dropbox client — critical blocker
- [Phase 17]: Genre clip scoring + compliance calibration are empirical — cannot be fully specified until real audio runs
- [Active]: `assets/podcast_logo.png` untracked (8.6MB) — needs Git LFS or compression

## Session Continuity

Last session: 2026-03-29T00:30:57.249Z
Stopped at: Completed 18-02-PLAN.md — DemoPackager module and package-demo CLI command
Resume file: None
