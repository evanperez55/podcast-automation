"""Tests for Spotify uploader module (RSS-only)."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from uploaders.spotify_uploader import SpotifyUploader, create_spotify_episode_data
from config import Config


class TestSpotifyUploader:
    """Test cases for SpotifyUploader class (RSS-only, no API)."""

    def test_init_no_credentials_needed(self):
        """Test initialization requires no API credentials."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator"):
            uploader = SpotifyUploader()
            assert uploader.rss_generator is not None

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_generate_rss_item(self):
        """Test RSS item generation."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator"):
            uploader = SpotifyUploader()

        rss_item = uploader.generate_rss_item(
            episode_number=1,
            title="Test Episode",
            description="Test Description",
            audio_url="https://example.com/audio.mp3",
            audio_file_size=10000000,
            duration_seconds=3600,
            pub_date=datetime(2024, 1, 1),
        )

        assert "<item>" in rss_item
        assert "Test Episode" in rss_item
        assert "Test Description" in rss_item
        assert "https://example.com/audio.mp3" in rss_item
        assert "<itunes:episode>1</itunes:episode>" in rss_item
        assert "01:00:00" in rss_item

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_create_episode_metadata(self):
        """Test episode metadata creation."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator"):
            uploader = SpotifyUploader()

        metadata = uploader.create_episode_metadata(
            episode_number=1, summary="Test summary", duration_seconds=3600
        )

        assert "title" in metadata
        assert "Episode 1" in metadata["title"]
        assert metadata["description"] == "Test summary"
        assert metadata["episode_number"] == 1
        assert metadata["duration_seconds"] == 3600

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_generate_rss_item_default_pub_date(self):
        """Test RSS item uses current time when no pub_date provided."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator"):
            uploader = SpotifyUploader()

        rss_item = uploader.generate_rss_item(
            episode_number=5,
            title="No Date Episode",
            description="Testing default date",
            audio_url="https://example.com/ep5.mp3",
            audio_file_size=5000000,
            duration_seconds=1800,
        )

        assert "<item>" in rss_item
        assert "No Date Episode" in rss_item
        assert "00:30:00" in rss_item


class TestCreateSpotifyEpisodeData:
    """Test cases for create_spotify_episode_data function."""

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("pathlib.Path.exists")
    def test_create_episode_data(self, mock_exists):
        """Test episode data creation."""
        mock_exists.return_value = True

        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=10000000)

            data = create_spotify_episode_data(
                episode_number=1,
                episode_summary="Test summary",
                audio_url="https://example.com/audio.mp3",
                audio_file_path=__file__,
                duration_seconds=3600,
            )

            assert data["episode_number"] == 1
            assert "Episode 1" in data["title"]
            assert data["description"] == "Test summary"
            assert data["audio_url"] == "https://example.com/audio.mp3"
            assert data["audio_file_size"] == 10000000
            assert data["duration_seconds"] == 3600

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("pathlib.Path.exists")
    def test_create_episode_data_missing_file(self, mock_exists):
        """Test episode data with missing file."""
        mock_exists.return_value = False

        data = create_spotify_episode_data(
            episode_number=1,
            episode_summary="Test",
            audio_url="https://example.com/audio.mp3",
            audio_file_path="/nonexistent/file.mp3",
            duration_seconds=3600,
        )

        assert data["audio_file_size"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
