"""Instagram uploader for podcast clips as Reels."""

import time
import requests
from typing import Optional, Dict, Any

from config import Config
from logger import logger
from retry_utils import retry_with_backoff


class InstagramUploader:
    """Handle Instagram Reels uploads via Graph API."""

    # Instagram Graph API base URL
    API_BASE = "https://graph.facebook.com/v18.0"

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
        endpoint = f"{self.API_BASE}/{self.account_id}/media"

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
        endpoint = f"{self.API_BASE}/{self.account_id}/media_publish"
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
        endpoint = f"{self.API_BASE}/{self.account_id}"
        params = {
            "fields": "id,username,name,profile_picture_url,followers_count,media_count",
            "access_token": self.access_token,
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error("Failed to get account info: %s", e)
            return None
