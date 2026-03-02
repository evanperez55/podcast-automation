"""Tests for video_converter module."""

import pytest
from unittest.mock import patch, MagicMock
from video_converter import VideoConverter


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
