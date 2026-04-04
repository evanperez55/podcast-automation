"""YouTube uploader for podcast episodes and clips."""

import time
import ssl
from pathlib import Path
from typing import Optional, Dict, Any
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import Config
from logger import logger
from retry_utils import retry_with_backoff


class YouTubeUploader:
    """Handle YouTube uploads with OAuth2 authentication."""

    # YouTube API scopes
    SCOPES = ["https://www.googleapis.com/auth/youtube"]

    # YouTube SEO: descriptions of 1000+ chars are recommended for discoverability
    YOUTUBE_SEO_MIN_DESCRIPTION_LENGTH = 200

    # Default token storage path
    TOKEN_PATH = Config.BASE_DIR / "credentials" / "youtube_token.pickle"
    CREDENTIALS_PATH = Config.BASE_DIR / "credentials" / "youtube_credentials.json"

    def __init__(self, token_path=None):
        """Initialize YouTube uploader.

        Args:
            token_path: Optional path to YouTube OAuth token pickle file.
                If provided, overrides the default TOKEN_PATH for per-client support.
        """
        if token_path:
            self.TOKEN_PATH = Path(token_path)
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        creds = None

        # Create credentials directory if it doesn't exist
        self.TOKEN_PATH.parent.mkdir(exist_ok=True)

        # Load existing credentials from token file
        if self.TOKEN_PATH.exists():
            with open(self.TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Try to refresh expired credentials
                logger.info("Refreshing YouTube credentials...")
                try:
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully!")
                except Exception as refresh_error:
                    logger.warning("Token refresh failed: %s", refresh_error)
                    logger.info("Will re-authenticate with OAuth flow...")
                    creds = None  # Force re-authentication

            if not creds or not creds.valid:
                # Run OAuth flow for new credentials
                if not self.CREDENTIALS_PATH.exists():
                    raise FileNotFoundError(
                        f"YouTube credentials file not found: {self.CREDENTIALS_PATH}\n"
                        f"Please follow the setup instructions:\n"
                        f"1. Go to https://console.cloud.google.com\n"
                        f"2. Create a project and enable YouTube Data API v3\n"
                        f"3. Create OAuth 2.0 credentials (Desktop app)\n"
                        f"4. Download the credentials JSON file\n"
                        f"5. Save it as: {self.CREDENTIALS_PATH}"
                    )

                logger.info("Starting YouTube OAuth2 authentication...")
                logger.info("A browser window will open for authorization")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.CREDENTIALS_PATH), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(self.TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)

            logger.info("YouTube authentication successful!")

        # Build YouTube API client
        self.youtube = build("youtube", "v3", credentials=creds)

    @staticmethod
    def _append_hashtags(description: str, tags: list) -> str:
        """Append hashtags to description if not already present.

        Args:
            description: Video description text.
            tags: List of tag strings to convert to hashtags.

        Returns:
            Description with hashtags appended (if none were present).
        """
        if not tags or "#" in description:
            return description
        hashtags = " ".join(f"#{tag.replace(' ', '')}" for tag in tags[:15])
        return f"{description.rstrip()}\n\n{hashtags}"

    def _ensure_min_description_length(
        self, description: str, title: str, episode_info: str = ""
    ) -> str:
        """Pad description to YouTube SEO minimum length if needed.

        YouTube SEO: descriptions should be at least 200 chars; 1000+ chars
        are recommended for optimal discoverability.

        Args:
            description: Current description text.
            title: Video title for padding context.
            episode_info: Additional episode info to pad with.

        Returns:
            Description padded to at least YOUTUBE_SEO_MIN_DESCRIPTION_LENGTH chars.
        """
        if len(description) >= self.YOUTUBE_SEO_MIN_DESCRIPTION_LENGTH:
            return description
        padding = f"\n\n{title}"
        if episode_info:
            padding += f" | {episode_info}"
        padding += f" | {Config.PODCAST_NAME}"
        description = description.rstrip() + padding
        return description

    def upload_episode(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "public",
        made_for_kids: bool = False,
        thumbnail_path: Optional[str] = None,
        publish_at: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a full episode to YouTube.

        Args:
            video_path: Path to the video file
            title: Video title (max 100 characters)
            description: Video description (max 5000 characters)
            tags: List of tags (max 500 characters total)
            category_id: YouTube category ID (default: 22 = People & Blogs)
            privacy_status: "public", "private", or "unlisted"
            made_for_kids: Whether the video is made for kids
            thumbnail_path: Optional path to custom thumbnail image

        Returns:
            Dictionary with video ID and URL, or None if upload failed
        """
        if not self.youtube:
            logger.error("YouTube API not authenticated")
            return None

        video_path = Path(video_path)
        if not video_path.exists():
            logger.error("Video file not found: %s", video_path)
            return None

        logger.info("Uploading episode to YouTube: %s", video_path.name)
        logger.info("Title: %s", title)
        logger.info("Privacy: %s", privacy_status)

        # SEO: append hashtags and ensure minimum description length
        description = self._append_hashtags(description, tags or [])
        description = self._ensure_min_description_length(description, title)

        # Prepare video metadata
        body = {
            "snippet": {
                "title": title[:100],  # YouTube max title length
                "description": description[:5000],  # YouTube max description length
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Add scheduled publishing if publish_at is provided
        if publish_at:
            body["status"]["publishAt"] = publish_at
            logger.info("Scheduled to publish at: %s", publish_at)

        # Prepare media upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
            resumable=True,
        )

        try:
            # Upload video
            request = self.youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            )

            logger.info("Upload started...")
            response = None
            retry_count = 0
            max_retries = 5
            while response is None:
                try:
                    status, response = request.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info("Upload progress: %s%%", progress)
                    retry_count = 0  # Reset on success
                except ssl.SSLError as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error("SSL error after %s retries: %s", max_retries, e)
                        raise
                    wait_time = 2**retry_count
                    logger.warning(
                        "SSL error, retrying in %ss (attempt %s/%s)...",
                        wait_time,
                        retry_count,
                        max_retries,
                    )
                    time.sleep(wait_time)
                except Exception as e:
                    if "EOF occurred" in str(e) or "ssl" in str(e).lower():
                        retry_count += 1
                        if retry_count > max_retries:
                            raise
                        wait_time = 2**retry_count
                        logger.warning(
                            "Connection error, retrying in %ss (attempt %s/%s)...",
                            wait_time,
                            retry_count,
                            max_retries,
                        )
                        time.sleep(wait_time)
                    else:
                        raise

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info("Upload complete!")
            logger.info("Video ID: %s", video_id)
            logger.info("Video URL: %s", video_url)

            # Upload thumbnail if provided
            if thumbnail_path and Path(thumbnail_path).exists():
                self._upload_thumbnail(video_id, thumbnail_path)

            return {
                "video_id": video_id,
                "video_url": video_url,
                "title": title,
                "status": "success",
            }

        except HttpError as e:
            logger.error("YouTube upload failed: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error during upload: %s", e)
            return None

    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        privacy_status: str = "public",
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a clip as a YouTube Short.

        YouTube Shorts requirements:
        - Video must be 60 seconds or less
        - Vertical (9:16) or square (1:1) aspect ratio recommended
        - Title should include #Shorts

        Args:
            video_path: Path to the video clip
            title: Video title (will append #Shorts if not present)
            description: Video description
            tags: List of tags
            privacy_status: "public", "private", or "unlisted"

        Returns:
            Dictionary with video ID and URL, or None if upload failed
        """
        # Ensure #Shorts is in the title or description
        if "#Shorts" not in title and "#Shorts" not in description:
            title = f"{title} #Shorts"

        # SEO: append hashtags and ensure minimum description length
        description = self._append_hashtags(description, tags or [])
        description = self._ensure_min_description_length(description, title)

        # Use same upload method as regular video
        # YouTube automatically detects Shorts based on duration and aspect ratio
        return self.upload_episode(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            category_id="22",  # People & Blogs
        )

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def _upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """
        Upload a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image

        Returns:
            True if successful, False otherwise
        """
        thumbnail_path = Path(thumbnail_path)
        if not thumbnail_path.exists():
            logger.warning("Thumbnail not found: %s", thumbnail_path)
            return False

        try:
            logger.info("Uploading thumbnail for video %s", video_id)

            media = MediaFileUpload(
                str(thumbnail_path), mimetype="image/jpeg", resumable=True
            )

            request = self.youtube.thumbnails().set(videoId=video_id, media_body=media)

            request.execute()
            logger.info("Thumbnail uploaded successfully")
            return True

        except HttpError as e:
            logger.error("Failed to upload thumbnail: %s", e)
            return False

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> bool:
        """
        Update metadata for an existing video.

        Args:
            video_id: YouTube video ID
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current video details
            video = self.youtube.videos().list(part="snippet", id=video_id).execute()

            if not video["items"]:
                logger.error("Video not found: %s", video_id)
                return False

            snippet = video["items"][0]["snippet"]

            # Update with new values if provided
            if title:
                snippet["title"] = title[:100]
            if description:
                snippet["description"] = description[:5000]
            if tags:
                snippet["tags"] = tags

            # Update video
            self.youtube.videos().update(
                part="snippet", body={"id": video_id, "snippet": snippet}
            ).execute()

            logger.info("Updated metadata for video %s", video_id)
            return True

        except HttpError as e:
            logger.error("Failed to update video: %s", e)
            return False

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def set_video_privacy(
        self,
        video_id: str,
        privacy_status: str = "public",
    ) -> bool:
        """
        Change the privacy status of a video.

        Args:
            video_id: YouTube video ID
            privacy_status: "public", "private", or "unlisted"

        Returns:
            True if successful, False otherwise
        """
        if not self.youtube:
            logger.error("YouTube API not authenticated")
            return False

        try:
            video = self.youtube.videos().list(part="status", id=video_id).execute()

            if not video["items"]:
                logger.error("Video not found: %s", video_id)
                return False

            self.youtube.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {"privacyStatus": privacy_status},
                },
            ).execute()

            logger.info("Set video %s privacy to %s", video_id, privacy_status)
            return True

        except HttpError as e:
            logger.error("Failed to set privacy for %s: %s", video_id, e)
            return False

    def delete_video(self, video_id: str) -> bool:
        """Delete a video from YouTube.

        Args:
            video_id: YouTube video ID to delete.

        Returns:
            True if successful, False otherwise.
        """
        if not self.youtube:
            logger.error("YouTube API not authenticated")
            return False

        try:
            self.youtube.videos().delete(id=video_id).execute()
            logger.info("Deleted YouTube video %s", video_id)
            return True
        except HttpError as e:
            logger.error("Failed to delete video %s: %s", video_id, e)
            return False

    def get_upload_quota_usage(self) -> Dict[str, Any]:
        """
        Get information about API quota usage.

        Returns:
            Dictionary with quota information
        """
        # Note: Quota is tracked per project in Google Cloud Console
        # This is a placeholder for quota information
        return {
            "daily_limit": 10000,  # Default quota (units per day)
            "upload_cost": 1600,  # Cost per video upload
            "note": "Check Google Cloud Console for actual usage",
        }


def _format_chapters_for_youtube(chapters: list) -> str:
    """Format chapter markers for YouTube description.

    YouTube requires at least 3 chapters, and the first must start at 0:00.

    Args:
        chapters: List of chapter dicts with 'start_timestamp' and 'title'

    Returns:
        Formatted chapters string, or empty string if requirements not met
    """
    if not chapters or len(chapters) < 3:
        return ""

    # Ensure first chapter starts at 0:00
    first = chapters[0]
    first_seconds = first.get("start_seconds", 0)
    if first_seconds != 0:
        return ""

    lines = []
    for ch in chapters:
        ts = ch.get("start_timestamp", "00:00:00")
        # Convert HH:MM:SS to M:SS or H:MM:SS for YouTube display
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), parts[2].split(".")[0]
            if h > 0:
                lines.append(f"{h}:{m:02d}:{s} {ch.get('title', '')}")
            else:
                lines.append(f"{m}:{s} {ch.get('title', '')}")
        else:
            lines.append(f"{ts} {ch.get('title', '')}")

    return "\n".join(lines)


def create_episode_metadata(
    episode_number: int,
    episode_summary: str,
    social_captions: Dict[str, str],
    clip_info: Optional[Dict[str, Any]] = None,
    show_notes: Optional[str] = None,
    chapters: Optional[list] = None,
    full_episode_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create YouTube metadata from episode analysis.

    Args:
        episode_number: Episode number
        episode_summary: Summary from Claude analysis
        social_captions: Social media captions from Claude
        clip_info: Information about the clip (for Shorts)
        show_notes: Detailed show notes (used for full episode description)
        chapters: List of chapter marker dicts (used for full episode description)
        full_episode_url: URL to the full episode on YouTube (for Shorts descriptions)

    Returns:
        Dictionary with title, description, and tags
    """
    podcast_name = Config.PODCAST_NAME

    if clip_info:
        # For Shorts/clips
        title = f"{clip_info.get('suggested_title', clip_info.get('title', f'Episode #{episode_number} Clip'))}"
        hook = clip_info.get("hook_caption", "")
        description = f"{hook}\n\n" if hook else ""
        description += f"{clip_info.get('description', '')}\n\n"
        description += f"From Episode #{episode_number} of {podcast_name}\n"
        if full_episode_url:
            description += f"Watch the full episode and find more: {full_episode_url}\n\n"
        else:
            description += "Find all episodes: youtube.com/@fakeproblemspodcast\n\n"
        description += social_captions.get("youtube", episode_summary)
    else:
        # For full episodes
        title = f"Episode #{episode_number}"
        # Use show_notes if available, otherwise fall back to episode_summary
        description = f"{show_notes or episode_summary}\n\n"
        description += social_captions.get("youtube", "")

        # Append YouTube chapters if available
        if chapters:
            chapters_text = _format_chapters_for_youtube(chapters)
            if chapters_text:
                description += f"\n\nChapters:\n{chapters_text}"

    # Common tags
    tags = [
        podcast_name,
        "podcast",
        "comedy",
        "humor",
        f"episode{episode_number}",
        "fake problems",
    ]

    return {"title": title, "description": description, "tags": tags}
