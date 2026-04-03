"""Tests for Spotify uploader module (RSS-only)."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from uploaders.spotify_uploader import SpotifyUploader
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


class TestUpdateRssFeed:
    """Tests for update_rss_feed."""

    def test_update_with_existing_metadata(self):
        """Updates feed using existing metadata."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator") as mock_rss_cls:
            mock_rss = mock_rss_cls.return_value
            mock_rss.load_podcast_metadata.return_value = {
                "title": "My Podcast",
                "description": "A podcast",
                "author": "Host",
                "website_url": "https://example.com",
                "email": "host@example.com",
                "categories": ["Comedy"],
            }
            mock_rss.update_or_create_feed.return_value = Mock()
            mock_rss.feed_path = "/output/feed.xml"

            uploader = SpotifyUploader()
            result = uploader.update_rss_feed(
                episode_number=5,
                episode_title="Ep 5",
                episode_description="Description",
                audio_url="https://example.com/ep5.mp3",
                audio_file_size=10000,
                duration_seconds=1800,
            )

            mock_rss.update_or_create_feed.assert_called_once()
            mock_rss.save_feed.assert_called_once()
            assert result == "/output/feed.xml"

    def test_update_with_no_metadata_uses_defaults(self):
        """Uses default metadata when none exists."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator") as mock_rss_cls:
            mock_rss = mock_rss_cls.return_value
            mock_rss.load_podcast_metadata.return_value = {}
            mock_rss.update_or_create_feed.return_value = Mock()
            mock_rss.feed_path = "/output/feed.xml"

            uploader = SpotifyUploader()
            uploader.update_rss_feed(
                episode_number=1,
                episode_title="Ep 1",
                episode_description="Desc",
                audio_url="https://example.com/ep1.mp3",
                audio_file_size=5000,
                duration_seconds=600,
            )

            call_args = mock_rss.update_or_create_feed.call_args
            metadata = call_args.kwargs["podcast_metadata"]
            assert metadata["categories"] == ["Comedy"]


class TestSetupPodcastMetadata:
    """Tests for setup_podcast_metadata."""

    def test_saves_metadata(self):
        """Saves podcast metadata via rss_generator."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator") as mock_rss_cls:
            mock_rss = mock_rss_cls.return_value

            uploader = SpotifyUploader()
            uploader.setup_podcast_metadata(
                title="My Show",
                description="A show",
                author="Me",
                email="me@example.com",
                website_url="https://example.com",
                categories=["Comedy", "News"],
            )

            mock_rss.save_podcast_metadata.assert_called_once()
            saved = mock_rss.save_podcast_metadata.call_args[0][0]
            assert saved["title"] == "My Show"
            assert saved["categories"] == ["Comedy", "News"]


class TestValidateRssFeed:
    """Tests for validate_rss_feed."""

    def test_delegates_to_rss_generator(self):
        """Delegates validation to rss_generator."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator") as mock_rss_cls:
            mock_rss = mock_rss_cls.return_value
            mock_rss.validate_feed.return_value = {"valid": True}

            uploader = SpotifyUploader()
            result = uploader.validate_rss_feed()

            assert result["valid"] is True


class TestGeneratePodcastRssFeed:
    """Tests for generate_podcast_rss_feed."""

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_generates_complete_feed(self):
        """Generates complete RSS feed XML."""
        with patch("uploaders.spotify_uploader.RSSFeedGenerator"):
            uploader = SpotifyUploader()

        result = uploader.generate_podcast_rss_feed(
            episodes_data=[
                {
                    "episode_number": 1,
                    "title": "Ep 1",
                    "description": "First",
                    "audio_url": "https://example.com/ep1.mp3",
                    "audio_file_size": 5000,
                    "duration_seconds": 300,
                    "pub_date": datetime(2026, 1, 1),
                },
            ],
            podcast_title="Test Show",
            podcast_description="A test show",
            podcast_author="Host",
            podcast_email="host@example.com",
            podcast_category="Comedy",
            podcast_image_url="https://example.com/art.jpg",
            podcast_website="https://example.com",
        )

        assert '<?xml version="1.0"' in result
        assert "Test Show" in result
        assert "Ep 1" in result
        assert "</rss>" in result
        assert "itunes:image" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
