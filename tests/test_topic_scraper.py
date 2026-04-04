"""Tests for TopicScraper class in topic_scraper.py."""

import json
import pytest
from unittest.mock import patch, Mock, MagicMock, mock_open
from pathlib import Path

from topic_scraper import TopicScraper


def _make_mock_post(title="Test Post", score=500, num_comments=50, selftext="body"):
    """Create a mock Reddit post object."""
    post = Mock()
    post.title = title
    post.permalink = "/r/test/comments/abc/test_post"
    post.score = score
    post.num_comments = num_comments
    post.created_utc = 1700000000.0
    post.selftext = selftext
    post.subreddit = Mock()
    post.subreddit.display_name = "test"
    return post


class TestTopicScraperInit:
    """Tests for TopicScraper initialization."""

    @patch.dict("os.environ", {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "secret"})
    @patch("topic_scraper.praw.Reddit")
    def test_init_with_reddit_credentials(self, mock_reddit_cls):
        """Initializes PRAW Reddit client when credentials are set."""
        mock_reddit_cls.return_value = Mock()
        scraper = TopicScraper()
        assert scraper.reddit is not None
        mock_reddit_cls.assert_called_once()

    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_credentials(self):
        """Reddit client is None when credentials are missing."""
        scraper = TopicScraper()
        assert scraper.reddit is None

    @patch.dict("os.environ", {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "secret"})
    @patch("topic_scraper.praw.Reddit", side_effect=Exception("auth failed"))
    def test_init_reddit_failure(self, mock_reddit_cls):
        """Reddit client is None when PRAW initialization fails."""
        scraper = TopicScraper()
        assert scraper.reddit is None


class TestScrapeRedditSubreddit:
    """Tests for TopicScraper.scrape_reddit_subreddit."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("topic_scraper.requests.get")
    def test_scrape_json_api_success(self, mock_get):
        """Scrapes via JSON API when no auth, returns topic list."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Wild headline",
                            "permalink": "/r/nottheonion/comments/xyz/wild",
                            "score": 1200,
                            "num_comments": 85,
                            "created_utc": 1700000000.0,
                            "selftext": "",
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = TopicScraper()
        topics = scraper.scrape_reddit_subreddit("nottheonion")

        assert len(topics) == 1
        assert topics[0]["title"] == "Wild headline"
        assert topics[0]["source"] == "r/nottheonion"
        assert topics[0]["source_type"] == "reddit"

    @patch.dict("os.environ", {"REDDIT_CLIENT_ID": "id", "REDDIT_CLIENT_SECRET": "secret"})
    @patch("topic_scraper.praw.Reddit")
    def test_scrape_praw_api_success(self, mock_reddit_cls):
        """Scrapes via PRAW when authenticated."""
        mock_post = _make_mock_post(title="PRAW topic")
        mock_subreddit = Mock()
        mock_subreddit.top.return_value = [mock_post]
        mock_reddit = Mock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_reddit_cls.return_value = mock_reddit

        scraper = TopicScraper()
        topics = scraper.scrape_reddit_subreddit("test", limit=5)

        assert len(topics) == 1
        assert topics[0]["title"] == "PRAW topic"

    @patch.dict("os.environ", {}, clear=True)
    @patch("topic_scraper.requests.get", side_effect=Exception("network error"))
    def test_scrape_failure_returns_empty(self, mock_get):
        """Returns empty list on scrape failure."""
        scraper = TopicScraper()
        topics = scraper.scrape_reddit_subreddit("nottheonion")
        assert topics == []


class TestScrapeMultipleSubreddits:
    """Tests for TopicScraper.scrape_multiple_subreddits."""

    @patch.dict("os.environ", {}, clear=True)
    @patch.object(TopicScraper, "scrape_reddit_subreddit")
    def test_scrape_multiple_aggregates(self, mock_scrape):
        """Scrapes multiple subreddits and combines results."""
        mock_scrape.side_effect = [
            [{"title": "Topic A", "source": "r/a"}],
            [{"title": "Topic B", "source": "r/b"}],
        ]
        scraper = TopicScraper()
        config = {"sub_a": {"time_filter": "week", "limit": 5}, "sub_b": {}}
        topics = scraper.scrape_multiple_subreddits(config)

        assert len(topics) == 2
        assert mock_scrape.call_count == 2


class TestDeduplicateTopics:
    """Tests for TopicScraper.deduplicate_topics."""

    @patch.dict("os.environ", {}, clear=True)
    def test_removes_exact_duplicates(self):
        """Removes topics with identical normalized titles."""
        scraper = TopicScraper()
        topics = [
            {"title": "Same Title"},
            {"title": "same title"},
            {"title": "Different Title"},
        ]
        result = scraper.deduplicate_topics(topics)
        assert len(result) == 2

    @patch.dict("os.environ", {}, clear=True)
    def test_no_duplicates_returns_all(self):
        """All unique topics are preserved."""
        scraper = TopicScraper()
        topics = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        result = scraper.deduplicate_topics(topics)
        assert len(result) == 3


class TestFilterByScore:
    """Tests for TopicScraper.filter_by_score."""

    @patch.dict("os.environ", {}, clear=True)
    def test_filters_low_engagement(self):
        """Only topics meeting both score and comment thresholds pass."""
        scraper = TopicScraper()
        topics = [
            {"title": "Hot", "score": 500, "num_comments": 50},
            {"title": "Low score", "score": 10, "num_comments": 50},
            {"title": "Low comments", "score": 500, "num_comments": 2},
        ]
        result = scraper.filter_by_score(topics, min_score=100, min_comments=10)
        assert len(result) == 1
        assert result[0]["title"] == "Hot"


class TestSaveScrapedTopics:
    """Tests for TopicScraper.save_scraped_topics."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("topic_scraper.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_writes_json(self, mock_file, mock_mkdir):
        """Saves topics to a JSON file and returns path."""
        scraper = TopicScraper()
        topics = [{"title": "Test"}]
        result = scraper.save_scraped_topics(topics, filename="test.json")

        assert isinstance(result, Path)
        mock_file.assert_called_once()
        mock_mkdir.assert_called_once_with(exist_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
