"""Tests for pipeline/steps/distribute.py — distribution step."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, Mock


# ---------------------------------------------------------------------------
# Shared fixtures / constants
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = {
    "episode_title": "Test Episode",
    "episode_summary": "A test summary.",
    "censor_timestamps": [],
    "best_clips": [
        {
            "start": "00:05:00",
            "end": "00:05:25",
            "start_seconds": 300,
            "end_seconds": 325,
            "duration_seconds": 25,
            "description": "Test clip",
            "why_interesting": "Test",
            "suggested_title": "Test Clip",
            "hook_caption": "Wait for it...",
            "clip_hashtags": ["test", "comedy"],
        }
    ],
    "social_captions": {
        "youtube": "YT caption",
        "instagram": "IG caption",
        "twitter": "Tweet text",
        "tiktok": "TikTok caption",
    },
    "show_notes": "Show notes here.",
    "chapters": [
        {"start_timestamp": "00:00:00", "title": "Intro", "start_seconds": 0},
    ],
}

SAMPLE_TRANSCRIPT = {
    "segments": [{"text": "Hello world", "start": 0.0, "end": 0.7}],
    "duration": 3600,
}


def _make_ctx(tmp_path, **overrides):
    """Build a PipelineContext with sensible defaults for distribution tests."""
    from pipeline.context import PipelineContext

    ep_dir = tmp_path / "output" / "ep_25"
    ep_dir.mkdir(parents=True, exist_ok=True)

    defaults = dict(
        episode_folder="ep_25",
        episode_number=25,
        episode_output_dir=ep_dir,
        timestamp="20260101_120000",
        audio_file=tmp_path / "episode.wav",
        censored_audio=tmp_path / "censored.wav",
        mp3_path=tmp_path / "episode.mp3",
        transcript_path=tmp_path / "transcript.json",
        transcript_data=SAMPLE_TRANSCRIPT,
        analysis=SAMPLE_ANALYSIS,
        clip_paths=[],
        video_clip_paths=[],
        full_episode_video_path=None,
        test_mode=False,
        dry_run=False,
        auto_approve=True,
        resume=False,
        force=False,
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


# ---------------------------------------------------------------------------
# _upload_youtube
# ---------------------------------------------------------------------------
class TestUploadYoutube:
    """Tests for _upload_youtube()."""

    def test_returns_none_when_no_youtube_uploader(self):
        """Returns None when YouTube uploader not in components."""
        from pipeline.steps.distribute import _upload_youtube

        result = _upload_youtube(25, [], SAMPLE_ANALYSIS, None, {"uploaders": {}})
        assert result is None

    @patch("uploaders.create_episode_metadata")
    def test_test_mode_skips_upload(self, mock_metadata):
        """Test mode logs but doesn't upload."""
        from pipeline.steps.distribute import _upload_youtube

        mock_metadata.return_value = {
            "title": "Test",
            "description": "desc",
            "tags": [],
        }
        mock_yt = Mock()
        components = {"uploaders": {"youtube": mock_yt}}

        result = _upload_youtube(
            25,
            ["/clip1.mp4"],
            SAMPLE_ANALYSIS,
            "/full_episode.mp4",
            components,
            test_mode=True,
        )

        assert result["full_episode"]["status"] == "test_mode"
        assert result["clips"][0]["status"] == "test_mode"
        mock_yt.upload_episode.assert_not_called()

    @patch("uploaders.create_episode_metadata")
    def test_uploads_full_episode(self, mock_metadata):
        """Uploads full episode to YouTube."""
        from pipeline.steps.distribute import _upload_youtube

        mock_metadata.return_value = {
            "title": "Test",
            "description": "desc",
            "tags": ["podcast"],
        }
        mock_yt = Mock()
        mock_yt.upload_episode.return_value = {
            "video_id": "abc123",
            "video_url": "https://youtube.com/abc123",
        }
        components = {"uploaders": {"youtube": mock_yt}}

        result = _upload_youtube(
            25, [], SAMPLE_ANALYSIS, "/full_episode.mp4", components, test_mode=False
        )

        assert result["full_episode"]["video_id"] == "abc123"
        mock_yt.upload_episode.assert_called_once()

    @patch("uploaders.create_episode_metadata")
    def test_handles_upload_error(self, mock_metadata):
        """Catches upload exceptions gracefully."""
        from pipeline.steps.distribute import _upload_youtube

        mock_metadata.return_value = {
            "title": "Test",
            "description": "desc",
            "tags": [],
        }
        mock_yt = Mock()
        mock_yt.upload_episode.side_effect = Exception("API error")
        components = {"uploaders": {"youtube": mock_yt}}

        result = _upload_youtube(
            25, [], SAMPLE_ANALYSIS, "/full_episode.mp4", components, test_mode=False
        )

        assert result["full_episode"]["status"] == "error"
        assert "API error" in result["full_episode"]["error"]


# ---------------------------------------------------------------------------
# _upload_twitter
# ---------------------------------------------------------------------------
class TestUploadTwitter:
    """Tests for _upload_twitter()."""

    def test_returns_none_when_no_twitter(self):
        """Returns None when Twitter uploader not available."""
        from pipeline.steps.distribute import _upload_twitter

        result = _upload_twitter(25, SAMPLE_ANALYSIS, None, {"uploaders": {}})
        assert result is None

    def test_test_mode_skips_posting(self):
        """Test mode returns test_mode status."""
        from pipeline.steps.distribute import _upload_twitter

        mock_tw = Mock()
        components = {"uploaders": {"twitter": mock_tw}}

        result = _upload_twitter(25, SAMPLE_ANALYSIS, None, components, test_mode=True)

        assert result["status"] == "test_mode"
        mock_tw.post_episode_announcement.assert_not_called()

    def test_posts_with_youtube_urls(self):
        """Posts announcement with YouTube URLs when available."""
        from pipeline.steps.distribute import _upload_twitter

        mock_tw = Mock()
        mock_tw.post_episode_announcement.return_value = [{"tweet_id": "123"}]
        components = {"uploaders": {"twitter": mock_tw}}

        youtube_results = {
            "full_episode": {"video_url": "https://youtube.com/full"},
            "clips": [
                {"video_url": "https://youtube.com/short1", "title": "Clip 1 #Shorts"}
            ],
        }

        _upload_twitter(
            25, SAMPLE_ANALYSIS, youtube_results, components, test_mode=False
        )

        mock_tw.post_episode_announcement.assert_called_once()
        call_kwargs = mock_tw.post_episode_announcement.call_args.kwargs
        assert call_kwargs["youtube_url"] == "https://youtube.com/full"
        assert len(call_kwargs["clip_youtube_urls"]) == 1
        # Verify #Shorts suffix stripped
        assert "#Shorts" not in call_kwargs["clip_youtube_urls"][0]["title"]

    def test_handles_post_error(self):
        """Catches Twitter posting errors."""
        from pipeline.steps.distribute import _upload_twitter

        mock_tw = Mock()
        mock_tw.post_episode_announcement.side_effect = Exception("rate limited")
        components = {"uploaders": {"twitter": mock_tw}}

        result = _upload_twitter(25, SAMPLE_ANALYSIS, None, components, test_mode=False)

        assert "error" in result


# ---------------------------------------------------------------------------
# _upload_instagram
# ---------------------------------------------------------------------------
class TestUploadInstagram:
    """Tests for _upload_instagram()."""

    def test_returns_none_when_no_instagram(self):
        """Returns None when Instagram not in uploaders."""
        from pipeline.steps.distribute import _upload_instagram

        result = _upload_instagram(["/clip.mp4"], components={"uploaders": {}})
        assert result is None

    def test_videos_ready(self):
        """Returns videos_ready status when clips available."""
        from pipeline.steps.distribute import _upload_instagram

        components = {"uploaders": {"instagram": Mock()}}
        result = _upload_instagram(
            ["/clip1.mp4", "/clip2.mp4"],
            analysis=SAMPLE_ANALYSIS,
            components=components,
        )
        assert result["status"] == "videos_ready"
        assert result["clips"] == 2

    def test_no_videos(self):
        """Returns no_videos when no clips."""
        from pipeline.steps.distribute import _upload_instagram

        components = {"uploaders": {"instagram": Mock()}}
        result = _upload_instagram([], components=components)
        assert result["status"] == "no_videos"


# ---------------------------------------------------------------------------
# _upload_to_social_media
# ---------------------------------------------------------------------------
class TestUploadToSocialMedia:
    """Tests for _upload_to_social_media()."""

    @patch("pipeline.steps.distribute._upload_instagram", return_value=None)
    @patch("pipeline.steps.distribute._upload_twitter", return_value=None)
    @patch("pipeline.steps.distribute._upload_youtube", return_value=None)
    def test_scheduling_enabled(self, mock_yt, mock_tw, mock_ig, tmp_path):
        """Creates upload schedule when scheduling enabled."""
        from pipeline.steps.distribute import _upload_to_social_media

        mock_scheduler = Mock()
        mock_scheduler.is_scheduling_enabled.return_value = True
        mock_scheduler.create_schedule.return_value = {
            "platforms": {"youtube": {}, "twitter": {}}
        }
        mock_scheduler.save_schedule.return_value = tmp_path / "schedule.json"
        mock_scheduler.get_optimal_publish_at.return_value = None

        components = {"uploaders": {}, "scheduler": mock_scheduler}

        result = _upload_to_social_media(
            25,
            tmp_path / "ep.mp3",
            [],
            SAMPLE_ANALYSIS,
            components,
            episode_output_dir=tmp_path,
        )

        assert "schedule" in result
        mock_scheduler.create_schedule.assert_called_once()

    @patch("pipeline.steps.distribute._upload_instagram", return_value=None)
    @patch("pipeline.steps.distribute._upload_twitter", return_value=None)
    @patch("pipeline.steps.distribute._upload_youtube")
    def test_saves_platform_ids(self, mock_yt, mock_tw, mock_ig, tmp_path):
        """Saves platform_ids.json when video_id present."""
        from pipeline.steps.distribute import _upload_to_social_media

        mock_yt.return_value = {
            "full_episode": {"video_id": "abc123"},
            "clips": [],
        }

        mock_scheduler = Mock()
        mock_scheduler.is_scheduling_enabled.return_value = False
        mock_scheduler.get_optimal_publish_at.return_value = None

        components = {
            "uploaders": {"youtube": Mock()},
            "scheduler": mock_scheduler,
        }

        _upload_to_social_media(
            25,
            tmp_path / "ep.mp3",
            [],
            SAMPLE_ANALYSIS,
            components,
            episode_output_dir=tmp_path,
        )

        ids_path = tmp_path / "platform_ids.json"
        assert ids_path.exists()
        with open(ids_path) as f:
            ids = json.load(f)
        assert ids["youtube"] == "abc123"

    @patch("pipeline.steps.distribute._upload_instagram", return_value=None)
    @patch("pipeline.steps.distribute._upload_twitter", return_value=None)
    @patch("pipeline.steps.distribute._upload_youtube", return_value=None)
    def test_tiktok_videos_ready(self, mock_yt, mock_tw, mock_ig):
        """TikTok section reports videos_ready when clips available."""
        from pipeline.steps.distribute import _upload_to_social_media

        mock_scheduler = Mock()
        mock_scheduler.is_scheduling_enabled.return_value = False
        mock_scheduler.get_optimal_publish_at.return_value = None

        components = {
            "uploaders": {"tiktok": Mock()},
            "scheduler": mock_scheduler,
        }

        result = _upload_to_social_media(
            25,
            Path("/ep.mp3"),
            ["/clip1.mp4"],
            SAMPLE_ANALYSIS,
            components,
        )

        assert result["tiktok"]["status"] == "videos_ready"

    @patch("pipeline.steps.distribute._upload_instagram", return_value=None)
    @patch("pipeline.steps.distribute._upload_twitter", return_value=None)
    @patch("pipeline.steps.distribute._upload_youtube", return_value=None)
    def test_spotify_rss_ready(self, mock_yt, mock_tw, mock_ig):
        """Spotify reports rss_ready status."""
        from pipeline.steps.distribute import _upload_to_social_media

        mock_scheduler = Mock()
        mock_scheduler.is_scheduling_enabled.return_value = False
        mock_scheduler.get_optimal_publish_at.return_value = None

        components = {
            "uploaders": {"spotify": Mock()},
            "scheduler": mock_scheduler,
        }

        result = _upload_to_social_media(
            25,
            Path("/ep.mp3"),
            [],
            SAMPLE_ANALYSIS,
            components,
        )

        assert result["spotify"]["status"] == "rss_ready"


# ---------------------------------------------------------------------------
# run_distribute
# ---------------------------------------------------------------------------
class TestRunDistribute:
    """Tests for run_distribute()."""

    def test_compliance_gate_blocks_uploads(self, tmp_path):
        """Critical compliance violation blocks all distribution."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(
            tmp_path,
            compliance_result={"critical": True, "report_path": "/report.md"},
            force=False,
        )
        components = {"uploaders": {}}

        result = run_distribute(ctx, components)
        # Should return early without modifying ctx significantly
        assert result.finished_path is None

    def test_compliance_gate_bypassed_with_force(self, tmp_path):
        """Force flag bypasses compliance gate."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(
            tmp_path,
            compliance_result={"critical": True},
            force=True,
            test_mode=True,
        )
        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        result = run_distribute(ctx, components)
        # Didn't return early — went through test_mode path
        assert result is not None

    def test_test_mode_skips_dropbox(self, tmp_path):
        """Test mode skips Dropbox uploads."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)
        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        result = run_distribute(ctx, components)
        assert result.finished_path is None

    def test_dropbox_upload_success(self, tmp_path):
        """Successfully uploads to Dropbox."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=False)

        mock_dbx = Mock()
        mock_dbx.upload_finished_episode.return_value = "/finished/ep25.mp3"
        mock_dbx.upload_clips.return_value = []

        components = {
            "dropbox": mock_dbx,
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        result = run_distribute(ctx, components)
        assert result.finished_path == "/finished/ep25.mp3"
        mock_dbx.upload_finished_episode.assert_called_once()

    def test_blog_generation(self, tmp_path):
        """Generates blog post when enabled."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)

        mock_blog = Mock(enabled=True)
        mock_blog.generate_blog_post.return_value = "# Blog post"
        mock_blog.save_blog_post.return_value = tmp_path / "blog.md"

        components = {
            "uploaders": {},
            "blog_generator": mock_blog,
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        run_distribute(ctx, components)
        mock_blog.generate_blog_post.assert_called_once()
        mock_blog.save_blog_post.assert_called_once()

    def test_blog_resume_from_checkpoint(self, tmp_path):
        """Skips blog generation on resume when already completed."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)

        mock_state = Mock()
        mock_state.is_step_completed.side_effect = lambda step: step == "blog_post"
        mock_state.get_step_outputs.return_value = {
            "blog_post_path": str(tmp_path / "blog.md")
        }

        mock_blog = Mock(enabled=True)

        components = {
            "uploaders": {},
            "blog_generator": mock_blog,
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        run_distribute(ctx, components, state=mock_state)
        mock_blog.generate_blog_post.assert_not_called()

    def test_search_indexing(self, tmp_path):
        """Indexes episode for full-text search."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)

        mock_index = Mock()
        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": mock_index,
        }

        run_distribute(ctx, components)
        mock_index.index_episode.assert_called_once()

    def test_webpage_deployment(self, tmp_path):
        """Deploys episode webpage when enabled."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)

        mock_webpage = Mock(enabled=True)
        mock_webpage.generate_and_deploy.return_value = "https://example.com/ep25"

        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": mock_webpage,
            "search_index": None,
        }

        run_distribute(ctx, components)
        mock_webpage.generate_and_deploy.assert_called_once()

    def test_no_dropbox_configured(self, tmp_path):
        """Handles missing Dropbox gracefully."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=False)

        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        result = run_distribute(ctx, components)
        assert result.finished_path is None

    @patch("content_calendar.ContentCalendar")
    def test_content_calendar(self, mock_cal_cls, tmp_path):
        """Content calendar is generated when enabled."""
        from pipeline.steps.distribute import run_distribute

        ctx = _make_ctx(tmp_path, test_mode=True)

        mock_cal = Mock(enabled=True)
        mock_cal.plan_episode.return_value = {"slots": {"day1": {}, "day2": {}}}
        mock_cal_cls.return_value = mock_cal

        components = {
            "uploaders": {},
            "blog_generator": Mock(enabled=False),
            "webpage_generator": Mock(enabled=False),
            "search_index": None,
        }

        run_distribute(ctx, components)
        mock_cal.plan_episode.assert_called_once()


# ---------------------------------------------------------------------------
# run_distribute_only
# ---------------------------------------------------------------------------
class TestRunDistributeOnly:
    """Tests for run_distribute_only()."""

    @patch("pipeline.steps.distribute.run_distribute")
    @patch("episode_webpage_generator.EpisodeWebpageGenerator")
    @patch("chapter_generator.ChapterGenerator")
    @patch("search_index.EpisodeSearchIndex")
    @patch("blog_generator.BlogPostGenerator")
    @patch("scheduler.UploadScheduler")
    @patch("uploaders.TikTokUploader", side_effect=ValueError("no"))
    @patch("uploaders.InstagramUploader", side_effect=ValueError("no"))
    @patch("uploaders.SpotifyUploader", side_effect=ValueError("no"))
    @patch("uploaders.TwitterUploader", side_effect=ValueError("no"))
    @patch("uploaders.YouTubeUploader", side_effect=ValueError("no"))
    @patch("dropbox_handler.DropboxHandler")
    def test_builds_context_from_existing_files(
        self,
        mock_dbx,
        mock_yt,
        mock_tw,
        mock_sp,
        mock_ig,
        mock_tt,
        mock_scheduler,
        mock_blog,
        mock_search,
        mock_chapter,
        mock_webpage,
        mock_run_dist,
        tmp_path,
        monkeypatch,
    ):
        """Builds PipelineContext from on-disk files."""
        monkeypatch.setattr("pipeline.steps.distribute.Config.OUTPUT_DIR", tmp_path)

        # Create expected files
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "test_censored.wav").write_text("fake")
        with open(ep_dir / "test_analysis.json", "w") as f:
            json.dump(SAMPLE_ANALYSIS, f)
        with open(ep_dir / "test_transcript.json", "w") as f:
            json.dump(SAMPLE_TRANSCRIPT, f)
        (ep_dir / "episode.mp3").write_text("fake")

        from pipeline.steps.distribute import run_distribute_only

        run_distribute_only(25)

        mock_run_dist.assert_called_once()
        ctx = mock_run_dist.call_args[0][0]
        assert ctx.episode_number == 25
        assert ctx.analysis == SAMPLE_ANALYSIS

    def test_raises_on_missing_directory(self, tmp_path, monkeypatch):
        """Raises FileNotFoundError when episode dir missing."""
        monkeypatch.setattr("pipeline.steps.distribute.Config.OUTPUT_DIR", tmp_path)

        from pipeline.steps.distribute import run_distribute_only

        with pytest.raises(FileNotFoundError, match="Episode output directory"):
            run_distribute_only(99)

    def test_raises_on_missing_censored_wav(self, tmp_path, monkeypatch):
        """Raises FileNotFoundError when no censored WAV found."""
        monkeypatch.setattr("pipeline.steps.distribute.Config.OUTPUT_DIR", tmp_path)
        (tmp_path / "ep_25").mkdir()

        from pipeline.steps.distribute import run_distribute_only

        with pytest.raises(FileNotFoundError, match="No censored WAV"):
            run_distribute_only(25)

    def test_raises_on_missing_analysis(self, tmp_path, monkeypatch):
        """Raises FileNotFoundError when no analysis JSON found."""
        monkeypatch.setattr("pipeline.steps.distribute.Config.OUTPUT_DIR", tmp_path)
        ep_dir = tmp_path / "ep_25"
        ep_dir.mkdir()
        (ep_dir / "test_censored.wav").write_text("fake")

        from pipeline.steps.distribute import run_distribute_only

        with pytest.raises(FileNotFoundError, match="No analysis JSON"):
            run_distribute_only(25)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
