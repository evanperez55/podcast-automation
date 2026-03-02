"""Tests for scheduler module."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from scheduler import UploadScheduler
from config import Config


SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode Title",
    "episode_summary": "A great episode about testing.",
    "show_notes": "- Topic 1\n- Topic 2",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
        {"start_timestamp": "00:10:00", "title": "Main", "start_seconds": 600},
    ],
    "social_captions": {
        "youtube": "YT caption",
        "twitter": "TW caption",
        "instagram": "IG caption",
        "tiktok": "TT caption",
    },
}


class TestUploadSchedulerInit:
    """Tests for UploadScheduler.__init__."""

    @patch.dict("os.environ", {}, clear=True)
    def test_init_defaults(self):
        """All delays default to 0 when no env vars are set."""
        scheduler = UploadScheduler()
        assert scheduler.youtube_delay == 0
        assert scheduler.twitter_delay == 0
        assert scheduler.instagram_delay == 0
        assert scheduler.tiktok_delay == 0

    @patch.dict(
        "os.environ",
        {
            "SCHEDULE_YOUTUBE_DELAY_HOURS": "2",
            "SCHEDULE_TWITTER_DELAY_HOURS": "4",
            "SCHEDULE_INSTAGRAM_DELAY_HOURS": "6",
            "SCHEDULE_TIKTOK_DELAY_HOURS": "8",
        },
    )
    def test_init_with_env_vars(self):
        """Delays are read from environment variables."""
        scheduler = UploadScheduler()
        assert scheduler.youtube_delay == 2
        assert scheduler.twitter_delay == 4
        assert scheduler.instagram_delay == 6
        assert scheduler.tiktok_delay == 8


class TestIsSchedulingEnabled:
    """Tests for UploadScheduler.is_scheduling_enabled."""

    @patch.dict("os.environ", {}, clear=True)
    def test_scheduling_disabled(self):
        """Returns False when all delays are 0."""
        scheduler = UploadScheduler()
        assert scheduler.is_scheduling_enabled() is False

    @patch.dict("os.environ", {"SCHEDULE_INSTAGRAM_DELAY_HOURS": "3"})
    def test_scheduling_enabled(self):
        """Returns True when at least one delay is greater than 0."""
        scheduler = UploadScheduler()
        assert scheduler.is_scheduling_enabled() is True


class TestCreateSchedule:
    """Tests for UploadScheduler.create_schedule."""

    @patch.dict("os.environ", {}, clear=True)
    def test_create_schedule_no_delays(self):
        """Platforms dict is empty when all delays are 0."""
        scheduler = UploadScheduler()
        schedule = scheduler.create_schedule("ep25_folder", "ep25", SAMPLE_ANALYSIS)
        assert schedule["platforms"] == {}

    @patch.dict(
        "os.environ",
        {"SCHEDULE_YOUTUBE_DELAY_HOURS": "2"},
    )
    def test_create_schedule_youtube_only(self):
        """Only youtube appears in platforms when only its delay is set."""
        scheduler = UploadScheduler()
        schedule = scheduler.create_schedule(
            "ep25_folder",
            "ep25",
            SAMPLE_ANALYSIS,
            full_episode_video_path="/videos/ep25.mp4",
        )
        assert "youtube" in schedule["platforms"]
        assert "twitter" not in schedule["platforms"]
        assert "instagram" not in schedule["platforms"]
        assert "tiktok" not in schedule["platforms"]

        yt = schedule["platforms"]["youtube"]
        assert yt["status"] == "pending"
        assert yt["delay_hours"] == 2
        assert yt["full_episode_video_path"] == "/videos/ep25.mp4"
        assert yt["episode_title"] == "Test Episode Title"
        assert yt["social_captions"] == "YT caption"

    @patch.dict(
        "os.environ",
        {
            "SCHEDULE_YOUTUBE_DELAY_HOURS": "1",
            "SCHEDULE_TWITTER_DELAY_HOURS": "2",
            "SCHEDULE_INSTAGRAM_DELAY_HOURS": "3",
            "SCHEDULE_TIKTOK_DELAY_HOURS": "4",
        },
    )
    def test_create_schedule_all_platforms(self):
        """All four platforms appear when all delays are > 0."""
        scheduler = UploadScheduler()
        schedule = scheduler.create_schedule(
            "ep25_folder",
            "ep25",
            SAMPLE_ANALYSIS,
            video_clip_paths=["/clips/c1.mp4"],
            full_episode_video_path="/videos/ep25.mp4",
            mp3_path="/audio/ep25.mp3",
        )
        platforms = schedule["platforms"]
        assert set(platforms.keys()) == {"youtube", "twitter", "instagram", "tiktok"}
        for entry in platforms.values():
            assert entry["status"] == "pending"
            assert "publish_at" in entry

    @patch.dict(
        "os.environ",
        {"SCHEDULE_YOUTUBE_DELAY_HOURS": "1"},
    )
    def test_create_schedule_contains_metadata(self):
        """Schedule contains episode_number, episode_folder, and created_at."""
        scheduler = UploadScheduler()
        schedule = scheduler.create_schedule("ep25_folder", "ep25", SAMPLE_ANALYSIS)
        assert schedule["episode_number"] == "ep25"
        assert schedule["episode_folder"] == "ep25_folder"
        assert "created_at" in schedule
        # created_at should be a valid ISO datetime
        datetime.fromisoformat(schedule["created_at"])


class TestSaveAndLoadSchedule:
    """Tests for UploadScheduler.save_schedule and load_schedule."""

    @patch.dict("os.environ", {"SCHEDULE_YOUTUBE_DELAY_HOURS": "1"})
    def test_save_and_load_schedule(self, tmp_path, monkeypatch):
        """Round-trip: save then load returns identical schedule."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        scheduler = UploadScheduler()
        schedule = scheduler.create_schedule("ep25_folder", "ep25", SAMPLE_ANALYSIS)

        saved_path = scheduler.save_schedule("ep25_folder", schedule)
        assert saved_path.exists()
        assert saved_path.name == "upload_schedule.json"

        loaded = scheduler.load_schedule("ep25_folder")
        assert loaded == schedule

    @patch.dict("os.environ", {}, clear=True)
    def test_load_schedule_not_found(self, tmp_path, monkeypatch):
        """Returns None when schedule file does not exist."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)
        scheduler = UploadScheduler()
        result = scheduler.load_schedule("nonexistent_folder")
        assert result is None


class TestGetPendingUploads:
    """Tests for UploadScheduler.get_pending_uploads."""

    @patch.dict("os.environ", {}, clear=True)
    def test_get_pending_uploads_none_ready(self):
        """Returns empty list when publish_at is in the future."""
        scheduler = UploadScheduler()
        future = (datetime.now() + timedelta(hours=24)).isoformat()
        schedule = {
            "platforms": {
                "youtube": {"status": "pending", "publish_at": future},
            }
        }
        assert scheduler.get_pending_uploads(schedule) == []

    @patch.dict("os.environ", {}, clear=True)
    def test_get_pending_uploads_ready(self):
        """Returns entries whose publish_at is in the past."""
        scheduler = UploadScheduler()
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        schedule = {
            "platforms": {
                "twitter": {"status": "pending", "publish_at": past, "data": "tw"},
            }
        }
        pending = scheduler.get_pending_uploads(schedule)
        assert len(pending) == 1
        assert pending[0]["platform"] == "twitter"
        assert pending[0]["data"] == "tw"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_pending_uploads_already_uploaded(self):
        """Skips entries whose status is 'uploaded'."""
        scheduler = UploadScheduler()
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        schedule = {
            "platforms": {
                "youtube": {"status": "uploaded", "publish_at": past},
            }
        }
        assert scheduler.get_pending_uploads(schedule) == []


class TestMarkUploaded:
    """Tests for UploadScheduler.mark_uploaded."""

    @patch.dict("os.environ", {}, clear=True)
    def test_mark_uploaded(self):
        """Status changes to 'uploaded', upload_result and uploaded_at are stored."""
        scheduler = UploadScheduler()
        schedule = {
            "platforms": {
                "youtube": {
                    "status": "pending",
                    "publish_at": datetime.now().isoformat(),
                },
            }
        }
        result_data = {"video_id": "abc123", "url": "https://youtube.com/abc123"}
        updated = scheduler.mark_uploaded(schedule, "youtube", result_data)

        yt = updated["platforms"]["youtube"]
        assert yt["status"] == "uploaded"
        assert yt["upload_result"] == result_data
        assert "uploaded_at" in yt
        # uploaded_at should be a valid ISO datetime
        datetime.fromisoformat(yt["uploaded_at"])


class TestGetYoutubePublishAt:
    """Tests for UploadScheduler.get_youtube_publish_at."""

    @patch.dict("os.environ", {"SCHEDULE_YOUTUBE_DELAY_HOURS": "3"})
    def test_get_youtube_publish_at_enabled(self):
        """Returns an ISO datetime string when youtube delay > 0."""
        scheduler = UploadScheduler()
        result = scheduler.get_youtube_publish_at()
        assert result is not None
        publish_at = datetime.fromisoformat(result)
        # Should be roughly 3 hours from now (allow 10s tolerance)
        expected = datetime.now() + timedelta(hours=3)
        assert abs((publish_at - expected).total_seconds()) < 10

    @patch.dict("os.environ", {}, clear=True)
    def test_get_youtube_publish_at_disabled(self):
        """Returns None when youtube delay is 0."""
        scheduler = UploadScheduler()
        result = scheduler.get_youtube_publish_at()
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
