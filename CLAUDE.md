# Project: Podcast Automation (Fake Problems Podcast)

Automated production pipeline: transcription, AI content analysis, auto-censorship, clip generation, multi-platform distribution (YouTube, Spotify, Instagram, Twitter/X, TikTok).

## Commands
- Install: `pip install -r requirements.txt` (also need FFmpeg installed separately)
- Process latest episode: `python main.py latest`
- Process specific episode: `python main.py ep25`
- List episodes: `python main.py list`
- Tests: `pytest` (or `pytest --cov`)
- Topic engine: `python topic_scraper.py` / `python topic_scorer.py`

## Architecture
- main.py -- CLI entry point (latest|epN|list)
- config.py -- Central config (all env vars, hardcoded podcast name + host names)
- audio_processor.py -- Audio processing + censorship
- transcription.py -- Whisper transcription
- diarize.py -- Speaker diarization
- content_editor.py -- AI content analysis
- topic_curator.py / topic_scraper.py / topic_scorer.py -- Topic engine
- ollama_client.py -- Local LLM client (replaced Anthropic)
- uploaders/ -- Platform-specific uploaders
- credentials/ -- OAuth credentials
- data/ -- raw files; output/ -- finished episodes; clips/ -- generated clips

## Tech Stack
- Python 3.12+, Whisper/WhisperX, PyTorch, pydub + FFmpeg, Ollama (Llama 3.1)
- APIs: Dropbox, YouTube, Twitter (tweepy), Reddit (PRAW)
- No web framework -- CLI-driven pipeline

## Standards
- Flat module structure (all top-level .py files, no src/ directory)
- Use GSD (`/gsd:new-project`) for multi-phase features

## Gotchas
- FFmpeg must be installed separately (default path: `C:\ffmpeg\bin\ffmpeg.exe`)
- Requires NVIDIA GPU + CUDA for fast Whisper -- CPU fallback is 3x slower
- config.py has hardcoded podcast name "Fake Problems Podcast" and host names for censorship
- Google Docs credential files are in project root (google_docs_credentials.json, google_docs_token.json)
- requirements.txt comments out anthropic (replaced by Ollama) but config.py still references OPENAI_API_KEY
