"""Tests for DiscordNotifier in notifications.py."""

from unittest.mock import patch, Mock

from notifications import DiscordNotifier
from config import Config


class TestDiscordNotifier:
    """Tests for the DiscordNotifier class."""

    def test_init_with_webhook_url(self):
        """Passing an explicit webhook URL sets enabled=True."""
        notifier = DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        assert notifier.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert notifier.enabled is True

    @patch.object(
        Config, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/456/def"
    )
    def test_init_with_config_url(self):
        """When no explicit URL is given, falls back to Config.DISCORD_WEBHOOK_URL."""
        notifier = DiscordNotifier()
        assert notifier.webhook_url == "https://discord.com/api/webhooks/456/def"
        assert notifier.enabled is True

    @patch.object(Config, "DISCORD_WEBHOOK_URL", None)
    def test_init_without_url(self):
        """When no URL is available anywhere, enabled is False."""
        notifier = DiscordNotifier()
        assert notifier.webhook_url is None
        assert notifier.enabled is False

    @patch.object(Config, "DISCORD_WEBHOOK_URL", None)
    @patch("notifications.requests.post")
    def test_send_notification_disabled(self, mock_post):
        """When disabled, send_notification returns False without making a request."""
        notifier = DiscordNotifier()
        result = notifier.send_notification("Title", "Description")
        assert result is False
        mock_post.assert_not_called()

    @patch("notifications.requests.post")
    def test_send_notification_success(self, mock_post):
        """Successful POST returns True and sends correct embed structure."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.send_notification("Test Title", "Test Description")

        assert result is True
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert embed["title"] == "Test Title"
        assert embed["description"] == "Test Description"
        assert embed["color"] == 0x00FF00
        assert "timestamp" in embed
        assert "fields" not in embed

    @patch("notifications.requests.post")
    def test_send_notification_with_fields(self, mock_post):
        """Fields are included in the embed when provided."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        fields = [
            {"name": "Field1", "value": "Value1", "inline": True},
            {"name": "Field2", "value": "Value2", "inline": False},
        ]
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.send_notification("Title", "Desc", fields=fields)

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["fields"] == fields

    @patch("notifications.requests.post")
    def test_send_notification_failure(self, mock_post):
        """When requests.post raises RequestException, returns False."""
        import requests

        mock_post.side_effect = requests.RequestException("Connection error")

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.send_notification("Title", "Desc")

        assert result is False

    @patch("notifications.requests.post")
    def test_notify_success(self, mock_post):
        """notify_success sends green embed with Episode, Clips, and Platforms fields."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        results = {
            "episode_title": "Ep 42: The Answer",
            "episode_number": 42,
            "clips": ["clip1.mp4", "clip2.mp4", "clip3.mp4"],
            "social_media_results": {"youtube": True, "twitter": True},
        }
        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.notify_success(results)

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["color"] == 0x00FF00
        assert embed["title"] == "Episode Processing Complete"

        field_map = {f["name"]: f["value"] for f in embed["fields"]}
        assert field_map["Episode"] == "Ep 42: The Answer"
        assert field_map["Clips"] == "3"
        assert "youtube" in field_map["Platforms"]
        assert "twitter" in field_map["Platforms"]

    @patch("notifications.requests.post")
    def test_notify_failure(self, mock_post):
        """notify_failure sends red embed with Step, Error, and Episode fields."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.notify_failure(
            "ep42", "Transcription timeout", step="transcription"
        )

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["color"] == 0xFF0000
        assert embed["title"] == "Episode Processing Failed"

        field_map = {f["name"]: f["value"] for f in embed["fields"]}
        assert field_map["Step"] == "transcription"
        assert field_map["Error"] == "Transcription timeout"
        assert field_map["Episode"] == "ep42"

    @patch("notifications.requests.post")
    def test_notify_partial_success(self, mock_post):
        """notify_partial_success sends yellow embed with warnings in description."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        results = {
            "episode_title": "Ep 43: Close Call",
            "episode_number": 43,
            "clips": ["clip1.mp4"],
            "social_media_results": {"youtube": True},
        }
        warnings = ["Twitter upload failed", "TikTok rate limited"]

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.notify_partial_success(results, warnings)

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["color"] == 0xFFFF00
        assert "Twitter upload failed" in embed["description"]
        assert "TikTok rate limited" in embed["description"]

    @patch("notifications.requests.post")
    def test_send_notification_custom_color(self, mock_post):
        """Custom color value is passed through to the embed."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.send_notification("Title", "Desc", color=0x9B59B6)

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        assert embed["color"] == 0x9B59B6

    @patch("notifications.requests.post")
    def test_notify_success_empty_results(self, mock_post):
        """notify_success with empty dict falls back to default field values."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test")
        result = notifier.notify_success({})

        assert result is True
        embed = mock_post.call_args.kwargs["json"]["embeds"][0]
        field_map = {f["name"]: f["value"] for f in embed["fields"]}
        assert field_map["Episode"] == "Unknown"
        assert field_map["Episode #"] == "?"
        assert field_map["Clips"] == "0"
        assert field_map["Platforms"] == "None"
