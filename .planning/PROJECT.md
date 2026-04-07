# Podcast Automation — Multi-Client Production Pipeline

## What This Is

A multi-client automated podcast production pipeline that works across genres. One command takes raw audio (from Dropbox or any public RSS feed) through transcription, AI content analysis with per-client voice persona, genre-aware compliance checking, smooth audio ducking censorship, LUFS-normalized mastering, chapter markers, content-aware clip generation, Hormozi-style subtitle clips, SEO-optimized episode webpages, engagement-optimized scheduling, and multi-platform distribution. Proven with comedy, true crime, and business/interview genres. Includes a `package-demo` command for assembling sales demo folders.

## Core Value

One command produces professional-quality, platform-ready podcast content with genre-appropriate voice and tone — without manual intervention.

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
- ✓ Burned-in subtitle clips (Hormozi-style word-by-word) for YouTube Shorts — v1.1
- ✓ Episode webpages with full transcripts, JSON-LD, SEO on GitHub Pages — v1.1
- ✓ YAKE keyword extraction for SEO metadata — v1.1
- ✓ Content compliance checker (GPT-4o) flagging YouTube guideline violations — v1.1
- ✓ Auto-muting flagged segments via censor_timestamps merge — v1.1
- ✓ Upload safety gate with --force override — v1.1
- ✓ Platform ID capture at upload time (quota-safe analytics) — v1.2
- ✓ Engagement history accumulation with upsert logic — v1.2
- ✓ Twitter impression null guard for free tier — v1.2
- ✓ Stub uploader detection (.functional flags) — v1.2
- ✓ Hashtag auto-injection into Twitter posts — v1.2
- ✓ Spearman category ranking with comedy voice constraint — v1.2
- ✓ GPT-4o content generation with engagement history context — v1.2
- ✓ Smart scheduling with per-platform optimal posting windows — v1.2
- ✓ Backfill-ids CLI command for existing episodes — v1.2
- ✓ topic_scorer episode number bug fix — v1.2
- ✓ Content calendar planner for bi-weekly episode + clip distribution — v1.3
- ✓ Multi-client YAML configs with output isolation — post-v1.3
- ✓ Per-client voice persona, blog voice, topic scoring profiles — post-v1.3
- ✓ Per-client RSS metadata and video input support — post-v1.3
- ✓ CLI: init-client, setup-client, validate-client, status, list-clients, process-all — post-v1.3
- ✓ Config hardening — no FP defaults leak to non-FP clients (required field validation) — v1.4
- ✓ RSS episode fetcher via feedparser — process any public podcast without Dropbox — v1.4
- ✓ Genre-aware clip selection (content vs energy mode) — v1.4
- ✓ Genre-aware compliance checking (strict/standard/permissive) — v1.4
- ✓ Real-world validation with true crime and business/interview genres — v1.4
- ✓ Demo packager — package-demo command for self-contained sales demos — v1.4
- ✓ Raw audio snapshot before censorship for before/after comparison — v1.4
- ✓ PyTorch CUDA 12.4 configured for GPU acceleration — v1.4

### Active (v1.6 — Production Quality & Operations)

- [ ] Iteratively improve demo output quality (clip selection, subtitle styling, thumbnails)
- [ ] Client onboarding documentation (ONBOARDING.md checklist)
- [x] Pipeline monitoring and alerting (Discord webhook on errors) — Phase 23
- [ ] Tune AudioClipScorer weights against engagement analytics data

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

- Originally built for Fake Problems Podcast (edgy comedy), now multi-client across genres
- v1.4 shipped: ~36,000 LOC Python across 40+ modules, 662 tests, modular pipeline/ architecture
- Pipeline architecture: main.py (CLI shim) → pipeline/runner.py (orchestrator) → pipeline/steps/ (5 step modules)
- Pipeline step order: 1 Download (Dropbox/RSS) → 2 Transcribe → 3 Analyze → 3.5 Topic → 3.6 Compliance → 3.9 Raw Snapshot → 4 Censor → 4.5 Normalize → 5 Clips → 5.1 Approval → 5.4 Subtitles → 5.5 Video → 5.6 Thumbnail → 6 MP3 → 7 Dropbox → 7.5 RSS → 8 Social → 8.5 Blog → 8.6 Webpage → 9 Search
- Multi-client: YAML configs in clients/<name>.yaml, output isolation in output/<client>/
- Proven genres: comedy (Fake Problems), true crime (Casefile), business/interview (How I Built This)
- GPU: NVIDIA RTX 3070 with CUDA 12.4, PyTorch 2.6.0+cu124

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
| pysubs2 ASS for subtitle rendering | Native SSA format with per-word styling avoids frame-by-frame rendering | ✓ Good — fast, clean output, no MoviePy dependency |
| YAKE over KeyBERT for keywords | Zero external model download, unsupervised, works on show_notes not raw transcript | ✓ Good — lightweight, adequate quality |
| PyGithub upsert for GitHub Pages | No git binary needed, API-based deploy with SHA tracking | ✓ Good — clean upsert, graceful skip on missing token |
| GPT-4o at temp=0.1 for compliance | Deterministic classification, not creative generation | ✓ Good — consistent flagging |
| Merge flagged segments into censor_timestamps | Reuse existing AudioProcessor duck-fade, zero new FFmpeg code | ✓ Good — elegant reuse |
| Comedy-aware compliance prompt | Dark humor and profanity are NOT violations; only genuine hate speech and dangerous misinformation | ✓ Good — avoids over-flagging |
| scipy Spearman over ML/scikit-learn | Dataset too small (~30 episodes) for ML; correlations are statistically appropriate | ✓ Good — simple, interpretable, no overfitting |
| Comedy voice as binary constraint | Edgy content categories (shocking_news, absurd_hypothetical) can never receive negative scores | ✓ Good — optimizer cannot erode the show's identity |
| 15-episode confidence gate | Below threshold, optimizer returns nothing — pipeline uses fixed delays | ✓ Good — prevents noisy early recommendations |
| Store video_id at upload time | Avoids 100-unit YouTube search API call per episode during analytics | ✓ Good — quota-safe from day one |
| feedparser for RSS ingest | Handles all RSS/Atom variants + iTunes extensions; hand-rolling XML would hit namespace edge cases | ✓ Good — one dependency, robust parsing |
| Skip all uploaders for non-dropbox clients | FP credentials in env vars and credentials/ would leak to new clients | ✓ Good — clean isolation, per-client opt-in later |
| Genre-aware compliance via COMPLIANCE_STYLE | True crime needs strict flagging; comedy needs permissive; one-size-fits-all was wrong | ✓ Good — Casefile got 12 flags, HIBT got 0 |
| Content-mode clip selection | RMS energy scoring is flat for non-comedy (measured delivery); content criteria needed | ✓ Good — interview clips selected for insight, not volume |
| rss_source YAML key (not rss) | Existing `rss` key maps to output feed metadata; collision risk | ✓ Good — clean separation of input vs output config |
| PyTorch CUDA index in pyproject.toml | uv sync was installing CPU-only build; needed explicit cu124 index | ✓ Good — 7 min transcription vs 30+ on CPU |

## Current Milestone: v1.6 Production Quality & Operations

**Goal:** Make the pipeline operationally ready for paying clients — polish output quality, add monitoring, and reduce per-client overhead.

**Target features:**
- Demo output polish: iteratively improve clip selection, subtitle styling, and thumbnail quality using autoresearch
- Client onboarding documentation: ONBOARDING.md checklist for smooth prospect-to-client handoff
- Pipeline monitoring & alerting: Discord webhook on pipeline errors so failures don't go silent with multiple clients
- Clip selection optimization: tune AudioClipScorer weights against engagement analytics data using autoresearch

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-07 after Phase 23 completion*
