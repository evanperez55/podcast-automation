"""Analytics feedback loop for podcast automation.

Collects engagement metrics from YouTube and Twitter, calculates
engagement scores, and correlates them with episode topics to
inform future topic selection.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import Config
from logger import logger


class AnalyticsCollector:
    """Collect engagement analytics from publishing platforms."""

    def __init__(self):
        """Initialize analytics collector."""
        self.enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
        self.analytics_dir = Config.BASE_DIR / "topic_data" / "analytics"
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

    def fetch_youtube_analytics(
        self, episode_number: int, video_id: Optional[str] = None
    ) -> Optional[dict]:
        """Fetch YouTube video statistics for an episode.

        When video_id is provided, skips the search API call (100 quota units)
        and goes directly to videos().list() (1 quota unit). When video_id is
        absent, searches by episode title to discover the video ID.

        Args:
            episode_number: The episode number to look up.
            video_id: Optional known YouTube video ID. When provided, skips the
                      search().list() call entirely.

        Returns:
            Dict with views, likes, comments, and video_id, or None on error.
        """
        try:
            import pickle
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            token_path = Config.BASE_DIR / "credentials" / "youtube_token.pickle"
            if not token_path.exists():
                logger.warning("YouTube token not found: %s", token_path)
                return None

            with open(token_path, "rb") as f:
                creds = pickle.load(f)

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            youtube = build("youtube", "v3", credentials=creds)

            if video_id is None:
                # Search for the episode video by title (100 quota units)
                search_response = (
                    youtube.search()
                    .list(
                        q=f"Episode #{episode_number}",
                        channelId=os.getenv("YOUTUBE_CHANNEL_ID", ""),
                        type="video",
                        part="id",
                        maxResults=1,
                    )
                    .execute()
                )

                items = search_response.get("items", [])
                if not items:
                    logger.warning(
                        "No YouTube video found for Episode #%s", episode_number
                    )
                    return None

                video_id = items[0]["id"]["videoId"]

            # Fetch video statistics (1 quota unit)
            stats_response = (
                youtube.videos().list(part="statistics", id=video_id).execute()
            )

            stats_items = stats_response.get("items", [])
            if not stats_items:
                logger.warning("No stats found for video %s", video_id)
                return None

            stats = stats_items[0]["statistics"]
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "video_id": video_id,
            }

        except Exception as e:
            logger.warning("Failed to fetch YouTube analytics: %s", e)
            return None

    def fetch_twitter_analytics(self, episode_number: int) -> Optional[dict]:
        """Fetch Twitter engagement metrics for an episode.

        Searches for recent tweets mentioning the episode and aggregates
        impression, engagement, retweet, and like counts.

        Args:
            episode_number: The episode number to look up.

        Returns:
            Dict with impressions, engagements, retweets, and likes,
            or None on error.
        """
        try:
            import tweepy

            api_key = Config.TWITTER_API_KEY
            api_secret = Config.TWITTER_API_SECRET
            access_token = Config.TWITTER_ACCESS_TOKEN
            access_secret = Config.TWITTER_ACCESS_SECRET

            if not all([api_key, api_secret, access_token, access_secret]):
                logger.warning("Twitter credentials not configured")
                return None

            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret,
            )

            # Search for tweets about this episode
            query = f"Episode {episode_number} {Config.PODCAST_NAME}"
            response = client.search_recent_tweets(
                query=query,
                tweet_fields=["public_metrics"],
                max_results=10,
            )

            if not response.data:
                logger.warning("No tweets found for Episode #%s", episode_number)
                return None

            # Aggregate metrics across matching tweets.
            # impression_count=0 on free tier is indistinguishable from "no data";
            # use None as a sentinel so callers can distinguish "not reported" from
            # genuinely zero impressions.
            impression_data_available = False
            total_impressions = 0
            total_engagements = 0
            total_retweets = 0
            total_likes = 0

            for tweet in response.data:
                metrics = tweet.public_metrics or {}
                imp = metrics.get("impression_count")
                if imp is not None and imp > 0:
                    impression_data_available = True
                    total_impressions += imp
                total_engagements += (
                    metrics.get("reply_count", 0)
                    + metrics.get("retweet_count", 0)
                    + metrics.get("like_count", 0)
                    + metrics.get("quote_count", 0)
                )
                total_retweets += metrics.get("retweet_count", 0)
                total_likes += metrics.get("like_count", 0)

            return {
                "impressions": total_impressions if impression_data_available else None,
                "engagements": total_engagements,
                "retweets": total_retweets,
                "likes": total_likes,
            }

        except Exception as e:
            logger.warning("Failed to fetch Twitter analytics: %s", e)
            return None

    def collect_analytics(self, episode_number: int) -> dict:
        """Collect analytics from all platforms for an episode.

        Args:
            episode_number: The episode number to collect analytics for.

        Returns:
            Dict with episode_number, collected_at timestamp, and
            per-platform analytics (youtube, twitter). Platform values
            are None if collection failed.
        """
        logger.info("Collecting analytics for Episode #%s", episode_number)

        youtube_data = self.fetch_youtube_analytics(episode_number)
        twitter_data = self.fetch_twitter_analytics(episode_number)

        return {
            "episode_number": episode_number,
            "collected_at": datetime.now().isoformat(),
            "youtube": youtube_data,
            "twitter": twitter_data,
        }

    def save_analytics(self, episode_number: int, analytics_data: dict) -> Path:
        """Save analytics data to a JSON file.

        Args:
            episode_number: The episode number.
            analytics_data: The analytics dict to persist.

        Returns:
            Path to the saved JSON file.
        """
        output_path = self.analytics_dir / f"ep_{episode_number}_analytics.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analytics_data, f, indent=2, ensure_ascii=False)

        logger.info("Saved analytics to %s", output_path)
        return output_path

    def load_analytics(self, episode_number: int) -> Optional[dict]:
        """Load previously saved analytics for an episode.

        Args:
            episode_number: The episode number to load.

        Returns:
            The analytics dict, or None if the file does not exist.
        """
        analytics_path = self.analytics_dir / f"ep_{episode_number}_analytics.json"

        if not analytics_path.exists():
            logger.warning("No analytics file found for Episode #%s", episode_number)
            return None

        with open(analytics_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _engagement_history_path(self) -> Path:
        """Return the path to the cross-episode engagement history file."""
        return Config.BASE_DIR / "topic_data" / "engagement_history.json"

    def append_to_engagement_history(
        self,
        episode_number: int,
        analytics_data: dict,
        platform_ids: dict,
        topics: list,
        post_timestamp: str,
    ) -> Path:
        """Append or update per-episode record in engagement_history.json.

        Upserts by episode_number — running analytics twice for the same episode
        updates the existing record rather than appending a duplicate.

        Args:
            episode_number: The episode number.
            analytics_data: Dict with 'youtube' and 'twitter' sub-dicts.
            platform_ids: Dict with 'youtube' and/or 'twitter' IDs.
            topics: List of topic strings (e.g. clip suggested titles).
            post_timestamp: ISO timestamp of when the episode was published.

        Returns:
            Path to the updated engagement_history.json file.
        """
        history_path = self._engagement_history_path()

        # Load existing history or start fresh
        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        # Build the record
        yt = analytics_data.get("youtube") or {}
        tw = analytics_data.get("twitter") or {}

        record: dict = {
            "episode_number": episode_number,
            "collected_at": datetime.now().isoformat(),
            "post_timestamp": post_timestamp,
            "topics": topics,
            "youtube": (
                {
                    "video_id": platform_ids.get("youtube"),
                    "views": yt.get("views", 0),
                    "likes": yt.get("likes", 0),
                    "comments": yt.get("comments", 0),
                }
                if yt
                else None
            ),
            "twitter": (
                {
                    "tweet_id": platform_ids.get("twitter"),
                    # None when free-tier API omits impression_count
                    "impressions": tw.get("impressions"),
                    "engagements": tw.get("engagements", 0),
                    "retweets": tw.get("retweets", 0),
                    "likes": tw.get("likes", 0),
                }
                if tw
                else None
            ),
        }

        # Upsert: update existing record for this episode, or append new
        idx = next(
            (i for i, r in enumerate(history) if r["episode_number"] == episode_number),
            None,
        )
        if idx is not None:
            history[idx] = record
        else:
            history.append(record)

        history_path.parent.mkdir(parents=True, exist_ok=True)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        logger.info(
            "Updated engagement history: %s (episode #%s)", history_path, episode_number
        )
        return history_path

    def _load_platform_ids(self, episode_number: int) -> dict:
        """Load stored platform IDs for an episode, or return empty dict.

        Args:
            episode_number: The episode number to load IDs for.

        Returns:
            Dict with 'youtube' and/or 'twitter' keys, or empty dict if not found.
        """
        platform_ids_path = (
            Config.OUTPUT_DIR / f"ep_{episode_number}" / "platform_ids.json"
        )
        if platform_ids_path.exists():
            with open(platform_ids_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


class TopicEngagementScorer:
    """Score episode engagement and correlate with topics."""

    def __init__(self):
        """Initialize engagement scorer."""
        self.analytics_dir = Config.BASE_DIR / "topic_data" / "analytics"

    def calculate_engagement_score(self, analytics_data: dict) -> float:
        """Calculate a composite engagement score from 0-10.

        YouTube metrics contribute up to 7 points:
            views * 0.001 + likes * 0.1 + comments * 0.5

        Twitter metrics contribute up to 3 points:
            impressions * 0.0001 + engagements * 0.05
            + retweets * 0.2 + likes * 0.1

        The total is capped at 10.

        Args:
            analytics_data: Dict containing 'youtube' and 'twitter' sub-dicts.

        Returns:
            Engagement score rounded to 1 decimal place (0.0 - 10.0).
        """
        youtube_score = 0.0
        twitter_score = 0.0

        yt = analytics_data.get("youtube")
        if yt:
            youtube_score = (
                yt.get("views", 0) * 0.001
                + yt.get("likes", 0) * 0.1
                + yt.get("comments", 0) * 0.5
            )
            youtube_score = min(youtube_score, 7.0)

        tw = analytics_data.get("twitter")
        if tw:
            # Guard against None impressions (free-tier Twitter returns null)
            tw_impressions = tw.get("impressions") or 0
            twitter_score = (
                tw_impressions * 0.0001
                + tw.get("engagements", 0) * 0.05
                + tw.get("retweets", 0) * 0.2
                + tw.get("likes", 0) * 0.1
            )
            twitter_score = min(twitter_score, 3.0)

        total = min(youtube_score + twitter_score, 10.0)
        return round(total, 1)

    def get_engagement_bonus(self, episode_number: int) -> Optional[float]:
        """Get the engagement score for a past episode.

        Loads saved analytics and calculates the score. Useful as a
        bonus modifier when scoring future topics that are similar to
        previously high-performing episodes.

        Args:
            episode_number: The episode number to look up.

        Returns:
            Engagement score (0.0-10.0), or None if no analytics found.
        """
        analytics_path = self.analytics_dir / f"ep_{episode_number}_analytics.json"

        if not analytics_path.exists():
            return None

        with open(analytics_path, "r", encoding="utf-8") as f:
            analytics_data = json.load(f)

        return self.calculate_engagement_score(analytics_data)

    def correlate_topics(self, episode_number: int, analysis: dict) -> dict:
        """Correlate episode topics with engagement metrics.

        Combines the AI content analysis (topics, title) with the
        calculated engagement score to produce a record that can
        inform future topic selection.

        Args:
            episode_number: The episode number.
            analysis: The content analysis dict from content_editor
                      (expects 'episode_title' and 'best_clips' keys).

        Returns:
            Dict with episode_number, engagement_score, episode_title,
            and topics_discussed list.
        """
        analytics_path = self.analytics_dir / f"ep_{episode_number}_analytics.json"

        engagement_score = 0.0
        if analytics_path.exists():
            with open(analytics_path, "r", encoding="utf-8") as f:
                analytics_data = json.load(f)
            engagement_score = self.calculate_engagement_score(analytics_data)

        # Extract topics from best_clips or other analysis fields
        topics_discussed = []
        for clip in analysis.get("best_clips", []):
            title = clip.get("suggested_title") or clip.get("title", "")
            if title:
                topics_discussed.append(title)

        return {
            "episode_number": episode_number,
            "engagement_score": engagement_score,
            "episode_title": analysis.get("episode_title"),
            "topics_discussed": topics_discussed,
        }
