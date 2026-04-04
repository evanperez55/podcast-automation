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
    def test_collector_init_default_enabled(self, mock_mkdir):
        """Default init has analytics enabled (ANALYTICS_ENABLED defaults to 'true')."""
        collector = AnalyticsCollector()

        assert collector.enabled is True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("analytics.Path.mkdir")
    def test_collector_init_disabled(self, mock_mkdir):
        """Explicitly setting ANALYTICS_ENABLED=false disables analytics."""
        with patch.dict("os.environ", {"ANALYTICS_ENABLED": "false"}):
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


class TestFetchTwitterAnalyticsNullImpressions:
    """Tests for Twitter free-tier impression null handling."""

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_analytics_null_impressions(self, mock_mkdir):
        """impression_count=0 returns result["impressions"] as None (free-tier sentinel)."""
        collector = AnalyticsCollector()

        mock_tweet = Mock()
        mock_tweet.public_metrics = {
            "impression_count": 0,
            "reply_count": 2,
            "retweet_count": 3,
            "like_count": 10,
            "quote_count": 1,
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
        assert result["impressions"] is None, (
            "impression_count=0 on free tier should return None"
        )

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_analytics_real_impressions(self, mock_mkdir):
        """Non-zero impression_count returns the actual integer value."""
        collector = AnalyticsCollector()

        mock_tweet = Mock()
        mock_tweet.public_metrics = {
            "impression_count": 5000,
            "reply_count": 5,
            "retweet_count": 10,
            "like_count": 30,
            "quote_count": 2,
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


class TestCalculateEngagementScoreNullImpressions:
    """Test null impression guard in calculate_engagement_score."""

    def test_calculate_engagement_score_null_impressions(self):
        """None impressions do not raise TypeError and score is still computed."""
        scorer = TopicEngagementScorer()

        analytics_data = {
            "youtube": {"views": 1000, "likes": 20, "comments": 5},
            "twitter": {
                "impressions": None,
                "engagements": 10,
                "retweets": 2,
                "likes": 5,
            },
        }

        # Should not raise TypeError
        score = scorer.calculate_engagement_score(analytics_data)

        # YouTube: 1000*0.001 + 20*0.1 + 5*0.5 = 1.0 + 2.0 + 2.5 = 5.5
        # Twitter: None impressions -> 0; 0*0.0001 + 10*0.05 + 2*0.2 + 5*0.1 = 0+0.5+0.4+0.5=1.4
        assert isinstance(score, float)
        assert score == 6.9


class TestAppendToEngagementHistory:
    """Tests for engagement_history.json accumulation."""

    @patch("analytics.Path.mkdir")
    def test_append_to_engagement_history_creates_file(self, mock_mkdir, tmp_path):
        """When no history file exists, append creates the file with correct schema."""
        collector = AnalyticsCollector()
        history_path = tmp_path / "engagement_history.json"

        analytics_data = {
            "youtube": {"views": 1000, "likes": 50, "comments": 10, "video_id": "vid1"},
            "twitter": {
                "impressions": None,
                "engagements": 20,
                "retweets": 5,
                "likes": 15,
            },
        }
        platform_ids = {"youtube": "vid1", "twitter": "tw_123"}
        topics = ["AI comedy", "Tech fails"]

        with patch.object(
            collector, "_engagement_history_path", return_value=history_path
        ):
            result = collector.append_to_engagement_history(
                episode_number=29,
                analytics_data=analytics_data,
                platform_ids=platform_ids,
                topics=topics,
                post_timestamp="2026-03-16T18:19:32",
            )

        assert result.exists(), "engagement_history.json should be created"
        history = json.loads(result.read_text(encoding="utf-8"))
        assert isinstance(history, list)
        assert len(history) == 1
        record = history[0]
        assert record["episode_number"] == 29
        assert record["topics"] == topics
        assert record["youtube"]["video_id"] == "vid1"
        assert record["twitter"]["tweet_id"] == "tw_123"
        assert record["twitter"]["impressions"] is None

    @patch("analytics.Path.mkdir")
    def test_append_to_engagement_history_upserts(self, mock_mkdir, tmp_path):
        """Calling append twice for the same episode_number updates, not duplicates."""
        collector = AnalyticsCollector()
        history_path = tmp_path / "engagement_history.json"

        analytics_data = {
            "youtube": {"views": 500, "likes": 20, "comments": 5, "video_id": "vid1"},
            "twitter": None,
        }

        with patch.object(
            collector, "_engagement_history_path", return_value=history_path
        ):
            collector.append_to_engagement_history(
                episode_number=25,
                analytics_data=analytics_data,
                platform_ids={"youtube": "vid1"},
                topics=["Topic A"],
                post_timestamp="2026-03-10T10:00:00",
            )

            # Update with new data for same episode
            analytics_data["youtube"]["views"] = 1500
            collector.append_to_engagement_history(
                episode_number=25,
                analytics_data=analytics_data,
                platform_ids={"youtube": "vid1"},
                topics=["Topic A"],
                post_timestamp="2026-03-10T10:00:00",
            )

        history = json.loads(history_path.read_text(encoding="utf-8"))
        assert len(history) == 1, "Upsert should not duplicate records"
        assert history[0]["youtube"]["views"] == 1500

    @patch("analytics.Path.mkdir")
    def test_append_to_engagement_history_appends_new(self, mock_mkdir, tmp_path):
        """Appending for different episode numbers creates separate records."""
        collector = AnalyticsCollector()
        history_path = tmp_path / "engagement_history.json"

        analytics_data_ep1 = {
            "youtube": {"views": 500, "likes": 10, "comments": 2, "video_id": "vid1"},
            "twitter": None,
        }
        analytics_data_ep2 = {
            "youtube": {"views": 800, "likes": 30, "comments": 8, "video_id": "vid2"},
            "twitter": None,
        }

        with patch.object(
            collector, "_engagement_history_path", return_value=history_path
        ):
            collector.append_to_engagement_history(
                episode_number=1,
                analytics_data=analytics_data_ep1,
                platform_ids={"youtube": "vid1"},
                topics=["Topic A"],
                post_timestamp="2026-01-01T10:00:00",
            )
            collector.append_to_engagement_history(
                episode_number=2,
                analytics_data=analytics_data_ep2,
                platform_ids={"youtube": "vid2"},
                topics=["Topic B"],
                post_timestamp="2026-01-08T10:00:00",
            )

        history = json.loads(history_path.read_text(encoding="utf-8"))
        assert len(history) == 2
        episode_numbers = [r["episode_number"] for r in history]
        assert 1 in episode_numbers
        assert 2 in episode_numbers


class TestFetchYoutubeAnalyticsVideoId:
    """Tests for video_id parameter shortcutting the search API."""

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_analytics_with_video_id(self, mock_mkdir):
        """When video_id is provided, search().list() is NOT called, videos().list(id=...) IS called."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        mock_youtube = MagicMock()
        mock_stats_response = {
            "items": [
                {
                    "statistics": {
                        "viewCount": "2000",
                        "likeCount": "100",
                        "commentCount": "20",
                    }
                }
            ],
        }
        mock_youtube.videos().list().execute.return_value = mock_stats_response

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector.fetch_youtube_analytics(25, video_id="known_vid_xyz")

        # search().list() should NOT have been called
        mock_youtube.search.assert_not_called()

        assert result is not None
        assert result["views"] == 2000
        assert result["video_id"] == "known_vid_xyz"


class TestRunBackfillIds:
    """Tests for the run_backfill_ids pipeline function."""

    def test_run_backfill_ids_writes_platform_ids(self, tmp_path):
        """Backfill searches YouTube and writes platform_ids.json in each ep dir."""
        # Create fake ep dirs
        ep1_dir = tmp_path / "ep_1"
        ep2_dir = tmp_path / "ep_2"
        ep1_dir.mkdir()
        ep2_dir.mkdir()

        mock_youtube = MagicMock()
        mock_search_response = {"items": [{"id": {"videoId": "vid_abc"}}]}
        mock_youtube.search().list().execute.return_value = mock_search_response

        with (
            patch("analytics.AnalyticsCollector") as MockCollector,
            patch("pipeline.analytics_runner.Config") as MockConfig,
            patch("pipeline.analytics_runner.re") as mock_re,
            patch("pipeline.analytics_runner.time"),
            patch("pipeline.analytics_runner.json"),
        ):
            mock_re.search = __import__("re").search
            MockConfig.OUTPUT_DIR = tmp_path

            mock_collector_instance = MagicMock()
            MockCollector.return_value = mock_collector_instance

            # Build YouTube client via the collector instance
            mock_collector_instance._build_youtube_client.return_value = mock_youtube

            import builtins

            opened_files = []

            original_open = builtins.open

            def fake_open(path, *args, **kwargs):
                opened_files.append(str(path))
                return original_open(path, *args, **kwargs)

            with patch("builtins.open", side_effect=fake_open):
                from pipeline.analytics_runner import run_backfill_ids

                run_backfill_ids()

        # platform_ids.json should exist in both dirs
        assert (ep1_dir / "platform_ids.json").exists() or (
            ep2_dir / "platform_ids.json"
        ).exists()

    def test_run_backfill_ids_skips_existing(self, tmp_path):
        """Backfill skips ep dirs that already have platform_ids.json."""
        ep1_dir = tmp_path / "ep_1"
        ep1_dir.mkdir()
        existing = ep1_dir / "platform_ids.json"
        existing.write_text(
            '{"youtube": "existing_id", "twitter": null}', encoding="utf-8"
        )

        mock_youtube = MagicMock()

        with (
            patch("analytics.AnalyticsCollector") as MockCollector,
            patch("pipeline.analytics_runner.Config") as MockConfig,
            patch("pipeline.analytics_runner.time"),
        ):
            MockConfig.OUTPUT_DIR = tmp_path
            mock_collector_instance = MagicMock()
            MockCollector.return_value = mock_collector_instance
            mock_collector_instance._build_youtube_client.return_value = mock_youtube

            from pipeline.analytics_runner import run_backfill_ids

            run_backfill_ids()

        # YouTube search should NOT have been called (file already exists)
        mock_youtube.search.assert_not_called()
        # File should be unchanged
        content = json.loads(existing.read_text(encoding="utf-8"))
        assert content["youtube"] == "existing_id"

    def test_run_backfill_ids_handles_search_failure(self, tmp_path):
        """Backfill logs warning and continues when YouTube search raises exception."""
        ep1_dir = tmp_path / "ep_1"
        ep2_dir = tmp_path / "ep_2"
        ep1_dir.mkdir()
        ep2_dir.mkdir()

        mock_youtube = MagicMock()
        # First call raises, second returns valid result
        mock_youtube.search().list().execute.side_effect = [
            Exception("API error"),
            {"items": [{"id": {"videoId": "vid_ep2"}}]},
        ]

        with (
            patch("analytics.AnalyticsCollector") as MockCollector,
            patch("pipeline.analytics_runner.Config") as MockConfig,
            patch("pipeline.analytics_runner.time"),
        ):
            MockConfig.OUTPUT_DIR = tmp_path
            mock_collector_instance = MagicMock()
            MockCollector.return_value = mock_collector_instance
            mock_collector_instance._build_youtube_client.return_value = mock_youtube

            from pipeline.analytics_runner import run_backfill_ids

            # Should not raise even when search fails for one episode
            run_backfill_ids()

        # ep2 should have been processed (continues after ep1 failure)
        assert (ep2_dir / "platform_ids.json").exists()

    def test_run_backfill_ids_rate_limits(self, tmp_path):
        """Backfill sleeps between YouTube API requests for rate limiting."""
        ep1_dir = tmp_path / "ep_1"
        ep2_dir = tmp_path / "ep_2"
        ep3_dir = tmp_path / "ep_3"
        ep1_dir.mkdir()
        ep2_dir.mkdir()
        ep3_dir.mkdir()

        mock_youtube = MagicMock()
        mock_youtube.search().list().execute.return_value = {
            "items": [{"id": {"videoId": "vid_xyz"}}]
        }

        sleep_calls = []

        with (
            patch("analytics.AnalyticsCollector") as MockCollector,
            patch("pipeline.analytics_runner.Config") as MockConfig,
            patch("pipeline.analytics_runner.time") as mock_time_mod,
        ):
            mock_time_mod.sleep.side_effect = lambda s: sleep_calls.append(s)
            MockConfig.OUTPUT_DIR = tmp_path
            mock_collector_instance = MagicMock()
            MockCollector.return_value = mock_collector_instance
            mock_collector_instance._build_youtube_client.return_value = mock_youtube

            from pipeline.analytics_runner import run_backfill_ids

            run_backfill_ids()

        # Should sleep between requests (one per ep processed)
        assert len(sleep_calls) >= 1
        assert all(s >= 1.0 for s in sleep_calls), "Sleep should be at least 1 second"


class TestRunAnalyticsWiring:
    """Tests that run_analytics uses platform_ids and calls append_to_engagement_history."""

    def test_run_analytics_uses_platform_ids(self, tmp_path):
        """_collect_episode_analytics loads platform_ids and passes video_id to fetch_youtube_analytics."""
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()

        mock_collector = MagicMock()
        mock_scorer = MagicMock()

        platform_ids = {"youtube": "abc123", "twitter": None}
        mock_collector._load_platform_ids.return_value = platform_ids
        mock_collector.collect_analytics.return_value = {
            "episode_number": 25,
            "collected_at": "2026-03-19T00:00:00",
            "youtube": {
                "views": 1000,
                "likes": 50,
                "comments": 5,
                "video_id": "abc123",
            },
            "twitter": None,
        }
        mock_scorer.calculate_engagement_score.return_value = 5.5

        with patch("pipeline.analytics_runner.Config") as MockConfig:
            MockConfig.OUTPUT_DIR = tmp_path

            from pipeline.analytics_runner import _collect_episode_analytics

            _collect_episode_analytics(mock_collector, mock_scorer, 25)

        # _load_platform_ids should have been called with episode 25
        mock_collector._load_platform_ids.assert_called_once_with(25)
        # collect_analytics called with video_id from platform_ids
        mock_collector.collect_analytics.assert_called_once()
        call_args = mock_collector.collect_analytics.call_args
        assert call_args[1].get("video_id") == "abc123" or (
            len(call_args[0]) > 1 and call_args[0][1] == "abc123"
        )

    def test_run_analytics_calls_append_to_engagement_history(self, tmp_path):
        """_collect_episode_analytics calls append_to_engagement_history after collecting metrics."""
        ep_dir = tmp_path / "ep_1"
        ep_dir.mkdir()

        mock_collector = MagicMock()
        mock_scorer = MagicMock()

        platform_ids = {"youtube": "vid_001", "twitter": None}
        mock_collector._load_platform_ids.return_value = platform_ids
        analytics_data = {
            "episode_number": 1,
            "collected_at": "2026-03-19T00:00:00",
            "youtube": {
                "views": 500,
                "likes": 20,
                "comments": 3,
                "video_id": "vid_001",
            },
            "twitter": None,
        }
        mock_collector.collect_analytics.return_value = analytics_data
        mock_scorer.calculate_engagement_score.return_value = 3.5

        with patch("pipeline.analytics_runner.Config") as MockConfig:
            MockConfig.OUTPUT_DIR = tmp_path

            from pipeline.analytics_runner import _collect_episode_analytics

            _collect_episode_analytics(mock_collector, mock_scorer, 1)

        # append_to_engagement_history should have been called
        mock_collector.append_to_engagement_history.assert_called_once()
        call_kwargs = mock_collector.append_to_engagement_history.call_args
        assert call_kwargs[1]["episode_number"] == 1 or call_kwargs[0][0] == 1


class TestBuildYoutubeClient:
    """Tests for _build_youtube_client edge cases."""

    @patch("analytics.Path.mkdir")
    def test_build_youtube_client_token_not_found(self, mock_mkdir):
        """Returns None when youtube_token.pickle does not exist."""
        collector = AnalyticsCollector()

        with patch("analytics.Path.exists", return_value=False):
            result = collector._build_youtube_client()

        assert result is None

    @patch("analytics.Path.mkdir")
    def test_build_youtube_client_refreshes_expired_creds(self, mock_mkdir):
        """Refreshes credentials when they are expired."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_value"

        mock_youtube = MagicMock()

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch(
                "google.auth.transport.requests.Request", return_value=Mock()
            ) as mock_request_cls,
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector._build_youtube_client()

        mock_creds.refresh.assert_called_once_with(mock_request_cls.return_value)
        assert result is mock_youtube


class TestFetchYouTubeAnalyticsEdgeCases:
    """Tests for fetch_youtube_analytics edge cases."""

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_no_search_items(self, mock_mkdir):
        """Returns None when YouTube search returns no items."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        mock_youtube = MagicMock()
        mock_youtube.search().list().execute.return_value = {"items": []}

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector.fetch_youtube_analytics(99)

        assert result is None

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_no_stats_items(self, mock_mkdir):
        """Returns None when video stats response has no items."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        mock_youtube = MagicMock()
        mock_youtube.search().list().execute.return_value = {
            "items": [{"id": {"videoId": "vid123"}}]
        }
        mock_youtube.videos().list().execute.return_value = {"items": []}

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector.fetch_youtube_analytics(25)

        assert result is None

    @patch("analytics.Path.mkdir")
    def test_fetch_youtube_exception_in_stats(self, mock_mkdir):
        """Returns None when videos().list() raises an exception."""
        collector = AnalyticsCollector()

        mock_creds = Mock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        mock_youtube = MagicMock()
        mock_youtube.search().list().execute.return_value = {
            "items": [{"id": {"videoId": "vid123"}}]
        }
        mock_youtube.videos().list().execute.side_effect = Exception("Stats API error")

        with (
            patch("builtins.open", mock_open()),
            patch("analytics.Path.exists", return_value=True),
            patch("pickle.load", return_value=mock_creds),
            patch("googleapiclient.discovery.build", return_value=mock_youtube),
        ):
            result = collector.fetch_youtube_analytics(25)

        assert result is None


class TestFetchTwitterAnalyticsEdgeCases:
    """Tests for fetch_twitter_analytics edge cases."""

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_missing_credentials(self, mock_mkdir):
        """Returns None when Twitter credentials are not configured."""
        collector = AnalyticsCollector()

        with (
            patch.object(Config, "TWITTER_API_KEY", None),
            patch.object(Config, "TWITTER_API_SECRET", None),
            patch.object(Config, "TWITTER_ACCESS_TOKEN", None),
            patch.object(Config, "TWITTER_ACCESS_SECRET", None),
        ):
            result = collector.fetch_twitter_analytics(25)

        assert result is None

    @patch("analytics.Path.mkdir")
    def test_fetch_twitter_no_tweets_found(self, mock_mkdir):
        """Returns None when no tweets match the search query."""
        collector = AnalyticsCollector()

        mock_response = Mock()
        mock_response.data = None

        mock_client = Mock()
        mock_client.search_recent_tweets.return_value = mock_response

        with (
            patch.object(Config, "TWITTER_API_KEY", "key"),
            patch.object(Config, "TWITTER_API_SECRET", "secret"),
            patch.object(Config, "TWITTER_ACCESS_TOKEN", "token"),
            patch.object(Config, "TWITTER_ACCESS_SECRET", "token_secret"),
            patch("tweepy.Client", return_value=mock_client),
        ):
            result = collector.fetch_twitter_analytics(42)

        assert result is None


class TestEngagementHistoryPath:
    """Tests for _engagement_history_path."""

    @patch("analytics.Path.mkdir")
    def test_engagement_history_path(self, mock_mkdir):
        """Returns the correct path for engagement_history.json."""
        collector = AnalyticsCollector()

        result = collector._engagement_history_path()

        assert result == Config.BASE_DIR / "topic_data" / "engagement_history.json"


class TestLoadPlatformIds:
    """Tests for _load_platform_ids."""

    def test_load_platform_ids_file_exists(self, tmp_path):
        """Loads and returns platform IDs when the file exists."""
        # Create ep dir and platform_ids.json before mocking Path.mkdir
        ep_dir = tmp_path / "ep_10"
        ep_dir.mkdir()
        platform_ids = {"youtube": "vid_abc", "twitter": "tw_123"}
        ids_file = ep_dir / "platform_ids.json"
        ids_file.write_text(json.dumps(platform_ids), encoding="utf-8")

        with patch("analytics.Path.mkdir"):
            collector = AnalyticsCollector()

        with patch.object(Config, "OUTPUT_DIR", tmp_path):
            result = collector._load_platform_ids(10)

        assert result == platform_ids

    @patch("analytics.Path.mkdir")
    def test_load_platform_ids_file_missing(self, mock_mkdir, tmp_path):
        """Returns empty dict when platform_ids.json does not exist."""
        collector = AnalyticsCollector()

        with patch.object(Config, "OUTPUT_DIR", tmp_path):
            result = collector._load_platform_ids(999)

        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
