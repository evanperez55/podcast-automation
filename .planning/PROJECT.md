# Fake Problems Podcast — Automated Production Pipeline

## What This Is

An automated podcast production pipeline for the "Fake Problems Podcast" — an edgy comedy show. One command takes raw audio through transcription, AI content analysis with the show's comedy voice, smooth audio ducking censorship, LUFS-normalized mastering, chapter markers, clip generation scored by audio energy, and multi-platform distribution (YouTube, Spotify, Twitter, Instagram, TikTok). Shipped v1.0 with modular pipeline architecture.

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
- ✓ Smooth audio ducking censorship (volume dip instead of beep) — v1.0
- ✓ True LUFS normalization using ffmpeg-loudnorm EBU R128 — v1.0
- ✓ Edgy comedy voice persona in all AI-generated content — v1.0
- ✓ AudioClipScorer for energy-based clip selection — v1.0
- ✓ Hook-style captions matching show humor — v1.0
- ✓ Chapter markers in MP3 ID3 tags — v1.0
- ✓ Chapter markers in RSS feed (Podcasting 2.0) — v1.0
- ✓ Scheduled upload execution (real uploads, not stubs) — v1.0
- ✓ openai SDK in requirements.txt — v1.0
- ✓ Naming cleanup (_parse_claude_response, duplicate config reads, inline re) — v1.0
- ✓ Google credentials moved to credentials/ directory — v1.0
- ✓ main.py refactored to 134-line CLI shim with pipeline/ package — v1.0
- ✓ continue_episode.py eliminated (pipeline.run_distribute_only) — v1.0

### Active (v1.1 — Discoverability & Short-Form)

- [ ] Burned-in subtitle clips (big bold word-by-word) for YouTube Shorts, Instagram Reels, TikTok
- [ ] Episode webpages with full transcripts and SEO metadata on GitHub Pages
- [ ] Keyword extraction for SEO metadata

### Future

- Instagram Reels auto-upload via pipeline
- Bluesky posting via atproto SDK
- Threads posting via Meta API
- Filler word removal (ums/ahs) with configurable threshold — note: may impact comedic timing
- Public chapters.json URL (needs Dropbox upload enhancement)

### Out of Scope

- Rewriting in another language — must stay Python
- Paid API additions beyond current stack — keep costs low
- Live streaming features — post-production pipeline only
- Mobile app — CLI-driven is the workflow
- Video editing beyond static image + audio — no multi-camera, no B-roll
- Dynamic ad insertion — requires CDN hosting, incompatible with zero-cost constraint
- Plugin registry / dynamic step discovery — fixed pipeline doesn't benefit

## Context

- Comedy podcast with edgy/dark humor tone — AI-generated content must match this voice
- Two hosts, weekly episodes (~70 minutes, ~700MB WAV)
- v1.0 shipped: 23,810 LOC Python across 30+ modules, 333 tests, modular pipeline/ architecture
- Pipeline architecture: main.py (134 lines, CLI shim) → pipeline/runner.py (orchestrator) → pipeline/steps/ (5 step modules)
- 9 checkpoint keys for resume: transcribe, analyze, censor, normalize, create_clips, subtitles, convert_videos, convert_mp3, blog_post

## Constraints

- **Cost**: No new paid APIs. Use existing OpenAI + Ollama + free platform APIs
- **Compatibility**: `python main.py ep29 --auto-approve` workflow must never break
- **Stack**: Python 3.12+, FFmpeg, existing dependencies. Add new packages only when necessary
- **Platform**: Windows 11, Git Bash, NVIDIA GPU + CUDA for Whisper

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Audio ducking over beep replacement | Smooth volume dip sounds professional, avoids jarring listener experience | ✓ Good — -40dB fade with 50ms ramps |
| Edgy comedy voice for AI content | Show's identity is dark humor — generic content undermines the brand | ✓ Good — VOICE_PERSONA + few-shot examples |
| Tech debt first, then features | Clean foundation makes features easier to build | ✓ Good — Phase 1 bugs fixed before any features |
| Architecture refactor last | Refactoring stable code is safer than refactoring moving targets | ✓ Good — all feature phases complete first |
| Keep costs near zero | Podcast is passion project, not revenue-generating (yet) | ✓ Good — Ollama for local LLM, no new paid APIs |
| Mechanical extraction for refactor | Faithful code movement preserves behavior, minimize risk | ✓ Good — 333 tests passing, no regressions |

## Current Milestone: v1.1 Discoverability & Short-Form

**Goal:** Make clips go viral with burned-in subtitle vertical videos and drive organic search traffic with SEO-optimized episode webpages.

**Target features:**
- Burned-in subtitle clips (Hormozi-style word-by-word) for Shorts/Reels/TikTok
- Static episode webpages with full transcripts on GitHub Pages
- Keyword extraction for SEO metadata

---
*Last updated: 2026-03-18 after v1.1 milestone start*
