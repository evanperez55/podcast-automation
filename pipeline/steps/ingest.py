"""Ingest step: download episode audio from Dropbox."""

from __future__ import annotations

from pipeline.context import PipelineContext


def run_ingest(ctx: PipelineContext, dropbox) -> PipelineContext:
    """Download episode audio and set ctx.audio_file.

    Stub — extraction pending Plan 02.
    """
    raise NotImplementedError("Extraction pending — Plan 02")
