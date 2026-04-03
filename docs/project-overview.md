# Podcast Automation -- Project Overview

Automated production pipeline for the **Fake Problems Podcast**. Takes raw audio from Dropbox and produces a fully distributed episode: transcribed, analyzed, censored, clipped, converted to video, uploaded to YouTube/Twitter/Bluesky, and indexed for search.

## Quick Start

**Prerequisites:**
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- FFmpeg installed and available in PATH (or at `C:\ffmpeg\bin\ffmpeg.exe`)
- NVIDIA GPU + CUDA recommended (CPU fallback is 3x slower for transcription)
- Ollama running locally with `qwen2.5:7b` model pulled

**Install:**

```bash
uv sync
```

**Process the latest episode:**

```bash
uv run main.py latest
```

**Process a specific episode:**

```bash
uv run main.py ep25
```

**List available episodes:**

```bash
uv run main.py list
```

**Search episodes:**

```bash
uv run main.py search "artificial intelligence"
```

**View analytics:**

```bash
uv run main.py analytics ep25
uv run main.py analytics all
```

**Dry run (validate pipeline without I/O):**

```bash
uv run main.py --dry-run latest
```

## Features

**Core Pipeline:**
- Automatic episode download from Dropbox (or RSS feed, or local file)
- Whisper/WhisperX transcription with word-level timestamps
- GPT-4o content analysis: episode summary, show notes, chapters, social captions
- Automatic profanity/slur censorship with beep overlay
- LUFS audio normalization
- Smart clip extraction (8 clips per episode, optimized for YouTube Shorts)
- Interactive clip approval UI
- SRT subtitle generation for all clips
- Video conversion: vertical (9:16) for Shorts/Reels/TikTok, horizontal (16:9) for full episodes
- Audiogram waveform videos
- Thumbnail generation (1280x720 PNG)
- MP3 export with configurable bitrate

**Distribution:**
- YouTube uploads (full episode + Shorts)
- Twitter/X posting with media
- Bluesky cross-posting
- Instagram Reels
- TikTok uploads
- Spotify via RSS feed
- Dropbox upload of finished files

**Content Marketing:**
- 2-week content calendar with staggered Shorts release
- Quote card image generation
- Blog post generation from transcript
- Discord notifications for pipeline events
- Per-platform upload scheduling with optimal posting times

**Topic Engine (standalone):**
- Reddit/RSS topic scraping
- Ollama-powered topic scoring and curation
- Topic context injection into content analysis

**Operations:**
- Pipeline checkpoint/resume (crash recovery)
- PID-based pipeline lock (`output/.pipeline_lock`) prevents concurrent runs
- Credential health check (`health-check` command) for all connected services
- Full-text episode search (SQLite FTS5)
- YouTube/Twitter engagement analytics
- Content compliance checking
- Multi-client support (YAML configs, isolated outputs)
- Prospect finder and outreach tracker for new clients

## Pipeline Overview

```
  Raw Audio (Dropbox / RSS / Local)
         |
  [1] Download
         |
  [2] Transcribe (Whisper/WhisperX + CUDA)
         |
  [3] Analyze (GPT-4o: summary, clips, chapters, captions)
         |
  [3.5] Topic Tracker (Google Docs, optional)
         |
  [4] Censor (beep overlay at flagged timestamps)
         |
  [4.5] Normalize (LUFS loudness targeting)
         |
  [5] Create Clips (8 short clips per episode)
         |
  [5.1] Clip Approval (interactive terminal UI)
         |
  [5.4] Subtitles (SRT from transcript timestamps)
         |
  [5.5] Video Conversion (vertical + horizontal MP4)
         |
  [5.6] Thumbnail (1280x720 PNG via Pillow)
         |
  [6] MP3 Export
         |
  [7] Dropbox Upload (finished files)
         |
  [7.5] RSS Feed Update (for Spotify/Apple Podcasts)
         |
  [8] Platform Uploads (YouTube, Twitter, Bluesky, Instagram, TikTok)
         |
  [8.5] Blog Post Generation
         |
  [9] Search Index (SQLite FTS5)
```

Each step checkpoints its output. If the pipeline crashes, re-running the same episode resumes from the last completed step.

## CLI Commands

| Command | Description |
|---------|-------------|
| `uv run main.py latest` | Process the most recent episode |
| `uv run main.py ep25` | Process episode 25 |
| `uv run main.py list` | List available episodes |
| `uv run main.py search "keyword"` | Full-text search across episodes |
| `uv run main.py analytics [ep25\|all]` | View engagement analytics |
| `uv run main.py upload-scheduled` | Execute pending scheduled uploads |
| `uv run main.py --client <name> latest` | Process for a specific client |
| `uv run main.py init-client <name>` | Initialize a new client config |
| `uv run main.py list-clients` | List configured clients |
| `uv run main.py validate-client <name>` | Validate client configuration |
| `uv run main.py find-prospects` | Find potential podcast clients |
| `uv run main.py gen-pitch <slug>` | Generate a pitch for a prospect |
| `uv run main.py outreach <action>` | Manage prospect outreach |
| `uv run main.py health-check` | Validate all API credentials (YouTube, Twitter, Bluesky, Discord, Dropbox, OpenAI) |

**Flags:**

| Flag | Effect |
|------|--------|
| `--dry-run` | Validate pipeline wiring without performing I/O |
| `--test` | Use test/mock data |
| `--auto-approve` | Skip interactive clip approval |
| `--client <name>` | Target a specific client configuration |
| `--ping` | Test API connectivity during validation |

## Project Structure

```
podcast-automation/
    main.py                 CLI + pipeline orchestration
    config.py               Central configuration (env vars)
    pipeline/               Pipeline runner + step modules
        runner.py           Step orchestration
        steps/              Individual pipeline steps
    uploaders/              Platform-specific upload clients
    tests/                  55 test files, 1255+ tests
    output/                 Processed episode artifacts
    clips/                  Generated short clips
    downloads/              Raw audio staging
    credentials/            OAuth tokens (gitignored)
    assets/                 Static assets (logo, beep tone)
    topic_data/             Topic engine data
```

## Further Reading

- [System Architecture](system-architecture.md) -- pipeline design, data flow, component map
- [Configuration Guide](configuration-guide.md) -- all env vars, credential setup, multi-client config
- [Testing Guide](testing-guide.md) -- running tests, mocking patterns, coverage
