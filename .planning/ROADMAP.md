# Roadmap: Fake Problems Podcast — Pipeline Upgrade

## Overview

This milestone upgrades an already-functional 28-module pipeline across four dimensions: silent bug elimination, professional audio quality, brand-consistent AI content, audience navigation features, and a sustainable codebase architecture. Phases run in dependency order — bugs fixed before features, audio clean before content generated, features stable before architecture extracted. Every phase ships something immediately usable.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundations** - Eliminate silent production bugs and dependency hygiene issues before any feature work
- [x] **Phase 2: Audio Quality** - Replace beep censorship with audio ducking and normalize to broadcast LUFS standards (completed 2026-03-17)
- [x] **Phase 3: Content Voice and Clips** - Make all AI-generated content sound like the show; select clips for comedy timing (completed 2026-03-17)
- [ ] **Phase 4: Chapter Markers** - Add navigable chapter markers to MP3 files and RSS feed
- [ ] **Phase 5: Architecture Refactor** - Split main.py God Object into testable pipeline modules

## Phase Details

### Phase 1: Foundations
**Goal**: Silent production bugs eliminated and dependency hygiene restored so all downstream phases build on a reliable base
**Depends on**: Nothing (first phase)
**Requirements**: DEBT-02, DEBT-03, DEBT-04, DIST-01
**Success Criteria** (what must be TRUE):
  1. Running `pip install -r requirements.txt` in a fresh environment installs openai without error
  2. Attempting a scheduled upload raises a clear error instead of silently marking the upload complete
  3. Google credential files live in credentials/ directory and no code references the old project-root paths
  4. _parse_claude_response is renamed, duplicate config reads are eliminated, and inline re imports are moved to module top
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Dependency and naming hygiene (openai in requirements, rename _parse_claude_response, consolidate scheduler config reads, move inline re imports)
- [x] 01-02-PLAN.md — Fix scheduled upload stub (replace no-op with real uploader dispatch, add mark_failed, Discord notification on failure)
- [x] 01-03-PLAN.md — Google credential file migration (move files to credentials/, update path references, add tests)

### Phase 2: Audio Quality
**Goal**: Episodes sound professionally mastered — censored moments are smooth volume dips and loudness meets broadcast platform standards
**Depends on**: Phase 1
**Requirements**: AUDIO-01, AUDIO-02, AUDIO-03
**Success Criteria** (what must be TRUE):
  1. Censored words are replaced by a smooth volume fade to near-silence rather than an audible beep tone
  2. A processed episode measures between -15 and -17 LUFS on any reference loudness meter
  3. The pipeline log for each episode records the measured LUFS, gain applied, and LRA values after normalization
  4. Normalization raises a warning if ffmpeg-loudnorm falls back to AGC mode instead of true two-pass EBU R128
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — TDD scaffold: write failing tests for audio ducking (TestAudioDucking) and LUFS normalization (TestNormalizeAudio rewrite)
- [ ] 02-02-PLAN.md — Implement audio ducking: add _apply_duck_segment(), rewrite apply_censorship() loop (AUDIO-01)
- [ ] 02-03-PLAN.md — Implement LUFS normalization: rewrite normalize_audio() with two-pass FFmpeg loudnorm, log metadata, warn on AGC fallback (AUDIO-02, AUDIO-03)

### Phase 3: Content Voice and Clips
**Goal**: All AI-generated text sounds like the show's edgy comedy voice and clips are selected for virality, not just topic boundaries
**Depends on**: Phase 2
**Requirements**: VOICE-01, VOICE-02, VOICE-03
**Success Criteria** (what must be TRUE):
  1. Generated titles, descriptions, social posts, and blog text use the show's edgy comedy tone — a human reader can distinguish them from generic AI output
  2. Clip selection scores moments by audio energy and laughter patterns; at least one selected clip corresponds to an obvious punchline rather than a topic transition
  3. Each generated clip includes a hook-style caption that matches the show's humor rather than a neutral transcript excerpt
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — TDD scaffold: write failing tests for voice persona (VOICE-01, VOICE-03) and audio clip scoring (VOICE-02)
- [ ] 03-02-PLAN.md — Inject voice persona and few-shot examples into content_editor and blog_generator (VOICE-01, VOICE-03)
- [ ] 03-03-PLAN.md — Implement AudioClipScorer with pydub RMS windowing and wire into analyze_content() (VOICE-02)

### Phase 4: Chapter Markers
**Goal**: Listeners can navigate episodes by chapter in Apple Podcasts and compatible apps via embedded MP3 markers and RSS chapter tags
**Depends on**: Phase 3
**Requirements**: VOICE-04, VOICE-05
**Success Criteria** (what must be TRUE):
  1. A processed MP3 file contains ID3 chapter tags that are readable by a tool such as mutagen or mp3tag
  2. Apple Podcasts (or a compatible player) displays chapter navigation for a processed episode
  3. The RSS feed includes a <podcast:chapters> tag or equivalent chapter entries for each episode
**Plans**: 2 plans

Plans:
- [ ] 04-01-PLAN.md — TDD scaffold: failing tests for ChapterGenerator ID3 embedding and RSS podcast:chapters tag; add mutagen to requirements.txt (VOICE-04, VOICE-05)
- [ ] 04-02-PLAN.md — Implement ChapterGenerator, update rss_feed_generator.py with podcast:chapters support, wire both into main.py pipeline (VOICE-04, VOICE-05)

### Phase 5: Architecture Refactor
**Goal**: main.py is reduced to a thin CLI shim; pipeline orchestration lives in testable modules; continue_episode.py is eliminated
**Depends on**: Phase 4
**Requirements**: DEBT-01, DEBT-05
**Success Criteria** (what must be TRUE):
  1. main.py is under 150 lines and contains only argument parsing and delegation to pipeline.py
  2. Each pipeline step group (ingest, audio, analysis, video, distribute) has its own file under pipeline/steps/ and is independently importable
  3. Running `python main.py ep29 --auto-approve` produces identical output to before the refactor (no behavior regression)
  4. continue_episode.py no longer exists; its functionality is available via pipeline.run_distribute_only() or equivalent
  5. Checkpoint key names are covered by a regression test asserting they match a known-good list
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations | 3/3 | Complete    | 2026-03-17 |
| 2. Audio Quality | 3/3 | Complete    | 2026-03-17 |
| 3. Content Voice and Clips | 2/3 | Complete    | 2026-03-17 |
| 4. Chapter Markers | 1/2 | In Progress|  |
| 5. Architecture Refactor | 0/TBD | Not started | - |
