"""Tests for post_daily_content.py — daily fake problem posting."""

import json
import pytest
from unittest.mock import patch, Mock, mock_open
from pathlib import Path

from post_daily_content import post_daily, _save_log


SAMPLE_CONTENT = {
    "twitter": "Today's fake problem: My coffee is too hot but also too cold",
    "bluesky": "Fake Problem of the Day: overthinking coffee temperature",
}


class TestPostDailyDryRun:
    """Tests for post_daily in dry-run mode."""

    @patch("post_daily_content._save_log")
    @patch("post_daily_content.DailyContentGenerator")
    def test_dry_run_generates_but_skips_posting(self, mock_gen_cls, mock_save):
        """Dry run generates content and saves log but does not post."""
        mock_gen = Mock()
        mock_gen.enabled = True
        mock_gen.generate_fake_problem.return_value = SAMPLE_CONTENT
        mock_gen_cls.return_value = mock_gen

        result = post_daily(dry_run=True)

        assert result is not None
        assert result["posted"] is False
        assert result["content"] == SAMPLE_CONTENT
        mock_save.assert_called_once()

    @patch("post_daily_content._save_log")
    @patch("post_daily_content.DailyContentGenerator")
    def test_dry_run_with_topic_hint(self, mock_gen_cls, mock_save):
        """Topic hint is passed to generate_fake_problem."""
        mock_gen = Mock()
        mock_gen.enabled = True
        mock_gen.generate_fake_problem.return_value = SAMPLE_CONTENT
        mock_gen_cls.return_value = mock_gen

        post_daily(dry_run=True, topic="parking")
        mock_gen.generate_fake_problem.assert_called_once_with(topic_hint="parking")


class TestPostDailyDisabled:
    """Tests for post_daily when generator is disabled."""

    @patch("post_daily_content.DailyContentGenerator")
    def test_disabled_returns_none(self, mock_gen_cls):
        """Returns None when generator is disabled."""
        mock_gen = Mock()
        mock_gen.enabled = False
        mock_gen_cls.return_value = mock_gen

        result = post_daily()
        assert result is None


class TestPostDailyGenerationFailure:
    """Tests for post_daily when content generation fails."""

    @patch("post_daily_content.DailyContentGenerator")
    def test_generation_failure_returns_none(self, mock_gen_cls):
        """Returns None when generate_fake_problem returns None."""
        mock_gen = Mock()
        mock_gen.enabled = True
        mock_gen.generate_fake_problem.return_value = None
        mock_gen_cls.return_value = mock_gen

        result = post_daily()
        assert result is None


class TestPostDailyPosting:
    """Tests for post_daily actual posting flow."""

    @patch("post_daily_content._save_log")
    @patch("post_daily_content.DailyContentGenerator")
    def test_posts_to_twitter_success(self, mock_gen_cls, mock_save):
        """Posts to Twitter and records result."""
        mock_gen = Mock()
        mock_gen.enabled = True
        mock_gen.generate_fake_problem.return_value = SAMPLE_CONTENT
        mock_gen_cls.return_value = mock_gen

        mock_twitter = Mock()
        mock_twitter.post_tweet.return_value = {"id": "12345"}

        with patch.dict("sys.modules", {}):
            with patch(
                "post_daily_content.TwitterUploader",
                create=True,
            ):
                # The import happens inside the function, so we patch the module import
                pass

        # Simpler approach: patch the import inside the function
        with patch("builtins.__import__", wraps=__import__) as mock_import:
            mock_twitter_mod = Mock()
            mock_twitter_mod.TwitterUploader.return_value = mock_twitter

            original_import = __import__

            def side_effect(name, *args, **kwargs):
                if name == "uploaders.twitter_uploader":
                    return mock_twitter_mod
                return original_import(name, *args, **kwargs)

            mock_import.side_effect = side_effect

            result = post_daily(dry_run=False)

        assert result is not None
        assert result["posted"] is True

    @patch("post_daily_content._save_log")
    @patch("post_daily_content.DailyContentGenerator")
    def test_twitter_import_failure_continues(self, mock_gen_cls, mock_save):
        """Twitter import failure is caught and logged, does not crash."""
        mock_gen = Mock()
        mock_gen.enabled = True
        mock_gen.generate_fake_problem.return_value = SAMPLE_CONTENT
        mock_gen_cls.return_value = mock_gen

        original_import = __import__

        def fail_twitter(name, *args, **kwargs):
            if name == "uploaders.twitter_uploader":
                raise ValueError("Twitter API credentials not configured")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fail_twitter):
            result = post_daily(dry_run=False)

        assert result is not None
        assert result["posted"] is True
        assert "error" in result.get("twitter_result", {})


class TestSaveLog:
    """Tests for _save_log helper."""

    @patch("post_daily_content.Config")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_log_appends_jsonl(self, mock_file, mock_config):
        """Appends JSON line to post_log.jsonl."""
        mock_config.OUTPUT_DIR = Path("/tmp/output")
        with patch.object(Path, "mkdir"):
            _save_log({"content": "test", "posted": True})
        mock_file.assert_called_once()
        written = mock_file().write.call_args[0][0]
        parsed = json.loads(written.strip())
        assert parsed["content"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
