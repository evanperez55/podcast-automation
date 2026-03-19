# Requirements: Fake Problems Podcast — Content Calendar & CI/CD

**Defined:** 2026-03-19
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## v1.3 Requirements

### Content Calendar

- [ ] **CAL-01**: Content calendar generates a 5-slot distribution plan per episode (D-1 teaser, D0 episode + clip 1, D+2 clip 2, D+4 clip 3)
- [ ] **CAL-02**: Calendar tracks per-slot, per-platform upload status in `topic_data/content_calendar.json`
- [ ] **CAL-03**: `python main.py upload-scheduled` fires due slots from the calendar (extends existing scheduled upload)
- [ ] **CAL-04**: Dry run displays the full calendar plan with slot dates and platform assignments

### CI/CD Automation

- [ ] **CI-01**: Self-hosted GitHub Actions runner configured on Windows machine with GPU access
- [ ] **CI-02**: Dropbox polling workflow detects new episode WAV files and triggers pipeline
- [ ] **CI-03**: Pipeline workflow runs full processing (download through MP3/blog) then pauses for human review
- [ ] **CI-04**: Human review gate via GitHub environment approval before any social/YouTube uploads execute
- [ ] **CI-05**: Manual workflow_dispatch trigger available as alternative to Dropbox polling

### Security & Reliability

- [ ] **SEC-01**: All credentials stored as GitHub Secrets (OAuth tokens split into scalar values)
- [ ] **SEC-02**: Concurrency groups prevent parallel runs (queue, don't cancel)
- [ ] **SEC-03**: All third-party GitHub Actions SHA-pinned (no tag references)
- [ ] **SEC-04**: Pre-flight credential check validates all required secrets before pipeline starts

## v2 Requirements

### Distribution Expansion

- **DIST-02**: Instagram Reels automatically uploaded via pipeline
- **DIST-03**: Bluesky posting via atproto SDK
- **DIST-04**: Threads posting via Meta API

### Audio Enhancement

- **AUDIO-04**: Filler word removal (ums/ahs) with configurable threshold and preview

### Content & SEO

- **VOICE-08**: Subtitle style presets (Hormozi/minimal/pop) and speaker labels

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud GPU runner | $25/episode cost, incompatible with zero-cost constraint |
| Dropbox webhooks | Requires public HTTPS endpoint — unnecessary infrastructure for polling |
| Full auto-post without review | ep29 YouTube strike makes human gate mandatory for edgy comedy content |
| Instagram/TikTok clip slots | Uploaders are stubs — calendar generates slots but skips non-functional platforms |
| ML engagement prediction | Dataset still too small; scipy correlations sufficient |
| Web dashboard for calendar | CLI-driven pipeline — calendar viewable via dry-run output |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAL-01 | TBD | Pending |
| CAL-02 | TBD | Pending |
| CAL-03 | TBD | Pending |
| CAL-04 | TBD | Pending |
| CI-01 | TBD | Pending |
| CI-02 | TBD | Pending |
| CI-03 | TBD | Pending |
| CI-04 | TBD | Pending |
| CI-05 | TBD | Pending |
| SEC-01 | TBD | Pending |
| SEC-02 | TBD | Pending |
| SEC-03 | TBD | Pending |
| SEC-04 | TBD | Pending |

**Coverage:**
- v1.3 requirements: 13 total
- Mapped to phases: 0
- Unmapped: 13

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after initial definition*
