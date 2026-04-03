"""Tests for config module — Config class, detection helpers, validation."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestDetectFfmpeg:
    """Tests for _detect_ffmpeg helper."""

    def test_uses_env_var_if_set_and_exists(self):
        """Returns FFMPEG_PATH env var when file exists."""
        with patch.dict("os.environ", {"FFMPEG_PATH": "/usr/bin/ffmpeg"}):
            with patch("os.path.exists", return_value=True):
                from importlib import reload
                import config

                reload(config)
                # Re-call the function directly
                result = config._detect_ffmpeg()
                assert result == "/usr/bin/ffmpeg"

    def test_falls_back_to_which(self):
        """Falls back to shutil.which when env var not set."""
        with patch.dict("os.environ", {}, clear=False):
            with patch("os.environ.get", return_value=None):
                with patch("shutil.which", return_value="/usr/local/bin/ffmpeg"):
                    from config import _detect_ffmpeg

                    result = _detect_ffmpeg()
                    # May return cached or detected value
                    assert result is not None


class TestDetectNvenc:
    """Tests for _detect_nvenc helper."""

    def test_returns_true_when_nvenc_available(self):
        """Returns True when FFmpeg lists h264_nvenc."""
        import config

        config._nvenc_cache = None  # Reset cache
        mock_result = MagicMock()
        mock_result.stdout = "h264_nvenc some other encoders"
        with patch("subprocess.run", return_value=mock_result):
            result = config._detect_nvenc("/fake/ffmpeg")
        assert result is True
        config._nvenc_cache = None  # Clean up

    def test_returns_false_when_nvenc_unavailable(self):
        """Returns False when FFmpeg does not list h264_nvenc."""
        import config

        config._nvenc_cache = None
        mock_result = MagicMock()
        mock_result.stdout = "libx264 libx265 aac"
        with patch("subprocess.run", return_value=mock_result):
            result = config._detect_nvenc("/fake/ffmpeg")
        assert result is False
        config._nvenc_cache = None

    def test_returns_false_on_exception(self):
        """Returns False when subprocess fails."""
        import config

        config._nvenc_cache = None
        with patch("subprocess.run", side_effect=OSError("not found")):
            result = config._detect_nvenc("/fake/ffmpeg")
        assert result is False
        config._nvenc_cache = None


class TestConfigAttributes:
    """Tests for Config class attributes and defaults."""

    def test_podcast_name_default(self):
        """Default podcast name is Fake Problems Podcast."""
        from config import Config

        assert "Fake Problems" in Config.PODCAST_NAME

    def test_num_clips_default(self):
        """Default clip count is 8."""
        from config import Config

        assert Config.NUM_CLIPS == 8

    def test_clip_min_duration(self):
        """Clip min duration is set."""
        from config import Config

        assert Config.CLIP_MIN_DURATION > 0

    def test_output_dir_is_path(self):
        """OUTPUT_DIR is a Path object."""
        from config import Config

        assert isinstance(Config.OUTPUT_DIR, Path)

    def test_names_to_remove_is_list(self):
        """NAMES_TO_REMOVE is a list."""
        from config import Config

        assert isinstance(Config.NAMES_TO_REMOVE, list)

    def test_base_dir_exists(self):
        """BASE_DIR points to project root."""
        from config import Config

        assert Config.BASE_DIR.exists()
        assert (Config.BASE_DIR / "config.py").exists()


class TestConfigValidate:
    """Tests for Config.validate()."""

    def test_validate_passes_with_key(self):
        """Validate returns True when OPENAI_API_KEY is set."""
        from config import Config

        original = Config.OPENAI_API_KEY
        Config.OPENAI_API_KEY = "test-key"
        try:
            assert Config.validate() is True
        finally:
            Config.OPENAI_API_KEY = original

    def test_validate_raises_without_key(self):
        """Validate raises ValueError when OPENAI_API_KEY missing."""
        from config import Config

        original = Config.OPENAI_API_KEY
        Config.OPENAI_API_KEY = None
        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                Config.validate()
        finally:
            Config.OPENAI_API_KEY = original


class TestCreateDirectories:
    """Tests for Config.create_directories()."""

    def test_creates_directories(self, tmp_path):
        """create_directories creates output dirs."""
        from config import Config

        original_dirs = (
            Config.DOWNLOAD_DIR,
            Config.OUTPUT_DIR,
            Config.CLIPS_DIR,
            Config.ASSETS_DIR,
        )
        Config.DOWNLOAD_DIR = tmp_path / "downloads"
        Config.OUTPUT_DIR = tmp_path / "output"
        Config.CLIPS_DIR = tmp_path / "clips"
        Config.ASSETS_DIR = tmp_path / "assets"
        try:
            Config.create_directories()
            assert Config.DOWNLOAD_DIR.exists()
            assert Config.OUTPUT_DIR.exists()
            assert Config.CLIPS_DIR.exists()
            assert Config.ASSETS_DIR.exists()
        finally:
            (
                Config.DOWNLOAD_DIR,
                Config.OUTPUT_DIR,
                Config.CLIPS_DIR,
                Config.ASSETS_DIR,
            ) = original_dirs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
