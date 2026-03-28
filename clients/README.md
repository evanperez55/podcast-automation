# Client Setup Guide

This pipeline supports multiple podcast clients. Each client gets its own YAML config, credentials directory, and isolated output.

## Quick Start

```bash
# 1. Scaffold a new client
uv run main.py init-client my-podcast

# 2. Edit the generated config
#    clients/my-podcast.yaml

# 3. Validate the setup
uv run main.py --client my-podcast --dry-run

# 4. Process an episode
uv run main.py --client my-podcast latest
```

## Client Config (YAML)

Each client has a `clients/{name}.yaml` file. See `example-client.yaml` for the full template.

**Required fields:**
- `client_name` -- unique identifier (matches filename)
- `podcast_name` -- display name used in prompts, RSS, blog posts

**Credentials** (set in YAML or as env vars -- YAML takes precedence):
- `dropbox.*` -- Dropbox OAuth (app_key, app_secret, refresh_token)
- `youtube.*` -- YouTube OAuth (client_id, client_secret, token_pickle)
- `twitter.*` -- Twitter API keys
- `instagram.*` -- Instagram access token + account ID
- `tiktok.*` -- TikTok credentials
- `discord.webhook_url` -- Discord notifications

**Content settings:**
- `content.num_clips` -- number of clips to extract (default: 3)
- `content.clip_min_duration` / `clip_max_duration` -- clip length bounds
- `content.names_to_remove` -- host names to censor from transcript
- `content.words_to_censor` -- slurs/words to beep out
- `content.voice_persona` -- custom GPT-4o persona prompt (null = default)

**Output directories** (optional -- auto-derived from client name if omitted):
- `output.dir`, `output.downloads_dir`, `output.clips_dir`, `output.topic_data_dir`

## Credentials Directory

Each client gets a `clients/{name}/` directory (gitignored) for platform tokens:
- `clients/my-podcast/youtube_token.pickle` -- YouTube OAuth token

Point to it in YAML:
```yaml
youtube:
  token_pickle: "clients/my-podcast/youtube_token.pickle"
```

## Output Isolation

When using `--client`, output automatically goes to per-client subdirectories:
```
output/my-podcast/ep_25/       # episode output
clips/my-podcast/ep_25/        # audio/video clips
downloads/my-podcast/          # raw downloads
topic_data/my-podcast/         # content calendar, scored topics
```

Without `--client`, output goes to the default locations (backward compatible).

## CLI Commands

```bash
# List available clients
uv run main.py list-clients

# Scaffold a new client
uv run main.py init-client <name>

# Process with a specific client
uv run main.py --client <name> latest
uv run main.py --client <name> ep25
uv run main.py --client <name> --dry-run

# Run scheduled uploads for a client
uv run main.py --client <name> upload-scheduled

# Analytics for a client
uv run main.py --client <name> analytics
```

## Null Values = Env Var Fallback

Any value set to `null` in YAML falls back to the corresponding environment variable. This lets you share common credentials across clients via `.env` while overriding only what differs per client.
