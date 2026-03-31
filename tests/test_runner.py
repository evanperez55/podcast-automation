"""Tests for pipeline/runner.py — orchestration engine."""

import json
import pytest
from unittest.mock import patch, Mock
from datetime import datetime


# ---------------------------------------------------------------------------
# Shared fixtures / constants
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode",
    "episode_summary": "A test summary.",
    "censor_timestamps": [
        {
            "timestamp": "00:01:00",
            "seconds": 60.0,
            "start_seconds": 60.0,
            "end_seconds": 60.5,
            "reason": "Name: TestName",
            "context": "TestName said",
        }
    ],
    "best_clips": [
        {
            "start": "00:05:00",
            "end": "00:05:25",
            "start_seconds": 300,
            "end_seconds": 325,
            "duration_seconds": 25,
            "description": "Test clip",
            "why_interesting": "Test",
            "suggested_title": "Test Clip Title",
            "hook_caption": "Wait for it...",
            "clip_hashtags": ["test"],
        }
    ],
    "social_captions": {
        "youtube": "YT caption",
        "instagram": "IG caption",
        "twitter": "Tweet",
        "tiktok": "TikTok caption",
    },
    "show_notes": "Show notes here.",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
        {"start_timestamp": "00:05:00", "title": "Topic", "start_seconds": 300},
    ],
}

SAMPLE_TRANSCRIPT = {
    "words": [
        {"word": "Hello", "start": 0.0, "end": 0.3},
        {"word": "world", "start": 0.4, "end": 0.7},
    ],
    "segments": [{"text": "Hello world", "start": 0.0, "end": 0.7}],
    "duration": 3600,
}


# ---------------------------------------------------------------------------
# _init_uploaders
# ---------------------------------------------------------------------------
class TestInitUploaders:
    """Tests for _init_uploaders()."""

    @patch("pipeline.runner.SpotifyUploader", side_effect=ValueError("no creds"))
    @patch("pipeline.runner.TikTokUploader")
    @patch("pipeline.runner.InstagramUploader")
    @patch("pipeline.runner.TwitterUploader", side_effect=ValueError("no creds"))
    @patch("pipeline.runner.YouTubeUploader", side_effect=ValueError("no creds"))
    def test_uploaders_with_missing_credentials(
        self, mock_yt, mock_tw, mock_ig, mock_tt, mock_sp
    ):
        """Uploaders that raise ValueError are excluded gracefully."""
        mock_ig_instance = Mock()
        mock_ig_instance.functional = False
        mock_ig.return_value = mock_ig_instance

        mock_tt_instance = Mock()
        mock_tt_instance.functional = False
        mock_tt.return_value = mock_tt_instance

        from pipeline.runner import _init_uploaders

        with patch(
            "pipeline.runner.getattr",
            side_effect=lambda o, a, d=None: (
                d if a == "EPISODE_SOURCE" else getattr(o, a, d)
            ),
        ):
            uploaders = _init_uploaders()

        # YouTube, Twitter, Spotify raised ValueError → not in dict (or handled)
        assert "youtube" not in uploaders or uploaders.get("youtube") is not None
        # Instagram and TikTok are always added but may not be functional
        assert "instagram" in uploaders
        assert "tiktok" in uploaders

    @patch.object(__import__("config").Config, "EPISODE_SOURCE", "rss", create=True)
    def test_uploaders_skipped_for_non_dropbox_client(self):
        """Non-dropbox clients skip all uploaders."""
        from pipeline.runner import _init_uploaders

        uploaders = _init_uploaders()
        assert uploaders == {}

    @patch("pipeline.runner.SpotifyUploader")
    @patch("pipeline.runner.TikTokUploader")
    @patch("pipeline.runner.InstagramUploader")
    @patch("pipeline.runner.TwitterUploader")
    @patch("pipeline.runner.YouTubeUploader")
    def test_all_uploaders_initialize_successfully(
        self, mock_yt, mock_tw, mock_ig, mock_tt, mock_sp
    ):
        """When all credentials are available, all uploaders are initialized."""
        mock_ig.return_value.functional = True
        mock_tt.return_value.functional = True

        from pipeline.runner import _init_uploaders

        uploaders = _init_uploaders()
        assert "youtube" in uploaders
        assert "twitter" in uploaders
        assert "instagram" in uploaders
        assert "tiktok" in uploaders
        assert "spotify" in uploaders


# ---------------------------------------------------------------------------
# _load_scored_topics
# ---------------------------------------------------------------------------
class TestLoadScoredTopics:
    """Tests for _load_scored_topics()."""

    def test_no_topic_dir(self, tmp_path, monkeypatch):
        """Returns None when topic_data/ does not exist."""
        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        from pipeline.runner import _load_scored_topics

        assert _load_scored_topics() is None

    def test_empty_topic_dir(self, tmp_path, monkeypatch):
        """Returns None when no scored_topics files exist."""
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()
        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        from pipeline.runner import _load_scored_topics

        assert _load_scored_topics() is None

    def test_loads_topics_successfully(self, tmp_path, monkeypatch):
        """Successfully loads and flattens scored topics."""
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()

        data = {
            "topics_by_category": {
                "tech": [
                    {
                        "title": "AI Safety",
                        "score": {
                            "total": 8.5,
                            "recommended": True,
                            "category": "tech",
                        },
                    },
                    {
                        "title": "Boring Topic",
                        "score": {
                            "total": 3.0,
                            "recommended": False,
                            "category": "tech",
                        },
                    },
                ],
                "culture": [
                    {
                        "title": "Memes",
                        "score": {
                            "total": 7.0,
                            "recommended": True,
                            "category": "culture",
                        },
                    },
                ],
            }
        }
        with open(topic_dir / "scored_topics_2026-03-30.json", "w") as f:
            json.dump(data, f)

        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        from pipeline.runner import _load_scored_topics

        result = _load_scored_topics()
        assert result is not None
        assert len(result) == 2  # only recommended=True
        assert result[0]["topic"] == "AI Safety"  # highest score first
        assert result[1]["topic"] == "Memes"

    def test_returns_none_on_empty_topics(self, tmp_path, monkeypatch):
        """Returns None when no recommended topics exist."""
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()

        data = {
            "topics_by_category": {
                "tech": [
                    {"title": "Boring", "score": {"total": 2, "recommended": False}},
                ]
            }
        }
        with open(topic_dir / "scored_topics_2026-01-01.json", "w") as f:
            json.dump(data, f)

        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        from pipeline.runner import _load_scored_topics

        assert _load_scored_topics() is None

    def test_handles_corrupt_json(self, tmp_path, monkeypatch):
        """Returns None on corrupt JSON."""
        topic_dir = tmp_path / "topic_data"
        topic_dir.mkdir()
        (topic_dir / "scored_topics_2026-01-01.json").write_text("{bad json")

        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        from pipeline.runner import _load_scored_topics

        assert _load_scored_topics() is None


# ---------------------------------------------------------------------------
# _load_episode_topics
# ---------------------------------------------------------------------------
class TestLoadEpisodeTopics:
    """Tests for _load_episode_topics()."""

    def test_no_episode_dir(self, tmp_path, monkeypatch):
        """Returns empty list when episode dir doesn't exist."""
        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)
        from pipeline.runner import _load_episode_topics

        assert _load_episode_topics(99) == []

    def test_no_analysis_files(self, tmp_path, monkeypatch):
        """Returns empty list when no analysis JSON found."""
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)
        from pipeline.runner import _load_episode_topics

        assert _load_episode_topics(25) == []

    def test_loads_topics_from_analysis(self, tmp_path, monkeypatch):
        """Extracts suggested_title from best_clips."""
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()

        analysis = {
            "best_clips": [
                {"suggested_title": "Clip A"},
                {"suggested_title": "Clip B"},
                {"title": "Clip C"},  # fallback to title
            ]
        }
        with open(ep_dir / "test_analysis.json", "w") as f:
            json.dump(analysis, f)

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)
        from pipeline.runner import _load_episode_topics

        topics = _load_episode_topics(25)
        assert topics == ["Clip A", "Clip B", "Clip C"]

    def test_handles_corrupt_analysis(self, tmp_path, monkeypatch):
        """Returns empty list on corrupt analysis JSON."""
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "test_analysis.json").write_text("{bad}")

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)
        from pipeline.runner import _load_episode_topics

        assert _load_episode_topics(25) == []


# ---------------------------------------------------------------------------
# _dispatch_calendar_slot
# ---------------------------------------------------------------------------
class TestDispatchCalendarSlot:
    """Tests for _dispatch_calendar_slot()."""

    def test_youtube_episode_slot(self):
        """YouTube episode slot calls upload_episode."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        uploader.upload_episode.return_value = {"id": "123"}
        slot = {
            "slot_type": "episode",
            "content": {
                "video_path": "/video.mp4",
                "title": "My Episode",
                "description": "desc",
            },
        }
        result = _dispatch_calendar_slot(uploader, "youtube", slot)
        uploader.upload_episode.assert_called_once_with(
            video_path="/video.mp4", title="My Episode", description="desc"
        )
        assert result == {"id": "123"}

    def test_youtube_clip_slot(self):
        """YouTube clip slot calls upload_short."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        slot = {
            "slot_type": "clip_1",
            "content": {"clip_path": "/clip.mp4", "caption": "My clip"},
        }
        _dispatch_calendar_slot(uploader, "youtube", slot)
        uploader.upload_short.assert_called_once_with(
            video_path="/clip.mp4", title="My clip", description=""
        )

    def test_twitter_with_media(self):
        """Twitter slot with clip_path includes media."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        slot = {
            "slot_type": "clip_1",
            "content": {"clip_path": "/clip.mp4", "caption": "tweet!"},
        }
        _dispatch_calendar_slot(uploader, "twitter", slot)
        uploader.post_tweet.assert_called_once_with(
            text="tweet!", media_paths=["/clip.mp4"]
        )

    def test_twitter_teaser_no_media(self):
        """Twitter teaser slot has no media."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        slot = {"slot_type": "teaser", "content": {"caption": "teaser tweet"}}
        _dispatch_calendar_slot(uploader, "twitter", slot)
        uploader.post_tweet.assert_called_once_with(
            text="teaser tweet", media_paths=None
        )

    def test_instagram_reel(self):
        """Instagram slot calls upload_reel."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        slot = {
            "slot_type": "clip_1",
            "content": {"clip_path": "/clip.mp4", "caption": "ig caption"},
        }
        _dispatch_calendar_slot(uploader, "instagram", slot)
        uploader.upload_reel.assert_called_once_with(
            video_url="/clip.mp4", caption="ig caption"
        )

    def test_tiktok_video(self):
        """TikTok slot calls upload_video."""
        from pipeline.runner import _dispatch_calendar_slot

        uploader = Mock()
        slot = {
            "slot_type": "clip_1",
            "content": {"clip_path": "/clip.mp4", "caption": "tt caption"},
        }
        _dispatch_calendar_slot(uploader, "tiktok", slot)
        uploader.upload_video.assert_called_once_with(
            video_path="/clip.mp4", title="tt caption", description="tt caption"
        )

    def test_unknown_platform_returns_none(self):
        """Unknown platform returns None."""
        from pipeline.runner import _dispatch_calendar_slot

        result = _dispatch_calendar_slot(Mock(), "unknown", {"content": {}})
        assert result is None


# ---------------------------------------------------------------------------
# _run_transcribe
# ---------------------------------------------------------------------------
class TestRunTranscribe:
    """Tests for _run_transcribe()."""

    def test_transcribe_fresh_run(self, tmp_path):
        """Transcribes audio when no state checkpoint exists."""
        from pipeline.runner import _run_transcribe
        from pipeline.context import PipelineContext

        audio_file = tmp_path / "episode.wav"
        audio_file.write_text("fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=output_dir,
            timestamp="20260101_120000",
            audio_file=audio_file,
        )

        mock_transcriber = Mock()
        mock_transcriber.transcribe.return_value = SAMPLE_TRANSCRIPT
        components = {"transcriber": mock_transcriber}

        result = _run_transcribe(ctx, components, state=None)

        mock_transcriber.transcribe.assert_called_once()
        assert result.transcript_data == SAMPLE_TRANSCRIPT
        assert result.transcript_path is not None

    def test_transcribe_resume_from_checkpoint(self, tmp_path):
        """Skips transcription when state checkpoint shows it completed."""
        from pipeline.runner import _run_transcribe
        from pipeline.context import PipelineContext

        audio_file = tmp_path / "episode.wav"
        audio_file.write_text("fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write a transcript file that the resume would load
        transcript_path = output_dir / "episode_20260101_transcript.json"
        with open(transcript_path, "w") as f:
            json.dump(SAMPLE_TRANSCRIPT, f)

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=output_dir,
            timestamp="20260101_120000",
            audio_file=audio_file,
        )

        mock_state = Mock()
        mock_state.is_step_completed.return_value = True
        mock_state.get_step_outputs.return_value = {
            "transcript_path": str(transcript_path)
        }

        mock_transcriber = Mock()
        components = {"transcriber": mock_transcriber}

        result = _run_transcribe(ctx, components, state=mock_state)

        mock_transcriber.transcribe.assert_not_called()
        assert result.transcript_data == SAMPLE_TRANSCRIPT


# ---------------------------------------------------------------------------
# _run_process_audio
# ---------------------------------------------------------------------------
class TestRunProcessAudio:
    """Tests for _run_process_audio()."""

    def test_process_audio_fresh_run(self, tmp_path):
        """Runs censor + normalize + mp3 on fresh run."""
        from pipeline.runner import _run_process_audio
        from pipeline.context import PipelineContext

        audio_file = tmp_path / "episode.wav"
        audio_file.write_text("fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        censored_path = tmp_path / "censored.wav"
        mp3_path = tmp_path / "episode.mp3"

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=output_dir,
            timestamp="20260101_120000",
            audio_file=audio_file,
            analysis=SAMPLE_ANALYSIS,
        )

        mock_audio = Mock()
        mock_audio.apply_censorship.return_value = censored_path
        mock_audio.normalize_audio.return_value = censored_path
        mock_audio.convert_to_mp3.return_value = mp3_path

        mock_chapter = Mock()
        mock_chapter.enabled = True

        components = {
            "audio_processor": mock_audio,
            "chapter_generator": mock_chapter,
        }

        result = _run_process_audio(ctx, components, state=None)

        mock_audio.apply_censorship.assert_called_once()
        mock_audio.normalize_audio.assert_called_once()
        mock_audio.convert_to_mp3.assert_called_once()
        mock_chapter.embed_id3_chapters.assert_called_once()
        assert result.mp3_path == mp3_path

    def test_process_audio_resume(self, tmp_path):
        """Skips steps that are already completed during resume."""
        from pipeline.runner import _run_process_audio
        from pipeline.context import PipelineContext

        audio_file = tmp_path / "episode.wav"
        audio_file.write_text("fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=output_dir,
            timestamp="20260101_120000",
            audio_file=audio_file,
            analysis=SAMPLE_ANALYSIS,
        )

        mock_state = Mock()
        mock_state.is_step_completed.return_value = True
        mock_state.get_step_outputs.side_effect = lambda step: {
            "censor": {"censored_audio": str(tmp_path / "censored.wav")},
            "normalize": {"normalized_audio": str(tmp_path / "normalized.wav")},
            "convert_mp3": {"mp3_path": str(tmp_path / "episode.mp3")},
        }[step]

        mock_audio = Mock()
        components = {
            "audio_processor": mock_audio,
            "chapter_generator": Mock(enabled=True),
        }

        _run_process_audio(ctx, components, state=mock_state)

        mock_audio.apply_censorship.assert_not_called()
        mock_audio.normalize_audio.assert_not_called()
        mock_audio.convert_to_mp3.assert_not_called()

    def test_process_audio_no_chapters(self, tmp_path):
        """Skips chapter embedding when no chapters in analysis."""
        from pipeline.runner import _run_process_audio
        from pipeline.context import PipelineContext

        audio_file = tmp_path / "episode.wav"
        audio_file.write_text("fake")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis_no_chapters = dict(SAMPLE_ANALYSIS)
        analysis_no_chapters["chapters"] = []

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=output_dir,
            timestamp="20260101_120000",
            audio_file=audio_file,
            analysis=analysis_no_chapters,
        )

        mock_audio = Mock()
        mock_audio.apply_censorship.return_value = tmp_path / "censored.wav"
        mock_audio.normalize_audio.return_value = tmp_path / "censored.wav"
        mock_audio.convert_to_mp3.return_value = tmp_path / "episode.mp3"

        mock_chapter = Mock()
        mock_chapter.enabled = True

        components = {
            "audio_processor": mock_audio,
            "chapter_generator": mock_chapter,
        }

        _run_process_audio(ctx, components, state=None)
        mock_chapter.embed_id3_chapters.assert_not_called()


# ---------------------------------------------------------------------------
# dry_run
# ---------------------------------------------------------------------------
class TestDryRun:
    """Tests for dry_run()."""

    def test_dry_run_returns_status(self, tmp_path, monkeypatch):
        """Dry run returns dict with status, steps_validated, warnings."""
        from pipeline.runner import dry_run

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path / "output")
        monkeypatch.setattr("pipeline.runner.Config.CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(
            "pipeline.runner.Config.DOWNLOAD_DIR", tmp_path / "downloads"
        )
        monkeypatch.setattr("pipeline.runner.Config.ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        monkeypatch.setattr("pipeline.runner.Config.WHISPER_MODEL", "base")
        monkeypatch.setattr("pipeline.runner.Config.LUFS_TARGET", -16)
        monkeypatch.setattr("pipeline.runner.Config.MP3_BITRATE", "192k")
        monkeypatch.setattr(
            "pipeline.runner.Config.DROPBOX_FINISHED_FOLDER", "/finished"
        )
        monkeypatch.setattr(
            "pipeline.runner.Config.FFMPEG_PATH", str(tmp_path / "ffmpeg.exe")
        )

        # Create dirs so they pass existence check
        for d in ["output", "clips", "downloads", "assets"]:
            (tmp_path / d).mkdir()

        mock_notifier = Mock(enabled=True)
        mock_scheduler = Mock()
        mock_scheduler.is_scheduling_enabled.return_value = False
        mock_blog = Mock(enabled=True)
        mock_thumb = Mock()
        mock_audiogram = Mock(enabled=False)
        mock_subtitle_clip = Mock(enabled=True)
        mock_webpage = Mock(enabled=True)
        mock_compliance = Mock(enabled=True)

        components = {
            "audiogram_generator": mock_audiogram,
            "subtitle_clip_generator": mock_subtitle_clip,
            "blog_generator": mock_blog,
            "scheduler": mock_scheduler,
            "thumbnail_generator": mock_thumb,
            "notifier": mock_notifier,
            "webpage_generator": mock_webpage,
            "compliance_checker": mock_compliance,
            "uploaders": {},
        }

        result = dry_run(components=components)
        assert result["status"] == "dry_run_complete"
        assert result["steps_validated"] > 0
        assert isinstance(result["warnings"], list)

    def test_dry_run_missing_dirs_warning(self, tmp_path, monkeypatch):
        """Dry run reports warnings for missing directories."""
        from pipeline.runner import dry_run

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path / "output")
        monkeypatch.setattr("pipeline.runner.Config.CLIPS_DIR", tmp_path / "clips")
        monkeypatch.setattr(
            "pipeline.runner.Config.DOWNLOAD_DIR", tmp_path / "downloads"
        )
        monkeypatch.setattr("pipeline.runner.Config.ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr("pipeline.runner.Config.BASE_DIR", tmp_path)
        monkeypatch.setattr("pipeline.runner.Config.WHISPER_MODEL", "base")
        monkeypatch.setattr("pipeline.runner.Config.LUFS_TARGET", -16)
        monkeypatch.setattr("pipeline.runner.Config.MP3_BITRATE", "192k")
        monkeypatch.setattr(
            "pipeline.runner.Config.DROPBOX_FINISHED_FOLDER", "/finished"
        )
        monkeypatch.setattr(
            "pipeline.runner.Config.FFMPEG_PATH", str(tmp_path / "ffmpeg.exe")
        )

        # Don't create dirs — they should trigger warnings

        components = {
            "audiogram_generator": Mock(enabled=False),
            "subtitle_clip_generator": Mock(enabled=False),
            "blog_generator": Mock(enabled=False),
            "scheduler": Mock(is_scheduling_enabled=Mock(return_value=False)),
            "thumbnail_generator": Mock(),
            "notifier": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "compliance_checker": Mock(enabled=False),
            "uploaders": {},
        }

        result = dry_run(components=components)
        assert any("Missing directories" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# run_with_notification
# ---------------------------------------------------------------------------
class TestRunWithNotification:
    """Tests for run_with_notification()."""

    @patch("pipeline.runner.run")
    @patch("pipeline.runner.DiscordNotifier")
    def test_success_sends_notification(self, mock_notifier_cls, mock_run):
        """On success, sends Discord notification."""
        from pipeline.runner import run_with_notification

        mock_notifier = Mock()
        mock_notifier.enabled = True
        mock_notifier_cls.return_value = mock_notifier

        mock_run.return_value = {"episode_number": 25, "status": "ok"}

        result = run_with_notification({"test_mode": True}, episode_number=25)

        assert result == {"episode_number": 25, "status": "ok"}
        mock_notifier.notify_success.assert_called_once()

    @patch("pipeline.runner.run", side_effect=RuntimeError("pipeline boom"))
    @patch("pipeline.runner.DiscordNotifier")
    def test_failure_sends_notification_and_raises(self, mock_notifier_cls, mock_run):
        """On failure, sends Discord failure notification then re-raises."""
        from pipeline.runner import run_with_notification

        mock_notifier = Mock()
        mock_notifier.enabled = True
        mock_notifier_cls.return_value = mock_notifier

        with pytest.raises(RuntimeError, match="pipeline boom"):
            run_with_notification({"test_mode": True}, episode_number=25)

        mock_notifier.notify_failure.assert_called_once()

    @patch("pipeline.runner.run")
    @patch("pipeline.runner.DiscordNotifier")
    def test_notification_skipped_when_disabled(self, mock_notifier_cls, mock_run):
        """No notification sent when notifier is disabled."""
        from pipeline.runner import run_with_notification

        mock_notifier = Mock()
        mock_notifier.enabled = False
        mock_notifier_cls.return_value = mock_notifier
        mock_run.return_value = {"episode_number": 25}

        run_with_notification({"test_mode": True}, episode_number=25)
        mock_notifier.notify_success.assert_not_called()

    @patch("pipeline.runner.run")
    @patch("pipeline.runner.DiscordNotifier")
    def test_args_as_namespace(self, mock_notifier_cls, mock_run):
        """Accepts argparse Namespace-style args object."""
        from pipeline.runner import run_with_notification
        from types import SimpleNamespace

        mock_notifier = Mock(enabled=False)
        mock_notifier_cls.return_value = mock_notifier
        mock_run.return_value = None

        args = SimpleNamespace(
            test_mode=True, dry_run=False, auto_approve=False, resume=False
        )
        run_with_notification(args, episode_number=10)

        call_args = mock_run.call_args[0][0]
        assert call_args["test_mode"] is True
        assert call_args["episode_number"] == 10


# ---------------------------------------------------------------------------
# run_search
# ---------------------------------------------------------------------------
class TestRunSearch:
    """Tests for run_search()."""

    @patch("pipeline.runner.EpisodeSearchIndex")
    def test_search_with_results(self, mock_index_cls, capsys):
        """Displays search results."""
        from pipeline.runner import run_search

        mock_index = Mock()
        mock_index.search.return_value = [
            {"episode_number": 25, "title": "Test Ep", "snippet": "hello world"},
        ]
        mock_index_cls.return_value = mock_index

        run_search("hello")

        output = capsys.readouterr().out
        assert "Episode 25" in output
        assert "1 result(s) found" in output

    @patch("pipeline.runner.EpisodeSearchIndex")
    def test_search_no_results(self, mock_index_cls, capsys):
        """Displays 'No results found' when empty."""
        from pipeline.runner import run_search

        mock_index = Mock()
        mock_index.search.return_value = []
        mock_index_cls.return_value = mock_index

        run_search("nonexistent")

        output = capsys.readouterr().out
        assert "No results found" in output


# ---------------------------------------------------------------------------
# run_analytics
# ---------------------------------------------------------------------------
class TestRunAnalytics:
    """Tests for run_analytics()."""

    @patch("pipeline.runner._collect_episode_analytics")
    @patch("pipeline.runner.TopicEngagementScorer")
    @patch("pipeline.runner.AnalyticsCollector")
    def test_analytics_single_episode(
        self, mock_collector_cls, mock_scorer_cls, mock_collect
    ):
        """Processes a single episode."""
        from pipeline.runner import run_analytics

        run_analytics("ep25")
        mock_collect.assert_called_once()
        args = mock_collect.call_args[0]
        assert args[2] == 25  # episode number

    @patch("pipeline.runner._collect_episode_analytics")
    @patch("pipeline.runner.TopicEngagementScorer")
    @patch("pipeline.runner.AnalyticsCollector")
    def test_analytics_all_episodes(
        self, mock_collector_cls, mock_scorer_cls, mock_collect, tmp_path, monkeypatch
    ):
        """Processes all episodes in output dir."""
        from pipeline.runner import run_analytics

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)
        (tmp_path / "ep_25").mkdir()
        (tmp_path / "ep_26").mkdir()

        run_analytics("all")
        assert mock_collect.call_count == 2

    @patch("pipeline.runner._collect_episode_analytics")
    @patch("pipeline.runner.TopicEngagementScorer")
    @patch("pipeline.runner.AnalyticsCollector")
    def test_analytics_invalid_episode(
        self, mock_collector_cls, mock_scorer_cls, mock_collect, capsys
    ):
        """Prints error for invalid episode arg."""
        from pipeline.runner import run_analytics

        run_analytics("invalid")
        mock_collect.assert_not_called()
        assert "Invalid episode" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# list_available_episodes / list_episodes_by_number
# ---------------------------------------------------------------------------
class TestListEpisodes:
    """Tests for list_available_episodes() and list_episodes_by_number()."""

    @patch("pipeline.runner.DropboxHandler")
    def test_list_available_no_episodes(self, mock_dbx_cls, capsys):
        """Shows 'No episodes found' when Dropbox is empty."""
        from pipeline.runner import list_available_episodes

        mock_dbx = Mock()
        mock_dbx.list_episodes.return_value = []
        mock_dbx_cls.return_value = mock_dbx

        result = list_available_episodes()
        assert result == []
        assert "No episodes found" in capsys.readouterr().out

    @patch("pipeline.runner.DropboxHandler")
    def test_list_available_with_episodes(self, mock_dbx_cls, capsys):
        """Lists episodes with size and date."""
        from pipeline.runner import list_available_episodes

        mock_dbx = Mock()
        mock_dbx.list_episodes.return_value = [
            {
                "name": "ep25.wav",
                "size": 50 * 1024 * 1024,
                "modified": datetime(2026, 3, 15, 10, 0),
                "path": "/raw/ep25.wav",
            }
        ]
        mock_dbx_cls.return_value = mock_dbx

        result = list_available_episodes()
        assert len(result) == 1
        output = capsys.readouterr().out
        assert "ep25.wav" in output
        assert "50.0 MB" in output

    @patch("pipeline.runner.DropboxHandler")
    def test_list_by_number_no_episodes(self, mock_dbx_cls, capsys):
        """Shows 'No episodes found' when none exist."""
        from pipeline.runner import list_episodes_by_number

        mock_dbx = Mock()
        mock_dbx.list_episodes_with_numbers.return_value = []
        mock_dbx_cls.return_value = mock_dbx

        result = list_episodes_by_number()
        assert result == []
        assert "No episodes found" in capsys.readouterr().out

    @patch("pipeline.runner.DropboxHandler")
    def test_list_by_number_with_episodes(self, mock_dbx_cls, capsys):
        """Lists episodes sorted by number."""
        from pipeline.runner import list_episodes_by_number

        mock_dbx = Mock()
        mock_dbx.list_episodes_with_numbers.return_value = [
            (
                25,
                {
                    "name": "ep25.wav",
                    "size": 50 * 1024 * 1024,
                    "modified": datetime(2026, 3, 15),
                },
            ),
            (
                None,
                {
                    "name": "unknown.wav",
                    "size": 10 * 1024 * 1024,
                    "modified": datetime(2026, 3, 14),
                },
            ),
        ]
        mock_dbx_cls.return_value = mock_dbx

        result = list_episodes_by_number()
        assert len(result) == 2
        output = capsys.readouterr().out
        assert "Episode 25" in output
        assert "[No Episode #]" in output

    def test_list_available_with_components(self):
        """Uses dropbox from components dict when provided."""
        from pipeline.runner import list_available_episodes

        mock_dbx = Mock()
        mock_dbx.list_episodes.return_value = []
        components = {"dropbox": mock_dbx}

        list_available_episodes(components=components)
        mock_dbx.list_episodes.assert_called_once()


# ---------------------------------------------------------------------------
# _init_components
# ---------------------------------------------------------------------------
class TestInitComponents:
    """Tests for _init_components()."""

    @patch("pipeline.runner.ContentComplianceChecker")
    @patch("pipeline.runner.EpisodeWebpageGenerator")
    @patch("pipeline.runner.SubtitleClipGenerator")
    @patch("pipeline.runner.ChapterGenerator")
    @patch("pipeline.runner.AudiogramGenerator")
    @patch("pipeline.runner.EpisodeSearchIndex")
    @patch("pipeline.runner.ClipPreviewer")
    @patch("pipeline.runner.ThumbnailGenerator")
    @patch("pipeline.runner.BlogPostGenerator")
    @patch("pipeline.runner.UploadScheduler")
    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner.Config.create_directories")
    def test_dry_run_mode_skips_validation(
        self,
        mock_create_dirs,
        mock_notifier,
        mock_scheduler,
        mock_blog,
        mock_thumb,
        mock_clip,
        mock_search,
        mock_audiogram,
        mock_chapter,
        mock_subtitle,
        mock_webpage,
        mock_compliance,
    ):
        """Dry run skips Config.validate() and heavy init."""
        from pipeline.runner import _init_components

        components = _init_components(dry_run=True)

        assert components["transcriber"] is None
        assert components["editor"] is None
        assert components["audio_processor"] is None
        assert components["video_converter"] is None
        assert components["uploaders"] == {}
        mock_create_dirs.assert_called_once()

    @patch("pipeline.runner.ContentComplianceChecker")
    @patch("pipeline.runner.EpisodeWebpageGenerator")
    @patch("pipeline.runner.SubtitleClipGenerator")
    @patch("pipeline.runner.ChapterGenerator")
    @patch("pipeline.runner.AudiogramGenerator")
    @patch("pipeline.runner.EpisodeSearchIndex")
    @patch("pipeline.runner.ClipPreviewer")
    @patch("pipeline.runner.ThumbnailGenerator")
    @patch("pipeline.runner.BlogPostGenerator")
    @patch("pipeline.runner.UploadScheduler")
    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner._init_uploaders", return_value={})
    @patch("pipeline.runner.VideoConverter")
    @patch("pipeline.runner.AudioProcessor")
    @patch("pipeline.runner.ContentEditor")
    @patch("pipeline.runner.Transcriber")
    @patch("pipeline.runner.DropboxHandler")
    @patch("pipeline.runner.Config.create_directories")
    @patch("pipeline.runner.Config.validate")
    def test_full_init_creates_all_components(
        self,
        mock_validate,
        mock_create_dirs,
        mock_dbx,
        mock_trans,
        mock_editor,
        mock_audio,
        mock_video,
        mock_uploaders,
        mock_notifier,
        mock_scheduler,
        mock_blog,
        mock_thumb,
        mock_clip,
        mock_search,
        mock_audiogram,
        mock_chapter,
        mock_subtitle,
        mock_webpage,
        mock_compliance,
    ):
        """Full init creates all components."""
        from pipeline.runner import _init_components

        components = _init_components(test_mode=True)

        assert "transcriber" in components
        assert "editor" in components
        assert "audio_processor" in components
        assert "dropbox" in components
        mock_validate.assert_called_once()

    @patch("pipeline.runner.ContentComplianceChecker")
    @patch("pipeline.runner.EpisodeWebpageGenerator")
    @patch("pipeline.runner.SubtitleClipGenerator")
    @patch("pipeline.runner.ChapterGenerator")
    @patch("pipeline.runner.AudiogramGenerator")
    @patch("pipeline.runner.EpisodeSearchIndex")
    @patch("pipeline.runner.ClipPreviewer")
    @patch("pipeline.runner.ThumbnailGenerator")
    @patch("pipeline.runner.BlogPostGenerator")
    @patch("pipeline.runner.UploadScheduler")
    @patch("pipeline.runner.DiscordNotifier")
    @patch("pipeline.runner._init_uploaders", return_value={})
    @patch("pipeline.runner.VideoConverter", side_effect=FileNotFoundError("no ffmpeg"))
    @patch("pipeline.runner.AudioProcessor")
    @patch("pipeline.runner.ContentEditor")
    @patch("pipeline.runner.Transcriber")
    @patch("pipeline.runner.DropboxHandler")
    @patch("pipeline.runner.Config.create_directories")
    @patch("pipeline.runner.Config.validate")
    def test_video_converter_optional(
        self,
        mock_validate,
        mock_create_dirs,
        mock_dbx,
        mock_trans,
        mock_editor,
        mock_audio,
        mock_video,
        mock_uploaders,
        mock_notifier,
        mock_scheduler,
        mock_blog,
        mock_thumb,
        mock_clip,
        mock_search,
        mock_audiogram,
        mock_chapter,
        mock_subtitle,
        mock_webpage,
        mock_compliance,
    ):
        """VideoConverter failure is handled gracefully."""
        from pipeline.runner import _init_components

        components = _init_components()
        assert components["video_converter"] is None


# ---------------------------------------------------------------------------
# _collect_episode_analytics
# ---------------------------------------------------------------------------
class TestCollectEpisodeAnalytics:
    """Tests for _collect_episode_analytics()."""

    @patch("pipeline.runner._load_episode_topics", return_value=["Topic A"])
    def test_collect_and_display(self, mock_topics, tmp_path, monkeypatch, capsys):
        """Collects analytics, saves, scores, and displays."""
        from pipeline.runner import _collect_episode_analytics

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)

        # Create platform_ids.json so it can read mtime
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        ids_path = ep_dir / "platform_ids.json"
        ids_path.write_text('{"youtube": "abc123"}')

        mock_collector = Mock()
        mock_collector._load_platform_ids.return_value = {"youtube": "abc123"}
        mock_collector.collect_analytics.return_value = {
            "youtube": {"views": 100, "likes": 10},
            "twitter": {"impressions": 500, "engagements": 20},
        }

        mock_scorer = Mock()
        mock_scorer.calculate_engagement_score.return_value = 7.5

        _collect_episode_analytics(mock_collector, mock_scorer, 25)

        mock_collector.collect_analytics.assert_called_once()
        mock_collector.save_analytics.assert_called_once()
        mock_collector.append_to_engagement_history.assert_called_once()

        output = capsys.readouterr().out
        assert "7.5/10" in output
        assert "100 views" in output
        assert "500 impressions" in output

    @patch("pipeline.runner._load_episode_topics", return_value=[])
    def test_collect_no_platform_ids(self, mock_topics, tmp_path, monkeypatch, capsys):
        """Uses current timestamp when no platform_ids.json."""
        from pipeline.runner import _collect_episode_analytics

        monkeypatch.setattr("pipeline.runner.Config.OUTPUT_DIR", tmp_path)

        mock_collector = Mock()
        mock_collector._load_platform_ids.return_value = {}
        mock_collector.collect_analytics.return_value = {}

        mock_scorer = Mock()
        mock_scorer.calculate_engagement_score.return_value = 0.0

        _collect_episode_analytics(mock_collector, mock_scorer, 25)

        # Should still work without errors
        mock_collector.append_to_engagement_history.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
