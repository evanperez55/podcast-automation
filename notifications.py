"""Discord notifications for podcast automation pipeline."""

from datetime import datetime, timezone

import requests
from logger import logger
from config import Config


class DiscordNotifier:
    """Fire-and-forget Discord webhook notifications for pipeline events."""

    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or Config.DISCORD_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)

    def send_notification(self, title, description, color=0x00FF00, fields=None):
        """Send a rich embed notification to Discord.

        Args:
            title: Embed title.
            description: Embed description text.
            color: Embed sidebar color (hex int).
            fields: Optional list of field dicts with name, value, inline keys.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.enabled:
            logger.warning("Discord notifications disabled (no webhook URL configured)")
            return False

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if fields:
            embed["fields"] = fields

        payload = {"embeds": [embed]}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Discord notification sent: %s", title)
            return True
        except requests.RequestException as e:
            logger.warning("Failed to send Discord notification: %s", e)
            return False

    def notify_success(self, results):
        """Send a green success notification after episode processing completes.

        Args:
            results: Pipeline results dict with episode info, clips, and social media results.
        """
        platforms = ", ".join(results.get("social_media_results", {}).keys()) or "None"
        fields = [
            {
                "name": "Episode",
                "value": results.get("episode_title", "Unknown"),
                "inline": True,
            },
            {
                "name": "Episode #",
                "value": str(results.get("episode_number", "?")),
                "inline": True,
            },
            {
                "name": "Clips",
                "value": str(len(results.get("clips", []))),
                "inline": True,
            },
            {"name": "Platforms", "value": platforms, "inline": False},
        ]
        return self.send_notification(
            title="Episode Processing Complete",
            description="The episode was processed and distributed successfully.",
            color=0x00FF00,
            fields=fields,
        )

    def notify_failure(self, episode_info, error, step="unknown"):
        """Send a red failure notification when episode processing fails.

        Args:
            episode_info: String or identifier for the episode being processed.
            error: The error message or exception.
            step: Pipeline step where the failure occurred.
        """
        fields = [
            {"name": "Step", "value": step, "inline": True},
            {"name": "Error", "value": str(error), "inline": False},
            {"name": "Episode", "value": str(episode_info), "inline": True},
        ]
        return self.send_notification(
            title="Episode Processing Failed",
            description=f"Processing failed during **{step}** step: {error}",
            color=0xFF0000,
            fields=fields,
        )

    def notify_partial_success(self, results, warnings):
        """Send a yellow notification when processing completes with warnings.

        Args:
            results: Pipeline results dict with episode info, clips, and social media results.
            warnings: List of warning strings describing issues encountered.
        """
        warning_text = (
            "\n".join(f"- {w}" for w in warnings) if warnings else "No details."
        )
        platforms = ", ".join(results.get("social_media_results", {}).keys()) or "None"
        fields = [
            {
                "name": "Episode",
                "value": results.get("episode_title", "Unknown"),
                "inline": True,
            },
            {
                "name": "Episode #",
                "value": str(results.get("episode_number", "?")),
                "inline": True,
            },
            {
                "name": "Clips",
                "value": str(len(results.get("clips", []))),
                "inline": True,
            },
            {"name": "Platforms", "value": platforms, "inline": False},
        ]
        return self.send_notification(
            title="Episode Processing Completed with Warnings",
            description=warning_text,
            color=0xFFFF00,
            fields=fields,
        )
