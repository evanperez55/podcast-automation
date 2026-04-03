"""Tests for TikTok uploader module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from uploaders.tiktok_uploader import TikTokUploader
from config import Config


class TestTikTokUploader:
    """Test cases for TikTokUploader class."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_init_with_valid_credentials(self):
        """Test initialization with valid credentials."""
        uploader = TikTokUploader()

        assert uploader.client_key == "valid_key"
        assert uploader.client_secret == "valid_secret"
        assert uploader.access_token == "valid_token"

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "your_tiktok_client_key_here")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_init_without_client_key(self):
        """Test initialization sets .functional = False without client key."""
        uploader = TikTokUploader()
        assert uploader.functional is False

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "your_tiktok_access_token_here")
    def test_init_without_access_token(self):
        """Test initialization sets .functional = False without access token."""
        uploader = TikTokUploader()
        assert uploader.functional is False

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_upload_video_file_not_found(self):
        """Test upload_video with non-existent file."""
        uploader = TikTokUploader()

        result = uploader.upload_video(
            video_path="/nonexistent/video.mp4", title="Test Video"
        )

        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("pathlib.Path.exists")
    @patch("requests.post")
    @patch("requests.put")
    def test_initialize_upload_success(self, mock_put, mock_post, mock_exists):
        """Test successful upload initialization."""
        mock_exists.return_value = True
        uploader = TikTokUploader()

        # Mock stat for file size
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value = Mock(st_size=1024000)

            # Mock API response
            mock_post.return_value = Mock(
                json=lambda: {
                    "data": {
                        "upload_url": "https://upload.tiktok.com/123",
                        "publish_id": "pub123",
                    }
                },
                raise_for_status=lambda: None,
            )

            upload_url, publish_id = uploader._initialize_upload(
                Path(__file__), title="Test Video"
            )

            assert upload_url == "https://upload.tiktok.com/123"
            assert publish_id == "pub123"

            # Verify title was included in the API payload
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["post_info"]["title"] == "Test Video"

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    @patch("requests.put")
    def test_upload_video_file_success(self, mock_put, mock_open, mock_exists):
        """Test successful video file upload."""
        mock_exists.return_value = True
        uploader = TikTokUploader()

        # Mock file read
        mock_open.return_value.__enter__.return_value.read.return_value = b"video_data"

        # Mock successful upload
        mock_put.return_value = Mock(raise_for_status=lambda: None)

        result = uploader._upload_video_file(
            "https://upload.tiktok.com/123", Path(__file__)
        )

        assert result is True

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_success(self, mock_sleep, mock_post):
        """Test successful video publish polling."""
        uploader = TikTokUploader()

        # Mock publish status check
        mock_post.return_value = Mock(
            json=lambda: {
                "data": {
                    "status": "PUBLISH_COMPLETE",
                    "share_url": "https://tiktok.com/@user/video/123",
                    "video_id": "vid123",
                }
            },
            raise_for_status=lambda: None,
        )

        result = uploader._wait_for_publish(publish_id="pub123")

        assert result is not None
        assert result["status"] == "PUBLISH_COMPLETE"
        assert result["video_id"] == "vid123"

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    def test_get_user_info_success(self, mock_post):
        """Test successful user info retrieval."""
        uploader = TikTokUploader()

        mock_post.return_value = Mock(
            json=lambda: {
                "data": {"user": {"display_name": "Test User", "follower_count": 1000}}
            },
            raise_for_status=lambda: None,
        )

        info = uploader.get_user_info()

        assert info is not None
        assert info["display_name"] == "Test User"
        assert info["follower_count"] == 1000


class TestTikTokFunctionalFlag:
    """Test cases for .functional flag on TikTokUploader."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", None)
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_tiktok_functional_false_when_no_key(self):
        """TikTokUploader sets .functional = False when client_key is None — no raise."""
        uploader = TikTokUploader()
        assert uploader.functional is False

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "your_tiktok_client_key_here")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_tiktok_functional_false_when_placeholder(self):
        """TikTokUploader sets .functional = False when client_key is placeholder."""
        uploader = TikTokUploader()
        assert uploader.functional is False

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "real_client_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "real_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "real_access_token")
    def test_tiktok_functional_true_when_configured(self):
        """TikTokUploader sets .functional = True when all real creds are set."""
        uploader = TikTokUploader()
        assert uploader.functional is True


class TestTikTokErrorPaths:
    """Tests for error handling paths."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_upload_video_not_functional(self):
        """upload_video returns None when not functional."""
        with patch.object(Config, "TIKTOK_CLIENT_KEY", None):
            uploader = TikTokUploader()
        result = uploader.upload_video("/fake.mp4", "Test")
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_get_user_info_not_functional(self):
        """get_user_info returns None when not functional."""
        with patch.object(Config, "TIKTOK_CLIENT_KEY", None):
            uploader = TikTokUploader()
        result = uploader.get_user_info()
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    def test_initialize_upload_api_error(self, mock_post):
        """Returns None on API error response."""
        import requests as req

        mock_post.side_effect = req.exceptions.RequestException("timeout")
        uploader = TikTokUploader()

        with patch.object(Path, "stat", return_value=Mock(st_size=1024)):
            url, pid = uploader._initialize_upload(Path("/fake.mp4"))
        assert url is None
        assert pid is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.put")
    def test_upload_video_file_failure(self, mock_put):
        """Returns False on upload failure."""
        import requests as req

        mock_put.side_effect = req.exceptions.RequestException("fail")
        uploader = TikTokUploader()

        result = uploader._upload_video_file(
            "https://upload.example.com", Path(__file__)
        )
        assert result is False

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_failed(self, mock_sleep, mock_post):
        """Returns None when publish status is FAILED."""
        mock_post.return_value = Mock(
            json=lambda: {"data": {"status": "FAILED", "fail_reason": "copyright"}},
            raise_for_status=lambda: None,
        )
        uploader = TikTokUploader()
        result = uploader._wait_for_publish("pub123")
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_api_error_response(self, mock_sleep, mock_post):
        """Returns None when API returns error."""
        mock_post.return_value = Mock(
            json=lambda: {"error": {"code": "invalid_token", "message": "expired"}},
            raise_for_status=lambda: None,
        )
        uploader = TikTokUploader()
        result = uploader._wait_for_publish("pub123")
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    def test_get_user_info_api_error(self, mock_post):
        """Returns None on API error."""
        mock_post.return_value = Mock(
            json=lambda: {"error": {"code": "invalid", "message": "err"}},
            raise_for_status=lambda: None,
        )
        uploader = TikTokUploader()
        result = uploader.get_user_info()
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    def test_get_user_info_request_exception(self, mock_post):
        """Returns None on request exception."""
        import requests as req

        mock_post.side_effect = req.exceptions.RequestException("network error")
        uploader = TikTokUploader()
        result = uploader.get_user_info()
        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    def test_initialize_upload_api_error_response(self):
        """Returns None when init response has error field."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                json=lambda: {"error": {"code": "rate_limit", "message": "slow down"}},
                raise_for_status=lambda: None,
            )
            uploader = TikTokUploader()
            with patch.object(Path, "stat", return_value=Mock(st_size=1024)):
                url, pid = uploader._initialize_upload(Path("/fake.mp4"))
        assert url is None
        assert pid is None


class TestUploadVideoHappyPath:
    """Tests for upload_video full flow through _initialize, _upload_file, _wait_for_publish."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_video_success(self, mock_exists):
        """Full success path returns result dict with publish_id and share_url."""
        uploader = TikTokUploader()
        publish_result = {
            "publish_id": "pub456",
            "status": "PUBLISH_COMPLETE",
            "share_url": "https://tiktok.com/@user/video/456",
            "video_id": "vid456",
        }
        with (
            patch.object(
                uploader,
                "_initialize_upload",
                return_value=("https://upload.tiktok.com/456", "pub456"),
            ),
            patch.object(uploader, "_upload_video_file", return_value=True),
            patch.object(uploader, "_wait_for_publish", return_value=publish_result),
        ):
            result = uploader.upload_video("/fake/video.mp4", "Test Title")

        assert result is not None
        assert result["publish_id"] == "pub456"
        assert result["share_url"] == "https://tiktok.com/@user/video/456"

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_video_init_failure_returns_none(self, mock_exists):
        """upload_video returns None when _initialize_upload fails."""
        uploader = TikTokUploader()
        with patch.object(uploader, "_initialize_upload", return_value=(None, None)):
            result = uploader.upload_video("/fake/video.mp4", "Test Title")

        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("pathlib.Path.exists", return_value=True)
    def test_upload_video_file_upload_failure_returns_none(self, mock_exists):
        """upload_video returns None when _upload_video_file fails."""
        uploader = TikTokUploader()
        with (
            patch.object(
                uploader,
                "_initialize_upload",
                return_value=("https://upload.tiktok.com/789", "pub789"),
            ),
            patch.object(uploader, "_upload_video_file", return_value=False),
        ):
            result = uploader.upload_video("/fake/video.mp4", "Test Title")

        assert result is None


class TestInitializeUploadResponseLogging:
    """Tests for _initialize_upload response text logging on exception."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    def test_initialize_upload_logs_response_text_on_exception(self, mock_post):
        """Logs e.response.text when RequestException has a response attached."""
        import requests as req

        mock_response = Mock()
        mock_response.text = "server error details"
        exc = req.exceptions.RequestException("fail")
        exc.response = mock_response
        mock_post.side_effect = exc

        uploader = TikTokUploader()
        with patch.object(Path, "stat", return_value=Mock(st_size=1024)):
            url, pid = uploader._initialize_upload(Path("/fake.mp4"))

        assert url is None
        assert pid is None


class TestWaitForPublishEdgeCases:
    """Tests for _wait_for_publish polling, timeout, and exception paths."""

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_polling_then_success(self, mock_sleep, mock_post):
        """Polls through IN_PROGRESS statuses then returns on PUBLISH_COMPLETE."""
        in_progress_resp = Mock(
            json=lambda: {"data": {"status": "PROCESSING"}},
            raise_for_status=lambda: None,
        )
        complete_resp = Mock(
            json=lambda: {
                "data": {
                    "status": "PUBLISH_COMPLETE",
                    "share_url": "https://tiktok.com/@user/video/999",
                    "video_id": "vid999",
                }
            },
            raise_for_status=lambda: None,
        )
        mock_post.side_effect = [in_progress_resp, in_progress_resp, complete_resp]

        uploader = TikTokUploader()
        result = uploader._wait_for_publish("pub999")

        assert result is not None
        assert result["status"] == "PUBLISH_COMPLETE"
        assert result["video_id"] == "vid999"
        # Should have slept for initial wait + 2 polling waits
        assert mock_sleep.call_count == 3

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_request_exception_returns_none(
        self, mock_sleep, mock_post
    ):
        """Returns None when a RequestException occurs during polling."""
        import requests as req

        mock_post.side_effect = req.exceptions.RequestException("network error")

        uploader = TikTokUploader()
        result = uploader._wait_for_publish("pub123")

        assert result is None

    @patch.object(Config, "TIKTOK_CLIENT_KEY", "valid_key")
    @patch.object(Config, "TIKTOK_CLIENT_SECRET", "valid_secret")
    @patch.object(Config, "TIKTOK_ACCESS_TOKEN", "valid_token")
    @patch("requests.post")
    @patch("time.sleep", return_value=None)
    def test_wait_for_publish_timeout_returns_none(self, mock_sleep, mock_post):
        """Returns None after max_attempts when status never reaches PUBLISH_COMPLETE."""
        mock_post.return_value = Mock(
            json=lambda: {"data": {"status": "PROCESSING"}},
            raise_for_status=lambda: None,
        )

        uploader = TikTokUploader()
        result = uploader._wait_for_publish("pub123")

        assert result is None
        # 30 polling attempts + 1 initial sleep
        assert mock_sleep.call_count == 31


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
