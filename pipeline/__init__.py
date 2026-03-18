"""Pipeline package — public API for the podcast automation pipeline.

Plan 03 will replace the stub run() and run_distribute_only() here with
delegation to pipeline/runner.py once extraction from main.py is complete.
"""

from __future__ import annotations

from pipeline.context import PipelineContext

__all__ = ["PipelineContext", "run", "run_distribute_only"]


def run(
    episode_folder: str,
    episode_number: int | None = None,
    test_mode: bool = False,
    dry_run: bool = False,
    auto_approve: bool = False,
    resume: bool = False,
) -> PipelineContext:
    """Run the full episode processing pipeline.

    Stub — runner delegation pending Plan 03.
    """
    raise NotImplementedError("Runner delegation pending — Plan 03")


def run_distribute_only(
    episode_number: int,
    skip_video: bool = False,
    skip_upload: bool = False,
) -> None:
    """Re-run distribution step only for an already-processed episode.

    Stub — runner delegation pending Plan 03.
    """
    raise NotImplementedError("Runner delegation pending — Plan 03")
