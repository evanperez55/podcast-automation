"""Tests for ContentCalendar module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from content_calendar import ContentCalendar


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _analysis_with_clips(n_clips: int = 2) -> dict:
    """Return a minimal analysis dict with n best_clips."""
    clips = [
        {"hook_caption": f"Clip {i} caption", "score": 0.9} for i in range(n_clips)
    ]
    return {"best_clips": clips}


def _analysis_no_clips() -> dict:
    return {"best_clips": []}


def _analysis_no_best_clips_key() -> dict:
    return {}


RELEASE_DATE = datetime(2026, 3, 19)


# ---------------------------------------------------------------------------
# class TestPlanEpisode
# ---------------------------------------------------------------------------


class TestPlanEpisode:
    """Tests for ContentCalendar.plan_episode()."""

    def test_generates_correct_slots_with_2_clips(self, tmp_path):
        """plan_episode with 2 clips produces 4 slots: teaser, episode, clip_1, clip_2."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(2),
                    video_clip_paths=["clip_a.mp4", "clip_b.mp4"],
                )

        slots = entry["slots"]
        assert len(slots) == 4
        slot_types = {s["slot_type"] for s in slots.values()}
        assert "teaser" in slot_types
        assert "episode" in slot_types
        assert "clip_1" in slot_types
        assert "clip_2" in slot_types

    def test_no_clips_skips_clip_slots(self, tmp_path):
        """plan_episode with 0 clips produces only teaser + episode (2 slots)."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(2),
                    video_clip_paths=[],
                )

        slots = entry["slots"]
        assert len(slots) == 2
        slot_types = {s["slot_type"] for s in slots.values()}
        assert "episode" in slot_types
        assert "teaser" in slot_types

    def test_one_clip_one_slot(self, tmp_path):
        """plan_episode with 1 clip produces 3 slots: teaser, episode, clip_1."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(1),
                    video_clip_paths=["clip_a.mp4"],
                )

        slots = entry["slots"]
        assert len(slots) == 3

    def test_cap_at_3_clips(self, tmp_path):
        """plan_episode caps clip slots at 3 even with more paths provided."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(2),
                    video_clip_paths=["c1.mp4", "c2.mp4", "c3.mp4", "c4.mp4", "c5.mp4"],
                )

        slots = entry["slots"]
        clip_slots = [s for s in slots.values() if s["slot_type"].startswith("clip_")]
        assert len(clip_slots) == 3

    def test_no_best_clips_skips_teaser(self, tmp_path):
        """plan_episode with no best_clips in analysis skips teaser slot."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                # analysis has no best_clips key
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_no_best_clips_key(),
                    video_clip_paths=["c1.mp4"],
                )

        slot_types = {s["slot_type"] for s in entry["slots"].values()}
        assert "teaser" not in slot_types

    def test_no_best_clips_with_empty_list_skips_teaser(self, tmp_path):
        """plan_episode with empty best_clips list skips teaser slot."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_no_clips(),
                    video_clip_paths=["c1.mp4"],
                )

        slot_types = {s["slot_type"] for s in entry["slots"].values()}
        assert "teaser" not in slot_types

    def test_no_duplicate_day_offsets(self, tmp_path):
        """No two slots share the same day_offset."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(3),
                    video_clip_paths=["c1.mp4", "c2.mp4", "c3.mp4"],
                )

        offsets = [s["day_offset"] for s in entry["slots"].values()]
        assert len(offsets) == len(set(offsets)), "Duplicate day offsets found"

    def test_idempotent(self, tmp_path):
        """Second call for same episode returns existing entry without overwriting."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                entry1 = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(2),
                    video_clip_paths=["c1.mp4", "c2.mp4"],
                )
                entry2 = cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(2),
                    video_clip_paths=["different.mp4"],  # changed — should be ignored
                )

        assert entry1 == entry2
        # Should still have original 2 clip slots
        clip_slots = [
            s for s in entry2["slots"].values() if s["slot_type"].startswith("clip_")
        ]
        assert len(clip_slots) == 2


# ---------------------------------------------------------------------------
# class TestSaveLoad
# ---------------------------------------------------------------------------


class TestSaveLoad:
    """Tests for ContentCalendar.save() and load_all()."""

    def test_atomic_write(self, tmp_path):
        """save() writes via .tmp + Path.replace() (no .tmp remains after save)."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                data = {"ep_29": {"slots": {}}}
                cal.save(data)

        calendar_file = tmp_path / "content_calendar.json"
        tmp_file = tmp_path / "content_calendar.json.tmp"
        assert calendar_file.exists(), "calendar file should exist after save"
        assert not tmp_file.exists(), ".tmp file should be removed after atomic replace"

    def test_load_missing_file_returns_empty(self, tmp_path):
        """load_all() returns empty dict when file doesn't exist."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                result = cal.load_all()

        assert result == {}

    def test_round_trip(self, tmp_path):
        """Data saved then loaded is identical."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                data = {"ep_42": {"slots": {"episode": {"status": "pending"}}}}
                cal.save(data)
                loaded = cal.load_all()

        assert loaded == data


# ---------------------------------------------------------------------------
# class TestGetPendingSlots
# ---------------------------------------------------------------------------


class TestGetPendingSlots:
    """Tests for ContentCalendar.get_pending_slots()."""

    def _make_slot(self, status: str, scheduled_at: datetime) -> dict:
        return {
            "slot_type": "episode",
            "day_offset": 0,
            "scheduled_at": scheduled_at.isoformat(),
            "platforms": ["youtube"],
            "status": status,
        }

    def test_returns_past_due_pending(self, tmp_path):
        """Pending slot scheduled in the past is returned."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                past = datetime.now() - timedelta(hours=1)
                episode_data = {
                    "slots": {
                        "episode": self._make_slot("pending", past),
                    }
                }
                result = cal.get_pending_slots(episode_data)

        assert len(result) == 1
        assert result[0]["slot_type"] == "episode"

    def test_skips_uploaded(self, tmp_path):
        """Uploaded slot is not returned."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                past = datetime.now() - timedelta(hours=1)
                episode_data = {
                    "slots": {
                        "episode": self._make_slot("uploaded", past),
                    }
                }
                result = cal.get_pending_slots(episode_data)

        assert result == []

    def test_skips_future(self, tmp_path):
        """Pending slot scheduled in the future is not returned."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path

            with patch("content_calendar.PostingTimeOptimizer"):
                cal = ContentCalendar()
                future = datetime.now() + timedelta(hours=2)
                episode_data = {
                    "slots": {
                        "episode": self._make_slot("pending", future),
                    }
                }
                result = cal.get_pending_slots(episode_data)

        assert result == []


# ---------------------------------------------------------------------------
# class TestMarkSlot
# ---------------------------------------------------------------------------


class TestMarkSlot:
    """Tests for mark_slot_uploaded() and mark_slot_failed()."""

    def test_mark_uploaded(self, tmp_path):
        """mark_slot_uploaded sets status=uploaded, stores upload_results."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(1),
                    video_clip_paths=["c1.mp4"],
                )
                cal.mark_slot_uploaded("ep_29", "episode", {"video_id": "abc123"})
                data = cal.load_all()

        slot = data["ep_29"]["slots"]["episode"]
        assert slot["status"] == "uploaded"
        assert slot["upload_results"] == {"video_id": "abc123"}
        assert slot["uploaded_at"] is not None

    def test_mark_failed(self, tmp_path):
        """mark_slot_failed sets status=failed with error message."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                cal.plan_episode(
                    episode_number=29,
                    release_date=RELEASE_DATE,
                    analysis=_analysis_with_clips(1),
                    video_clip_paths=["c1.mp4"],
                )
                cal.mark_slot_failed("ep_29", "episode", "Rate limit exceeded")
                data = cal.load_all()

        slot = data["ep_29"]["slots"]["episode"]
        assert slot["status"] == "failed"
        assert "Rate limit exceeded" in slot.get("error", "")


# ---------------------------------------------------------------------------
# class TestSlotDatetime
# ---------------------------------------------------------------------------


class TestSlotDatetime:
    """Tests for _slot_datetime() helper."""

    def test_uses_optimizer_hour(self, tmp_path):
        """When PostingTimeOptimizer returns a datetime, its hour is used."""
        optimal_dt = datetime(2026, 3, 25, 9, 0, 0)  # hour = 9

        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = optimal_dt
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                result = cal._slot_datetime(RELEASE_DATE, 0, "youtube")

        assert result.hour == 9

    def test_falls_back_to_config_hour(self, tmp_path):
        """When optimizer returns None, Config posting hour is used."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                result = cal._slot_datetime(RELEASE_DATE, 0, "youtube")

        assert result.hour == 14

    def test_falls_back_twitter_config_hour(self, tmp_path):
        """When optimizer returns None for twitter, Twitter config hour is used."""
        with patch("content_calendar.Config") as mock_cfg:
            mock_cfg.CONTENT_CALENDAR_ENABLED = True
            mock_cfg.TOPIC_DATA_DIR = tmp_path
            mock_cfg.SCHEDULE_YOUTUBE_POSTING_HOUR = 14
            mock_cfg.SCHEDULE_TWITTER_POSTING_HOUR = 10
            mock_cfg.SCHEDULE_INSTAGRAM_POSTING_HOUR = 12
            mock_cfg.SCHEDULE_TIKTOK_POSTING_HOUR = 12

            with patch("content_calendar.PostingTimeOptimizer") as mock_pto_cls:
                mock_pto = MagicMock()
                mock_pto.get_optimal_publish_at.return_value = None
                mock_pto_cls.return_value = mock_pto

                cal = ContentCalendar()
                result = cal._slot_datetime(RELEASE_DATE, -1, "twitter")

        assert result.hour == 10
