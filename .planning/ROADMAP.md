# Roadmap: Fake Problems Podcast — Pipeline Automation

## Milestones

- ✅ **v1.0 Pipeline Upgrade** — Phases 1-5 (shipped 2026-03-18)
- 🚧 **v1.1 Discoverability & Short-Form** — Phases 6-8 (in progress)

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

### 🚧 v1.1 Discoverability & Short-Form (In Progress)

**Milestone Goal:** Make clips go viral with burned-in subtitle vertical videos and drive organic search traffic with SEO-optimized episode webpages.

- [x] **Phase 6: Subtitle Clip Generator** - Vertical 9:16 MP4 clips with word-by-word burned-in captions uploaded to Shorts/Reels/TikTok (completed 2026-03-18)
- [x] **Phase 7: Episode Webpages** - SEO-optimized static HTML pages with full transcripts deployed to GitHub Pages (completed 2026-03-18)
- [ ] **Phase 8: Content Compliance** - YouTube community guidelines safety gate blocking non-compliant uploads

## Phase Details

### Phase 6: Subtitle Clip Generator
**Goal**: Clips are rendered as vertical 9:16 videos with large, bold, word-by-word burned-in captions and uploaded to YouTube Shorts, Instagram Reels, and TikTok
**Depends on**: Phase 5 (v1.0 pipeline complete — subtitle clip step replaces audiogram in Step 5.5)
**Requirements**: CLIP-01, CLIP-02, CLIP-03, CLIP-04
**Success Criteria** (what must be TRUE):
  1. Running `python main.py ep29 --auto-approve` produces vertical MP4 clips with visible large bold captions over each spoken word (not SRT overlays — burned in via FFmpeg)
  2. The currently spoken word appears in an accent highlight color while surrounding words remain white, visually tracking speech through the clip
  3. Caption timing sourced from WhisperX word-level JSON aligns captions to within 100ms of spoken audio
  4. Clips are uploaded to YouTube Shorts, Instagram Reels queue, and TikTok automatically as part of the distribute step
**Plans:** 2/2 plans complete

Plans:
- [ ] 06-01-PLAN.md — Build SubtitleClipGenerator core module (rendering engine + tests)
- [ ] 06-02-PLAN.md — Wire into pipeline + font asset + visual verification

### Phase 7: Episode Webpages
**Goal**: Each published episode gets an SEO-optimized static HTML page on GitHub Pages with the full searchable transcript, structured data, and chapter navigation
**Depends on**: Phase 6 (independent — can be built in parallel; depends only on v1.0 pipeline data)
**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06
**Success Criteria** (what must be TRUE):
  1. After running the distribute step, a publicly accessible HTML page exists at the GitHub Pages URL for that episode containing the full searchable transcript
  2. The episode page passes Google Rich Results Test for PodcastEpisode JSON-LD structured data
  3. The page HTML includes Open Graph and Twitter Card meta tags with episode-specific keywords extracted from the transcript
  4. Chapter timestamps are rendered as clickable jump links within the transcript page
  5. sitemap.xml at the GitHub Pages root is updated with the new episode URL within the same pipeline run
**Plans:** 2/2 plans complete

Plans:
- [ ] 07-01-PLAN.md — Build EpisodeWebpageGenerator core module (HTML generation, JSON-LD, meta tags, keywords, chapters, sitemap)
- [ ] 07-02-PLAN.md — GitHub Pages deployment + pipeline wiring + visual verification

### Phase 8: Content Compliance
**Goal**: Transcripts are analyzed against YouTube community guidelines before any upload, with flagged segments logged and critical violations blocking the upload unless overridden
**Depends on**: Phase 6 (upload blocking requires the upload step to exist; analysis and flagging are independent)
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04
**Success Criteria** (what must be TRUE):
  1. After analysis runs, a compliance report is written listing any flagged segments with their timestamps, quoted text, and violation category (e.g., "hate speech", "graphic content")
  2. Flagged segments are automatically muted or cut from the video file before the upload step executes, with no manual intervention required
  3. When critical violations are detected, the upload step is skipped and the pipeline prints a clear blocking message; running with `--force` overrides the block and proceeds to upload
**Plans:** 2 plans

Plans:
- [ ] 08-01-PLAN.md — Build ContentComplianceChecker module (GPT-4o violation classification + report + tests)
- [ ] 08-02-PLAN.md — Wire into pipeline as Step 3.6 + upload block + --force flag

## Progress

**Execution Order:** 6 → 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundations | v1.0 | 3/3 | Complete | 2026-03-17 |
| 2. Audio Quality | v1.0 | 3/3 | Complete | 2026-03-17 |
| 3. Content Voice and Clips | v1.0 | 3/3 | Complete | 2026-03-17 |
| 4. Chapter Markers | v1.0 | 2/2 | Complete | 2026-03-17 |
| 5. Architecture Refactor | v1.0 | 3/3 | Complete | 2026-03-18 |
| 6. Subtitle Clip Generator | v1.1 | 2/2 | Complete | 2026-03-18 |
| 7. Episode Webpages | v1.1 | 2/2 | Complete | 2026-03-18 |
| 8. Content Compliance | v1.1 | 0/2 | Not started | - |
