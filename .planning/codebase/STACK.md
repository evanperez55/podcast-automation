# Technology Stack

**Analysis Date:** 2026-03-16

## Languages

**Primary:**
- Python 3.12+ - All pipeline logic, CLI, uploaders, content generation, analytics

**Secondary:**
- XML - RSS feed generation (`rss_feed_generator.py`)
- SQL (SQLite FTS5) - Episode search index (`search_index.py`)

## Runtime

**Environment:**
- Python 3.12+
- CUDA (NVIDIA GPU) strongly recommended for Whisper transcription; CPU fallback is 3x slower

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (pinned versions)

## Frameworks

**Core:**
- None (plain Python, no web framework) - CLI-driven pipeline via `main.py`

**AI/ML:**
- `openai-whisper==20231117` - Local speech-to-text transcription
- `whisperx==3.1.6` - Extended Whisper with speaker diarization and word-level alignment
- `torch==2.1.0` / `torchaudio==2.1.0` - Required by Whisper and WhisperX
- Ollama (HTTP, local) - Local LLM inference (Llama 3.2 default); accessed via `ollama_client.py`

**Audio/Video Processing:**
- `pydub==0.25.1` - Audio manipulation (clips, fade, censorship)
- `ffmpeg-python==0.2.0` - FFmpeg Python bindings (audiogram waveform generation)
- FFmpeg binary - Required external install at `C:\ffmpeg\bin\ffmpeg.exe` (auto-detected from PATH)

**Image Processing:**
- `Pillow==10.2.0` - Thumbnail generation (`thumbnail_generator.py`)

**Testing:**
- `pytest==7.4.3` - Test runner; config in `pyproject.toml` (`testpaths = ["tests"]`)
- `pytest-cov==4.1.0` - Coverage reporting
- `pytest-mock==3.12.0` - Mock utilities

**Build/Dev:**
- `ruff` - Linting and formatting (pre-commit enforced)
- `python-dotenv==1.0.0` - `.env` file loading

## Key Dependencies

**Critical:**
- `dropbox==12.0.2` - Source audio download from Dropbox (pipeline step 1 and 7)
- `google-api-python-client==2.116.0` + `google-auth-oauthlib==1.2.0` + `google-auth-httplib2==0.2.0` - YouTube uploads and Google Docs topic tracker
- `tweepy==4.14.0` - Twitter/X posting and media uploads
- `praw==7.7.1` - Reddit scraping for topic discovery
- `requests==2.31.0` - HTTP client for Instagram Graph API, TikTok API, Discord webhooks, Ollama HTTP API

**Infrastructure:**
- `tqdm==4.66.1` - Progress bars in download/processing steps
- `pyyaml==6.0.1` - YAML config parsing
- `pyannote` (via WhisperX) - Speaker diarization model; requires `HF_TOKEN`

## Configuration

**Environment:**
- All secrets via `.env` file loaded by `python-dotenv` in `config.py`
- `Config` class in `config.py` exposes all settings as class attributes
- FFmpeg auto-detected from PATH, then `FFMPEG_PATH` env var, then `C:\ffmpeg\bin\ffmpeg.exe`
- Ollama base URL: `OLLAMA_BASE_URL` (default: `http://localhost:11434`)

**Key configs required:**
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN` (or `DROPBOX_ACCESS_TOKEN`)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
- `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID`
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`
- `HF_TOKEN` - HuggingFace token for pyannote diarization
- `GOOGLE_DOC_ID` - Google Doc ID for topic tracker
- `DISCORD_WEBHOOK_URL` - Discord notifications (optional)
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` - Reddit scraping (optional, falls back to JSON API)
- `OPENAI_API_KEY` - Listed in `Config.validate()` as required but Anthropic replaced by Ollama; used optionally by `blog_generator.py`

**Build:**
- `pyproject.toml` - Pytest configuration only
- No build step required; direct Python execution

## Platform Requirements

**Development:**
- Windows 11 (project default), bash shell
- Python 3.12+
- FFmpeg installed and available at `C:\ffmpeg\bin\ffmpeg.exe` or in PATH
- Ollama running locally on port 11434 with `llama3.2` model pulled
- NVIDIA GPU + CUDA recommended

**Production:**
- No containerization detected
- No deployment config detected
- Runs locally or on a machine with GPU access for Whisper

---

*Stack analysis: 2026-03-16*
