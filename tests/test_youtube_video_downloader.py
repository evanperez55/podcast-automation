"""Tests for YouTube video downloader module."""

from unittest.mock import MagicMock, patch

import pytest

from youtube_video_downloader import YouTubeVideoDownloader


class TestYouTubeVideoDownloaderInit:
    """Tests for YouTubeVideoDownloader initialization."""

    def test_init_enabled(self):
        """Downloader is enabled when yt-dlp is importable."""
        downloader = YouTubeVideoDownloader()
        assert downloader.enabled is True

    def test_init_disabled_no_ytdlp(self):
        """Downloader is disabled when yt-dlp is not importable."""
        real_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )

        def mock_import(name, *args, **kwargs):
            if name == "yt_dlp":
                raise ImportError("No module named 'yt_dlp'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            downloader = YouTubeVideoDownloader()
            assert downloader.enabled is False


def _make_mock_ydl(extract_return=None, extract_side_effect=None, filename=None):
    """Helper to create a mock yt-dlp YoutubeDL context manager."""
    mock_ydl = MagicMock()
    if extract_side_effect:
        mock_ydl.extract_info.side_effect = extract_side_effect
    else:
        mock_ydl.extract_info.return_value = extract_return
    if filename:
        mock_ydl.prepare_filename.return_value = filename
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    return mock_ydl


class TestDownloadLatest:
    """Tests for YouTubeVideoDownloader.download_latest."""

    def test_returns_none_when_disabled(self, tmp_path):
        """Returns None immediately when yt-dlp is not available."""
        downloader = YouTubeVideoDownloader()
        downloader.enabled = False
        result = downloader.download_latest("https://youtube.com/@test", tmp_path)
        assert result is None

    @patch("yt_dlp.YoutubeDL")
    def test_returns_none_on_list_failure(self, mock_ydl_cls, tmp_path):
        """Returns None when channel listing fails."""
        mock_ydl_cls.return_value = _make_mock_ydl(
            extract_side_effect=Exception("Network error")
        )
        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest("https://youtube.com/@test", tmp_path)
        assert result is None

    @patch("yt_dlp.YoutubeDL")
    def test_returns_none_when_no_videos(self, mock_ydl_cls, tmp_path):
        """Returns None when channel has no videos."""
        mock_ydl_cls.return_value = _make_mock_ydl(extract_return={"entries": []})
        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest("https://youtube.com/@test", tmp_path)
        assert result is None

    @patch("yt_dlp.YoutubeDL")
    def test_downloads_latest_video(self, mock_ydl_cls, tmp_path):
        """Downloads the latest video and returns path."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video data")

        list_ydl = _make_mock_ydl(
            extract_return={
                "entries": [{"id": "abc123", "title": "Test Video", "url": None}]
            }
        )
        dl_ydl = _make_mock_ydl(
            extract_return={"title": "Test Video"}, filename=str(video_file)
        )
        mock_ydl_cls.side_effect = [list_ydl, dl_ydl]

        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest("https://youtube.com/@test", tmp_path)
        assert result == video_file

    @patch("yt_dlp.YoutubeDL")
    def test_matches_title(self, mock_ydl_cls, tmp_path):
        """Downloads video matching the given title."""
        video_file = tmp_path / "breaking_bad_habits.mp4"
        video_file.write_bytes(b"fake video data")

        list_ydl = _make_mock_ydl(
            extract_return={
                "entries": [
                    {"id": "older", "title": "Old Episode", "url": None},
                    {"id": "match", "title": "Breaking Bad Habits", "url": None},
                ]
            }
        )
        dl_ydl = _make_mock_ydl(
            extract_return={"title": "Breaking Bad Habits"},
            filename=str(video_file),
        )
        mock_ydl_cls.side_effect = [list_ydl, dl_ydl]

        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest(
            "https://youtube.com/@test", tmp_path, match_title="Breaking Bad"
        )
        assert result == video_file

    @patch("yt_dlp.YoutubeDL")
    def test_falls_back_to_latest_on_no_match(self, mock_ydl_cls, tmp_path):
        """Falls back to latest video when title doesn't match."""
        video_file = tmp_path / "latest_video.mp4"
        video_file.write_bytes(b"fake video data")

        list_ydl = _make_mock_ydl(
            extract_return={
                "entries": [
                    {"id": "latest", "title": "Latest Episode", "url": None},
                    {"id": "older", "title": "Old Episode", "url": None},
                ]
            }
        )
        dl_ydl = _make_mock_ydl(
            extract_return={"title": "Latest Episode"},
            filename=str(video_file),
        )
        mock_ydl_cls.side_effect = [list_ydl, dl_ydl]

        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest(
            "https://youtube.com/@test", tmp_path, match_title="Nonexistent Title"
        )
        assert result == video_file

    @patch("yt_dlp.YoutubeDL")
    def test_returns_none_on_download_failure(self, mock_ydl_cls, tmp_path):
        """Returns None when video download fails."""
        list_ydl = _make_mock_ydl(
            extract_return={"entries": [{"id": "abc", "title": "Test", "url": None}]}
        )
        dl_ydl = _make_mock_ydl(extract_side_effect=Exception("Download failed"))
        mock_ydl_cls.side_effect = [list_ydl, dl_ydl]

        downloader = YouTubeVideoDownloader()
        result = downloader.download_latest("https://youtube.com/@test", tmp_path)
        assert result is None


class TestDownloadUrl:
    """Tests for YouTubeVideoDownloader.download_url."""

    def test_returns_none_when_disabled(self, tmp_path):
        """Returns None when disabled."""
        downloader = YouTubeVideoDownloader()
        downloader.enabled = False
        result = downloader.download_url("https://youtube.com/watch?v=abc", tmp_path)
        assert result is None

    @patch("yt_dlp.YoutubeDL")
    def test_downloads_specific_url(self, mock_ydl_cls, tmp_path):
        """Downloads video by URL and returns path."""
        video_file = tmp_path / "specific_video.mp4"
        video_file.write_bytes(b"fake video data")

        mock_ydl_cls.return_value = _make_mock_ydl(
            extract_return={"title": "Specific Video"},
            filename=str(video_file),
        )

        downloader = YouTubeVideoDownloader()
        result = downloader.download_url("https://youtube.com/watch?v=abc", tmp_path)
        assert result == video_file

    @patch("yt_dlp.YoutubeDL")
    def test_returns_none_on_failure(self, mock_ydl_cls, tmp_path):
        """Returns None when download fails."""
        mock_ydl_cls.return_value = _make_mock_ydl(
            extract_side_effect=Exception("Download failed")
        )

        downloader = YouTubeVideoDownloader()
        result = downloader.download_url("https://youtube.com/watch?v=abc", tmp_path)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
