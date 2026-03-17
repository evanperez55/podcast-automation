# Fake Problems Podcast — Pipeline Upgrade

## What This Is

An automated podcast production pipeline for the "Fake Problems Podcast" — an edgy comedy show. The pipeline handles everything from raw audio to multi-platform distribution: transcription, AI content analysis, censorship, clip generation, video creation, and social media posting. This milestone is a comprehensive upgrade to make the output sound professional, the content match the show's voice, and the system cleaner and more capable.

## Core Value

One command produces professional-quality, platform-ready podcast content that sounds hand-edited and captures the show's edgy comedy voice — without manual intervention.

## Requirements

### Validated

- ✓ Download raw audio from Dropbox — existing
- ✓ Whisper transcription with word-level timestamps — existing
- ✓ AI content analysis (GPT-4) for censorship detection — existing
- ✓ Auto-censorship of names and words from configurable lists — existing
- ✓ Audio normalization — existing
- ✓ AI-selected clip extraction (3 best moments) — existing
- ✓ Clip approval workflow (interactive + auto-approve mode) — existing
- ✓ Subtitle/SRT generation for clips — existing
- ✓ Audiogram waveform videos for clips — existing
- ✓ Full episode video (static image + audio) for YouTube — existing
- ✓ Thumbnail generation with episode title overlay — existing
- ✓ MP3 conversion and Dropbox upload — existing
- ✓ RSS feed generation and update for Spotify — existing
- ✓ YouTube full episode + Shorts upload — existing
- ✓ Twitter thread posting (episode + clip links) — existing
- ✓ Blog post generation from transcript — existing
- ✓ Episode search index (FTS5) — existing
- ✓ Discord webhook notifications — existing
- ✓ Upload scheduling with configurable delays — existing
- ✓ Topic scraping and scoring engine — existing
- ✓ Analytics collection (YouTube + Twitter) — existing
- ✓ Pipeline state checkpointing for resume — existing
- ✓ --dry-run, --test, --auto-approve modes — existing

### Active

- [ ] Replace beep censorship with smooth audio ducking (volume dip, like radio)
- [ ] True LUFS normalization using ffmpeg-loudnorm (not dBFS approximation)
- [ ] Smarter clip detection — find actually funny/viral moments, not just topic changes
- [ ] AI content generation in edgy comedy voice (titles, descriptions, social posts, blog)
- [ ] Tech debt cleanup — break up 1700-line main.py, fix hardcoded values, resolve concerns report
- [ ] Marketing & growth features — SEO, cross-promotion, audience analytics, discoverability
- [ ] Expand to more platforms (Threads, Bluesky, etc.)
- [ ] Fix scheduled upload execution (currently a stub that marks uploads done without uploading)
- [ ] Wire Instagram upload into pipeline (currently manual-only)
- [ ] Fix openai SDK missing from requirements.txt
- [ ] Proper LUFS loudness normalization (ffmpeg-loudnorm filter)
- [ ] Move Google credentials to credentials/ directory
- [ ] Clean up naming artifacts (_parse_claude_response, duplicate config reads, inline re imports)

### Out of Scope

- Rewriting in another language — must stay Python
- Paid API additions beyond current stack (OpenAI, Dropbox) — keep costs low
- Live streaming features — this is a post-production pipeline
- Mobile app — CLI-driven is the workflow
- Video editing beyond static image + audio — no multi-camera, no B-roll

## Context

- Comedy podcast with edgy/dark humor tone — AI-generated content must match this voice
- Two hosts, weekly episodes (~70 minutes, ~700MB WAV)
- Current pipeline works end-to-end but output feels amateur (harsh beep censorship, generic AI text)
- main.py is 1700+ lines — the God Object problem. Orchestration, CLI, and business logic are tangled
- The codebase concerns report (.planning/codebase/CONCERNS.md) identifies 8+ tech debt items and several known bugs
- 279+ tests across 20 test files provide a solid safety net for refactoring
- Pipeline must keep working during upgrade — no breaking changes to current workflow

## Constraints

- **Cost**: No new paid APIs. Use existing OpenAI + Ollama + free platform APIs
- **Compatibility**: Current `python main.py ep29 --auto-approve` workflow must never break
- **Stack**: Python 3.12+, FFmpeg, existing dependencies. Add new packages only when necessary
- **Platform**: Windows 11, Git Bash, NVIDIA GPU + CUDA for Whisper

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Audio ducking over beep replacement | Smooth volume dip sounds professional, avoids jarring listener experience | — Pending |
| Edgy comedy voice for AI content | Show's identity is dark humor — generic content undermines the brand | — Pending |
| Tech debt first vs. features first | Clean foundation makes features easier, but ship them together | — Pending |
| Keep costs near zero | Podcast is passion project, not revenue-generating (yet) | — Pending |

---
*Last updated: 2026-03-16 after initialization*
