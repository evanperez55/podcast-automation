# Requirements: Fake Problems Podcast — Pipeline Upgrade

**Defined:** 2026-03-16
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## v1 Requirements

### Audio Quality

- [x] **AUDIO-01**: Censored segments use smooth audio ducking (volume fade to silence) instead of beep tones
- [x] **AUDIO-02**: Episodes normalized to -16 LUFS using ffmpeg-normalize EBU R128 two-pass filter
- [x] **AUDIO-03**: Normalization metadata logged per episode (measured LUFS, gain applied, LRA)

### Content Voice

- [x] **VOICE-01**: All AI-generated text (titles, descriptions, social posts, blog) uses edgy comedy tone via few-shot prompts
- [x] **VOICE-02**: Clip detection scores moments by audio energy, laughter patterns, and conversation dynamics (not just topic changes)
- [x] **VOICE-03**: Generated clips include hook-style captions matching show's humor
- [ ] **VOICE-04**: Chapter markers auto-generated from transcript segments and embedded in MP3 ID3 tags
- [ ] **VOICE-05**: Chapter markers included in RSS feed for podcast apps

### Distribution

- [x] **DIST-01**: Scheduled upload execution actually uploads to platforms (fix stub)

### Tech Debt

- [ ] **DEBT-01**: main.py split into pipeline/ package with modular step classes and PipelineContext dataclass
- [x] **DEBT-02**: openai SDK added to requirements.txt
- [x] **DEBT-03**: Naming artifacts cleaned up (_parse_claude_response renamed, duplicate config reads fixed, inline re imports moved to top)
- [x] **DEBT-04**: Google credential files moved to credentials/ directory
- [ ] **DEBT-05**: continue_episode.py eliminated by delegating to extracted pipeline steps

## v2 Requirements

### Distribution Expansion

- **DIST-02**: Instagram Reels automatically uploaded via pipeline
- **DIST-03**: Bluesky posting via atproto SDK
- **DIST-04**: Threads posting via Meta API

### Audio Enhancement

- **AUDIO-04**: Filler word removal (ums/ahs) with configurable threshold and preview

### Content & SEO

- **VOICE-06**: Episode webpage generation for SEO (requires hosting decision)
- **VOICE-07**: Keyword extraction via KeyBERT for SEO metadata
- **VOICE-08**: Burned-in subtitle Shorts/Reels for vertical video platforms

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dynamic ad insertion | Requires CDN hosting infrastructure, incompatible with zero-cost constraint |
| Live streaming | Post-production pipeline only |
| Mobile app | CLI-driven workflow is the right fit |
| Language rewrite | Must stay Python |
| Multi-camera video editing | Beyond pipeline scope, no B-roll source material |
| Plugin registry / dynamic step discovery | Fixed 18-step pipeline doesn't benefit from dynamic registration |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIO-01 | Phase 2 | In Progress |
| AUDIO-02 | Phase 2 | In Progress |
| AUDIO-03 | Phase 2 | In Progress |
| VOICE-01 | Phase 3 | Complete |
| VOICE-02 | Phase 3 | Complete |
| VOICE-03 | Phase 3 | Complete |
| VOICE-04 | Phase 4 | Pending |
| VOICE-05 | Phase 4 | Pending |
| DIST-01 | Phase 1 | Complete |
| DEBT-01 | Phase 5 | Pending |
| DEBT-02 | Phase 1 | Complete |
| DEBT-03 | Phase 1 | Complete |
| DEBT-04 | Phase 1 | Complete |
| DEBT-05 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after roadmap creation*
