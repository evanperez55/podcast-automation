"""Posting time optimizer for Fake Problems Podcast.

Computes the optimal publish datetime per platform based on historical
engagement data from EngagementScorer.  Returns None when data is
insufficient — callers should fall back to their own scheduling logic.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from config import Config
from engagement_scorer import EngagementScorer

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _best_weekday(day_scores: dict) -> Optional[str]:
    """Return the weekday name with the highest score, ignoring None values.

    Returns None if all values are None.
    """
    valid = {day: score for day, score in day_scores.items() if score is not None}
    if not valid:
        return None
    return max(valid, key=lambda d: valid[d])


def _posting_hour_for(platform: str) -> int:
    """Return the configured posting hour (0-23) for the given platform.

    Falls back to 12 for unrecognised platforms.
    """
    mapping = {
        "youtube": Config.SCHEDULE_YOUTUBE_POSTING_HOUR,
        "twitter": Config.SCHEDULE_TWITTER_POSTING_HOUR,
        "instagram": Config.SCHEDULE_INSTAGRAM_POSTING_HOUR,
        "tiktok": Config.SCHEDULE_TIKTOK_POSTING_HOUR,
    }
    return mapping.get(platform.lower(), 12)


def _next_occurrence(weekday_name: str, hour: int) -> datetime:
    """Compute the next future datetime for weekday_name at the given hour.

    If today is the target weekday but the posting hour has already passed,
    advances by 7 days to the same weekday next week.
    """
    now = datetime.now()
    today_index = now.weekday()  # 0=Monday … 6=Sunday
    target_index = WEEKDAY_NAMES.index(weekday_name)

    days_ahead = (target_index - today_index) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )

    # If candidate is not strictly in the future, push to next week
    if candidate <= now:
        candidate += timedelta(weeks=1)

    return candidate


class PostingTimeOptimizer:
    """Compute optimal publish datetimes per platform from engagement history."""

    def __init__(self, history_path: Optional[Path] = None):
        """Initialise with an optional custom history path (for testing)."""
        self._scorer = EngagementScorer(history_path=history_path)

    def get_optimal_publish_at(self, platform: str) -> Optional[datetime]:
        """Return the next best datetime to publish on the given platform.

        Returns None when:
        - Engagement history has fewer than 15 episodes.
        - The platform has no day-of-week data (all None scores).
        """
        rankings = self._scorer.get_category_rankings()
        if rankings["status"] != "ok":
            return None

        day_of_week = rankings.get("day_of_week") or {}
        platform_days = day_of_week.get(platform.lower())
        if not platform_days:
            return None

        best_day = _best_weekday(platform_days)
        if best_day is None:
            return None

        posting_hour = _posting_hour_for(platform)
        return _next_occurrence(best_day, posting_hour)
