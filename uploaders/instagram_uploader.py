"""Instagram uploader for podcast clips as Reels."""

import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from config import Config
from logger import logger
from retry_utils import retry_with_backoff


class InstagramUploader:
    """Handle Instagram Reels uploads via Graph API."""

    # Instagram Graph API base URL
    API_BASE = "https://graph.instagram.com/v21.0"

    def __init__(self):
        """Initialize Instagram uploader."""
        token = Config.INSTAGRAM_ACCESS_TOKEN
        account_id = Config.INSTAGRAM_ACCOUNT_ID
        self.functional = (
            bool(token)
            and token != "your_instagram_access_token_here"
            and bool(account_id)
            and account_id != "your_instagram_account_id_here"
        )
        if not self.functional:
            return
        self.access_token = token
        self.account_id = account_id
        # Instagram Login tokens use "me" instead of account ID for API calls
        self.api_user = "me" if token.startswith("IGAA") else account_id

        # Auto-refresh token if expiring within 7 days
        self._refresh_token_if_needed()

    # Token refresh threshold: 7 days in seconds
    REFRESH_THRESHOLD = 7 * 86400

    def _refresh_token_if_needed(self):
        """Refresh the Instagram token if it expires within 7 days.

        Skips refresh in CI environments (no .env to persist to).
        Only calls the refresh API when the token is near expiry.
        Persists the new token to .env so subsequent runs use it.
        """
        import os

        # Skip in CI — can't persist refreshed token to GitHub Secrets
        if os.getenv("CI"):
            return

        try:
            # Check current token expiry without refreshing
            refresh_resp = requests.get(
                "https://graph.instagram.com/refresh_access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": self.access_token,
                },
            )
            if refresh_resp.status_code != 200:
                logger.warning("Instagram token check failed: %s", refresh_resp.text)
                return

            data = refresh_resp.json()
            expires_in = data.get("expires_in", 0)
            new_token = data.get("access_token")
            days_left = expires_in // 86400

            if not new_token:
                return

            # Only persist if within refresh threshold
            if expires_in > self.REFRESH_THRESHOLD:
                logger.debug("Instagram token OK (%s days left)", days_left)
                return

            logger.info(
                "Instagram token expires in %s days — refreshing", days_left
            )

            if new_token != self.access_token:
                self.access_token = new_token
                self._persist_token(new_token)
                logger.info("Instagram token refreshed and saved to .env")

        except requests.exceptions.RequestException as e:
            logger.warning("Instagram token refresh check failed: %s", e)

    def _persist_token(self, new_token: str):
        """Update INSTAGRAM_ACCESS_TOKEN in the .env file.

        Args:
            new_token: The new long-lived access token.
        """
        env_path = Path(".env")
        if not env_path.exists():
            return

        lines = env_path.read_text().splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
                lines[i] = f"INSTAGRAM_ACCESS_TOKEN={new_token}"
                updated = True
                break

        if updated:
            env_path.write_text("\n".join(lines) + "\n")

    def upload_reel(
        self,
        video_url: str,
        caption: str,
        share_to_feed: bool = True,
        cover_url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a video as an Instagram Reel.

        Note: Instagram requires the video to be hosted at a publicly accessible URL.
        You may need to temporarily upload to Dropbox or another host with public links.

        Instagram Reels requirements:
        - Duration: 3-90 seconds
        - Aspect ratio: 9:16 (vertical)
        - Resolution: Minimum 500x888 pixels
        - File size: Maximum 1GB
        - Format: MP4

        Args:
            video_url: Publicly accessible URL to the video file
            caption: Caption for the Reel (max 2200 characters)
            share_to_feed: Whether to share to main feed
            cover_url: Optional publicly accessible URL to cover image

        Returns:
            Dictionary with Reel ID and permalink, or None if upload failed
        """
        if not self.functional:
            return None
        logger.info("Uploading Reel to Instagram")
        logger.info("Caption: %s...", caption[:80])

        # Step 1: Create Reel container
        container_id = self._create_reel_container(
            video_url=video_url,
            caption=caption,
            share_to_feed=share_to_feed,
            cover_url=cover_url,
        )

        if not container_id:
            logger.error("Failed to create Reel container")
            return None

        # Step 2: Wait for video to be processed
        logger.info("Waiting for Instagram to process the video...")
        if not self._wait_for_container_ready(container_id):
            logger.error("Video processing failed or timed out")
            return None

        # Step 3: Publish the Reel
        result = self._publish_reel(container_id)

        if result:
            logger.info("Reel uploaded successfully!")
            logger.info("Reel ID: %s", result["id"])
            if result.get("permalink"):
                logger.info("Reel URL: %s", result["permalink"])

        return result

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            ConnectionError,
            TimeoutError,
        ),
    )
    def _create_reel_container(
        self,
        video_url: str,
        caption: str,
        share_to_feed: bool,
        cover_url: Optional[str],
    ) -> Optional[str]:
        """
        Create a Reel media container.

        Args:
            video_url: URL to video file
            caption: Reel caption
            share_to_feed: Share to feed flag
            cover_url: Optional cover image URL

        Returns:
            Container ID if successful, None otherwise
        """
        endpoint = f"{self.API_BASE}/{self.api_user}/media"

        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],  # Instagram max caption length
            "share_to_feed": share_to_feed,
            "access_token": self.access_token,
        }

        if cover_url:
            params["cover_url"] = cover_url

        try:
            response = requests.post(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            container_id = data.get("id")
            logger.info("Reel container created: %s", container_id)
            return container_id

        except requests.exceptions.HTTPError as e:
            logger.error("Failed to create Reel container: %s", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response: %s", e.response.text)
            return None

    def _wait_for_container_ready(
        self, container_id: str, max_wait: int = 300, check_interval: int = 5
    ) -> bool:
        """
        Wait for Instagram to process the video container.

        Args:
            container_id: Media container ID
            max_wait: Maximum time to wait in seconds
            check_interval: Time between status checks in seconds

        Returns:
            True if ready, False if failed or timed out
        """
        endpoint = f"{self.API_BASE}/{container_id}"
        params = {"fields": "status_code,status", "access_token": self.access_token}

        elapsed = 0
        current_interval = 3  # Start at 3s, grow with backoff
        while elapsed < max_wait:
            try:
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

                status_code = data.get("status_code")
                status = data.get("status", "UNKNOWN")

                if status_code == "FINISHED":
                    logger.info("Video processing complete")
                    return True
                elif status_code == "ERROR":
                    logger.error("Video processing failed: %s", status)
                    return False
                elif status_code == "IN_PROGRESS":
                    logger.info("Processing... (%ss elapsed)", elapsed)
                else:
                    logger.info("Status: %s (%ss elapsed)", status_code, elapsed)

                time.sleep(current_interval)
                elapsed += current_interval
                current_interval = min(
                    current_interval * 1.5, 30
                )  # Exponential backoff, cap 30s

            except requests.exceptions.RequestException as e:
                logger.error("Failed to check status: %s", e)
                return False

        logger.error("Processing timed out after %ss", max_wait)
        return False

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            ConnectionError,
            TimeoutError,
        ),
    )
    def _publish_reel(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Publish a processed Reel container.

        Args:
            container_id: Media container ID

        Returns:
            Dictionary with Reel ID and permalink, or None if failed
        """
        endpoint = f"{self.API_BASE}/{self.api_user}/media_publish"
        params = {"creation_id": container_id, "access_token": self.access_token}

        try:
            response = requests.post(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            reel_id = data.get("id")

            # Get permalink
            permalink = self._get_media_permalink(reel_id)

            return {"id": reel_id, "permalink": permalink, "status": "success"}

        except requests.exceptions.HTTPError as e:
            logger.error("Failed to publish Reel: %s", e)
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response: %s", e.response.text)
            return None

    def _get_media_permalink(self, media_id: str) -> Optional[str]:
        """
        Get the permalink URL for a published media item.

        Args:
            media_id: Instagram media ID

        Returns:
            Permalink URL if successful, None otherwise
        """
        endpoint = f"{self.API_BASE}/{media_id}"
        params = {"fields": "permalink", "access_token": self.access_token}

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("permalink")

        except requests.exceptions.RequestException:
            return None

    def upload_reel_from_dropbox(
        self, dropbox_path: str, caption: str, share_to_feed: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a Reel using a Dropbox shared link.

        This is a convenience method that handles getting a public Dropbox link.

        Args:
            dropbox_path: Path to video in Dropbox
            caption: Reel caption
            share_to_feed: Whether to share to feed

        Returns:
            Dictionary with Reel ID and permalink, or None if upload failed
        """
        if not self.functional:
            return None
        # Note: This requires Dropbox handler integration
        # For now, this is a placeholder that expects a direct link
        logger.info("To upload from Dropbox, you need to:")
        logger.info("1. Get a public shared link for the video")
        logger.info("2. Replace 'dl=0' with 'dl=1' in the URL")
        logger.info("3. Use upload_reel() with that URL")

        return None

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the Instagram account.

        Returns:
            Dictionary with account information
        """
        if not self.functional:
            return None
        endpoint = f"{self.API_BASE}/{self.api_user}"
        params = {
            "fields": "id,username,followers_count,media_count",
            "access_token": self.access_token,
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error("Failed to get account info: %s", e)
            return None

    def delete_media(self, media_id: str) -> bool:
        """Delete a media item (Reel, photo, etc.) from Instagram.

        Safety: verifies the media caption contains '[TEST]' before deleting
        to prevent accidental deletion of real content.

        Args:
            media_id: Instagram media ID to delete.

        Returns:
            True if successful, False otherwise.
        """
        if not self.functional:
            return False

        # Safety check: verify the media is a test upload
        try:
            check_resp = requests.get(
                f"{self.API_BASE}/{media_id}",
                params={"fields": "caption", "access_token": self.access_token},
            )
            if check_resp.status_code == 200:
                caption = check_resp.json().get("caption", "")
                if "[TEST]" not in caption:
                    logger.error(
                        "Refusing to delete media %s — caption does not contain [TEST]",
                        media_id,
                    )
                    return False
        except requests.exceptions.RequestException:
            logger.error("Cannot verify media %s before deletion — aborting", media_id)
            return False

        endpoint = f"{self.API_BASE}/{media_id}"
        params = {"access_token": self.access_token}

        try:
            response = requests.delete(endpoint, params=params)
            response.raise_for_status()
            logger.info("Deleted Instagram media %s", media_id)
            return True
        except requests.exceptions.RequestException as e:
            logger.error("Failed to delete Instagram media %s: %s", media_id, e)
            return False
