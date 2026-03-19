# Requirements: Fake Problems Podcast — Engagement & Smart Scheduling

**Defined:** 2026-03-18
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## v1.2 Requirements

### Analytics Infrastructure

- [x] **ANLYT-01**: Video IDs stored at upload time for each platform (no search API calls needed for analytics)
- [x] **ANLYT-02**: Twitter analytics handles missing impressions gracefully on free tier
- [x] **ANLYT-03**: Engagement history accumulated in rolling JSON per episode (post time, platform, engagement metrics)
- [x] **ANLYT-04**: Stub uploaders detected and flagged so scheduling/analytics skip non-functional platforms

### Engagement Scoring

- [x] **ENGAGE-01**: Topic categories ranked by historical engagement correlation
- [x] **ENGAGE-02**: Day-of-week performance analysis per platform
- [x] **ENGAGE-03**: Comedy voice preserved as constraint — optimizer cannot de-score edgy content
- [x] **ENGAGE-04**: Confidence gating — no recommendations until minimum data threshold met (15+ episodes)

### Smart Scheduling

- [ ] **SCHED-01**: Optimal posting time computed from own historical data + research defaults
- [ ] **SCHED-02**: Platform-specific scheduling windows (YouTube, Twitter differ)
- [ ] **SCHED-03**: scheduler.py accepts computed optimal times instead of fixed delay config

### Content Optimization

- [x] **CONTENT-01**: Relevant hashtags auto-injected into Twitter posts (1-2 tags from curated list)
- [x] **CONTENT-02**: GPT-4o title/caption optimization using engagement history as context

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
| ML engagement prediction model | Dataset too small (~29 episodes); scipy correlations are appropriate now. Revisit at v1.3 with 50+ episodes |
| Instagram/TikTok analytics collection | Uploaders are stubs — analytics require working upload pipeline first (DIST-02) |
| A/B testing clips | Episodic content with confounders makes true A/B impractical at current scale |
| Cross-platform analytics dashboard | CLI-driven pipeline, no web UI — engagement reports via CLI output |
| Real-time scheduling daemon | Conflicts with CLI run-and-exit model; compute schedule at pipeline time |
| Animated pop-in/bounce subtitle effects | Requires frame renderer (MoviePy/pycaps), v1.3+ concern |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANLYT-01 | Phase 9 | Complete |
| ANLYT-02 | Phase 9 | Complete |
| ANLYT-03 | Phase 9 | Complete |
| ANLYT-04 | Phase 9 | Complete |
| CONTENT-01 | Phase 9 | Complete |
| ENGAGE-01 | Phase 10 | Complete |
| ENGAGE-02 | Phase 10 | Complete |
| ENGAGE-03 | Phase 10 | Complete |
| ENGAGE-04 | Phase 10 | Complete |
| CONTENT-02 | Phase 10 | Complete |
| SCHED-01 | Phase 11 | Pending |
| SCHED-02 | Phase 11 | Pending |
| SCHED-03 | Phase 11 | Pending |

**Coverage:**
- v1.2 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
