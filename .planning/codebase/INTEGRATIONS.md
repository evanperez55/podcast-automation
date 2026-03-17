# External Integrations

**Analysis Date:** 2026-03-16

## APIs & External Services

**Cloud Storage:**
- Dropbox - Source of raw episode audio files (download) and destination for finished files (upload)
  - SDK/Client: `dropbox==12.0.2` via `dropbox_handler.py`
  - Auth: `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN` (OAuth auto-refresh) or `DROPBOX_ACCESS_TOKEN` (short-lived, deprecated)
  - Paths configured via `DROPBOX_FOLDER_PATH`, `DROPBOX_FINISHED_FOLDER`, `DROPBOX_EDITED_FOLDER`

**Video Platforms:**
- YouTube - Full episode and clip uploads; analytics retrieval
  - SDK/Client: `google-api-python-client` (`googleapiclient.discovery.build("youtube", "v3", ...)`) via `uploaders/youtube_uploader.py` and `analytics.py`
  - Auth: OAuth2 via `InstalledAppFlow`; credentials stored in `credentials/youtube_credentials.json`; token persisted at `credentials/youtube_token.pickle`
  - Scopes: `https://www.googleapis.com/auth/youtube.upload`
  - Env vars: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`

- TikTok - Short-form clip uploads
  - SDK/Client: `requests` (raw HTTP) against `https://open.tiktokapis.com/v2` via `uploaders/tiktok_uploader.py`
  - Auth: OAuth2 access token
  - Env vars: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`

**Social Media:**
- Twitter/X - Episode announcements and clip posts
  - SDK/Client: `tweepy==4.14.0` via `uploaders/twitter_uploader.py` and `repost_twitter.py`
  - Auth: OAuth 1.0a (API v1.1 for media uploads, API v2 for tweets)
  - Env vars: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET`
  - Note: Requires Twitter Developer Elevated access for media uploads

- Instagram - Reels uploads
  - SDK/Client: `requests` (raw HTTP) against Facebook Graph API `https://graph.facebook.com/v18.0` via `uploaders/instagram_uploader.py`
  - Auth: Long-lived access token via Facebook Developer App
  - Env vars: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID`
  - Note: Requires video hosted at a publicly accessible URL (e.g., Dropbox) before posting

**Topic Research:**
- Reddit - Trend scraping for topic discovery
  - SDK/Client: `praw==7.7.1` via `topic_scraper.py`
  - Auth: Client credentials (optional; falls back to unauthenticated JSON API)
  - Env vars: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`

**Documents & Collaboration:**
- Google Docs - Topic tracker document (mark discussed topics)
  - SDK/Client: `google-api-python-client` (`googleapiclient.discovery.build("docs", "v1", ...)`) via `google_docs_tracker.py`
  - Auth: OAuth2; credentials at `google_docs_credentials.json` (project root); token at `google_docs_token.json`
  - Scopes: `https://www.googleapis.com/auth/documents`
  - Env vars: `GOOGLE_DOC_ID`

**AI/LLM:**
- Ollama (local) - Content analysis, blog post generation, topic matching
  - SDK/Client: `requests` (raw HTTP) against `http://localhost:11434/api/generate` via `ollama_client.py`
  - Model: `llama3.2` (default), configurable
  - Auth: None (local service)
  - Env vars: `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
  - Note: `ollama_client.py` provides an Anthropic-compatible wrapper interface (`Ollama`, `Messages`, `MessageResponse`)

- HuggingFace - Pyannote speaker diarization model download
  - SDK/Client: Used internally by `whisperx`/`pyannote`
  - Auth: `HF_TOKEN` env var

**Notifications:**
- Discord - Pipeline event notifications (fire-and-forget webhooks)
  - SDK/Client: `requests` (raw HTTP) via `notifications.py`
  - Auth: Webhook URL (no token required beyond URL itself)
  - Env vars: `DISCORD_WEBHOOK_URL`
  - Enabled only if `DISCORD_WEBHOOK_URL` is set

## Data Storage

**Databases:**
- SQLite (FTS5) - Episode full-text search index
  - Connection: File at `output/episode_search.db`
  - Client: Python `sqlite3` stdlib module via `search_index.py`

**File Storage:**
- Local filesystem - Primary working storage
  - `downloads/` - Raw episode audio from Dropbox
  - `output/` - Finished MP3s, RSS feed XML, transcript JSON, blog posts, log file
  - `clips/` - Generated short clips and audiograms
  - `assets/` - Static assets (beep.wav, podcast_logo.png)
  - `credentials/` - OAuth token files (youtube_token.pickle, youtube_credentials.json)
  - `topic_data/` - Topic scores, analytics JSON files

- Dropbox (remote) - Source + archive of episode files

**Caching:**
- None (no Redis or in-memory cache layer)

## Authentication & Identity

**Auth Provider:**
- No user-facing authentication (CLI-only tool)
- All service auth is machine-to-machine:
  - YouTube: OAuth2 via pickled token file (`credentials/youtube_token.pickle`)
  - Google Docs: OAuth2 via JSON token file (`google_docs_token.json`)
  - Dropbox: OAuth2 refresh token via env vars
  - Twitter: OAuth 1.0a via env vars
  - Instagram: Long-lived access token via env var
  - TikTok: OAuth2 access token via env var

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Rollbar, etc.)

**Logs:**
- Python `logging` module via `logger.py`
- Console: INFO+ level, stdout
- File: DEBUG+ level at `output/podcast_automation.log`
- Format: `YYYY-MM-DD HH:MM:SS [LEVEL] message`

## CI/CD & Deployment

**Hosting:**
- Local machine (no cloud deployment detected)

**CI Pipeline:**
- None (no GitHub Actions, CircleCI, etc.)

**Pre-commit:**
- ruff lint + ruff format on staged files (enforced via pre-commit hook)

## Environment Configuration

**Required env vars (pipeline will fail without these):**
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN` - Dropbox access
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` - YouTube uploads
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` - Twitter posts
- `HF_TOKEN` - HuggingFace for diarization

**Optional env vars (features degrade gracefully):**
- `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID` - Instagram Reels
- `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN` - TikTok uploads
- `GOOGLE_DOC_ID` - Google Docs topic tracker
- `DISCORD_WEBHOOK_URL` - Discord notifications
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` - Reddit topic scraping (falls back to JSON API)
- `OPENAI_API_KEY` - Legacy; optionally used by `blog_generator.py` when `BLOG_USE_OPENAI=true`

**Secrets location:**
- `.env` file in project root (not committed to git)
- OAuth token files committed to `credentials/` and project root (google_docs_token.json, google_docs_credentials.json)

## Webhooks & Callbacks

**Incoming:**
- None (no inbound webhooks; CLI-only, no HTTP server)

**Outgoing:**
- Discord webhook via `notifications.py` (fire-and-forget POST to `DISCORD_WEBHOOK_URL`)

## Distribution (RSS)

**Podcast RSS Feed:**
- Generated locally as `output/podcast_feed.xml` via `rss_feed_generator.py`
- iTunes/Apple Podcasts namespace support (`http://www.itunes.com/dtds/podcast-1.0.dtd`)
- Submitted to Spotify and Apple Podcasts as an RSS URL (no direct API integration)
- No RSS hosting service detected; feed file requires manual hosting

---

*Integration audit: 2026-03-16*
