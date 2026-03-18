# Architecture Patterns

**Domain:** Podcast automation pipeline — v1.1 feature integration
**Researched:** 2026-03-18
**Focus:** Burned-in subtitle clips and static episode webpages

## Current Architecture (as-built)

The v1.0 refactor is complete. The actual running structure:

```
main.py (134-line CLI shim)
    |
pipeline/runner.py (orchestrator, component factory, checkpoint logic)
    |
    +---> pipeline/context.py (PipelineContext dataclass)
    |
    +---> pipeline/steps/ingest.py     (Step 1: download)
    +---> pipeline/steps/analysis.py   (Step 3-3.5: AI analysis)
    +---> pipeline/steps/audio.py      (stub — Steps 4-6 still in runner.py)
    +---> pipeline/steps/video.py      (Steps 5.1-5.6: clips, subs, video, thumb)
    +---> pipeline/steps/distribute.py (Steps 7-9: Dropbox, RSS, social, blog, search)
```

`PipelineContext` fields relevant to new features:

```python
clip_paths: list          # WAV audio clips (set in video step, Step 5)
srt_paths: list           # SRT files per clip (set in video step, Step 5.4)
video_clip_paths: list    # MP4 videos per clip (set in video step, Step 5.5)
transcript_data: dict     # Full Whisper transcript with word-level timestamps
analysis: dict            # AI analysis including episode_title, chapters, keywords(TODO)
episode_output_dir: Path  # output/ep_N/
```

---

## Feature 1: Burned-in Subtitle Clips

### What it produces

Vertical (9:16) MP4 clips with large, bold, word-by-word captions burned directly
into the video frame — the "Hormozi style" used on YouTube Shorts, Instagram Reels,
and TikTok. These replace or supplement the current audiogram clips.

### How it fits into the existing step sequence

The burned-in subtitle clips slot into Step 5.5, replacing the audiogram path for
clips destined for short-form platforms. The current Step 5.5 branch:

```
if audiogram_generator.enabled:
    → create_audiogram_clips() using audiogram_generator
else:
    → video_converter.convert_clips_to_videos()
```

The new path adds a third option controlled by an env var (`USE_SUBTITLE_CLIPS`):

```
if subtitle_clip_generator.enabled:   # new branch, checked first
    → subtitle_clip_generator.create_subtitle_clips()
elif audiogram_generator.enabled:
    → create_audiogram_clips()
else:
    → video_converter.convert_clips_to_videos()
```

This means the feature is opt-in, does not break existing behavior, and respects
the `self.enabled` pattern used by every other component.

### New module: `subtitle_clip_generator.py`

**Responsibility:** Take a WAV clip + SRT file, produce a 9:16 MP4 with word-by-word
captions rendered over a dark background with the podcast logo.

**Interface (matches AudiogramGenerator's interface for a clean swap):**

```python
class SubtitleClipGenerator:
    def __init__(self):
        self.enabled = os.getenv("USE_SUBTITLE_CLIPS", "true").lower() == "true"
        self.ffmpeg_path = Config.FFMPEG_PATH
        self.logo_path = Config.ASSETS_DIR / "podcast_logo.png"
        self.font_size = int(os.getenv("SUBTITLE_FONT_SIZE", "72"))
        self.font_color = os.getenv("SUBTITLE_FONT_COLOR", "white")
        self.bg_color = os.getenv("SUBTITLE_BG_COLOR", "0x1a1a2e")

    def create_subtitle_clips(
        self,
        clip_paths: list[str],
        srt_paths: list[str | None],
        format_type: str = "vertical",
    ) -> list[str]:
        """Create MP4 clips with burned-in word-by-word captions.

        Returns list of output MP4 paths (parallel to clip_paths).
        """

    def create_subtitle_clip(
        self,
        audio_path: str,
        srt_path: str | None,
        output_path: str | None = None,
        format_type: str = "vertical",
    ) -> str | None:
        """Create a single subtitle clip. Returns output path or None."""
```

**FFmpeg approach:** The word-by-word effect uses the ASS subtitle format (not SRT
directly) because ASS supports `\an8` (top alignment) and per-word `{\k}` karaoke
tags for word highlighting. The generator converts the SRT to ASS in memory before
passing to FFmpeg's `subtitles=` filter.

Alternatively, FFmpeg's `subtitles=` filter with a custom `force_style` can achieve
the bold-large look from SRT without full ASS conversion — simpler, slightly less
precise control. Start with the `force_style` approach; upgrade to ASS only if
per-word highlighting is required in a later phase.

**FFmpeg filter pattern (SRT with force_style):**

```
subtitles='path/to/clip.srt':force_style='FontName=Arial,FontSize=72,
PrimaryColour=&H00FFFFFF&,Bold=1,Alignment=2,MarginV=80,BorderStyle=3,
OutlineColour=&H00000000&,Outline=2'
```

### Integration points in `pipeline/steps/video.py`

Two changes to `run_video()`:

1. Import and initialize `SubtitleClipGenerator` from `components` (added by runner).
2. In the Step 5.5 block, add the new branch before the audiogram check:

```python
subtitle_clip_generator = components.get("subtitle_clip_generator")

if subtitle_clip_generator and subtitle_clip_generator.enabled and clip_paths:
    # new path
    srt_list = [str(s) if s else None for s in srt_paths]
    video_clip_paths = [
        Path(p) for p in subtitle_clip_generator.create_subtitle_clips(
            clip_paths=[str(p) for p in clip_paths],
            srt_paths=srt_list,
            format_type="vertical",
        )
    ]
elif audiogram_generator and audiogram_generator.enabled and clip_paths:
    # existing audiogram path (unchanged)
    ...
```

3. The `checkpoint key` for `convert_videos` already stores `video_clip_paths`,
   so checkpoint/resume works unchanged — the new branch just populates the same
   key through a different code path.

### Changes to `pipeline/runner.py`

Add to `_init_components()` (both the dry-run and full-init branches):

```python
from subtitle_clip_generator import SubtitleClipGenerator
...
"subtitle_clip_generator": SubtitleClipGenerator(),
```

Add to the `dry_run()` mock step log:

```
[MOCK] Step 5.5: Subtitle clips -- would create N word-by-word caption videos
```

### Changes to `pipeline/context.py`

No changes needed. `video_clip_paths` already holds the output.

### Dependency on existing `SubtitleGenerator`

`subtitle_clip_generator.py` does NOT subclass or import `SubtitleGenerator`. They
are separate concerns:

- `SubtitleGenerator` — produces `.srt` files from transcript data (Step 5.4)
- `SubtitleClipGenerator` — consumes `.srt` files, produces `.mp4` with captions burned in (Step 5.5)

The SRT files produced in Step 5.4 are the input to Step 5.5. This dependency is
already satisfied in the current pipeline: `srt_paths` on `ctx` is populated before
Step 5.5 runs.

---

## Feature 2: Static Episode Webpages (GitHub Pages)

### What it produces

One HTML file per episode published to a GitHub Pages site. Each page contains:
- Episode title, number, date
- Full transcript (formatted, searchable)
- Episode summary and show notes
- Chapter list with timestamps
- SEO `<meta>` tags (description, keywords, og:title, og:description)
- Links to YouTube, Spotify

### How it fits into the step sequence

Episode webpage generation belongs in `pipeline/steps/distribute.py` as a new
Step 8.6, immediately after the blog post (Step 8.5) and before the search index
(Step 9). The webpage depends on `analysis` (for title, summary, chapters) and
`transcript_data` (for full transcript), both of which are available on `ctx` by
Step 8.5.

```
Step 8.5: Blog post (existing)
Step 8.6: Episode webpage generation (new) ← insert here
Step 9:   Search index (existing)
```

**Why distribute.py, not video.py:** The webpage is a distribution artifact (it
gets deployed to GitHub Pages, a public URL). It has no dependency on the video
clips. It follows the same pattern as the blog post — AI-assisted content artifact
that gets written to disk and then optionally published.

### New module: `webpage_generator.py`

**Responsibility:** Render episode data into a static HTML file and optionally
deploy it to a GitHub Pages repository via the GitHub API or git push.

```python
class EpisodeWebpageGenerator:
    def __init__(self):
        self.enabled = os.getenv("WEBPAGE_ENABLED", "true").lower() == "true"
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repo = os.getenv("GITHUB_PAGES_REPO")  # "username/repo"
        self.site_base_url = os.getenv("SITE_BASE_URL", "")

    def generate_webpage(
        self,
        episode_number: int,
        analysis: dict,
        transcript_data: dict,
        output_dir: Path,
    ) -> str | None:
        """Render HTML to output_dir/episode_N.html. Returns file path or None."""

    def deploy_to_github_pages(
        self,
        html_path: str,
        episode_number: int,
    ) -> str | None:
        """Push HTML file to GitHub Pages repo. Returns public URL or None."""
```

### GitHub Pages deployment: how it works

GitHub Pages serves static files from a repository's `gh-pages` branch (or `docs/`
folder). Two deployment approaches are viable:

**Option A: GitHub API (no git required on machine)**
The GitHub REST API `PUT /repos/{owner}/{repo}/contents/{path}` can create or update
a file in the repo. This approach requires only `GITHUB_TOKEN` and `GITHUB_PAGES_REPO`
env vars. No git config, no SSH keys, no local clone needed.

```python
import base64, requests

def _push_via_api(self, html_content: str, filename: str) -> str | None:
    url = f"https://api.github.com/repos/{self.github_repo}/contents/{filename}"
    headers = {"Authorization": f"token {self.github_token}"}
    # Check if file exists (to get sha for update)
    existing = requests.get(url, headers=headers)
    sha = existing.json().get("sha") if existing.status_code == 200 else None
    payload = {
        "message": f"Add episode webpage {filename}",
        "content": base64.b64encode(html_content.encode()).decode(),
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, json=payload, headers=headers)
    return f"https://{owner}.github.io/{repo_name}/{filename}" if r.ok else None
```

This is the recommended approach. No subprocess, no git commands, works on Windows
without SSH configuration.

**Option B: git push via subprocess**
Clone or fetch the `gh-pages` branch, write the file, commit, push. More complex,
requires git configured with credentials, more failure modes. Avoid unless Option A
proves insufficient.

**GitHub Pages configuration required (one-time, manual):**
1. Create a dedicated repo (e.g., `fakeproblemspodcast/episodes`) or use an existing one
2. Enable GitHub Pages in repo Settings → Pages → Source: `gh-pages` branch
3. Set `GITHUB_TOKEN`, `GITHUB_PAGES_REPO`, `SITE_BASE_URL` in `.env`

The `GITHUB_TOKEN` can be a fine-grained personal access token scoped to just that
repository with `Contents: read and write` permission. No additional GitHub App or
OAuth flow needed.

### Keyword extraction: where it lives

The PROJECT.md lists "keyword extraction for SEO metadata" as a third feature in
this milestone. Keyword extraction feeds into both the RSS feed (which already
accepts a `keywords` list) and the episode webpage `<meta keywords>` tag.

The extraction should be a method on `ContentEditor` (or a standalone function) that
runs during Step 3 (analysis) and stores results in `ctx.analysis["keywords"]`. The
existing `distribute.py` Step 7.5 already pulls `keywords` from `analysis` — it
currently hardcodes `["podcast", "comedy", "fake-problems"]`. With extracted keywords,
it would use `analysis.get("keywords", [...fallback...])`.

This is a modification to `content_editor.py`'s analysis prompt (or a separate
`_extract_keywords()` call), not a new module. Keywords are a field on the analysis
dict, not a pipeline step of their own.

### Integration points in `pipeline/steps/distribute.py`

Add Step 8.6 after the blog post block:

```python
# Step 8.6: Generate episode webpage
print("STEP 8.6: GENERATING EPISODE WEBPAGE")
print("-" * 60)
webpage_path = None
webpage_generator = components.get("webpage_generator")
if webpage_generator and webpage_generator.enabled:
    if state and state.is_step_completed("episode_webpage"):
        outputs = state.get_step_outputs("episode_webpage")
        webpage_path = outputs.get("webpage_path")
        logger.info("[RESUME] Skipping episode webpage (already completed)")
    else:
        try:
            webpage_path = webpage_generator.generate_webpage(
                episode_number=episode_number,
                analysis=analysis,
                transcript_data=transcript_data,
                output_dir=episode_output_dir,
            )
            if webpage_path and not ctx.test_mode:
                webpage_url = webpage_generator.deploy_to_github_pages(
                    html_path=webpage_path,
                    episode_number=episode_number,
                )
                if webpage_url:
                    logger.info("Episode webpage published: %s", webpage_url)
            if state and webpage_path:
                state.complete_step("episode_webpage", {"webpage_path": str(webpage_path)})
        except Exception as e:
            logger.warning("Episode webpage generation failed: %s", e)
else:
    logger.info("Episode webpage generation disabled or not configured")
print()
```

### Changes to `pipeline/context.py`

Add optional field:

```python
webpage_path: Optional[str] = None
```

This is optional — the pipeline completes successfully whether or not the webpage
is generated/deployed.

### Changes to `pipeline/runner.py`

Add to `_init_components()`:

```python
from webpage_generator import EpisodeWebpageGenerator
...
"webpage_generator": EpisodeWebpageGenerator(),
```

Add a checkpoint key `"episode_webpage"` to the existing 9-key checkpoint set.

---

## Component Boundaries (updated for v1.1)

| Component | Responsibility | New in v1.1 |
|-----------|---------------|-------------|
| `subtitle_clip_generator.py` | Convert WAV + SRT to MP4 with large burned-in captions (Step 5.5) | Yes |
| `webpage_generator.py` | Render episode HTML + deploy to GitHub Pages (Step 8.6) | Yes |
| `pipeline/steps/video.py` | Modified: add subtitle clip branch in Step 5.5 | Modified |
| `pipeline/steps/distribute.py` | Modified: add Step 8.6 webpage generation | Modified |
| `pipeline/runner.py` | Modified: register two new components in `_init_components()` | Modified |
| `pipeline/context.py` | Modified: add `webpage_path` field | Modified |
| `content_editor.py` | Modified: add keyword extraction to analysis output | Modified |

---

## Data Flow for New Features

```
Step 5.4: SubtitleGenerator
  reads:  ctx.transcript_data, ctx.clip_paths
  writes: ctx.srt_paths (existing, unchanged)

Step 5.5: SubtitleClipGenerator (new path)
  reads:  ctx.clip_paths, ctx.srt_paths
  writes: ctx.video_clip_paths (same field, new generator)

Step 3:  ContentEditor (modified)
  writes: ctx.analysis["keywords"] (new field in analysis dict)

Step 8.6: EpisodeWebpageGenerator (new)
  reads:  ctx.analysis, ctx.transcript_data, ctx.episode_number,
          ctx.episode_output_dir
  writes: ctx.webpage_path
  side effect: HTTP PUT to GitHub API → public URL
```

---

## Checkpoint Keys (updated)

Existing 9 keys remain unchanged. One new key added:

| Key | Step | New |
|-----|------|-----|
| `transcribe` | 2 | no |
| `analyze` | 3 | no |
| `censor` | 4 | no |
| `normalize` | 4.5 | no |
| `create_clips` | 5 | no |
| `subtitles` | 5.4 | no |
| `convert_videos` | 5.5 | no |
| `convert_mp3` | 6 | no |
| `blog_post` | 8.5 | no |
| `episode_webpage` | 8.6 | yes |

The `convert_videos` key already covers the subtitle clip output since both paths
write to `video_clip_paths`. No separate key needed for the subtitle clip approach.

---

## Build Order (Dependencies)

```
1. subtitle_clip_generator.py  (new module, no dependencies on new code)
   - Standalone, uses only FFmpeg and existing SRT files
   - Can be built and tested in isolation before pipeline wiring

2. Modify pipeline/steps/video.py  (add new branch in Step 5.5)
   - Requires subtitle_clip_generator.py to be importable
   - Requires adding component registration in runner.py

3. content_editor.py keyword extraction  (modify existing module)
   - Small prompt change + new "keywords" key in analysis dict
   - Must be done before webpage_generator to have SEO data available
   - Does not depend on subtitle clips

4. webpage_generator.py  (new module, depends on analysis having keywords)
   - HTML rendering has no external dependencies
   - GitHub API deployment requires GITHUB_TOKEN env var (optional for local testing)

5. Modify pipeline/steps/distribute.py  (add Step 8.6)
   - Requires webpage_generator.py to be importable

6. Modify pipeline/runner.py  (register both new components)
   - Do last: both new modules must be importable first
   - Single commit covers all _init_components() additions

7. Modify pipeline/context.py  (add webpage_path field)
   - Trivial, do alongside runner.py changes
```

**Items 1-2 are independent of items 3-5.** Subtitle clips and webpages can be
built and merged separately.

---

## Anti-Patterns to Avoid

### Don't create a "Step 5.5b" checkpoint key for subtitle clips

The `convert_videos` checkpoint key covers whichever Step 5.5 code path runs. Both
the audiogram and subtitle clip generators write to `ctx.video_clip_paths`. Using
the same checkpoint key means resume works regardless of which mode was active.
Adding a separate key would break resume for episodes processed before the feature
was added.

### Don't generate the webpage in the video step

The webpage has no video dependency. Putting it in `video.py` couples two
unrelated concerns and makes the webpage unavailable on `run_distribute_only()`
re-runs. It belongs in `distribute.py` for the same reason `blog_generator` lives
there.

### Don't attempt git push for GitHub Pages deployment

Using `subprocess.run(["git", "push", ...])` for deployment requires git credentials,
SSH keys, or a PAT stored in `.netrc` — all fragile on Windows. The GitHub Contents
API (`requests.put`) achieves the same result with only an HTTP call and a token.

### Don't add SRT-to-ASS conversion in `subtitle_generator.py`

`SubtitleGenerator` produces `.srt` files for compatibility with multiple consumers
(the old audiogram, future editors, caption export). ASS conversion for the burned-in
effect belongs in `SubtitleClipGenerator`, which is the only consumer that needs it.
Keep the boundary: subtitle format production is separate from subtitle rendering.

---

## Confidence Assessment

| Claim | Confidence | Basis |
|-------|------------|-------|
| FFmpeg `subtitles=` filter with `force_style` works for large bold captions | HIGH | Verified FFmpeg docs; current audiogram already uses this filter at smaller size |
| GitHub Contents API supports create/update file via PUT | HIGH | Official GitHub REST API docs — no verification gap |
| Step 5.5 branch insertion is safe (no checkpoint key change needed) | HIGH | Derived directly from existing checkpoint logic in video.py |
| SRT → ASS conversion needed for per-word karaoke highlighting | MEDIUM | FFmpeg ASS/SRT behavior; `force_style` alone cannot do per-word timing without ASS |
| `requests` library sufficient for GitHub API calls | HIGH | Already a transitive dependency; no new packages required |

---

## Sources

- FFmpeg subtitles filter documentation: https://ffmpeg.org/ffmpeg-filters.html#subtitles — HIGH confidence
- GitHub REST API — Create or update file contents: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents — HIGH confidence
- Existing pipeline code (`pipeline/steps/video.py`, `pipeline/runner.py`, `pipeline/context.py`) — direct inspection

---

*Architecture research: 2026-03-18 — v1.1 feature integration*
