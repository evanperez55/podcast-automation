# Project: Podcast Automation (Fake Problems Podcast)

Automated production pipeline: transcription, AI content analysis, auto-censorship, clip generation, multi-platform distribution (YouTube, Spotify, Instagram, Twitter/X, TikTok).

## Commands
- Install: `uv sync` (also need FFmpeg installed separately)
- Process latest episode: `uv run main.py latest`
- Process specific episode: `uv run main.py ep25`
- List episodes: `uv run main.py list`
- Search episodes: `uv run main.py search "keyword"`
- Analytics: `uv run main.py analytics [ep25|all]`
- Tests: `uv run pytest` (or `uv run pytest --cov`)
- Lint: `uv run ruff check .` / `uv run ruff format .`
- Topic engine: `uv run topic_scraper.py` / `uv run topic_scorer.py`
- Multi-client: `uv run main.py --client <name> latest`
- Init new client: `uv run main.py init-client <name>`
- List clients: `uv run main.py list-clients`
- Validate client: `uv run main.py validate-client <name> [--ping]`
- Setup credentials: `uv run main.py setup-client <name> youtube`
- Client status: `uv run main.py status <name>`
- Find prospects: `uv run main.py find-prospects --genre comedy --min-episodes 20 --max-episodes 500`
- Gen pitch: `uv run main.py gen-pitch <slug> [ep_id]`
- Outreach tracker: `uv run main.py outreach <add|list|update|status> ...`
  - Add prospect: `uv run main.py outreach add <slug> <show_name> [email]`
  - List all: `uv run main.py outreach list`
  - Update status: `uv run main.py outreach update <slug> <status>`
  - View details: `uv run main.py outreach status <slug>`
- Flags: `--dry-run`, `--test`, `--auto-approve`, `--client <name>`, `--ping`, `--demo`

## Pipeline Step Order
1 Download -> 2 Transcribe -> 3 Analyze -> 3.5 Topic tracker -> 4 Censor -> 4.5 Normalize -> 5 Clips -> 5.1 Clip approval -> 5.4 Subtitles -> 5.5 Video/Audiogram -> 5.6 Thumbnail -> 6 MP3 -> 7 Dropbox -> 7.5 RSS -> 8 Social media -> 8.5 Blog post -> 9 Search index

## Architecture
See @.planning/codebase/ARCHITECTURE.md for full component map.
See @.planning/codebase/CONVENTIONS.md for code patterns and style.
See @.planning/codebase/TESTING.md for test patterns and mocking strategy.

- main.py (thin CLI) → pipeline/runner.py → pipeline/steps/ (ingest, audio, analysis, video, distribute)
- Flat module structure (all top-level .py files, no src/ directory)
- Each module has a `self.enabled` pattern gated by env vars in config.py
- Tech: Python 3.12+, Whisper/WhisperX, pydub + FFmpeg, Ollama (Llama 3.1), Pillow
- APIs: Dropbox, YouTube, Twitter (tweepy), Reddit (PRAW)

## Testing
- 518+ tests, shared fixtures in `tests/conftest.py`
- Convention: `tests/test_<module>.py` with `class Test<ClassName>` grouping
- Pre-commit hook: ruff lint + ruff format (`.githooks/pre-commit`)
- All new features must respect `--dry-run`, `--test`, `--auto-approve` modes

## Gotchas
- FFmpeg must be installed separately (default path: `C:\ffmpeg\bin\ffmpeg.exe`)
- Requires NVIDIA GPU + CUDA for fast Whisper -- CPU fallback is 3x slower
- config.py has hardcoded podcast name "Fake Problems Podcast" and host names for censorship
- Google Docs credential files are in credentials/ directory (credentials/google_docs_credentials.json, credentials/google_docs_token.json)
- requirements.txt is kept as fallback; pyproject.toml is the primary dependency source (managed by uv)
- `assets/podcast_logo.png` is untracked (8.6MB) -- needs Git LFS or compression before committing
