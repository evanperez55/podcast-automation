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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 0)
    @patch.object(Config, "SCHEDULE_TWITTER_DELAY_HOURS", 0)
    @patch.object(Config, "SCHEDULE_INSTAGRAM_DELAY_HOURS", 0)
    @patch.object(Config, "SCHEDULE_TIKTOK_DELAY_HOURS", 0)
    def test_init_defaults(self):
        """All delays default to 0 when no env vars are set."""
        scheduler = UploadScheduler()
        assert scheduler.youtube_delay == 0
        assert scheduler.twitter_delay == 0
        assert scheduler.instagram_delay == 0
        assert scheduler.tiktok_delay == 0

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 2)
    @patch.object(Config, "SCHEDULE_TWITTER_DELAY_HOURS", 4)
    @patch.object(Config, "SCHEDULE_INSTAGRAM_DELAY_HOURS", 6)
    @patch.object(Config, "SCHEDULE_TIKTOK_DELAY_HOURS", 8)
    def test_init_with_env_vars(self):
        """Delays are read from Config attributes."""
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

    @patch.object(Config, "SCHEDULE_INSTAGRAM_DELAY_HOURS", 3)
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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 2)
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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 1)
    @patch.object(Config, "SCHEDULE_TWITTER_DELAY_HOURS", 2)
    @patch.object(Config, "SCHEDULE_INSTAGRAM_DELAY_HOURS", 3)
    @patch.object(Config, "SCHEDULE_TIKTOK_DELAY_HOURS", 4)
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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 1)
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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 1)
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

    @patch.object(Config, "SCHEDULE_YOUTUBE_DELAY_HOURS", 3)
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


class TestMarkFailed:
    """Tests for UploadScheduler.mark_failed."""

    @patch.dict("os.environ", {}, clear=True)
    def test_mark_failed_sets_status(self):
        """Status changes to 'failed' after mark_failed."""
        scheduler = UploadScheduler()
        schedule = {
            "platforms": {
                "youtube": {
                    "status": "pending",
                    "publish_at": datetime.now().isoformat(),
                },
            }
        }
        updated = scheduler.mark_failed(schedule, "youtube", "timeout")
        assert updated["platforms"]["youtube"]["status"] == "failed"

    @patch.dict("os.environ", {}, clear=True)
    def test_mark_failed_stores_error(self):
        """Error message is stored in the platform entry."""
        scheduler = UploadScheduler()
        schedule = {
            "platforms": {
                "youtube": {
                    "status": "pending",
                    "publish_at": datetime.now().isoformat(),
                },
            }
        }
        updated = scheduler.mark_failed(schedule, "youtube", "connection refused")
        assert updated["platforms"]["youtube"]["error"] == "connection refused"

    @patch.dict("os.environ", {}, clear=True)
    def test_mark_failed_stores_failed_at(self):
        """failed_at is set to an ISO datetime string."""
        scheduler = UploadScheduler()
        schedule = {
            "platforms": {
                "twitter": {
                    "status": "pending",
                    "publish_at": datetime.now().isoformat(),
                },
            }
        }
        updated = scheduler.mark_failed(schedule, "twitter", "rate limit")
        assert "failed_at" in updated["platforms"]["twitter"]
        datetime.fromisoformat(updated["platforms"]["twitter"]["failed_at"])

    @patch.dict("os.environ", {}, clear=True)
    def test_mark_failed_unknown_platform_is_noop(self):
        """mark_failed does not raise for an unknown platform."""
        scheduler = UploadScheduler()
        schedule = {"platforms": {}}
        updated = scheduler.mark_failed(schedule, "nonexistent", "error")
        assert updated == {"platforms": {}}


class TestRunUploadScheduled:
    """Tests for pipeline.runner.run_upload_scheduled with real uploader dispatch."""

    def _make_schedule(self, platform="youtube"):
        """Return a minimal schedule dict with one pending past-due platform."""
        return {
            "episode_number": "ep25",
            "episode_folder": "ep_25",
            "created_at": datetime.now().isoformat(),
            "platforms": {
                platform: {
                    "status": "pending",
                    "publish_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "episode_title": "Test Title",
                    "episode_summary": "Summary",
                    "full_episode_video_path": "/output/ep_25/ep25.mp4",
                    "social_captions": "Test caption",
                }
            },
        }

    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner.YouTubeUploader")
    @patch("pipeline.runner.UploadScheduler")
    def test_upload_success(
        self,
        mock_scheduler_cls,
        mock_yt_cls,
        mock_notifier_cls,
        tmp_path,
        monkeypatch,
    ):
        """On success: upload method called once, mark_uploaded called, mark_failed not called."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)

        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "upload_schedule.json").write_text("{}", encoding="utf-8")

        schedule = self._make_schedule("youtube")
        mock_scheduler = mock_scheduler_cls.return_value
        mock_scheduler.load_schedule.return_value = schedule
        mock_scheduler.get_pending_uploads.return_value = [
            {**schedule["platforms"]["youtube"], "platform": "youtube"}
        ]
        mock_scheduler.mark_uploaded.return_value = schedule
        mock_scheduler.mark_failed.return_value = schedule

        upload_result = {"video_id": "abc123", "url": "https://youtube.com/abc123"}
        mock_yt_instance = mock_yt_cls.return_value
        mock_yt_instance.upload_episode.return_value = upload_result

        from pipeline.runner import run_upload_scheduled

        run_upload_scheduled()

        mock_yt_instance.upload_episode.assert_called_once()
        mock_scheduler.mark_uploaded.assert_called_once()
        mock_scheduler.mark_failed.assert_not_called()

    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner.YouTubeUploader")
    @patch("pipeline.runner.UploadScheduler")
    def test_upload_failure_after_retries(
        self,
        mock_scheduler_cls,
        mock_yt_cls,
        mock_notifier_cls,
        tmp_path,
        monkeypatch,
    ):
        """On upload failure: mark_failed called, notify_failure called, mark_uploaded NOT called."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)

        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "upload_schedule.json").write_text("{}", encoding="utf-8")

        schedule = self._make_schedule("youtube")
        mock_scheduler = mock_scheduler_cls.return_value
        mock_scheduler.load_schedule.return_value = schedule
        mock_scheduler.get_pending_uploads.return_value = [
            {**schedule["platforms"]["youtube"], "platform": "youtube"}
        ]
        mock_scheduler.mark_uploaded.return_value = schedule
        mock_scheduler.mark_failed.return_value = schedule

        mock_yt_instance = mock_yt_cls.return_value
        mock_yt_instance.upload_episode.side_effect = RuntimeError("upload failed")

        mock_notifier_instance = mock_notifier_cls.return_value

        from pipeline.runner import run_upload_scheduled

        run_upload_scheduled()

        mock_scheduler.mark_failed.assert_called_once()
        mock_notifier_instance.notify_failure.assert_called_once()
        mock_scheduler.mark_uploaded.assert_not_called()

    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner.YouTubeUploader")
    @patch("pipeline.runner.UploadScheduler")
    def test_no_silent_success(
        self,
        mock_scheduler_cls,
        mock_yt_cls,
        mock_notifier_cls,
        tmp_path,
        monkeypatch,
    ):
        """mark_uploaded is never called when the upload raises an exception."""
        monkeypatch.setattr(Config, "OUTPUT_DIR", tmp_path)

        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "upload_schedule.json").write_text("{}", encoding="utf-8")

        schedule = self._make_schedule("youtube")
        mock_scheduler = mock_scheduler_cls.return_value
        mock_scheduler.load_schedule.return_value = schedule
        mock_scheduler.get_pending_uploads.return_value = [
            {**schedule["platforms"]["youtube"], "platform": "youtube"}
        ]
        mock_scheduler.mark_uploaded.return_value = schedule
        mock_scheduler.mark_failed.return_value = schedule

        mock_yt_instance = mock_yt_cls.return_value
        mock_yt_instance.upload_episode.side_effect = ValueError("bad data")

        from pipeline.runner import run_upload_scheduled

        run_upload_scheduled()

        mock_scheduler.mark_uploaded.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
