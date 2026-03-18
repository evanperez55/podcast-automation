# Feature Landscape

**Domain:** Burned-in subtitle vertical clips + SEO episode webpages for podcast automation
**Researched:** 2026-03-18
**Milestone:** v1.1 — Discoverability & Short-Form

## Context: What Already Exists

The following are built and NOT re-researched here. New features must integrate with them:

- Whisper transcription with word-level timestamps (already in `transcription.py`)
- SRT generation grouped into 5-word lines with 2.5s max duration (`subtitle_generator.py`)
- Audiogram waveform videos with SRT burn-in via FFmpeg ASS (`audiogram_generator.py`)
- Vertical 720x1280 video output (Config.VERTICAL_RESOLUTION)
- AI-selected clips (3 per episode) with approval workflow
- Blog post generation from transcript + analysis (Markdown, `blog_generator.py`)
- Episode search index FTS5 (`search_index.py`)
- YouTube Shorts + Instagram + TikTok uploaders (in `uploaders/`)

**Key technical constraint:** The existing SRT burn in `audiogram_generator.py` uses
`subtitles='path.srt':force_style='FontSize=24,PrimaryColour=&Hffffff&,Alignment=2,MarginV=40'`
— plain white centered text. This is the baseline to replace/extend.

---

## Table Stakes

Features that are non-negotiable for clips to compete on Shorts/Reels/TikTok.
Missing = clips look amateur and get ignored.

| Feature | Why Expected | Complexity | Dependency on Existing | Notes |
|---------|--------------|------------|----------------------|-------|
| Big bold word-by-word caption pop | Every top podcast clip channel (Huberman, Lex, Rogan clips) uses this; plain subtitles look unpolished | Medium | Uses existing word timestamps from WhisperX/Whisper; extends `subtitle_generator.py` | ASS format with per-word timing segments rather than line-level SRT |
| All-caps text | Hormozi/podcast clip convention; easier to read on phone at small sizes | Low | Formatting only; post-process word text | Apply `.upper()` to caption text |
| High-contrast text + outline/shadow | Dark or busy backgrounds make white text illegible; black outline is standard | Low | FFmpeg ASS `Outline` and `Shadow` style fields | 3-4px black outline on white or yellow text |
| Bottom-third positioning (center, ~75-85% down frame) | Eye is drawn to center-bottom in vertical video; top positioning feels wrong | Low | Already uses `Alignment=2,MarginV=40` — needs margin tuning for taller fonts | Increase MarginV for 60-80px font |
| 1-3 words per caption segment | Short segments read faster, match speaking pace, create punchy rhythm | Low | Current grouping is up to 5 words per line — reduce to 1-3 for "pop" style | New grouping mode in `subtitle_generator.py` |
| Font size ~80-120px on 720x1280 | Readable on phone without squinting; small text gets ignored | Low | Current FontSize=24 is too small for impact style | Scale to ~100px (ASS Fontsize in points, calibrate to output px) |
| Vertical 9:16 video output | TikTok, Reels, Shorts are all 9:16; landscape clips get letterboxed or rejected | Low | Already built: Config.VERTICAL_RESOLUTION = 720x1280 | Already handled |
| Single background (branded color or image) | Solid color or branded image keeps focus on text/audio; busy backgrounds distract | Low | Audiogram already uses dark branded background (0x1a1a2e) | Already handled |
| No audio issues (clean censored audio) | Clips with raw profanity or jarring beeps get flagged/removed | Low | Audio ducking censorship already in pipeline | Already handled |

## Differentiators

Features that make clips stand out. Not universally expected, but drive virality.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Keyword highlight color (yellow/accent for emphasis) | Captions that highlight a key word per phrase look more dynamic; Hormozi-branded yellow highlight is recognizable | Medium | Requires AI to identify "emphasis words" per segment, or heuristic (nouns, last word of phrase); ASS `{\c&H...&}` inline tags |
| Animated text entrance (pop-in from bottom, scale) | Creates kinetic energy; static captions look flat compared to animated competitors | High | Requires frame-by-frame rendering (MoviePy/pycaps), not achievable with pure FFmpeg ASS; adds significant render time |
| Speaker label overlay | "Joey:" prefix or name card when speaker changes; helps multi-host shows | Low-Med | Requires diarization data (already have `diarize.py`); simple text overlay |
| Hook text overlay (first 1-2 seconds) | Static text at top "This changes everything" / "Nobody talks about this" before captions begin; used by viral channels | Low | Hard-code or AI-generate 1 hook line per clip; drawtext overlay for first 2s |
| Comedy-aware caption timing | Hold caption longer on punchline; rush through setup; matches comedic rhythm | High | Requires clip-level comedic analysis; high risk of feeling wrong if automated |
| Waveform visualization retained | The audiogram waveform adds visual interest absent in face-cam clips | Low | Already have this; keep it in the new subtitle clip style |
| Multiple caption style presets (hormozi / clean / karaoke) | Different styles for different platforms/moods; Instagram skews cleaner, TikTok skews louder | Low | Parameterize ASS style; add SUBTITLE_STYLE env var |

## Anti-Features

Features to explicitly not build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full animated text (scale/bounce per word) | Requires MoviePy or pycaps (alpha-stage library); adds Python dependencies and 5-10x render time per clip | Use FFmpeg ASS with per-word timing — achieves most of the visual impact at FFmpeg speed |
| Face-cam / speaker video crop | Would require video recording infrastructure; this is an audio-only podcast | Keep branded background + waveform; the show's identity is audio-first |
| Platform-specific cut lengths (separate 15s/30s/60s clips) | Adds clip management complexity; the AI already selects good 30-60s moments | Ensure clip scorer targets 30-60s duration; don't generate multiple lengths per clip |
| AI-generated talking head avatars (HeyGen style) | Expensive APIs, uncanny valley risk, off-brand for edgy comedy | — |
| Automatic B-roll / stock footage insertion | Would require stock video API (paid) and scene analysis | — |
| Caption translation for multi-language | Out of scope for a single-language comedy show | — |

---

## Episode Webpage Features

### Table Stakes

Features expected from any podcast episode page in 2025.
Missing = page doesn't rank, looks unprofessional, misses distribution opportunities.

| Feature | Why Expected | Complexity | Dependency on Existing | Notes |
|---------|--------------|------------|----------------------|-------|
| Full transcript on page | Google indexes transcripts; "This American Life" saw +4.36% traffic after publishing transcripts; Apple Podcasts links to transcripts | Low-Med | Full transcript already available from Whisper; needs HTML formatting | Format segments with timestamps as anchor links |
| Episode title, number, publish date | Basic metadata; required for schema markup and social sharing | Low | Available from analysis/config | — |
| Episode description / show notes | Summary that tells search engines and humans what the episode is about | Low | `episode_summary` and `show_notes` from `content_editor.py` analysis | Already generated; needs HTML rendering |
| Open Graph + Twitter Card meta tags | Without OG tags, social shares show no preview image/title; clicks drop significantly | Low | Episode thumbnail already generated | `og:image`, `og:title`, `og:description`, `twitter:card` |
| schema.org PodcastEpisode JSON-LD | Enables rich search results (embedded player, episode info); Google explicitly supports PodcastEpisode schema | Low | Structured data is a few JSON fields | `@type: PodcastEpisode`, `partOfSeries`, `associatedMedia`, `datePublished` |
| Canonical URL per episode | Without canonical URL, search engines may not index the page | Low | GitHub Pages assigns URL automatically based on file path | — |
| sitemap.xml | Search engines use sitemap to discover pages; new pages without sitemap take weeks to index | Low | Generate alongside episode pages | Static XML file listing all episode URLs |
| Chapter timestamps with links | Jump-to-chapter links improve time-on-page and UX; Google surfaces timestamps in results for video content | Low | Chapter data already generated by `chapter_generator.py` | Format as `<a href="#t=123">` or timestamp links |

### Differentiators for Episode Webpages

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Embedded clip videos (Shorts) on episode page | Keeps visitors on page longer; links YouTube Shorts back to source content; backlinks improve SEO | Low | YouTube embed iframes; use clip URLs from upload step |
| Keyword-rich page slug (not just /ep25) | `/episode/why-true-crime-is-funny-ep25` ranks for show topics; generic slugs don't | Low-Med | AI-extract 3-5 keywords from episode title + summary; use as URL slug |
| Keyword meta tags and page keywords | Drives long-tail search traffic; "podcast about [topic]" queries | Low | YAKE or simple frequency analysis on transcript; 5-10 keywords per episode |
| Related episodes section | Reduces bounce rate; encourages binge-listening | Medium | FTS5 search index can surface related episodes by keyword overlap |
| RSS/subscribe buttons on episode page | Converts web visitors to subscribers | Low | Static links to Spotify/Apple Podcasts RSS URL |

### Anti-Features for Episode Webpages

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| JavaScript-heavy SPA / React page | GitHub Pages serves static HTML; JS-heavy pages have worse SEO and add build complexity | Jinja2-templated static HTML; zero JavaScript required |
| CMS / database-backed pages | Adds hosting infrastructure; the constraint is zero-cost static hosting | Static HTML generated per episode by pipeline; committed to GitHub repo |
| Comments / community features | Requires auth, moderation, database; completely out of scope | Link to Discord or YouTube comments |
| Real-time audio player (custom) | Heavy JS dependency; mediocre UX vs native browser `<audio>` | Use plain HTML `<audio>` tag with episode MP3 URL; or Spotify embed |
| Analytics dashboard on page | Use GitHub Pages + GA4 (free) for page analytics if needed | — |

---

## Feature Dependencies (v1.1 scope only)

```
Burned-in subtitle clips (Hormozi-style)
  └── Requires: word-level timestamps (already in transcript_data["words"])
  └── Requires: ASS format subtitle generation (new: word_to_ass_segments())
  └── Extends: subtitle_generator.py (new grouping mode: 1-3 words, pop style)
  └── Extends: audiogram_generator.py (pass ASS file instead of SRT file)
  └── Enables: all three platforms (YouTube Shorts, Reels, TikTok) already wired

Keyword extraction
  └── Requires: transcript text (already available)
  └── Enables: episode webpage URL slug
  └── Enables: SEO meta tags on episode page
  └── Enables: page <title> tag keywords

Episode webpage (GitHub Pages static HTML)
  └── Requires: episode title, number, date (from analysis/config)
  └── Requires: episode summary + show notes (from content_editor.py)
  └── Requires: full transcript (from Whisper — already available)
  └── Requires: chapter timestamps (from chapter_generator.py — already available)
  └── Requires: keyword extraction (new feature, same milestone)
  └── Requires: episode thumbnail path (already generated)
  └── Requires: GitHub Pages repo configured (one-time setup, outside pipeline)
  └── Produces: HTML file committed to gh-pages repo/branch
  └── Enables: sitemap.xml update
  └── Enables: SEO-indexed transcripts

sitemap.xml
  └── Requires: episode webpage (must exist before sitemap entry)
  └── Generated: alongside each episode page commit
```

---

## MVP Recommendation for v1.1

**Burned-in subtitle clips** — implement in two layers:

Layer 1 (core, must-have): Convert SRT line-grouping to word-level segments (1-3 words), generate ASS file with big font (FontSize ~100), high-contrast white text with black outline, positioned center-bottom. Feed ASS to existing audiogram FFmpeg command replacing the SRT force_style hack. This is a pure Python + FFmpeg change with no new dependencies.

Layer 2 (differentiator, if time allows): Add per-word keyword highlighting — identify emphasis word in each segment (last word, or noun), override color with yellow accent `#e94560` (already the show's accent color). Still pure ASS, no MoviePy needed.

**Episode webpages** — implement as static HTML generator:

1. Keyword extractor: Use YAKE (lightweight, no model download required) on transcript text. Produces 5-10 keyphrases. Feed to URL slug and meta tags.
2. Jinja2 HTML template: Single episode page template. Fill with episode data. Write to `output/epXX/index.html`.
3. GitHub Pages commit step: New pipeline step that pushes generated HTML to `gh-pages` branch of a separate repo (or `docs/` folder in this repo). One-time GitHub Pages setup required.
4. sitemap.xml update: Append episode URL to sitemap on each run.

**Defer:**
- Animated text entrance (MoviePy/pycaps) — too complex for v1.1, FFmpeg ASS achieves 80% of the visual effect
- Related episodes section — FTS5 integration adds complexity; defer to v1.2
- Embedded Shorts on episode page — defer until Shorts upload produces stable URLs in pipeline output

---

## Sources

**Burned-in subtitle clips:**
- [Hormozi-style captions guide — Riverside](https://riverside.com/blog/hormozi-style-videos) — MEDIUM confidence (WebSearch)
- [Alex Hormozi Captions — SendShort](https://sendshort.ai/guides/hormozi-captions/) — MEDIUM confidence (WebSearch)
- [3 Ways to Make Alex Hormozi Captions — Submagic](https://www.submagic.co/blog/how-to-make-alex-hormozi-captions) — MEDIUM confidence (WebSearch)
- [Word-by-word captions with Python — AngelFolio](https://www.angel1254.com/blog/posts/word-by-word-captions) — MEDIUM confidence (WebSearch)
- [Pycaps open-source subtitle animation — GitHub](https://github.com/francozanardi/pycaps) — HIGH confidence (official repo)
- [Content-aware animated subtitles with Python — DEV.to](https://dev.to/francozanardi/how-to-create-content-aware-animated-subtitles-with-python-24dn) — MEDIUM confidence (WebSearch)
- [Burn styled subtitles with FFmpeg — maxime.sh](https://maxime.sh/posts/burn-styled-subtitles-with-ffmpeg/) — MEDIUM confidence (WebSearch)
- [FFmpeg ASS subtitle guide — Bannerbear](https://www.bannerbear.com/blog/how-to-add-subtitles-to-a-video-with-ffmpeg-5-different-styles/) — MEDIUM confidence (WebSearch)
- [Vertical subtitle alignment stabilization — Alibaba product insights](https://www.alibaba.com/product-insights/why-do-ai-subtitle-burn-ins-shift-position-during-vertical-video-playback-and-how-to-stabilize-alignment.html) — LOW confidence (single source)
- [Viral podcast clip guide 2025 — Fame](https://www.fame.so/post/ultimate-podcast-clip-guide) — MEDIUM confidence (WebSearch)

**Episode webpages / SEO:**
- [PodcastEpisode schema.org type](https://schema.org/PodcastEpisode) — HIGH confidence (official spec)
- [Schema markup for podcast websites — Podpage](https://support.podpage.com/en/articles/8649011-schema-markup-for-your-podcast-website) — MEDIUM confidence (WebSearch)
- [Podcast SEO best practices 2025 — Fame](https://www.fame.so/post/podcast-seo) — MEDIUM confidence (WebSearch)
- [Structured data for podcasts — Outcast](https://outcast.ai/blog/how-to-use-schema-markup-for-your-podcast/) — MEDIUM confidence (WebSearch)
- [YAKE keyword extraction](http://yake.inesctec.pt/) — HIGH confidence (official project site)
- [Staticjinja static site generator](https://github.com/staticjinja/staticjinja) — HIGH confidence (official repo)
- [WhisperX word timestamps — openai/whisper discussion](https://github.com/openai/whisper/discussions/684) — HIGH confidence (official repo discussion)
