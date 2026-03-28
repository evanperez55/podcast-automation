# Architecture Research

**Domain:** Real-world podcast client testing and sales demo packaging — v1.4 integration into existing multi-client pipeline
**Researched:** 2026-03-28
**Confidence:** HIGH — based on direct code inspection of all relevant modules (ingest.py, client_config.py, dropbox_handler.py, runner.py, pipeline/steps/, config.py)

---

## Current Architecture (as-built, post-v1.3)

```
main.py (134-line CLI shim)
    |
    +-- client_config.py:activate_client()   (applied before runner starts)
    |
pipeline/runner.py (orchestrator, component factory)
    |
    +---> pipeline/steps/ingest.py      (Step 1: download from Dropbox OR local file)
    +---> pipeline/steps/analysis.py    (Steps 2-3.5: transcribe, analyze, topics)
    +---> pipeline/steps/audio.py       (Steps 4-4.5: censor, normalize)
    +---> pipeline/steps/video.py       (Steps 5-5.6: clips, subtitles, video, thumb)
    +---> pipeline/steps/distribute.py  (Steps 6-9: MP3, Dropbox, RSS, social, blog, search)

Client configs:
    clients/<name>.yaml          — per-client overrides applied to Config class
    clients/<name>/              — per-client credential files (YouTube token, etc.)
    output/<client>/             — per-client output isolation
    downloads/<client>/          — per-client download isolation
```

Critical constraint in ingest.py (line 45):
```python
# Even when audio_file is pre-set from local path, ingest still calls:
dropbox = components["dropbox"]
episode_number = dropbox.extract_episode_number(audio_file.name)
```
This means `DropboxHandler` is **always instantiated** even for local-file processing. This is the primary blocker for clients without Dropbox credentials.

---

## System Overview: v1.4 Additions

```
┌──────────────────────────────────────────────────────────────────────┐
│                  EPISODE SOURCE LAYER (NEW)                           │
│                                                                       │
│  rss_episode_fetcher.py                                               │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  RSSEpisodeFetcher                                                │ │
│  │  - fetch_latest(rss_url) → EpisodeMeta                           │ │
│  │  - fetch_episode(rss_url, n) → EpisodeMeta                       │ │
│  │  - download_audio(url, dest_path) → Path                         │ │
│  │  - extract_episode_number(filename_or_url) → Optional[int]       │ │
│  │                                                                   │ │
│  │  EpisodeMeta: title, audio_url, pub_date, description,           │ │
│  │               episode_number, duration_seconds                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  client YAML config (new fields):                                     │
│    episode_source: "rss" | "dropbox" | "local"  (default: dropbox)   │
│    rss:                                                               │
│      feed_url: "https://feeds.example.com/podcast.rss"               │
├──────────────────────────────────────────────────────────────────────┤
│                  GENRE-AWARE PIPELINE (MODIFIED)                      │
│                                                                       │
│  client YAML config (new fields):                                     │
│    content:                                                           │
│      genre: "comedy" | "true-crime" | "business" | "interview"       │
│      compliance_enabled: true/false                                   │
│      censor_enabled: true/false                                       │
│      clip_scoring_mode: "energy" | "topic-match" | "balanced"        │
│                                                                       │
│  pipeline/steps/analysis.py (MODIFIED):                              │
│    reads genre from Config; adjusts compliance and clip-scoring       │
│    passes genre context into ContentEditor prompt                     │
├──────────────────────────────────────────────────────────────────────┤
│                  DEMO PACKAGING LAYER (NEW)                           │
│                                                                       │
│  demo_packager.py                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  DemoPackager                                                     │ │
│  │  - package_demo(client_name, episode_folder) → Path              │ │
│  │  - generates demo/<client>/<episode>/                            │ │
│  │      summary.html      — single-page visual summary              │ │
│  │      clips/            — clip mp4s (already exist in output/)    │ │
│  │      thumbnails/       — thumbnails (already exist)              │ │
│  │      captions.txt      — platform captions from analysis.json    │ │
│  │      blog_post.html    — blog post (already exists)              │ │
│  │      README.md         — what client receives and how to use it  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  CLI: python main.py package-demo <client> [ep_N]                    │
├──────────────────────────────────────────────────────────────────────┤
│                  EXISTING PIPELINE (post-v1.3, unchanged core)        │
│                                                                       │
│  pipeline/runner.py → pipeline/steps/                                │
│  client_config.py:activate_client() applies YAML overrides to Config │
│  output/<client>/ep_N/ isolation already in place                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Project Structure

```
podcast-automation/
├── main.py                              # MODIFIED: add package-demo command
├── config.py                           # MODIFIED: EPISODE_SOURCE, GENRE, CLIP_SCORING_MODE
├── client_config.py                    # MODIFIED: map new YAML fields to Config
├── rss_episode_fetcher.py              # NEW: RSS download + episode metadata
├── demo_packager.py                    # NEW: demo output packaging
├── pipeline/
│   └── steps/
│       ├── ingest.py                   # MODIFIED: RSS/local source routing, decouple Dropbox
│       └── analysis.py                 # MODIFIED: genre-aware compliance + clip scoring
├── clients/
│   ├── example-client.yaml            # MODIFIED: add episode_source, genre, new fields
│   ├── fake-problems.yaml             # EXISTING (unchanged behavior)
│   ├── <new-client-1>.yaml            # NEW (e.g., true-crime-client.yaml)
│   └── <new-client-2>.yaml            # NEW (e.g., business-podcast.yaml)
├── demo/
│   └── <client>/
│       └── <episode>/                 # Generated demo packages (gitignored)
└── tests/
    ├── test_rss_episode_fetcher.py     # NEW
    └── test_demo_packager.py           # NEW
```

### Structure Rationale

- **`rss_episode_fetcher.py` at root** — follows project convention of flat module structure. Peer to `dropbox_handler.py`. Both satisfy the "episode source" role; ingest.py chooses between them.
- **`demo_packager.py` at root** — standalone post-processing tool, not part of the core pipeline loop. Same level as `analytics.py`, `content_calendar.py`.
- **`demo/` directory** — separate from `output/` (which is pipeline working state). Demo output is presentation-ready, curated copies.

---

## Architectural Patterns

### Pattern 1: Episode Source Abstraction via Config Flag

**What:** `ingest.py` reads `Config.EPISODE_SOURCE` (set from `episode_source` in client YAML) and branches to either `DropboxHandler` or `RSSEpisodeFetcher`. The `DropboxHandler` instantiation is moved inside the `dropbox` branch — it is no longer unconditionally constructed.

**When to use:** Any client whose audio lives in a public RSS feed rather than a shared Dropbox.

**Trade-offs:** No interface/abstract class needed — three branches (dropbox, rss, local) are simple `if/elif`. Adding a fourth source type later is a 10-line addition. The episode number extraction must be handled by each source type — RSS fetchers can parse episode numbers from the `<itunes:episode>` tag or from the audio filename in the enclosure URL.

**Implementation in ingest.py:**
```python
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")

if ctx.audio_file and ctx.audio_file.exists():
    audio_file = ctx.audio_file  # local path provided directly
elif episode_source == "rss":
    fetcher = components["rss_fetcher"]
    meta = fetcher.fetch_latest(Config.RSS_FEED_URL)
    audio_file = fetcher.download_audio(meta.audio_url, Config.DOWNLOAD_DIR)
    ctx.episode_meta = meta  # carry forward for RSS field population
else:  # dropbox (default)
    dropbox = components["dropbox"]
    latest = dropbox.get_latest_episode()
    audio_file = dropbox.download_episode(latest["path"])

# Episode number extraction: each source provides its own
```

The `components` dict in `runner.py` conditionally includes `"rss_fetcher"` or `"dropbox"` based on `Config.EPISODE_SOURCE`. This prevents `DropboxHandler.__init__()` from raising `ValueError` for clients with no Dropbox credentials.

### Pattern 2: Genre Config as Prompt Context Injection

**What:** The `genre` field in the client YAML maps to `Config.PODCAST_GENRE`. The `ContentEditor.analyze_content()` method receives genre as a parameter and injects it into the GPT-4o prompt, adjusting tone expectations, clip selection criteria, and compliance sensitivity.

**When to use:** Any non-comedy podcast. Without this, GPT-4o generates comedy-voiced show notes and over-censors non-profanity content.

**Trade-offs:** Genre is a soft hint to the AI, not a hard rule switch. The existing `VOICE_PERSONA` field in client YAML already provides the primary tone control. Genre is additive context that helps the AI understand what "good" looks like for this show type. Do not create separate ContentEditor subclasses per genre — that's premature.

**Genre effects on pipeline:**
```
comedy (default, existing behavior):
    compliance_enabled: optional (default false for edgy content)
    clip_scoring: energy-based (AudioClipScorer)
    censorship: names + words lists

true-crime:
    compliance_enabled: true (check for identifying victims, legal risk)
    clip_scoring: balanced (topic relevance + energy)
    censorship: typically light (no profanity lists needed)

business/interview:
    compliance_enabled: false (low-risk content)
    clip_scoring: topic-match weighted (quotable insights > loud moments)
    censorship: typically empty lists
```

### Pattern 3: Demo Package as a Read-Only View of Existing Output

**What:** `DemoPackager` does NOT re-generate content. It reads what the pipeline already produced in `output/<client>/ep_N/` and assembles a demo-ready copy in `demo/<client>/ep_N/`. The summary HTML is the only new artifact — it wraps existing outputs in a visual layout.

**When to use:** After a full pipeline run completes. Invoked manually via `python main.py package-demo <client> [ep_N]`.

**Trade-offs:** This pattern avoids any risk of demo packaging breaking the core pipeline. Demo packaging can fail without affecting episode output. Copying files (not moving) preserves the original pipeline artifacts. The summary HTML is a static single-file document (no web server needed) so it's shareable as an email attachment or Dropbox link.

**What the demo package contains:**
```
demo/<client>/ep_N/
    README.md               — "Here's what we produced for your episode"
    summary.html            — visual overview: thumbnail, captions, clips list
    clips/
        clip_0.mp4          — copy of subtitled clip video
        clip_1.mp4
        clip_2.mp4
    thumbnail.png           — copy of generated thumbnail
    blog_post.html          — copy of blog post
    captions.txt            — extracted social captions (Twitter, YouTube, LinkedIn)
```

The `summary.html` is generated with Python's `string.Template` or simple f-string concatenation — no external template engine needed. It embeds the thumbnail as a base64 data URL so the file is self-contained.

### Pattern 4: Conditional Component Initialization in runner.py

**What:** `runner.py:_init_components()` already uses try/except to build the `components` dict, silently omitting unavailable uploaders. The same pattern extends to episode source components: if `EPISODE_SOURCE = "rss"`, only `RSSEpisodeFetcher` is constructed (no Dropbox attempt). If `EPISODE_SOURCE = "dropbox"`, only `DropboxHandler` is constructed.

**Current pattern (runner.py):**
```python
# Uploaders already conditional:
try:
    uploaders["youtube"] = YouTubeUploader(token_path=youtube_token)
except (ValueError, FileNotFoundError) as e:
    logger.info("YouTube uploader not available: %s", ...)
```

**Extension for episode sources:**
```python
episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
if episode_source == "rss":
    from rss_episode_fetcher import RSSEpisodeFetcher
    components["rss_fetcher"] = RSSEpisodeFetcher()
else:
    components["dropbox"] = DropboxHandler()  # existing behavior
```

This is the minimal change needed to un-block non-Dropbox clients.

---

## Data Flow

### RSS Episode Processing Flow

```
python main.py --client true-crime-client latest
    |
client_config.py:activate_client("true-crime-client")
    - applies episode_source: "rss" → Config.EPISODE_SOURCE = "rss"
    - applies rss.feed_url → Config.RSS_FEED_URL = "https://..."
    - applies content.genre → Config.PODCAST_GENRE = "true-crime"
    - applies voice_persona, scoring_profile overrides
    |
pipeline/runner.py:_init_components()
    - sees EPISODE_SOURCE = "rss" → constructs RSSEpisodeFetcher
    - skips DropboxHandler construction entirely
    |
pipeline/steps/ingest.py
    - calls rss_fetcher.fetch_latest(Config.RSS_FEED_URL)
    - returns EpisodeMeta(title, audio_url, episode_number, pub_date)
    - calls rss_fetcher.download_audio(meta.audio_url, DOWNLOAD_DIR / <client>)
    - sets ctx.audio_file, ctx.episode_number, ctx.episode_meta
    |
pipeline/steps/analysis.py (MODIFIED)
    - reads Config.PODCAST_GENRE, Config.COMPLIANCE_ENABLED
    - injects genre context into ContentEditor prompt
    - skips compliance check if Config.COMPLIANCE_ENABLED = False
    |
[remaining steps: audio, video, distribute — unchanged]
    |
output/true-crime-client/ep_N/
    {stem}_transcript.json
    {stem}_analysis.json
    clip_0.mp4, clip_1.mp4, clip_2.mp4
    thumbnail.png
    blog_post.html
```

### Demo Package Flow

```
python main.py package-demo true-crime-client ep_42
    |
demo_packager.py:DemoPackager.package_demo("true-crime-client", "ep_42")
    |
    +-- reads output/true-crime-client/ep_42/{stem}_analysis.json
    |   extracts: episode_title, social_captions, show_notes
    |
    +-- locates: clip_*_subtitled.mp4, thumbnail.png, blog_post.html
    |
    +-- creates demo/true-crime-client/ep_42/
    |       copies clips/, thumbnail.png, blog_post.html
    |       writes captions.txt (formatted from analysis.social_captions)
    |       writes summary.html (template, embeds thumbnail as base64)
    |       writes README.md
    |
    +-- prints: "Demo package ready: demo/true-crime-client/ep_42/"
```

### Client Config Application (existing + new fields)

```
clients/<name>.yaml
    episode_source: "rss"           → Config.EPISODE_SOURCE
    rss.feed_url: "https://..."     → Config.RSS_FEED_URL        (NEW)
    content.genre: "true-crime"     → Config.PODCAST_GENRE        (NEW)
    content.compliance_enabled: true → Config.COMPLIANCE_ENABLED  (NEW)
    content.censor_enabled: false   → Config.CENSOR_ENABLED       (NEW)
    [all existing fields unchanged]
```

---

## Integration Points

### New Modules

| Module | Integrates With | Direction |
|--------|-----------------|-----------|
| `rss_episode_fetcher.py` | `pipeline/runner.py` | runner constructs it; passes via `components["rss_fetcher"]` |
| `rss_episode_fetcher.py` | `pipeline/steps/ingest.py` | ingest calls `fetch_latest()` + `download_audio()` |
| `demo_packager.py` | `pipeline/steps/distribute.py` output | reads analysis JSON + copies output files |
| `demo_packager.py` | `main.py` | new `package-demo` CLI command routes to it |

### Modified Existing Modules

| Module | Change | Risk |
|--------|--------|------|
| `pipeline/steps/ingest.py` | Branch on `Config.EPISODE_SOURCE`; move Dropbox instantiation inside `else` branch; add RSS fetch path | LOW — additive branching; Dropbox path is behaviorally identical |
| `pipeline/runner.py` | Conditional component construction (rss_fetcher vs dropbox) based on `EPISODE_SOURCE` | LOW — existing try/except pattern already handles optional components |
| `pipeline/steps/analysis.py` | Inject genre context into ContentEditor call; respect `COMPLIANCE_ENABLED` flag | LOW — additive prompt context; compliance skip already has `self.enabled` pattern |
| `client_config.py` | Map new YAML fields (`episode_source`, `rss.feed_url`, `content.genre`, etc.) to Config | MINIMAL — additive to `_YAML_TO_CONFIG` dict |
| `config.py` | Add `EPISODE_SOURCE`, `RSS_FEED_URL`, `PODCAST_GENRE`, `COMPLIANCE_ENABLED`, `CENSOR_ENABLED` with env-var defaults | MINIMAL — all new, no existing attribute changes |
| `clients/example-client.yaml` | Add commented-out new fields with documentation | NONE — purely additive, no existing clients affected |
| `main.py` | Add `package-demo` command routing | LOW — new elif branch in command dispatch |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `RSSEpisodeFetcher` ↔ `ingest.py` | `EpisodeMeta` dataclass return from `fetch_latest()` | Store on `ctx.episode_meta` for downstream use (RSS distribution step may want pub_date) |
| `ingest.py` ↔ `runner.py` | `components` dict key: `"rss_fetcher"` vs `"dropbox"` | Only one is present per run; ingest checks which key exists |
| `DemoPackager` ↔ output files | Read-only access to `output/<client>/ep_N/` | Never modifies pipeline output; only copies |
| `ContentEditor` ↔ genre config | Genre passed as parameter to `analyze_content()` | Not stored in ContentEditor instance — Config is the source of truth |
| `Config.CENSOR_ENABLED` ↔ audio step | Audio step skips `apply_censorship()` if False | Must check flag, not rely on empty word lists (empty lists currently still run the duck-fade pass) |

---

## Anti-Patterns

### Anti-Pattern 1: Subclassing DropboxHandler for RSS

**What people do:** Create `RSSHandler(DropboxHandler)` or add `download_from_rss()` to the existing DropboxHandler class.
**Why it's wrong:** DropboxHandler owns Dropbox-specific auth, retry logic, and folder path conventions. These are meaningless for RSS. Subclassing adds dead weight and confuses future readers.
**Do this instead:** Separate `rss_episode_fetcher.py` module. Both DropboxHandler and RSSEpisodeFetcher are peers in the `components` dict. Ingest selects one based on `Config.EPISODE_SOURCE`.

### Anti-Pattern 2: Genre-Specific ContentEditor Subclasses

**What people do:** `TrueCrimeContentEditor(ContentEditor)`, `BusinessContentEditor(ContentEditor)` with overridden prompts.
**Why it's wrong:** Subclass proliferation for what is really just a config difference. The ContentEditor prompt is already parameterized by `VOICE_PERSONA`. Genre is additive context, not a code branch.
**Do this instead:** Single ContentEditor with genre injected as prompt context: `"This is a {genre} podcast. Adjust your analysis accordingly."` + the existing `VOICE_PERSONA` per-client config.

### Anti-Pattern 3: Demo Packager Regenerating Content

**What people do:** Make the demo packager re-run GPT-4o to produce "cleaner" or "demo-ready" captions.
**Why it's wrong:** (a) Costs money. (b) Produces inconsistency between what the demo shows and what the pipeline actually delivered. (c) Adds latency.
**Do this instead:** The demo is a presentation of what was actually produced. If the output isn't good enough for a demo, fix the pipeline config (voice_persona, genre) and re-run the episode. The demo package is a mirror, not a polish layer.

### Anti-Pattern 4: Unconditional DropboxHandler Construction

**What people do:** Leave `DropboxHandler()` construction in `_init_components()` regardless of `EPISODE_SOURCE`.
**Why it's wrong:** `DropboxHandler.__init__()` raises `ValueError` if no Dropbox credentials are configured. Real clients won't have Dropbox credentials. This blocks the entire pipeline for any RSS-sourced client.
**Do this instead:** Gate `DropboxHandler` construction behind `episode_source == "dropbox"` check. This is the primary architectural fix needed for v1.4.

### Anti-Pattern 5: Storing Demo in output/ Directory

**What people do:** Write demo files into `output/<client>/ep_N/demo/` alongside pipeline artifacts.
**Why it's wrong:** `output/` is ephemeral working state — it may be cleaned, regenerated, or gitignored entirely. Demos are persistent deliverables meant to be shared with clients.
**Do this instead:** Separate `demo/<client>/<episode>/` tree. Clearly communicates intent. Can be committed to git, zipped and emailed, or hosted on Dropbox independently of pipeline state.

---

## Build Order (Dependency-Driven)

```
Phase A — RSS episode source (prerequisite for real client testing):
  1. rss_episode_fetcher.py
     - fetch_latest(rss_url) → EpisodeMeta
     - download_audio(url, dest) → Path with progress bar (tqdm, already dep)
     - extract_episode_number() using itunes:episode tag, then filename fallback
     - Standalone, no pipeline dependencies
  2. tests/test_rss_episode_fetcher.py
     - mock requests.get for RSS XML parsing tests
     - mock urllib.request for audio download tests

Phase B — Ingest decoupling (unblocks non-Dropbox clients):
  3. config.py: add EPISODE_SOURCE, RSS_FEED_URL, PODCAST_GENRE,
                COMPLIANCE_ENABLED, CENSOR_ENABLED
  4. client_config.py: map new YAML fields in _YAML_TO_CONFIG
  5. clients/example-client.yaml: add commented new fields
  6. pipeline/runner.py: conditional component construction
  7. pipeline/steps/ingest.py: branch on EPISODE_SOURCE
     - RSS path uses RSSEpisodeFetcher
     - Dropbox path unchanged (existing behavior preserved)

Phase C — Genre-aware pipeline (quality for real clients):
  8. pipeline/steps/analysis.py: inject genre context into ContentEditor
     - Read Config.PODCAST_GENRE, pass to analyze_content()
     - Respect Config.COMPLIANCE_ENABLED flag
     - Respect Config.CENSOR_ENABLED flag in audio step
  9. Create real client YAML configs (2-3 genres)
     - Set voice_persona, genre, scoring_profile, censor lists appropriately
  10. Test run: process one real RSS episode per client, fix breakage

Phase D — Demo packaging (sales readiness):
  11. demo_packager.py
      - package_demo(client_name, episode_folder) reads output/ → writes demo/
      - Generates summary.html (self-contained, base64 thumbnail)
      - Copies clips, captions, blog post
  12. tests/test_demo_packager.py
  13. main.py: add package-demo command
```

Phases A and B must complete before real client testing. Phase C requires B. Phase D requires a successful Phase C test run (needs real output to package).

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 2-3 clients (v1.4 target) | Current YAML-per-client approach is adequate; no changes needed |
| 10+ clients | `process-all` command already exists; add concurrency flag (ProcessPoolExecutor) |
| 50+ clients (SaaS path) | Client YAML → database; output/ → cloud storage; pipeline as a service |
| Unsupported audio hosts | Extend `RSSEpisodeFetcher` with host-specific download logic (e.g., Anchor CDN, Spreaker) |

---

## Sources

- Direct code inspection: `pipeline/steps/ingest.py`, `pipeline/runner.py`, `client_config.py`, `dropbox_handler.py`, `config.py`, `clients/example-client.yaml`, `content_compliance_checker.py`, `audio_processor.py`
- `feedparser` library — standard Python RSS/Atom parsing library, available on PyPI, HIGH confidence for RSS feed parsing
- Project conventions: flat module structure, `self.enabled` pattern, `components` dict pattern in runner.py, `try/except ValueError` for optional component init

---

*Architecture research for: v1.4 Real-World Testing & Sales Readiness — Podcast Automation Pipeline*
*Researched: 2026-03-28*
