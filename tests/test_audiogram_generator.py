"""Tests for audiogram_generator module."""

import pytest
from unittest.mock import patch, MagicMock

from audiogram_generator import AudiogramGenerator
from config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove audiogram-related env vars so each test starts from defaults."""
    for key in ("USE_AUDIOGRAM", "AUDIOGRAM_BG_COLOR", "AUDIOGRAM_WAVE_COLOR"):
        monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# 1. test_init_defaults
# ---------------------------------------------------------------------------
class TestInitDefaults:
    def test_disabled_and_default_colors(self):
        gen = AudiogramGenerator()
        assert gen.enabled is False
        assert gen.bg_color == "0x1a1a2e"
        assert gen.wave_color == "0xe94560"
        assert gen.ffmpeg_path == Config.FFMPEG_PATH


# ---------------------------------------------------------------------------
# 2. test_init_enabled
# ---------------------------------------------------------------------------
class TestInitEnabled:
    def test_env_enables_audiogram(self, monkeypatch):
        monkeypatch.setenv("USE_AUDIOGRAM", "true")
        gen = AudiogramGenerator()
        assert gen.enabled is True


# ---------------------------------------------------------------------------
# 3. test_build_ffmpeg_command_no_subs
# ---------------------------------------------------------------------------
class TestBuildFfmpegCommandNoSubs:
    def test_no_subtitles_filter(self):
        gen = AudiogramGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )

        assert cmd[0] == gen.ffmpeg_path
        assert "-filter_complex" in cmd
        assert "-map" in cmd

        # The map label should be [video], not [final] (no subtitles)
        map_indices = [i for i, v in enumerate(cmd) if v == "-map"]
        map_values = [cmd[i + 1] for i in map_indices]
        assert "[video]" in map_values
        assert "[final]" not in map_values

        # No subtitles reference in the filter_complex string
        fc_index = cmd.index("-filter_complex")
        filter_string = cmd[fc_index + 1]
        assert "subtitles" not in filter_string

        # Output path is last element
        assert cmd[-1] == "/path/output.mp4"


# ---------------------------------------------------------------------------
# 4. test_build_ffmpeg_command_with_subs
# ---------------------------------------------------------------------------
class TestBuildFfmpegCommandWithSubs:
    def test_subtitles_filter_present(self):
        gen = AudiogramGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
            srt_path="/path/subs.srt",
        )

        fc_index = cmd.index("-filter_complex")
        filter_string = cmd[fc_index + 1]
        assert "subtitles" in filter_string

        # The map label should be [final] when subtitles are included
        map_indices = [i for i, v in enumerate(cmd) if v == "-map"]
        map_values = [cmd[i + 1] for i in map_indices]
        assert "[final]" in map_values


# ---------------------------------------------------------------------------
# 5. test_build_ffmpeg_command_dimensions_vertical
# ---------------------------------------------------------------------------
class TestBuildFfmpegCommandDimensionsVertical:
    def test_vertical_uses_720x1280(self):
        gen = AudiogramGenerator()
        cmd = gen._build_ffmpeg_command(
            audio_path="/path/audio.wav",
            output_path="/path/output.mp4",
            width=720,
            height=1280,
        )

        fc_index = cmd.index("-filter_complex")
        filter_string = cmd[fc_index + 1]
        assert "720x1280" in filter_string

        # Wave height should be height // 3 = 426
        wave_height = 1280 // 3
        assert f"720x{wave_height}" in filter_string


# ---------------------------------------------------------------------------
# 6. test_create_audiogram_success
# ---------------------------------------------------------------------------
class TestCreateAudiogramSuccess:
    @patch("audiogram_generator.subprocess.run")
    @patch("audiogram_generator.Path.exists", return_value=True)
    def test_returns_output_path(self, _mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        gen = AudiogramGenerator()
        result = gen.create_audiogram("/path/audio.wav", output_path="/path/output.mp4")
        assert result == "/path/output.mp4"
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 7. test_create_audiogram_failure
# ---------------------------------------------------------------------------
class TestCreateAudiogramFailure:
    @patch("audiogram_generator.subprocess.run")
    @patch("audiogram_generator.Path.exists", return_value=True)
    def test_returns_none_on_failure(self, _mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="encoding error")
        gen = AudiogramGenerator()
        result = gen.create_audiogram("/path/audio.wav", output_path="/path/output.mp4")
        assert result is None
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# 8. test_create_audiogram_clips_batch
# ---------------------------------------------------------------------------
class TestCreateAudiogramClipsBatch:
    @patch.object(AudiogramGenerator, "create_audiogram")
    def test_batch_processes_all_clips(self, mock_create):
        mock_create.side_effect = [
            "/out/clip1_audiogram.mp4",
            "/out/clip2_audiogram.mp4",
            "/out/clip3_audiogram.mp4",
        ]
        gen = AudiogramGenerator()
        clips = ["/clips/clip1.wav", "/clips/clip2.wav", "/clips/clip3.wav"]
        results = gen.create_audiogram_clips(clips, format_type="vertical")

        assert len(results) == 3
        assert mock_create.call_count == 3
        for i, clip in enumerate(clips):
            call_kwargs = mock_create.call_args_list[i]
            assert call_kwargs.kwargs["audio_path"] == clip
            assert call_kwargs.kwargs["format_type"] == "vertical"
