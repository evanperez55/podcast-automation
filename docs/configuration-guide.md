# Configuration Guide

All configuration is centralized in `config.py` via the `Config` class. Values are loaded from environment variables (`.env` file supported via `python-dotenv`). Copy `.env.example` to `.env` and fill in your values.

## Environment Variables Reference

### Core / Required

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | OpenAI API key (required -- pipeline fails without it) |
| `EPISODE_SOURCE` | `"dropbox"` | Episode source: `dropbox`, `rss`, or `local` |
| `PODCAST_NAME` | `"Fake Problems Podcast"` | Podcast name used in titles and metadata |

### Dropbox

| Variable | Default | Description |
|----------|---------|-------------|
| `DROPBOX_APP_KEY` | *(none)* | Dropbox OAuth app key (recommended) |
| `DROPBOX_APP_SECRET` | *(none)* | Dropbox OAuth app secret |
| `DROPBOX_REFRESH_TOKEN` | *(none)* | Dropbox OAuth refresh token (auto-refreshes) |
| `DROPBOX_ACCESS_TOKEN` | *(none)* | Short-lived access token (deprecated) |
| `DROPBOX_FOLDER_PATH` | `"/Fake Problems Podcast/new_raw_files"` | Source folder for raw audio |
| `DROPBOX_FINISHED_FOLDER` | `"/Fake Problems Podcast/finished_files"` | Destination for finished files |
| `DROPBOX_EDITED_FOLDER` | `"/Fake Problems Podcast/edited_files"` | Destination for edited files |

### RSS Episode Source

| Variable | Default | Description |
|----------|---------|-------------|
| `RSS_FEED_URL` | *(none)* | RSS feed URL (when `EPISODE_SOURCE=rss`) |
| `RSS_EPISODE_INDEX` | `0` | Episode index in the RSS feed (0 = latest) |

### YouTube

| Variable | Default | Description |
|----------|---------|-------------|
| `YOUTUBE_CLIENT_ID` | *(none)* | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | *(none)* | Google OAuth client secret |

### Twitter/X

| Variable | Default | Description |
|----------|---------|-------------|
| `TWITTER_ENABLED` | `"true"` | Enable/disable Twitter uploads |
| `TWITTER_API_KEY` | *(none)* | Twitter API key |
| `TWITTER_API_SECRET` | *(none)* | Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | *(none)* | Twitter OAuth access token |
| `TWITTER_ACCESS_SECRET` | *(none)* | Twitter OAuth access secret |

### Bluesky

| Variable | Default | Description |
|----------|---------|-------------|
| `BLUESKY_HANDLE` | *(none)* | Bluesky handle (e.g., `yourpodcast.bsky.social`) |
| `BLUESKY_APP_PASSWORD` | *(none)* | Bluesky app password (generate in Settings > App Passwords) |

### Instagram

| Variable | Default | Description |
|----------|---------|-------------|
| `INSTAGRAM_ACCESS_TOKEN` | *(none)* | Instagram Graph API long-lived access token |
| `INSTAGRAM_ACCOUNT_ID` | *(none)* | Instagram business account ID |

### TikTok

| Variable | Default | Description |
|----------|---------|-------------|
| `TIKTOK_CLIENT_KEY` | *(none)* | TikTok OAuth client key |
| `TIKTOK_CLIENT_SECRET` | *(none)* | TikTok OAuth client secret |
| `TIKTOK_ACCESS_TOKEN` | *(none)* | TikTok access token (expires frequently) |

### Reddit

| Variable | Default | Description |
|----------|---------|-------------|
| `REDDIT_CLIENT_ID` | *(none)* | Reddit API client ID |
| `REDDIT_CLIENT_SECRET` | *(none)* | Reddit API client secret |
| `REDDIT_USERNAME` | *(none)* | Reddit username |
| `REDDIT_PASSWORD` | *(none)* | Reddit password |
| `REDDIT_USER_AGENT` | `"PodcastAutomation/1.0"` | Reddit API user agent string |
| `REDDIT_SUBREDDITS` | `""` | Comma-separated list of subreddits |

### Google Docs

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_DOC_ID` | *(none)* | Google Doc ID for topic tracker |

### Discord Notifications

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_WEBHOOK_URL` | *(none)* | Discord webhook URL for notifications |

### Upload Scheduling

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULE_YOUTUBE_DELAY_HOURS` | `0` | Hours to delay YouTube upload (0 = immediate) |
| `SCHEDULE_TWITTER_DELAY_HOURS` | `0` | Hours to delay Twitter post |
| `SCHEDULE_INSTAGRAM_DELAY_HOURS` | `0` | Hours to delay Instagram post |
| `SCHEDULE_TIKTOK_DELAY_HOURS` | `0` | Hours to delay TikTok upload |
| `SCHEDULE_YOUTUBE_POSTING_HOUR` | `14` | Optimal posting hour for YouTube (24h) |
| `SCHEDULE_TWITTER_POSTING_HOUR` | `10` | Optimal posting hour for Twitter (24h) |
| `SCHEDULE_INSTAGRAM_POSTING_HOUR` | `12` | Optimal posting hour for Instagram (24h) |
| `SCHEDULE_TIKTOK_POSTING_HOUR` | `12` | Optimal posting hour for TikTok (24h) |

### Feature Toggles

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTENT_CALENDAR_ENABLED` | `"true"` | Enable 2-week content calendar |
| `BLOG_ENABLED` | `"true"` | Enable blog post generation |
| `BLOG_USE_OPENAI` | `"true"` | Use OpenAI for blog posts (vs Ollama) |
| `ANALYTICS_ENABLED` | `"true"` | Enable analytics collection |
| `DAILY_CONTENT_ENABLED` | `"true"` | Enable daily content generation |
| `QUOTE_CARD_ENABLED` | `"true"` | Enable quote card image generation |
| `USE_AUDIOGRAM` | `"true"` | Enable audiogram waveform videos |
| `TWITTER_ENABLED` | `"true"` | Enable Twitter/X uploads |

### Audio Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MP3_BITRATE` | `"192k"` | MP3 export bitrate |
| `WHISPER_MODEL` | `"distil-large-v3"` | Whisper model name |
| `CLIP_FADE_MS` | `100` | Fade in/out duration for clips (ms) |
| `LUFS_TARGET` | `-16` | Target loudness (LUFS) |
| `CLIP_MAX_DURATION` | `60` | Maximum clip duration (seconds) |
| `CLIP_TARGET_DURATION` | `30` | Ideal clip length for YouTube Shorts |
| `NUM_CLIPS` | `8` | Number of clips to generate per episode |
| `CLIP_AUDIO_TOP_N` | `10` | Top-N high-energy segments for GPT-4o |

### Video / Visual Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NVENC_ENABLED` | *(auto-detect)* | Override GPU encoding detection (`true`/`false`) |
| `MAX_NVENC_SESSIONS` | `3` | Max parallel NVENC encoding sessions |
| `THUMBNAIL_FONT` | *(none)* | Custom font path for thumbnails |
| `THUMBNAIL_BG_COLOR` | `"#1a1a2e"` | Thumbnail background color |
| `THUMBNAIL_TEXT_COLOR` | `"#ffffff"` | Thumbnail text color |
| `THUMBNAIL_BADGE_COLOR` | `"#e94560"` | Thumbnail badge/accent color |
| `QUOTE_CARD_BG_COLOR` | `"#1a1a2e"` | Quote card background color |
| `QUOTE_CARD_TEXT_COLOR` | `"#ffffff"` | Quote card text color |
| `QUOTE_CARD_ACCENT_COLOR` | `"#e94560"` | Quote card accent color |
| `AUDIOGRAM_BG_COLOR` | `"0x1a1a2e"` | Audiogram background color (hex) |
| `AUDIOGRAM_WAVE_COLOR` | `"0xe94560"` | Audiogram waveform color (hex) |

### AI / LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama API base URL |
| `OLLAMA_MODEL` | `"qwen2.5:7b"` | Ollama model for topic scoring |
| `OPENAI_ANALYSIS_MODEL` | `"gpt-4.1-mini"` | OpenAI model for content analysis |
| `OPENAI_BLOG_MODEL` | `"gpt-4.1-mini"` | OpenAI model for blog generation |
| `HF_TOKEN` | *(none)* | HuggingFace token for pyannote diarization |

### Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `FFMPEG_PATH` | *(auto-detect)* | FFmpeg binary path |
| `FFPROBE_PATH` | *(auto-detect)* | FFprobe binary path |
| `BEEP_SOUND_PATH` | `"./assets/beep.wav"` | Path to censorship beep sound |

FFmpeg detection order: `FFMPEG_PATH` env var > `shutil.which("ffmpeg")` (PATH) > `C:\ffmpeg\bin\ffmpeg.exe`.

## Credential Setup

### YouTube OAuth2

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project
2. Enable the YouTube Data API v3
3. Create OAuth 2.0 Client ID credentials (Desktop application)
4. Download the credentials JSON file
5. Save as `credentials/youtube_credentials.json`
6. Set `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in `.env`
7. On first upload, a browser window opens for OAuth consent. The token is saved to `credentials/youtube_token.pickle`

### Twitter/X API

1. Apply for a [Twitter Developer account](https://developer.twitter.com/)
2. Create a project and app with Read and Write permissions
3. Generate API Key, API Secret, Access Token, and Access Secret
4. Set all four values in `.env`:
   ```
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_SECRET=your_access_secret
   ```
5. Twitter API is pay-per-use (approximately $0.01 per tweet)

### Bluesky

1. Log into your Bluesky account
2. Go to Settings > App Passwords
3. Create a new app password
4. Set in `.env`:
   ```
   BLUESKY_HANDLE=yourpodcast.bsky.social
   BLUESKY_APP_PASSWORD=your_app_password
   ```

### Dropbox OAuth2

1. Create a Dropbox app at [Dropbox Developer Console](https://www.dropbox.com/developers/apps)
2. Set permissions: `files.content.read`, `files.content.write`
3. Generate a refresh token using the OAuth2 flow
4. Set in `.env`:
   ```
   DROPBOX_APP_KEY=your_app_key
   DROPBOX_APP_SECRET=your_app_secret
   DROPBOX_REFRESH_TOKEN=your_refresh_token
   ```

### Discord Webhook

1. In your Discord server, go to Server Settings > Integrations > Webhooks
2. Create a new webhook and copy the URL
3. Set in `.env`:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

### Google Docs (Topic Tracker)

1. Enable the Google Docs API in Google Cloud Console
2. Create OAuth 2.0 credentials (Desktop application)
3. Save credentials as `credentials/google_docs_credentials.json`
4. Set `GOOGLE_DOC_ID` in `.env` to the document ID from the Google Doc URL
5. On first run, OAuth browser flow saves token to `credentials/google_docs_token.json`

### HuggingFace (Speaker Diarization)

1. Create a [HuggingFace account](https://huggingface.co/)
2. Accept the pyannote model license agreements
3. Generate an access token at Settings > Access Tokens
4. Set in `.env`:
   ```
   HF_TOKEN=hf_your_token
   ```

## Multi-Client Configuration

The system supports multiple podcast clients via YAML configuration files. Each client gets isolated output directories and independent platform credentials.

### Initialize a New Client

```bash
uv run main.py init-client my-podcast
```

This creates a YAML config at `clients/my-podcast/config.yaml`.

### Client Config Structure

```yaml
name: My Podcast
slug: my-podcast
podcast_name: "My Podcast Name"

# Override any Config attribute
dropbox_folder_path: "/My Podcast/raw"
dropbox_finished_folder: "/My Podcast/finished"

# Platform credentials (override global .env)
youtube_client_id: "..."
youtube_client_secret: "..."
twitter_api_key: "..."

# Content settings
names_to_remove:
  - "Host Name"
words_to_censor:
  - "word1"
```

### Process for a Specific Client

```bash
uv run main.py --client my-podcast latest
```

### Manage Clients

```bash
uv run main.py list-clients                    # List all configured clients
uv run main.py validate-client my-podcast      # Validate config
uv run main.py validate-client my-podcast --ping  # Validate + test API connectivity
uv run main.py status my-podcast               # View client status
```

## Disabling Features

Any feature can be disabled by setting its env var to `"false"`. The module will log a warning and skip its work without crashing the pipeline:

```bash
# Disable specific features
BLOG_ENABLED=false
ANALYTICS_ENABLED=false
TWITTER_ENABLED=false
QUOTE_CARD_ENABLED=false
USE_AUDIOGRAM=false
CONTENT_CALENDAR_ENABLED=false
DAILY_CONTENT_ENABLED=false
```

Features also disable themselves automatically when their required credentials are missing. For example, YouTube uploads are skipped if `YOUTUBE_CLIENT_ID` is not set.

## Directory Structure

The pipeline creates these directories automatically:

| Directory | Purpose |
|-----------|---------|
| `downloads/` | Raw audio staging (gitignored) |
| `output/` | Processed artifacts per episode (gitignored) |
| `output/ep_N/` | Episode-specific outputs |
| `output/.pipeline_state/` | Checkpoint JSON files |
| `clips/` | Generated clips per episode (gitignored) |
| `clips/ep_N/` | Episode-specific clips |
| `credentials/` | OAuth token files (gitignored) |
| `topic_data/` | Topic engine data (gitignored) |
| `assets/` | Static assets (logo, beep tone) |
