"""Tests for video_converter module."""

import subprocess

import pytest
from unittest.mock import patch, MagicMock
from config import Config
from video_converter import VideoConverter, get_video_duration


@pytest.fixture
def converter(tmp_path):
    logo = tmp_path / "logo.jpg"
    logo.write_bytes(b"\xff\xd8\xff\xe0")  # minimal JPEG header
    with patch.object(VideoConverter, "__init__", lambda self, **kw: None):
        vc = VideoConverter()
        vc.logo_path = str(logo)
        vc.ffmpeg_path = "ffmpeg"
        return vc


class TestAudioToVideo:
    @patch("video_converter.subprocess.run")
    def test_success(self, mock_run, converter, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        result = converter.audio_to_video(str(audio))
        assert result is not None
        assert result.endswith(".mp4")
        mock_run.assert_called_once()

    @patch("video_converter.subprocess.run")
    def test_ffmpeg_failure(self, mock_run, converter, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        result = converter.audio_to_video(str(audio))
        assert result is None

    def test_missing_audio(self, converter):
        result = converter.audio_to_video("/nonexistent/file.wav")
        assert result is None


class TestAudioToVideoWithSubtitles:
    @patch("video_converter.subprocess.run")
    def test_with_srt(self, mock_run, converter, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
        mock_run.return_value = MagicMock(returncode=0)

        result = converter.audio_to_video_with_subtitles(str(audio), str(srt))
        assert result is not None
        # Check subtitle filter is in command
        cmd_args = mock_run.call_args[0][0]
        vf_arg = [a for a in cmd_args if "subtitles=" in str(a)]
        assert len(vf_arg) > 0

    @patch("video_converter.subprocess.run")
    def test_fallback_on_missing_srt(self, mock_run, converter, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        result = converter.audio_to_video_with_subtitles(str(audio), "/no/such.srt")
        assert result is not None  # Falls back to no subtitles

    @patch("video_converter.subprocess.run")
    def test_fallback_on_subtitle_burn_failure(self, mock_run, converter, tmp_path):
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
        # First call fails (subtitle), second succeeds (fallback)
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="subtitle error"),
            MagicMock(returncode=0),
        ]

        result = converter.audio_to_video_with_subtitles(str(audio), str(srt))
        assert result is not None
        assert mock_run.call_count == 2


class TestConvertClipsToVideos:
    @patch("video_converter.subprocess.run")
    def test_multiple_clips(self, mock_run, converter, tmp_path):
        clips = []
        for i in range(3):
            p = tmp_path / f"clip{i}.wav"
            p.write_text("fake")
            clips.append(str(p))
        mock_run.return_value = MagicMock(returncode=0)

        results = converter.convert_clips_to_videos(clips, output_dir=str(tmp_path))
        assert len(results) == 3

    @patch("video_converter.subprocess.run")
    def test_with_srt_paths(self, mock_run, converter, tmp_path):
        clip = tmp_path / "clip.wav"
        clip.write_text("fake")
        srt = tmp_path / "clip.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
        mock_run.return_value = MagicMock(returncode=0)

        results = converter.convert_clips_to_videos(
            [str(clip)], output_dir=str(tmp_path), srt_paths=[str(srt)]
        )
        assert len(results) == 1


class TestVideoConverterInit:
    """Tests for VideoConverter initialization."""

    def test_init_with_logo_path(self, tmp_path):
        """Accepts explicit logo path."""
        logo = tmp_path / "custom_logo.jpg"
        logo.write_bytes(b"\xff\xd8")

        vc = VideoConverter(logo_path=str(logo))
        assert vc.logo_path == str(logo)

    def test_init_client_logo(self, tmp_path, monkeypatch):
        """Uses CLIENT_LOGO_PATH when set."""
        logo = tmp_path / "client_logo.png"
        logo.write_bytes(b"\xff\xd8")
        monkeypatch.setattr(Config, "CLIENT_LOGO_PATH", str(logo))

        vc = VideoConverter()
        assert vc.logo_path == str(logo)

    def test_init_missing_logo_raises(self):
        """Raises FileNotFoundError when logo doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Logo file not found"):
            VideoConverter(logo_path="/nonexistent/logo.jpg")


class TestFaststartFlag:
    """Tests that -movflags +faststart is included in FFmpeg commands."""

    @patch("video_converter.subprocess.run")
    def test_audio_to_video_has_faststart(self, mock_run, converter, tmp_path):
        """audio_to_video includes -movflags +faststart for progressive playback."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        converter.audio_to_video(str(audio))

        cmd = mock_run.call_args[0][0]
        assert "-movflags" in cmd
        assert "+faststart" in cmd

    @patch("video_converter.subprocess.run")
    def test_subtitle_video_has_faststart(self, mock_run, converter, tmp_path):
        """audio_to_video_with_subtitles includes -movflags +faststart."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
        mock_run.return_value = MagicMock(returncode=0)

        converter.audio_to_video_with_subtitles(str(audio), str(srt))

        cmd = mock_run.call_args[0][0]
        assert "-movflags" in cmd
        assert "+faststart" in cmd


class TestAudioToVideoFormats:
    """Tests for different format types."""

    @patch("video_converter.subprocess.run")
    def test_custom_resolution(self, mock_run, converter, tmp_path):
        """Custom resolution is used in FFmpeg command."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        converter.audio_to_video(str(audio), resolution=(800, 600))

        cmd = mock_run.call_args[0][0]
        vf = [a for a in cmd if "800:600" in str(a)]
        assert len(vf) > 0

    @patch("video_converter.subprocess.run")
    def test_vertical_format(self, mock_run, converter, tmp_path):
        """Vertical format uses Config.VERTICAL_RESOLUTION."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        converter.audio_to_video(str(audio), format_type="vertical")

        cmd = mock_run.call_args[0][0]
        vf_args = " ".join(str(a) for a in cmd)
        assert "720:1280" in vf_args

    @patch("video_converter.subprocess.run")
    def test_square_format(self, mock_run, converter, tmp_path):
        """Square format uses Config.SQUARE_RESOLUTION."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        converter.audio_to_video(str(audio), format_type="square")

        cmd = mock_run.call_args[0][0]
        vf_args = " ".join(str(a) for a in cmd)
        assert "720:720" in vf_args

    @patch("video_converter.subprocess.run")
    def test_timeout_returns_none(self, mock_run, converter, tmp_path):
        """Returns None on timeout."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 7200)

        result = converter.audio_to_video(str(audio))
        assert result is None

    @patch("video_converter.subprocess.run")
    def test_generic_error_returns_none(self, mock_run, converter, tmp_path):
        """Returns None on generic error."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        mock_run.side_effect = OSError("broken")

        result = converter.audio_to_video(str(audio))
        assert result is None


class TestSubtitleErrors:
    """Tests for subtitle video error paths."""

    def test_missing_audio_returns_none(self, converter):
        """Returns None when audio file doesn't exist."""
        result = converter.audio_to_video_with_subtitles("/no.wav", "/no.srt")
        assert result is None

    @patch("video_converter.subprocess.run")
    def test_timeout_returns_none(self, mock_run, converter, tmp_path):
        """Returns None on timeout."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 7200)

        result = converter.audio_to_video_with_subtitles(str(audio), str(srt))
        assert result is None

    @patch("video_converter.subprocess.run")
    def test_exception_falls_back(self, mock_run, converter, tmp_path):
        """Falls back to no subtitles on exception."""
        audio = tmp_path / "test.wav"
        audio.write_text("fake")
        srt = tmp_path / "test.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
        # First call raises, second (fallback) succeeds
        mock_run.side_effect = [OSError("broken"), MagicMock(returncode=0)]

        result = converter.audio_to_video_with_subtitles(str(audio), str(srt))
        assert result is not None


class TestCreateEpisodeVideo:
    """Tests for create_episode_video."""

    @patch("video_converter.subprocess.run")
    def test_creates_horizontal_video(self, mock_run, converter, tmp_path):
        """Creates a horizontal video for full episode."""
        audio = tmp_path / "episode.wav"
        audio.write_text("fake")
        mock_run.return_value = MagicMock(returncode=0)

        result = converter.create_episode_video(str(audio))
        assert result is not None


class TestGetVideoDuration:
    """Tests for get_video_duration standalone function."""

    @patch("video_converter.subprocess.run")
    def test_returns_duration(self, mock_run):
        """Returns duration float on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="123.45\n")

        result = get_video_duration("/video.mp4")
        assert result == pytest.approx(123.45)

    @patch("video_converter.subprocess.run")
    def test_returns_none_on_failure(self, mock_run):
        """Returns None on ffprobe failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = get_video_duration("/video.mp4")
        assert result is None

    @patch("video_converter.subprocess.run")
    def test_returns_none_on_exception(self, mock_run):
        """Returns None on exception."""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")

        result = get_video_duration("/video.mp4")
        assert result is None
