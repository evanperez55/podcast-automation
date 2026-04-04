"""Tests for weekly_topic_refresh.py — weekly topic curation pipeline."""

import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest


class TestRunWeeklyRefreshAllSteps:
    """Tests for run_weekly_refresh with all steps enabled."""

    @patch("weekly_topic_refresh.TopicCurator")
    @patch("weekly_topic_refresh.TopicScorer")
    @patch("weekly_topic_refresh.TopicScraper")
    @patch("weekly_topic_refresh.Path.mkdir")
    def test_all_steps_success(self, mock_mkdir, mock_scraper_cls, mock_scorer_cls, mock_curator_cls):
        """All four steps succeed and results dict has all step keys."""
        from weekly_topic_refresh import run_weekly_refresh

        # Setup scraper
        mock_scraper = mock_scraper_cls.return_value
        mock_scraper.scrape_multiple_subreddits.return_value = [{"title": "t1"}]
        mock_scraper.scrape_trending_topics.return_value = [{"title": "t2"}]
        mock_scraper.deduplicate_topics.return_value = [{"title": "t1"}, {"title": "t2"}]
        mock_scraper.filter_by_score.return_value = [{"title": "t1"}]
        mock_scraper.save_scraped_topics.return_value = Path("topic_data/scraped.json")

        # Setup scorer
        mock_scorer = mock_scorer_cls.return_value
        mock_scored = [{"title": "t1", "score": {"total": 8.0}}]
        mock_scorer.score_topics.return_value = mock_scored
        mock_scorer.save_scored_topics.return_value = Path("topic_data/scored.json")
        mock_scorer.filter_recommended.return_value = mock_scored

        # Setup curator
        mock_curator = mock_curator_cls.return_value
        mock_curator.load_scored_topics.return_value = mock_scored
        mock_curator.restructure_google_doc.return_value = True
        mock_curator.plan_next_episode.return_value = {"total_topics": 5}

        # Mock Path.glob for finding scraped files in step 2
        mock_scraped_file = MagicMock()
        mock_scraped_file.stat.return_value.st_mtime = 1000
        scraped_json = json.dumps({"topics": [{"title": "t1"}]})
        mock_file_read = MagicMock()
        mock_file_read.__enter__ = Mock(return_value=mock_file_read)
        mock_file_read.__exit__ = Mock(return_value=False)
        mock_file_read.read.return_value = scraped_json

        with patch("weekly_topic_refresh.Path.glob", return_value=[mock_scraped_file]):
            with patch("builtins.open", return_value=mock_file_read):
                with patch("json.load", return_value={"topics": [{"title": "t1"}]}):
                    result = run_weekly_refresh(scrape=True, score=True, curate=True, plan_episode=True)

        assert result["steps"]["scrape"]["success"] is True
        assert result["steps"]["score"]["success"] is True
        assert result["steps"]["curate"]["success"] is True
        assert result["steps"]["plan"]["success"] is True

    @patch("weekly_topic_refresh.TopicScraper")
    @patch("weekly_topic_refresh.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_scrape_failure_stops_pipeline(self, mock_open, mock_mkdir, mock_scraper_cls):
        """When scraping fails, pipeline returns early without scoring."""
        from weekly_topic_refresh import run_weekly_refresh

        mock_scraper_cls.side_effect = Exception("Reddit API down")

        result = run_weekly_refresh(scrape=True, score=True, curate=True, plan_episode=True)

        assert result["steps"]["scrape"]["success"] is False
        assert "score" not in result["steps"]


class TestRunWeeklyRefreshSelectiveSteps:
    """Tests for run_weekly_refresh with selective step execution."""

    @patch("weekly_topic_refresh.TopicCurator")
    @patch("weekly_topic_refresh.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_curate_only(self, mock_open, mock_mkdir, mock_curator_cls):
        """Running curate-only skips scrape and score steps."""
        from weekly_topic_refresh import run_weekly_refresh

        mock_curator = mock_curator_cls.return_value
        mock_curator.load_scored_topics.return_value = []
        mock_curator.restructure_google_doc.return_value = True
        mock_curator.plan_next_episode.return_value = {"total_topics": 3}

        result = run_weekly_refresh(scrape=False, score=False, curate=True, plan_episode=True)

        assert "scrape" not in result["steps"]
        assert "score" not in result["steps"]
        assert result["steps"]["curate"]["success"] is True

    @patch("weekly_topic_refresh.TopicCurator")
    @patch("weekly_topic_refresh.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_plan_failure_does_not_block_curate(self, mock_open, mock_mkdir, mock_curator_cls):
        """Planning failure is non-fatal — curate result is preserved."""
        from weekly_topic_refresh import run_weekly_refresh

        mock_curator = mock_curator_cls.return_value
        mock_curator.load_scored_topics.return_value = []
        mock_curator.restructure_google_doc.return_value = True
        # Second call for plan_episode raises
        mock_curator.plan_next_episode.side_effect = Exception("Ollama offline")

        result = run_weekly_refresh(scrape=False, score=False, curate=True, plan_episode=True)

        assert result["steps"]["curate"]["success"] is True
        assert result["steps"]["plan"]["success"] is False
        assert "Ollama offline" in result["steps"]["plan"]["error"]

    @patch("weekly_topic_refresh.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_no_steps_returns_empty_results(self, mock_open, mock_mkdir):
        """Running with all steps disabled returns results with no step entries."""
        from weekly_topic_refresh import run_weekly_refresh

        result = run_weekly_refresh(scrape=False, score=False, curate=False, plan_episode=False)

        assert result["steps"] == {}
        assert "started_at" in result


class TestRunWeeklyRefreshScoring:
    """Tests for the scoring step specifically."""

    @patch("weekly_topic_refresh.TopicScorer")
    @patch("weekly_topic_refresh.Path.mkdir")
    @patch("builtins.open", new_callable=MagicMock)
    def test_score_no_scraped_files_fails(self, mock_open, mock_mkdir, mock_scorer_cls):
        """Scoring fails when no scraped topic files exist."""
        from weekly_topic_refresh import run_weekly_refresh

        with patch("weekly_topic_refresh.Path.glob", return_value=[]):
            result = run_weekly_refresh(scrape=False, score=True, curate=False, plan_episode=False)

        assert result["steps"]["score"]["success"] is False
        assert "No scraped topics found" in result["steps"]["score"]["error"]

    @patch("weekly_topic_refresh.TopicScorer")
    @patch("weekly_topic_refresh.Path.mkdir")
    def test_score_calculates_average(self, mock_mkdir, mock_scorer_cls):
        """Scoring step correctly calculates average score and recommended count."""
        from weekly_topic_refresh import run_weekly_refresh

        mock_scorer = mock_scorer_cls.return_value
        scored = [
            {"title": "a", "score": {"total": 6.0}},
            {"title": "b", "score": {"total": 8.0}},
        ]
        mock_scorer.score_topics.return_value = scored
        mock_scorer.save_scored_topics.return_value = Path("scored.json")
        mock_scorer.filter_recommended.return_value = [scored[1]]

        mock_file = MagicMock()
        mock_file.stat.return_value.st_mtime = 999
        mock_file_ctx = MagicMock()
        mock_file_ctx.__enter__ = Mock(return_value=mock_file_ctx)
        mock_file_ctx.__exit__ = Mock(return_value=False)

        with patch("weekly_topic_refresh.Path.glob", return_value=[mock_file]):
            with patch("builtins.open", return_value=mock_file_ctx):
                with patch("json.load", return_value={"topics": [{"t": 1}]}):
                    result = run_weekly_refresh(scrape=False, score=True, curate=False, plan_episode=False)

        assert result["steps"]["score"]["success"] is True
        assert result["steps"]["score"]["topics_scored"] == 2
        assert result["steps"]["score"]["recommended"] == 1
        assert result["steps"]["score"]["average_score"] == 7.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
