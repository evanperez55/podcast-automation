"""Tests for Spotify uploader module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import requests

from uploaders.spotify_uploader import SpotifyUploader, create_spotify_episode_data
from config import Config


class TestSpotifyUploader:
    """Test cases for SpotifyUploader class."""

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'valid_client_id')
    @patch.object(Config, 'SPOTIFY_CLIENT_SECRET', 'valid_client_secret')
    @patch.object(Config, 'SPOTIFY_SHOW_ID', 'valid_show_id')
    @patch('requests.post')
    def test_init_with_valid_credentials(self, mock_post):
        """Test initialization with valid credentials."""
        # Mock authentication
        mock_post.return_value = Mock(
            json=lambda: {'access_token': 'token123'},
            raise_for_status=lambda: None
        )

        uploader = SpotifyUploader()

        assert uploader.client_id == 'valid_client_id'
        assert uploader.client_secret == 'valid_client_secret'
        assert uploader.show_id == 'valid_show_id'
        assert uploader.access_token == 'token123'

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'your_spotify_client_id_here')
    def test_init_without_client_id(self):
        """Test initialization fails without client ID."""
        with pytest.raises(ValueError, match="Spotify client ID not configured"):
            SpotifyUploader()

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'valid_client_id')
    @patch.object(Config, 'SPOTIFY_CLIENT_SECRET', 'valid_client_secret')
    @patch.object(Config, 'SPOTIFY_SHOW_ID', 'valid_show_id')
    @patch('requests.post')
    @patch('requests.get')
    def test_get_show_info_success(self, mock_get, mock_post):
        """Test successful show info retrieval."""
        # Mock authentication
        mock_post.return_value = Mock(
            json=lambda: {'access_token': 'token123'},
            raise_for_status=lambda: None
        )

        # Mock show info
        mock_get.return_value = Mock(
            json=lambda: {
                'id': 'show123',
                'name': 'Test Podcast',
                'publisher': 'Test Publisher',
                'description': 'Test Description',
                'total_episodes': 25,
                'external_urls': {'spotify': 'https://open.spotify.com/show/123'}
            },
            raise_for_status=lambda: None
        )

        uploader = SpotifyUploader()
        info = uploader.get_show_info()

        assert info is not None
        assert info['name'] == 'Test Podcast'
        assert info['total_episodes'] == 25

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'valid_client_id')
    @patch.object(Config, 'SPOTIFY_CLIENT_SECRET', 'valid_client_secret')
    @patch.object(Config, 'SPOTIFY_SHOW_ID', 'valid_show_id')
    @patch('requests.post')
    @patch('requests.get')
    def test_get_episodes_success(self, mock_get, mock_post):
        """Test successful episodes retrieval."""
        # Mock authentication
        mock_post.return_value = Mock(
            json=lambda: {'access_token': 'token123'},
            raise_for_status=lambda: None
        )

        # Mock episodes
        mock_get.return_value = Mock(
            json=lambda: {
                'items': [
                    {
                        'id': 'ep1',
                        'name': 'Episode 1',
                        'description': 'First episode',
                        'release_date': '2024-01-01',
                        'duration_ms': 3600000,
                        'external_urls': {'spotify': 'https://open.spotify.com/episode/ep1'}
                    }
                ]
            },
            raise_for_status=lambda: None
        )

        uploader = SpotifyUploader()
        episodes = uploader.get_episodes(limit=20)

        assert episodes is not None
        assert len(episodes) == 1
        assert episodes[0]['name'] == 'Episode 1'

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'valid_client_id')
    @patch.object(Config, 'SPOTIFY_CLIENT_SECRET', 'valid_client_secret')
    @patch.object(Config, 'SPOTIFY_SHOW_ID', 'valid_show_id')
    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    @patch('requests.post')
    def test_generate_rss_item(self, mock_post):
        """Test RSS item generation."""
        # Mock authentication
        mock_post.return_value = Mock(
            json=lambda: {'access_token': 'token123'},
            raise_for_status=lambda: None
        )

        uploader = SpotifyUploader()

        rss_item = uploader.generate_rss_item(
            episode_number=1,
            title='Test Episode',
            description='Test Description',
            audio_url='https://example.com/audio.mp3',
            audio_file_size=10000000,
            duration_seconds=3600,
            pub_date=datetime(2024, 1, 1)
        )

        assert '<item>' in rss_item
        assert 'Test Episode' in rss_item
        assert 'Test Description' in rss_item
        assert 'https://example.com/audio.mp3' in rss_item
        assert '<itunes:episode>1</itunes:episode>' in rss_item

    @patch.object(Config, 'SPOTIFY_CLIENT_ID', 'valid_client_id')
    @patch.object(Config, 'SPOTIFY_CLIENT_SECRET', 'valid_client_secret')
    @patch.object(Config, 'SPOTIFY_SHOW_ID', 'valid_show_id')
    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    @patch('requests.post')
    def test_create_episode_metadata(self, mock_post):
        """Test episode metadata creation."""
        # Mock authentication
        mock_post.return_value = Mock(
            json=lambda: {'access_token': 'token123'},
            raise_for_status=lambda: None
        )

        uploader = SpotifyUploader()

        metadata = uploader.create_episode_metadata(
            episode_number=1,
            summary='Test summary',
            duration_seconds=3600
        )

        assert 'title' in metadata
        assert 'Episode 1' in metadata['title']
        assert metadata['description'] == 'Test summary'
        assert metadata['episode_number'] == 1
        assert metadata['duration_seconds'] == 3600


class TestCreateSpotifyEpisodeData:
    """Test cases for create_spotify_episode_data function."""

    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    @patch('pathlib.Path.exists')
    def test_create_episode_data(self, mock_exists):
        """Test episode data creation."""
        mock_exists.return_value = True

        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=10000000)

            data = create_spotify_episode_data(
                episode_number=1,
                episode_summary='Test summary',
                audio_url='https://example.com/audio.mp3',
                audio_file_path=__file__,
                duration_seconds=3600
            )

            assert data['episode_number'] == 1
            assert 'Episode 1' in data['title']
            assert data['description'] == 'Test summary'
            assert data['audio_url'] == 'https://example.com/audio.mp3'
            assert data['audio_file_size'] == 10000000
            assert data['duration_seconds'] == 3600

    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    @patch('pathlib.Path.exists')
    def test_create_episode_data_missing_file(self, mock_exists):
        """Test episode data with missing file."""
        mock_exists.return_value = False

        data = create_spotify_episode_data(
            episode_number=1,
            episode_summary='Test',
            audio_url='https://example.com/audio.mp3',
            audio_file_path='/nonexistent/file.mp3',
            duration_seconds=3600
        )

        assert data['audio_file_size'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
