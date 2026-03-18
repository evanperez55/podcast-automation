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

    def test_main_under_150_lines(self):
        """main.py must be under 150 lines after extraction to pipeline/.

        This test is EXPECTED TO FAIL until Plan 03 extracts main.py logic.
        Currently main.py is ~1870 lines.
        """
        lines = Path("main.py").read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 150, (
            f"main.py has {len(lines)} lines — must be refactored to pipeline/runner.py "
            f"(Plan 03) before this test goes green"
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
