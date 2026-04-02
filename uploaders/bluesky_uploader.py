"""Bluesky uploader for podcast announcements and clips."""

import requests
from typing import Optional, Dict, Any, List

from config import Config
from logger import logger
from retry_utils import retry_with_backoff


class BlueskyUploader:
    """Handle Bluesky posts via the AT Protocol API."""

    API_BASE = "https://bsky.social/xrpc"

    def __init__(self):
        """Initialize Bluesky uploader."""
        self.handle = Config.BLUESKY_HANDLE
        self.app_password = Config.BLUESKY_APP_PASSWORD

        if not self.handle or not self.app_password:
            raise ValueError(
                "Bluesky credentials not configured in .env file.\n"
                "Setup instructions:\n"
                "1. Go to https://bsky.app/settings/app-passwords\n"
                "2. Create an app password\n"
                "3. Add to .env:\n"
                "   - BLUESKY_HANDLE=yourname.bsky.social\n"
                "   - BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx"
            )

        self.session = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Bluesky AT Protocol."""
        try:
            response = requests.post(
                f"{self.API_BASE}/com.atproto.server.createSession",
                json={
                    "identifier": self.handle,
                    "password": self.app_password,
                },
                timeout=10,
            )
            response.raise_for_status()
            self.session = response.json()
            logger.info("Bluesky authentication successful")
        except requests.RequestException as e:
            logger.warning("Bluesky authentication failed: %s", e)
            self.session = None

    def _get_headers(self):
        """Get authorization headers."""
        if not self.session:
            return None
        return {"Authorization": f"Bearer {self.session['accessJwt']}"}

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def post(
        self,
        text: str,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        url_description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post to Bluesky.

        Bluesky limits:
        - Text: 300 characters (graphemes)

        Args:
            text: Post text (max 300 characters)
            url: Optional URL to embed as a link card
            url_title: Optional title for the link card
            url_description: Optional description for the link card

        Returns:
            Dictionary with post info, or None if failed
        """
        if not self.session:
            logger.error("Bluesky not authenticated")
            return None

        headers = self._get_headers()
        text = text[:300]

        # Build the record
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": _iso_now(),
        }

        # Add link facet if URL is in the text
        if url and url in text:
            start = text.index(url)
            record["facets"] = [
                {
                    "index": {
                        "byteStart": len(text[:start].encode("utf-8")),
                        "byteEnd": len(text[: start + len(url)].encode("utf-8")),
                    },
                    "features": [
                        {
                            "$type": "app.bsky.richtext.facet#link",
                            "uri": url,
                        }
                    ],
                }
            ]

        # Add external embed (link card) if URL provided but not in text
        if url and url not in text:
            record["embed"] = {
                "$type": "app.bsky.embed.external",
                "external": {
                    "uri": url,
                    "title": url_title or "",
                    "description": url_description or "",
                },
            }

        try:
            logger.info("Posting to Bluesky")
            try:
                logger.info("Text: %s...", text[:100])
            except UnicodeEncodeError:
                logger.info(
                    "Text: %s...",
                    text[:100].encode("ascii", "replace").decode("ascii"),
                )

            response = requests.post(
                f"{self.API_BASE}/com.atproto.repo.createRecord",
                headers=headers,
                json={
                    "repo": self.session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            post_uri = data.get("uri", "")
            # Extract rkey for URL construction
            rkey = post_uri.split("/")[-1] if "/" in post_uri else ""
            post_url = f"https://bsky.app/profile/{self.handle}/post/{rkey}"

            logger.info("Bluesky post successful!")
            logger.info("Post URL: %s", post_url)

            return {
                "post_uri": post_uri,
                "post_url": post_url,
                "text": text,
                "status": "success",
            }

        except requests.RequestException as e:
            logger.error("Failed to post to Bluesky: %s", e)
            return None

    def upload_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Upload an image blob to Bluesky.

        Args:
            image_path: Path to the image file (PNG/JPEG).

        Returns:
            Blob reference dict for embedding, or None on failure.
        """
        if not self.session:
            return None

        from pathlib import Path

        path = Path(image_path)
        if not path.exists():
            logger.warning("Image not found: %s", image_path)
            return None

        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"

        try:
            with open(path, "rb") as f:
                response = requests.post(
                    f"{self.API_BASE}/com.atproto.repo.uploadBlob",
                    headers={
                        "Authorization": f"Bearer {self.session['accessJwt']}",
                        "Content-Type": mime,
                    },
                    data=f.read(),
                    timeout=30,
                )
                response.raise_for_status()
                return response.json().get("blob")
        except requests.RequestException as e:
            logger.error("Failed to upload image to Bluesky: %s", e)
            return None

    def post_with_image(
        self,
        text: str,
        image_path: str,
        alt_text: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Post to Bluesky with an embedded image.

        Args:
            text: Post text (max 300 characters).
            image_path: Path to image file.
            alt_text: Alt text for the image.

        Returns:
            Dictionary with post info, or None if failed.
        """
        if not self.session:
            logger.error("Bluesky not authenticated")
            return None

        blob = self.upload_image(image_path)
        if not blob:
            return None

        text = text[:300]
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": _iso_now(),
            "embed": {
                "$type": "app.bsky.embed.images",
                "images": [
                    {
                        "alt": alt_text or text[:100],
                        "image": blob,
                    }
                ],
            },
        }

        try:
            logger.info("Posting to Bluesky with image")
            response = requests.post(
                f"{self.API_BASE}/com.atproto.repo.createRecord",
                headers=self._get_headers(),
                json={
                    "repo": self.session["did"],
                    "collection": "app.bsky.feed.post",
                    "record": record,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            post_uri = data.get("uri", "")
            rkey = post_uri.split("/")[-1] if "/" in post_uri else ""
            post_url = f"https://bsky.app/profile/{self.handle}/post/{rkey}"

            logger.info("Bluesky image post successful!")
            logger.info("Post URL: %s", post_url)

            return {
                "post_uri": post_uri,
                "post_url": post_url,
                "text": text,
                "status": "success",
            }

        except requests.RequestException as e:
            logger.error("Failed to post image to Bluesky: %s", e)
            return None

    def post_episode_announcement(
        self,
        episode_number: int,
        episode_summary: str,
        youtube_url: Optional[str] = None,
        clip_youtube_urls: Optional[List[Dict[str, str]]] = None,
        bluesky_caption: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post an episode announcement to Bluesky.

        Args:
            episode_number: Episode number
            episode_summary: Summary from AI analysis
            youtube_url: Optional YouTube URL for full episode
            clip_youtube_urls: Optional list of dicts with 'title' and 'url'
            bluesky_caption: Optional AI-generated caption
            hashtags: Optional list of hashtags

        Returns:
            Dictionary with post info, or None if failed
        """
        if bluesky_caption:
            text = bluesky_caption
        else:
            text = (
                f"New Episode! Episode {episode_number} "
                f"of {Config.PODCAST_NAME} is out!\n\n"
                f"{episode_summary[:200]}"
            )

        if hashtags:
            hashtag_line = " ".join(f"#{tag}" for tag in hashtags[:3])
            if len(text) + len(hashtag_line) + 2 <= 300:
                text = f"{text}\n\n{hashtag_line}"

        return self.post(
            text=text,
            url=youtube_url,
            url_title=f"Episode {episode_number}",
            url_description=episode_summary[:150] if episode_summary else None,
        )


def create_bluesky_caption(
    clip_title: str, social_caption: str, hashtags: Optional[list] = None
) -> str:
    """
    Create a Bluesky caption within character limits.

    Args:
        clip_title: Title of the clip
        social_caption: Caption from AI analysis
        hashtags: Optional list of hashtags

    Returns:
        Formatted caption string (max 300 characters)
    """
    if not hashtags:
        hashtags = ["podcast", "comedy"]

    caption = f"{clip_title}\n\n{social_caption}"
    hashtag_str = " ".join(f"#{tag}" for tag in hashtags)
    full_caption = f"{caption}\n\n{hashtag_str}"

    if len(full_caption) > 300:
        if len(caption) <= 300:
            return caption[:300]
        return caption[:297] + "..."

    return full_caption


def _iso_now():
    """Return current UTC time in ISO 8601 format."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
