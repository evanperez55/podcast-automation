"""Tests for Instagram uploader module."""

import pytest
from unittest.mock import Mock, patch
import requests

from uploaders.instagram_uploader import InstagramUploader, create_instagram_caption
from config import Config


class TestInstagramUploader:
    """Test cases for InstagramUploader class."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        uploader = InstagramUploader()

        assert uploader.access_token == "valid_token"
        assert uploader.account_id == "valid_account_id"

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "your_instagram_access_token_here")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_init_without_access_token(self):
        """Test initialization sets .functional = False without access token."""
        uploader = InstagramUploader()
        assert uploader.functional is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "your_instagram_account_id_here")
    def test_init_without_account_id(self):
        """Test initialization sets .functional = False without account ID."""
        uploader = InstagramUploader()
        assert uploader.functional is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.post")
    @patch("requests.get")
    def test_upload_reel_success(self, mock_get, mock_post):
        """Test successful Reel upload."""
        uploader = InstagramUploader()

        # Mock container creation
        mock_post.side_effect = [
            Mock(
                json=lambda: {"id": "container123"},
                status_code=200,
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {"id": "reel123"},
                status_code=200,
                raise_for_status=lambda: None,
            ),
        ]

        # Mock status check - FINISHED on first check
        mock_get.side_effect = [
            Mock(
                json=lambda: {"status_code": "FINISHED"},
                status_code=200,
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {"permalink": "https://instagram.com/reel/123"},
                status_code=200,
                raise_for_status=lambda: None,
            ),
        ]

        result = uploader.upload_reel(
            video_url="https://example.com/video.mp4", caption="Test caption"
        )

        assert result is not None
        assert result["id"] == "reel123"
        assert result["status"] == "success"

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.post")
    def test_create_reel_container_failure(self, mock_post):
        """Test Reel container creation failure."""
        uploader = InstagramUploader()

        # Mock failed container creation (HTTPError from raise_for_status on 4xx/5xx)
        mock_response = Mock()
        mock_response.text = "Bad Request"
        mock_post.side_effect = requests.exceptions.HTTPError(
            "API Error", response=mock_response
        )

        result = uploader._create_reel_container(
            video_url="https://example.com/video.mp4",
            caption="Test",
            share_to_feed=True,
            cover_url=None,
        )

        assert result is None

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_wait_for_container_ready_success(self, mock_get):
        """Test waiting for container processing success."""
        uploader = InstagramUploader()

        # Mock status progression
        mock_get.side_effect = [
            Mock(
                json=lambda: {"status_code": "IN_PROGRESS"},
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {"status_code": "FINISHED"}, raise_for_status=lambda: None
            ),
        ]

        result = uploader._wait_for_container_ready(
            "container123", max_wait=60, check_interval=1
        )

        assert result is True

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_wait_for_container_ready_error(self, mock_get):
        """Test waiting for container with ERROR status."""
        uploader = InstagramUploader()

        mock_get.return_value = Mock(
            json=lambda: {"status_code": "ERROR", "status": "Processing failed"},
            raise_for_status=lambda: None,
        )

        result = uploader._wait_for_container_ready(
            "container123", max_wait=10, check_interval=1
        )

        assert result is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_wait_for_container_ready_timeout(self, mock_get):
        """Test timeout while waiting for container."""
        uploader = InstagramUploader()

        # Always return IN_PROGRESS
        mock_get.return_value = Mock(
            json=lambda: {"status_code": "IN_PROGRESS"}, raise_for_status=lambda: None
        )

        result = uploader._wait_for_container_ready(
            "container123", max_wait=2, check_interval=1
        )

        assert result is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_get_account_info_success(self, mock_get):
        """Test successful account info retrieval."""
        uploader = InstagramUploader()

        mock_get.return_value = Mock(
            json=lambda: {"id": "123", "username": "testuser", "followers_count": 1000},
            raise_for_status=lambda: None,
        )

        info = uploader.get_account_info()

        assert info is not None
        assert info["username"] == "testuser"
        assert info["followers_count"] == 1000


class TestCreateInstagramCaption:
    """Test cases for create_instagram_caption function."""

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_create_caption_basic(self):
        """Test basic caption creation."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title="Funny Moment",
            social_caption="This was hilarious!",
            hashtags=None,
        )

        assert "Funny Moment" in caption
        assert "This was hilarious!" in caption
        assert "Episode 25" in caption
        assert "#podcast" in caption

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_create_caption_custom_hashtags(self):
        """Test caption with custom hashtags."""
        caption = create_instagram_caption(
            episode_number=1,
            clip_title="Test",
            social_caption="Caption",
            hashtags=["custom", "tags"],
        )

        assert "#custom" in caption
        assert "#tags" in caption

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_caption_length_limit(self):
        """Test caption respects Instagram length limit."""
        long_caption = "A" * 3000

        caption = create_instagram_caption(
            episode_number=1,
            clip_title="Test",
            social_caption=long_caption,
            hashtags=None,
        )

        assert len(caption) <= 2200


class TestCreateInstagramCaptionNewFields:
    """Test cases for hook_caption and clip_hashtags in create_instagram_caption."""

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_hook_caption_prepended(self):
        """Test that hook_caption is prepended to caption."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title="Funny Moment",
            social_caption="This was hilarious!",
            hook_caption="Wait for it...",
        )
        assert caption.startswith("Wait for it...")
        assert "Funny Moment" in caption

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_no_hook_caption(self):
        """Test caption without hook_caption starts with clip_title."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title="Funny Moment",
            social_caption="This was hilarious!",
        )
        assert caption.startswith("Funny Moment")

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_clip_hashtags_used_when_no_explicit(self):
        """Test that clip_hashtags are used when no explicit hashtags provided."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title="Test",
            social_caption="Caption",
            clip_hashtags=["ai", "funny", "viral"],
        )
        assert "#ai" in caption
        assert "#funny" in caption
        assert "#viral" in caption
        # Should NOT have default hashtags
        assert "#podcastrecommendations" not in caption

    @patch.object(Config, "PODCAST_NAME", "Test Podcast")
    def test_explicit_hashtags_override_clip_hashtags(self):
        """Test that explicit hashtags take priority over clip_hashtags."""
        caption = create_instagram_caption(
            episode_number=25,
            clip_title="Test",
            social_caption="Caption",
            hashtags=["explicit"],
            clip_hashtags=["clip_tag"],
        )
        assert "#explicit" in caption
        assert "#clip_tag" not in caption


class TestInstagramFunctionalFlag:
    """Test cases for .functional flag on InstagramUploader."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", None)
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_instagram_functional_false_when_no_token(self):
        """InstagramUploader sets .functional = False when token is None — no raise."""
        uploader = InstagramUploader()
        assert uploader.functional is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "your_instagram_access_token_here")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_instagram_functional_false_when_placeholder(self):
        """InstagramUploader sets .functional = False when token is placeholder."""
        uploader = InstagramUploader()
        assert uploader.functional is False

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "real_token_abc123")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "real_account_id_456")
    def test_instagram_functional_true_when_configured(self):
        """InstagramUploader sets .functional = True when real creds are set."""
        uploader = InstagramUploader()
        assert uploader.functional is True


class TestUploadReelNotFunctional:
    """Tests for upload_reel when not functional."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", None)
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_upload_reel_returns_none_when_not_functional(self):
        """upload_reel returns None when uploader is not functional."""
        uploader = InstagramUploader()
        result = uploader.upload_reel(
            video_url="https://example.com/video.mp4", caption="Test"
        )
        assert result is None


class TestUploadReelContainerFailure:
    """Tests for upload_reel container/processing failures."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_upload_reel_returns_none_when_container_creation_fails(self):
        """upload_reel returns None when container creation fails."""
        uploader = InstagramUploader()

        with patch.object(uploader, "_create_reel_container", return_value=None):
            result = uploader.upload_reel(
                video_url="https://example.com/video.mp4", caption="Test"
            )
        assert result is None

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_upload_reel_returns_none_when_processing_fails(self):
        """upload_reel returns None when video processing fails."""
        uploader = InstagramUploader()

        with patch.object(
            uploader, "_create_reel_container", return_value="container123"
        ):
            with patch.object(
                uploader, "_wait_for_container_ready", return_value=False
            ):
                result = uploader.upload_reel(
                    video_url="https://example.com/video.mp4", caption="Test"
                )
        assert result is None


class TestCreateReelContainerCoverUrl:
    """Tests for cover_url in _create_reel_container."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.post")
    def test_cover_url_added_to_params(self, mock_post):
        """cover_url is included in container creation params when provided."""
        uploader = InstagramUploader()

        mock_post.return_value = Mock(
            json=lambda: {"id": "container123"},
            raise_for_status=lambda: None,
        )

        uploader._create_reel_container(
            video_url="https://example.com/video.mp4",
            caption="Test",
            share_to_feed=True,
            cover_url="https://example.com/cover.jpg",
        )

        call_args = mock_post.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["cover_url"] == "https://example.com/cover.jpg"


class TestWaitForContainerEdgeCases:
    """Tests for _wait_for_container_ready edge cases."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    @patch("time.sleep")
    def test_unknown_status_code_logs_and_continues(self, mock_sleep, mock_get):
        """Unknown status_code is logged and polling continues."""
        uploader = InstagramUploader()

        mock_get.side_effect = [
            Mock(
                json=lambda: {"status_code": "PROCESSING", "status": "processing"},
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {"status_code": "FINISHED"},
                raise_for_status=lambda: None,
            ),
        ]

        result = uploader._wait_for_container_ready(
            "container123", max_wait=60, check_interval=1
        )
        assert result is True

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_request_exception_returns_false(self, mock_get):
        """RequestException during status check returns False."""
        uploader = InstagramUploader()

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = uploader._wait_for_container_ready("container123", max_wait=10)
        assert result is False


class TestPublishReelHTTPError:
    """Tests for _publish_reel error handling."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.post")
    def test_publish_reel_http_error_returns_none(self, mock_post):
        """_publish_reel returns None on HTTPError."""
        uploader = InstagramUploader()

        mock_response = Mock()
        mock_response.text = "Bad Request"
        mock_post.side_effect = requests.exceptions.HTTPError(
            "Publish failed", response=mock_response
        )

        result = uploader._publish_reel("container123")
        assert result is None


class TestGetMediaPermalinkError:
    """Tests for _get_media_permalink error handling."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_request_exception_returns_none(self, mock_get):
        """_get_media_permalink returns None on RequestException."""
        uploader = InstagramUploader()

        mock_get.side_effect = requests.exceptions.RequestException("error")

        result = uploader._get_media_permalink("media123")
        assert result is None


class TestUploadReelFromDropbox:
    """Tests for upload_reel_from_dropbox."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", None)
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_returns_none_when_not_functional(self):
        """upload_reel_from_dropbox returns None when not functional."""
        uploader = InstagramUploader()

        result = uploader.upload_reel_from_dropbox(
            dropbox_path="/test/video.mp4", caption="Test"
        )
        assert result is None

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_functional_returns_none_with_instructions(self):
        """upload_reel_from_dropbox logs instructions and returns None."""
        uploader = InstagramUploader()

        result = uploader.upload_reel_from_dropbox(
            dropbox_path="/test/video.mp4", caption="Test"
        )
        assert result is None


class TestGetAccountInfoEdgeCases:
    """Tests for get_account_info edge cases."""

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", None)
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    def test_returns_none_when_not_functional(self):
        """get_account_info returns None when not functional."""
        uploader = InstagramUploader()

        result = uploader.get_account_info()
        assert result is None

    @patch.object(Config, "INSTAGRAM_ACCESS_TOKEN", "valid_token")
    @patch.object(Config, "INSTAGRAM_ACCOUNT_ID", "valid_account_id")
    @patch("requests.get")
    def test_request_exception_returns_none(self, mock_get):
        """get_account_info returns None on RequestException."""
        uploader = InstagramUploader()

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = uploader.get_account_info()
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
