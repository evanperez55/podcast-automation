"""Tests for PostingTimeOptimizer.

Covers:
- _best_weekday helper: filters None values, returns weekday with highest score
- _next_occurrence: returns future datetime, handles same-day past-hour scenario
- _posting_hour_for: returns platform-specific hours from Config
- PostingTimeOptimizer.get_optimal_publish_at: delegates to EngagementScorer, returns None on insufficient data
"""

from datetime import datetime
from unittest.mock import MagicMock, patch


class TestBestWeekday:
    """Tests for _best_weekday helper."""

    def test_returns_weekday_with_highest_score(self):
        from posting_time_optimizer import _best_weekday

        scores = {
            "Monday": 1.5,
            "Tuesday": 3.2,
            "Wednesday": 2.1,
            "Thursday": None,
            "Friday": 0.8,
            "Saturday": None,
            "Sunday": 1.0,
        }
        assert _best_weekday(scores) == "Tuesday"

    def test_returns_none_when_all_values_are_none(self):
        from posting_time_optimizer import _best_weekday

        scores = {
            "Monday": None,
            "Tuesday": None,
            "Wednesday": None,
            "Thursday": None,
            "Friday": None,
            "Saturday": None,
            "Sunday": None,
        }
        assert _best_weekday(scores) is None

    def test_handles_single_non_none_value(self):
        from posting_time_optimizer import _best_weekday

        scores = {
            "Monday": None,
            "Tuesday": None,
            "Wednesday": 2.5,
            "Thursday": None,
            "Friday": None,
            "Saturday": None,
            "Sunday": None,
        }
        assert _best_weekday(scores) == "Wednesday"

    def test_filters_out_none_values_before_comparison(self):
        from posting_time_optimizer import _best_weekday

        scores = {
            "Monday": 5.0,
            "Tuesday": None,
            "Wednesday": 4.9,
        }
        # Should not raise even with None mixed in
        result = _best_weekday(scores)
        assert result == "Monday"


class TestNextOccurrence:
    """Tests for _next_occurrence helper."""

    def test_returns_today_when_best_day_is_today_and_before_posting_hour(self):
        from posting_time_optimizer import _next_occurrence

        # Freeze time to Wednesday 2026-03-18 at 09:00
        frozen_dt = datetime(2026, 3, 18, 9, 0, 0)  # Wednesday
        with patch("posting_time_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _next_occurrence("Wednesday", 14)

        assert result.year == 2026
        assert result.month == 3
        assert result.day == 18
        assert result.hour == 14
        assert result.minute == 0
        assert result.second == 0

    def test_advances_to_next_week_when_today_is_best_day_but_past_posting_hour(self):
        from posting_time_optimizer import _next_occurrence

        # Freeze time to Wednesday 2026-03-18 at 15:00 (past 14:00 posting hour)
        frozen_dt = datetime(2026, 3, 18, 15, 0, 0)  # Wednesday
        with patch("posting_time_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _next_occurrence("Wednesday", 14)

        # Should advance to next Wednesday (7 days later)
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 25
        assert result.hour == 14

    def test_returns_future_datetime_for_different_weekday(self):
        from posting_time_optimizer import _next_occurrence

        # Freeze time to Wednesday 2026-03-18 at 09:00
        frozen_dt = datetime(2026, 3, 18, 9, 0, 0)  # Wednesday
        with patch("posting_time_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _next_occurrence("Friday", 10)

        # Next Friday from Wednesday is 2 days later
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 20
        assert result.hour == 10

    def test_result_is_always_in_the_future(self):
        from posting_time_optimizer import _next_occurrence

        frozen_dt = datetime(2026, 3, 18, 15, 0, 0)  # Wednesday at 15:00
        with patch("posting_time_optimizer.datetime") as mock_dt:
            mock_dt.now.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = _next_occurrence("Wednesday", 14)

        assert result > frozen_dt


class TestPlatformHours:
    """Tests for _posting_hour_for helper."""

    def test_youtube_uses_configured_hour_default_14(self):
        from posting_time_optimizer import _posting_hour_for

        with patch("posting_time_optimizer.Config") as mock_cfg:
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12
            assert _posting_hour_for("youtube") == 14

    def test_twitter_uses_configured_hour_default_10(self):
        from posting_time_optimizer import _posting_hour_for

        with patch("posting_time_optimizer.Config") as mock_cfg:
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12
            assert _posting_hour_for("twitter") == 10

    def test_youtube_and_twitter_have_different_hours(self):
        from posting_time_optimizer import _posting_hour_for

        with patch("posting_time_optimizer.Config") as mock_cfg:
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12
            yt_hour = _posting_hour_for("youtube")
            tw_hour = _posting_hour_for("twitter")
            assert yt_hour != tw_hour

    def test_unknown_platform_returns_default_12(self):
        from posting_time_optimizer import _posting_hour_for

        with patch("posting_time_optimizer.Config") as mock_cfg:
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12
            assert _posting_hour_for("unknown_platform") == 12


class TestGetOptimalPublishAt:
    """Tests for PostingTimeOptimizer.get_optimal_publish_at."""

    def _make_ok_rankings(self, best_day="Tuesday"):
        """Helper to create a valid get_category_rankings response."""
        day_of_week = {
            "youtube": {
                "Monday": 1.0,
                "Tuesday": 3.5,
                "Wednesday": 2.0,
                "Thursday": None,
                "Friday": 1.5,
                "Saturday": None,
                "Sunday": 0.5,
            },
            "twitter": {
                "Monday": 2.0,
                "Tuesday": 1.0,
                "Wednesday": None,
                "Thursday": 3.0,
                "Friday": None,
                "Saturday": None,
                "Sunday": 1.5,
            },
        }
        return {
            "status": "ok",
            "episodes_analyzed": 20,
            "episodes_needed": 0,
            "rankings": [],
            "day_of_week": day_of_week,
        }

    def test_returns_future_datetime_for_youtube_when_data_sufficient(self):
        from posting_time_optimizer import PostingTimeOptimizer

        with patch("posting_time_optimizer.EngagementScorer") as MockScorer:
            mock_instance = MagicMock()
            mock_instance.get_category_rankings.return_value = self._make_ok_rankings()
            MockScorer.return_value = mock_instance

            optimizer = PostingTimeOptimizer()
            result = optimizer.get_optimal_publish_at("youtube")

        assert result is not None
        assert isinstance(result, datetime)
        assert result > datetime.now()

    def test_returns_none_when_status_is_insufficient_data(self):
        from posting_time_optimizer import PostingTimeOptimizer

        with patch("posting_time_optimizer.EngagementScorer") as MockScorer:
            mock_instance = MagicMock()
            mock_instance.get_category_rankings.return_value = {
                "status": "insufficient_data",
                "episodes_analyzed": 10,
                "episodes_needed": 5,
                "rankings": None,
                "day_of_week": None,
            }
            MockScorer.return_value = mock_instance

            optimizer = PostingTimeOptimizer()
            result = optimizer.get_optimal_publish_at("youtube")

        assert result is None

    def test_returns_none_when_all_platform_scores_are_none(self):
        from posting_time_optimizer import PostingTimeOptimizer

        with patch("posting_time_optimizer.EngagementScorer") as MockScorer:
            mock_instance = MagicMock()
            mock_instance.get_category_rankings.return_value = {
                "status": "ok",
                "episodes_analyzed": 20,
                "episodes_needed": 0,
                "rankings": [],
                "day_of_week": {
                    "youtube": {
                        day: None
                        for day in [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ]
                    },
                    "twitter": {
                        "Monday": 1.5,
                        "Tuesday": 2.0,
                        "Wednesday": None,
                        "Thursday": None,
                        "Friday": None,
                        "Saturday": None,
                        "Sunday": None,
                    },
                },
            }
            MockScorer.return_value = mock_instance

            optimizer = PostingTimeOptimizer()
            result = optimizer.get_optimal_publish_at("youtube")

        assert result is None

    def test_twitter_returns_different_hour_than_youtube(self):
        from posting_time_optimizer import PostingTimeOptimizer

        ok_data = self._make_ok_rankings()
        frozen_dt = datetime(2026, 3, 18, 9, 0, 0)  # Wednesday at 09:00

        with patch("posting_time_optimizer.EngagementScorer") as MockScorer:
            mock_instance = MagicMock()
            mock_instance.get_category_rankings.return_value = ok_data
            MockScorer.return_value = mock_instance

            with patch("posting_time_optimizer.datetime") as mock_dt:
                mock_dt.now.return_value = frozen_dt
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                optimizer = PostingTimeOptimizer()
                yt_result = optimizer.get_optimal_publish_at("youtube")
                tw_result = optimizer.get_optimal_publish_at("twitter")

        # Both return datetimes but at different hours
        assert yt_result is not None
        assert tw_result is not None
        assert yt_result.hour != tw_result.hour

    def test_history_path_passed_to_engagement_scorer(self):
        from pathlib import Path

        from posting_time_optimizer import PostingTimeOptimizer

        custom_path = Path("/tmp/custom_history.json")
        with patch("posting_time_optimizer.EngagementScorer") as MockScorer:
            mock_instance = MagicMock()
            MockScorer.return_value = mock_instance
            PostingTimeOptimizer(history_path=custom_path)

        MockScorer.assert_called_once_with(history_path=custom_path)
