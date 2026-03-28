"""Tests for client_config module — multi-client YAML loading and Config patching."""

import pytest
from pathlib import Path

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
        assert len(overrides) == 1  # Only podcast_name was non-null

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

        # Cleanup
        delattr(Config, "_YOUTUBE_TOKEN_PICKLE")


class TestOutputIsolation:
    """Tests for per-client output directory isolation."""

    def test_output_dirs_auto_derived(self, tmp_path, monkeypatch):
        """When --client is used, output dirs include client name."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
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
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "acme.yaml").write_text(
            'client_name: "acme"\npodcast_name: "Acme Show"\n'
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
            'client_name: "test-show"\npodcast_name: "Test Show"\n'
        )

        from client_config import validate_client

        validate_client("test-show")

        output = capsys.readouterr().out
        assert "Test Show" in output
        assert "[OK]" in output
        assert "Podcast Name" in output
        assert "not configured" in output  # some services won't be configured

    def test_validate_no_ping_by_default(self, tmp_path, monkeypatch, capsys):
        """validate_client suggests --ping when not used."""
        monkeypatch.setattr(Config, "BASE_DIR", tmp_path)
        monkeypatch.setattr(Config, "PODCAST_NAME", Config.PODCAST_NAME)
        monkeypatch.setattr(Config, "OUTPUT_DIR", Config.OUTPUT_DIR)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", Config.DOWNLOAD_DIR)
        monkeypatch.setattr(Config, "CLIPS_DIR", Config.CLIPS_DIR)
        monkeypatch.setattr(Config, "TOPIC_DATA_DIR", Config.TOPIC_DATA_DIR)
        clients_dir = tmp_path / "clients"
        clients_dir.mkdir()
        (clients_dir / "fp.yaml").write_text('client_name: "fp"\npodcast_name: "FP"\n')

        from client_config import validate_client

        validate_client("fp")

        output = capsys.readouterr().out
        assert "--ping" in output


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
