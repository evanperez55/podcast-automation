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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
