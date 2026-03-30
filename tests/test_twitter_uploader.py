"""Tests for Twitter uploader module."""

import pytest
from unittest.mock import Mock, patch

from uploaders.twitter_uploader import TwitterUploader, create_twitter_caption
from config import Config


class TestTwitterUploader:
    """Test cases for TwitterUploader class."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_init_with_valid_credentials(self, mock_client, mock_api):
        """Test initialization with valid credentials."""
        uploader = TwitterUploader()

        assert uploader.api_key == "valid_key"
        assert uploader.api_secret == "valid_secret"
        assert uploader.access_token == "valid_token"
        assert uploader.access_secret == "valid_token_secret"

    @patch.object(Config, "TWITTER_API_KEY", None)
    @patch.object(Config, "TWITTER_API_SECRET", None)
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", None)
    @patch.object(Config, "TWITTER_ACCESS_SECRET", None)
    def test_init_without_credentials(self):
        """Test initialization fails without credentials."""
        with pytest.raises(ValueError, match="Twitter API credentials not configured"):
            TwitterUploader()

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_tweet_success(self, mock_client_class, mock_api_class):
        """Test successful tweet posting."""
        uploader = TwitterUploader()

        # Mock client response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {"id": "123456789"}
        mock_client.create_tweet.return_value = mock_response
        uploader.client = mock_client

        result = uploader.post_tweet(text="Test tweet")

        assert result is not None
        assert result["tweet_id"] == "123456789"
        assert result["status"] == "success"

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    @patch("pathlib.Path.exists")
    def test_post_tweet_with_media(
        self, mock_exists, mock_client_class, mock_api_class
    ):
        """Test tweet with media upload."""
        mock_exists.return_value = True
        uploader = TwitterUploader()

        # Mock media upload
        mock_api = Mock()
        mock_media = Mock()
        mock_media.media_id_string = "media123"
        mock_api.media_upload.return_value = mock_media
        uploader.api_v1 = mock_api

        # Mock tweet posting
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {"id": "123456789"}
        mock_client.create_tweet.return_value = mock_response
        uploader.client = mock_client

        result = uploader.post_tweet(text="Test tweet", media_paths=[__file__])

        assert result is not None
        assert result["media_count"] == 1

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_thread_success(self, mock_client_class, mock_api_class):
        """Test successful thread posting."""
        uploader = TwitterUploader()

        # Mock client
        mock_client = Mock()

        def create_tweet_side_effect(*args, **kwargs):
            response = Mock()
            response.data = {"id": str(mock_client.create_tweet.call_count)}
            return response

        mock_client.create_tweet.side_effect = create_tweet_side_effect
        uploader.client = mock_client

        tweets = ["First tweet", "Second tweet", "Third tweet"]
        result = uploader.post_thread(tweets)

        assert result is not None
        assert len(result) == 3
        assert mock_client.create_tweet.call_count == 3

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_episode_announcement(self, mock_client_class, mock_api_class):
        """Test episode announcement posting."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}, {"tweet_id": "2"}]

            result = uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                youtube_url="https://youtube.com/watch?v=123",
                spotify_url="https://spotify.com/episode/123",
            )

            assert result is not None
            mock_post_thread.assert_called_once()

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_get_user_info_success(self, mock_client_class, mock_api_class):
        """Test successful user info retrieval."""
        uploader = TwitterUploader()

        # Mock user data
        mock_user = Mock()
        mock_user.data = Mock(
            id="123",
            username="testuser",
            name="Test User",
            description="Bio",
            public_metrics={
                "followers_count": 1000,
                "following_count": 500,
                "tweet_count": 5000,
            },
        )

        mock_client = Mock()
        mock_client.get_me.return_value = mock_user
        uploader.client = mock_client

        info = uploader.get_user_info()

        assert info is not None
        assert info["username"] == "testuser"
        assert info["followers"] == 1000


class TestCreateTwitterCaption:
    """Test cases for create_twitter_caption function."""

    def test_create_caption_basic(self):
        """Test basic caption creation."""
        caption = create_twitter_caption(
            clip_title="Funny Moment",
            social_caption="This was hilarious!",
            hashtags=None,
        )

        assert "Funny Moment" in caption
        assert "This was hilarious!" in caption
        assert "#podcast" in caption

    def test_create_caption_custom_hashtags(self):
        """Test caption with custom hashtags."""
        caption = create_twitter_caption(
            clip_title="Test", social_caption="Caption", hashtags=["custom"]
        )

        assert "#custom" in caption

    def test_caption_length_limit(self):
        """Test caption respects Twitter length limit."""
        long_caption = "A" * 300

        caption = create_twitter_caption(
            clip_title="Test", social_caption=long_caption, hashtags=None
        )

        assert len(caption) <= 280

    def test_caption_trimming(self):
        """Test caption is trimmed when too long."""
        long_text = "A" * 300

        caption = create_twitter_caption(
            clip_title=long_text, social_caption="", hashtags=["tag1", "tag2", "tag3"]
        )

        assert len(caption) <= 280
        assert caption.endswith("...")


class TestPostEpisodeAnnouncementAICaption:
    """Test cases for AI-generated twitter_caption in post_episode_announcement."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_ai_caption_used_when_provided(self, mock_client_class, mock_api_class):
        """Test that AI caption replaces hardcoded template when provided."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                youtube_url="https://youtube.com/watch?v=123",
                twitter_caption="This episode is fire",
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            # AI caption should be the first tweet, not the hardcoded template
            assert "This episode is fire" in tweets[0]
            assert "New Episode Alert" not in tweets[0]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_fallback_template_when_no_caption(self, mock_client_class, mock_api_class):
        """Test that hardcoded template is used when no AI caption provided."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert "New Episode Alert" in tweets[0]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_ai_caption_with_youtube_url(self, mock_client_class, mock_api_class):
        """Test that YouTube URL is appended to AI caption if space allows."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            short_caption = "Short tweet"
            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Summary",
                youtube_url="https://youtube.com/watch?v=123",
                twitter_caption=short_caption,
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert "https://youtube.com/watch?v=123" in tweets[0]


class TestHashtagInjection:
    """Test cases for hashtag injection in post_episode_announcement."""

    def _make_uploader(self):
        """Helper: create uploader with all credentials mocked."""
        with (
            patch.object(Config, "TWITTER_API_KEY", "valid_key"),
            patch.object(Config, "TWITTER_API_SECRET", "valid_secret"),
            patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token"),
            patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret"),
            patch("uploaders.twitter_uploader.tweepy.API"),
            patch("uploaders.twitter_uploader.tweepy.Client"),
        ):
            return TwitterUploader()

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_hashtag_injection_appended_to_tweet(
        self, mock_client_class, mock_api_class
    ):
        """Tweet text ends with '\\n\\n#comedy #podcast' when hashtags are provided."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                twitter_caption="Short caption",
                hashtags=["comedy", "podcast"],
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert tweets[0].endswith("\n\n#comedy #podcast")

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_hashtag_injection_limited_to_two(self, mock_client_class, mock_api_class):
        """Only first 2 hashtags appear in tweet when more are provided."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                twitter_caption="Short caption",
                hashtags=["a", "b", "c", "d"],
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert "#a" in tweets[0]
            assert "#b" in tweets[0]
            assert "#c" not in tweets[0]
            assert "#d" not in tweets[0]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_hashtag_injection_none_skipped(self, mock_client_class, mock_api_class):
        """No hashtag line added when hashtags=None."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                twitter_caption="Short caption",
                hashtags=None,
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            # Should not contain a hashtag line
            assert "\n\n#" not in tweets[0]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_hashtag_injection_empty_list_skipped(
        self, mock_client_class, mock_api_class
    ):
        """No hashtag line added when hashtags=[]."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Great episode!",
                twitter_caption="Short caption",
                hashtags=[],
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert "\n\n#" not in tweets[0]


class TestPostTweetEdgeCases:
    """Test edge cases in post_tweet method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_tweet_unicode_encode_error_in_logging(
        self, mock_client_class, mock_api_class
    ):
        """UnicodeEncodeError in text logging falls back to ascii-replaced text."""
        import uploaders.twitter_uploader as mod

        uploader = TwitterUploader()

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {"id": "999"}
        mock_client.create_tweet.return_value = mock_response
        uploader.client = mock_client

        original_info = mod.logger.info
        call_count = [0]

        def info_side_effect(msg, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise UnicodeEncodeError("ascii", "", 0, 1, "mock")
            return original_info(msg, *args, **kwargs)

        with patch.object(mod.logger, "info", side_effect=info_side_effect):
            result = uploader.post_tweet(text="Test \u2603 tweet")

        assert result is not None
        assert result["tweet_id"] == "999"

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_tweet_media_upload_returns_empty(
        self, mock_client_class, mock_api_class
    ):
        """When _upload_media returns empty list, post_tweet returns None."""
        uploader = TwitterUploader()

        with patch.object(uploader, "_upload_media", return_value=[]):
            result = uploader.post_tweet(
                text="Test tweet", media_paths=["/fake/path.jpg"]
            )

        assert result is None

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_tweet_tweepy_exception_returns_none(
        self, mock_client_class, mock_api_class
    ):
        """TweepyException in create_tweet returns None."""
        import tweepy

        uploader = TwitterUploader()

        mock_client = Mock()
        mock_client.create_tweet.side_effect = tweepy.TweepyException("Rate limited")
        uploader.client = mock_client

        result = uploader.post_tweet(text="Test tweet")

        assert result is None


class TestUploadMedia:
    """Test edge cases in _upload_media method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_upload_media_file_not_found(self, mock_client_class, mock_api_class):
        """Non-existent media file is skipped with warning."""
        uploader = TwitterUploader()

        result = uploader._upload_media(["/nonexistent/file.jpg"])

        assert result == []

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_upload_media_video_category(
        self, mock_client_class, mock_api_class, tmp_path
    ):
        """Video files use tweet_video media category."""
        uploader = TwitterUploader()

        video_file = tmp_path / "clip.mp4"
        video_file.write_text("fake video")

        mock_api = Mock()
        mock_media = Mock()
        mock_media.media_id_string = "vid_123"
        mock_api.media_upload.return_value = mock_media
        uploader.api_v1 = mock_api

        result = uploader._upload_media([str(video_file)])

        assert result == ["vid_123"]
        mock_api.media_upload.assert_called_once_with(
            filename=str(video_file), media_category="tweet_video"
        )

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_upload_media_tweepy_exception(
        self, mock_client_class, mock_api_class, tmp_path
    ):
        """TweepyException during upload is caught and file is skipped."""
        import tweepy

        uploader = TwitterUploader()

        img_file = tmp_path / "photo.jpg"
        img_file.write_text("fake image")

        mock_api = Mock()
        mock_api.media_upload.side_effect = tweepy.TweepyException("Upload failed")
        uploader.api_v1 = mock_api

        result = uploader._upload_media([str(img_file)])

        assert result == []


class TestPostThreadEdgeCases:
    """Test edge cases in post_thread method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_thread_with_media_paths(self, mock_client_class, mock_api_class):
        """Thread with media_paths passes media to individual tweets."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_tweet") as mock_post:
            mock_post.return_value = {"tweet_id": "1"}

            result = uploader.post_thread(
                ["Tweet 1", "Tweet 2"],
                media_paths=[["/img1.jpg"], None],
            )

            assert result is not None
            assert len(result) == 2
            first_call = mock_post.call_args_list[0]
            assert first_call.kwargs["media_paths"] == ["/img1.jpg"]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_thread_failure_returns_none(self, mock_client_class, mock_api_class):
        """Thread returns None when a tweet in the thread fails."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_tweet") as mock_post:
            mock_post.return_value = None

            result = uploader.post_thread(["Tweet 1", "Tweet 2"])

            assert result is None


class TestPostEpisodeAnnouncementEdgeCases:
    """Test edge cases in post_episode_announcement."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_caption_trimmed_with_url(self, mock_client_class, mock_api_class):
        """Long AI caption is trimmed to fit YouTube URL within 280 chars."""
        uploader = TwitterUploader()

        long_caption = "A" * 270

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Summary",
                youtube_url="https://youtube.com/watch?v=123",
                twitter_caption=long_caption,
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert "https://youtube.com/watch?v=123" in tweets[0]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_hashtag_truncation_when_too_long(self, mock_client_class, mock_api_class):
        """Hashtags truncate main tweet text when combined length exceeds 280."""
        uploader = TwitterUploader()

        long_caption = "B" * 270

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [{"tweet_id": "1"}]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Summary",
                twitter_caption=long_caption,
                hashtags=["comedy", "podcast"],
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert tweets[0].endswith("\n\n#comedy #podcast")
            assert len(tweets[0]) <= 280

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_clip_youtube_urls_in_thread(self, mock_client_class, mock_api_class):
        """Clip YouTube URLs are added as thread tweets."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_thread") as mock_post_thread:
            mock_post_thread.return_value = [
                {"tweet_id": "1"},
                {"tweet_id": "2"},
                {"tweet_id": "3"},
            ]

            uploader.post_episode_announcement(
                episode_number=25,
                episode_summary="Summary",
                twitter_caption="Main tweet",
                clip_youtube_urls=[
                    {"title": "Best Moment", "url": "https://youtube.com/shorts/abc"},
                    {"title": "Funny Part", "url": "https://youtube.com/shorts/def"},
                ],
            )

            call_args = mock_post_thread.call_args
            tweets = call_args[0][0]
            assert len(tweets) == 3
            assert "Best Moment" in tweets[1]
            assert "https://youtube.com/shorts/abc" in tweets[1]
            assert "Funny Part" in tweets[2]


class TestPostClip:
    """Test cases for post_clip method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_clip_with_youtube_url(self, mock_client_class, mock_api_class):
        """Post clip with YouTube URL includes URL in tweet and no media."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_tweet") as mock_post:
            mock_post.return_value = {"tweet_id": "42", "status": "success"}

            result = uploader.post_clip(
                caption="Hilarious moment",
                episode_number=10,
                youtube_url="https://youtube.com/shorts/xyz",
            )

            assert result is not None
            call_kwargs = mock_post.call_args.kwargs
            assert "https://youtube.com/shorts/xyz" in call_kwargs["text"]
            assert "Episode 10" in call_kwargs["text"]
            assert "Test Podcast" in call_kwargs["text"]
            assert call_kwargs["media_paths"] is None

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_clip_with_video_path_no_youtube(
        self, mock_client_class, mock_api_class
    ):
        """Post clip with video_path but no youtube_url uploads video as media."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_tweet") as mock_post:
            mock_post.return_value = {"tweet_id": "43", "status": "success"}

            result = uploader.post_clip(
                caption="Great clip",
                episode_number=5,
                video_path="/path/to/clip.mp4",
            )

            assert result is not None
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["media_paths"] == ["/path/to/clip.mp4"]

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_post_clip_no_url_no_video(self, mock_client_class, mock_api_class):
        """Post clip with neither youtube_url nor video_path sends text only."""
        uploader = TwitterUploader()

        with patch.object(uploader, "post_tweet") as mock_post:
            mock_post.return_value = {"tweet_id": "44", "status": "success"}

            result = uploader.post_clip(
                caption="Just text",
                episode_number=3,
            )

            assert result is not None
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["media_paths"] is None


class TestGetUserInfoEdgeCases:
    """Test edge cases in get_user_info method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_get_user_info_no_data(self, mock_client_class, mock_api_class):
        """Returns None when get_me response has no data."""
        uploader = TwitterUploader()

        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = None
        mock_client.get_me.return_value = mock_response
        uploader.client = mock_client

        result = uploader.get_user_info()

        assert result is None

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_get_user_info_tweepy_exception(self, mock_client_class, mock_api_class):
        """TweepyException in get_me returns None."""
        import tweepy

        uploader = TwitterUploader()

        mock_client = Mock()
        mock_client.get_me.side_effect = tweepy.TweepyException("Auth failed")
        uploader.client = mock_client

        result = uploader.get_user_info()

        assert result is None


class TestDeleteTweet:
    """Test cases for delete_tweet method."""

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_delete_tweet_success(self, mock_client_class, mock_api_class):
        """Successful delete returns True."""
        uploader = TwitterUploader()

        mock_client = Mock()
        uploader.client = mock_client

        result = uploader.delete_tweet("12345")

        assert result is True
        mock_client.delete_tweet.assert_called_once_with("12345")

    @patch.object(Config, "TWITTER_API_KEY", "valid_key")
    @patch.object(Config, "TWITTER_API_SECRET", "valid_secret")
    @patch.object(Config, "TWITTER_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "TWITTER_ACCESS_SECRET", "valid_token_secret")
    @patch("uploaders.twitter_uploader.tweepy.API")
    @patch("uploaders.twitter_uploader.tweepy.Client")
    def test_delete_tweet_tweepy_exception(self, mock_client_class, mock_api_class):
        """TweepyException in delete returns False."""
        import tweepy

        uploader = TwitterUploader()

        mock_client = Mock()
        mock_client.delete_tweet.side_effect = tweepy.TweepyException("Not found")
        uploader.client = mock_client

        result = uploader.delete_tweet("99999")

        assert result is False


class TestCreateTwitterCaptionEdgeCases:
    """Test edge cases for create_twitter_caption function."""

    def test_caption_without_hashtags_when_only_caption_fits(self):
        """Returns caption without hashtags when caption alone fits but with hashtags does not."""
        clip_title = "Title"
        social_caption = "X" * 260
        caption = create_twitter_caption(
            clip_title=clip_title,
            social_caption=social_caption,
            hashtags=["verylonghashtag", "anotherlongone"],
        )

        assert "#" not in caption
        assert len(caption) <= 280


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
