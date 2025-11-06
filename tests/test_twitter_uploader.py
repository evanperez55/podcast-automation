"""Tests for Twitter uploader module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tweepy

from uploaders.twitter_uploader import TwitterUploader, create_twitter_caption
from config import Config


class TestTwitterUploader:
    """Test cases for TwitterUploader class."""

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    def test_init_with_valid_credentials(self, mock_client, mock_api):
        """Test initialization with valid credentials."""
        uploader = TwitterUploader()

        assert uploader.api_key == 'valid_key'
        assert uploader.api_secret == 'valid_secret'
        assert uploader.access_token == 'valid_token'
        assert uploader.access_secret == 'valid_token_secret'

    @patch.object(Config, 'TWITTER_API_KEY', None)
    @patch.object(Config, 'TWITTER_API_SECRET', None)
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', None)
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', None)
    def test_init_without_credentials(self):
        """Test initialization fails without credentials."""
        with pytest.raises(ValueError, match="Twitter API credentials not configured"):
            TwitterUploader()

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    def test_post_tweet_success(self, mock_client_class, mock_api_class):
        """Test successful tweet posting."""
        uploader = TwitterUploader()

        # Mock client response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {'id': '123456789'}
        mock_client.create_tweet.return_value = mock_response
        uploader.client = mock_client

        result = uploader.post_tweet(text='Test tweet')

        assert result is not None
        assert result['tweet_id'] == '123456789'
        assert result['status'] == 'success'

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    @patch('pathlib.Path.exists')
    def test_post_tweet_with_media(self, mock_exists, mock_client_class, mock_api_class):
        """Test tweet with media upload."""
        mock_exists.return_value = True
        uploader = TwitterUploader()

        # Mock media upload
        mock_api = Mock()
        mock_media = Mock()
        mock_media.media_id_string = 'media123'
        mock_api.media_upload.return_value = mock_media
        uploader.api_v1 = mock_api

        # Mock tweet posting
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {'id': '123456789'}
        mock_client.create_tweet.return_value = mock_response
        uploader.client = mock_client

        result = uploader.post_tweet(
            text='Test tweet',
            media_paths=[__file__]
        )

        assert result is not None
        assert result['media_count'] == 1

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    def test_post_thread_success(self, mock_client_class, mock_api_class):
        """Test successful thread posting."""
        uploader = TwitterUploader()

        # Mock client
        mock_client = Mock()

        def create_tweet_side_effect(*args, **kwargs):
            response = Mock()
            response.data = {'id': str(mock_client.create_tweet.call_count)}
            return response

        mock_client.create_tweet.side_effect = create_tweet_side_effect
        uploader.client = mock_client

        tweets = ['First tweet', 'Second tweet', 'Third tweet']
        result = uploader.post_thread(tweets)

        assert result is not None
        assert len(result) == 3
        assert mock_client.create_tweet.call_count == 3

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch.object(Config, 'PODCAST_NAME', 'Test Podcast')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    def test_post_episode_announcement(self, mock_client_class, mock_api_class):
        """Test episode announcement posting."""
        uploader = TwitterUploader()

        with patch.object(uploader, 'post_thread') as mock_post_thread:
            mock_post_thread.return_value = [{'tweet_id': '1'}, {'tweet_id': '2'}]

            result = uploader.post_episode_announcement(
                episode_number=25,
                episode_summary='Great episode!',
                youtube_url='https://youtube.com/watch?v=123',
                spotify_url='https://spotify.com/episode/123'
            )

            assert result is not None
            mock_post_thread.assert_called_once()

    @patch.object(Config, 'TWITTER_API_KEY', 'valid_key')
    @patch.object(Config, 'TWITTER_API_SECRET', 'valid_secret')
    @patch.object(Config, 'TWITTER_ACCESS_TOKEN', 'valid_token')
    @patch.object(Config, 'TWITTER_ACCESS_SECRET', 'valid_token_secret')
    @patch('uploaders.twitter_uploader.tweepy.API')
    @patch('uploaders.twitter_uploader.tweepy.Client')
    def test_get_user_info_success(self, mock_client_class, mock_api_class):
        """Test successful user info retrieval."""
        uploader = TwitterUploader()

        # Mock user data
        mock_user = Mock()
        mock_user.data = Mock(
            id='123',
            username='testuser',
            name='Test User',
            description='Bio',
            public_metrics={
                'followers_count': 1000,
                'following_count': 500,
                'tweet_count': 5000
            }
        )

        mock_client = Mock()
        mock_client.get_me.return_value = mock_user
        uploader.client = mock_client

        info = uploader.get_user_info()

        assert info is not None
        assert info['username'] == 'testuser'
        assert info['followers'] == 1000


class TestCreateTwitterCaption:
    """Test cases for create_twitter_caption function."""

    def test_create_caption_basic(self):
        """Test basic caption creation."""
        caption = create_twitter_caption(
            clip_title='Funny Moment',
            social_caption='This was hilarious!',
            hashtags=None
        )

        assert 'Funny Moment' in caption
        assert 'This was hilarious!' in caption
        assert '#podcast' in caption

    def test_create_caption_custom_hashtags(self):
        """Test caption with custom hashtags."""
        caption = create_twitter_caption(
            clip_title='Test',
            social_caption='Caption',
            hashtags=['custom']
        )

        assert '#custom' in caption

    def test_caption_length_limit(self):
        """Test caption respects Twitter length limit."""
        long_caption = 'A' * 300

        caption = create_twitter_caption(
            clip_title='Test',
            social_caption=long_caption,
            hashtags=None
        )

        assert len(caption) <= 280

    def test_caption_trimming(self):
        """Test caption is trimmed when too long."""
        long_text = 'A' * 300

        caption = create_twitter_caption(
            clip_title=long_text,
            social_caption='',
            hashtags=['tag1', 'tag2', 'tag3']
        )

        assert len(caption) <= 280
        assert caption.endswith('...')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
