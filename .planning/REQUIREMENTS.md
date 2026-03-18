# Requirements: Fake Problems Podcast — Discoverability & Short-Form

**Defined:** 2026-03-18
**Core Value:** One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## v1.1 Requirements

### Subtitle Clips

- [ ] **CLIP-01**: Clips rendered as vertical 9:16 video with word-by-word bold captions burned in
- [ ] **CLIP-02**: Active word highlighted with accent color as it's spoken
- [ ] **CLIP-03**: Word timing sourced from WhisperX word-level JSON (not sentence-level SRT)
- [ ] **CLIP-04**: Subtitle clips uploaded to YouTube Shorts, Instagram Reels, and TikTok

### Episode Webpages

- [ ] **WEB-01**: Static HTML episode page with full searchable transcript
- [ ] **WEB-02**: PodcastEpisode JSON-LD structured data on each page
- [ ] **WEB-03**: SEO meta tags (Open Graph, Twitter Card) with episode-specific keywords
- [ ] **WEB-04**: Chapter navigation within the transcript page
- [ ] **WEB-05**: Sitemap.xml auto-generated and updated with each new episode
- [ ] **WEB-06**: Pages deployed to GitHub Pages automatically

### Content Compliance

- [ ] **SAFE-01**: Transcript analyzed against YouTube community guidelines before upload
- [ ] **SAFE-02**: Flagged segments include timestamps, quoted text, and rule category
- [ ] **SAFE-03**: Flagged segments can be auto-muted or cut from the video before upload
- [ ] **SAFE-04**: Upload blocked when critical violations detected (requires --force to override)

## v2 Requirements

### Distribution Expansion

- **DIST-02**: Instagram Reels automatically uploaded via pipeline
- **DIST-03**: Bluesky posting via atproto SDK
- **DIST-04**: Threads posting via Meta API

### Audio Enhancement

- **AUDIO-04**: Filler word removal (ums/ahs) with configurable threshold and preview

### Content & SEO

- **VOICE-06**: Keyword extraction via KeyBERT for SEO metadata (beyond basic yake)
- **VOICE-08**: Subtitle style presets (Hormozi/minimal/pop) and speaker labels

## Out of Scope

| Feature | Reason |
|---------|--------|
| Animated pop-in/bounce subtitle effects | Requires frame renderer (MoviePy/pycaps), v1.2 concern |
| Speaker labels on subtitle clips | Requires diarization integration into clip step, defer to v1.2 |
| Filler word removal | May impact comedic timing per user feedback |
| Self-hosted webpages | GitHub Pages is free and sufficient |
| Video background replacement for clips | Beyond current pipeline scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLIP-01 | TBD | Pending |
| CLIP-02 | TBD | Pending |
| CLIP-03 | TBD | Pending |
| CLIP-04 | TBD | Pending |
| WEB-01 | TBD | Pending |
| WEB-02 | TBD | Pending |
| WEB-03 | TBD | Pending |
| WEB-04 | TBD | Pending |
| WEB-05 | TBD | Pending |
| WEB-06 | TBD | Pending |
| SAFE-01 | TBD | Pending |
| SAFE-02 | TBD | Pending |
| SAFE-03 | TBD | Pending |
| SAFE-04 | TBD | Pending |

**Coverage:**
- v1.1 requirements: 14 total
- Mapped to phases: 0
- Unmapped: 14

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after initial definition*
