"""Tests for Reddit uploader."""

import pytest
from unittest.mock import patch, MagicMock

import praw

from uploaders.reddit_uploader import RedditUploader, create_reddit_caption


class TestRedditUploaderInit:
    """Tests for RedditUploader initialization."""

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_init_success(self, mock_config, mock_reddit):
        """Valid credentials should initialize successfully."""
        mock_config.REDDIT_CLIENT_ID = "client_id"
        mock_config.REDDIT_CLIENT_SECRET = "client_secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"
        uploader = RedditUploader()
        assert uploader.client_id == "client_id"
        mock_reddit.assert_called_once()

    @patch("uploaders.reddit_uploader.Config")
    def test_init_missing_credentials(self, mock_config):
        """Missing credentials should raise ValueError."""
        mock_config.REDDIT_CLIENT_ID = None
        mock_config.REDDIT_CLIENT_SECRET = None
        mock_config.REDDIT_USERNAME = None
        mock_config.REDDIT_PASSWORD = None
        with pytest.raises(ValueError, match="Reddit API credentials not configured"):
            RedditUploader()

    @patch("uploaders.reddit_uploader.Config")
    def test_init_partial_credentials(self, mock_config):
        """Partial credentials should raise ValueError."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = None
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        with pytest.raises(ValueError):
            RedditUploader()


class TestRedditPostLink:
    """Tests for RedditUploader.post_link."""

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_post_link_success(self, mock_config, mock_reddit_cls):
        """Successful link post returns post info."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"

        mock_submission = MagicMock()
        mock_submission.id = "abc123"
        mock_submission.permalink = "/r/podcasts/comments/abc123/test/"

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit.return_value = mock_submission
        mock_reddit_cls.return_value = mock_reddit

        uploader = RedditUploader()
        result = uploader.post_link(
            subreddit="podcasts",
            title="New Episode!",
            url="https://youtube.com/watch?v=abc",
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["post_id"] == "abc123"
        assert result["subreddit"] == "podcasts"

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_post_link_api_error(self, mock_config, mock_reddit_cls):
        """Reddit API error returns None."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit.side_effect = (
            praw.exceptions.RedditAPIException(
                [["SUBREDDIT_NOEXIST", "Not found", "subreddit"]]
            )
        )
        mock_reddit_cls.return_value = mock_reddit

        uploader = RedditUploader()
        result = uploader.post_link(
            subreddit="nonexistent",
            title="Test",
            url="https://example.com",
        )
        assert result is None

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_post_link_title_truncated(self, mock_config, mock_reddit_cls):
        """Title longer than 300 chars should be truncated."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"

        mock_submission = MagicMock()
        mock_submission.id = "abc123"
        mock_submission.permalink = "/r/podcasts/comments/abc123/test/"

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit.return_value = mock_submission
        mock_reddit_cls.return_value = mock_reddit

        uploader = RedditUploader()
        long_title = "a" * 500
        uploader.post_link("podcasts", long_title, "https://example.com")

        call_kwargs = mock_reddit.subreddit.return_value.submit.call_args.kwargs
        assert len(call_kwargs["title"]) == 300


class TestRedditPostText:
    """Tests for RedditUploader.post_text."""

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_post_text_success(self, mock_config, mock_reddit_cls):
        """Successful text post returns post info."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"

        mock_submission = MagicMock()
        mock_submission.id = "def456"
        mock_submission.permalink = "/r/comedy/comments/def456/test/"

        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value.submit.return_value = mock_submission
        mock_reddit_cls.return_value = mock_reddit

        uploader = RedditUploader()
        result = uploader.post_text(
            subreddit="comedy",
            title="Discussion Thread",
            body="What did you think of this episode?",
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["subreddit"] == "comedy"


class TestRedditEpisodeAnnouncement:
    """Tests for RedditUploader.post_episode_announcement."""

    @patch.object(RedditUploader, "post_link", return_value={"status": "success"})
    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_announcement_with_youtube(self, mock_config, mock_reddit, mock_post):
        """With YouTube URL, posts link to each subreddit."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"
        mock_config.REDDIT_SUBREDDITS = ["podcasts", "comedy"]
        mock_config.PODCAST_NAME = "Fake Problems Podcast"

        uploader = RedditUploader()
        results = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
            youtube_url="https://youtube.com/watch?v=abc",
            episode_title="How Far Would You Go",
        )

        assert len(results) == 2
        assert mock_post.call_count == 2

    @patch.object(RedditUploader, "post_text", return_value={"status": "success"})
    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_announcement_without_youtube(self, mock_config, mock_reddit, mock_post):
        """Without YouTube URL, posts text to each subreddit."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"
        mock_config.REDDIT_SUBREDDITS = ["podcasts"]
        mock_config.PODCAST_NAME = "Fake Problems Podcast"

        uploader = RedditUploader()
        results = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
        )

        assert len(results) == 1
        mock_post.assert_called_once()

    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_announcement_no_subreddits(self, mock_config, mock_reddit):
        """No configured subreddits returns empty list."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"
        mock_config.REDDIT_SUBREDDITS = []

        uploader = RedditUploader()
        results = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
        )
        assert results == []

    @patch.object(RedditUploader, "post_link", return_value={"status": "success"})
    @patch("uploaders.reddit_uploader.praw.Reddit")
    @patch("uploaders.reddit_uploader.Config")
    def test_announcement_custom_subreddits(self, mock_config, mock_reddit, mock_post):
        """Custom subreddit list overrides config."""
        mock_config.REDDIT_CLIENT_ID = "id"
        mock_config.REDDIT_CLIENT_SECRET = "secret"
        mock_config.REDDIT_USERNAME = "user"
        mock_config.REDDIT_PASSWORD = "pass"
        mock_config.REDDIT_USER_AGENT = "TestAgent/1.0"
        mock_config.REDDIT_SUBREDDITS = ["default"]
        mock_config.PODCAST_NAME = "Test Podcast"

        uploader = RedditUploader()
        results = uploader.post_episode_announcement(
            episode_number=30,
            episode_summary="Great episode",
            youtube_url="https://youtube.com/watch?v=abc",
            subreddits=["custom1", "custom2"],
        )

        assert len(results) == 2
        # Should use custom subreddits, not config default
        calls = mock_post.call_args_list
        assert calls[0].kwargs["subreddit"] == "custom1"
        assert calls[1].kwargs["subreddit"] == "custom2"


class TestCreateRedditCaption:
    """Tests for create_reddit_caption helper."""

    def test_caption_with_youtube(self):
        """Caption includes YouTube link."""
        result = create_reddit_caption(
            30, "Test Episode", "Summary", "https://youtube.com/watch?v=abc"
        )
        assert "Episode 30" in result
        assert "https://youtube.com/watch?v=abc" in result
        assert "Test Episode" in result

    def test_caption_without_youtube(self):
        """Caption without YouTube link omits watch link."""
        result = create_reddit_caption(30, "Test Episode", "Summary")
        assert "Episode 30" in result
        assert "Watch" not in result

    def test_caption_has_discussion_prompt(self):
        """Caption includes discussion prompt."""
        result = create_reddit_caption(30, "Test", "Summary")
        assert "thoughts" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
