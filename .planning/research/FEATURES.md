# Feature Landscape

**Domain:** Automated podcast production and multi-platform distribution
**Researched:** 2026-03-16

## Context: What the Pipeline Already Has

The following are already implemented and NOT targets for this research:
- Whisper transcription with word-level timestamps
- AI content analysis and auto-censorship
- Audio normalization (dBFS approximation)
- AI-selected clip extraction (3 clips per episode)
- Subtitle/SRT generation for clips
- Audiogram waveform videos
- Full episode video (static image + audio) for YouTube
- Thumbnail generation with episode title overlay
- MP3 + Dropbox upload
- RSS feed generation (Apple/Spotify iTunes namespace)
- YouTube full episode + Shorts upload
- Twitter thread posting
- Blog post generation from transcript
- Episode FTS5 search index
- Discord webhook notifications
- Upload scheduling
- Topic scraping and scoring engine
- YouTube + Twitter analytics collection
- Pipeline state checkpointing

## Table Stakes

Features listeners and hosts expect from a professional podcast. Missing = product feels amateur or breaks distribution.

| Feature | Why Expected | Complexity | Currently | Notes |
|---------|--------------|------------|-----------|-------|
| Smooth audio ducking (not beep) censorship | Beep censorship sounds jarring and amateur; radio standard is volume dip | Medium | Beep (existing) | Replace harsh beep with -15dB volume duck + fade in/out |
| True LUFS loudness normalization | Spotify, Apple Podcasts, YouTube all normalize to target LUFS; incorrect levels get auto-adjusted and sound wrong | Medium | dBFS approximation | ffmpeg-loudnorm filter; -14 LUFS for Spotify, -16 for Apple |
| Chapter markers in MP3 + RSS | Apple Podcasts now auto-generates chapters; listeners expect navigation; 2025 standard | Medium | None | ID3 chapter tags (mutagen) + `<podcast:chapters>` RSS tag |
| Episode webpage with full transcript + show notes | Google and podcast platforms now index transcripts; SEO requires dedicated episode page | High | Blog post only | Dedicated URL per episode; structured show notes with timestamps |
| Shorts/Reels with auto-generated subtitles burned in | 58% of podcast discovery comes from short-form video; burned-in subs are expected for social clips | Medium | Audiogram only | Vertical crop + burned subtitle overlays via FFmpeg |
| Instagram Reels actually wired into pipeline | Instagram is a top-3 discovery platform; currently manual-only | Medium | Manual stub | Wire instagram_uploader.py into main pipeline |
| Functional scheduled uploads | Scheduler currently marks uploads done without executing them — a silent bug | Medium | Broken stub | Fix to actually queue and execute uploads at scheduled times |

## Differentiators

Features that set the show apart from generic automated podcasts. Not universally expected, but create real competitive advantage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Edgy comedy voice for all AI-generated content | Generic AI text undermines brand; voice-matched content sounds hand-crafted | Medium | System prompt engineering; few-shot examples from existing episodes |
| Smart viral clip detection | Most clip tools find topic changes, not funny/viral moments; comedy timing matters | High | Train on engagement signals: laugh cues, escalating energy, punchline patterns |
| Threads + Bluesky posting | Both platforms growing fast (275M Threads users); early presence builds audience before competition arrives | Low | Threads API + Bluesky AT Protocol; both support simple text+image posts |
| LinkedIn posting for B2B discovery | LinkedIn high-reach for comedy tech/culture topics; underused by comedy podcasts | Low | Simple text post; no video required for initial cut |
| Email newsletter generation per episode | Email has 22% higher retention than social; Beehiiv/Substack integrate with RSS | Medium | Generate newsletter-formatted content from transcript; integrate with existing blog generator |
| SEO-optimized episode pages with schema markup | Podcast schema in HTML enables rich search results (embedded player, episode list); transcripts are indexed by Google | High | Requires hosting; schema markup generation is straightforward once page exists |
| Chapter-level analytics (where listeners drop off) | YouTube Studio provides per-chapter retention graphs when chapters are set; informs future content decisions | Low | Requires chapters feature first; YouTube Analytics API already integrated |
| Clip virality scoring (predict before posting) | AI analysis of transcript segment for humor density, quotability, shareability before selecting clips | Medium | Feeds into smart clip detection; uses existing Ollama LLM |
| Filler word removal | AI removal of "um", "uh", "like" makes hosts sound sharper; expected from professional shows | Medium | Cleanvoice/Auphonic approach; can implement via Whisper word timestamps + audio editing |
| Cross-episode topic clustering | Surface related episodes automatically; improve search and "listen next" recommendations | Medium | Extends existing FTS5 search index; TF-IDF or embedding similarity |

## Anti-Features

Features to explicitly NOT build, despite them being common in the ecosystem.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Dynamic ad insertion (DAI) | Requires hosting infrastructure, CDN integration, and ad network relationships; $5B market but not relevant to a passion project podcast | Use host-read sponsorships if monetization comes; read ads in recording |
| Multi-user collaboration / team permissions | This is a personal pipeline for two hosts; collaboration features add auth complexity, conflict resolution, and UI work | Config file + env vars for any per-user settings |
| Web-based dashboard / admin UI | CLI-driven is the stated architecture; a web UI is a separate project | Improve CLI output quality and Discord notifications instead |
| Listener subscription management | Substack/Beehiiv handle this; building a custom email list system is high complexity | Integrate with an existing ESP via their API or SMTP |
| Video recording / live streaming features | Out of scope per PROJECT.md; post-production only | — |
| In-browser audio editor | This is a $20M engineering effort (Descript); not appropriate for a single-developer pipeline | Accept that some edits require manual intervention |
| Paid API additions (Anthropic, ElevenLabs, etc.) | PROJECT.md constraint: keep costs near zero; existing OpenAI + Ollama stack is sufficient | Maximize Ollama quality through prompt engineering first |
| Podcast network / cross-show management | Single-show pipeline; multi-show management adds config complexity with zero immediate benefit | Use ENV vars to support different shows if needed |
| Automatic guest booking / CRM | Out of scope; this is post-recording automation | — |
| Custom analytics dashboard (rebuild metrics UI) | YouTube Studio and Twitter Analytics provide richer data than anything we'd build | Pull key metrics via API, report them in Discord notifications |

## Feature Dependencies

```
Audio ducking (smooth censorship)
  └── No hard dependencies; replaces beep.wav logic in audio_processor.py

True LUFS normalization
  └── No hard dependencies; replaces existing normalization in audio_processor.py

Chapter markers
  └── Requires: Whisper word-level timestamps (already available)
  └── Enables: Chapter-level analytics (YouTube)
  └── Enables: Chapter navigation in episode webpage

Episode webpage
  └── Requires: Blog post generation (already available)
  └── Requires: Full transcript (already available)
  └── Requires: Chapter markers (for navigation)
  └── Enables: SEO schema markup
  └── Enables: SEO-indexed transcripts

Edgy comedy voice
  └── Requires: Existing blog/social generation modules
  └── Enables: Better clips (voice-matched captions)
  └── Enables: Better email newsletter

Smart viral clip detection
  └── Requires: Clip virality scoring (can be same feature)
  └── Requires: Whisper word-level timestamps (already available)
  └── Requires: Filler word removal (improves clip quality)
  └── Currently: clip logic in content_editor.py

Filler word removal
  └── Requires: Whisper word-level timestamps (already available)
  └── Enables: Cleaner clips
  └── Enables: Better audio quality overall

Shorts/Reels with burned-in subtitles
  └── Requires: Clip extraction (already available)
  └── Requires: SRT/subtitle data (already available)
  └── Enables: Instagram Reels pipeline

Instagram Reels pipeline
  └── Requires: Vertical video output (Shorts/Reels with subtitles)
  └── Requires: Fix instagram_uploader.py wiring

Threads + Bluesky posting
  └── Requires: Episode metadata (title, description, URL) — already available
  └── No dependency on other new features

Email newsletter
  └── Requires: Blog post generator (already available)
  └── Requires: Episode webpage URL (for links)

Cross-episode topic clustering
  └── Requires: FTS5 search index (already available)
  └── Requires: Episode transcripts (already available)
```

## MVP Recommendation

Given the project's stated goals (sound professional, match the show's voice, system cleaner), the MVP priority is:

**Ship together as Phase 1 (Audio Quality):**
1. Audio ducking — immediate audible improvement, table stakes
2. True LUFS normalization — required for platform compliance

**Ship together as Phase 2 (Content Voice):**
3. Edgy comedy voice for AI content — highest brand impact
4. Clip virality scoring + smart clip detection — clips are the primary discovery channel

**Ship together as Phase 3 (Distribution Gaps):**
5. Burned-in subtitle Shorts/Reels — 58% of discovery from short-form video
6. Wire Instagram into pipeline — closes the existing stub
7. Threads + Bluesky posting — low effort, growing platforms
8. Fix scheduled upload execution — silent bug, must fix

**Defer (Phase 4+):**
- Chapter markers: Medium complexity, requires new RSS schema support; not blocking anything else
- Episode webpage: High complexity (needs hosting); large SEO payoff but requires infrastructure decision
- Filler word removal: Risk of altering hosts' natural speech patterns; needs tuning
- Email newsletter: Valuable but requires external ESP integration decision
- LinkedIn posting: Easy win; defer only because it's lower-priority than fixing existing distribution
- Cross-episode topic clustering: Nice-to-have for listener UX; no pipeline blocking dependency

## Sources

- [7 AI Podcast Production Systems That Automated the Entire Workflow](https://www.godofprompt.ai/blog/7-ai-podcast-production-systems-that-automated-the-entire-workflow) — MEDIUM confidence (WebSearch)
- [The 50 Best Podcasting Tools in 2025](https://podsqueeze.com/blog/the-best-podcasting-tools/) — MEDIUM confidence (WebSearch)
- [Castmagic Review 2025](https://www.aidirecthub.com/ai-tool/castmagic) — MEDIUM confidence (WebSearch)
- [Castmagic vs Descript 2025 Showdown](https://skywork.ai/skypage/en/Castmagic-vs.-Descript-(2025)-The-Ultimate-AI-Showdown-for-Content-Creators/1972913659783999488) — MEDIUM confidence (WebSearch)
- [Apple Podcasts AI Chapters announcement](https://podnews.net/update/apple-podcasts-chapters-timedlinks) — HIGH confidence (official source)
- [Chapters on Apple Podcasts — Apple official](https://podcasters.apple.com/support/5482-using-chapters-on-apple-podcasts) — HIGH confidence (official)
- [7 Podcast SEO Best Practices 2025](https://www.fame.so/post/7-podcast-seo-best-practices-for-explosive-growth-in-2025) — MEDIUM confidence (WebSearch)
- [State of Video Podcasts 2025](https://www.sweetfishmedia.com/blog/the-2025-state-of-video-podcasts) — MEDIUM confidence (WebSearch)
- [New Data: Video Clips Fuel Podcast Discovery](https://www.podcastnewsdaily.com/news/new-data-shows-video-clips-social-media-fuel-podcast-discovery-more-than-ever/article_998a85fd-6508-477c-9cfe-1ae90b37f64e.html) — MEDIUM confidence (WebSearch)
- [Podcast Analytics That Actually Matter — Cohost](https://www.cohostpodcasting.com/resources/podcast-analytics-that-matter) — MEDIUM confidence (WebSearch)
- [Dynamic Ad Insertion — Captivate FM](https://www.captivate.fm/podcast-monetization/sponsorship/what-is-dynamic-ad-insertion) — MEDIUM confidence (WebSearch)
- [Bluesky, Threads, X Landscape 2025](https://circleboom.com/blog/is-bluesky-or-threads-more-popular-in-2025/) — MEDIUM confidence (WebSearch)
- [Email Marketing Boosts Retention 22%](https://elasticemail.com/blog/how-to-promote-your-podcast-with-email-marketing) — LOW confidence (single source, unverified stat)
- [Cleanvoice AI filler word removal](https://cleanvoice.ai/) — HIGH confidence (official product site)
- [Auphonic audio processing](https://auphonic.com/) — HIGH confidence (official product site)
