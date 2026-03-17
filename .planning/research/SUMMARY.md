# Project Research Summary

**Project:** Podcast Automation Pipeline Upgrade — Fake Problems Podcast
**Domain:** Automated podcast production and multi-platform distribution
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

This project upgrades an already-functional podcast automation pipeline (28 modules, 279 tests) across four dimensions: audio quality, content voice, distribution reach, and code architecture. The existing stack is sound and should not be replaced — only extended. The recommended approach is to attack problems in dependency order: fix the audio chain first (ducking + LUFS normalization), then improve content quality (comedy voice, smarter clips), then close distribution gaps (Instagram, Threads, Bluesky, scheduled uploads), then refactor `main.py` as the final structural improvement. This order ensures every phase ships usable improvements rather than accumulating risk.

The pipeline has two critical structural problems that undermine everything else. First, the `main.py` God Object (1,802 lines, zero test coverage) makes it impossible to test orchestration logic in isolation, and the closely related `continue_episode.py` duplicates its upload logic outside of test coverage. Second, the scheduled upload executor is a silent stub — it marks uploads as complete without executing them. Both problems must be treated as blockers, but they should be fixed after audio and distribution improvements rather than first, to avoid refactoring code while also changing its behavior.

The main risks are Whisper timestamp drift causing mis-censored audio, `ffmpeg-loudnorm` silently falling back to AGC mode, and the checkpoint resume system breaking during the `main.py` refactor if key names are not frozen before extraction begins. All three risks have clear prevention strategies documented in research. The Threads platform integration carries additional uncertainty due to Meta's app review process — the fallback is direct REST calls via `requests`, avoiding the `pythreads` library entirely if approval is delayed.

## Key Findings

### Recommended Stack

The existing stack (Python 3.12+, Whisper/WhisperX, pydub + FFmpeg, Ollama/Llama 3.2, tweepy, google-api-python-client) stays unchanged. Six additions are required. `ffmpeg-normalize 1.37.3` handles true EBU R128 two-pass loudness normalization without requiring custom FFmpeg pipeline code. `librosa 0.11.0` provides audio feature extraction (RMS energy, onset detection) for smarter clip selection. `atproto 0.0.65` is the officially endorsed AT Protocol SDK for Bluesky. `keybert 0.9.0` adds deterministic BERT-based keyword extraction for SEO, which is more reliable than prompting the LLM for keywords. Audio ducking (censorship) requires no new library — pydub's `.fade()` and `.apply_gain()` methods plus WhisperX word timestamps are sufficient. The `main.py` refactor is a code organization change, not a library addition.

**Core new technologies:**
- `ffmpeg-normalize 1.37.3`: LUFS normalization — handles two-pass loudnorm correctly, exposes normalization_type for AGC detection
- `librosa 0.11.0`: audio feature extraction — RMS energy and onset density for viral clip scoring
- `atproto 0.0.65`: Bluesky posting — official AT Protocol SDK, mirrors tweepy pattern
- `pythreads 0.2.1`: Threads posting — wraps Meta Graph API (beta; fallback is direct `requests` calls)
- `keybert 0.9.0`: keyword extraction for SEO — deterministic, BERT-based, more reliable than LLM prompts
- `openai>=1.0.0`: fix missing requirements.txt entry — currently used in blog_generator.py but untracked

### Expected Features

**Must have (table stakes):**
- Audio ducking censorship — replace beep.wav with -15dB volume dip + fade; broadcast standard, beep sounds amateur
- True LUFS normalization — Spotify targets -14 LUFS, Apple targets -16 LUFS; current dBFS approximation produces platform-adjusted inconsistency
- Chapter markers in MP3 + RSS — Apple Podcasts now auto-generates chapters; listeners expect navigation
- Burned-in subtitle Shorts/Reels — 58% of podcast discovery from short-form video; audiogram-only output is insufficient
- Instagram Reels wired into pipeline — currently a manual stub; top-3 discovery platform
- Functional scheduled uploads — currently silently marks uploads done without executing; silent production bug

**Should have (differentiators):**
- Edgy comedy voice for AI-generated content — generic AI text undermines brand identity; requires few-shot prompt engineering
- Smart viral clip detection — audio energy + transcript analysis identifies punchlines, not just topic changes
- Threads + Bluesky posting — growing platforms with easy integration; early presence compounds
- Clip virality scoring — AI pre-screening of clips before selection using Ollama
- Filler word removal — cleaner audio via Whisper word timestamps; moderate risk of over-processing hosts' natural speech
- Cross-episode topic clustering — "listen next" recommendations using existing FTS5 search index

**Defer (v2+):**
- Episode webpage with full transcript — requires hosting infrastructure decision; high SEO value but high complexity
- Email newsletter generation — requires ESP integration decision (Beehiiv/Substack)
- LinkedIn posting — easy win, defer only due to lower priority vs. fixing existing distribution gaps
- Chapter-level analytics — requires chapters feature first; valuable once chapters ship

### Architecture Approach

The recommended architecture is a Modular Orchestrator: keep the monolith (no microservices, no task queue), but surgically extract `main.py`'s orchestration into three bounded layers — `cli.py` (argument parsing), `pipeline.py` (step sequencing + checkpoint wrapping), and `pipeline/steps/*.py` (one file per step group). Component classes (`audio_processor.py`, `transcription.py`, etc.) are already correctly decomposed and should not be touched. A `PipelineContext` dataclass carries all inter-step data, replacing the current implicit `analysis` dict handoff. Checkpoint logic moves entirely into the orchestrator wrapper, making step functions checkpoint-unaware and trivially testable.

**Major components (new):**
1. `pipeline/context.py` — `PipelineContext` dataclass; single data handoff object for all steps
2. `pipeline.py` — step sequencer; owns checkpoint wrapping, test/dry-run guards, component initialization
3. `pipeline/steps/distribute.py` — extract `_upload_*` methods; eliminates `continue_episode.py` duplication
4. `pipeline/steps/audio.py`, `video.py`, `analysis.py`, `ingest.py` — one file per step group
5. `cli.py` — thin argument parser delegating to `pipeline.py`

### Critical Pitfalls

1. **Whisper timestamp drift causes mis-censored audio** — add 150ms pre / 75ms post PAD_MS buffer to every censor window; always route through WhisperX alignment (never single-pass Whisper); export 5-second QA clips around each mute point in --test mode
2. **ffmpeg-loudnorm silent AGC fallback** — parse `normalization_type` from first-pass JSON after every normalization; raise a warning and optionally abort if value equals `"dynamic"`; target -16 LUFS / -2 dBTP for podcast platforms
3. **main.py refactor breaks checkpoint resume** — freeze checkpoint key names before refactoring begins; write a regression test asserting key names match a known-good list; add `schema_version` field to checkpoint JSON
4. **Scheduled upload stub marks items done without uploading** — replace stub with `NotImplementedError` guard immediately; do not ship new scheduled platforms until real executors are wired
5. **LLM voice inconsistency degrades across episodes** — store 3-5 gold-standard examples in `config.py` or `voice_examples.py`; include as few-shot examples in every content generation prompt; lower temperature to 0.7 for social copy

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Tech Debt and Prerequisites
**Rationale:** The scheduled upload stub (Pitfall 4) and missing `openai` dependency (Pitfall 11) are silent production bugs that affect everything downstream. Fixing them first ensures no other phase silently fails. This phase has no risky behavior changes — pure fixes and guards.
**Delivers:** Reliable foundation — scheduled uploads raise errors instead of silently failing; fresh environments install correctly; `continue_episode.py` covered by smoke tests
**Addresses:** Table stakes fix (scheduled uploads), dependency hygiene
**Avoids:** Pitfall 4 (silent upload stub), Pitfall 11 (missing openai SDK), Pitfall 9 (continue_episode.py divergence)

### Phase 2: Audio Quality
**Rationale:** Audio quality issues are audible to every listener and are the table-stakes fixes with the clearest ROI. LUFS normalization and audio ducking are independent of each other and of the architecture refactor. Shipping them early validates the new library additions before the pipeline refactor makes testing harder.
**Delivers:** Professional-sounding output — smooth censorship ducking, EBU R128 compliant loudness levels
**Uses:** `ffmpeg-normalize 1.37.3`, pydub `.fade()` / `.apply_gain()`, WhisperX word timestamps
**Implements:** Upgrades to `audio_processor.py` only; no new modules
**Avoids:** Pitfall 1 (timestamp drift — PAD_MS buffer required), Pitfall 2 (AGC fallback — normalization_type check required), Pitfall 5 (attack/release timing — use 30ms/50ms broadcast standard)

### Phase 3: Content Voice and Smart Clips
**Rationale:** Once audio is clean, content quality is the next highest-impact lever. Edgy comedy voice transforms all downstream AI-generated content (social captions, blog posts, clip descriptions). Smart clip detection requires `librosa` and directly feeds the distribution phases — better clips = better Shorts/Reels.
**Delivers:** Brand-consistent AI content; clips selected for comedy timing and energy, not just topic changes
**Uses:** `librosa 0.11.0` (audio features), `keybert 0.9.0` (SEO keywords), Ollama (clip virality scoring)
**Avoids:** Pitfall 8 (LLM voice inconsistency — few-shot examples required before this phase ships)

### Phase 4: Distribution Expansion
**Rationale:** With good audio and content voice, closing distribution gaps delivers maximum reach. This phase groups Instagram (wiring an existing stub), Threads/Bluesky (new platforms), and burned-in subtitle Shorts/Reels (new video format) because they all depend on Phase 2 clip quality and share the same testing surface (platform uploaders).
**Delivers:** Full multi-platform distribution — Instagram Reels, Threads, Bluesky, vertical video with burned-in subtitles, scheduler actually executing uploads
**Uses:** `atproto 0.0.65`, `pythreads 0.2.1` (or direct requests fallback), FFmpeg subtitle burn-in
**Avoids:** Pitfall 6 (Instagram API version rot — move to v22.0 via env var), Pitfall 7 (Twitter URL length edge cases — fix during this phase), Pitfall 12 (TikTok token expiry — validate tokens at pipeline start)

### Phase 5: main.py Architecture Refactor
**Rationale:** Refactoring after feature work rather than before means the refactor extracts stable, tested code rather than a moving target. The build order within this phase is dictated by risk: `distribute.py` first (most isolated, eliminates continue_episode.py duplication), then `video.py`, `audio.py`, `analysis.py`, `ingest.py` (highest risk, Whisper model loading), then orchestrator wiring.
**Delivers:** Testable pipeline orchestration; `main.py` reduced to thin CLI shim; `continue_episode.py` replaced by `pipeline.run_distribute_only()`; each step independently testable
**Implements:** Full Modular Orchestrator pattern — `PipelineContext`, `ComponentSet`, `pipeline/steps/*.py`
**Avoids:** Pitfall 3 (checkpoint key breakage — freeze key names, write regression test before any extraction)

### Phase 6: Chapter Markers and SEO
**Rationale:** Chapter markers depend on stable pipeline output (Phase 5) and unlock chapter-level analytics and episode webpage navigation. Deferred because infrastructure for episode webpages (hosting decision) must be made separately.
**Delivers:** Chapter navigation in Apple Podcasts, chapter retention data in YouTube Analytics, RSS `<podcast:chapters>` tag
**Uses:** `mutagen` (ID3 chapter tags), WhisperX timestamps already available
**Note:** Episode webpage (full SEO payoff) requires a separate hosting decision — treat as a sub-phase or separate project

### Phase Ordering Rationale

- Phases 1-2 fix existing production failures before adding new behavior; any other order risks shipping new features onto broken foundations
- Phase 3 before Phase 4 ensures distribution platforms receive high-quality clips and voice-consistent content rather than requiring re-generation after voice work ships
- Phase 5 (refactor) deliberately comes after feature phases — refactoring stable code is safer than refactoring code under active development; the God Object problem is painful but not blocking feature delivery
- Phase 6 is last because it depends on stable pipeline output AND an external infrastructure decision (hosting)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Distribution Expansion):** Threads API requires Meta app review for publishing permissions — verify approval status before planning sprint; fallback plan needed if approval is delayed
- **Phase 5 (Architecture Refactor):** The `analysis` dict schema (primary cross-step data carrier) must be fully documented before `pipeline/steps/analysis.py` extraction begins; schema changes propagate to all downstream steps
- **Phase 6 (Chapter Markers / SEO):** Episode webpage hosting requires an infrastructure decision (static site? GitHub Pages? existing host?) that is not resolved in current research

Phases with standard patterns (skip research-phase):
- **Phase 1 (Tech Debt):** All fixes are well-scoped; no research needed
- **Phase 2 (Audio Quality):** `ffmpeg-normalize` two-pass pattern and pydub ducking are well-documented; implementation is mechanical
- **Phase 3 (Content Voice):** Few-shot prompt engineering is standard; `librosa` feature extraction is well-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified on PyPI with confirmed versions and release dates; rejected alternatives explicitly documented |
| Features | MEDIUM | Table stakes verified via official Apple/Spotify sources; differentiator rankings based on industry blogs and single-source stats (email retention stat LOW confidence) |
| Architecture | HIGH | Refactoring patterns sourced from Refactoring.Guru (official); PipelineContext pattern matches established Python pipeline frameworks; build order derived directly from codebase dependency graph |
| Pitfalls | HIGH | Critical pitfalls grounded in WhisperX GitHub issues, official FFmpeg docs, and direct codebase audit of CONCERNS.md; not inferred |

**Overall confidence:** HIGH

### Gaps to Address

- **Threads app review status:** Research confirms the API exists and `pythreads` wraps it, but does not confirm whether the Fake Problems Podcast Meta developer account has publishing permissions approved. Must be verified before Phase 4 planning begins; keep direct `requests` fallback ready.
- **Episode webpage hosting:** No hosting decision has been made. Phase 6 SEO work (episode webpages) cannot be planned until the hosting platform is selected. Treat as a separate decision gate.
- **WhisperX upgrade path:** `whisperx==3.1.6` pins `torch==2.1.0`. The safe upgrade path to PyTorch 2.2+ with newer WhisperX needs testing on the production GPU before Phase 2 or 5 touches transcription code.
- **Filler word removal risk calibration:** Research flags this as moderate risk for altering natural speech patterns. Needs real-episode testing with adjustable aggressiveness threshold before production deployment. Recommend treating as a separate opt-in flag, not default behavior.

## Sources

### Primary (HIGH confidence)
- [ffmpeg-normalize PyPI](https://pypi.org/project/ffmpeg-normalize/) — version 1.37.3, EBU R128 two-pass
- [librosa PyPI](https://pypi.org/project/librosa/) — version 0.11.0, audio feature extraction
- [atproto PyPI](https://pypi.org/project/atproto/) — version 0.0.65, AT Protocol official SDK
- [keybert PyPI](https://pypi.org/project/keybert/) — version 0.9.0, BERT keyword extraction
- [Apple Podcasts chapters — official](https://podcasters.apple.com/support/5482-using-chapters-on-apple-podcasts)
- [WhisperX timestamp accuracy — issue #1247](https://github.com/m-bain/whisperX/issues/1247)
- [Instagram Graph API changelog](https://developers.facebook.com/docs/instagram-platform/changelog/)
- [Extract Class — Refactoring.Guru](https://refactoring.guru/extract-class)
- [CrisperWhisper: Accurate Timestamps](https://arxiv.org/html/2408.16589v1) — Whisper timestamp limitations
- Project codebase audit (.planning/codebase/CONCERNS.md)

### Secondary (MEDIUM confidence)
- [pythreads PyPI](https://pypi.org/project/pythreads/) — version 0.2.1, Meta Threads wrapper (beta)
- [ffmpeg loudnorm filter — author's blog](http://k.ylo.ph/2016/04/04/loudnorm.html) — two-pass loudnorm mechanics
- [State of Video Podcasts 2025](https://www.sweetfishmedia.com/blog/the-2025-state-of-video-podcasts) — short-form discovery stats
- [Bluesky, Threads, X Landscape 2025](https://circleboom.com/blog/is-bluesky-or-threads-more-popular-in-2025/) — platform growth data
- [7 Podcast SEO Best Practices 2025](https://www.fame.so/post/7-podcast-seo-best-practices-for-explosive-growth-in-2025)

### Tertiary (LOW confidence)
- [Email Marketing Boosts Retention 22%](https://elasticemail.com/blog/how-to-promote-your-podcast-with-email-marketing) — single source, unverified stat; treat as directional only

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
