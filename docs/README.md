# Podcast Automation

Automated production pipeline for podcast episodes. Handles the full workflow from raw audio to multi-platform distribution: transcription, AI-powered content analysis, automatic censorship, clip generation, video conversion, and uploads to YouTube, Twitter/X, Bluesky, Instagram, TikTok, and Spotify.

Built for the **Fake Problems Podcast**, with multi-client support for additional podcasts.

<!-- Badges -->
<!-- ![Tests](https://img.shields.io/badge/tests-1255%2B-green) -->
<!-- ![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen) -->

## Quick Start

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), FFmpeg, NVIDIA GPU + CUDA (recommended)

```bash
# Install dependencies
uv sync

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys and credentials

# Process the latest episode
uv run main.py latest

# Process a specific episode
uv run main.py ep25

# Dry run (validate without I/O)
uv run main.py --dry-run latest
```

## What It Does

```
Raw Audio --> Transcribe --> Analyze --> Censor --> Clips --> Video --> Upload
                (Whisper)   (GPT-4o)   (beep)    (8x)     (MP4)   (6 platforms)
```

**18-step pipeline** with checkpoint/resume:

1. Download raw audio (Dropbox, RSS, or local)
2. Transcribe with Whisper/WhisperX (word-level timestamps)
3. Analyze with GPT-4o (summary, chapters, clip selection, social captions)
4. Auto-censor profanity with beep overlay
5. Normalize audio loudness
6. Extract 8 short clips optimized for YouTube Shorts
7. Generate subtitles, vertical video, thumbnails
8. Export MP3, update RSS feed
9. Upload to YouTube, Twitter/X, Bluesky, Instagram, TikTok
10. Generate blog post, index for search

## Commands

```bash
uv run main.py latest              # Process latest episode
uv run main.py ep25                # Process specific episode
uv run main.py list                # List available episodes
uv run main.py search "keyword"    # Full-text search
uv run main.py analytics all       # View engagement analytics
uv run main.py --client foo latest # Process for a specific client
uv run main.py health-check        # Validate all API credentials
```

**Flags:** `--dry-run`, `--test`, `--auto-approve`, `--client <name>`

## Tech Stack

| Category | Tools |
|----------|-------|
| Language | Python 3.12+ |
| AI/ML | OpenAI GPT-4o, Whisper/WhisperX, Ollama (Qwen 2.5), PyTorch + CUDA |
| Audio | pydub, FFmpeg, mutagen |
| Video | FFmpeg (h264_nvenc GPU encoding) |
| Image | Pillow |
| Platforms | YouTube API, Twitter/X API, Bluesky AT Protocol, Instagram Graph API, TikTok API |
| Storage | Dropbox API, SQLite FTS5 |
| Testing | pytest (1,255+ tests, ~94% coverage) |
| Linting | ruff (lint + format, pre-commit enforced) |
| Package Mgr | uv |

## Project Structure

```
main.py                  CLI entry point + orchestration
config.py                Central configuration (env vars)
pipeline/                Pipeline runner + step modules
uploaders/               Platform upload clients (7 platforms)
tests/                   55 test files, 1,255+ tests
output/                  Processed episode artifacts
clips/                   Generated short clips
```

## Testing

```bash
uv run pytest              # Run all tests
uv run pytest --cov        # With coverage
uv run ruff check .        # Lint
uv run ruff format .       # Format
```

## Documentation

Detailed documentation is in the [`docs/`](docs/) directory:

- [Project Overview](docs/project-overview.md) -- features, pipeline diagram, CLI reference
- [System Architecture](docs/system-architecture.md) -- component map, data flow, design patterns
- [Configuration Guide](docs/configuration-guide.md) -- all env vars, credential setup, multi-client
- [Testing Guide](docs/testing-guide.md) -- test conventions, mocking patterns, fixtures

## Contributing

1. Create a feature branch from `main`
2. Write tests for new functionality (every module gets a test file)
3. Ensure `uv run pytest` passes and `uv run ruff check .` is clean
4. New features must respect `--dry-run` and `--test` flags
5. Use `from logger import logger` for logging (never `print()`)
6. Add env vars to `config.py` and `.env.example`

## License

Private repository. All rights reserved.
