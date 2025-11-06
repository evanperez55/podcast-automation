"""Tests for Instagram uploader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from uploaders.instagram_uploader import InstagramUploader, create_instagram_caption
from config import Config


class TestInstagramUploader:
    """Test cases for InstagramUploader class."""

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        uploader = InstagramUploader()

        assert uploader.access_token == 'valid_token'
        assert uploader.account_id == 'valid_account_id'

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'your_instagram_access_token_here')
    def test_init_without_access_token(self):
        """Test initialization fails without access token."""
        with pytest.raises(ValueError, match="Instagram access token not configured"):
            InstagramUploader()

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'your_instagram_account_id_here')
    def test_init_without_account_id(self):
        """Test initialization fails without account ID."""
        with pytest.raises(ValueError, match="Instagram account ID not configured"):
            InstagramUploader()

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.post')
    @patch('requests.get')
    def test_upload_reel_success(self, mock_get, mock_post):
        """Test successful Reel upload."""
        uploader = InstagramUploader()

        # Mock container creation
        mock_post.side_effect = [
            Mock(json=lambda: {'id': 'container123'}, status_code=200, raise_for_status=lambda: None),
            Mock(json=lambda: {'id': 'reel123'}, status_code=200, raise_for_status=lambda: None)
        ]

        # Mock status check - FINISHED on first check
        mock_get.side_effect = [
            Mock(json=lambda: {'status_code': 'FINISHED'}, status_code=200, raise_for_status=lambda: None),
            Mock(json=lambda: {'permalink': 'https://instagram.com/reel/123'}, status_code=200, raise_for_status=lambda: None)
        ]

        result = uploader.upload_reel(
            video_url='https://example.com/video.mp4',
            caption='Test caption'
        )

        assert result is not None
        assert result['id'] == 'reel123'
        assert result['status'] == 'success'

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.post')
    def test_create_reel_container_failure(self, mock_post):
        """Test Reel container creation failure."""
        uploader = InstagramUploader()

        # Mock failed container creation
        mock_post.side_effect = requests.exceptions.RequestException("API Error")

        result = uploader._create_reel_container(
            video_url='https://example.com/video.mp4',
            caption='Test',
            share_to_feed=True,
            cover_url=None
        )

        assert result is None

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.get')
    def test_wait_for_container_ready_success(self, mock_get):
        """Test waiting for container processing success."""
        uploader = InstagramUploader()

        # Mock status progression
        mock_get.side_effect = [
            Mock(json=lambda: {'status_code': 'IN_PROGRESS'}, raise_for_status=lambda: None),
            Mock(json=lambda: {'status_code': 'FINISHED'}, raise_for_status=lambda: None)
        ]

        result = uploader._wait_for_container_ready('container123', max_wait=60, check_interval=1)

        assert result is True

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.get')
    def test_wait_for_container_ready_error(self, mock_get):
        """Test waiting for container with ERROR status."""
        uploader = InstagramUploader()

        mock_get.return_value = Mock(
            json=lambda: {'status_code': 'ERROR', 'status': 'Processing failed'},
            raise_for_status=lambda: None
        )

        result = uploader._wait_for_container_ready('container123', max_wait=10, check_interval=1)

        assert result is False

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.get')
    def test_wait_for_container_ready_timeout(self, mock_get):
        """Test timeout while waiting for container."""
        uploader = InstagramUploader()

        # Always return IN_PROGRESS
        mock_get.return_value = Mock(
            json=lambda: {'status_code': 'IN_PROGRESS'},
            raise_for_status=lambda: None
        )

        result = uploader._wait_for_container_ready('container123', max_wait=2, check_interval=1)

        assert result is False

    @patch.object(Config, 'INSTAGRAM_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'INSTAGRAM_ACCOUNT_ID', 'valid_account_id')
    @patch('requests.get')
    def test_get_account_info_success(self, mock_get):
        """Test successful account info retrieval."""
        uploader = InstagramUploader()

        mock_get.return_value = Mock(
            json=lambda: {
                'id': '123',
                'username': 'testuser',
                'followers_count': 1000
            },
            raise_for_status=lambda: None
        )

        info = uploader.get_account_info()

        assert info is not None
        assert info['username'] == 'testuser'
        assert info['followers_count'] == 1000


class TestCreateInstagramCaption:
    """Test cases for create_instagram_caption function."""

    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    def test_create_caption_basic(self):
        """Test basic caption creation."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title='Funny Moment',
            social_caption='This was hilarious!',
            hashtags=None
        )

        assert 'Funny Moment' in caption
        assert 'This was hilarious!' in caption
        assert 'Episode 25' in caption
        assert '#podcast' in caption

    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    def test_create_caption_custom_hashtags(self):
        """Test caption with custom hashtags."""
        caption = create_instagram_caption(
            episode_number=1,
            clip_title='Test',
            social_caption='Caption',
            hashtags=['custom', 'tags']
        )

        assert '#custom' in caption
        assert '#tags' in caption

    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    def test_caption_length_limit(self):
        """Test caption respects Instagram length limit."""
        long_caption = 'A' * 3000

        caption = create_instagram_caption(
            episode_number=1,
            clip_title='Test',
            social_caption=long_caption,
            hashtags=None
        )

        assert len(caption) <= 2200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
