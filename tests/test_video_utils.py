"""Tests for video_utils module — FFmpeg video operations."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from config import Config

import video_utils
from video_utils import (
    is_video_file,
    probe_video,
    extract_audio,
    cut_video_clip,
    mux_audio_to_video,
    get_h264_encoder_args,
)


@pytest.fixture(autouse=True)
def _clear_probe_cache():
    """Clear probe cache between tests to prevent state leakage."""
    video_utils._probe_cache.clear()
    yield
    video_utils._probe_cache.clear()


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


class TestProbeVideoCache:
    """Tests for probe_video() result caching."""

    @patch("video_utils.subprocess.run")
    def test_probe_cache_avoids_repeated_subprocess(self, mock_run):
        """Second probe_video call for same path uses cache, skips subprocess."""
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
                    "format": {"duration": "100"},
                }
            ),
        )

        result1 = probe_video("/same/video.mp4")
        result2 = probe_video("/same/video.mp4")

        assert result1 == result2
        mock_run.assert_called_once()  # Only one subprocess call, second was cached

    @patch("video_utils.subprocess.run")
    def test_different_paths_not_cached(self, mock_run):
        """Different paths are probed independently."""
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
                    "format": {"duration": "100"},
                }
            ),
        )

        probe_video("/video_a.mp4")
        probe_video("/video_b.mp4")

        assert mock_run.call_count == 2


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
        # Probe fails in test → defaults to 1280x720 (horizontal) → uses -filter_complex
        # with blurred background layout (default); split layout requires VIDEO_LAYOUT=split
        if "-filter_complex" in cmd:
            fc_idx = cmd.index("-filter_complex")
            fc_value = cmd[fc_idx + 1]
            assert "scale=720" in fc_value
            assert "gblur" in fc_value or "crop=" in fc_value
        else:
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
    def test_libx264_writes_bt709_to_sps_via_x264_params(self):
        """B023 regression: -color_primaries/-color_trc/-colorspace bt709 on
        the FFmpeg command line are container-level metadata; libx264 does
        NOT always copy them into the H.264 SPS VUI. The result was clips
        with color_transfer=unspecified that hung Drive's transcoder. Fix:
        emit -x264-params with explicit colorprim/transfer/colormatrix so
        libx264 writes the correct values into the bitstream.

        See open_b023_regression.md (resolved 2026-04-27) for context."""
        args = get_h264_encoder_args()
        assert "-x264-params" in args
        idx = args.index("-x264-params")
        assert "colorprim=bt709" in args[idx + 1]
        assert "transfer=bt709" in args[idx + 1]
        assert "colormatrix=bt709" in args[idx + 1]

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_custom_preset(self):
        """Custom preset is passed through for libx264."""
        args = get_h264_encoder_args(preset="fast", crf=23)
        assert "fast" in args
        assert "23" in args

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_includes_h264_metadata_bsf(self):
        """Belt-and-suspenders: even if -x264-params is enough on most builds,
        the post-encode h264_metadata bsf rewrites SPS bytes deterministically
        so we never ship clips with `unspecified` color metadata regardless
        of encoder version. Same operation as remux_color_metadata.py."""
        args = get_h264_encoder_args()
        assert "-bsf:v" in args
        idx = args.index("-bsf:v")
        bsf_arg = args[idx + 1]
        assert "h264_metadata" in bsf_arg
        assert "colour_primaries=1" in bsf_arg
        assert "transfer_characteristics=1" in bsf_arg
        assert "matrix_coefficients=1" in bsf_arg

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_includes_h264_metadata_bsf(self):
        """NVENC was the actual broken path on 2026-04-27 — all 50 clips that
        session were h264_nvenc-encoded and shipped with `unspecified`. The
        SPS-rewrite bsf must apply equally to NVENC outputs."""
        args = get_h264_encoder_args()
        assert "h264_nvenc" in args
        assert "-bsf:v" in args
        idx = args.index("-bsf:v")
        assert "h264_metadata" in args[idx + 1]
        assert "colour_primaries=1" in args[idx + 1]

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

    @patch.object(Config, "USE_NVENC", False)
    def test_libx264_sets_bt709_color_metadata(self):
        """libx264 args tag output with consistent bt709 color metadata.

        Without this, lavfi `color=` sources default to bt470m transfer,
        producing a primaries/transfer mismatch that stalls Drive's
        transcoder ("still processing" hangs).
        """
        args = get_h264_encoder_args()
        assert "-color_primaries" in args
        assert "-color_trc" in args
        assert "-colorspace" in args
        assert "-color_range" in args
        for flag in ("-color_primaries", "-color_trc", "-colorspace"):
            assert args[args.index(flag) + 1] == "bt709"
        assert args[args.index("-color_range") + 1] == "tv"

    @patch.object(Config, "USE_NVENC", True)
    def test_nvenc_sets_bt709_color_metadata(self):
        """NVENC args tag output with consistent bt709 color metadata."""
        args = get_h264_encoder_args()
        assert "-color_primaries" in args
        assert "-color_trc" in args
        assert "-colorspace" in args
        assert "-color_range" in args
        for flag in ("-color_primaries", "-color_trc", "-colorspace"):
            assert args[args.index(flag) + 1] == "bt709"
        assert args[args.index("-color_range") + 1] == "tv"


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


class TestExtractAudioErrors:
    """Tests for extract_audio error paths."""

    @patch("video_utils.Path.exists", return_value=False)
    @patch("video_utils.subprocess.run")
    def test_no_output_file_returns_none(self, mock_run, mock_exists):
        """Returns None when output file not created."""
        mock_run.return_value = MagicMock(returncode=0)

        result = extract_audio("/video.mp4", "/audio.wav")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        """Returns None on timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 600)

        result = extract_audio("/video.mp4", "/audio.wav")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_generic_error_returns_none(self, mock_run):
        """Returns None on generic exception."""
        mock_run.side_effect = OSError("disk full")

        result = extract_audio("/video.mp4", "/audio.wav")
        assert result is None


class TestMuxAudioErrors:
    """Tests for mux_audio_to_video error paths."""

    @patch("video_utils.Path.exists", return_value=False)
    @patch("video_utils.subprocess.run")
    def test_no_output_returns_none(self, mock_run, mock_exists):
        """Returns None when output file not created."""
        mock_run.return_value = MagicMock(returncode=0)

        result = mux_audio_to_video("/video.mp4", "/audio.wav", "/out.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        """Returns None on timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 600)

        result = mux_audio_to_video("/video.mp4", "/audio.wav", "/out.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_generic_error_returns_none(self, mock_run):
        """Returns None on generic exception."""
        mock_run.side_effect = RuntimeError("broken")

        result = mux_audio_to_video("/video.mp4", "/audio.wav", "/out.mp4")
        assert result is None


class TestCutVideoClipErrors:
    """Tests for cut_video_clip error paths."""

    @patch("video_utils.Path.exists", return_value=False)
    @patch("video_utils.subprocess.run")
    def test_no_output_returns_none(self, mock_run, mock_exists):
        """Returns None when output file not created."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip("/video.mp4", 0.0, 10.0, "/clip.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_timeout_returns_none(self, mock_run):
        """Returns None on timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 300)

        result = cut_video_clip("/video.mp4", 0.0, 10.0, "/clip.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    def test_generic_error_returns_none(self, mock_run):
        """Returns None on generic exception."""
        mock_run.side_effect = OSError("disk error")

        result = cut_video_clip("/video.mp4", 0.0, 10.0, "/clip.mp4")
        assert result is None


class TestBurnSubtitlesOnVideo:
    """Tests for burn_subtitles_on_video."""

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_success(self, mock_escape, mock_run, mock_exists):
        """Returns output path on success."""
        mock_run.return_value = MagicMock(returncode=0)

        from video_utils import burn_subtitles_on_video

        result = burn_subtitles_on_video("/clip.mp4", "/clip.ass", "/output.mp4")
        assert result == "/output.mp4"

    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_failure_returns_none(self, mock_escape, mock_run):
        """Returns None on FFmpeg failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="burn error")

        from video_utils import burn_subtitles_on_video

        result = burn_subtitles_on_video("/clip.mp4", "/clip.ass", "/output.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_timeout_returns_none(self, mock_escape, mock_run):
        """Returns None on timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 300)

        from video_utils import burn_subtitles_on_video

        result = burn_subtitles_on_video("/clip.mp4", "/clip.ass", "/output.mp4")
        assert result is None


class TestProbeVideoPlainFps:
    """Tests for probe_video() with non-fractional fps string."""

    @patch("video_utils.subprocess.run")
    def test_probe_plain_fps_no_slash(self, mock_run):
        """Plain fps string (no '/') is parsed as a float directly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "streams": [
                        {
                            "width": 1280,
                            "height": 720,
                            "r_frame_rate": "25",
                            "codec_name": "h264",
                        }
                    ],
                    "format": {"duration": "60"},
                }
            ),
        )

        result = probe_video("/path/to/plain_fps.mp4")

        assert result is not None
        assert result["fps"] == 25.0


class TestCutVideoClipWithSubtitles:
    """Tests for cut_video_clip() subtitle burn-in paths."""

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    @patch("video_utils.probe_video", return_value={"width": 1920, "height": 1080})
    def test_cut_vertical_horizontal_source_with_subtitles(
        self, mock_probe, mock_escape, mock_run, mock_exists
    ):
        """Horizontal source with crop_vertical=True and ass_path uses filter_complex with subtitles."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip(
            "/video.mp4",
            5.0,
            15.0,
            "/clip.mp4",
            crop_vertical=True,
            ass_path="/subs.ass",
        )

        assert result == "/clip.mp4"
        cmd = mock_run.call_args[0][0]
        fc_idx = cmd.index("-filter_complex")
        fc_value = cmd[fc_idx + 1]
        assert "subtitles=" in fc_value
        assert "[composed]" in fc_value

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    @patch("video_utils.probe_video", return_value={"width": 720, "height": 1280})
    def test_cut_vertical_square_source_with_subtitles(
        self, mock_probe, mock_escape, mock_run, mock_exists
    ):
        """Vertical/square source with crop_vertical=True and ass_path uses -vf with subtitles."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip(
            "/video.mp4",
            5.0,
            15.0,
            "/clip.mp4",
            crop_vertical=True,
            ass_path="/subs.ass",
        )

        assert result == "/clip.mp4"
        cmd = mock_run.call_args[0][0]
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert "subtitles=" in vf_value
        assert "scale=720:1280" in vf_value

    @patch("video_utils.Path.exists", return_value=True)
    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_cut_no_crop_with_subtitles(self, mock_escape, mock_run, mock_exists):
        """Non-cropped clip with ass_path burns subtitles via -vf filter."""
        mock_run.return_value = MagicMock(returncode=0)

        result = cut_video_clip(
            "/video.mp4",
            0.0,
            10.0,
            "/clip.mp4",
            crop_vertical=False,
            ass_path="/subs.ass",
        )

        assert result == "/clip.mp4"
        cmd = mock_run.call_args[0][0]
        vf_idx = cmd.index("-vf")
        vf_value = cmd[vf_idx + 1]
        assert "subtitles=" in vf_value
        assert "fontsdir=" in vf_value


class TestBurnSubtitlesErrors:
    """Tests for burn_subtitles_on_video additional error paths."""

    @patch("video_utils.Path.exists", return_value=False)
    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_no_output_file_returns_none(self, mock_escape, mock_run, mock_exists):
        """Returns None when output file is not created after success returncode."""
        mock_run.return_value = MagicMock(returncode=0)

        from video_utils import burn_subtitles_on_video

        result = burn_subtitles_on_video("/clip.mp4", "/clip.ass", "/output.mp4")
        assert result is None

    @patch("video_utils.subprocess.run")
    @patch(
        "subtitle_clip_generator.SubtitleClipGenerator._escape_ffmpeg_filter_path",
        side_effect=lambda p: p,
    )
    def test_generic_exception_returns_none(self, mock_escape, mock_run):
        """Returns None on generic exception during subtitle burn."""
        mock_run.side_effect = OSError("disk full")

        from video_utils import burn_subtitles_on_video

        result = burn_subtitles_on_video("/clip.mp4", "/clip.ass", "/output.mp4")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
