"""Client configuration loader for multi-client podcast automation.

Loads per-client YAML config files from clients/ directory and applies
overrides to the global Config class. Null/missing values fall back to
env var defaults.
"""

from pathlib import Path

import requests
import yaml

from config import Config
from logger import logger

# Mapping from YAML nested keys to flat Config attribute names
_YAML_TO_CONFIG = {
    # Podcast identity
    "podcast_name": "PODCAST_NAME",
    # Dropbox paths
    "dropbox.folder_path": "DROPBOX_FOLDER_PATH",
    "dropbox.finished_folder": "DROPBOX_FINISHED_FOLDER",
    "dropbox.edited_folder": "DROPBOX_EDITED_FOLDER",
    "dropbox.app_key": "DROPBOX_APP_KEY",
    "dropbox.app_secret": "DROPBOX_APP_SECRET",
    "dropbox.refresh_token": "DROPBOX_REFRESH_TOKEN",
    # YouTube
    "youtube.client_id": "YOUTUBE_CLIENT_ID",
    "youtube.client_secret": "YOUTUBE_CLIENT_SECRET",
    # Twitter
    "twitter.api_key": "TWITTER_API_KEY",
    "twitter.api_secret": "TWITTER_API_SECRET",
    "twitter.access_token": "TWITTER_ACCESS_TOKEN",
    "twitter.access_secret": "TWITTER_ACCESS_SECRET",
    # Instagram
    "instagram.access_token": "INSTAGRAM_ACCESS_TOKEN",
    "instagram.account_id": "INSTAGRAM_ACCOUNT_ID",
    # TikTok
    "tiktok.client_key": "TIKTOK_CLIENT_KEY",
    "tiktok.client_secret": "TIKTOK_CLIENT_SECRET",
    "tiktok.access_token": "TIKTOK_ACCESS_TOKEN",
    # Discord
    "discord.webhook_url": "DISCORD_WEBHOOK_URL",
    # Content settings
    "content.num_clips": "NUM_CLIPS",
    "content.clip_min_duration": "CLIP_MIN_DURATION",
    "content.clip_max_duration": "CLIP_MAX_DURATION",
    "content.clip_selection_mode": "CLIP_SELECTION_MODE",
    "content.compliance_style": "COMPLIANCE_STYLE",
    "content.whisper_model": "WHISPER_MODEL",
    # Episode source (dropbox | rss | local)
    "episode_source": "EPISODE_SOURCE",
    "rss_source.feed_url": "RSS_FEED_URL",
    "rss_source.episode_index": "RSS_EPISODE_INDEX",
    # RSS / podcast metadata
    "rss.description": "RSS_DESCRIPTION",
    "rss.author": "RSS_AUTHOR",
    "rss.email": "RSS_EMAIL",
    "rss.website_url": "RSS_WEBSITE_URL",
    "rss.artwork_url": "RSS_ARTWORK_URL",
    "rss.language": "RSS_LANGUAGE",
    "rss.explicit": "RSS_EXPLICIT",
    # Branding
    "branding.logo_path": "CLIENT_LOGO_PATH",
    # Output directories (optional — auto-derived from client name if not set)
    "output.dir": "OUTPUT_DIR",
    "output.downloads_dir": "DOWNLOAD_DIR",
    "output.clips_dir": "CLIPS_DIR",
    "output.topic_data_dir": "TOPIC_DATA_DIR",
}


def _get_nested(data: dict, dotted_key: str):
    """Retrieve a value from a nested dict using dot notation.

    Returns None if any key in the path is missing or None.
    """
    keys = dotted_key.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def load_client_config(client_name: str) -> dict:
    """Load a client YAML config file and return flat Config overrides.

    Args:
        client_name: Name of the client (matches clients/{name}.yaml)

    Returns:
        Dict mapping Config attribute names to override values.
        Only non-null values are included.

    Raises:
        FileNotFoundError: If the client YAML file doesn't exist.
        ValueError: If the YAML file is invalid or empty.
    """
    clients_dir = Config.BASE_DIR / "clients"
    yaml_path = clients_dir / f"{client_name}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Client config not found: {yaml_path}\n"
            f"Available clients: {_list_available_clients()}"
        )

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        raise ValueError(f"Invalid client config (empty or not a mapping): {yaml_path}")

    # Required field: content.names_to_remove must be explicitly present in YAML
    # (even if null or empty list) to prevent Fake Problems host names leaking
    content_section = data.get("content", {}) or {}
    if "names_to_remove" not in content_section:
        raise ValueError(
            f"Client config '{client_name}' is missing required field: "
            "content.names_to_remove\n"
            "Set to an empty list [] if this client has no host names to censor."
        )

    overrides = {}

    # Map YAML keys to Config attributes
    for yaml_key, config_attr in _YAML_TO_CONFIG.items():
        value = _get_nested(data, yaml_key)
        if value is not None:
            overrides[config_attr] = value

    # Special handling: names_to_remove and words_to_censor are lists
    names = _get_nested(data, "content.names_to_remove")
    if names is not None and isinstance(names, list):
        overrides["NAMES_TO_REMOVE"] = names

    words = _get_nested(data, "content.words_to_censor")
    if words is not None and isinstance(words, list):
        overrides["WORDS_TO_CENSOR"] = words

    # Special handling: RSS categories (list)
    rss_cats = _get_nested(data, "rss.categories")
    if rss_cats is not None and isinstance(rss_cats, list):
        overrides["RSS_CATEGORIES"] = rss_cats

    # Special handling: YouTube token path (per-client)
    youtube_token = _get_nested(data, "youtube.token_pickle")
    if youtube_token is not None:
        overrides["_YOUTUBE_TOKEN_PICKLE"] = str(Config.BASE_DIR / youtube_token)

    # Special handling: voice persona
    voice_persona = _get_nested(data, "content.voice_persona")
    if voice_persona is not None:
        overrides["VOICE_PERSONA"] = voice_persona

    # Special handling: blog voice
    blog_voice = _get_nested(data, "content.blog_voice")
    if blog_voice is not None:
        overrides["BLOG_VOICE"] = blog_voice

    # Special handling: scoring profile (nested dict)
    scoring = _get_nested(data, "content.scoring_profile")
    if scoring is not None and isinstance(scoring, dict):
        overrides["SCORING_PROFILE"] = scoring

    # Special handling: RSS_EPISODE_INDEX must be int
    if "RSS_EPISODE_INDEX" in overrides:
        overrides["RSS_EPISODE_INDEX"] = int(overrides["RSS_EPISODE_INDEX"])

    # Special handling: output directories are Path objects
    for dir_attr in ("OUTPUT_DIR", "DOWNLOAD_DIR", "CLIPS_DIR", "TOPIC_DATA_DIR"):
        if dir_attr in overrides:
            overrides[dir_attr] = Path(overrides[dir_attr])

    logger.info(
        "Loaded client config '%s' with %d overrides", client_name, len(overrides)
    )
    return overrides


def apply_client_config(overrides: dict) -> None:
    """Apply a dict of overrides to the Config class.

    Args:
        overrides: Dict mapping Config attribute names to values.
            Only non-None values will be applied.
    """
    applied = 0
    for attr, value in overrides.items():
        if value is not None:
            setattr(Config, attr, value)
            applied += 1

    logger.info("Applied %d client config overrides", applied)


def activate_client(client_name: str) -> dict:
    """Load and apply a client config, including output directory isolation.

    Convenience function combining load + apply + auto-derive output dirs.
    Returns the overrides dict for inspection.
    """
    overrides = load_client_config(client_name)
    apply_client_config(overrides)

    # Auto-isolate output directories per client (unless explicitly set in YAML)
    if "OUTPUT_DIR" not in overrides:
        Config.OUTPUT_DIR = Config.BASE_DIR / "output" / client_name
    if "DOWNLOAD_DIR" not in overrides:
        Config.DOWNLOAD_DIR = Config.BASE_DIR / "downloads" / client_name
    if "CLIPS_DIR" not in overrides:
        Config.CLIPS_DIR = Config.BASE_DIR / "clips" / client_name
    if "TOPIC_DATA_DIR" not in overrides:
        Config.TOPIC_DATA_DIR = Config.BASE_DIR / "topic_data" / client_name

    logger.info("Using client config: %s", client_name)
    return overrides


def init_client(client_name: str) -> None:
    """Scaffold a new client config from the example template.

    Creates clients/{name}.yaml and clients/{name}/ credentials directory.
    """
    clients_dir = Config.BASE_DIR / "clients"
    clients_dir.mkdir(exist_ok=True)

    yaml_path = clients_dir / f"{client_name}.yaml"
    creds_dir = clients_dir / client_name

    if yaml_path.exists():
        print(f"Client config already exists: {yaml_path}")
        return

    # Copy from example template
    template_path = clients_dir / "example-client.yaml"
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return

    template_text = template_path.read_text(encoding="utf-8")
    # Replace placeholder values with the actual client name
    client_text = template_text.replace("your-client-name", client_name)
    client_text = client_text.replace(
        "Your Podcast Name", client_name.replace("-", " ").title()
    )
    client_text = client_text.replace(
        "Your Podcast", client_name.replace("-", " ").title()
    )

    yaml_path.write_text(client_text, encoding="utf-8")
    creds_dir.mkdir(exist_ok=True)

    print(f"Created client config: {yaml_path}")
    print(f"Created credentials dir: {creds_dir}/")
    print()
    print("Next steps:")
    print(f"  1. Edit {yaml_path} with your podcast details")
    print(f"  2. Add platform credentials to {creds_dir}/")
    print(f"  3. Run: uv run main.py --client {client_name} --dry-run")


def get_client_names() -> list:
    """Return list of available client names (excluding example template)."""
    clients_dir = Config.BASE_DIR / "clients"
    if not clients_dir.exists():
        return []
    yamls = sorted(clients_dir.glob("*.yaml")) + sorted(clients_dir.glob("*.yml"))
    return [y.stem for y in yamls if y.stem != "example-client"]


def process_all(args: dict) -> None:
    """Process latest episode for every configured client.

    Args:
        args: CLI args dict (test_mode, dry_run, auto_approve, etc.)
    """
    clients = get_client_names()
    if not clients:
        print("No clients configured. Run: uv run main.py init-client <name>")
        return

    print(f"Processing {len(clients)} client(s): {', '.join(clients)}")
    print("=" * 60)

    results = {}
    for client_name in clients:
        print(f"\n{'=' * 60}")
        print(f"CLIENT: {client_name}")
        print(f"{'=' * 60}")

        client_args = dict(args)
        client_args["client_name"] = client_name

        try:
            from pipeline import run_with_notification

            run_with_notification(client_args)
            results[client_name] = "OK"
        except Exception as e:
            logger.warning("Client %s failed: %s", client_name, e)
            results[client_name] = f"FAILED: {e}"

    # Print summary
    print(f"\n{'=' * 60}")
    print("BATCH SUMMARY")
    print(f"{'=' * 60}")
    for name, status in results.items():
        print(f"  {name:20s}  {status}")


def list_clients() -> None:
    """Print available client configs."""
    clients_dir = Config.BASE_DIR / "clients"
    if not clients_dir.exists():
        print("No clients/ directory found. Run: uv run main.py init-client <name>")
        return

    yamls = sorted(clients_dir.glob("*.yaml")) + sorted(clients_dir.glob("*.yml"))
    # Exclude the example template
    yamls = [y for y in yamls if y.stem != "example-client"]

    if not yamls:
        print("No client configs found. Run: uv run main.py init-client <name>")
        return

    print("Available clients:")
    for yaml_path in yamls:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        podcast_name = data.get("podcast_name", "(unnamed)")
        print(f"  {yaml_path.stem:20s}  {podcast_name}")


def validate_client(client_name: str, ping: bool = False) -> None:
    """Validate a client's configuration and optionally test credentials.

    Args:
        client_name: Client to validate.
        ping: If True, make live API calls to verify credentials work.
    """
    # Load and activate client config
    activate_client(client_name)
    print(f"Validating client: {client_name} ({Config.PODCAST_NAME})")
    print()

    results = []

    # --- Required: Podcast identity ---
    _check(results, "Podcast Name", bool(Config.PODCAST_NAME), Config.PODCAST_NAME)

    # --- Episode source ---
    episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")

    if episode_source == "rss":
        # RSS source: check RSS_FEED_URL instead of Dropbox credentials
        has_feed_url = bool(getattr(Config, "RSS_FEED_URL", None))
        _check(
            results,
            "RSS Feed URL",
            has_feed_url,
            getattr(Config, "RSS_FEED_URL", None) if has_feed_url else None,
        )
        if ping and has_feed_url:
            _ping(results, "RSS Feed", _ping_rss_feed)
    else:
        # Dropbox source (default)
        has_oauth = all(
            [
                getattr(Config, "DROPBOX_REFRESH_TOKEN", None),
                getattr(Config, "DROPBOX_APP_KEY", None),
                getattr(Config, "DROPBOX_APP_SECRET", None),
            ]
        )
        has_token = bool(getattr(Config, "DROPBOX_ACCESS_TOKEN", None))
        _check(
            results,
            "Dropbox",
            has_oauth or has_token,
            "OAuth" if has_oauth else "Access token" if has_token else None,
        )
        if ping and (has_oauth or has_token):
            _ping(results, "Dropbox", _ping_dropbox)

    # --- OpenAI ---
    has_openai = bool(getattr(Config, "OPENAI_API_KEY", None))
    _check(results, "OpenAI (GPT-4o)", has_openai)
    if ping and has_openai:
        _ping(results, "OpenAI", _ping_openai)

    # --- YouTube ---
    token_path = getattr(Config, "_YOUTUBE_TOKEN_PICKLE", None)
    creds_path = Config.BASE_DIR / "credentials" / "youtube_credentials.json"
    has_yt = creds_path.exists() or (token_path and Path(token_path).exists())
    _check(
        results,
        "YouTube",
        has_yt,
        f"token: {token_path}" if token_path else "default credentials",
    )
    if ping and has_yt:
        _ping(results, "YouTube", _ping_youtube)

    # --- Twitter ---
    has_twitter = all(
        [
            getattr(Config, "TWITTER_API_KEY", None),
            getattr(Config, "TWITTER_API_SECRET", None),
            getattr(Config, "TWITTER_ACCESS_TOKEN", None),
            getattr(Config, "TWITTER_ACCESS_SECRET", None),
        ]
    )
    _check(results, "Twitter", has_twitter)
    if ping and has_twitter:
        _ping(results, "Twitter", _ping_twitter)

    # --- Instagram ---
    has_ig = bool(getattr(Config, "INSTAGRAM_ACCESS_TOKEN", None)) and bool(
        getattr(Config, "INSTAGRAM_ACCOUNT_ID", None)
    )
    _check(results, "Instagram", has_ig)
    if ping and has_ig:
        _ping(results, "Instagram", _ping_instagram)

    # --- Bluesky ---
    has_bluesky = bool(getattr(Config, "BLUESKY_HANDLE", None)) and bool(
        getattr(Config, "BLUESKY_APP_PASSWORD", None)
    )
    _check(results, "Bluesky", has_bluesky)
    if ping and has_bluesky:
        _ping(results, "Bluesky", _ping_bluesky)

    # --- TikTok ---
    has_tt = bool(getattr(Config, "TIKTOK_CLIENT_KEY", None)) and bool(
        getattr(Config, "TIKTOK_ACCESS_TOKEN", None)
    )
    _check(results, "TikTok", has_tt)

    # --- Discord ---
    has_discord = bool(getattr(Config, "DISCORD_WEBHOOK_URL", None))
    _check(results, "Discord", has_discord)
    if ping and has_discord:
        _ping(results, "Discord", _ping_discord)

    # --- Content settings ---
    has_names = bool(getattr(Config, "NAMES_TO_REMOVE", None))
    _check(
        results,
        "Censor names list",
        has_names,
        f"{len(Config.NAMES_TO_REMOVE)} names" if has_names else None,
    )

    has_words = bool(getattr(Config, "WORDS_TO_CENSOR", None))
    _check(
        results,
        "Censor words list",
        has_words,
        f"{len(Config.WORDS_TO_CENSOR)} words" if has_words else None,
    )

    # --- Output dirs ---
    _check(results, "Output dir", True, str(Config.OUTPUT_DIR))
    _check(results, "Clips dir", True, str(Config.CLIPS_DIR))

    # --- Active content configuration ---
    print()
    print("Active content configuration:")
    print(f"  Podcast name:    {Config.PODCAST_NAME}")
    print(f"  episode_source:  {episode_source}")

    voice = getattr(Config, "VOICE_PERSONA", None)
    if voice:
        preview = voice.strip().replace("\n", " ")[:80]
        if len(voice.strip()) > 80:
            preview += "..."
        print(f"  Voice persona:   {preview}")
    else:
        print("  Voice persona:   (built-in Fake Problems default)")

    names = Config.NAMES_TO_REMOVE
    if names:
        print(f"  names_to_remove: {names}")
    else:
        print("  names_to_remove: (empty -- no host censorship)")

    words = Config.WORDS_TO_CENSOR
    if words:
        print(f"  words_to_censor: {len(words)} words")
    else:
        print("  words_to_censor: (empty)")

    blog_voice = getattr(Config, "BLOG_VOICE", None)
    if blog_voice:
        print(f"  blog_voice:      configured ({len(blog_voice)} chars)")
    else:
        print("  blog_voice:      (not set)")

    scoring = getattr(Config, "SCORING_PROFILE", None)
    if scoring:
        print("  scoring_profile: configured")
    else:
        print("  scoring_profile: (not set)")

    # --- Print results ---
    print()
    configured = sum(1 for _, ok, _ in results if ok)
    total = sum(1 for _, ok, _ in results if ok is not None)
    skipped = sum(1 for _, ok, _ in results if ok is False)
    print(f"{configured} configured, {skipped} not configured, {total} total")

    if not ping:
        print("\nRun with --ping to test live API connections:")
        print(f"  uv run main.py validate-client {client_name} --ping")


def _check(results, name, ok, detail=None):
    """Record and print a validation check."""
    if ok:
        msg = f"  [OK]   {name}"
        if detail:
            msg += f"  ({detail})"
    else:
        msg = f"  [ ]    {name}  -- not configured"
    print(msg)
    results.append((name, ok, detail))


def _ping(results, name, fn):
    """Run a live API ping and record the result."""
    try:
        fn()
        print("         ^ ping OK")
    except Exception as e:
        err = str(e)[:80]
        print(f"         ^ ping FAILED: {err}")
        results.append((f"{name} ping", False, err))


def _ping_dropbox():
    """Test Dropbox connection."""
    from dropbox_handler import DropboxHandler

    handler = DropboxHandler()
    handler.dbx.files_list_folder(Config.DROPBOX_FOLDER_PATH)


def _ping_openai():
    """Test OpenAI API key."""
    import openai

    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    client.models.list()


def _ping_rss_feed():
    """Test RSS feed URL reachability via HTTP HEAD request."""
    url = getattr(Config, "RSS_FEED_URL", None)
    r = requests.head(url, timeout=10, allow_redirects=True)
    r.raise_for_status()


def _ping_youtube():
    """Test YouTube API credentials by listing channels."""
    from uploaders.youtube_uploader import YouTubeUploader

    yt = YouTubeUploader()
    # channels().list with "mine" verifies auth works
    result = yt.youtube.channels().list(part="snippet", mine=True).execute()
    channel = result.get("items", [{}])[0].get("snippet", {}).get("title", "unknown")
    print(f"         ^ channel: {channel}")


def _ping_twitter():
    """Test Twitter API credentials by fetching authenticated user."""
    from uploaders.twitter_uploader import TwitterUploader

    tw = TwitterUploader()
    user = tw.client.get_me()
    username = user.data.username if user.data else "unknown"
    print(f"         ^ @{username}")


def _ping_instagram():
    """Test Instagram token by fetching account info."""
    from uploaders.instagram_uploader import InstagramUploader

    ig = InstagramUploader()
    info = ig.get_account_info()
    if not info:
        raise RuntimeError("get_account_info returned None")
    print(f"         ^ @{info.get('username', 'unknown')}")


def _ping_bluesky():
    """Test Bluesky credentials by authenticating."""
    from uploaders.bluesky_uploader import BlueskyUploader

    BlueskyUploader()  # authenticates in __init__ — raises on failure
    print(f"         ^ handle: {Config.BLUESKY_HANDLE}")


def _ping_discord():
    """Test Discord webhook by sending a silent ping (no visible message)."""
    # Use the webhook info endpoint (GET) to verify it's valid without posting
    url = Config.DISCORD_WEBHOOK_URL
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    print(f"         ^ webhook: {data.get('name', 'unknown')}")


def client_status(client_name: str) -> None:
    """Show processing status for a client's episodes."""
    import json as _json

    activate_client(client_name)
    output_dir = Config.OUTPUT_DIR
    state_dir = output_dir / ".pipeline_state"

    print(f"Status for: {client_name} ({Config.PODCAST_NAME})")
    print(f"Output dir: {output_dir}")
    print()

    if not output_dir.exists():
        print("No output directory yet. Run your first episode:")
        print(f"  uv run main.py --client {client_name} latest")
        return

    # Find episode folders
    ep_dirs = sorted(
        [d for d in output_dir.iterdir() if d.is_dir() and d.name.startswith("ep_")],
        key=lambda d: d.name,
    )

    if not ep_dirs:
        print("No episodes processed yet.")
        return

    print(f"Episodes processed: {len(ep_dirs)}")
    print()

    for ep_dir in ep_dirs:
        ep_name = ep_dir.name
        line = f"  {ep_name:20s}"

        # Check pipeline state
        state_file = state_dir / f"{ep_name}.json"
        if state_file.exists():
            try:
                state = _json.loads(state_file.read_text(encoding="utf-8"))
                steps = list(state.get("completed_steps", {}).keys())
                updated = state.get("updated_at", "")[:16]
                line += f"  steps: {len(steps):2d}  last: {updated}"
            except Exception:
                line += "  (state unreadable)"
        else:
            line += "  (no state file)"

        # Check platform uploads
        platforms = []
        pid_file = ep_dir / "platform_ids.json"
        if pid_file.exists():
            try:
                pids = _json.loads(pid_file.read_text(encoding="utf-8"))
                platforms = list(pids.keys())
            except Exception:
                pass

        sched_file = ep_dir / "upload_schedule.json"
        pending = 0
        if sched_file.exists():
            try:
                sched = _json.loads(sched_file.read_text(encoding="utf-8"))
                for plat, info in sched.get("platforms", {}).items():
                    if info.get("status") == "pending" and plat not in platforms:
                        pending += 1
            except Exception:
                pass

        if platforms:
            line += f"  uploaded: {', '.join(platforms)}"
        if pending:
            line += f"  pending: {pending}"

        print(line)

    # Content calendar summary
    cal_path = Config.TOPIC_DATA_DIR / "content_calendar.json"
    if cal_path.exists():
        try:
            cal = _json.loads(cal_path.read_text(encoding="utf-8"))
            pending_slots = 0
            for ep_data in cal.values():
                for slot in ep_data.get("slots", {}).values():
                    if slot.get("status") == "pending":
                        pending_slots += 1
            if pending_slots:
                print(f"\nContent calendar: {pending_slots} pending slot(s)")
        except Exception:
            pass


def setup_client_platform(client_name: str, platform: str) -> None:
    """Run credential setup for a specific platform and client.

    Args:
        client_name: Client to configure.
        platform: Platform to set up (youtube, dropbox).
    """
    activate_client(client_name)

    if platform == "youtube":
        _setup_youtube(client_name)
    elif platform == "dropbox":
        print("Dropbox setup: Add these to your client YAML or .env:")
        print("  dropbox.app_key, dropbox.app_secret, dropbox.refresh_token")
        print("  See: https://www.dropbox.com/developers/apps")
    else:
        print(f"Unknown platform: {platform}")
        print("Supported: youtube, dropbox")


def _setup_youtube(client_name: str) -> None:
    """Run YouTube OAuth flow for a specific client."""
    # Determine token path
    token_path = getattr(Config, "_YOUTUBE_TOKEN_PICKLE", None)
    if not token_path:
        # Default per-client location
        token_path = str(
            Config.BASE_DIR / "clients" / client_name / "youtube_token.pickle"
        )

    token_file = Path(token_path)
    creds_path = Config.BASE_DIR / "credentials" / "youtube_credentials.json"

    print(f"YouTube OAuth Setup for: {client_name}")
    print(f"  Credentials: {creds_path}")
    print(f"  Token will be saved to: {token_file}")
    print()

    if not creds_path.exists():
        print(f"[ERROR] YouTube credentials file not found: {creds_path}")
        print()
        print("To set up YouTube:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create OAuth 2.0 credentials (Desktop app)")
        print("  3. Download as credentials/youtube_credentials.json")
        return

    # Delete expired token if it exists
    if token_file.exists():
        print(f"[INFO] Deleting existing token: {token_file}")
        token_file.unlink()

    token_file.parent.mkdir(parents=True, exist_ok=True)

    print("This will open a browser window for Google authorization.")
    input("Press Enter to continue...")
    print()

    try:
        from uploaders import YouTubeUploader

        YouTubeUploader(token_path=str(token_file))
        print()
        print("[SUCCESS] YouTube authentication complete!")
        print(f"Token saved to: {token_file}")
        print()
        print("Make sure your client YAML points to this token:")
        print("  youtube:")
        print(f'    token_pickle: "clients/{client_name}/youtube_token.pickle"')
    except Exception as e:
        print(f"\n[ERROR] Authentication failed: {e}")


def _list_available_clients() -> str:
    """List available client config files (for error messages)."""
    clients_dir = Config.BASE_DIR / "clients"
    if not clients_dir.exists():
        return "(no clients/ directory)"

    yamls = list(clients_dir.glob("*.yaml")) + list(clients_dir.glob("*.yml"))
    if not yamls:
        return "(no .yaml files in clients/)"

    names = [p.stem for p in yamls]
    return ", ".join(sorted(names))
