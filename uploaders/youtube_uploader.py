"""YouTube uploader for podcast episodes and clips."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import Config


class YouTubeUploader:
    """Handle YouTube uploads with OAuth2 authentication."""

    # YouTube API scopes
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    # Token storage path
    TOKEN_PATH = Config.BASE_DIR / 'credentials' / 'youtube_token.pickle'
    CREDENTIALS_PATH = Config.BASE_DIR / 'credentials' / 'youtube_credentials.json'

    def __init__(self):
        """Initialize YouTube uploader."""
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        creds = None

        # Create credentials directory if it doesn't exist
        self.TOKEN_PATH.parent.mkdir(exist_ok=True)

        # Load existing credentials from token file
        if self.TOKEN_PATH.exists():
            with open(self.TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Try to refresh expired credentials
                print("[INFO] Refreshing YouTube credentials...")
                try:
                    creds.refresh(Request())
                    print("[OK] Token refreshed successfully!")
                except Exception as refresh_error:
                    print(f"[WARNING] Token refresh failed: {refresh_error}")
                    print("[INFO] Will re-authenticate with OAuth flow...")
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

                print("[INFO] Starting YouTube OAuth2 authentication...")
                print("[INFO] A browser window will open for authorization")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.CREDENTIALS_PATH), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(self.TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)

            print("[OK] YouTube authentication successful!")

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=creds)

    def upload_episode(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "22",  # People & Blogs
        privacy_status: str = "public",
        made_for_kids: bool = False,
        thumbnail_path: Optional[str] = None
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
            print("[ERROR] YouTube API not authenticated")
            return None

        video_path = Path(video_path)
        if not video_path.exists():
            print(f"[ERROR] Video file not found: {video_path}")
            return None

        print(f"[INFO] Uploading episode to YouTube: {video_path.name}")
        print(f"[INFO] Title: {title}")
        print(f"[INFO] Privacy: {privacy_status}")

        # Prepare video metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube max title length
                'description': description[:5000],  # YouTube max description length
                'tags': tags or [],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': made_for_kids
            }
        }

        # Prepare media upload
        media = MediaFileUpload(
            str(video_path),
            chunksize=10*1024*1024,  # 10 MB chunks
            resumable=True
        )

        try:
            # Upload video
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )

            print("[INFO] Upload started...")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"[INFO] Upload progress: {progress}%")

            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"[OK] Upload complete!")
            print(f"[OK] Video ID: {video_id}")
            print(f"[OK] Video URL: {video_url}")

            # Upload thumbnail if provided
            if thumbnail_path and Path(thumbnail_path).exists():
                self._upload_thumbnail(video_id, thumbnail_path)

            return {
                'video_id': video_id,
                'video_url': video_url,
                'title': title,
                'status': 'success'
            }

        except HttpError as e:
            print(f"[ERROR] YouTube upload failed: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error during upload: {e}")
            return None

    def upload_short(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        privacy_status: str = "public"
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
        if '#Shorts' not in title and '#Shorts' not in description:
            title = f"{title} #Shorts"

        # Use same upload method as regular video
        # YouTube automatically detects Shorts based on duration and aspect ratio
        return self.upload_episode(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            category_id="22"  # People & Blogs
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
            print(f"[WARNING] Thumbnail not found: {thumbnail_path}")
            return False

        try:
            print(f"[INFO] Uploading thumbnail for video {video_id}")

            media = MediaFileUpload(
                str(thumbnail_path),
                mimetype='image/jpeg',
                resumable=True
            )

            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            )

            response = request.execute()
            print("[OK] Thumbnail uploaded successfully")
            return True

        except HttpError as e:
            print(f"[ERROR] Failed to upload thumbnail: {e}")
            return False

    def update_video_metadata(
        self,
        video_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list] = None
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
            video = self.youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if not video['items']:
                print(f"[ERROR] Video not found: {video_id}")
                return False

            snippet = video['items'][0]['snippet']

            # Update with new values if provided
            if title:
                snippet['title'] = title[:100]
            if description:
                snippet['description'] = description[:5000]
            if tags:
                snippet['tags'] = tags

            # Update video
            self.youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            ).execute()

            print(f"[OK] Updated metadata for video {video_id}")
            return True

        except HttpError as e:
            print(f"[ERROR] Failed to update video: {e}")
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
            'daily_limit': 10000,  # Default quota (units per day)
            'upload_cost': 1600,    # Cost per video upload
            'note': 'Check Google Cloud Console for actual usage'
        }


def create_episode_metadata(
    episode_number: int,
    episode_summary: str,
    social_captions: Dict[str, str],
    clip_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create YouTube metadata from episode analysis.

    Args:
        episode_number: Episode number
        episode_summary: Summary from Claude analysis
        social_captions: Social media captions from Claude
        clip_info: Information about the clip (for Shorts)

    Returns:
        Dictionary with title, description, and tags
    """
    podcast_name = Config.PODCAST_NAME

    if clip_info:
        # For Shorts/clips
        title = f"{podcast_name} - Ep {episode_number}: {clip_info.get('title', 'Clip')}"
        description = f"{clip_info.get('description', '')}\n\n"
        description += f"From Episode {episode_number} of {podcast_name}\n\n"
        description += social_captions.get('youtube', episode_summary)
    else:
        # For full episodes
        title = f"{podcast_name} - Episode {episode_number}"
        description = f"{episode_summary}\n\n"
        description += social_captions.get('youtube', '')

    # Common tags
    tags = [
        podcast_name,
        'podcast',
        'comedy',
        'humor',
        f'episode{episode_number}',
        'fake problems'
    ]

    return {
        'title': title,
        'description': description,
        'tags': tags
    }
