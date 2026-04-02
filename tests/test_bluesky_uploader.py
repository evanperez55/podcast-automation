"""Tests for Bluesky uploader."""

import pytest
from unittest.mock import patch, MagicMock

from uploaders.bluesky_uploader import BlueskyUploader, create_bluesky_caption


MOCK_SESSION = {
    "did": "did:plc:abc123",
    "accessJwt": "fake-jwt-token",
    "refreshJwt": "fake-refresh-token",
}


class TestBlueskyUploaderInit:
    """Tests for BlueskyUploader initialization."""

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_init_success(self, mock_config, mock_auth):
        """Valid credentials should initialize successfully."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx-xxxx-xxxx"
        uploader = BlueskyUploader()
        assert uploader.handle == "test.bsky.social"
        mock_auth.assert_called_once()

    @patch("uploaders.bluesky_uploader.Config")
    def test_init_missing_credentials(self, mock_config):
        """Missing credentials should raise ValueError."""
        mock_config.BLUESKY_HANDLE = None
        mock_config.BLUESKY_APP_PASSWORD = None
        with pytest.raises(ValueError, match="Bluesky credentials not configured"):
            BlueskyUploader()

    @patch("uploaders.bluesky_uploader.Config")
    def test_init_missing_handle(self, mock_config):
        """Missing handle should raise ValueError."""
        mock_config.BLUESKY_HANDLE = None
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        with pytest.raises(ValueError, match="Bluesky credentials not configured"):
            BlueskyUploader()

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_authenticate_success(self, mock_config, mock_post):
        """Successful authentication stores session."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        mock_post.return_value = MagicMock(status_code=200, json=lambda: MOCK_SESSION)
        mock_post.return_value.raise_for_status = MagicMock()
        uploader = BlueskyUploader()
        assert uploader.session == MOCK_SESSION

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_authenticate_failure(self, mock_config, mock_post):
        """Failed authentication sets session to None."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "bad-password"
        import requests as req

        mock_post.side_effect = req.RequestException("Auth failed")
        uploader = BlueskyUploader()
        assert uploader.session is None


class TestBlueskyPost:
    """Tests for BlueskyUploader.post."""

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_success(self, mock_config, mock_post):
        """Successful post returns post info."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/rkey123"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]

        uploader = BlueskyUploader()
        result = uploader.post("Hello Bluesky!")
        assert result is not None
        assert result["status"] == "success"
        assert "rkey123" in result["post_url"]

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_not_authenticated(self, mock_config, mock_auth):
        """Post without session returns None."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = None
        result = uploader.post("Hello!")
        assert result is None

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_truncates_to_300(self, mock_config, mock_post):
        """Text longer than 300 chars should be truncated."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/rkey456"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]

        uploader = BlueskyUploader()
        long_text = "a" * 500
        result = uploader.post(long_text)
        assert result is not None
        assert result["text"] == "a" * 300

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_external_url(self, mock_config, mock_post):
        """Post with URL not in text adds external embed."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/rkey789"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]

        uploader = BlueskyUploader()
        result = uploader.post(
            "Check out our new episode!",
            url="https://youtube.com/watch?v=abc",
            url_title="Episode 30",
        )
        assert result is not None
        # Verify the create record call included embed
        call_args = mock_post.call_args_list[1]
        record = call_args.kwargs["json"]["record"]
        assert "embed" in record
        assert record["embed"]["external"]["uri"] == "https://youtube.com/watch?v=abc"


class TestBlueskyEpisodeAnnouncement:
    """Tests for BlueskyUploader.post_episode_announcement."""

    @patch.object(BlueskyUploader, "post", return_value={"status": "success"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_announcement_with_caption(self, mock_config, mock_auth, mock_post):
        """AI-generated caption should be used when provided."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        mock_config.PODCAST_NAME = "Test Podcast"
        uploader = BlueskyUploader()
        result = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
            bluesky_caption="Custom caption here",
        )
        assert result is not None
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "Custom caption here" in call_kwargs["text"]

    @patch.object(BlueskyUploader, "post", return_value={"status": "success"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_announcement_fallback_template(self, mock_config, mock_auth, mock_post):
        """Without caption, uses default template."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        mock_config.PODCAST_NAME = "Test Podcast"
        uploader = BlueskyUploader()
        result = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode about stuff",
        )
        assert result is not None
        call_kwargs = mock_post.call_args.kwargs
        assert "Episode 30" in call_kwargs["text"]

    @patch.object(BlueskyUploader, "post", return_value={"status": "success"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_announcement_with_hashtags(self, mock_config, mock_auth, mock_post):
        """Hashtags should be appended if space allows."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        mock_config.PODCAST_NAME = "Test Podcast"
        uploader = BlueskyUploader()
        uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
            bluesky_caption="Short caption",
            hashtags=["podcast", "comedy"],
        )
        call_kwargs = mock_post.call_args.kwargs
        assert "#podcast" in call_kwargs["text"]


class TestCreateBlueskyCaption:
    """Tests for create_bluesky_caption helper."""

    def test_caption_within_limits(self):
        """Caption under 300 chars includes hashtags."""
        result = create_bluesky_caption("Title", "Description")
        assert "#podcast" in result
        assert len(result) <= 300

    def test_caption_truncated(self):
        """Long caption is truncated to 300 chars."""
        result = create_bluesky_caption("Title", "x" * 500)
        assert len(result) <= 300
        assert result.endswith("...")

    def test_custom_hashtags(self):
        """Custom hashtags are used when provided."""
        result = create_bluesky_caption("Title", "Desc", hashtags=["custom"])
        assert "#custom" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
