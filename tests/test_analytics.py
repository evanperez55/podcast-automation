"""Tests for analytics module - AnalyticsCollector and TopicEngagementScorer."""

import json

import pytest
from unittest.mock import patch, Mock, MagicMock, mock_open

from analytics import AnalyticsCollector, TopicEngagementScorer
from config import Config


# ---------------------------------------------------------------------------
# AnalyticsCollector tests
# ---------------------------------------------------------------------------


class TestAnalyticsCollectorInit:
    """Tests for AnalyticsCollector initialization."""

    @patch("analytics.Path.mkdir")
    def test_collector_init_disabled(self, mock_mkdir):
        """Default init has analytics disabled."""
        with patch.dict("os.environ", {}, clear=True):
            collector = AnalyticsCollector()

        assert collector.enabled is False
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("analytics.Path.mkdir")
    def test_collector_init_enabled(self, mock_mkdir):
        """Setting ANALYTICS_ENABLED=true enables analytics."""
        with patch.dict("os.environ", {"ANALYTICS_ENABLED": "true"}):
            collector = AnalyticsCollector()

        assert collector.enabled is True


class TestFetchYouTubeAnalytics:
    """Tests for YouTube analytics fetching."""

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_success(self, mock_mkdir):
        """Successful YouTube fetch returns views, likes, comments, video_id."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        # Mock the YouTube API chain
        mock_youtube = MagicMock()
        mock_search_response = {
            "items": [{"id": {"videoId": "abc123"}}],
        }
        mock_stats_response = {
            "items": [
                {
                    "statistics": {
                        "viewCount": "1500",
                        "likeCount": "120",
                        "commentCount": "30",
                    }
                }
            ],
        }
        mock_youtube.search().list().execute.return_value = mock_search_response
        mock_youtube.videos().list().execute.return_value = mock_stats_response

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector.fetch_youtube_analytics(25)

        assert result is not None
        assert result["views"] == 1500
        assert result["likes"] == 120
        assert result["comments"] == 30
        assert result["video_id"] == "abc123"

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_failure(self, mock_mkdir):
        """YouTube fetch returns None on exception."""
        collector = AnalyticsCollector()

        with patch("analytics.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("API error")):
                result = collector.fetch_youtube_analytics(25)

        assert result is None


class TestFetchTwitterAnalytics:
    """Tests for Twitter analytics fetching."""

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_success(self, mock_mkdir):
        """Successful Twitter fetch returns impressions, engagements, retweets, likes."""
        collector = AnalyticsCollector()

        mock_tweet = Mock()
        mock_tweet.public_metrics = {
            "impression_count": 5000,
            "reply_count": 10,
            "retweet_count": 25,
            "like_count": 80,
            "quote_count": 5,
        }

        mock_response = Mock()
        mock_response.data = [mock_tweet]

        mock_client = Mock()
        mock_client.search_recent_tweets.return_value = mock_response

        with (
            patch.object(Config, "TWITTER_API_KEY", "key"),
            patch.object(Config, "TWITTER_API_SECRET", "secret"),
            patch.object(Config, "TWITTER_ACCESS_TOKEN", "token"),
            patch.object(Config, "TWITTER_ACCESS_SECRET", "token_secret"),
            patch("tweepy.Client", return_value=mock_client),
        ):
            result = collector.fetch_twitter_analytics(25)

        assert result is not None
        assert result["impressions"] == 5000
        # engagements = reply(10) + retweet(25) + like(80) + quote(5) = 120
        assert result["engagements"] == 120
        assert result["retweets"] == 25
        assert result["likes"] == 80

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_failure(self, mock_mkdir):
        """Twitter fetch returns None on exception."""
        collector = AnalyticsCollector()

        with (
            patch.object(Config, "TWITTER_API_KEY", "key"),
            patch.object(Config, "TWITTER_API_SECRET", "secret"),
            patch.object(Config, "TWITTER_ACCESS_TOKEN", "token"),
            patch.object(Config, "TWITTER_ACCESS_SECRET", "token_secret"),
            patch("tweepy.Client", side_effect=Exception("API error")),
        ):
            result = collector.fetch_twitter_analytics(25)

        assert result is None


class TestCollectAnalytics:
    """Tests for combined analytics collection."""

    @patch("analytics.Path.mkdir")
    def test_collect_analytics(self, mock_mkdir):
        """collect_analytics calls both fetchers and returns combined dict."""
        collector = AnalyticsCollector()

        youtube_data = {"views": 1000, "likes": 50, "comments": 10, "video_id": "vid1"}
        twitter_data = {
            "impressions": 3000,
            "engagements": 200,
            "retweets": 30,
            "likes": 60,
        }

        with (
            patch.object(
                collector, "fetch_youtube_analytics", return_value=youtube_data
            ),
            patch.object(
                collector, "fetch_twitter_analytics", return_value=twitter_data
            ),
        ):
            result = collector.collect_analytics(25)

        assert result["episode_number"] == 25
        assert "collected_at" in result
        assert result["youtube"] == youtube_data
        assert result["twitter"] == twitter_data


class TestSaveAndLoadAnalytics:
    """Tests for analytics persistence."""

    @patch("analytics.Path.mkdir")
    def test_save_and_load_analytics(self, mock_mkdir, tmp_path):
        """Round-trip save then load preserves data."""
        collector = AnalyticsCollector()
        collector.analytics_dir = tmp_path

        analytics_data = {
            "episode_number": 25,
            "collected_at": "2026-03-02T12:00:00",
            "youtube": {"views": 1000, "likes": 50, "comments": 10, "video_id": "v1"},
            "twitter": {
                "impressions": 3000,
                "engagements": 200,
                "retweets": 30,
                "likes": 60,
            },
        }

        saved_path = collector.save_analytics(25, analytics_data)
        assert saved_path.exists()

        loaded = collector.load_analytics(25)
        assert loaded == analytics_data

    @patch("analytics.Path.mkdir")
    def test_load_analytics_not_found(self, mock_mkdir, tmp_path):
        """Loading analytics for nonexistent episode returns None."""
        collector = AnalyticsCollector()
        collector.analytics_dir = tmp_path

        result = collector.load_analytics(999)
        assert result is None


# ---------------------------------------------------------------------------
# TopicEngagementScorer tests
# ---------------------------------------------------------------------------


class TestCalculateEngagementScore:
    """Tests for engagement score calculation."""

    def test_engagement_score_youtube_only(self):
        """YouTube-only data produces correct score."""
        scorer = TopicEngagementScorer()

        analytics_data = {
            "youtube": {"views": 2000, "likes": 100, "comments": 20},
            "twitter": None,
        }

        # views*0.001 + likes*0.1 + comments*0.5
        # 2000*0.001 + 100*0.1 + 20*0.5 = 2.0 + 10.0 + 10.0 = 22.0 -> capped at 7.0
        # total = 7.0, twitter = 0.0 -> 7.0
        score = scorer.calculate_engagement_score(analytics_data)
        assert score == 7.0

    def test_engagement_score_twitter_only(self):
        """Twitter-only data produces correct score."""
        scorer = TopicEngagementScorer()

        analytics_data = {
            "youtube": None,
            "twitter": {
                "impressions": 5000,
                "engagements": 20,
                "retweets": 5,
                "likes": 10,
            },
        }

        # impressions*0.0001 + engagements*0.05 + retweets*0.2 + likes*0.1
        # 5000*0.0001 + 20*0.05 + 5*0.2 + 10*0.1 = 0.5 + 1.0 + 1.0 + 1.0 = 3.5
        # capped at 3.0
        score = scorer.calculate_engagement_score(analytics_data)
        assert score == 3.0

    def test_engagement_score_both(self):
        """Combined YouTube and Twitter data returns correct total."""
        scorer = TopicEngagementScorer()

        analytics_data = {
            "youtube": {"views": 1000, "likes": 20, "comments": 5},
            "twitter": {
                "impressions": 2000,
                "engagements": 10,
                "retweets": 2,
                "likes": 5,
            },
        }

        # YouTube: 1000*0.001 + 20*0.1 + 5*0.5 = 1.0 + 2.0 + 2.5 = 5.5 (cap 7)
        # Twitter: 2000*0.0001 + 10*0.05 + 2*0.2 + 5*0.1 = 0.2 + 0.5 + 0.4 + 0.5 = 1.6 (cap 3)
        # Total: 5.5 + 1.6 = 7.1 (cap 10)
        score = scorer.calculate_engagement_score(analytics_data)
        assert score == 7.1

    def test_engagement_score_caps(self):
        """Very high numbers are capped: YouTube max 7, Twitter max 3, total max 10."""
        scorer = TopicEngagementScorer()

        analytics_data = {
            "youtube": {"views": 999999, "likes": 99999, "comments": 99999},
            "twitter": {
                "impressions": 999999,
                "engagements": 99999,
                "retweets": 99999,
                "likes": 99999,
            },
        }

        score = scorer.calculate_engagement_score(analytics_data)
        assert score == 10.0


class TestGetEngagementBonus:
    """Tests for engagement bonus lookup."""

    def test_get_engagement_bonus(self, tmp_path):
        """Returns engagement score when analytics file exists."""
        scorer = TopicEngagementScorer()
        scorer.analytics_dir = tmp_path

        analytics_data = {
            "youtube": {"views": 1000, "likes": 20, "comments": 5},
            "twitter": None,
        }

        # Write a test analytics file
        analytics_path = tmp_path / "ep_25_analytics.json"
        analytics_path.write_text(json.dumps(analytics_data), encoding="utf-8")

        score = scorer.get_engagement_bonus(25)

        # YouTube: 1000*0.001 + 20*0.1 + 5*0.5 = 1.0 + 2.0 + 2.5 = 5.5
        assert score == 5.5

    def test_get_engagement_bonus_no_data(self, tmp_path):
        """Returns None when no analytics file exists."""
        scorer = TopicEngagementScorer()
        scorer.analytics_dir = tmp_path

        result = scorer.get_engagement_bonus(999)
        assert result is None


class TestCorrelateTopics:
    """Tests for topic-engagement correlation."""

    def test_correlate_topics(self, tmp_path):
        """Correlate returns correct structure with engagement score and topics."""
        scorer = TopicEngagementScorer()
        scorer.analytics_dir = tmp_path

        # Write analytics file
        analytics_data = {
            "youtube": {"views": 500, "likes": 10, "comments": 2},
            "twitter": None,
        }
        analytics_path = tmp_path / "ep_25_analytics.json"
        analytics_path.write_text(json.dumps(analytics_data), encoding="utf-8")

        analysis = {
            "episode_title": "The Best Episode",
            "best_clips": [
                {"suggested_title": "Clip About AI"},
                {"suggested_title": "Clip About Dating"},
            ],
        }

        result = scorer.correlate_topics(25, analysis)

        assert result["episode_number"] == 25
        assert result["episode_title"] == "The Best Episode"
        assert result["topics_discussed"] == ["Clip About AI", "Clip About Dating"]
        # YouTube: 500*0.001 + 10*0.1 + 2*0.5 = 0.5 + 1.0 + 1.0 = 2.5
        assert result["engagement_score"] == 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
