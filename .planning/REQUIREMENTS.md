# Requirements: Fake Problems Podcast — Content Calendar

**Defined:** 2026-03-19
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## v1.3 Requirements

### Content Calendar

- [x] **CAL-01**: Content calendar generates a 5-slot distribution plan per episode (D-1 teaser, D0 episode + clip 1, D+2 clip 2, D+4 clip 3)
- [x] **CAL-02**: Calendar tracks per-slot, per-platform upload status in `topic_data/content_calendar.json`
- [x] **CAL-03**: `python main.py upload-scheduled` fires due slots from the calendar (extends existing scheduled upload)
- [x] **CAL-04**: Dry run displays the full calendar plan with slot dates and platform assignments

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
| CI/CD automation | Pipeline requires GPU + Ollama locally; GitHub-hosted runners can't support this |
| Instagram/TikTok clip slots | Uploaders are stubs — calendar generates slots but skips non-functional platforms |
| ML engagement prediction | Dataset still too small; scipy correlations sufficient |
| Web dashboard for calendar | CLI-driven pipeline — calendar viewable via dry-run output |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAL-01 | Phase 12 | Complete |
| CAL-02 | Phase 12 | Complete |
| CAL-03 | Phase 12 | Complete |
| CAL-04 | Phase 12 | Complete |

**Coverage:**
- v1.3 requirements: 4 total
- Mapped to phases: 4
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 — traceability mapped after roadmap creation*
