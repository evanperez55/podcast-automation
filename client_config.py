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


def _list_available_clients() -> str:
    """List available client config files."""
    clients_dir = Config.BASE_DIR / "clients"
    if not clients_dir.exists():
        return "(no clients/ directory)"

    yamls = list(clients_dir.glob("*.yaml")) + list(clients_dir.glob("*.yml"))
    if not yamls:
        return "(no .yaml files in clients/)"

    names = [p.stem for p in yamls]
    return ", ".join(sorted(names))
