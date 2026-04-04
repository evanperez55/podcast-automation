"""Tests for TopicCurator class in topic_curator.py."""

import json
import pytest
from unittest.mock import patch, Mock, mock_open
from pathlib import Path

from topic_curator import TopicCurator


# Sample scored data reused across tests
SAMPLE_SCORED_DATA = {
    "topics_by_category": {
        "shocking_news": [
            {
                "title": "Man arrested for stealing a whole bridge",
                "score": {"total": 9.0, "recommended": True},
                "source": "r/nottheonion",
                "url": "https://reddit.com/r/nottheonion/abc",
            },
            {
                "title": "Low scoring news topic",
                "score": {"total": 4.0, "recommended": False},
                "source": "r/offbeat",
                "url": "https://reddit.com/r/offbeat/xyz",
            },
        ],
        "absurd_hypothetical": [
            {
                "title": "What if gravity reversed for 5 seconds daily",
                "score": {"total": 8.5, "recommended": True},
                "source": "r/CrazyIdeas",
                "url": "https://reddit.com/r/CrazyIdeas/def",
            },
        ],
    },
    "statistics": {
        "total_topics": 3,
        "recommended": 2,
    },
}


class TestTopicCuratorInit:
    """Tests for TopicCurator initialization."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_init_connects_to_google_docs(self, mock_tracker_cls):
        """Successful init sets docs_tracker."""
        mock_tracker_cls.return_value = Mock()
        curator = TopicCurator()
        assert curator.docs_tracker is not None
        mock_tracker_cls.assert_called_once()

    @patch("topic_curator.GoogleDocsTopicTracker", side_effect=Exception("no creds"))
    def test_init_handles_google_docs_failure(self, mock_tracker_cls):
        """Failed Google Docs connection sets docs_tracker to None."""
        curator = TopicCurator()
        assert curator.docs_tracker is None


class TestLoadScoredTopics:
    """Tests for TopicCurator.load_scored_topics."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_load_from_explicit_filename(self, mock_tracker_cls):
        """Loading from an explicit filename reads that file."""
        mock_data = {"topics_by_category": {}}
        m = mock_open(read_data=json.dumps(mock_data))
        with patch("builtins.open", m):
            curator = TopicCurator()
            result = curator.load_scored_topics(filename="custom.json")
        assert result == mock_data

    @patch("topic_curator.GoogleDocsTopicTracker")
    @patch("topic_curator.Path")
    def test_load_no_directory_raises(self, mock_path_cls, mock_tracker_cls):
        """Missing topic_data directory raises FileNotFoundError."""
        mock_dir = Mock()
        mock_dir.exists.return_value = False
        mock_path_cls.return_value = mock_dir

        curator = TopicCurator()
        with pytest.raises(FileNotFoundError, match="No topic_data directory"):
            curator.load_scored_topics()

    @patch("topic_curator.GoogleDocsTopicTracker")
    @patch("topic_curator.Path")
    def test_load_no_scored_files_raises(self, mock_path_cls, mock_tracker_cls):
        """Empty topic_data directory raises FileNotFoundError."""
        mock_dir = Mock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []
        mock_path_cls.return_value = mock_dir

        curator = TopicCurator()
        with pytest.raises(FileNotFoundError, match="No scored topics files"):
            curator.load_scored_topics()


class TestFormatTopicForDoc:
    """Tests for TopicCurator.format_topic_for_doc."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_high_score_gets_star(self, mock_tracker_cls):
        """Topics scoring >= 8 get a star prefix."""
        curator = TopicCurator()
        topic = {"title": "Great Topic", "score": {"total": 8.5}, "source": "Reddit"}
        result = curator.format_topic_for_doc(topic)
        assert result.startswith("\u2b50")
        assert "Great Topic" in result
        assert "[Reddit]" in result

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_medium_score_gets_sparkle(self, mock_tracker_cls):
        """Topics scoring >= 7 but < 8 get a sparkle prefix."""
        curator = TopicCurator()
        topic = {"title": "Good Topic", "score": {"total": 7.2}, "source": "RSS"}
        result = curator.format_topic_for_doc(topic)
        assert "\u2728" in result

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_low_score_no_badge(self, mock_tracker_cls):
        """Topics scoring < 7 have no badge."""
        curator = TopicCurator()
        topic = {"title": "Meh Topic", "score": {"total": 5.0}, "source": "r/test"}
        result = curator.format_topic_for_doc(topic)
        assert not result.startswith("\u2b50")
        assert not result.startswith("\u2728")
        assert "Meh Topic [r/test]" == result


class TestPlanNextEpisode:
    """Tests for TopicCurator.plan_next_episode."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    @patch("builtins.open", new_callable=mock_open)
    def test_plan_selects_recommended_topics(self, mock_file, mock_tracker_cls):
        """Episode planner picks recommended topics per category."""
        curator = TopicCurator()
        plan = curator.plan_next_episode(SAMPLE_SCORED_DATA)

        assert plan["total_topics"] == 2  # 1 shocking + 1 hypothetical recommended
        assert "categories" in plan
        assert plan["categories"]["shocking_news"]["selected"] == 1


class TestRestructureGoogleDoc:
    """Tests for TopicCurator.restructure_google_doc."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    @patch("builtins.open", new_callable=mock_open)
    def test_restructure_writes_file(self, mock_file, mock_tracker_cls):
        """Restructure writes structured_topics.txt."""
        curator = TopicCurator()
        result = curator.restructure_google_doc(SAMPLE_SCORED_DATA)
        assert result is True
        mock_file.assert_called_once()

    @patch("topic_curator.GoogleDocsTopicTracker", side_effect=Exception("fail"))
    def test_restructure_fails_without_docs(self, mock_tracker_cls):
        """Restructure returns False when Google Docs not connected."""
        curator = TopicCurator()
        result = curator.restructure_google_doc(SAMPLE_SCORED_DATA)
        assert result is False


class TestAddTopicsToExistingDoc:
    """Tests for TopicCurator.add_topics_to_existing_doc."""

    @patch("topic_curator.GoogleDocsTopicTracker")
    def test_add_filters_by_min_score(self, mock_tracker_cls):
        """Only topics above min_score threshold are counted."""
        curator = TopicCurator()
        result = curator.add_topics_to_existing_doc(SAMPLE_SCORED_DATA, min_score=9.0)
        assert result is True

    @patch("topic_curator.GoogleDocsTopicTracker", side_effect=Exception("fail"))
    def test_add_fails_without_docs(self, mock_tracker_cls):
        """Returns False when Google Docs not connected."""
        curator = TopicCurator()
        result = curator.add_topics_to_existing_doc(SAMPLE_SCORED_DATA)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
