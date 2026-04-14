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
- Find prospects: `uv run main.py find-prospects --genre business --min-episodes 20 --max-episodes 80 --save-all`
- Gen pitch: `uv run main.py gen-pitch <slug> [ep_id]`
- Outreach tracker: `uv run main.py outreach <add|list|update|status> ...`
  - Add prospect: `uv run main.py outreach add <slug> <show_name> [email]`
  - List all: `uv run main.py outreach list`
  - Update status: `uv run main.py outreach update <slug> <status>`
  - View details: `uv run main.py outreach status <slug>`
- Flags: `--dry-run`, `--test`, `--auto-approve`, `--client <name>`, `--ping`, `--demo`

## Pipeline Step Order
1 Download -> 2 Transcribe -> 3 Analyze -> 3.5 Topic tracker -> 4 Censor -> 4.5 Normalize -> 5 Clips -> 5.1 Clip approval -> 5.4 Subtitles -> 5.5 Video/Audiogram -> 5.6 Thumbnail -> 6 MP3 -> 7 Dropbox -> 7.5 RSS -> 8 Social media -> 8.5 Blog post -> 9 Search index

## Architecture (summary — read .planning/codebase/ for full docs)
- main.py (thin CLI) → pipeline/runner.py → pipeline/steps/ (ingest, audio, analysis, video, distribute)
- Flat module structure (all top-level .py files, no src/ directory)
- Each module has a `self.enabled` pattern gated by env vars in config.py
- Config via class attributes: `from config import Config; Config.ATTR`
- Logging via `from logger import logger` singleton (never print())
- Tests: `tests/test_<module>.py`, `class Test<ClassName>`, `unittest.mock.patch` for external deps
- Tech: Python 3.12+, Whisper/WhisperX, pydub + FFmpeg, Ollama (Llama 3.1), Pillow
- APIs: Dropbox, YouTube, Twitter (tweepy), Reddit (PRAW)

## Decisions (do not revisit without discussion)
- Filler words KEPT in transcripts — removing kills comedy timing
- Twitter API is pay-per-use ~$0.01/tweet, NOT $100/mo subscription
- No CI/CD pipeline — manual GitHub Actions only
- Pitch angle is FULL AUTOMATION (not "you don't have clips") — one episode in, 15+ content pieces out
- Episode source for prospects is RSS, not Dropbox
- NEVER run multiple episode pipelines simultaneously — kills GPU/RAM
- Website is org-based GitHub Pages (fakeproblemspodcast org, not personal account)
- cuDNN DLLs manually copied — may break on venv rebuild

## Testing
- 1500+ tests, shared fixtures in `tests/conftest.py`
- Convention: `tests/test_<module>.py` with `class Test<ClassName>` grouping (pipeline steps use `test_<name>_step.py`)
- Pre-commit hook: ruff lint + ruff format + pytest (`.githooks/pre-commit`) — test failures block commit
- All new features must respect `--dry-run`, `--test`, `--auto-approve` modes
- **Every new source file needs a matching test file.** Exceptions (already documented): `main.py` (thin CLI dispatcher — covered by `test_main_exit_code.py`), `logger.py` (stdlib logging wrapper — no logic to test), `generate_logo.py` (one-shot DALL-E script), `setup_dropbox_oauth.py` / `setup_google_docs.py` / `setup_instagram.py` / `setup_youtube_auth.py` (interactive browser OAuth — tested manually per integration), `__init__.py` files (re-exports only), `scripts/archive/*` (dead code). Anything else added without a test should be flagged at review time.

## Gotchas
- FFmpeg must be installed separately (default path: `C:\ffmpeg\bin\ffmpeg.exe`)
- Requires NVIDIA GPU + CUDA for fast Whisper -- CPU fallback is 3x slower
- config.py has hardcoded podcast name "Fake Problems Podcast" and host names for censorship
- Google Docs credential files are in credentials/ directory (credentials/google_docs_credentials.json, credentials/google_docs_token.json)
- requirements.txt is kept as fallback; pyproject.toml is the primary dependency source (managed by uv)
- `assets/podcast_logo.png` is untracked (8.6MB) -- needs Git LFS or compression before committing

## Podcast Growth Data (for content generation, clip selection, marketing)
- Clips → 65% audience reach growth. Aim for 3-5 clips per episode, 30-60s sweet spot
- Hook in first 2-3 seconds is critical (question, bold claim, surprising fact)
- Subtitles mandatory — most social users scroll with sound off
- Transcripts → 7.2x organic traffic vs audio-only pages
- Show notes → 20% more organic traffic when 300+ words with timestamps
- Audio normalization is table stakes — 78% of listeners leave over bad audio
- YouTube Shorts have longest shelf life (months of views via search)
- TikTok has highest engagement (3.15%), Instagram Reels best for shares
- Apple ranks on subscriber growth VELOCITY (last 24-72 hrs), not total count
- Spotify rewards 15-day release cycles with ~5 position chart boost
- Clip distribution across episode timeline matters — represent beginning, middle, end
- One episode should generate 15+ content pieces (clips, blog, captions, quotes)
- See `output/podcast_growth_research.md` for full data with sources
