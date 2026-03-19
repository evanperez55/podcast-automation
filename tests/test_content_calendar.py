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


# ---------------------------------------------------------------------------
# class TestDryRunDisplay
# ---------------------------------------------------------------------------


class TestDryRunDisplay:
    """Tests for ContentCalendar.get_calendar_display() used in dry_run."""

    def _make_calendar(self, tmp_path):
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
                return cal, mock_cfg

    def test_get_calendar_display_returns_slots_with_labels(self, tmp_path):
        """get_calendar_display returns list of dicts with label, dt, type, platforms."""
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
                slots = cal.get_calendar_display(
                    episode_number="XX",
                    release_date=RELEASE_DATE,
                )

        assert len(slots) >= 2  # at minimum teaser + episode
        for slot in slots:
            assert "label" in slot, "slot must have 'label'"
            assert "dt" in slot, "slot must have 'dt'"
            assert "type" in slot, "slot must have 'type'"
            assert "platforms" in slot, "slot must have 'platforms'"
            assert isinstance(slot["dt"], datetime)
            assert isinstance(slot["platforms"], list)

    def test_display_no_duplicate_days(self, tmp_path):
        """No two slots in get_calendar_display share the same calendar date."""
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
                slots = cal.get_calendar_display(
                    episode_number="XX",
                    release_date=RELEASE_DATE,
                )

        dates = [s["dt"].date() for s in slots]
        assert len(dates) == len(set(dates)), (
            "Duplicate dates found in calendar display"
        )


# ---------------------------------------------------------------------------
# class TestDistributeIntegration
# ---------------------------------------------------------------------------


class TestDistributeIntegration:
    """Tests for ContentCalendar.plan_episode() wiring in distribute step."""

    def test_distribute_calls_plan_episode(self, tmp_path):
        """run_distribute calls ContentCalendar.plan_episode() with correct args."""
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        episode_output_dir = tmp_path / "ep_29"
        episode_output_dir.mkdir()

        ctx = PipelineContext(
            episode_folder="ep_29",
            episode_number=29,
            episode_output_dir=episode_output_dir,
            timestamp="20260319_120000",
            audio_file=tmp_path / "ep29.wav",
            analysis={
                "episode_title": "Test Episode",
                "best_clips": [{"hook_caption": "test", "score": 0.9}],
                "social_captions": {},
                "chapters": [],
            },
            mp3_path=tmp_path / "ep29.mp3",
            video_clip_paths=["clip1.mp4"],
            full_episode_video_path=str(tmp_path / "ep29_full.mp4"),
            test_mode=True,
            transcript_path=None,
            transcript_data={"segments": [], "duration": 3600},
        )

        mock_calendar = MagicMock()
        mock_calendar.enabled = True
        mock_calendar.plan_episode.return_value = {"slots": {}}

        mock_calendar_cls = MagicMock(return_value=mock_calendar)

        components = {"uploaders": {}}

        # ContentCalendar is imported inside distribute's try block, so patch at source
        with patch("content_calendar.ContentCalendar", mock_calendar_cls):
            run_distribute(ctx, components)

        # plan_episode should have been called
        mock_calendar.plan_episode.assert_called_once()
        call_kwargs = mock_calendar.plan_episode.call_args
        assert call_kwargs.kwargs.get("episode_number") == 29 or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] == 29
        )

    def test_distribute_skips_calendar_when_disabled(self, tmp_path):
        """run_distribute skips calendar when ContentCalendar.enabled is False."""
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        episode_output_dir = tmp_path / "ep_29"
        episode_output_dir.mkdir()

        ctx = PipelineContext(
            episode_folder="ep_29",
            episode_number=29,
            episode_output_dir=episode_output_dir,
            timestamp="20260319_120000",
            audio_file=tmp_path / "ep29.wav",
            analysis={
                "episode_title": "Test Episode",
                "best_clips": [],
                "social_captions": {},
                "chapters": [],
            },
            mp3_path=tmp_path / "ep29.mp3",
            video_clip_paths=[],
            full_episode_video_path=None,
            test_mode=True,
            transcript_path=None,
            transcript_data={"segments": [], "duration": 3600},
        )

        mock_calendar = MagicMock()
        mock_calendar.enabled = False

        mock_calendar_cls = MagicMock(return_value=mock_calendar)

        components = {"uploaders": {}}

        # ContentCalendar is imported inside distribute's try block, so patch at source
        with patch("content_calendar.ContentCalendar", mock_calendar_cls):
            run_distribute(ctx, components)

        mock_calendar.plan_episode.assert_not_called()


# ---------------------------------------------------------------------------
# class TestUploadScheduledIntegration
# ---------------------------------------------------------------------------


class TestUploadScheduledIntegration:
    """Tests for ContentCalendar slot dispatch in run_upload_scheduled()."""

    def test_fires_past_due_calendar_slots(self, tmp_path, monkeypatch):
        """run_upload_scheduled dispatches past-due pending calendar slots."""
        from pipeline import runner

        past = datetime.now() - timedelta(hours=1)
        mock_slot = {
            "slot_name": "episode",
            "slot_type": "episode",
            "platforms": ["youtube"],
            "content": {
                "title": "Test Ep",
                "video_path": "ep29.mp4",
                "description": "desc",
            },
        }

        mock_calendar = MagicMock()
        mock_calendar.enabled = True
        mock_calendar.load_all.return_value = {
            "ep_29": {
                "slots": {
                    "episode": {
                        "slot_type": "episode",
                        "scheduled_at": past.isoformat(),
                        "platforms": ["youtube"],
                        "status": "pending",
                    }
                }
            }
        }
        mock_calendar.get_pending_slots.return_value = [mock_slot]

        mock_yt_uploader = MagicMock()
        mock_yt_uploader.upload_episode.return_value = {"video_id": "abc"}

        # Patch output dir to tmp_path (no schedule files)
        monkeypatch.setattr(runner.Config, "OUTPUT_DIR", tmp_path)

        # ContentCalendar is imported locally inside run_upload_scheduled, patch at source
        with patch(
            "content_calendar.ContentCalendar", MagicMock(return_value=mock_calendar)
        ):
            with patch(
                "pipeline.runner.YouTubeUploader",
                MagicMock(return_value=mock_yt_uploader),
            ):
                runner.run_upload_scheduled()

        mock_calendar.get_pending_slots.assert_called_once()
        mock_yt_uploader.upload_episode.assert_called_once()
        mock_calendar.mark_slot_uploaded.assert_called_once()

    def test_skips_future_calendar_slots(self, tmp_path, monkeypatch):
        """run_upload_scheduled does not dispatch future pending calendar slots."""
        from pipeline import runner

        mock_calendar = MagicMock()
        mock_calendar.enabled = True
        mock_calendar.load_all.return_value = {"ep_29": {"slots": {}}}
        mock_calendar.get_pending_slots.return_value = []  # nothing due

        monkeypatch.setattr(runner.Config, "OUTPUT_DIR", tmp_path)

        # ContentCalendar is imported locally inside run_upload_scheduled, patch at source
        with patch(
            "content_calendar.ContentCalendar", MagicMock(return_value=mock_calendar)
        ):
            runner.run_upload_scheduled()

        mock_calendar.mark_slot_uploaded.assert_not_called()
        mock_calendar.mark_slot_failed.assert_not_called()

    def test_dispatch_calendar_slot_maps_episode_to_upload_episode(self):
        """_dispatch_calendar_slot routes episode slots to upload_episode on YouTube."""
        from pipeline.runner import _dispatch_calendar_slot

        mock_uploader = MagicMock()
        slot = {
            "slot_type": "episode",
            "content": {
                "title": "My Episode",
                "video_path": "ep29.mp4",
                "description": "Great ep",
            },
        }
        _dispatch_calendar_slot(mock_uploader, "youtube", slot)

        mock_uploader.upload_episode.assert_called_once_with(
            video_path="ep29.mp4",
            title="My Episode",
            description="Great ep",
        )

    def test_dispatch_calendar_slot_maps_clip_to_upload_short(self):
        """_dispatch_calendar_slot routes clip slots to upload_short on YouTube."""
        from pipeline.runner import _dispatch_calendar_slot

        mock_uploader = MagicMock()
        slot = {
            "slot_type": "clip_1",
            "content": {
                "clip_path": "clip1.mp4",
                "caption": "Funny moment",
            },
        }
        _dispatch_calendar_slot(mock_uploader, "youtube", slot)

        mock_uploader.upload_short.assert_called_once_with(
            video_path="clip1.mp4",
            title="Funny moment",
            description="",
        )
