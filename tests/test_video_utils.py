"""Tests for video_utils module — FFmpeg video operations."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from config import Config

from video_utils import (
    is_video_file,
    probe_video,
    extract_audio,
    cut_video_clip,
    mux_audio_to_video,
    get_h264_encoder_args,
)


class TestIsVideoFile:
    """Tests for is_video_file()."""

    def test_mp4_is_video(self):
        """MP4 files are detected as video."""
        assert is_video_file(Path("episode.mp4")) is True

    def test_mkv_is_video(self):
        """MKV files are detected as video."""
        assert is_video_file(Path("episode.mkv")) is True

    def test_mov_is_video(self):
        """MOV files are detected as video."""
        assert is_video_file(Path("episode.mov")) is True

    def test_avi_is_video(self):
        """AVI files are detected as video."""
        assert is_video_file(Path("episode.avi")) is True

    def test_webm_is_video(self):
        """WebM files are detected as video."""
        assert is_video_file(Path("episode.webm")) is True

    def test_wav_is_not_video(self):
        """WAV files are not video."""
        assert is_video_file(Path("episode.wav")) is False

    def test_mp3_is_not_video(self):
        """MP3 files are not video."""
        assert is_video_file(Path("episode.mp3")) is False

    def test_case_insensitive(self):
        """Extension detection is case-insensitive."""
        assert is_video_file(Path("episode.MP4")) is True
        assert is_video_file(Path("episode.MKV")) is True


class TestProbeVideo:
    """Tests for probe_video()."""

    @patch("video_utils.subprocess.run")
    def test_probe_success(self, mock_run):
        """Successful probe returns metadata dict."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "width": 1920,
                            "height": 1080,
                            "r_frame_rate": "30/1",
                            "codec_name": "h264",
                        }
                    ],
                    "format": {"duration": "3600.5"},
                }
            ),
        )

        result = probe_video("/path/to/video.mp4")

        assert result is not None
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["fps"] == 30.0
        assert result["codec"] == "h264"
        assert result["duration"] == 3600.5

    @patch("video_utils.subprocess.run")
    def test_probe_fractional_fps(self, mock_run):
        """Fractional frame rates (e.g., 30000/1001) are parsed correctly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "width": 1920,
                            "height": 1080,
                            "r_frame_rate": "30000/1001",
                            "codec_name": "h264",
                        }
                    ],
                    "format": {"duration": "100"},
                }
            ),
        )

        result = probe_video("/path/to/video.mp4")
        assert result["fps"] == pytest.approx(29.97, abs=0.01)

    @patch("video_utils.subprocess.run")
    def test_probe_failure_returns_none(self, mock_run):
        """Failed ffprobe returns None."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="error: file not found",
        )

        result = probe_video("/path/to/missing.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_probe_timeout_returns_none(self, mock_run):
        """Timed-out ffprobe returns None."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=30)

        result = probe_video("/path/to/video.mp4")
        assert result is None


class TestExtractAudio:
    """Tests for extract_audio()."""

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    def test_extract_success(self, mock_run, mock_exists):
        """Successful extraction returns output path."""
        mock_run.return_value = MagicMock(returncode=0)

        result = extract_audio("/video.mp4", "/audio.wav")

        assert result == "/audio.wav"
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "-vn" in cmd  # No video
        assert "-acodec" in cmd

    @patch("video_utils.subprocess.run")
    def test_extract_failure_returns_none(self, mock_run):
        """Failed extraction returns None."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="error extracting audio",
        )

        result = extract_audio("/video.mp4", "/audio.wav")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_extract_timeout_returns_none(self, mock_run):
        """Timed-out extraction returns None."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600)

        result = extract_audio("/video.mp4", "/audio.wav")
        assert result is None


class TestCutVideoClip:
    """Tests for cut_video_clip()."""

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    def test_cut_success(self, mock_run, mock_exists):
        """Successful clip cut returns output path."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip("/video.mp4", 10.0, 25.0, "/clip.mp4")

        assert result == "/clip.mp4"
        cmd = mock_run.call_args[0][0]
        assert "-ss" in cmd
        assert "-t" in cmd

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    def test_cut_vertical_crop(self, mock_run, mock_exists):
        """Vertical crop applies correct FFmpeg filter."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip(
            "/video.mp4", 10.0, 25.0, "/clip.mp4", crop_vertical=True
        )

        assert result == "/clip.mp4"
        cmd = mock_run.call_args[0][0]
        # Check that -vf with crop filter is present
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert "crop=" in vf_value
        assert "scale=720:1280" in vf_value

    def test_cut_invalid_duration_returns_none(self):
        """Invalid duration (start >= end) returns None."""
        result = cut_video_clip("/video.mp4", 25.0, 10.0, "/clip.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_cut_failure_returns_none(self, mock_run):
        """Failed cut returns None."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="error cutting",
        )

        result = cut_video_clip("/video.mp4", 10.0, 25.0, "/clip.mp4")
        assert result is None


class TestMuxAudioToVideo:
    """Tests for mux_audio_to_video()."""

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    def test_mux_success(self, mock_run, mock_exists):
        """Successful mux returns output path."""
        mock_run.return_value = MagicMock(returncode=0)

        result = mux_audio_to_video("/video.mp4", "/censored.wav", "/output.mp4")

        assert result == "/output.mp4"
        cmd = mock_run.call_args[0][0]
        assert "-map" in cmd
        assert "0:v:0" in cmd
        assert "1:a:0" in cmd

    @patch("video_utils.subprocess.run")
    def test_mux_failure_returns_none(self, mock_run):
        """Failed mux returns None."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="mux error",
        )

        result = mux_audio_to_video("/video.mp4", "/censored.wav", "/output.mp4")
        assert result is None


class TestGetH264EncoderArgs:
    """Tests for get_h264_encoder_args()."""

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_default(self):
        """Returns libx264 args when NVENC is disabled."""
        args = get_h264_encoder_args()
        assert "-c:v" in args
        assert "libx264" in args
        assert "-preset" in args
        assert "medium" in args
        assert "-crf" in args
        assert "18" in args
        assert "-pix_fmt" in args
        assert "yuv420p" in args
        assert "-profile:v" in args
        assert "high" in args

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_no_profile(self):
        """Omitting profile skips -profile:v flag for libx264."""
        args = get_h264_encoder_args(profile=None)
        assert "-profile:v" not in args

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_custom_preset(self):
        """Custom preset is passed through for libx264."""
        args = get_h264_encoder_args(preset="fast", crf=23)
        assert "fast" in args
        assert "23" in args

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_default(self):
        """Returns NVENC args when USE_NVENC is True."""
        args = get_h264_encoder_args()
        assert "-c:v" in args
        assert "h264_nvenc" in args
        assert "-preset" in args
        assert "p4" in args
        assert "-cq" in args
        assert "18" in args
        assert "-profile:v" in args
        assert "high" in args
        assert "-pix_fmt" in args
        assert "yuv420p" in args

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_preset_mapping(self):
        """NVENC maps libx264 preset names to p-levels."""
        args_fast = get_h264_encoder_args(preset="fast")
        assert "p2" in args_fast

        args_slow = get_h264_encoder_args(preset="slow")
        assert "p6" in args_slow

        args_ultrafast = get_h264_encoder_args(preset="ultrafast")
        assert "p1" in args_ultrafast

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_unknown_preset_defaults_p4(self):
        """Unknown preset names fall back to p4 for NVENC."""
        args = get_h264_encoder_args(preset="veryslow")
        assert "p4" in args

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_uses_cq_not_crf(self):
        """NVENC uses -cq instead of -crf."""
        args = get_h264_encoder_args(crf=23)
        assert "-cq" in args
        assert "-crf" not in args


class TestDetectNvenc:
    """Tests for _detect_nvenc()."""

    @patch("config._nvenc_cache", None)
    @patch("config.subprocess.run")
    def test_detect_nvenc_available(self, mock_run):
        """Returns True when h264_nvenc is in FFmpeg encoder list."""
        mock_run.return_value = MagicMock(
            stdout=" V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)\n"
        )
        from config import _detect_nvenc

        result = _detect_nvenc("ffmpeg")
        assert result is True

    @patch("config._nvenc_cache", None)
    @patch("config.subprocess.run")
    def test_detect_nvenc_not_available(self, mock_run):
        """Returns False when h264_nvenc is not in FFmpeg encoder list."""
        mock_run.return_value = MagicMock(
            stdout=" V..... libx264              libx264 H.264 / AVC\n"
        )
        from config import _detect_nvenc

        result = _detect_nvenc("ffmpeg")
        assert result is False

    @patch("config._nvenc_cache", None)
    @patch("config.subprocess.run")
    def test_detect_nvenc_ffmpeg_error(self, mock_run):
        """Returns False when FFmpeg fails to run."""
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        from config import _detect_nvenc

        result = _detect_nvenc("ffmpeg")
        assert result is False

    @patch("config._nvenc_cache", True)
    def test_detect_nvenc_uses_cache(self):
        """Returns cached value without running FFmpeg again."""
        from config import _detect_nvenc

        result = _detect_nvenc("ffmpeg")
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
