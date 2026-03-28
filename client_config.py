"""Client configuration loader for multi-client podcast automation.

Loads per-client YAML config files from clients/ directory and applies
overrides to the global Config class. Null/missing values fall back to
env var defaults.
"""

from pathlib import Path

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

    # Special handling: YouTube token path (per-client)
    youtube_token = _get_nested(data, "youtube.token_pickle")
    if youtube_token is not None:
        overrides["_YOUTUBE_TOKEN_PICKLE"] = str(Config.BASE_DIR / youtube_token)

    # Special handling: voice persona
    voice_persona = _get_nested(data, "content.voice_persona")
    if voice_persona is not None:
        overrides["VOICE_PERSONA"] = voice_persona

    # Special handling: scoring profile (nested dict)
    scoring = _get_nested(data, "content.scoring_profile")
    if scoring is not None and isinstance(scoring, dict):
        overrides["SCORING_PROFILE"] = scoring

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

    # --- Dropbox ---
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

    # --- Instagram ---
    has_ig = bool(getattr(Config, "INSTAGRAM_ACCESS_TOKEN", None)) and bool(
        getattr(Config, "INSTAGRAM_ACCOUNT_ID", None)
    )
    _check(results, "Instagram", has_ig)

    # --- TikTok ---
    has_tt = bool(getattr(Config, "TIKTOK_CLIENT_KEY", None)) and bool(
        getattr(Config, "TIKTOK_ACCESS_TOKEN", None)
    )
    _check(results, "TikTok", has_tt)

    # --- Discord ---
    has_discord = bool(getattr(Config, "DISCORD_WEBHOOK_URL", None))
    _check(results, "Discord", has_discord)

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
