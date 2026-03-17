# Codebase Structure

**Analysis Date:** 2026-03-16

## Directory Layout

```
podcast-automation/
├── main.py                     # CLI entry point + full pipeline orchestration (1800 lines)
├── config.py                   # Central configuration (env vars, paths, constants)
├── logger.py                   # Singleton logger setup
├── pipeline_state.py           # Checkpoint/resume state management
├── retry_utils.py              # Exponential backoff decorator
├── ollama_client.py            # Local LLM client (Ollama/Llama 3.1)
│
├── audio_processor.py          # Censorship beep overlay, normalization, clip slicing
├── transcription.py            # Whisper transcription
├── diarize.py                  # Speaker diarization (pyannote)
├── content_editor.py           # GPT-4o content analysis (censor timestamps, clip selection)
├── video_converter.py          # FFmpeg WAV→MP4 (vertical/horizontal/square)
├── subtitle_generator.py       # SRT generation from transcript timestamps
│
├── blog_generator.py           # Auto-generate blog posts from transcript/analysis
├── thumbnail_generator.py      # Pillow-based episode thumbnail (1280×720 PNG)
├── audiogram_generator.py      # FFmpeg animated waveform clip videos
├── clip_previewer.py           # Interactive terminal clip approval UI
│
├── dropbox_handler.py          # Dropbox download/upload (OAuth2, retry)
├── rss_feed_generator.py       # RSS feed XML generation for Spotify
├── notifications.py            # Discord webhook notifications
├── scheduler.py                # Per-platform upload delay scheduling
├── analytics.py                # YouTube/Twitter engagement metrics + scoring
├── search_index.py             # SQLite FTS5 full-text episode search
│
├── topic_scraper.py            # Reddit/RSS topic scraping
├── topic_scorer.py             # Ollama-powered topic scoring
├── topic_curator.py            # Topic curation and deduplication
├── track_episode_topics.py     # Track which topics were covered in episodes
│
├── uploaders/                  # Platform-specific upload clients
│   ├── __init__.py             # Exports all uploaders + caption helpers
│   ├── youtube_uploader.py     # YouTube Data API v3 (OAuth2)
│   ├── twitter_uploader.py     # Twitter/X API v2 (tweepy)
│   ├── instagram_uploader.py   # Instagram Graph API
│   ├── tiktok_uploader.py      # TikTok API
│   └── spotify_uploader.py     # Spotify RSS submission
│
├── tests/                      # Pytest test suite (279+ tests, 20 files)
│   ├── __init__.py
│   ├── test_audio_processor.py
│   ├── test_content_editor.py
│   ├── test_analytics.py
│   ├── test_audiogram_generator.py
│   ├── test_blog_generator.py
│   ├── test_clip_previewer.py
│   ├── test_notifications.py
│   ├── test_pipeline_state.py
│   ├── test_retry_utils.py
│   ├── test_scheduler.py
│   ├── test_search_index.py
│   ├── test_subtitle_generator.py
│   ├── test_thumbnail_generator.py
│   ├── test_video_converter.py
│   ├── test_instagram_uploader.py
│   ├── test_spotify_uploader.py
│   ├── test_tiktok_uploader.py
│   ├── test_twitter_uploader.py
│   ├── test_youtube_uploader.py
│   └── test_process_historical_episodes.py
│
├── credentials/                # OAuth tokens and credentials files (gitignored)
│   └── youtube_token.pickle    # YouTube OAuth2 token (auto-refreshed)
│
├── downloads/                  # Raw episode audio downloaded from Dropbox (gitignored)
├── output/                     # Processed episode artifacts, one subfolder per episode
│   ├── ep_N/                   # Episode N outputs
│   │   ├── *_transcript.json   # Whisper transcript (words + segments + timestamps)
│   │   ├── *_analysis.json     # GPT-4o analysis (censor_timestamps, best_clips, etc.)
│   │   ├── *_show_notes.txt    # Extracted show notes
│   │   ├── *_censored.wav      # Censored + normalized audio
│   │   ├── *_episode.mp4       # Full episode horizontal video (16:9)
│   │   ├── *_thumbnail.png     # 1280×720 episode thumbnail
│   │   └── *_mp3.mp3           # Final MP3 for distribution
│   └── .pipeline_state/        # Checkpoint JSON files per episode (resume support)
│       └── ep_N.json
│
├── clips/                      # Generated audio/video clips, one subfolder per episode
│   └── ep_N/
│       ├── clip_1.wav          # Short audio clip
│       ├── clip_1.srt          # Subtitle file for clip
│       └── clip_1_vertical.mp4 # Vertical video (9:16) for Shorts/Reels/TikTok
│
├── topic_data/                 # Topic engine data (gitignored)
│   ├── scraped_topics_*.json   # Raw scraped topics
│   ├── scored_topics_*.json    # Topics scored by Ollama
│   └── analytics/              # Per-episode engagement analytics JSON
│
├── assets/                     # Static assets
│   ├── podcast_logo.png        # Podcast logo (untracked, 8.6MB)
│   └── beep.wav                # Auto-generated censorship beep tone
│
├── historical_ep/              # Historical episode files for batch processing
│
├── pyproject.toml              # Pytest configuration (testpaths = tests)
├── requirements.txt            # Python dependencies
├── .env                        # Local secrets (gitignored)
├── .env.example                # Template for required env vars
└── .gitignore
```

## Directory Purposes

**Root (`.py` files):**
- Purpose: All application modules live flat in the root — no `src/` subdirectory
- Contains: Every pipeline component, utility, and standalone script
- Key files: `main.py` (entry point), `config.py` (configuration), `logger.py` (logging)

**`uploaders/`:**
- Purpose: Isolate platform-specific distribution logic from the core pipeline
- Contains: One module per social/distribution platform, plus `__init__.py` barrel exports
- Key files: `uploaders/__init__.py` (all public exports), `uploaders/youtube_uploader.py`

**`tests/`:**
- Purpose: All pytest tests, one file per production module
- Contains: Unit tests using `unittest.mock` — no integration tests that call real APIs
- Key files: Named `test_<module>.py` matching each production file

**`credentials/`:**
- Purpose: OAuth2 token storage for platform uploaders
- Contains: `youtube_token.pickle`, other platform token files
- Generated: Yes (by OAuth setup scripts); Committed: No (gitignored)

**`output/`:**
- Purpose: All processed artifacts for each episode, organized by episode folder `ep_N/`
- Contains: Transcripts, analysis JSON, censored audio, videos, thumbnails, MP3s
- Generated: Yes; Committed: No

**`clips/`:**
- Purpose: Short-form audio and video clips extracted per episode
- Contains: `.wav` clip audio, `.srt` subtitle files, `.mp4` vertical/audiogram videos
- Generated: Yes; Committed: No

**`downloads/`:**
- Purpose: Temporary staging for audio downloaded from Dropbox before processing
- Generated: Yes; Committed: No

**`topic_data/`:**
- Purpose: Topic engine persistence — scraped topics, scored topics, analytics results
- Contains: Timestamped JSON files; most recent `scored_topics_*.json` fed into content analysis
- Generated: Yes; Committed: No

**`assets/`:**
- Purpose: Static files used during processing (logo overlay, beep tone)
- Contains: `podcast_logo.png` (needs Git LFS — 8.6MB untracked), `beep.wav` (auto-generated)
- Committed: Partially — `beep.wav` yes, `podcast_logo.png` no

## Key File Locations

**Entry Points:**
- `main.py`: Primary CLI entry point (`python main.py [command]`)
- `topic_scraper.py`: Standalone topic scraping (`python topic_scraper.py`)
- `topic_scorer.py`: Standalone topic scoring (`python topic_scorer.py`)

**Configuration:**
- `config.py`: All env vars, constants, directory paths, censorship word lists
- `.env`: Runtime secrets (gitignored; use `.env.example` as template)
- `pyproject.toml`: Pytest configuration only (`testpaths = ["tests"]`)
- `requirements.txt`: Python package dependencies

**Core Pipeline Logic:**
- `main.py` `PodcastAutomation.process_episode()`: Step sequencing (~800–1300 lines)
- `content_editor.py` `ContentEditor.analyze_content()`: GPT-4o analysis prompt + parsing
- `audio_processor.py` `AudioProcessor.apply_censorship()`: Beep overlay at timestamps
- `pipeline_state.py` `PipelineState`: Checkpoint/resume JSON state

**Distribution:**
- `uploaders/youtube_uploader.py`: YouTube Data API v3 with OAuth2
- `uploaders/twitter_uploader.py`: Twitter v2 API via tweepy
- `dropbox_handler.py`: Source download + finished file upload
- `rss_feed_generator.py`: RSS XML feed for Spotify distribution

**Testing:**
- `tests/`: All test files
- `tests/test_audio_processor.py`, `tests/test_content_editor.py`: Core component tests
- `tests/test_pipeline_state.py`: Checkpoint logic tests

## Naming Conventions

**Files:**
- Production modules: `snake_case.py` (e.g., `audio_processor.py`, `blog_generator.py`)
- Test files: `test_<module_name>.py` in `tests/` (e.g., `tests/test_audio_processor.py`)
- Setup/utility scripts: `setup_<service>.py` or `<action>_<noun>.py` (e.g., `setup_dropbox_oauth.py`, `repost_twitter.py`)
- Output artifacts: `{audio_stem}_{timestamp}_{type}.{ext}` (e.g., `ep25_raw_20251104_225120_transcript.json`)

**Classes:**
- PascalCase matching module purpose (e.g., `AudioProcessor`, `DropboxHandler`, `YouTubeUploader`)
- Each module contains one primary class

**Variables/Functions:**
- snake_case throughout
- Pipeline steps in `process_episode()` named `step_N_<description>` in print statements
- Output paths consistently named `<type>_path` or `<type>_paths`

## Where to Add New Code

**New Pipeline Step:**
- Implementation: New `{feature}.py` file in root (matches flat module pattern)
- Instantiation: Add to `PodcastAutomation.__init__()` in `main.py`
- Step execution: Add numbered step block in `PodcastAutomation.process_episode()`
- Config: Add env var to `config.py` + `.env.example`
- Tests: `tests/test_{feature}.py`

**New Platform Uploader:**
- Implementation: `uploaders/{platform}_uploader.py`
- Export: Add to `uploaders/__init__.py`
- Init: Add try/except block in `PodcastAutomation._init_uploaders()`
- Tests: `tests/test_{platform}_uploader.py`

**New CLI Command:**
- Lightweight (no `PodcastAutomation` needed): Add `_run_{command}()` standalone function in `main.py`, dispatch in `main()` before `PodcastAutomation` init
- Heavy (needs components): Add method to `PodcastAutomation`, dispatch after init

**Shared Utilities:**
- Retry / network helpers: `retry_utils.py`
- Logging: Import `from logger import logger` — never create a new logger
- Config: Add to `config.py` `Config` class — never `os.getenv()` outside config

## Special Directories

**`.planning/`:**
- Purpose: GSD planning documents and codebase maps
- Generated: Yes (by GSD commands); Committed: Yes

**`credentials/`:**
- Purpose: OAuth2 token storage for YouTube and other platforms
- Generated: Yes (by `setup_youtube_auth.py`, etc.); Committed: No (gitignored)

**`output/.pipeline_state/`:**
- Purpose: Resume checkpoint JSON per episode
- Generated: Yes (by `PipelineState`); Committed: No

**`historical_ep/`:**
- Purpose: Batch-processing historical episodes with `process_historical_episodes.py`
- Generated: No (manually placed); Committed: No

---

*Structure analysis: 2026-03-16*
