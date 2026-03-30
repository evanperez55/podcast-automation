"""Tests for pipeline.steps.ingest (run_ingest)."""

from unittest.mock import MagicMock, patch

import pytest

from config import Config
from pipeline.context import PipelineContext
from pipeline.steps.ingest import run_ingest


def _make_ctx(tmp_path, **overrides):
    """Create a minimal PipelineContext for testing."""
    defaults = {
        "episode_folder": str(tmp_path),
        "episode_number": None,
        "episode_output_dir": tmp_path,
        "timestamp": "20260329",
        "audio_file": None,
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)


class TestRunIngestLocal:
    """Tests for local file path ingestion."""

    @patch("video_utils.is_video_file", return_value=False)
    @patch(
        "pipeline.steps.ingest.extract_episode_number_from_filename", return_value=25
    )
    def test_local_audio_file(self, mock_extract, mock_is_video, tmp_path, monkeypatch):
        """Uses pre-set audio_file when it exists."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        audio = tmp_path / "ep25.wav"
        audio.write_bytes(b"fake")

        ctx = _make_ctx(tmp_path, audio_file=audio)
        result = run_ingest(ctx, {})

        assert result.audio_file == audio
        assert result.episode_number == 25
        assert result.episode_folder == "ep_25"


class TestRunIngestDropbox:
    """Tests for Dropbox source ingestion."""

    @patch("video_utils.is_video_file", return_value=False)
    @patch(
        "pipeline.steps.ingest.extract_episode_number_from_filename", return_value=30
    )
    def test_dropbox_download(self, mock_extract, mock_is_video, tmp_path, monkeypatch):
        """Downloads from Dropbox when no local file."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(Config, "EPISODE_SOURCE", "dropbox")

        audio = tmp_path / "ep30.wav"
        audio.write_bytes(b"fake")

        dropbox = MagicMock()
        dropbox.get_latest_episode.return_value = {
            "name": "ep30.wav",
            "path": "/ep30.wav",
        }
        dropbox.download_episode.return_value = audio

        ctx = _make_ctx(tmp_path)
        result = run_ingest(ctx, {"dropbox": dropbox})

        assert result.audio_file == audio
        dropbox.get_latest_episode.assert_called_once()

    @patch("video_utils.is_video_file", return_value=False)
    def test_dropbox_no_episodes_raises(self, mock_is_video, tmp_path, monkeypatch):
        """Raises when no episodes in Dropbox."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(Config, "EPISODE_SOURCE", "dropbox")

        dropbox = MagicMock()
        dropbox.get_latest_episode.return_value = None

        ctx = _make_ctx(tmp_path)
        with pytest.raises(Exception, match="No episodes found"):
            run_ingest(ctx, {"dropbox": dropbox})


class TestRunIngestRSS:
    """Tests for RSS feed source ingestion."""

    @patch("video_utils.is_video_file", return_value=False)
    @patch(
        "pipeline.steps.ingest.extract_episode_number_from_filename", return_value=10
    )
    def test_rss_download(self, mock_extract, mock_is_video, tmp_path, monkeypatch):
        """Downloads from RSS feed."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(Config, "EPISODE_SOURCE", "rss")
        monkeypatch.setattr(Config, "RSS_FEED_URL", "https://example.com/feed.xml")
        monkeypatch.setattr(Config, "RSS_EPISODE_INDEX", 0)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", tmp_path)

        audio = tmp_path / "ep10.mp3"
        audio.write_bytes(b"fake")

        meta = MagicMock()
        meta.audio_url = "https://example.com/ep10.mp3"
        meta.episode_number = 10

        fetcher = MagicMock()
        fetcher.fetch_episode.return_value = meta
        fetcher.download_audio.return_value = audio

        ctx = _make_ctx(tmp_path)
        result = run_ingest(ctx, {"rss_fetcher": fetcher})

        assert result.audio_file == audio
        assert result.episode_number == 10


class TestRunIngestVideoInput:
    """Tests for video file input detection."""

    @patch("video_utils.extract_audio", return_value="/extracted.wav")
    @patch(
        "video_utils.probe_video",
        return_value={"width": 1920, "height": 1080, "duration": 3600, "codec": "h264"},
    )
    @patch("video_utils.is_video_file", return_value=True)
    @patch("pipeline.steps.ingest.extract_episode_number_from_filename", return_value=5)
    def test_video_input_extracts_audio(
        self,
        mock_extract_ep,
        mock_is_video,
        mock_probe,
        mock_extract_audio,
        tmp_path,
        monkeypatch,
    ):
        """Video input triggers audio extraction."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", tmp_path)

        video = tmp_path / "ep5.mp4"
        video.write_bytes(b"fake video")

        ctx = _make_ctx(tmp_path, audio_file=video)
        result = run_ingest(ctx, {})

        assert result.has_video_source is True
        assert result.source_video_path == video
        assert result.video_metadata is not None

    @patch("video_utils.extract_audio", return_value=None)
    @patch("video_utils.probe_video", return_value=None)
    @patch("video_utils.is_video_file", return_value=True)
    @patch("pipeline.steps.ingest.extract_episode_number_from_filename", return_value=5)
    def test_video_extraction_failure_raises(
        self,
        mock_extract_ep,
        mock_is_video,
        mock_probe,
        mock_extract_audio,
        tmp_path,
        monkeypatch,
    ):
        """Raises when audio extraction from video fails."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        monkeypatch.setattr(Config, "DOWNLOAD_DIR", tmp_path)

        video = tmp_path / "ep5.mp4"
        video.write_bytes(b"fake video")

        ctx = _make_ctx(tmp_path, audio_file=video)
        with pytest.raises(Exception, match="Failed to extract audio"):
            run_ingest(ctx, {})


class TestEpisodeFolderNaming:
    """Tests for episode folder naming logic."""

    @patch("video_utils.is_video_file", return_value=False)
    @patch(
        "pipeline.steps.ingest.extract_episode_number_from_filename", return_value=None
    )
    def test_no_episode_number_uses_stem(
        self, mock_extract, mock_is_video, tmp_path, monkeypatch
    ):
        """When no episode number found, uses file stem + timestamp."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)

        audio = tmp_path / "mystery_show.wav"
        audio.write_bytes(b"fake")

        ctx = _make_ctx(tmp_path, audio_file=audio)
        result = run_ingest(ctx, {})

        assert "mystery_show" in result.episode_folder
        assert "20260329" in result.episode_folder


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
