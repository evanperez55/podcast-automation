"""Tests for post_scheduled_content.py."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from post_scheduled_content import post_scheduled, _post_slot


class TestPostScheduled:
    """Tests for the post_scheduled orchestrator."""

    @patch("post_scheduled_content.ContentCalendar")
    def test_no_pending_slots(self, mock_cal_cls):
        """When no pending slots, returns empty list."""
        mock_cal = MagicMock()
        mock_cal.get_all_pending_slots.return_value = []
        mock_cal_cls.return_value = mock_cal

        results = post_scheduled()
        assert results == []

    @patch("post_scheduled_content.ContentCalendar")
    def test_dry_run_skips_posting(self, mock_cal_cls):
        """Dry run logs slots but does not post."""
        mock_cal = MagicMock()
        mock_cal.get_all_pending_slots.return_value = [
            {
                "episode_key": "ep_30",
                "slot_name": "clip_1",
                "slot_type": "clip_1",
                "content": {"caption": "test", "youtube_url": "https://yt.com/x"},
                "platforms": ["twitter"],
            }
        ]
        mock_cal_cls.return_value = mock_cal

        results = post_scheduled(dry_run=True)
        assert results[0]["status"] == "dry_run"
        mock_cal.mark_slot_uploaded.assert_not_called()

    @patch("post_scheduled_content._save_log")
    @patch("post_scheduled_content._init_uploaders")
    @patch("post_scheduled_content.ContentCalendar")
    def test_successful_post_marks_uploaded(self, mock_cal_cls, mock_init, mock_log):
        """Successful post calls mark_slot_uploaded."""
        mock_cal = MagicMock()
        mock_cal.get_all_pending_slots.return_value = [
            {
                "episode_key": "ep_30",
                "slot_name": "clip_1",
                "slot_type": "clip_1",
                "content": {"caption": "Hook text", "youtube_url": "https://yt.com/x"},
                "platforms": ["twitter"],
            }
        ]
        mock_cal_cls.return_value = mock_cal

        mock_twitter = MagicMock()
        mock_twitter.post_tweet.return_value = {"tweet_id": "123", "status": "success"}
        mock_init.return_value = {"twitter": mock_twitter}

        results = post_scheduled()
        assert len(results) == 1
        mock_cal.mark_slot_uploaded.assert_called_once()

    @patch("post_scheduled_content._save_log")
    @patch("post_scheduled_content._init_uploaders")
    @patch("post_scheduled_content.ContentCalendar")
    def test_failed_post_marks_failed(self, mock_cal_cls, mock_init, mock_log):
        """Failed post calls mark_slot_failed."""
        mock_cal = MagicMock()
        mock_cal.get_all_pending_slots.return_value = [
            {
                "episode_key": "ep_30",
                "slot_name": "clip_1",
                "slot_type": "clip_1",
                "content": {"caption": "test"},
                "platforms": ["twitter"],
            }
        ]
        mock_cal_cls.return_value = mock_cal

        mock_twitter = MagicMock()
        mock_twitter.post_tweet.side_effect = Exception("API error")
        mock_init.return_value = {"twitter": mock_twitter}

        post_scheduled()
        mock_cal.mark_slot_failed.assert_called_once()


class TestPostSlot:
    """Tests for _post_slot helper."""

    def test_clip_slot_posts_youtube_url(self):
        """Clip slot appends YouTube URL to caption."""
        mock_twitter = MagicMock()
        mock_twitter.post_tweet.return_value = {"tweet_id": "123"}

        slot = {
            "slot_type": "clip_1",
            "content": {
                "caption": "Hook text",
                "youtube_url": "https://youtube.com/watch?v=abc",
            },
            "platforms": ["twitter"],
        }
        results = _post_slot(slot, {"twitter": mock_twitter})
        assert "twitter" in results
        call_text = mock_twitter.post_tweet.call_args.kwargs["text"]
        assert "https://youtube.com/watch?v=abc" in call_text

    def test_teaser_slot_posts_text_only(self):
        """Teaser slot posts caption text without URL."""
        mock_twitter = MagicMock()
        mock_twitter.post_tweet.return_value = {"tweet_id": "456"}

        slot = {
            "slot_type": "teaser",
            "content": {"caption": "Something wild is coming tomorrow"},
            "platforms": ["twitter"],
        }
        results = _post_slot(slot, {"twitter": mock_twitter})
        assert "twitter" in results

    def test_skips_unavailable_platform(self):
        """Platforms not in uploaders dict are skipped."""
        slot = {
            "slot_type": "clip_1",
            "content": {"caption": "test"},
            "platforms": ["twitter", "bluesky"],
        }
        results = _post_slot(slot, {})
        assert results == {}

    def test_bluesky_posts_with_link_card(self):
        """Bluesky slot posts with URL as link card."""
        mock_bsky = MagicMock()
        mock_bsky.post.return_value = {"post_url": "https://bsky.app/post/123"}

        slot = {
            "slot_type": "clip_1",
            "content": {
                "caption": "Check this out",
                "youtube_url": "https://youtube.com/watch?v=abc",
                "clip_title": "Amazing Clip",
            },
            "platforms": ["bluesky"],
        }
        # No post_with_image method
        del mock_bsky.post_with_image

        results = _post_slot(slot, {"bluesky": mock_bsky})
        assert "bluesky" in results
        mock_bsky.post.assert_called_once()


class TestCarryForwardLogic:
    """Tests for prior result carry-forward in _post_slot."""

    def test_empty_dict_not_carried_forward(self):
        """An empty dict {} from a prior YouTube attempt must NOT be treated as success.

        This was the root cause of clip_7 failing to retry YouTube — the
        empty dict had no 'error' key so it was carried forward as a success.
        """
        mock_twitter = MagicMock()
        mock_twitter.post_tweet.return_value = {"tweet_id": "789", "status": "success"}

        slot = {
            "slot_type": "clip_7",
            "content": {
                "caption": "They ate their dead friends",
                "youtube_video_id": "Q8SeD33qz9M",
                "youtube_url": "https://youtube.com/watch?v=Q8SeD33qz9M",
            },
            "platforms": ["twitter", "youtube"],
            "upload_results": {
                "youtube": {},  # empty dict from prior failed attempt
                "twitter": {
                    "tweet_id": "123",
                    "status": "success",
                },
            },
        }
        results = _post_slot(slot, {"twitter": mock_twitter})
        # Twitter should be carried forward (real success)
        assert results["twitter"]["tweet_id"] == "123"
        # YouTube should NOT be carried forward — {} is not a success
        # It should have been retried (will fail here since no YouTube uploader,
        # but the key point is it wasn't carried forward as success)
        yt_result = results.get("youtube", {})
        assert yt_result != {}  # must not be the empty dict carried forward

    def test_none_result_not_carried_forward(self):
        """A None prior result should not be carried forward."""
        slot = {
            "slot_type": "clip_1",
            "content": {"caption": "test"},
            "platforms": ["instagram"],
            "upload_results": {
                "instagram": None,
            },
        }
        results = _post_slot(slot, {})
        assert "instagram" not in results

    def test_real_success_is_carried_forward(self):
        """A prior result with actual data IS carried forward."""
        slot = {
            "slot_type": "clip_1",
            "content": {"caption": "test"},
            "platforms": ["twitter"],
            "upload_results": {
                "twitter": {
                    "tweet_id": "123",
                    "tweet_url": "https://twitter.com/...",
                    "status": "success",
                },
            },
        }
        results = _post_slot(slot, {})
        assert results["twitter"]["tweet_id"] == "123"


class TestContentCalendarNewMethods:
    """Tests for update_slot_content and get_all_pending_slots."""

    def test_update_slot_content(self, tmp_path):
        """update_slot_content merges new keys into slot content."""
        from content_calendar import ContentCalendar

        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            cal = ContentCalendar()
            # Write initial data
            cal.save(
                {
                    "ep_30": {
                        "slots": {
                            "clip_1": {
                                "status": "pending",
                                "content": {"caption": "test"},
                            }
                        }
                    }
                }
            )
            cal.update_slot_content(
                "ep_30", "clip_1", {"youtube_url": "https://yt.com"}
            )
            data = cal.load_all()
            assert (
                data["ep_30"]["slots"]["clip_1"]["content"]["youtube_url"]
                == "https://yt.com"
            )
            assert data["ep_30"]["slots"]["clip_1"]["content"]["caption"] == "test"

    def test_update_slot_content_nonexistent(self, tmp_path):
        """update_slot_content silently ignores missing episodes."""
        from content_calendar import ContentCalendar

        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            cal = ContentCalendar()
            cal.save({})
            cal.update_slot_content("ep_99", "clip_1", {"url": "x"})
            # Should not raise

    def test_get_all_pending_slots(self, tmp_path):
        """get_all_pending_slots returns past-due pending slots."""
        from content_calendar import ContentCalendar

        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            cal = ContentCalendar()
            past = (datetime.now() - timedelta(hours=1)).isoformat()
            future = (datetime.now() + timedelta(hours=24)).isoformat()
            cal.save(
                {
                    "ep_30": {
                        "slots": {
                            "clip_1": {
                                "status": "pending",
                                "scheduled_at": past,
                                "slot_type": "clip_1",
                            },
                            "clip_2": {
                                "status": "pending",
                                "scheduled_at": future,
                                "slot_type": "clip_2",
                            },
                            "clip_3": {
                                "status": "uploaded",
                                "scheduled_at": past,
                                "slot_type": "clip_3",
                            },
                        }
                    }
                }
            )
            pending = cal.get_all_pending_slots()
            assert len(pending) == 1
            assert pending[0]["slot_name"] == "clip_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
