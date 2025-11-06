"""Tests for TikTok uploader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import requests

from uploaders.tiktok_uploader import TikTokUploader, create_tiktok_caption
from config import Config


class TestTikTokUploader:
    """Test cases for TikTokUploader class."""

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        uploader = TikTokUploader()

        assert uploader.client_key == 'valid_key'
        assert uploader.client_secret == 'valid_secret'
        assert uploader.access_token == 'valid_token'

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'your_tiktok_client_key_here')
    def test_init_without_client_key(self):
        """Test initialization fails without client key."""
        with pytest.raises(ValueError, match="TikTok client key not configured"):
            TikTokUploader()

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'your_tiktok_access_token_here')
    def test_init_without_access_token(self):
        """Test initialization fails without access token."""
        with pytest.raises(ValueError, match="TikTok access token not configured"):
            TikTokUploader()

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    def test_upload_video_file_not_found(self):
        """Test upload_video with non-existent file."""
        uploader = TikTokUploader()

        result = uploader.upload_video(
            video_path='/nonexistent/video.mp4',
            title='Test Video'
        )

        assert result is None

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    @patch('pathlib.Path.exists')
    @patch('requests.post')
    @patch('requests.put')
    def test_initialize_upload_success(self, mock_put, mock_post, mock_exists):
        """Test successful upload initialization."""
        mock_exists.return_value = True
        uploader = TikTokUploader()

        # Mock stat for file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1024000)

            # Mock API response
            mock_post.return_value = Mock(
                json=lambda: {
                    'data': {
                        'upload_url': 'https://upload.tiktok.com/123',
                        'publish_id': 'pub123'
                    }
                },
                raise_for_status=lambda: None
            )

            upload_url, publish_id = uploader._initialize_upload(Path(__file__))

            assert upload_url == 'https://upload.tiktok.com/123'
            assert publish_id == 'pub123'

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', create=True)
    @patch('requests.put')
    def test_upload_video_file_success(self, mock_put, mock_open, mock_exists):
        """Test successful video file upload."""
        mock_exists.return_value = True
        uploader = TikTokUploader()

        # Mock file read
        mock_open.return_value.__enter__.return_value.read.return_value = b'video_data'

        # Mock successful upload
        mock_put.return_value = Mock(raise_for_status=lambda: None)

        result = uploader._upload_video_file(
            'https://upload.tiktok.com/123',
            Path(__file__)
        )

        assert result is True

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    @patch('requests.post')
    @patch('time.sleep', return_value=None)
    def test_publish_video_success(self, mock_sleep, mock_post):
        """Test successful video publishing."""
        uploader = TikTokUploader()

        # Mock publish status check
        mock_post.return_value = Mock(
            json=lambda: {
                'data': {
                    'status': 'PUBLISH_COMPLETE',
                    'share_url': 'https://tiktok.com/@user/video/123',
                    'video_id': 'vid123'
                }
            },
            raise_for_status=lambda: None
        )

        result = uploader._publish_video(
            publish_id='pub123',
            title='Test',
            description=None,
            privacy_level='PUBLIC_TO_EVERYONE',
            disable_duet=False,
            disable_stitch=False,
            disable_comment=False,
            video_cover_timestamp_ms=1000
        )

        assert result is not None
        assert result['status'] == 'PUBLISH_COMPLETE'
        assert result['video_id'] == 'vid123'

    @patch.object(Config, 'TIKTOK_CLIENT_KEY', 'valid_key')
    @patch.object(Config, 'TIKTOK_CLIENT_SECRET', 'valid_secret')
    @patch.object(Config, 'TIKTOK_ACCESS_TOKEN', 'valid_token')
    @patch('requests.post')
    def test_get_user_info_success(self, mock_post):
        """Test successful user info retrieval."""
        uploader = TikTokUploader()

        mock_post.return_value = Mock(
            json=lambda: {
                'data': {
                    'user': {
                        'display_name': 'Test User',
                        'follower_count': 1000
                    }
                }
            },
            raise_for_status=lambda: None
        )

        info = uploader.get_user_info()

        assert info is not None
        assert info['display_name'] == 'Test User'
        assert info['follower_count'] == 1000


class TestCreateTikTokCaption:
    """Test cases for create_tiktok_caption function."""

    def test_create_caption_basic(self):
        """Test basic caption creation."""
        caption = create_tiktok_caption(
            clip_title='Funny Moment',
            social_caption='This was hilarious!',
            hashtags=None
        )

        assert 'Funny Moment' in caption
        assert 'This was hilarious!' in caption
        assert '#podcast' in caption
        assert '#fyp' in caption

    def test_create_caption_custom_hashtags(self):
        """Test caption with custom hashtags."""
        caption = create_tiktok_caption(
            clip_title='Test',
            social_caption='Caption',
            hashtags=['custom', 'tags']
        )

        assert '#custom' in caption
        assert '#tags' in caption

    def test_caption_length_limit(self):
        """Test caption respects TikTok length limit."""
        long_title = 'A' * 200

        caption = create_tiktok_caption(
            clip_title=long_title,
            social_caption='Caption',
            hashtags=None
        )

        assert len(caption) <= 150


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
