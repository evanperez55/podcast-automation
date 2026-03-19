"""Engagement scorer for Fake Problems Podcast topic categories.

Ranks topic categories by Spearman correlation with historical engagement,
analyzes day-of-week performance, and gates output on data confidence.
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

from scipy import stats

from config import Config

KNOWN_CATEGORIES = [
    "shocking_news",
    "absurd_hypothetical",
    "dating_social",
    "pop_science",
    "cultural_observation",
]

COMEDY_PROTECTED_CATEGORIES = {"shocking_news", "absurd_hypothetical"}

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class EngagementScorer:
    """Rank topic categories by historical engagement correlation."""

    def __init__(self, history_path: Optional[Path] = None):
        """Initialize with optional custom history path (for testing)."""
        if history_path is not None:
            self.history_path = Path(history_path)
        else:
            self.history_path = (
                Config.BASE_DIR / "topic_data" / "engagement_history.json"
            )
        self.min_episodes = 15

    def get_category_rankings(self) -> dict:
        """Return ranked categories with Spearman correlation and day-of-week analysis.

        Returns:
            Dict with keys:
              status: "ok" | "insufficient_data"
              episodes_analyzed: int
              episodes_needed: int (0 when status is ok)
              rankings: list | None
              day_of_week: dict | None
        """
        history = self._load_history()
        n = len(history)
        needed = max(0, self.min_episodes - n)

        if n < self.min_episodes:
            return {
                "status": "insufficient_data",
                "episodes_analyzed": n,
                "episodes_needed": needed,
                "rankings": None,
                "day_of_week": None,
            }

        rankings = self._compute_rankings(history)
        rankings = self._apply_comedy_constraint(rankings)
        # Sort by abs(correlation) descending, NaN/None entries last
        rankings.sort(
            key=lambda e: abs(e["correlation"]) if e["correlation"] is not None else -1,
            reverse=True,
        )

        day_of_week = self._analyze_day_of_week(history)

        return {
            "status": "ok",
            "episodes_analyzed": n,
            "episodes_needed": 0,
            "rankings": rankings,
            "day_of_week": day_of_week,
        }

    def _load_history(self) -> list:
        """Load engagement history from JSON file. Returns [] if absent."""
        if not self.history_path.exists():
            return []
        with open(self.history_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _compute_score(self, record: dict) -> float:
        """Compute composite engagement score replicating TopicEngagementScorer formula."""
        yt = record.get("youtube") or {}
        tw = record.get("twitter") or {}

        views = yt.get("views", 0) or 0
        likes_yt = yt.get("likes", 0) or 0
        comments = yt.get("comments", 0) or 0
        yt_score = min(views * 0.001 + likes_yt * 0.1 + comments * 0.5, 7.0)

        impressions = tw.get("impressions") or 0
        engagements = tw.get("engagements", 0) or 0
        retweets = tw.get("retweets", 0) or 0
        likes_tw = tw.get("likes", 0) or 0
        tw_score = min(
            impressions * 0.0001 + engagements * 0.05 + retweets * 0.2 + likes_tw * 0.1,
            3.0,
        )

        return min(yt_score + tw_score, 10.0)

    def _compute_yt_score(self, record: dict) -> float:
        """Compute YouTube-only score component."""
        yt = record.get("youtube") or {}
        views = yt.get("views", 0) or 0
        likes = yt.get("likes", 0) or 0
        comments = yt.get("comments", 0) or 0
        return min(views * 0.001 + likes * 0.1 + comments * 0.5, 7.0)

    def _compute_tw_score(self, record: dict) -> float:
        """Compute Twitter-only score component."""
        tw = record.get("twitter") or {}
        impressions = tw.get("impressions") or 0
        engagements = tw.get("engagements", 0) or 0
        retweets = tw.get("retweets", 0) or 0
        likes = tw.get("likes", 0) or 0
        return min(
            impressions * 0.0001 + engagements * 0.05 + retweets * 0.2 + likes * 0.1,
            3.0,
        )

    def _correlate_category(self, history: list, category: str) -> Optional[dict]:
        """Compute Spearman correlation between category presence and engagement score.

        Returns None if correlation is NaN or data has no variance.
        Returns dict with correlation=None and skipped="no_variance" if constant presence.
        """
        presence = [
            1
            if any(category.lower() in str(t).lower() for t in r.get("topics", []))
            else 0
            for r in history
        ]
        scores = [self._compute_score(r) for r in history]

        # Check for constant presence (no variance)
        if len(set(presence)) == 1:
            return {
                "category": category,
                "correlation": None,
                "p_value": None,
                "method": "spearman",
                "episode_count": len(history),
                "skipped": "no_variance",
            }

        result = stats.spearmanr(presence, scores, nan_policy="omit")
        corr = result.statistic
        pval = result.pvalue

        # Skip if NaN
        if corr is None or math.isnan(corr):
            return None

        return {
            "category": category,
            "correlation": float(corr),
            "p_value": float(pval),
            "method": "spearman",
            "episode_count": len(history),
        }

    def _compute_rankings(self, history: list) -> list:
        """Compute correlation rankings for all known categories."""
        rankings = []
        for category in KNOWN_CATEGORIES:
            entry = self._correlate_category(history, category)
            if entry is not None:
                rankings.append(entry)
        return rankings

    def _analyze_day_of_week(self, history: list) -> dict:
        """Group engagement by weekday per platform. Returns {platform: {weekday: avg | None}}."""
        yt_buckets: dict[str, list[float]] = {day: [] for day in WEEKDAY_NAMES}
        tw_buckets: dict[str, list[float]] = {day: [] for day in WEEKDAY_NAMES}

        for record in history:
            ts_str = record.get("post_timestamp")
            if not ts_str:
                continue
            try:
                dt = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                continue

            weekday_name = WEEKDAY_NAMES[dt.weekday()]
            yt_buckets[weekday_name].append(self._compute_yt_score(record))
            tw_buckets[weekday_name].append(self._compute_tw_score(record))

        def avg_or_none(vals: list) -> Optional[float]:
            return sum(vals) / len(vals) if vals else None

        return {
            "youtube": {day: avg_or_none(yt_buckets[day]) for day in WEEKDAY_NAMES},
            "twitter": {day: avg_or_none(tw_buckets[day]) for day in WEEKDAY_NAMES},
        }

    def _apply_comedy_constraint(self, rankings: list) -> list:
        """Clamp comedy-protected categories to correlation >= 0.0."""
        for entry in rankings:
            if entry["category"] in COMEDY_PROTECTED_CATEGORIES:
                entry["comedy_protected"] = True
                if entry.get("correlation") is not None:
                    entry["correlation"] = max(entry["correlation"], 0.0)
        return rankings
