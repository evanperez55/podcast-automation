# Technology Stack

**Project:** Podcast Automation v1.1 — Burned-in Subtitle Clips + Episode Webpages
**Researched:** 2026-03-18

---

## Existing Stack (Do Not Replace)

These are validated, working dependencies. Not candidates for replacement or re-research.

| Technology | Version (pinned) | Role |
|------------|-----------------|------|
| Python | 3.12+ | Language |
| FFmpeg binary | C:\ffmpeg\bin\ffmpeg.exe | Media processing engine |
| ffmpeg-python | 0.2.0 | FFmpeg bindings |
| WhisperX | 3.1.6 | Word-level timestamps (already produces per-word timing) |
| pydub | 0.25.1 | Audio manipulation |
| Pillow | 10.2.0 | Image generation |
| Jinja2 | transitive dep | HTML templating (already available) |
| openai | >=1.0.0 | GPT-4o for keyword/SEO generation |

---

## New Stack Additions

### Subtitle Generation: pysubs2

**Recommended:** `pysubs2==1.8.0`

**Why:** The burned-in subtitle workflow requires generating ASS (Advanced SubStation Alpha) files with per-word timing and custom styles (large bold text, color fills, drop shadows, centered positioning). `pysubs2` is the canonical Python library for this — it provides an object model for ASS styles and events, handles the format's encoding quirks, and serializes to valid ASS that FFmpeg's `ass=` filter accepts directly.

The existing `audiogram_generator.py` already burns SRT subtitles via FFmpeg's `subtitles=` filter with `force_style=`. For Hormozi-style word-by-word display, SRT is insufficient — SRT has no per-word timing or style override support at the word level. ASS solves this: each word becomes a separate `Dialogue` event in the ASS file with its own start/end time, font size, color, shadow, and outline. pysubs2 makes constructing these events straightforward.

WhisperX already outputs word-level timestamps in its JSON/dict result. The generation path is: WhisperX word timestamps → Python loop building pysubs2 `SSAEvent` objects → save as `.ass` → pass to FFmpeg `ass=` filter.

**Why not raw string generation:** ASS format has encoding-sensitive headers, color format quirks (`&H00FFFFFF&` BGR hex with alpha prefix), and escape rules. Writing ASS by hand-formatting strings is fragile. pysubs2 handles all of this correctly.

**Why not `drawtext` filter:** FFmpeg's `drawtext` filter can overlay text but requires one `-vf drawtext=...` expression per word with exact `enable=` time windows. For a 60-second clip with ~150 words, this produces an unwieldy 150-segment filter graph that is hard to generate, debug, and modify. ASS is the right abstraction for styled timed text.

**Why not WhisperX's built-in `highlight_words` ASS output:** WhisperX can produce ASS with karaoke-style `\k` tags for highlight effects, but this requires re-running WhisperX at clip generation time. The pipeline already has WhisperX output cached from the transcription step. pysubs2 lets us consume the cached word timestamps and produce styled ASS without re-running transcription.

**Integration point:** New `subtitle_clip_generator.py` module. Consumes `clip.words` (word-level timestamp list already present on clip objects from WhisperX). Produces a `.ass` file alongside each clip. `audiogram_generator.py` passes the `.ass` path to FFmpeg using the `ass=` filter (instead of `subtitles=` with force_style, which only applies to SRT).

```bash
pip install pysubs2==1.8.0
```

**Confidence:** HIGH — PyPI confirmed version 1.8.0, released December 24, 2024. Official docs at pysubs2.readthedocs.io. No external dependencies beyond Python stdlib.

---

### FFmpeg: Vertical Video Canvas

**Recommended:** No new library. Use existing `ffmpeg-python==0.2.0` or `subprocess` calls to the existing FFmpeg binary.

**Why:** The vertical crop and pad operation for 9:16 (1080x1920) is a standard FFmpeg filter graph: `scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black`. This is the same pattern already used in `audiogram_generator.py` for horizontal/vertical format switching. No new dependency needed — the work is in constructing the correct filter string for portrait orientation with the waveform replaced by a solid background + burned-in ASS.

**Concrete filter chain for a Hormozi-style clip:**
```
-vf "scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,ass='/path/to/subtitles.ass'"
```

**Confidence:** HIGH — This is documented FFmpeg filter composition, validated against existing audiogram_generator.py patterns in this codebase.

---

### Keyword Extraction: yake

**Recommended:** `yake==0.4.8`

**Why:** SEO keywords for episode webpages must be extracted from podcast transcripts (~10,000 words each). The project constraint is no heavy new dependencies and no paid APIs.

`yake` (Yet Another Keyword Extractor) is a statistical, unsupervised keyword extractor with no ML model dependency. It uses local text features (word frequency, co-occurrence, position) to rank keyphrases. It runs in milliseconds on a full transcript with zero additional downloads.

**Why not KeyBERT:** KeyBERT requires `sentence-transformers`, which downloads a ~400MB transformer model on first use. The project already has `torch` and WhisperX occupying significant GPU memory during processing. Adding another transformer for keyword extraction creates unnecessary memory pressure and download time. KeyBERT is overkill for podcast SEO keywords where statistical extraction is accurate enough.

**Why not Ollama/GPT-4o prompt:** Ollama is already used in the pipeline and is available for free. However, LLM-based keyword extraction produces inconsistent output formats requiring parsing, and adds latency. For deterministic, fast, structured keyword output, yake is more reliable.

**Why not rake-nltk:** RAKE requires NLTK stopword downloads and corpus data. yake has no external corpus dependency.

**Integration point:** New `keyword_extractor.py` module called from the webpage generation step. Input: full transcript text. Output: list of ranked keyphrases for `<meta name="keywords">`, Open Graph tags, and JSON-LD structured data.

```bash
pip install yake==0.4.8
```

**Confidence:** MEDIUM — PyPI shows yake 0.4.8 is the latest stable version. Last release was 2023, but the package is stable and the algorithm is deterministic. The LIAAD/yake GitHub has 1k+ stars and is actively used. No newer version found in 2024-2025 searches; the algorithm is stable, not actively developed.

---

### Static Site Generation: Jinja2 (already available)

**Recommended:** Use existing `Jinja2` (transitive dependency, already installed). No new package needed.

**Why:** GitHub Pages accepts raw HTML pushed to a `gh-pages` branch. The episode webpage generation task is: take episode metadata + transcript → render HTML files → push to `gh-pages`. Jinja2 is already available as a transitive dependency (it ships with many packages in the stack). The blog_generator.py pattern confirms the project uses f-strings and Ollama for text generation, but Jinja2 is available for HTML templating.

**Template structure:** One `episode.html.j2` template containing the full HTML document with Open Graph meta tags, JSON-LD `PodcastEpisode` structured data, transcript with chapter navigation, and canonical URL. Jinja2 renders it per episode with episode-specific context data.

**Confidence:** HIGH — Jinja2 is a Python standard for HTML templating. The CLAUDE.md milestone context confirms it's already in deps. No new install needed.

---

### GitHub Pages Deployment: ghp-import

**Recommended:** `ghp-import==2.1.0`

**Why:** The webpage generation step must push generated HTML files to the `gh-pages` branch of the podcast repository without overwriting unrelated branches. `ghp-import` does exactly this: takes a local directory of built HTML files, creates/replaces the `gh-pages` branch, and optionally pushes to origin — all in one call. It is used by MkDocs, Sphinx, and Pelican for the same purpose.

**Python API usage (no CLI required):**
```python
import ghp_import
ghp_import.ghp_import("output/pages/", push=True, branch="gh-pages")
```

**Why not manual git operations:** Manually creating/switching to the `gh-pages` branch, copying files, committing, and pushing requires careful handling of detached HEAD state and branch isolation. `ghp-import` handles this correctly and atomically. The pipeline's `--dry-run` mode can be honored by passing `push=False`.

**Caveat:** `ghp-import` 2.1.0 was released May 2022 and has not had a new release since. The project is considered stable/maintenance-mode. The underlying git operations it performs are simple and unlikely to break. MkDocs (widely used) still depends on it. Acceptable risk for this use case.

**Why not GitHub Actions:** GitHub Actions would require a separate CI workflow file and GitHub secrets setup. The project is a local CLI pipeline (`python main.py ep29`). Deployment from local Python code is consistent with the existing pattern (all uploaders are local Python calls, not CI-triggered).

```bash
pip install ghp-import==2.1.0
```

**Confidence:** MEDIUM — Version confirmed on PyPI and libraries.io. Package is stable but unmaintained since 2022. No known breaking changes; git operations it wraps are stable. MkDocs community continues to use it successfully.

---

## Packages Evaluated and Rejected

| Package | Use Case | Decision | Reason |
|---------|----------|----------|--------|
| `KeyBERT==0.9.0` | Keyword extraction | Rejected | Pulls `sentence-transformers` + ~400MB model download. yake provides sufficient quality for podcast SEO with zero ML overhead |
| `rake-nltk` | Keyword extraction | Rejected | Requires NLTK corpus downloads; yake is simpler with equivalent output for short keyphrases |
| FFmpeg `drawtext` filter | Word-by-word subtitle burn-in | Rejected | Requires one filter expression per word (~150 per clip); ASS format via pysubs2 is the correct abstraction for timed styled text |
| WhisperX `highlight_words` ASS output | ASS generation | Rejected | Requires re-running transcription; pysubs2 can consume cached word timestamps |
| Jekyll | Static episode pages | Rejected | Requires Ruby runtime. Python-based Jinja2 generation + ghp-import is consistent with the existing Python-only pipeline |
| Hugo | Static episode pages | Rejected | Requires Go runtime. Same reasoning as Jekyll |
| `auto-subs` (PyPI) | Subtitle generation | Rejected | Wraps Whisper for transcription — redundant. We already have WhisperX word timestamps. pysubs2 is the right tool for the ASS file layer only |

---

## Full Dependency Delta

Libraries to add to `requirements.txt`:

```
# Word-level ASS subtitle file generation (Hormozi-style burned-in clips)
pysubs2==1.8.0

# Keyword extraction for episode webpage SEO (no ML dependency)
yake==0.4.8

# GitHub Pages deployment (push generated HTML to gh-pages branch)
ghp-import==2.1.0
```

**No version changes needed** to existing packages for this milestone. FFmpeg vertical video processing uses existing `ffmpeg-python==0.2.0`. HTML templating uses existing Jinja2 (already transitive dep). OpenAI GPT-4o for fallback SEO description generation uses existing `openai>=1.0.0`.

---

## Integration Points with Existing Pipeline

| New Component | Plugs Into | Checkpoint Key |
|--------------|-----------|----------------|
| `subtitle_clip_generator.py` | `pipeline/steps/video.py` after existing subtitle step (5.4) | `subtitles` (existing) or new `subtitle_ass` key |
| `subtitle_clip_generator.py` → `audiogram_generator.py` | Replace `subtitles=` SRT filter with `ass=` filter for vertical clips | In existing `create_audiogram()` |
| `keyword_extractor.py` | `pipeline/steps/distribute.py` before webpage generation | New `keywords` checkpoint key |
| `webpage_generator.py` | `pipeline/steps/distribute.py` after keywords, before social upload | New `webpages` checkpoint key |
| `webpage_generator.py` → `ghp-import` | End of distribute step | Controlled by `GITHUB_PAGES_REPO` env var + `self.enabled` pattern |

---

## Sources

- [pysubs2 PyPI](https://pypi.org/project/pysubs2/) — version 1.8.0, released December 24, 2024
- [pysubs2 documentation](https://pysubs2.readthedocs.io/en/latest/) — SSAEvent API, style objects
- [yake PyPI](https://pypi.org/project/yake/) — version 0.4.8
- [yake GitHub (LIAAD)](https://github.com/LIAAD/yake) — unsupervised keyword extraction
- [ghp-import PyPI](https://pypi.org/project/ghp-import/) — version 2.1.0, released May 2022
- [ghp-import GitHub (c-w)](https://github.com/c-w/ghp-import) — gh-pages branch deployment
- [FFmpeg Filters Documentation — subtitles/ass](https://ffmpeg.org/ffmpeg-filters.html) — ass and subtitles filter syntax
- [Schema.org PodcastEpisode](https://schema.org/PodcastEpisode) — JSON-LD structured data type for episode pages
- [Karaoke Videos with FFmpeg and SRT Subtitles](https://www.samgalope.dev/2024/11/05/diy-karaoke-videos-with-ffmpeg-and-srt-format-sync-and-style/) — word-timing subtitle generation pattern
- [The Power of Single-Word Subtitles (Medium)](https://medium.com/@didierlacroix/the-power-of-single-word-subtitles-662f8c3891bd) — WhisperX → ASS per-word generation pattern
