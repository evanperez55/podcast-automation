"""Twitter/X uploader for podcast announcements and clips."""

import time
import tweepy
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import Config
from logger import logger
from retry_utils import retry_with_backoff

# Minimum interval between tweets (seconds) for rate limiting
_MIN_TWEET_INTERVAL = 2.0
_last_tweet_time = 0.0


def _rate_limit_wait():
    """Enforce minimum interval between tweets."""
    global _last_tweet_time
    now = time.time()
    elapsed = now - _last_tweet_time
    if elapsed < _MIN_TWEET_INTERVAL and _last_tweet_time > 0:
        wait = _MIN_TWEET_INTERVAL - elapsed
        logger.debug("Rate limit: waiting %.1fs before next tweet", wait)
        time.sleep(wait)
    _last_tweet_time = time.time()


class TwitterUploader:
    """Handle Twitter/X posts with media uploads."""

    def __init__(self):
        """Initialize Twitter uploader."""
        self.api_key = Config.TWITTER_API_KEY
        self.api_secret = Config.TWITTER_API_SECRET
        self.access_token = Config.TWITTER_ACCESS_TOKEN
        self.access_secret = Config.TWITTER_ACCESS_SECRET

        if not all(
            [self.api_key, self.api_secret, self.access_token, self.access_secret]
        ):
            raise ValueError(
                "Twitter API credentials not configured in .env file.\n"
                "Please follow the setup instructions:\n"
                "1. Apply for Twitter Developer access at https://developer.twitter.com\n"
                "2. Create a project and app\n"
                "3. Get API keys and access tokens\n"
                "4. Add credentials to .env file:\n"
                "   - TWITTER_API_KEY\n"
                "   - TWITTER_API_SECRET\n"
                "   - TWITTER_ACCESS_TOKEN\n"
                "   - TWITTER_ACCESS_SECRET\n\n"
                "Note: You need Elevated access for media uploads"
            )

        # Initialize Tweepy clients
        # API v1.1 for media uploads
        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret, self.access_token, self.access_secret
        )
        self.api_v1 = tweepy.API(auth)

        # API v2 for posting tweets
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret,
        )

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def post_tweet(
        self,
        text: str,
        media_paths: Optional[List[str]] = None,
        reply_to_tweet_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post a tweet with optional media.

        Twitter limits:
        - Text: 280 characters (4000 for Twitter Blue/Premium)
        - Media: Up to 4 images or 1 video per tweet
        - Video: Max 512MB, up to 2 minutes 20 seconds

        Args:
            text: Tweet text (max 280 characters)
            media_paths: Optional list of paths to media files (images or videos)
            reply_to_tweet_id: Optional tweet ID to reply to

        Returns:
            Dictionary with tweet info, or None if post failed
        """
        _rate_limit_wait()
        logger.info("Posting to Twitter/X")
        # Handle Windows console encoding issues
        try:
            logger.info("Text: %s...", text[:100])
        except UnicodeEncodeError:
            logger.info(
                "Text: %s...", text[:100].encode("ascii", "replace").decode("ascii")
            )

        media_ids = []

        # Upload media if provided
        if media_paths:
            media_ids = self._upload_media(media_paths)
            if not media_ids:
                logger.error("Failed to upload media")
                return None

        try:
            # Post tweet with v2 API
            response = self.client.create_tweet(
                text=text[:280],  # Enforce character limit
                media_ids=media_ids if media_ids else None,
                in_reply_to_tweet_id=reply_to_tweet_id,
            )

            tweet_id = response.data["id"]
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"

            logger.info("Tweet posted successfully!")
            logger.info("Tweet ID: %s", tweet_id)
            logger.info("Tweet URL: %s", tweet_url)

            return {
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "text": text,
                "media_count": len(media_ids),
                "status": "success",
            }

        except tweepy.TweepyException as e:
            logger.error("Failed to post tweet: %s", e)
            return None

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def _upload_media(self, media_paths: List[str]) -> List[str]:
        """
        Upload media files to Twitter.

        Args:
            media_paths: List of paths to media files

        Returns:
            List of media IDs
        """
        media_ids = []

        for media_path in media_paths[:4]:  # Twitter max 4 media items
            media_path = Path(media_path)
            if not media_path.exists():
                logger.warning("Media file not found: %s", media_path)
                continue

            try:
                logger.info("Uploading media: %s", media_path.name)

                # Determine media category
                if media_path.suffix.lower() in [".mp4", ".mov", ".avi"]:
                    media_category = "tweet_video"
                else:
                    media_category = "tweet_image"

                # Upload media using v1.1 API
                media = self.api_v1.media_upload(
                    filename=str(media_path), media_category=media_category
                )

                media_ids.append(media.media_id_string)
                logger.info("Media uploaded: %s", media.media_id_string)

            except tweepy.TweepyException as e:
                logger.error("Failed to upload %s: %s", media_path.name, e)
                continue

        return media_ids

    def post_thread(
        self, tweets: List[str], media_paths: Optional[List[List[str]]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Post a Twitter thread.

        Args:
            tweets: List of tweet texts
            media_paths: Optional list of media paths for each tweet

        Returns:
            List of tweet info dictionaries, or None if thread failed
        """
        logger.info("Posting Twitter thread (%s tweets)", len(tweets))

        thread_results = []
        previous_tweet_id = None

        for i, tweet_text in enumerate(tweets):
            # Get media for this tweet if available
            tweet_media = None
            if media_paths and i < len(media_paths):
                tweet_media = media_paths[i]

            # Post tweet
            result = self.post_tweet(
                text=tweet_text,
                media_paths=tweet_media,
                reply_to_tweet_id=previous_tweet_id,
            )

            if not result:
                logger.error("Failed to post tweet %s in thread", i + 1)
                return None

            thread_results.append(result)
            previous_tweet_id = result["tweet_id"]

        logger.info("Thread posted successfully!")
        return thread_results

    def post_episode_announcement(
        self,
        episode_number: int,
        episode_summary: str,
        youtube_url: Optional[str] = None,
        spotify_url: Optional[str] = None,
        clip_youtube_urls: Optional[List[Dict[str, str]]] = None,
        twitter_caption: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Post an episode announcement as a thread.

        Args:
            episode_number: Episode number
            episode_summary: Summary from Claude
            youtube_url: Optional YouTube URL for full episode
            spotify_url: Optional Spotify URL
            clip_youtube_urls: Optional list of dicts with 'title' and 'url' for each clip
            twitter_caption: Optional AI-generated tweet text (used instead of template)

        Returns:
            List of tweet info dictionaries, or None if failed
        """
        if twitter_caption:
            # Use AI-generated caption, append YouTube URL if space allows
            # Twitter wraps URLs to 23 chars via t.co, so use that for length calc
            main_tweet = twitter_caption
            if youtube_url:
                url_display_len = 23  # t.co wrapped length
                caption_with_url_len = len(twitter_caption) + 2 + url_display_len
                if caption_with_url_len <= 280:
                    main_tweet = f"{twitter_caption}\n\n{youtube_url}"
                else:
                    # Trim caption to fit URL
                    max_caption_len = 280 - 2 - url_display_len
                    main_tweet = f"{twitter_caption[:max_caption_len]}\n\n{youtube_url}"
        else:
            # Fallback: hardcoded template
            main_tweet = (
                f"🎙️ New Episode Alert! 🎙️\n\n"
                f"Episode {episode_number} of {Config.PODCAST_NAME} is now live!\n\n"
                f"{episode_summary[:150]}"
            )
            if youtube_url:
                main_tweet += f"\n\n{youtube_url}"

        # Build thread
        tweets = [main_tweet]
        media_list = [None]

        # Add clip tweets as YouTube links (no video upload)
        if clip_youtube_urls:
            for clip in clip_youtube_urls[:3]:
                clip_tweet = f"🎬 {clip.get('title', 'Clip')}\n\n{clip['url']}"
                tweets.append(clip_tweet)
                media_list.append(None)

        return self.post_thread(tweets, media_list)

    def post_clip(
        self,
        caption: str,
        episode_number: int,
        youtube_url: Optional[str] = None,
        video_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Post a single clip with caption and YouTube link.

        Args:
            caption: Tweet caption
            episode_number: Episode number
            youtube_url: YouTube Shorts URL to link to
            video_path: Optional path to video (fallback if no YouTube URL)

        Returns:
            Dictionary with tweet info, or None if post failed
        """
        suffix = f"\n\n🎙️ From Episode {episode_number} of {Config.PODCAST_NAME}"
        if youtube_url:
            suffix += f"\n\n{youtube_url}"
            # Twitter wraps URLs to 23 chars via t.co
            suffix_display_len = len(suffix) - len(youtube_url) + 23
        else:
            suffix_display_len = len(suffix)

        max_caption_len = 280 - suffix_display_len
        full_caption = f"{caption[:max_caption_len]}{suffix}"

        return self.post_tweet(
            text=full_caption,
            media_paths=[video_path] if video_path and not youtube_url else None,
        )

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the authenticated user.

        Returns:
            Dictionary with user information
        """
        try:
            user = self.client.get_me(
                user_fields=["description", "created_at", "public_metrics"]
            )

            if user.data:
                return {
                    "id": user.data.id,
                    "username": user.data.username,
                    "name": user.data.name,
                    "description": user.data.description,
                    "followers": user.data.public_metrics["followers_count"],
                    "following": user.data.public_metrics["following_count"],
                    "tweets": user.data.public_metrics["tweet_count"],
                }

            return None

        except tweepy.TweepyException as e:
            logger.error("Failed to get user info: %s", e)
            return None

    def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet.

        Args:
            tweet_id: ID of tweet to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_tweet(tweet_id)
            logger.info("Deleted tweet %s", tweet_id)
            return True

        except tweepy.TweepyException as e:
            logger.error("Failed to delete tweet: %s", e)
            return False


def create_twitter_caption(
    clip_title: str, social_caption: str, hashtags: Optional[list] = None
) -> str:
    """
    Create a Twitter caption within character limits.

    Args:
        clip_title: Title of the clip
        social_caption: Caption from Claude analysis
        hashtags: Optional list of hashtags

    Returns:
        Formatted caption string (max 280 characters)
    """
    # Default hashtags if none provided
    if not hashtags:
        hashtags = ["podcast", "comedy", "fakeproblems"]

    # Build caption
    caption = f"{clip_title}\n\n{social_caption}"

    # Add hashtags if space allows
    hashtag_str = " ".join(f"#{tag}" for tag in hashtags)
    full_caption = f"{caption}\n\n{hashtag_str}"

    # Trim if too long
    if len(full_caption) > 280:
        # Try without hashtags
        if len(caption) <= 280:
            return caption[:280]
        # Trim caption
        return caption[:277] + "..."

    return full_caption
