"""Ingest step: download episode audio from Dropbox."""

from __future__ import annotations

import logging

from config import Config
from pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


def run_ingest(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Download episode audio and set ctx.audio_file, ctx.episode_folder, etc.

    Covers Step 1: download/find episode from Dropbox or local path.
    """
    timestamp = ctx.timestamp

    # Step 1: Download from Dropbox (if needed)
    # Note: ctx.audio_file may be pre-set if local_audio_path was provided.
    if ctx.audio_file and ctx.audio_file.exists():
        audio_file = ctx.audio_file
        logger.info("Using local audio file: %s", audio_file)
    else:
        dropbox = components["dropbox"]
        # Use latest episode
        print("STEP 1: FINDING LATEST EPISODE IN DROPBOX")
        print("-" * 60)
        latest = dropbox.get_latest_episode()
        if not latest:
            raise Exception("No episodes found in Dropbox")

        logger.info("Latest episode: %s", latest["name"])
        audio_file = dropbox.download_episode(latest["path"])
        if not audio_file:
            raise Exception("Failed to download episode from Dropbox")

    # Extract episode number for folder organization
    dropbox = components["dropbox"]
    episode_number = dropbox.extract_episode_number(audio_file.name)
    if episode_number:
        episode_folder = f"ep_{episode_number}"
    else:
        episode_folder = f"ep_{audio_file.stem}_{timestamp}"

    # Create episode output subfolder
    episode_output_dir = Config.OUTPUT_DIR / episode_folder
    episode_output_dir.mkdir(exist_ok=True, parents=True)

    ctx.audio_file = audio_file
    ctx.episode_folder = episode_folder
    ctx.episode_number = episode_number
    ctx.episode_output_dir = episode_output_dir

    return ctx
