"""TikTok uploader for podcast clips."""

import requests
import time
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config


class TikTokUploader:
    """Handle TikTok video uploads via Content Posting API."""

    # TikTok API endpoints
    API_BASE = "https://open.tiktokapis.com/v2"

    def __init__(self):
        """Initialize TikTok uploader."""
        client_key = Config.TIKTOK_CLIENT_KEY
        client_secret = Config.TIKTOK_CLIENT_SECRET
        access_token = Config.TIKTOK_ACCESS_TOKEN
        self.functional = (
            bool(client_key)
            and client_key != "your_tiktok_client_key_here"
            and bool(access_token)
            and access_token != "your_tiktok_access_token_here"
        )
        if not self.functional:
            return
        self.client_key = client_key
        self.client_secret = client_secret
        self.access_token = access_token

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: Optional[str] = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False,
        video_cover_timestamp_ms: int = 1000,
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a video to TikTok.

        TikTok video requirements:
        - Duration: 3 seconds to 10 minutes
        - Resolution: Minimum 720p, recommended 1080p
        - Aspect ratio: 9:16 (vertical) recommended
        - File size: Maximum 4GB
        - Format: MP4 or WebM

        Args:
            video_path: Path to the video file
            title: Video title (max 150 characters)
            description: Video description/caption
            privacy_level: "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"
            disable_duet: Disable duet feature
            disable_stitch: Disable stitch feature
            disable_comment: Disable comments
            video_cover_timestamp_ms: Timestamp for auto-generated cover (milliseconds)

        Returns:
            Dictionary with video info, or None if upload failed
        """
        if not self.functional:
            return None
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"[ERROR] Video file not found: {video_path}")
            return None

        print(f"[INFO] Uploading video to TikTok: {video_path.name}")
        print(f"[INFO] Title: {title}")

        # Step 1: Initialize upload (all post metadata is sent here)
        upload_url, publish_id = self._initialize_upload(
            video_path,
            title=title,
            privacy_level=privacy_level,
            disable_duet=disable_duet,
            disable_stitch=disable_stitch,
            disable_comment=disable_comment,
            video_cover_timestamp_ms=video_cover_timestamp_ms,
        )
        if not upload_url:
            print("[ERROR] Failed to initialize upload")
            return None

        # Step 2: Upload video file
        if not self._upload_video_file(upload_url, video_path):
            print("[ERROR] Failed to upload video file")
            return None

        # Step 3: Wait for TikTok to publish the video
        result = self._wait_for_publish(publish_id)

        if result:
            print("[OK] Video uploaded successfully!")
            print(f"[OK] Publish ID: {result['publish_id']}")
            if result.get("share_url"):
                print(f"[OK] Video URL: {result['share_url']}")

        return result

    def _initialize_upload(
        self,
        video_path: Path,
        title: str = "",
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False,
        video_cover_timestamp_ms: int = 1000,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Initialize a video upload session.

        TikTok's Content Posting API only accepts post metadata at init time,
        so all post info must be provided here.

        Args:
            video_path: Path to video file
            title: Video title (max 150 characters)
            privacy_level: "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"
            disable_duet: Disable duet feature
            disable_stitch: Disable stitch feature
            disable_comment: Disable comments
            video_cover_timestamp_ms: Timestamp for auto-generated cover (milliseconds)

        Returns:
            Tuple of (upload_url, publish_id) or (None, None) if failed
        """
        endpoint = f"{self.API_BASE}/post/publish/video/init/"

        # Get video file size
        file_size = video_path.stat().st_size
        chunk_size = min(file_size, 64 * 1024 * 1024)  # 64MB max chunk size
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "post_info": {
                "title": title[:150],
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_comment": disable_comment,
                "disable_stitch": disable_stitch,
                "video_cover_timestamp_ms": video_cover_timestamp_ms,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                error_code = data["error"].get("code")
                error_msg = data["error"].get("message")
                print(f"[ERROR] TikTok API error: {error_code} - {error_msg}")
                return None, None

            upload_url = data["data"].get("upload_url")
            publish_id = data["data"].get("publish_id")

            print(f"[OK] Upload initialized: {publish_id}")
            return upload_url, publish_id

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to initialize upload: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"[ERROR] Response: {e.response.text}")
            return None, None

    def _upload_video_file(self, upload_url: str, video_path: Path) -> bool:
        """
        Upload video file to TikTok's servers.

        Args:
            upload_url: Upload URL from initialization
            video_path: Path to video file

        Returns:
            True if successful, False otherwise
        """
        try:
            print("[INFO] Uploading video file...")

            with open(video_path, "rb") as video_file:
                video_data = video_file.read()

            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(len(video_data)),
            }

            response = requests.put(upload_url, headers=headers, data=video_data)
            response.raise_for_status()

            print("[OK] Video file uploaded")
            return True

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to upload video file: {e}")
            return False

    def _wait_for_publish(self, publish_id: str) -> Optional[Dict[str, Any]]:
        """
        Poll TikTok until the video is published or fails.

        Args:
            publish_id: Publish ID from initialization

        Returns:
            Dictionary with video info, or None if failed
        """
        endpoint = f"{self.API_BASE}/post/publish/status/fetch/"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Wait for processing (TikTok processes asynchronously)
        print("[INFO] Waiting for TikTok to process the video...")
        time.sleep(5)  # Initial wait

        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                payload = {"publish_id": publish_id}

                response = requests.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                if data.get("error"):
                    error_code = data["error"].get("code")
                    error_msg = data["error"].get("message")
                    print(f"[ERROR] TikTok API error: {error_code} - {error_msg}")
                    return None

                status = data["data"].get("status")

                if status == "PUBLISH_COMPLETE":
                    print("[OK] Video published successfully")
                    return {
                        "publish_id": publish_id,
                        "status": status,
                        "share_url": data["data"].get("share_url"),
                        "video_id": data["data"].get("video_id"),
                    }
                elif status == "FAILED":
                    fail_reason = data["data"].get("fail_reason")
                    print(f"[ERROR] Publishing failed: {fail_reason}")
                    return None
                else:
                    print(
                        f"[INFO] Status: {status} (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(10)

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Failed to check publish status: {e}")
                return None

        print("[ERROR] Publishing timed out")
        return None

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the authenticated user.

        Returns:
            Dictionary with user information
        """
        if not self.functional:
            return None
        endpoint = f"{self.API_BASE}/user/info/"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "fields": [
                "open_id",
                "union_id",
                "avatar_url",
                "display_name",
                "follower_count",
                "following_count",
                "video_count",
            ]
        }

        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("error"):
                print(f"[ERROR] Failed to get user info: {data['error']}")
                return None

            return data.get("data", {}).get("user")

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to get user info: {e}")
            return None


def create_tiktok_caption(
    clip_title: str,
    social_caption: str = "",
    hashtags: Optional[list] = None,
    hook_caption: Optional[str] = None,
) -> str:
    """
    Create a TikTok video title/caption (max 150 characters).

    TikTok's title field is limited to 150 characters, so we prioritize
    the clip title and a few key hashtags rather than trying to fit
    the full social caption.

    Args:
        clip_title: Title of the clip
        social_caption: Caption from Claude analysis (used as fallback)
        hashtags: Optional list of hashtags
        hook_caption: Optional hook line from AI (used as primary text if short)

    Returns:
        Formatted title string (max 150 chars)
    """
    if not hashtags:
        hashtags = ["podcast", "comedy", "fakeproblems", "fyp"]

    hashtag_str = " ".join(f"#{tag}" for tag in hashtags)

    # Use hook_caption as primary text if it's short enough
    primary_text = clip_title
    if hook_caption and len(hook_caption) < 80:
        primary_text = hook_caption

    # Try primary text + hashtags first
    caption = f"{primary_text} {hashtag_str}"
    if len(caption) <= 150:
        return caption

    # If too long, truncate primary text to fit hashtags
    max_title_len = 150 - len(hashtag_str) - 2  # 2 for space + ellipsis
    if max_title_len > 10:
        return f"{primary_text[:max_title_len]}… {hashtag_str}"

    # Last resort: just truncate the primary text
    return primary_text[:150]
