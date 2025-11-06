"""Twitter/X uploader for podcast announcements and clips."""

import tweepy
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import Config


class TwitterUploader:
    """Handle Twitter/X posts with media uploads."""

    def __init__(self):
        """Initialize Twitter uploader."""
        self.api_key = Config.TWITTER_API_KEY
        self.api_secret = Config.TWITTER_API_SECRET
        self.access_token = Config.TWITTER_ACCESS_TOKEN
        self.access_secret = Config.TWITTER_ACCESS_SECRET

        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
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
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_secret
        )
        self.api_v1 = tweepy.API(auth)

        # API v2 for posting tweets
        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret
        )

    def post_tweet(
        self,
        text: str,
        media_paths: Optional[List[str]] = None,
        reply_to_tweet_id: Optional[str] = None
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
        print(f"[INFO] Posting to Twitter/X")
        print(f"[INFO] Text: {text[:100]}...")

        media_ids = []

        # Upload media if provided
        if media_paths:
            media_ids = self._upload_media(media_paths)
            if not media_ids:
                print("[ERROR] Failed to upload media")
                return None

        try:
            # Post tweet with v2 API
            response = self.client.create_tweet(
                text=text[:280],  # Enforce character limit
                media_ids=media_ids if media_ids else None,
                in_reply_to_tweet_id=reply_to_tweet_id
            )

            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"

            print(f"[OK] Tweet posted successfully!")
            print(f"[OK] Tweet ID: {tweet_id}")
            print(f"[OK] Tweet URL: {tweet_url}")

            return {
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'text': text,
                'media_count': len(media_ids),
                'status': 'success'
            }

        except tweepy.TweepyException as e:
            print(f"[ERROR] Failed to post tweet: {e}")
            return None

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
                print(f"[WARNING] Media file not found: {media_path}")
                continue

            try:
                print(f"[INFO] Uploading media: {media_path.name}")

                # Determine media category
                if media_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
                    media_category = 'tweet_video'
                else:
                    media_category = 'tweet_image'

                # Upload media using v1.1 API
                media = self.api_v1.media_upload(
                    filename=str(media_path),
                    media_category=media_category
                )

                media_ids.append(media.media_id_string)
                print(f"[OK] Media uploaded: {media.media_id_string}")

            except tweepy.TweepyException as e:
                print(f"[ERROR] Failed to upload {media_path.name}: {e}")
                continue

        return media_ids

    def post_thread(
        self,
        tweets: List[str],
        media_paths: Optional[List[List[str]]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Post a Twitter thread.

        Args:
            tweets: List of tweet texts
            media_paths: Optional list of media paths for each tweet

        Returns:
            List of tweet info dictionaries, or None if thread failed
        """
        print(f"[INFO] Posting Twitter thread ({len(tweets)} tweets)")

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
                reply_to_tweet_id=previous_tweet_id
            )

            if not result:
                print(f"[ERROR] Failed to post tweet {i + 1} in thread")
                return None

            thread_results.append(result)
            previous_tweet_id = result['tweet_id']

        print(f"[OK] Thread posted successfully!")
        return thread_results

    def post_episode_announcement(
        self,
        episode_number: int,
        episode_summary: str,
        youtube_url: Optional[str] = None,
        spotify_url: Optional[str] = None,
        clip_paths: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Post an episode announcement as a thread.

        Args:
            episode_number: Episode number
            episode_summary: Summary from Claude
            youtube_url: Optional YouTube URL
            spotify_url: Optional Spotify URL
            clip_paths: Optional list of clip video paths

        Returns:
            List of tweet info dictionaries, or None if failed
        """
        # Main announcement tweet
        main_tweet = (
            f"🎙️ New Episode Alert! 🎙️\n\n"
            f"Episode {episode_number} of {Config.PODCAST_NAME} is now live!\n\n"
            f"{episode_summary[:180]}"  # Leave room for links
        )

        # Links tweet
        links_parts = ["Listen now:"]
        if youtube_url:
            links_parts.append(f"🎥 YouTube: {youtube_url}")
        if spotify_url:
            links_parts.append(f"🎵 Spotify: {spotify_url}")

        links_tweet = "\n".join(links_parts) if len(links_parts) > 1 else None

        # Build thread
        tweets = [main_tweet]
        if links_tweet:
            tweets.append(links_tweet)

        media_list = [None] * len(tweets)  # No media for text tweets

        # Add clip tweets if available
        if clip_paths:
            for i, clip_path in enumerate(clip_paths[:3], 1):  # Max 3 clips
                clip_tweet = f"🎬 Clip {i} from Episode {episode_number}"
                tweets.append(clip_tweet)
                media_list.append([clip_path])

        return self.post_thread(tweets, media_list)

    def post_clip(
        self,
        video_path: str,
        caption: str,
        episode_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Post a single clip with caption.

        Args:
            video_path: Path to video clip
            caption: Tweet caption
            episode_number: Episode number

        Returns:
            Dictionary with tweet info, or None if post failed
        """
        # Add episode reference
        full_caption = (
            f"{caption}\n\n"
            f"🎙️ From Episode {episode_number} of {Config.PODCAST_NAME}"
        )

        return self.post_tweet(
            text=full_caption[:280],
            media_paths=[video_path]
        )

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the authenticated user.

        Returns:
            Dictionary with user information
        """
        try:
            user = self.client.get_me(
                user_fields=['description', 'created_at', 'public_metrics']
            )

            if user.data:
                return {
                    'id': user.data.id,
                    'username': user.data.username,
                    'name': user.data.name,
                    'description': user.data.description,
                    'followers': user.data.public_metrics['followers_count'],
                    'following': user.data.public_metrics['following_count'],
                    'tweets': user.data.public_metrics['tweet_count']
                }

            return None

        except tweepy.TweepyException as e:
            print(f"[ERROR] Failed to get user info: {e}")
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
            print(f"[OK] Deleted tweet {tweet_id}")
            return True

        except tweepy.TweepyException as e:
            print(f"[ERROR] Failed to delete tweet: {e}")
            return False


def create_twitter_caption(
    clip_title: str,
    social_caption: str,
    hashtags: Optional[list] = None
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
        hashtags = ['podcast', 'comedy', 'fakeproblems']

    # Build caption
    caption = f"{clip_title}\n\n{social_caption}"

    # Add hashtags if space allows
    hashtag_str = ' '.join(f'#{tag}' for tag in hashtags)
    full_caption = f"{caption}\n\n{hashtag_str}"

    # Trim if too long
    if len(full_caption) > 280:
        # Try without hashtags
        if len(caption) <= 280:
            return caption[:280]
        # Trim caption
        return caption[:277] + "..."

    return full_caption
