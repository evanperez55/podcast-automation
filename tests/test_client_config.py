"""Tests for client_config module — multi-client YAML loading and Config patching."""

import pytest
from pathlib import Path
from unittest.mock import patch

from config import Config


# Sample YAML content for tests
SAMPLE_CLIENT_YAML = """
client_name: "test-client"
podcast_name: "Test Podcast"

dropbox:
  folder_path: "/Test Podcast/raw"
  finished_folder: "/Test Podcast/finished"
  edited_folder: null
  app_key: null

youtube:
  client_id: "yt-test-id"
  client_secret: null
  token_pickle: "clients/test-client/youtube_token.pickle"

twitter:
  api_key: "tw-test-key"
  api_secret: null

content:
  num_clips: 5
  clip_min_duration: 10
  clip_max_duration: 45
  names_to_remove:
    - "Alice"
    - "Bob"
  words_to_censor:
    - "badword"
  voice_persona: "You are a friendly podcast host."
"""

MINIMAL_YAML = """
client_name: "minimal"
podcast_name: "Minimal Podcast"
content:
  names_to_remove: []
"""

EMPTY_YAML = ""

INVALID_YAML = "just a string, not a mapping"


class TestLoadClientConfig:
    """Tests for load_client_config()."""

    def test_load_valid_config(self, tmp_path, monkeypatch):
        """Loading a valid YAML produces correct Config overrides."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-client.yaml").write_text(SAMPLE_CLIENT_YAML)

        from client_config import load_client_config

        overrides = load_client_config("test-client")

        assert overrides["PODCAST_NAME"] == "Test Podcast"
        assert overrides["DROPBOX_FOLDER_PATH"] == "/Test Podcast/raw"
        assert overrides["DROPBOX_FINISHED_FOLDER"] == "/Test Podcast/finished"
        assert overrides["YOUTUBE_CLIENT_ID"] == "yt-test-id"
        assert overrides["TWITTER_API_KEY"] == "tw-test-key"
        assert overrides["NUM_CLIPS"] == 5
        assert overrides["CLIP_MIN_DURATION"] == 10
        assert overrides["CLIP_MAX_DURATION"] == 45
        assert overrides["NAMES_TO_REMOVE"] == ["Alice", "Bob"]
        assert overrides["WORDS_TO_CENSOR"] == ["badword"]
        assert overrides["VOICE_PERSONA"] == "You are a friendly podcast host."

    def test_null_values_excluded(self, tmp_path, monkeypatch):
        """Null YAML values are not included in overrides dict."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-client.yaml").write_text(SAMPLE_CLIENT_YAML)

        from client_config import load_client_config

        overrides = load_client_config("test-client")

        # These were null in the YAML
        assert "DROPBOX_EDITED_FOLDER" not in overrides
        assert "DROPBOX_APP_KEY" not in overrides
        assert "YOUTUBE_CLIENT_SECRET" not in overrides
        assert "TWITTER_API_SECRET" not in overrides

    def test_minimal_config(self, tmp_path, monkeypatch):
        """A minimal YAML with only client_name and podcast_name works."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "minimal.yaml").write_text(MINIMAL_YAML)

        from client_config import load_client_config

        overrides = load_client_config("minimal")

        assert overrides["PODCAST_NAME"] == "Minimal Podcast"
        assert overrides["NAMES_TO_REMOVE"] == []
        assert len(overrides) == 2  # podcast_name + NAMES_TO_REMOVE (empty list)

    def test_missing_file_raises(self, tmp_path, monkeypatch):
        """Loading a nonexistent client raises FileNotFoundError."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()

        from client_config import load_client_config

        with pytest.raises(FileNotFoundError, match="Client config not found"):
            load_client_config("nonexistent")

    def test_empty_yaml_raises(self, tmp_path, monkeypatch):
        """An empty YAML file raises ValueError."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "empty.yaml").write_text(EMPTY_YAML)

        from client_config import load_client_config

        with pytest.raises(ValueError, match="Invalid client config"):
            load_client_config("empty")

    def test_invalid_yaml_raises(self, tmp_path, monkeypatch):
        """A YAML that parses to a string (not dict) raises ValueError."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "bad.yaml").write_text(INVALID_YAML)

        from client_config import load_client_config

        with pytest.raises(ValueError, match="Invalid client config"):
            load_client_config("bad")

    def test_missing_names_to_remove_raises(self, tmp_path, monkeypatch):
        """YAML without content.names_to_remove raises ValueError with clear message."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = 'client_name: "no-names"\npodcast_name: "No Names Podcast"\n'
        (clients_dir / "no-names.yaml").write_text(yaml_content)

        from client_config import load_client_config

        with pytest.raises(ValueError, match="content.names_to_remove"):
            load_client_config("no-names")

    def test_null_names_to_remove_is_valid(self, tmp_path, monkeypatch):
        """YAML with names_to_remove: null loads without error (field is present)."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = 'client_name: "null-names"\npodcast_name: "Null Names"\ncontent:\n  names_to_remove: null\n'
        (clients_dir / "null-names.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("null-names")
        # null means field is present; NAMES_TO_REMOVE is NOT in overrides (value is null)
        assert "NAMES_TO_REMOVE" not in overrides

    def test_empty_names_to_remove_is_valid(self, tmp_path, monkeypatch):
        """YAML with names_to_remove: [] loads without error and sets NAMES_TO_REMOVE to []."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = 'client_name: "empty-names"\npodcast_name: "Empty Names"\ncontent:\n  names_to_remove: []\n'
        (clients_dir / "empty-names.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("empty-names")
        assert overrides["NAMES_TO_REMOVE"] == []

    def test_youtube_token_path(self, tmp_path, monkeypatch):
        """YouTube token pickle path is resolved relative to BASE_DIR."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-client.yaml").write_text(SAMPLE_CLIENT_YAML)

        from client_config import load_client_config

        overrides = load_client_config("test-client")

        expected = str(tmp_path / "clients" / "test-client" / "youtube_token.pickle")
        assert overrides["_YOUTUBE_TOKEN_PICKLE"] == expected


class TestApplyClientConfig:
    """Tests for apply_client_config()."""

    def test_applies_overrides(self, monkeypatch):
        """apply_client_config patches Config class attributes."""
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)

        from client_config import apply_client_config

        apply_client_config({"PODCAST_NAME": "New Podcast"})
        assert Config.PODCAST_NAME == "New Podcast"

    def test_skips_none_values(self, monkeypatch):
        """None values in overrides dict are not applied."""
        original = Config.PODCAST_NAME
        monkeypatch.setattr(Config, "PODCAST_NAME", original)

        from client_config import apply_client_config

        apply_client_config({"PODCAST_NAME": None})
        assert Config.PODCAST_NAME == original

    def test_sets_new_attributes(self):
        """Overrides can set attributes that don't exist on Config yet."""
        from client_config import apply_client_config

        apply_client_config({"_YOUTUBE_TOKEN_PICKLE": "/some/path"})
        assert Config._YOUTUBE_TOKEN_PICKLE == "/some/path"


class TestNewYamlMappings:
    """Tests for new YAML -> Config attribute mappings added for genre awareness."""

    def test_clip_selection_mode_mapping(self):
        """content.clip_selection_mode maps to CLIP_SELECTION_MODE in _YAML_TO_CONFIG."""
        from client_config import _YAML_TO_CONFIG

        assert "content.clip_selection_mode" in _YAML_TO_CONFIG
        assert _YAML_TO_CONFIG["content.clip_selection_mode"] == "CLIP_SELECTION_MODE"

    def test_compliance_style_mapping(self):
        """content.compliance_style maps to COMPLIANCE_STYLE in _YAML_TO_CONFIG."""
        from client_config import _YAML_TO_CONFIG

        assert "content.compliance_style" in _YAML_TO_CONFIG
        assert _YAML_TO_CONFIG["content.compliance_style"] == "COMPLIANCE_STYLE"


class TestOutputIsolation:
    """Tests for per-client output directory isolation."""

    def test_output_dirs_auto_derived(self, tmp_path, monkeypatch):
        """When --client is used, output dirs include client name."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-client.yaml").write_text(
            MINIMAL_YAML.replace("minimal", "test-client")
        )

        from client_config import load_client_config, apply_client_config

        overrides = load_client_config("test-client")
        apply_client_config(overrides)

        # Simulate runner.py auto-isolation logic
        client_name = "test-client"
        if "OUTPUT_DIR" not in overrides:
            Config.OUTPUT_DIR = Config.BASE_DIR / "output" / client_name
        if "CLIPS_DIR" not in overrides:
            Config.CLIPS_DIR = Config.BASE_DIR / "clips" / client_name

        assert Config.OUTPUT_DIR == tmp_path / "output" / "test-client"
        assert Config.CLIPS_DIR == tmp_path / "clips" / "test-client"

    def test_explicit_output_dir_not_overridden(self, tmp_path, monkeypatch):
        """Explicit output.dir in YAML takes precedence over auto-derivation."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = """
client_name: "custom"
podcast_name: "Custom Podcast"
content:
  names_to_remove: []
output:
  dir: "/custom/output/path"
"""
        (clients_dir / "custom.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("custom")

        assert "OUTPUT_DIR" in overrides
        assert overrides["OUTPUT_DIR"] == Path("/custom/output/path")

    def test_output_dir_values_are_paths(self, tmp_path, monkeypatch):
        """Output directory overrides from YAML are converted to Path objects."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = """
client_name: "pathtest"
podcast_name: "Path Test"
content:
  names_to_remove: []
output:
  dir: "/some/output"
  clips_dir: "/some/clips"
"""
        (clients_dir / "pathtest.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("pathtest")

        assert isinstance(overrides["OUTPUT_DIR"], Path)
        assert isinstance(overrides["CLIPS_DIR"], Path)


class TestActivateClient:
    """Tests for activate_client() — combined load + apply + output isolation."""

    def test_activate_sets_config_and_output_dirs(self, tmp_path, monkeypatch):
        """activate_client patches Config and auto-derives output dirs."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "acme.yaml").write_text(
            'client_name: "acme"\npodcast_name: "Acme Show"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import activate_client

        activate_client("acme")

        assert Config.PODCAST_NAME == "Acme Show"
        assert Config.OUTPUT_DIR == tmp_path / "output" / "acme"
        assert Config.DOWNLOAD_DIR == tmp_path / "downloads" / "acme"
        assert Config.CLIPS_DIR == tmp_path / "clips" / "acme"
        assert Config.TOPIC_DATA_DIR == tmp_path / "topic_data" / "acme"


class TestInitClient:
    """Tests for init_client() — scaffolding new client configs."""

    def test_creates_yaml_and_creds_dir(self, tmp_path, monkeypatch):
        """init_client creates YAML config and credentials directory."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        # Write a minimal example template
        (clients_dir / "example-client.yaml").write_text(
            'client_name: "your-client-name"\npodcast_name: "Your Podcast Name"\n'
        )

        from client_config import init_client

        init_client("cool-show")

        yaml_path = clients_dir / "cool-show.yaml"
        assert yaml_path.exists()
        content = yaml_path.read_text()
        assert "cool-show" in content
        assert "Cool Show" in content
        assert (clients_dir / "cool-show").is_dir()

    def test_does_not_overwrite_existing(self, tmp_path, monkeypatch, capsys):
        """init_client refuses to overwrite an existing config."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "existing.yaml").write_text("original content")

        from client_config import init_client

        init_client("existing")

        assert (clients_dir / "existing.yaml").read_text() == "original content"
        assert "already exists" in capsys.readouterr().out


class TestListClients:
    """Tests for list_clients() output."""

    def test_lists_clients_excluding_example(self, tmp_path, monkeypatch, capsys):
        """list_clients shows real clients but not the example template."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "example-client.yaml").write_text('podcast_name: "Example"\n')
        (clients_dir / "my-show.yaml").write_text('podcast_name: "My Show"\n')

        from client_config import list_clients

        list_clients()

        output = capsys.readouterr().out
        assert "my-show" in output
        assert "My Show" in output
        assert "example-client" not in output

    def test_empty_directory(self, tmp_path, monkeypatch, capsys):
        """list_clients handles no clients gracefully."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()

        from client_config import list_clients

        list_clients()

        assert "No client configs found" in capsys.readouterr().out


class TestValidateClient:
    """Tests for validate_client() credential checks."""

    def test_validate_shows_config_status(self, tmp_path, monkeypatch, capsys):
        """validate_client prints status for each service."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Show")
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output")
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", tmp_path / "downloads")
        monkeypatch.setattr(Config, "CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", tmp_path / "topic_data")
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", ["Alice"])
        monkeypatch.setattr(Config, "WORDS_TO_CENSOR", ["badword"])
        # Clear optional credentials
        monkeypatch.setattr(Config, "DISCORD_WEBHOOK_URL", None)
        monkeypatch.setattr(Config, "TWITTER_API_KEY", None)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-show.yaml").write_text(
            'client_name: "test-show"\npodcast_name: "Test Show"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import validate_client

        validate_client("test-show")

        output = capsys.readouterr().out
        assert "Test Show" in output
        assert "[OK]" in output
        assert "Podcast Name" in output
        assert "not configured" in output  # some services won't be configured

    def test_validate_prints_active_podcast_name(self, tmp_path, monkeypatch, capsys):
        """validate_client prints Active content configuration with the client's podcast name."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "cold-case.yaml").write_text(
            'client_name: "cold-case"\npodcast_name: "Cold Case Chronicles"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import validate_client

        validate_client("cold-case")

        output = capsys.readouterr().out
        assert "Active content configuration" in output
        assert "Cold Case Chronicles" in output
        # Podcast name line should show the client's name
        assert "Podcast name:    Cold Case Chronicles" in output

    def test_validate_prints_active_names_to_remove(
        self, tmp_path, monkeypatch, capsys
    ):
        """validate_client active config section shows the client's names_to_remove list."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = (
            'client_name: "mystery-pod"\npodcast_name: "Mystery Pod"\n'
            "content:\n  names_to_remove:\n    - Host1\n    - Host2\n"
        )
        (clients_dir / "mystery-pod.yaml").write_text(yaml_content)

        from client_config import validate_client

        validate_client("mystery-pod")

        output = capsys.readouterr().out
        assert "Host1" in output
        assert "Host2" in output
        assert "names_to_remove" in output

    def test_validate_prints_voice_persona_or_default(
        self, tmp_path, monkeypatch, capsys
    ):
        """validate_client shows voice persona preview or built-in default message."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        # Ensure VOICE_PERSONA is cleaned up after test (it may not exist initially)
        if hasattr(Config, "VOICE_PERSONA"):
            monkeypatch.setattr(Config, "VOICE_PERSONA", None)
        else:
            monkeypatch.delattr(Config, "VOICE_PERSONA", raising=False)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()

        # (a) Client with voice_persona set
        yaml_content = (
            'client_name: "with-voice"\npodcast_name: "With Voice"\n'
            'content:\n  names_to_remove: []\n  voice_persona: "You are a calm narrator."\n'
        )
        (clients_dir / "with-voice.yaml").write_text(yaml_content)

        from client_config import validate_client

        validate_client("with-voice")
        output = capsys.readouterr().out
        assert "You are a calm narrator." in output

        # (b) Client without voice_persona — manually clear VOICE_PERSONA and test again
        if hasattr(Config, "VOICE_PERSONA"):
            delattr(Config, "VOICE_PERSONA")
        (clients_dir / "no-voice.yaml").write_text(
            'client_name: "no-voice"\npodcast_name: "No Voice"\ncontent:\n  names_to_remove: []\n'
        )
        validate_client("no-voice")
        output = capsys.readouterr().out
        assert "(built-in Fake Problems default)" in output

    def test_validate_no_ping_by_default(self, tmp_path, monkeypatch, capsys):
        """validate_client suggests --ping when not used."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "fp.yaml").write_text(
            'client_name: "fp"\npodcast_name: "FP"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import validate_client

        validate_client("fp")

        output = capsys.readouterr().out
        assert "--ping" in output


class TestClientStatus:
    """Tests for client_status() reporting."""

    def test_status_with_episodes(self, tmp_path, monkeypatch, capsys):
        """status shows episode folders and their state."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)

        # Create client config
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test.yaml").write_text(
            'client_name: "test"\npodcast_name: "Test"\ncontent:\n  names_to_remove: []\n'
        )

        # Create output structure
        output_dir = tmp_path / "output" / "test"
        (output_dir / "ep_1").mkdir(parents=True)
        (output_dir / "ep_2").mkdir(parents=True)

        # Add platform IDs to ep_1
        import json

        (output_dir / "ep_1" / "platform_ids.json").write_text(
            json.dumps({"youtube": "abc123"})
        )

        from client_config import client_status

        client_status("test")

        output = capsys.readouterr().out
        assert "Episodes processed: 2" in output
        assert "ep_1" in output
        assert "ep_2" in output
        assert "youtube" in output

    def test_status_no_output_dir(self, tmp_path, monkeypatch, capsys):
        """status handles missing output directory gracefully."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)

        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "empty.yaml").write_text(
            'client_name: "empty"\npodcast_name: "Empty"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import client_status

        client_status("empty")

        output = capsys.readouterr().out
        assert "No output directory" in output


class TestSetupClientPlatform:
    """Tests for setup_client_platform() credential setup."""

    def test_unknown_platform(self, tmp_path, monkeypatch, capsys):
        """Unknown platform prints helpful message."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test.yaml").write_text(
            'client_name: "test"\npodcast_name: "Test"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import setup_client_platform

        setup_client_platform("test", "unknown")

        output = capsys.readouterr().out
        assert "Unknown platform" in output
        assert "youtube" in output

    def test_youtube_missing_credentials(self, tmp_path, monkeypatch, capsys):
        """YouTube setup reports missing credentials file."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test.yaml").write_text(
            'client_name: "test"\npodcast_name: "Test"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import setup_client_platform

        setup_client_platform("test", "youtube")

        output = capsys.readouterr().out
        assert "credentials file not found" in output

    def test_dropbox_prints_instructions(self, tmp_path, monkeypatch, capsys):
        """Dropbox setup prints configuration instructions."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test.yaml").write_text(
            'client_name: "test"\npodcast_name: "Test"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import setup_client_platform

        setup_client_platform("test", "dropbox")

        output = capsys.readouterr().out
        assert "app_key" in output


class TestBackwardCompatibility:
    """Verify no-client mode preserves default Fake Problems config."""

    def test_defaults_unchanged_without_client(self):
        """Without --client, Config keeps Fake Problems defaults."""
        assert Config.PODCAST_NAME == "Fake Problems Podcast"
        assert "Joey" in Config.NAMES_TO_REMOVE
        assert "Evan" in Config.NAMES_TO_REMOVE
        assert Config.OUTPUT_DIR == Config.BASE_DIR / "output"
        assert Config.CLIPS_DIR == Config.BASE_DIR / "clips"
        assert Config.DOWNLOAD_DIR == Config.BASE_DIR / "downloads"

    def test_voice_persona_not_on_config_by_default(self):
        """Config doesn't have VOICE_PERSONA unless set by client config."""
        assert not hasattr(Config, "VOICE_PERSONA") or Config.VOICE_PERSONA is None


class TestEpisodeSourceYAMLMapping:
    """Tests for episode_source and rss_source YAML-to-Config mapping."""

    def test_episode_source_rss_maps_to_config(self, tmp_path, monkeypatch):
        """episode_source: rss in YAML sets Config.EPISODE_SOURCE to 'rss'."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = (
            'client_name: "rss-show"\npodcast_name: "RSS Show"\n'
            'episode_source: "rss"\n'
            "rss_source:\n"
            '  feed_url: "https://feeds.example.com/show.xml"\n'
            "  episode_index: 0\n"
            "content:\n  names_to_remove: []\n"
        )
        (clients_dir / "rss-show.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("rss-show")

        assert overrides["EPISODE_SOURCE"] == "rss"
        assert overrides["RSS_FEED_URL"] == "https://feeds.example.com/show.xml"
        assert overrides["RSS_EPISODE_INDEX"] == 0

    def test_episode_index_as_int(self, tmp_path, monkeypatch):
        """rss_source.episode_index is loaded as int, not string."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = (
            'client_name: "idx-show"\npodcast_name: "Idx Show"\n'
            "rss_source:\n"
            '  feed_url: "https://feeds.example.com/show.xml"\n'
            "  episode_index: 2\n"
            "content:\n  names_to_remove: []\n"
        )
        (clients_dir / "idx-show.yaml").write_text(yaml_content)

        from client_config import load_client_config

        overrides = load_client_config("idx-show")

        assert overrides["RSS_EPISODE_INDEX"] == 2
        assert isinstance(overrides["RSS_EPISODE_INDEX"], int)

    def test_missing_episode_source_not_in_overrides(self, tmp_path, monkeypatch):
        """YAML without episode_source does not add EPISODE_SOURCE override."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "minimal.yaml").write_text(
            'client_name: "minimal"\npodcast_name: "Minimal"\ncontent:\n  names_to_remove: []\n'
        )

        from client_config import load_client_config

        overrides = load_client_config("minimal")

        assert "EPISODE_SOURCE" not in overrides
        assert "RSS_FEED_URL" not in overrides


class TestValidateClientRSS:
    """Tests for validate_client() with episode_source=rss."""

    def _setup_rss_client(self, tmp_path, monkeypatch, feed_url=None):
        """Create a client YAML with episode_source=rss and set up Config."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        feed_line = f'  feed_url: "{feed_url}"' if feed_url else "  feed_url: null"
        yaml_content = (
            'client_name: "rss-client"\npodcast_name: "RSS Client"\n'
            'episode_source: "rss"\n'
            f"rss_source:\n{feed_line}\n"
            "content:\n  names_to_remove: []\n"
        )
        (clients_dir / "rss-client.yaml").write_text(yaml_content)

    def test_validate_rss_client_skips_dropbox_check(
        self, tmp_path, monkeypatch, capsys
    ):
        """validate_client with episode_source=rss does not check Dropbox credentials."""
        self._setup_rss_client(
            tmp_path, monkeypatch, feed_url="https://feeds.example.com/show.xml"
        )

        from client_config import validate_client

        validate_client("rss-client")

        output = capsys.readouterr().out
        assert "Dropbox" not in output

    def test_validate_rss_client_checks_feed_url(self, tmp_path, monkeypatch, capsys):
        """validate_client with episode_source=rss checks RSS_FEED_URL is set."""
        self._setup_rss_client(
            tmp_path, monkeypatch, feed_url="https://feeds.example.com/show.xml"
        )

        from client_config import validate_client

        validate_client("rss-client")

        output = capsys.readouterr().out
        assert "RSS Feed URL" in output
        assert "[OK]" in output

    def test_validate_rss_client_shows_episode_source(
        self, tmp_path, monkeypatch, capsys
    ):
        """validate_client active config shows episode_source: rss."""
        self._setup_rss_client(
            tmp_path, monkeypatch, feed_url="https://feeds.example.com/show.xml"
        )

        from client_config import validate_client

        validate_client("rss-client")

        output = capsys.readouterr().out
        assert "episode_source" in output
        assert "rss" in output

    def test_validate_rss_client_no_feed_url_shows_not_configured(
        self, tmp_path, monkeypatch, capsys
    ):
        """validate_client with episode_source=rss and no feed_url shows not configured."""
        self._setup_rss_client(tmp_path, monkeypatch, feed_url=None)

        from client_config import validate_client

        validate_client("rss-client")

        output = capsys.readouterr().out
        assert "RSS Feed URL" in output
        assert "not configured" in output


class TestPingRSSFeed:
    """Tests for _ping_rss_feed() live connectivity check."""

    def test_ping_rss_feed_success(self, monkeypatch):
        """_ping_rss_feed returns without error when HEAD request succeeds."""
        from unittest.mock import MagicMock, patch

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch(
            "client_config.requests.head", return_value=mock_response
        ) as mock_head:
            from client_config import _ping_rss_feed

            monkeypatch.setattr(
                Config, "RSS_FEED_URL", "https://feeds.example.com/show.xml"
            )
            _ping_rss_feed()

        mock_head.assert_called_once_with(
            "https://feeds.example.com/show.xml", timeout=10, allow_redirects=True
        )
        mock_response.raise_for_status.assert_called_once()

    def test_ping_rss_feed_failure_raises(self, monkeypatch):
        """_ping_rss_feed raises when HEAD request fails."""
        from unittest.mock import patch
        import requests as req

        with patch(
            "client_config.requests.head",
            side_effect=req.RequestException("Connection refused"),
        ):
            from client_config import _ping_rss_feed

            monkeypatch.setattr(
                Config, "RSS_FEED_URL", "https://feeds.example.com/show.xml"
            )

            with pytest.raises(req.RequestException):
                _ping_rss_feed()

    def test_validate_rss_ping_calls_ping_rss_feed(self, tmp_path, monkeypatch, capsys):
        """validate_client with episode_source=rss and ping=True calls _ping_rss_feed."""
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "NAMES_TO_REMOVE", Config.NAMES_TO_REMOVE)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = (
            'client_name: "rss-ping"\npodcast_name: "RSS Ping"\n'
            'episode_source: "rss"\n'
            'rss_source:\n  feed_url: "https://feeds.example.com/show.xml"\n'
            "content:\n  names_to_remove: []\n"
        )
        (clients_dir / "rss-ping.yaml").write_text(yaml_content)

        with patch("client_config._ping_rss_feed") as mock_ping:
            from client_config import validate_client

            validate_client("rss-ping", ping=True)

        mock_ping.assert_called_once()


class TestGetClientNames:
    """Tests for get_client_names()."""

    def test_returns_list_of_client_names(self, tmp_path, monkeypatch):
        """Returns client names from clients/ directory."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "alpha.yaml").write_text("client_name: alpha\n")
        (clients_dir / "beta.yaml").write_text("client_name: beta\n")
        (clients_dir / "example-client.yaml").write_text("client_name: example\n")

        from client_config import get_client_names

        names = get_client_names()
        assert "alpha" in names
        assert "beta" in names
        assert "example-client" not in names

    def test_no_clients_dir_returns_empty(self, tmp_path, monkeypatch):
        """Returns empty list when clients/ dir does not exist."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        from client_config import get_client_names

        assert get_client_names() == []


class TestProcessAll:
    """Tests for process_all()."""

    def test_no_clients_prints_message(self, tmp_path, monkeypatch, capsys):
        """Prints help message when no clients configured."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        from client_config import process_all

        process_all({})
        output = capsys.readouterr().out
        assert "No clients configured" in output

    def test_processes_each_client(self, tmp_path, monkeypatch, capsys):
        """Iterates over each configured client."""
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "test-show.yaml").write_text(
            'client_name: "test-show"\npodcast_name: "Test"\n'
            "content:\n  names_to_remove: []\n"
        )

        with patch("pipeline.run_with_notification") as mock_run:
            from client_config import process_all

            process_all({"test_mode": True})

        mock_run.assert_called_once()
        output = capsys.readouterr().out
        assert "test-show" in output

    def test_handles_client_failure(self, tmp_path, monkeypatch, capsys):
        """Records failure status when client processing raises."""
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "broken.yaml").write_text(
            'client_name: "broken"\npodcast_name: "Broken"\n'
            "content:\n  names_to_remove: []\n"
        )

        with patch("pipeline.run_with_notification", side_effect=RuntimeError("boom")):
            from client_config import process_all

            process_all({})

        output = capsys.readouterr().out
        assert "FAILED" in output


class TestListClientsNoDir:
    """Tests for list_clients edge cases."""

    def test_no_clients_dir(self, tmp_path, monkeypatch, capsys):
        """Prints message when clients/ dir doesn't exist."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        from client_config import list_clients

        list_clients()
        output = capsys.readouterr().out
        assert "No clients/ directory" in output


class TestClientStatusEdgeCases:
    """Tests for client_status edge cases."""

    def test_no_episodes_processed(self, tmp_path, monkeypatch, capsys):
        """Shows message when no episode dirs exist."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Pod")
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path / "output")
        (tmp_path / "output").mkdir()

        from client_config import client_status

        with patch("client_config.activate_client"):
            client_status("test")
        output = capsys.readouterr().out
        assert "No episodes processed" in output

    def test_with_pipeline_state(self, tmp_path, monkeypatch, capsys):
        """Shows step count and timestamp from pipeline state."""
        import json
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Pod")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(Config, "OUTPUT_DIR", output_dir)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", tmp_path / "topics")

        # Create episode dir with state
        ep_dir = output_dir / "ep_01"
        ep_dir.mkdir(parents=True)
        state_dir = output_dir / ".pipeline_state"
        state_dir.mkdir()
        state = {
            "completed_steps": {"transcribe": {}, "censor": {}, "normalize": {}},
            "updated_at": "2026-03-30T12:00:00",
        }
        (state_dir / "ep_01.json").write_text(json.dumps(state))

        with patch("client_config.activate_client"):
            from client_config import client_status

            client_status("test")
        output = capsys.readouterr().out
        assert "steps:" in output
        assert "ep_01" in output

    def test_with_platform_ids(self, tmp_path, monkeypatch, capsys):
        """Shows uploaded platforms from platform_ids.json."""
        import json
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Pod")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(Config, "OUTPUT_DIR", output_dir)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", tmp_path / "topics")

        ep_dir = output_dir / "ep_01"
        ep_dir.mkdir(parents=True)
        (ep_dir / "platform_ids.json").write_text(json.dumps({"youtube": "abc123"}))

        with patch("client_config.activate_client"):
            from client_config import client_status

            client_status("test")
        output = capsys.readouterr().out
        assert "youtube" in output

    def test_with_pending_schedule(self, tmp_path, monkeypatch, capsys):
        """Shows pending upload count from schedule file."""
        import json
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Pod")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(Config, "OUTPUT_DIR", output_dir)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", tmp_path / "topics")

        ep_dir = output_dir / "ep_01"
        ep_dir.mkdir(parents=True)
        sched = {"platforms": {"instagram": {"status": "pending"}}}
        (ep_dir / "upload_schedule.json").write_text(json.dumps(sched))

        with patch("client_config.activate_client"):
            from client_config import client_status

            client_status("test")
        output = capsys.readouterr().out
        assert "pending" in output

    def test_content_calendar_pending(self, tmp_path, monkeypatch, capsys):
        """Shows pending content calendar slots."""
        import json
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", "Test Pod")
        output_dir = tmp_path / "output"
        monkeypatch.setattr(Config, "OUTPUT_DIR", output_dir)
        topics_dir = tmp_path / "topics"
        topics_dir.mkdir(parents=True)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", topics_dir)

        # Need at least one ep dir
        (output_dir / "ep_01").mkdir(parents=True)

        cal = {"ep_01": {"slots": {"twitter": {"status": "pending"}}}}
        (topics_dir / "content_calendar.json").write_text(json.dumps(cal))

        with patch("client_config.activate_client"):
            from client_config import client_status

            client_status("test")
        output = capsys.readouterr().out
        assert "pending slot" in output


class TestListAvailableClients:
    """Tests for _list_available_clients()."""

    def test_no_clients_dir(self, tmp_path, monkeypatch):
        """Returns message when no clients directory exists."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)

        from client_config import _list_available_clients

        result = _list_available_clients()
        assert "no clients/ directory" in result

    def test_no_yaml_files(self, tmp_path, monkeypatch):
        """Returns message when no YAML files in clients/."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        (tmp_path / "clients").mkdir()

        from client_config import _list_available_clients

        result = _list_available_clients()
        assert "no .yaml files" in result

    def test_lists_client_names(self, tmp_path, monkeypatch):
        """Returns comma-separated list of client names."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "alpha.yaml").write_text("x: y\n")
        (clients_dir / "beta.yaml").write_text("x: y\n")

        from client_config import _list_available_clients

        result = _list_available_clients()
        assert "alpha" in result
        assert "beta" in result


class TestPingFunction:
    """Tests for _ping helper."""

    def test_ping_success(self, capsys):
        """Successful ping prints OK."""
        from client_config import _ping

        results = []
        _ping(results, "TestService", lambda: None)
        output = capsys.readouterr().out
        assert "ping OK" in output

    def test_ping_failure(self, capsys):
        """Failed ping records error."""
        from client_config import _ping

        results = []

        def _fail():
            raise ConnectionError("refused")

        _ping(results, "TestService", _fail)
        output = capsys.readouterr().out
        assert "ping FAILED" in output
        assert any("ping" in r[0] for r in results)


class TestYAMLSpecialHandling:
    """Tests for YAML special handling branches in _build_overrides."""

    @pytest.fixture(autouse=True)
    def _save_restore_config(self):
        """Save Config state before test and restore after."""
        # Save all current Config class attributes
        saved = {k: v for k, v in vars(Config).items() if not k.startswith("_")}
        yield
        # Remove any new attrs added by activate_client
        current = {k for k in vars(Config) if not k.startswith("_")}
        for attr in current - set(saved):
            delattr(Config, attr)
        # Restore original values
        for k, v in saved.items():
            setattr(Config, k, v)

    def _activate(self, tmp_path, client_name, yaml_content):
        """Activate a client config."""
        setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir(exist_ok=True)
        (clients_dir / f"{client_name}.yaml").write_text(yaml_content)

        from client_config import activate_client

        return activate_client(client_name)

    def test_rss_categories(self, tmp_path):
        """RSS categories list from YAML is mapped to Config."""
        self._activate(
            tmp_path,
            "cats",
            'client_name: "cats"\npodcast_name: "Cats"\n'
            "content:\n  names_to_remove: []\n"
            "rss:\n  categories:\n    - Comedy\n    - Society\n",
        )
        assert Config.RSS_CATEGORIES == ["Comedy", "Society"]

    def test_blog_voice(self, tmp_path):
        """Blog voice from YAML is mapped to Config."""
        self._activate(
            tmp_path,
            "bv",
            'client_name: "bv"\npodcast_name: "BV"\n'
            "content:\n  names_to_remove: []\n"
            '  blog_voice: "Write like Hemingway"\n',
        )
        assert Config.BLOG_VOICE == "Write like Hemingway"

    def test_scoring_profile(self, tmp_path):
        """Scoring profile dict from YAML is mapped to Config."""
        self._activate(
            tmp_path,
            "sp",
            'client_name: "sp"\npodcast_name: "SP"\n'
            "content:\n  names_to_remove: []\n"
            "  scoring_profile:\n    humor_weight: 0.8\n    debate_weight: 0.5\n",
        )
        assert Config.SCORING_PROFILE == {"humor_weight": 0.8, "debate_weight": 0.5}


class TestValidateConfigDisplay:
    """Tests for validate_client config display branches."""

    @pytest.fixture(autouse=True)
    def _save_restore_config(self):
        """Save Config state before test and restore after."""
        saved = {k: v for k, v in vars(Config).items() if not k.startswith("_")}
        yield
        current = {k for k in vars(Config) if not k.startswith("_")}
        for attr in current - set(saved):
            delattr(Config, attr)
        for k, v in saved.items():
            setattr(Config, k, v)

    def _setup_client(self, tmp_path, yaml_extra=""):
        """Create a minimal client config."""
        setattr(Config, "BASE_DIR", tmp_path)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        yaml_content = (
            'client_name: "disp"\npodcast_name: "Display Test"\n'
            "content:\n  names_to_remove: []\n" + yaml_extra
        )
        (clients_dir / "disp.yaml").write_text(yaml_content)

    def test_shows_empty_words_to_censor(self, tmp_path, capsys):
        """Shows (empty) when words_to_censor is empty."""
        self._setup_client(tmp_path)

        from client_config import validate_client

        validate_client("disp")
        output = capsys.readouterr().out
        assert "words_to_censor" in output

    def test_shows_blog_voice_configured(self, tmp_path, capsys):
        """Shows blog_voice when configured."""
        self._setup_client(tmp_path, '  blog_voice: "Write casually"\n')

        from client_config import validate_client

        validate_client("disp")
        output = capsys.readouterr().out
        assert "blog_voice" in output

    def test_shows_scoring_profile(self, tmp_path, capsys):
        """Shows scoring_profile when configured."""
        self._setup_client(
            tmp_path,
            "  scoring_profile:\n    weight: 0.5\n",
        )

        from client_config import validate_client

        validate_client("disp")
        output = capsys.readouterr().out
        assert "scoring_profile" in output


class TestSetupYouTubeEdgeCases:
    """Tests for _setup_youtube edge cases."""

    def test_deletes_existing_token(self, tmp_path, monkeypatch, capsys):
        """Deletes existing token file before re-auth."""
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "_YOUTUBE_TOKEN_PICKLE", None)

        # Create credentials file
        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        (creds_dir / "youtube_credentials.json").write_text("{}")

        # Create existing token
        token_dir = tmp_path / "clients" / "test"
        token_dir.mkdir(parents=True)
        token_file = token_dir / "youtube_token.pickle"
        token_file.write_text("old token")

        with (
            patch("builtins.input", return_value=""),
            patch("uploaders.YouTubeUploader"),
        ):
            from client_config import _setup_youtube

            _setup_youtube("test")

        assert not token_file.exists()
        output = capsys.readouterr().out
        assert "Deleting existing token" in output

    def test_auth_failure(self, tmp_path, monkeypatch, capsys):
        """Prints error on authentication failure."""
        from unittest.mock import patch

        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "_YOUTUBE_TOKEN_PICKLE", None)

        creds_dir = tmp_path / "credentials"
        creds_dir.mkdir()
        (creds_dir / "youtube_credentials.json").write_text("{}")

        with (
            patch("builtins.input", return_value=""),
            patch("uploaders.YouTubeUploader", side_effect=RuntimeError("auth failed")),
        ):
            from client_config import _setup_youtube

            _setup_youtube("test")

        output = capsys.readouterr().out
        assert "ERROR" in output
        assert "auth failed" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
