# Architecture

**Analysis Date:** 2026-03-16

## Pattern Overview

**Overall:** Linear Pipeline Orchestration with Optional Module Pattern

**Key Characteristics:**
- Single `PodcastAutomation` class in `main.py` owns all components and drives the pipeline
- All components are initialized at startup; failures are caught and logged, not raised
- Each step produces file artifacts; `PipelineState` checkpoints completions to disk for resume
- Every feature module exposes a `self.enabled` flag gated by env vars — absent credentials silently disable the feature
- No web framework, no task queue — pure CLI-driven sequential execution

## Layers

**CLI / Entry Point:**
- Purpose: Argument parsing and routing commands to pipeline methods
- Location: `main.py` (function `main()`, lines ~1679+)
- Contains: `sys.argv` parsing, dispatch to `PodcastAutomation` methods or standalone command functions
- Depends on: `PodcastAutomation`, `AnalyticsCollector`, `EpisodeSearchIndex`, `UploadScheduler`
- Used by: User via `python main.py [command]`

**Orchestration Layer:**
- Purpose: Drive all pipeline steps in order, coordinate data handoffs between components
- Location: `main.py` — class `PodcastAutomation`, method `process_episode()`
- Contains: Step sequencing, `PipelineState` checkpoint logic, test/dry-run mode guards
- Depends on: All component classes
- Used by: CLI layer

**Core Processing Components:**
- Purpose: The substantive work of each pipeline step
- Location: `audio_processor.py`, `transcription.py`, `content_editor.py`, `video_converter.py`, `subtitle_generator.py`, `diarize.py`
- Contains: Domain logic for audio/video/text manipulation
- Depends on: `config.py`, `logger.py`, external libraries (pydub, whisper, openai)
- Used by: Orchestration layer

**Content Generation Components:**
- Purpose: Produce derivative content from processed episode
- Location: `blog_generator.py`, `thumbnail_generator.py`, `audiogram_generator.py`, `clip_previewer.py`
- Contains: Blog post HTML/markdown generation, image generation (Pillow), waveform videos (FFmpeg)
- Depends on: `config.py`, `logger.py`
- Used by: Orchestration layer

**Distribution Layer:**
- Purpose: Upload finished content to external platforms
- Location: `uploaders/` directory (`youtube_uploader.py`, `twitter_uploader.py`, `instagram_uploader.py`, `tiktok_uploader.py`, `spotify_uploader.py`), `dropbox_handler.py`, `rss_feed_generator.py`
- Contains: Platform-specific API clients, OAuth2 flows, retry logic
- Depends on: `config.py`, `logger.py`, `retry_utils.py`
- Used by: Orchestration layer

**Topic Engine (Standalone):**
- Purpose: Discover, score, and track discussion topics independent of the main pipeline
- Location: `topic_scraper.py`, `topic_scorer.py`, `topic_curator.py`
- Contains: Reddit/RSS scraping, Ollama-based topic scoring, curation logic
- Depends on: `ollama_client.py`, external APIs (Reddit PRAW)
- Used by: Invoked separately; scored outputs loaded by orchestration layer via `_load_scored_topics()`

**Infrastructure / Cross-Cutting:**
- Purpose: Shared utilities used by every other layer
- Location: `config.py`, `logger.py`, `pipeline_state.py`, `retry_utils.py`, `ollama_client.py`
- Contains: Central env-var configuration, singleton logger, checkpoint state persistence, retry decorator
- Depends on: Nothing internal (leaf nodes)
- Used by: All layers

## Data Flow

**Main Episode Processing Flow:**

1. CLI parses args → calls `PodcastAutomation.process_episode()` (or `_process_with_notification()` wrapper)
2. Step 1 — `DropboxHandler` downloads raw `.wav`/`.mp3` → `downloads/` directory
3. Step 2 — `Transcriber` (Whisper) produces `transcript_data` dict (words + segments with timestamps) → saved as `{stem}_transcript.json` in `output/ep_N/`
4. Step 3 — `ContentEditor` (GPT-4o) receives transcript, produces `analysis` dict containing `censor_timestamps`, `best_clips`, `episode_summary`, `social_captions`, `show_notes`, `chapters` → saved as `{stem}_analysis.json`
5. Step 3.5 — `GoogleDocsTopicTracker` updates topic tracker doc (disabled/optional)
6. Step 4 — `AudioProcessor.apply_censorship()` overlays beep tones at censor timestamps → `{stem}_censored.wav`
7. Step 4.5 — `AudioProcessor.normalize_audio()` adjusts LUFS levels in place
8. Step 5 — `AudioProcessor.create_clips()` slices censored audio into short clips → `clips/ep_N/clip_N.wav`
9. Step 5.1 — `ClipPreviewer.preview_clips()` optionally presents interactive approval; filters `clip_paths` and `best_clips` lists
10. Step 5.4 — `SubtitleGenerator` produces `.srt` files for each clip from transcript timestamps
11. Step 5.5 — `AudiogramGenerator` (if enabled) or `VideoConverter` converts audio clips to vertical `.mp4` videos; `VideoConverter` also creates horizontal full-episode video in parallel (ThreadPoolExecutor)
12. Step 5.6 — `ThumbnailGenerator` creates 1280×720 PNG thumbnail (Pillow)
13. Step 6 — `AudioProcessor.convert_to_mp3()` produces final `.mp3`
14. Step 7 — `DropboxHandler` uploads MP3 to finished folder
15. Step 7.5 — `RSSFeedGenerator` updates `podcast_feed.xml`
16. Step 8 — Per-platform uploaders run (`YouTubeUploader`, `TwitterUploader`, `InstagramUploader`, `TikTokUploader`, `SpotifyUploader`), optionally scheduled via `UploadScheduler`
17. Step 8.5 — `BlogPostGenerator` writes blog post from transcript + analysis
18. Step 9 — `EpisodeSearchIndex` indexes transcript into SQLite FTS5 for full-text search

**State Management:**
- `PipelineState` writes JSON to `output/.pipeline_state/{episode_id}.json` after each step
- On `--resume`, completed steps are skipped and their file-path outputs reloaded from state
- `analysis` dict is the primary data handoff between Step 3 and all downstream steps

**Topic Engine Flow (Separate):**
1. `topic_scraper.py` scrapes Reddit/RSS → raw topic JSON in `topic_data/`
2. `topic_scorer.py` sends topics to Ollama (Llama 3.1) for scoring → `scored_topics_{date}.json` in `topic_data/`
3. `main.py._load_scored_topics()` reads most recent scored file at Step 3 and injects as `topic_context` into `ContentEditor.analyze_content()`

## Key Abstractions

**`PodcastAutomation` (Orchestrator):**
- Purpose: Single object holding all component references; methods map to pipeline sub-commands
- Examples: `main.py` class `PodcastAutomation`
- Pattern: Facade — callers interact only with this object, never with component classes directly

**`Config` (Centralized Configuration):**
- Purpose: All env vars, constants, directory paths, and content filtering lists in one place
- Examples: `config.py` class `Config` (all class-level attributes)
- Pattern: Class-level attributes loaded at import time via `os.getenv()`; consumed via `Config.ATTRIBUTE_NAME`

**`PipelineState` (Checkpoint/Resume):**
- Purpose: Persists completed step names and their output file paths so runs can be resumed after failure
- Examples: `pipeline_state.py` class `PipelineState`
- Pattern: Simple key-value JSON store per episode; `is_step_completed()` / `complete_step()` / `get_step_outputs()` interface

**`self.enabled` Pattern:**
- Purpose: Every optional feature module disables itself gracefully when credentials/config are missing
- Examples: `notifications.py` `DiscordNotifier.enabled`, `analytics.py` `AnalyticsCollector.enabled`, `audiogram_generator.py` `AudiogramGenerator.enabled`
- Pattern: Set in `__init__` based on env var presence; all public methods check `self.enabled` first and return early

**Uploaders Package:**
- Purpose: Isolate platform-specific API logic behind a uniform interface
- Examples: `uploaders/youtube_uploader.py`, `uploaders/twitter_uploader.py`, etc. — all exposed via `uploaders/__init__.py`
- Pattern: Each uploader class handles its own OAuth2 auth; raises `ValueError` on missing credentials so orchestrator can skip gracefully

## Entry Points

**`main()` function:**
- Location: `main.py` line ~1679
- Triggers: `python main.py [latest|epN|list|search|analytics|upload-scheduled|--dry-run]`
- Responsibilities: Flag parsing, command routing, `PodcastAutomation` instantiation

**`main.process_episode()`:**
- Location: `main.py` line ~807
- Triggers: Called for `latest`, `epN`, or file-path commands
- Responsibilities: Full 18-step pipeline execution with checkpoint support

**`main.dry_run_episode()`:**
- Location: `main.py` line ~500 (approximate)
- Triggers: `--dry-run` flag
- Responsibilities: Validates pipeline wiring with mock data, no I/O performed

**Topic Engine scripts:**
- Location: `topic_scraper.py`, `topic_scorer.py`
- Triggers: `python topic_scraper.py` / `python topic_scorer.py` (run manually/periodically)
- Responsibilities: Populate `topic_data/scored_topics_*.json` for use as content context

## Error Handling

**Strategy:** Fail-fast at system boundaries for required services; silent disable for optional features

**Patterns:**
- Required services (Dropbox, OpenAI) raise `ValueError` in `__init__` → caught by `Config.validate()` before pipeline starts
- Optional uploaders (YouTube, Twitter, etc.) raise `ValueError` if unconfigured → caught in `_init_uploaders()`, excluded from `self.uploaders` dict
- Each upload step wraps in `try/except Exception` → logs error, records `{"status": "error"}` in results, continues pipeline
- `retry_utils.retry_with_backoff` decorator applied to Dropbox network operations (3 retries, exponential backoff)
- `SubtitleGenerator` import failure → caught with `try/except`, pipeline continues without subtitles
- Pipeline-level errors bubble up to `main()` where a top-level `try/except` prints traceback and exits with code 1

## Cross-Cutting Concerns

**Logging:** `logger.py` provides a module-level `logger` singleton (Python `logging`). Console handler at INFO+, file handler at DEBUG+ writing to `output/podcast_automation.log`. All modules import `from logger import logger`.

**Validation:** Input validation occurs only at system boundaries: `Config.validate()` checks required env vars; uploaders validate credentials in `__init__`; internal data flows trust previous steps' outputs.

**Authentication:** Each external service manages its own credentials — Dropbox uses OAuth2 refresh tokens via `dropbox.Dropbox(oauth2_refresh_token=...)`, YouTube/Instagram use stored pickle/token files in `credentials/`, Twitter uses tweepy with API key/secret env vars.

---

*Architecture analysis: 2026-03-16*
