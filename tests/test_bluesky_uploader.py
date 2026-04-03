"""Tests for Bluesky uploader."""

import pytest
from unittest.mock import patch, MagicMock

from uploaders.bluesky_uploader import BlueskyUploader


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

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_success(self, mock_config, mock_post, mock_get):
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
        mock_get.return_value = MagicMock(status_code=200)

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

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_truncates_long_text(self, mock_config, mock_post, mock_get):
        """Text longer than 280 chars should be truncated for grapheme safety."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/rkey456"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()
        long_text = "a" * 500
        result = uploader.post(long_text)
        assert result is not None
        assert result["text"] == "a" * 280

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_external_url(self, mock_config, mock_post, mock_get):
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
        mock_get.return_value = MagicMock(status_code=200)

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


class TestGetHeaders:
    """Tests for BlueskyUploader._get_headers."""

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_get_headers_no_session(self, mock_config, mock_auth):
        """Returns None when session is not set."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = None
        result = uploader._get_headers()
        assert result is None


class TestPostLinkFacet:
    """Tests for post with URL in text (link facet)."""

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_url_in_text(self, mock_config, mock_post, mock_get):
        """URL embedded in text creates a link facet."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/facet1"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()
        url = "https://example.com"
        result = uploader.post(f"Check this out {url}", url=url)
        assert result is not None
        call_args = mock_post.call_args_list[1]
        record = call_args.kwargs["json"]["record"]
        assert "facets" in record
        assert record["facets"][0]["features"][0]["uri"] == url


class TestPostUnicodeEncodeError:
    """Tests for UnicodeEncodeError handling in post logging."""

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_unicode_logging_fallback(self, mock_config, mock_post, mock_get):
        """UnicodeEncodeError in logging falls back to ASCII replacement."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/uni1"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.side_effect = [auth_response, post_response]
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()

        # The inner try/except on lines 131-137 catches UnicodeEncodeError
        # from logger.info("Text: %s...", text[:100]) and retries with ASCII.
        # We need the first "Text:" call to raise, but the second to succeed.
        text_call_count = {"n": 0}

        def _raise_first_text_log(msg, *args, **kwargs):
            if "Text:" in str(msg):
                text_call_count["n"] += 1
                if text_call_count["n"] == 1:
                    raise UnicodeEncodeError("ascii", "text", 0, 1, "mock")

        with patch("uploaders.bluesky_uploader.logger") as mock_logger:
            mock_logger.info = MagicMock(side_effect=_raise_first_text_log)
            mock_logger.error = MagicMock()
            result = uploader.post("Hello emoji text")

        assert result is not None
        # The fallback logger.info call should have been made
        assert text_call_count["n"] == 2


class TestPostRequestFailure:
    """Tests for post request failure handling."""

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_request_exception(self, mock_config, mock_post, mock_get):
        """RequestException during post returns None."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        import requests as req

        auth_response = MagicMock(json=lambda: MOCK_SESSION)
        auth_response.raise_for_status = MagicMock()
        mock_post.side_effect = [
            auth_response,
            req.RequestException("Post failed"),
        ]
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()
        result = uploader.post("Hello!")
        assert result is None


class TestUploadImage:
    """Tests for BlueskyUploader.upload_image."""

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_upload_image_no_session(self, mock_config, mock_auth):
        """Returns None when not authenticated."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = None
        result = uploader.upload_image("/some/image.png")
        assert result is None

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_upload_image_not_found(self, mock_config, mock_auth):
        """Returns None when image file does not exist."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION
        result = uploader.upload_image("/nonexistent/image.png")
        assert result is None

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_upload_image_success_png(
        self, mock_config, mock_auth, mock_post, tmp_path
    ):
        """Successfully uploads a PNG image."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake image")

        mock_response = MagicMock()
        mock_response.json.return_value = {"blob": {"ref": "blob-ref-123"}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = uploader.upload_image(str(img))
        assert result == {"ref": "blob-ref-123"}
        call_kwargs = mock_post.call_args
        assert "image/png" in str(call_kwargs)

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_upload_image_success_jpeg(
        self, mock_config, mock_auth, mock_post, tmp_path
    ):
        """Successfully uploads a JPEG image."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0 fake jpeg")

        mock_response = MagicMock()
        mock_response.json.return_value = {"blob": {"ref": "blob-ref-456"}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = uploader.upload_image(str(img))
        assert result == {"ref": "blob-ref-456"}

    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_upload_image_request_exception(
        self, mock_config, mock_auth, mock_post, tmp_path
    ):
        """Returns None on upload request failure."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        import requests as req

        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake")

        mock_post.side_effect = req.RequestException("Upload failed")
        result = uploader.upload_image(str(img))
        assert result is None


class TestPostWithImage:
    """Tests for BlueskyUploader.post_with_image."""

    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_image_no_session(self, mock_config, mock_auth):
        """Returns None when not authenticated."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        uploader = BlueskyUploader()
        uploader.session = None
        result = uploader.post_with_image("Hello", "/some/image.png")
        assert result is None

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch.object(BlueskyUploader, "upload_image", return_value=None)
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_image_upload_fails(
        self, mock_config, mock_auth, mock_upload, mock_get
    ):
        """Returns None when image upload fails."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        mock_get.return_value = MagicMock(status_code=200)
        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION
        result = uploader.post_with_image("Hello", "/some/image.png")
        assert result is None

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "upload_image", return_value={"ref": "blob-ref"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_image_success(
        self, mock_config, mock_auth, mock_upload, mock_post, mock_get
    ):
        """Successfully posts with image embed."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/img1"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.return_value = post_response
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION
        result = uploader.post_with_image("Hello image!", "/img.png", alt_text="Alt")
        assert result is not None
        assert result["status"] == "success"
        assert "img1" in result["post_url"]

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "upload_image", return_value={"ref": "blob-ref"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_image_no_alt_text(
        self, mock_config, mock_auth, mock_upload, mock_post, mock_get
    ):
        """Uses text[:100] as alt text when none provided."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"

        post_response = MagicMock(
            json=lambda: {"uri": "at://did:plc:abc123/app.bsky.feed.post/img2"}
        )
        post_response.raise_for_status = MagicMock()
        mock_post.return_value = post_response
        mock_get.return_value = MagicMock(status_code=200)

        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION
        result = uploader.post_with_image("Hello image!", "/img.png")
        assert result is not None

        call_kwargs = mock_post.call_args.kwargs
        record = call_kwargs["json"]["record"]
        assert record["embed"]["images"][0]["alt"] == "Hello image!"

    @patch("uploaders.bluesky_uploader.requests.get")
    @patch("uploaders.bluesky_uploader.requests.post")
    @patch.object(BlueskyUploader, "upload_image", return_value={"ref": "blob-ref"})
    @patch.object(BlueskyUploader, "_authenticate")
    @patch("uploaders.bluesky_uploader.Config")
    def test_post_with_image_request_exception(
        self, mock_config, mock_auth, mock_upload, mock_post, mock_get
    ):
        """Returns None on post request failure."""
        mock_config.BLUESKY_HANDLE = "test.bsky.social"
        mock_config.BLUESKY_APP_PASSWORD = "xxxx"
        import requests as req

        mock_post.side_effect = req.RequestException("Post failed")
        mock_get.return_value = MagicMock(status_code=200)
        uploader = BlueskyUploader()
        uploader.session = MOCK_SESSION
        result = uploader.post_with_image("Hello!", "/img.png")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
