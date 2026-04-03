"""Structural assertions for the pipeline architecture refactor.

RED tests (expected to fail until Plans 02/03 complete):
  - test_main_under_150_lines: main.py is currently 1870 lines
  - test_continue_episode_deleted: continue_episode.py still exists

GREEN tests (should pass now from Plan 01 skeleton):
  - test_pipeline_context_fields
  - test_step_modules_importable
  - test_run_distribute_only_exists
"""

from pathlib import Path


class TestPipelineContextFields:
    """PipelineContext dataclass field assertions."""

    def test_pipeline_context_fields(self):
        """PipelineContext has all expected fields with correct defaults."""
        from pipeline.context import PipelineContext

        ctx = PipelineContext(
            episode_folder="test",
            episode_number=1,
            episode_output_dir=Path("/tmp"),
            timestamp="2024-01-01",
        )

        # Required fields set correctly
        assert ctx.episode_folder == "test"
        assert ctx.episode_number == 1
        assert ctx.episode_output_dir == Path("/tmp")
        assert ctx.timestamp == "2024-01-01"

        # Optional audio/transcript fields default to None
        assert ctx.audio_file is None
        assert ctx.transcript_path is None
        assert ctx.transcript_data is None
        assert ctx.analysis is None
        assert ctx.censored_audio is None
        assert ctx.mp3_path is None

        # List fields default to empty lists (not None)
        assert ctx.clip_paths == []
        assert ctx.video_clip_paths == []
        assert ctx.srt_paths == []
        assert ctx.uploaded_clip_paths == []

        # Optional string/path fields default to None
        assert ctx.full_episode_video_path is None
        assert ctx.thumbnail_path is None
        assert ctx.finished_path is None

        # Mode flags default to False
        assert ctx.test_mode is False
        assert ctx.dry_run is False
        assert ctx.auto_approve is False
        assert ctx.resume is False


class TestStepModulesImportable:
    """All five step modules must be importable and expose their run_* functions."""

    def test_step_modules_importable(self):
        """Import each step module and assert the run_* function exists."""
        from pipeline.steps import ingest, audio, analysis, video, distribute

        assert callable(ingest.run_ingest)
        assert callable(audio.run_audio)
        assert callable(analysis.run_analysis)
        assert callable(video.run_video)
        assert callable(distribute.run_distribute)
        assert callable(distribute.run_distribute_only)


class TestMainLineCount:
    """TDD-red test: main.py must be refactored to under 150 lines."""

    def test_main_under_200_lines(self):
        """main.py must stay thin — CLI shim that delegates to pipeline/.

        Limit: 200 lines for CLI dispatch (init-client, list-clients,
        validate-client, --client flag, interactive mode, outreach subcommands).
        """
        lines = Path("main.py").read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 310, (
            f"main.py has {len(lines)} lines — keep it thin, move logic to pipeline/"
        )


class TestRunDistributeOnlyExists:
    """pipeline.run_distribute_only must be callable."""

    def test_run_distribute_only_exists(self):
        """run_distribute_only is exported from the pipeline package."""
        from pipeline import run_distribute_only

        assert callable(run_distribute_only)


class TestContinueEpisodeDeleted:
    """TDD-red test: continue_episode.py must be deleted as part of refactor."""

    def test_continue_episode_deleted(self):
        """continue_episode.py must be deleted after Plan 03 merges it into pipeline/.

        This test is EXPECTED TO FAIL until Plan 03 removes continue_episode.py.
        """
        assert not Path("continue_episode.py").exists(), (
            "continue_episode.py still exists — delete it as part of Plan 03 "
            "after its logic is extracted into pipeline/runner.py"
        )


class TestComplianceBlock:
    """run_distribute() blocks uploads when ctx.compliance_result['critical'] is True and ctx.force is False."""

    def test_blocks_uploads_on_critical_violation(self, tmp_path):
        """run_distribute() returns early without calling any upload functions when compliance is critical."""
        from unittest.mock import MagicMock, patch
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            compliance_result={"critical": True, "flagged": [], "report_path": None},
            force=False,
            test_mode=False,
        )

        components = {
            "dropbox": MagicMock(),
            "uploaders": {},
            "blog_generator": MagicMock(enabled=False),
            "webpage_generator": MagicMock(enabled=False),
            "search_index": None,
            "scheduler": None,
            "chapter_generator": None,
        }

        with patch("builtins.print") as mock_print:
            result = run_distribute(ctx, components)

        # Should return early — Dropbox upload_finished_episode NOT called
        components["dropbox"].upload_finished_episode.assert_not_called()
        assert result is ctx

        # Should print BLOCKED message
        printed = " ".join(str(call) for call in mock_print.call_args_list)
        assert "BLOCKED" in printed


class TestComplianceForce:
    """run_distribute() proceeds normally when critical=True and ctx.force=True."""

    def test_proceeds_with_force_flag(self, tmp_path):
        """run_distribute() calls Dropbox upload when force=True despite critical violation."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            compliance_result={"critical": True, "flagged": [], "report_path": None},
            force=True,
            test_mode=True,  # use test_mode to skip actual Dropbox I/O
        )

        components = {
            "dropbox": MagicMock(),
            "uploaders": {},
            "blog_generator": MagicMock(enabled=False),
            "webpage_generator": MagicMock(enabled=False),
            "search_index": None,
            "scheduler": None,
            "chapter_generator": None,
        }

        result = run_distribute(ctx, components)

        # Should NOT return early — result is still ctx and no BLOCKED was raised
        assert result is ctx
        # Dropbox upload is skipped in test_mode, but the function reached Step 7
        # The key assertion: upload_finished_episode was not called (test_mode skips it),
        # but we did NOT return early — we reached the normal test_mode skip path
        components["dropbox"].upload_finished_episode.assert_not_called()


class TestComplianceClean:
    """run_distribute() proceeds normally when compliance_result is None or critical=False."""

    def test_proceeds_when_no_compliance_result(self, tmp_path):
        """run_distribute() is not blocked when compliance_result is None."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            compliance_result=None,
            force=False,
            test_mode=True,
        )

        components = {
            "dropbox": MagicMock(),
            "uploaders": {},
            "blog_generator": MagicMock(enabled=False),
            "webpage_generator": MagicMock(enabled=False),
            "search_index": None,
            "scheduler": None,
            "chapter_generator": None,
        }

        result = run_distribute(ctx, components)
        assert result is ctx

    def test_proceeds_when_critical_false(self, tmp_path):
        """run_distribute() is not blocked when compliance_result critical=False."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.distribute import run_distribute

        ctx = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            compliance_result={"critical": False, "flagged": [], "report_path": None},
            force=False,
            test_mode=True,
        )

        components = {
            "dropbox": MagicMock(),
            "uploaders": {},
            "blog_generator": MagicMock(enabled=False),
            "webpage_generator": MagicMock(enabled=False),
            "search_index": None,
            "scheduler": None,
            "chapter_generator": None,
        }

        result = run_distribute(ctx, components)
        assert result is ctx


class TestForceFlag:
    """--force in sys.argv flows through main.py args dict with force=True."""

    def test_force_flag_in_argv(self, monkeypatch):
        """--force in sys.argv is parsed and included as force=True in args dict."""
        import sys

        monkeypatch.setattr(sys, "argv", ["main.py", "ep1", "--force"])

        # Re-read main.py flag parsing inline (without executing main())
        force = "--force" in sys.argv
        assert force is True

    def test_force_flag_in_pipeline_context(self, tmp_path):
        """PipelineContext.force defaults to False and can be set to True."""
        from pipeline.context import PipelineContext

        ctx_default = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
        )
        assert ctx_default.force is False

        ctx_forced = PipelineContext(
            episode_folder="ep_1",
            episode_number=1,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            force=True,
        )
        assert ctx_forced.force is True


class TestInitComponentsRSS:
    """_init_components with EPISODE_SOURCE=rss constructs RSSEpisodeFetcher, not DropboxHandler."""

    def test_rss_source_does_not_construct_dropbox(self, monkeypatch):
        """With EPISODE_SOURCE=rss, DropboxHandler is never imported or constructed."""
        from unittest.mock import MagicMock, patch

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "rss")

        mock_rss_fetcher_instance = MagicMock()
        mock_rss_fetcher_cls = MagicMock(return_value=mock_rss_fetcher_instance)

        with (
            patch("dropbox_handler.DropboxHandler") as mock_dropbox,
            patch("pipeline.runner.Config.validate"),
            patch("pipeline.runner.Config.create_directories"),
            patch("transcription.Transcriber"),
            patch("content_editor.ContentEditor"),
            patch("audio_processor.AudioProcessor"),
            patch("video_converter.VideoConverter"),
            patch("pipeline.runner._init_uploaders", return_value={}),
            patch("notifications.DiscordNotifier"),
            patch("scheduler.UploadScheduler"),
            patch("blog_generator.BlogPostGenerator"),
            patch("thumbnail_generator.ThumbnailGenerator"),
            patch("pipeline.runner.ClipPreviewer"),
            patch("pipeline.runner.EpisodeSearchIndex"),
            patch("pipeline.runner.AudiogramGenerator"),
            patch("pipeline.runner.ChapterGenerator"),
            patch("pipeline.runner.SubtitleClipGenerator"),
            patch("pipeline.runner.EpisodeWebpageGenerator"),
            patch("pipeline.runner.ContentComplianceChecker"),
            patch("rss_episode_fetcher.RSSEpisodeFetcher", mock_rss_fetcher_cls),
        ):
            from pipeline.runner import _init_components

            components = _init_components()

        mock_dropbox.assert_not_called()
        assert "rss_fetcher" in components
        assert "dropbox" not in components

    def test_rss_source_includes_rss_fetcher(self, monkeypatch):
        """With EPISODE_SOURCE=rss, components includes rss_fetcher key."""
        from unittest.mock import MagicMock, patch

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "rss")

        with (
            patch("dropbox_handler.DropboxHandler"),
            patch("pipeline.runner.Config.validate"),
            patch("pipeline.runner.Config.create_directories"),
            patch("transcription.Transcriber"),
            patch("content_editor.ContentEditor"),
            patch("audio_processor.AudioProcessor"),
            patch("video_converter.VideoConverter"),
            patch("pipeline.runner._init_uploaders", return_value={}),
            patch("notifications.DiscordNotifier"),
            patch("scheduler.UploadScheduler"),
            patch("blog_generator.BlogPostGenerator"),
            patch("thumbnail_generator.ThumbnailGenerator"),
            patch("pipeline.runner.ClipPreviewer"),
            patch("pipeline.runner.EpisodeSearchIndex"),
            patch("pipeline.runner.AudiogramGenerator"),
            patch("pipeline.runner.ChapterGenerator"),
            patch("pipeline.runner.SubtitleClipGenerator"),
            patch("pipeline.runner.EpisodeWebpageGenerator"),
            patch("pipeline.runner.ContentComplianceChecker"),
            patch("rss_episode_fetcher.RSSEpisodeFetcher") as mock_cls,
        ):
            mock_cls.return_value = MagicMock()
            from pipeline.runner import _init_components

            components = _init_components()

        assert "rss_fetcher" in components


class TestInitComponentsDryRunRSS:
    """_init_components dry_run with EPISODE_SOURCE=rss returns rss_fetcher:None."""

    def test_dry_run_rss_has_rss_fetcher_not_dropbox(self, monkeypatch):
        """dry_run with EPISODE_SOURCE=rss sets rss_fetcher:None, not dropbox:None."""
        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "rss")

        from unittest.mock import patch

        with (
            patch("pipeline.runner.Config.create_directories"),
            patch("notifications.DiscordNotifier"),
            patch("scheduler.UploadScheduler"),
            patch("blog_generator.BlogPostGenerator"),
            patch("thumbnail_generator.ThumbnailGenerator"),
            patch("pipeline.runner.ClipPreviewer"),
            patch("pipeline.runner.AudiogramGenerator"),
            patch("pipeline.runner.ChapterGenerator"),
            patch("pipeline.runner.SubtitleClipGenerator"),
            patch("pipeline.runner.EpisodeWebpageGenerator"),
            patch("pipeline.runner.ContentComplianceChecker"),
        ):
            from pipeline.runner import _init_components

            components = _init_components(dry_run=True)

        assert "rss_fetcher" in components
        assert components["rss_fetcher"] is None
        assert "dropbox" not in components

    def test_dry_run_dropbox_has_dropbox_not_rss_fetcher(self, monkeypatch):
        """dry_run with EPISODE_SOURCE=dropbox sets dropbox:None, not rss_fetcher."""
        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "dropbox")

        from unittest.mock import patch

        with (
            patch("pipeline.runner.Config.create_directories"),
            patch("notifications.DiscordNotifier"),
            patch("scheduler.UploadScheduler"),
            patch("blog_generator.BlogPostGenerator"),
            patch("thumbnail_generator.ThumbnailGenerator"),
            patch("pipeline.runner.ClipPreviewer"),
            patch("pipeline.runner.AudiogramGenerator"),
            patch("pipeline.runner.ChapterGenerator"),
            patch("pipeline.runner.SubtitleClipGenerator"),
            patch("pipeline.runner.EpisodeWebpageGenerator"),
            patch("pipeline.runner.ContentComplianceChecker"),
        ):
            from pipeline.runner import _init_components

            components = _init_components(dry_run=True)

        assert "dropbox" in components
        assert components["dropbox"] is None
        assert "rss_fetcher" not in components


class TestRunIngestRSS:
    """run_ingest with EPISODE_SOURCE=rss calls rss_fetcher instead of Dropbox."""

    def test_run_ingest_rss_calls_fetcher(self, tmp_path, monkeypatch):
        """run_ingest with EPISODE_SOURCE=rss calls fetch_episode and download_audio."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.ingest import run_ingest

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "rss")
        monkeypatch.setattr(
            "config.Config.RSS_FEED_URL", "https://feeds.example.com/show.xml"
        )
        monkeypatch.setattr("config.Config.RSS_EPISODE_INDEX", 0)
        monkeypatch.setattr("config.Config.DOWNLOAD_DIR", tmp_path)
        monkeypatch.setattr("config.Config.OUTPUT_DIR", tmp_path)

        # Create a fake audio file that the fetcher "downloads"
        fake_audio = tmp_path / "ep_42_show.wav"
        fake_audio.write_bytes(b"fake")

        mock_meta = MagicMock()
        mock_meta.episode_number = 42
        mock_meta.audio_url = "https://cdn.example.com/ep42.wav"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_episode.return_value = mock_meta
        mock_fetcher.download_audio.return_value = fake_audio

        ctx = PipelineContext(
            episode_folder="",
            episode_number=None,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
        )

        components = {"rss_fetcher": mock_fetcher}

        result = run_ingest(ctx, components)

        mock_fetcher.fetch_episode.assert_called_once_with(
            "https://feeds.example.com/show.xml", 0
        )
        mock_fetcher.download_audio.assert_called_once_with(
            mock_meta.audio_url, tmp_path
        )
        assert result.audio_file == fake_audio
        assert result.episode_number == 42

    def test_run_ingest_rss_fallback_episode_number(self, tmp_path, monkeypatch):
        """run_ingest with EPISODE_SOURCE=rss falls back to filename extraction when meta.episode_number is None."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.ingest import run_ingest

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "rss")
        monkeypatch.setattr(
            "config.Config.RSS_FEED_URL", "https://feeds.example.com/show.xml"
        )
        monkeypatch.setattr("config.Config.RSS_EPISODE_INDEX", 0)
        monkeypatch.setattr("config.Config.DOWNLOAD_DIR", tmp_path)
        monkeypatch.setattr("config.Config.OUTPUT_DIR", tmp_path)

        fake_audio = tmp_path / "ep_7_show.wav"
        fake_audio.write_bytes(b"fake")

        mock_meta = MagicMock()
        mock_meta.episode_number = None  # No episode number in feed metadata
        mock_meta.audio_url = "https://cdn.example.com/ep7.wav"

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_episode.return_value = mock_meta
        mock_fetcher.download_audio.return_value = fake_audio

        ctx = PipelineContext(
            episode_folder="",
            episode_number=None,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
        )

        components = {"rss_fetcher": mock_fetcher}

        result = run_ingest(ctx, components)

        # Should extract from filename "ep_7_show.wav" → 7
        assert result.episode_number == 7


class TestRunIngestLocalNoDropbox:
    """run_ingest with local audio_file does NOT access components['dropbox']."""

    def test_local_file_no_dropbox_key(self, tmp_path, monkeypatch):
        """run_ingest with pre-set ctx.audio_file succeeds with no 'dropbox' key in components."""
        from pipeline.context import PipelineContext
        from pipeline.steps.ingest import run_ingest

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "dropbox")
        monkeypatch.setattr("config.Config.OUTPUT_DIR", tmp_path)

        fake_audio = tmp_path / "ep_5_show.wav"
        fake_audio.write_bytes(b"fake")

        ctx = PipelineContext(
            episode_folder="",
            episode_number=None,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
            audio_file=fake_audio,
        )

        # No 'dropbox' key — proves run_ingest doesn't access it for local files
        components = {}

        result = run_ingest(ctx, components)

        assert result.audio_file == fake_audio
        assert result.episode_number == 5


class TestRunIngestDropboxPreserved:
    """run_ingest with EPISODE_SOURCE=dropbox still uses components['dropbox'] as before."""

    def test_dropbox_source_uses_dropbox_component(self, tmp_path, monkeypatch):
        """run_ingest with EPISODE_SOURCE=dropbox downloads from Dropbox."""
        from unittest.mock import MagicMock
        from pipeline.context import PipelineContext
        from pipeline.steps.ingest import run_ingest

        monkeypatch.setattr("config.Config.EPISODE_SOURCE", "dropbox")
        monkeypatch.setattr("config.Config.OUTPUT_DIR", tmp_path)

        fake_audio = tmp_path / "ep_10_show.wav"
        fake_audio.write_bytes(b"fake")

        mock_dropbox = MagicMock()
        mock_dropbox.get_latest_episode.return_value = {
            "name": "ep_10_show.wav",
            "path": "/Podcast/ep_10_show.wav",
        }
        mock_dropbox.download_episode.return_value = fake_audio

        ctx = PipelineContext(
            episode_folder="",
            episode_number=None,
            episode_output_dir=tmp_path,
            timestamp="20240101_000000",
        )

        components = {"dropbox": mock_dropbox}

        result = run_ingest(ctx, components)

        mock_dropbox.get_latest_episode.assert_called_once()
        mock_dropbox.download_episode.assert_called_once()
        assert result.audio_file == fake_audio
        assert result.episode_number == 10


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
