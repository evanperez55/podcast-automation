# Project: Podcast Automation (Fake Problems Podcast)

Automated production pipeline: transcription, AI content analysis, auto-censorship, clip generation, multi-platform distribution (YouTube, Spotify, Instagram, Twitter/X, TikTok).

## Commands
- Install: `pip install -r requirements.txt` (also need FFmpeg installed separately)
- Process latest episode: `python main.py latest`
- Process specific episode: `python main.py ep25`
- List episodes: `python main.py list`
- Search episodes: `python main.py search "keyword"`
- Analytics: `python main.py analytics [ep25|all]`
- Tests: `pytest` (or `pytest --cov`)
- Lint: `ruff check .` / `ruff format .`
- Topic engine: `python topic_scraper.py` / `python topic_scorer.py`
- Flags: `--dry-run`, `--test`, `--auto-approve`

## Pipeline Step Order
1 Download -> 2 Transcribe -> 3 Analyze -> 3.5 Topic tracker -> 4 Censor -> 4.5 Normalize -> 5 Clips -> 5.1 Clip approval -> 5.4 Subtitles -> 5.5 Video/Audiogram -> 5.6 Thumbnail -> 6 MP3 -> 7 Dropbox -> 7.5 RSS -> 8 Social media -> 8.5 Blog post -> 9 Search index

## Architecture
### Core Pipeline
- main.py -- CLI entry point + pipeline orchestration (latest|epN|list|search|analytics)
- config.py -- Central config (all env vars, podcast name, host names, censorship lists)
- audio_processor.py -- Audio processing + censorship
- transcription.py -- Whisper transcription
- diarize.py -- Speaker diarization (pyannote, needs HF_TOKEN)
- content_editor.py -- AI content analysis

### Content Generation
- blog_generator.py -- Auto-generate blog posts from transcripts
- thumbnail_generator.py -- Episode thumbnail generation (Pillow)
- audiogram_generator.py -- Animated waveform clip videos (FFmpeg)
- clip_previewer.py -- Interactive clip approval/selection

### Topic Engine
- topic_curator.py / topic_scraper.py / topic_scorer.py -- Topic discovery + scoring
- analytics.py -- YouTube/Twitter engagement metrics, feeds back into topic scoring

### Distribution
- uploaders/ -- Platform-specific uploaders (YouTube, Twitter, Instagram, TikTok, Spotify/RSS)
- rss_feed_generator.py -- RSS feed for Spotify
- notifications.py -- Discord webhook notifications
- scheduler.py -- Upload scheduling
- search_index.py -- FTS5 episode search index

### Supporting
- ollama_client.py -- Local LLM client (Ollama/Llama 3.1)
- credentials/ -- OAuth credentials
- data/ -- raw files; output/ -- finished episodes; clips/ -- generated clips

## Tech Stack
- Python 3.12+, Whisper/WhisperX, PyTorch, pydub + FFmpeg, Ollama (Llama 3.1), Pillow
- APIs: Dropbox, YouTube, Twitter (tweepy), Reddit (PRAW)
- No web framework -- CLI-driven pipeline

## Testing
- 279+ tests across 20 test files
- Convention: `tests/test_<module>.py` with `class Test<ClassName>` grouping
- Use `unittest.mock.patch` / `@patch.object(Config, ...)` for external deps
- All new features must respect `--dry-run`, `--test`, `--auto-approve` modes
- Pre-commit hook: ruff lint + ruff format (must pass before commit)

## Standards
- Flat module structure (all top-level .py files, no src/ directory)
- Each module has a `self.enabled` pattern gated by env vars in config.py
- Use GSD (`/gsd:new-project`) for multi-phase features

## Gotchas
- FFmpeg must be installed separately (default path: `C:\ffmpeg\bin\ffmpeg.exe`)
- Requires NVIDIA GPU + CUDA for fast Whisper -- CPU fallback is 3x slower
- config.py has hardcoded podcast name "Fake Problems Podcast" and host names for censorship
- Google Docs credential files are in credentials/ directory (credentials/google_docs_credentials.json, credentials/google_docs_token.json)
- requirements.txt comments out anthropic (replaced by Ollama) but config.py still references OPENAI_API_KEY
- `assets/podcast_logo.png` is untracked (8.6MB) -- needs Git LFS or compression before committing
