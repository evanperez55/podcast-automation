# Project Research Summary

**Project:** Podcast Automation v1.1 — Burned-in Subtitle Clips + Episode Webpages
**Domain:** Podcast media processing and SEO distribution
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

This milestone adds two distinct capabilities to an existing, well-structured podcast automation pipeline: (1) Hormozi-style word-by-word burned-in subtitle clips for short-form platforms (YouTube Shorts, Instagram Reels, TikTok), and (2) static episode webpages deployed to GitHub Pages for SEO and transcript discoverability. Both features plug into an already-refactored pipeline with clean checkpoint-based orchestration, defined component interfaces, and platform uploaders already wired. The technical foundation is sound; the work is additive, not architectural.

The recommended approach for subtitle clips is: consume existing WhisperX word-level timestamps, normalize them (fill gaps, resolve overlaps), generate ASS subtitle files via `pysubs2`, and pass them to FFmpeg's `ass=` filter over a 9:16 vertical canvas. This avoids the two dead ends (MoviePy animation, chained `drawtext` filters) and produces full Hormozi-style quality at FFmpeg encoding speed. A new `SubtitleClipGenerator` component replaces the audiogram path in Step 5.5 under an opt-in env var. For webpages, the approach is Jinja2 HTML templates with `autoescape=True`, keyword extraction via `yake`, and deployment to GitHub Pages via the GitHub Contents API — no git subprocess required on Windows. These pages must include `PodcastEpisode` JSON-LD structured data from day one to get any podcast-specific SEO value.

The two dominant risks are both Windows-specific: FFmpeg's subtitle filter misparses Windows drive-letter colons in paths (silent failure, clips render without text), and libass silently substitutes a thin fallback font when the target typeface is not found via fontconfig. Both require targeted mitigations before any clips are generated. The webpage risks are more straightforward: use Jinja2 autoescaping to prevent transcript HTML injection, embed schema.org JSON-LD for rich results, and never commit media files to the Pages repo to avoid build limit exhaustion.

## Key Findings

### Recommended Stack

The existing stack requires only three new packages. `pysubs2==1.8.0` handles ASS subtitle file generation — it provides the correct encoding, color format (`&H00FFFFFF&` BGR hex), and escape rules that raw f-string ASS construction gets wrong. `yake==0.4.8` provides statistical keyword extraction for SEO metadata with no ML model dependency, ruling out KeyBERT's 400MB sentence-transformer download. `ghp-import==2.1.0` handles atomic push of generated HTML to the `gh-pages` branch. All other work uses existing tools: `ffmpeg-python==0.2.0` for vertical video, Jinja2 (already a transitive dep) for HTML templates, `requests` (already transitive) for the GitHub Contents API.

**Core technologies:**
- `pysubs2==1.8.0`: ASS subtitle file generation — handles encoding and escaping that raw f-strings get wrong; no external dependencies; released December 2024
- `yake==0.4.8`: Keyword extraction for episode SEO — statistical, no model download, deterministic output; stable but unmaintained since 2023 (algorithm is frozen and correct)
- `ghp-import==2.1.0`: GitHub Pages branch deployment — atomic, Python API, honors `--dry-run` via `push=False`; stable/maintenance-mode since 2022, acceptable risk
- FFmpeg binary (existing): vertical canvas + ASS subtitle burn-in via `ass=` filter
- Jinja2 (existing transitive dep): HTML template rendering with `autoescape=True`
- GitHub Contents API via `requests` (existing transitive dep): file create/update in gh-pages repo without git subprocess

### Expected Features

**Subtitle clips — must have (table stakes for short-form platforms):**
- Word-by-word caption pop (1-3 words per segment) — plain SRT subtitles look amateur on Shorts/Reels
- All-caps text — readability convention on small phone screens
- Large font (~80-120px on 720x1280) — current FontSize=24 is too small for impact style
- High-contrast text with black outline/shadow — legibility over any background
- Bottom-third center positioning — standard eye target in vertical video
- 9:16 vertical canvas — already built; must be preserved through the new render path

**Subtitle clips — should have (differentiators):**
- Keyword highlight color (yellow/accent per phrase) — drives recognition; achievable via ASS inline `{\c}` tags
- Multiple style presets (hormozi / clean / karaoke) — parameterized via env var; enables platform-specific defaults
- Speaker label overlay — diarization data already available from `diarize.py`

**Subtitle clips — defer to v2+:**
- Animated text entrance (scale/bounce per word) — requires MoviePy, 5-10x render time, not worth it for v1.1
- Platform-specific clip lengths (15s/30s/60s) — adds clip management complexity; AI scorer already targets good durations
- Comedy-aware caption timing — too subjective; high failure risk if automated

**Episode webpages — must have:**
- Full transcript with timestamp anchor links — Google indexes transcripts; documented +4% traffic in industry case studies
- `PodcastEpisode` JSON-LD structured data — without this, pages do not qualify for podcast-specific rich results
- Open Graph + Twitter Card meta tags — without OG tags, social shares show no preview image
- Chapter timestamps with jump links — improves time-on-page; chapter data already generated by `chapter_generator.py`
- SEO keywords in page title, slug, and meta — drives long-tail "podcast about [topic]" search traffic
- sitemap.xml updated on each episode publish

**Episode webpages — should have:**
- Keyword-rich URL slug (not just `/ep25`) — named slugs rank for show topics
- RSS/subscribe buttons — converts web visitors to subscribers

**Episode webpages — defer:**
- Related episodes section (FTS5 integration adds complexity; defer to v1.2)
- Embedded Shorts on episode page (defer until Shorts upload produces stable URLs)

### Architecture Approach

Both features slot cleanly into the existing `pipeline/steps/` structure without disrupting checkpoint keys or pipeline state. `SubtitleClipGenerator` replaces the audiogram branch in `video.py` Step 5.5, writing to the same `video_clip_paths` context field under an opt-in env var. `EpisodeWebpageGenerator` adds Step 8.6 in `distribute.py` after the blog post, writing an optional `webpage_path` to context. Keyword extraction is a modification to `content_editor.py`'s analysis output — not a new step — feeding `ctx.analysis["keywords"]` which the RSS generator already reads. The two feature tracks (subtitle clips, webpages) are independent; they share no code and can be built and merged in parallel.

**Major components:**
1. `subtitle_clip_generator.py` (new) — consumes WAV clip + SRT path; normalizes WhisperX word timestamps; generates ASS via pysubs2; invokes FFmpeg with `ass=` filter on 9:16 black canvas; outputs MP4 (Step 5.5)
2. `webpage_generator.py` (new) — renders Jinja2 HTML template with episode metadata, transcript, chapters, JSON-LD; deploys to GitHub Pages via GitHub Contents API (Step 8.6)
3. `content_editor.py` (modified) — adds keyword extraction via yake to analysis output; result stored in `ctx.analysis["keywords"]`
4. `pipeline/steps/video.py` (modified) — adds subtitle clip branch before audiogram check in Step 5.5
5. `pipeline/steps/distribute.py` (modified) — adds Step 8.6 webpage generation block
6. `pipeline/runner.py` (modified) — registers two new components in `_init_components()`
7. `pipeline/context.py` (modified) — adds optional `webpage_path` field

### Critical Pitfalls

1. **Windows path colon breaks FFmpeg subtitle filter** — FFmpeg's filter graph parser treats `:` in `C:\path\file.ass` as an option separator, silently producing clips with no subtitles. Write `_escape_ffmpeg_filter_path()` helper converting backslashes to forward slashes and escaping the colon (`C\:/path/file.ass`). Use `subprocess.run(list_args)`, not `shell=True`. (Phase 1, must be resolved before any subtitle rendering ships.)

2. **WhisperX word timestamps have gaps, overlaps, and missing words** — Consecutive words have 200-500ms gaps causing subtitle flicker, or overlaps breaking karaoke highlighting. Numbers, contractions, and punctuation-attached words are dropped from alignment entirely. Implement `normalize_word_timestamps()` that closes sub-150ms gaps, resolves overlaps, and interpolates time for unaligned words. (Phase 1, prerequisite for all subtitle rendering.)

3. **libass on Windows silently substitutes DejaVu Sans font** — When the specified font is not found via fontconfig, libass substitutes a thin, unreadable fallback with no error or warning. Embed font file in `assets/fonts/`, pass `fontsdir=assets/fonts` to FFmpeg, check stderr for "substituting font" after rendering. (Phase 1, visual quality gate.)

4. **ASS override tag corruption via naive string construction** — Transcript `{` and `}` characters are interpreted as ASS inline override tags, producing garbled or invisible subtitles. Use `pysubs2` for all ASS generation; never raw f-strings; sanitize transcript text by escaping literal curly braces before insertion. (Phase 1, affects every clip.)

5. **Episode webpage transcript without JSON-LD gets no podcast SEO benefit** — Pages without `PodcastEpisode` schema markup rank as generic text, not podcast episodes, missing Google's podcast-specific rich results surfaces entirely. Embed `PodcastEpisode` + `AudioObject` JSON-LD in the initial template; validate with Google Rich Results Test before publishing. (Phase 2, must be in initial template — not retrofitted.)

## Implications for Roadmap

Based on combined research, two independent feature tracks with clear internal dependency ordering:

### Phase 1: Hormozi-Style Subtitle Clip Generator

**Rationale:** All upstream dependencies are already satisfied — WhisperX word timestamps exist on `transcript_data`, SRT files exist from Step 5.4, vertical canvas FFmpeg patterns are established in `audiogram_generator.py`. The four critical pitfalls are all scoped to this phase and well-understood. Subtitle clips are the higher short-form value feature and have no dependency on webpage work.

**Delivers:** Vertical MP4 clips with large, bold, word-by-word captions — replaces audiogram clips for short-form platform uploads.

**Addresses:** Word-by-word caption pop, all-caps text, large font, high-contrast outline, bottom-third positioning, 9:16 format.

**Avoids:** Pitfalls 1 (path escaping), 2 (timestamp normalization), 3 (font resolution), 4 (ASS construction), 5 (drawtext filter complexity), 6 (SRT-vs-word-level data source), 7 (audio re-encode quality loss), 11 (aspect ratio), 13 (checkpoint key collision).

**Build order within phase:**
1. `normalize_word_timestamps()` function — Pitfall 2 mitigation and prerequisite for everything else
2. `_escape_ffmpeg_filter_path()` helper — Pitfall 1 mitigation; test with `C:\Users\...` path
3. Font file sourced and added to `assets/fonts/` — Pitfall 3 prerequisite
4. `subtitle_clip_generator.py` core module — ASS generation via pysubs2, FFmpeg invocation
5. Wire into `pipeline/steps/video.py` + `pipeline/runner.py`
6. Tests: timestamp normalization edge cases, path escaping, dry-run mode, frame spot-check for font rendering

### Phase 2: Static Episode Webpages (GitHub Pages)

**Rationale:** Webpage generation is fully independent of subtitle clips and can proceed concurrently. It depends only on data already in the pipeline (`analysis`, `transcript_data`, `chapter` data). Structured data and HTML escaping must be in the initial implementation — retrofitting schema markup to already-published pages is significantly more work.

**Delivers:** One SEO-optimized HTML page per episode on GitHub Pages with transcript, chapters, JSON-LD, and Open Graph tags — plus sitemap.xml.

**Uses:** `yake` (keyword extraction), Jinja2 with autoescape (HTML rendering), GitHub Contents API via `requests` (deployment), `ghp-import` (optional batch push).

**Implements:** `content_editor.py` keyword extraction + new `webpage_generator.py` + Step 8.6 in `distribute.py`.

**Avoids:** Pitfall 8 (GitHub Pages build limits — batch pushes, no media files), Pitfall 9 (missing JSON-LD — must be in initial template), Pitfall 10 (HTML injection — Jinja2 autoescape only), Pitfall 12 (duplicate content — AI summary in meta description, transcript as supplementary section).

**Build order within phase:**
1. Keyword extraction in `content_editor.py` — feeds both RSS (existing) and webpage meta tags
2. Jinja2 HTML template with JSON-LD, OG tags, transcript section, chapter links
3. `webpage_generator.py` core module — render + GitHub Contents API deploy
4. Wire into `pipeline/steps/distribute.py` Step 8.6 + `pipeline/runner.py` + `pipeline/context.py`
5. sitemap.xml generation alongside episode page commit
6. Tests: HTML injection (transcript with `<script>` tag), JSON-LD field validation, dry-run mode, GitHub API mock

### Phase 3: Subtitle Style Differentiators

**Rationale:** Once the core subtitle clip pipeline is stable and tested, differentiating features are incremental extensions of Phase 1 code. Keyword color highlighting in ASS uses the existing `pysubs2` SSAEvent model with inline `{\c}` color tags. Style presets require only parameterizing the existing ASS style object.

**Delivers:** Configurable subtitle styles (hormozi / clean / karaoke) for platform-specific output; accent-color keyword highlighting; optional speaker label overlays.

**Addresses:** Keyword highlight color, multiple style presets, speaker label overlay from the differentiator list.

### Phase Ordering Rationale

- Phases 1 and 2 are independent and can be built concurrently or sequentially without conflict — no shared code, no shared checkpoint keys.
- Phase 3 requires Phase 1 to exist first (extends its code); no dependency on Phase 2.
- All Pitfall 1 and 2 mitigations (path escaping, timestamp normalization) are correctness prerequisites for Phase 1, not quality improvements — they must be implemented before the first real episode clip is generated.
- Keyword extraction (Phase 2 sub-task) should be done before webpage generation but has no dependency on subtitle clips.

### Research Flags

Phases needing deeper research during planning:
- None identified. Both major feature tracks have well-documented patterns and the architecture research provides concrete implementation guidance including code sketches and interface signatures.

Phases with standard patterns (no research-phase needed):
- **Phase 1:** pysubs2 API is fully documented (readthedocs.io); FFmpeg ASS filter is documented; patterns are derived from the existing `audiogram_generator.py` in this codebase.
- **Phase 2:** Jinja2 templating is standard; GitHub Contents API is official REST documentation; schema.org JSON-LD types are official spec with validator tool.
- **Phase 3:** Incremental extension of Phase 1 code; no new technologies.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pysubs2 and ghp-import version-confirmed on PyPI; yake is MEDIUM (stable but unmaintained since 2023, algorithm is frozen); FFmpeg and Jinja2 are existing validated deps with no version changes needed |
| Features | HIGH | Table stakes verified against top short-form podcast clip channels and official SEO sources; schema.org JSON-LD requirements confirmed against official spec |
| Architecture | HIGH | Derived from direct inspection of existing codebase files (`pipeline/steps/video.py`, `pipeline/runner.py`, `pipeline/context.py`); integration points include concrete code sketches, not inferences |
| Pitfalls | HIGH | Windows FFmpeg path bug confirmed by upstream MSYS2 issue #11018; WhisperX timing issues confirmed by merged PRs #816 and #999; libass fontconfig issue confirmed by libass/libass#389; GitHub Pages limits from official docs |

**Overall confidence:** HIGH

### Gaps to Address

- **WhisperX word-level data persistence:** The `subtitles` checkpoint currently stores SRT paths, not word-level JSON. Verify during Phase 1 implementation whether `transcript_data` on context preserves word-level timestamps across checkpoints, or whether explicit persistence is needed at Step 2. If not persisted, add it before subtitle clip generation code is written.
- **yake on full podcast transcripts:** yake is validated for short documents; podcast transcripts are ~10,000 words. Benchmark on a full episode transcript during Phase 2 implementation. Expected to be fast (statistical algorithm), but unconfirmed at this scale.
- **GitHub Pages one-time setup:** `GITHUB_TOKEN`, `GITHUB_PAGES_REPO`, and `SITE_BASE_URL` env vars must be configured before Phase 2 can deploy. The pipeline should handle missing env vars gracefully — log a warning and skip deployment, not crash.
- **Font file sourcing:** Phase 1 requires a specific font file in `assets/fonts/` to avoid libass silent substitution. Anton (Google Fonts, open license) or Impact (common on Windows) should be selected and committed before Phase 1 is testable end-to-end.

## Sources

### Primary (HIGH confidence)
- [pysubs2 PyPI](https://pypi.org/project/pysubs2/) — version 1.8.0, December 2024
- [pysubs2 documentation](https://pysubs2.readthedocs.io/en/latest/) — SSAEvent API, style objects
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html) — `subtitles`/`ass` filter, `force_style`
- [GitHub REST API — Create or update file contents](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Schema.org PodcastEpisode](https://schema.org/PodcastEpisode) — JSON-LD structured data type
- [Schema.org PodcastSeries](https://schema.org/PodcastSeries)
- [WhisperX issue #1247](https://github.com/m-bain/whisperX/issues/1247) — word timestamp inaccuracy confirmed by maintainer
- [WhisperX PR #999](https://github.com/m-bain/whisperX/pull/999) — overlap fix (merged)
- [WhisperX PR #816](https://github.com/m-bain/whisperX/pull/816) — timing overlap fix (merged)
- [libass/libass #389](https://github.com/libass/libass/issues/389) — fontconfig Windows font substitution issue
- [MSYS2 MINGW-packages #11018](https://github.com/msys2/MINGW-packages/issues/11018) — Windows subtitle path colon bug confirmed

### Secondary (MEDIUM confidence)
- [Hormozi-style captions guide — Riverside](https://riverside.com/blog/hormozi-style-videos) — feature expectations for short-form clips
- [Word-by-word captions with Python — AngelFolio](https://www.angel1254.com/blog/posts/word-by-word-captions) — WhisperX to ASS per-word generation pattern
- [FFmpeg ASS subtitle guide — Bannerbear](https://www.bannerbear.com/blog/how-to-add-subtitles-to-a-video-with-ffmpeg-5-different-styles/) — burn-in filter patterns
- [Podcast SEO best practices 2025 — Fame](https://www.fame.so/post/podcast-seo) — SEO feature expectations and transcript traffic data
- [yake GitHub (LIAAD)](https://github.com/LIAAD/yake) — keyword extraction, 1k+ stars, confirmed stable
- [ghp-import PyPI](https://pypi.org/project/ghp-import/) — version 2.1.0, May 2022
- [pycaps GitHub](https://github.com/francozanardi/pycaps) — animated subtitles (evaluated and deferred)
- [Burned-in subtitles quality guide — md-subs.com](https://www.md-subs.com/blog/burned-in-subtitles-journey-to-quality) — rendering quality considerations

### Tertiary (LOW confidence)
- [Vertical subtitle alignment stabilization — Alibaba product insights](https://www.alibaba.com/product-insights/why-do-ai-subtitle-burn-ins-shift-position-during-vertical-video-playback-and-how-to-stabilize-alignment.html) — single source, corroborates alignment positioning advice

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
