"""Distribute step: upload to all platforms and finalize distribution."""

from __future__ import annotations

from pipeline.context import PipelineContext


def run_distribute(ctx: PipelineContext, components: dict) -> PipelineContext:
    """Upload MP3 and clips to all configured platforms.

    Stub — extraction pending Plan 02.
    """
    raise NotImplementedError("Extraction pending — Plan 02")


def run_distribute_only(
    episode_number: int,
    skip_video: bool = False,
    skip_upload: bool = False,
) -> None:
    """Re-run distribution for an already-processed episode.

    Stub — extraction pending Plan 02.
    """
    raise NotImplementedError("Extraction pending — Plan 02")
