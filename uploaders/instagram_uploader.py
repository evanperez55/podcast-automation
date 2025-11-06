"""Instagram uploader for podcast clips as Reels."""

import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config


class InstagramUploader:
    """Handle Instagram Reels uploads via Graph API."""

    # Instagram Graph API base URL
    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self):
        """Initialize Instagram uploader."""
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.account_id = Config.INSTAGRAM_ACCOUNT_ID

        if not self.access_token or self.access_token == 'your_instagram_access_token_here':
            raise ValueError(
                "Instagram access token not configured in .env file.\n"
                "Please follow the setup instructions:\n"
                "1. Create a Facebook App at https://developers.facebook.com\n"
                "2. Add Instagram Graph API product\n"
                "3. Get an Instagram Business Account access token\n"
                "4. Add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID to .env"
            )

        if not self.account_id or self.account_id == 'your_instagram_account_id_here':
            raise ValueError(
                "Instagram account ID not configured in .env file.\n"
                "Add INSTAGRAM_ACCOUNT_ID to .env"
            )

    def upload_reel(
        self,
        video_url: str,
        caption: str,
        share_to_feed: bool = True,
        cover_url: Optional[str] = None
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
        print(f"[INFO] Uploading Reel to Instagram")
        print(f"[INFO] Caption: {caption[:80]}...")

        # Step 1: Create Reel container
        container_id = self._create_reel_container(
            video_url=video_url,
            caption=caption,
            share_to_feed=share_to_feed,
            cover_url=cover_url
        )

        if not container_id:
            print("[ERROR] Failed to create Reel container")
            return None

        # Step 2: Wait for video to be processed
        print("[INFO] Waiting for Instagram to process the video...")
        if not self._wait_for_container_ready(container_id):
            print("[ERROR] Video processing failed or timed out")
            return None

        # Step 3: Publish the Reel
        result = self._publish_reel(container_id)

        if result:
            print(f"[OK] Reel uploaded successfully!")
            print(f"[OK] Reel ID: {result['id']}")
            if result.get('permalink'):
                print(f"[OK] Reel URL: {result['permalink']}")

        return result

    def _create_reel_container(
        self,
        video_url: str,
        caption: str,
        share_to_feed: bool,
        cover_url: Optional[str]
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
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption[:2200],  # Instagram max caption length
            'share_to_feed': share_to_feed,
            'access_token': self.access_token
        }

        if cover_url:
            params['cover_url'] = cover_url

        try:
            response = requests.post(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            container_id = data.get('id')
            print(f"[OK] Reel container created: {container_id}")
            return container_id

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to create Reel container: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] Response: {e.response.text}")
            return None

    def _wait_for_container_ready(
        self,
        container_id: str,
        max_wait: int = 300,
        check_interval: int = 5
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
        params = {
            'fields': 'status_code,status',
            'access_token': self.access_token
        }

        elapsed = 0
        while elapsed < max_wait:
            try:
                response = requests.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()

                status_code = data.get('status_code')
                status = data.get('status', 'UNKNOWN')

                if status_code == 'FINISHED':
                    print("[OK] Video processing complete")
                    return True
                elif status_code == 'ERROR':
                    print(f"[ERROR] Video processing failed: {status}")
                    return False
                elif status_code == 'IN_PROGRESS':
                    print(f"[INFO] Processing... ({elapsed}s elapsed)")
                else:
                    print(f"[INFO] Status: {status_code} ({elapsed}s elapsed)")

                time.sleep(check_interval)
                elapsed += check_interval

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Failed to check status: {e}")
                return False

        print(f"[ERROR] Processing timed out after {max_wait}s")
        return False

    def _publish_reel(self, container_id: str) -> Optional[Dict[str, Any]]:
        """
        Publish a processed Reel container.

        Args:
            container_id: Media container ID

        Returns:
            Dictionary with Reel ID and permalink, or None if failed
        """
        endpoint = f"{self.API_BASE}/{self.account_id}/media_publish"
        params = {
            'creation_id': container_id,
            'access_token': self.access_token
        }

        try:
            response = requests.post(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            reel_id = data.get('id')

            # Get permalink
            permalink = self._get_media_permalink(reel_id)

            return {
                'id': reel_id,
                'permalink': permalink,
                'status': 'success'
            }

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to publish Reel: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[ERROR] Response: {e.response.text}")
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
        params = {
            'fields': 'permalink',
            'access_token': self.access_token
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('permalink')

        except requests.exceptions.RequestException:
            return None

    def upload_reel_from_dropbox(
        self,
        dropbox_path: str,
        caption: str,
        share_to_feed: bool = True
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
        # Note: This requires Dropbox handler integration
        # For now, this is a placeholder that expects a direct link
        print("[INFO] To upload from Dropbox, you need to:")
        print("1. Get a public shared link for the video")
        print("2. Replace 'dl=0' with 'dl=1' in the URL")
        print("3. Use upload_reel() with that URL")

        return None

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the Instagram account.

        Returns:
            Dictionary with account information
        """
        endpoint = f"{self.API_BASE}/{self.account_id}"
        params = {
            'fields': 'id,username,name,profile_picture_url,followers_count,media_count',
            'access_token': self.access_token
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get account info: {e}")
            return None


def create_instagram_caption(
    episode_number: int,
    clip_title: str,
    social_caption: str,
    hashtags: Optional[list] = None
) -> str:
    """
    Create an Instagram Reel caption.

    Args:
        episode_number: Episode number
        clip_title: Title of the clip
        social_caption: Caption from Claude analysis
        hashtags: Optional list of hashtags

    Returns:
        Formatted caption string
    """
    caption = f"{clip_title}\n\n"
    caption += f"{social_caption}\n\n"
    caption += f"🎙️ From Episode {episode_number} of {Config.PODCAST_NAME}\n\n"

    # Default hashtags if none provided
    if not hashtags:
        hashtags = [
            'podcast',
            'comedy',
            'funny',
            'podcastclips',
            'fakeproblems',
            'humor',
            'reels',
            'podcastrecommendations'
        ]

    # Add hashtags
    caption += ' '.join(f'#{tag}' for tag in hashtags)

    return caption[:2200]  # Instagram max caption length
