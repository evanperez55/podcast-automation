"""Ingest step: download episode audio from Dropbox, RSS feed, or local path."""

from __future__ import annotations

import logging
from pathlib import Path

from config import Config
from pipeline.context import PipelineContext
from rss_episode_fetcher import extract_episode_number_from_filename

logger = logging.getLogger(__name__)


def run_ingest(
    ctx: PipelineContext,
    components: dict,
    state=None,
) -> PipelineContext:
    """Download episode audio and set ctx.audio_file, ctx.episode_folder, etc.

    Covers Step 1: download/find episode from Dropbox, RSS feed, or local path.
    """
    timestamp = ctx.timestamp
    episode_source = getattr(Config, "EPISODE_SOURCE", "dropbox")
    rss_episode_title = None  # Track RSS title for YouTube video matching

    # Step 1: Determine audio source and download/locate file
    if ctx.audio_file and ctx.audio_file.exists():
        # Local file path — pre-set by caller (e.g., direct path argument)
        audio_file = ctx.audio_file
        logger.info("Using local audio file: %s", audio_file)
        episode_number = extract_episode_number_from_filename(audio_file.name)
    elif episode_source == "rss":
        # RSS feed source
        print("STEP 1: FETCHING LATEST EPISODE FROM RSS FEED")
        print("-" * 60)
        fetcher = components["rss_fetcher"]
        feed_url = getattr(Config, "RSS_FEED_URL", None)
        episode_index = getattr(Config, "RSS_EPISODE_INDEX", 0)
        meta = fetcher.fetch_episode(feed_url, episode_index)
        audio_file = fetcher.download_audio(meta.audio_url, Config.DOWNLOAD_DIR)
        if not audio_file:
            raise Exception("Failed to download episode from RSS feed")
        logger.info("Downloaded RSS episode: %s", audio_file)
        rss_episode_title = meta.title
        # Use episode number from feed metadata, fallback to filename
        episode_number = meta.episode_number or extract_episode_number_from_filename(
            audio_file.name
        )
    else:
        # Dropbox source (default)
        dropbox = components["dropbox"]
        print("STEP 1: FINDING LATEST EPISODE IN DROPBOX")
        print("-" * 60)
        latest = dropbox.get_latest_episode()
        if not latest:
            raise Exception("No episodes found in Dropbox")

        logger.info("Latest episode: %s", latest["name"])
        audio_file = dropbox.download_episode(latest["path"])
        if not audio_file:
            raise Exception("Failed to download episode from Dropbox")
        episode_number = extract_episode_number_from_filename(audio_file.name)

    if episode_number:
        episode_folder = f"ep_{episode_number}"
    else:
        episode_folder = f"ep_{audio_file.stem}_{timestamp}"

    # Create episode output subfolder
    episode_output_dir = Config.OUTPUT_DIR / episode_folder
    episode_output_dir.mkdir(exist_ok=True, parents=True)

    # Check if input is a video file — extract audio for transcription pipeline
    from video_utils import is_video_file, probe_video, extract_audio

    # If input is audio-only but a YouTube channel is configured, download video
    youtube_channel = getattr(Config, "VIDEO_SOURCE_YOUTUBE_CHANNEL", None)
    if not is_video_file(audio_file) and youtube_channel:
        logger.info("YouTube video source configured: %s", youtube_channel)
        from youtube_video_downloader import YouTubeVideoDownloader

        yt_downloader = YouTubeVideoDownloader()
        if yt_downloader.enabled:
            # Try to match by episode title from RSS metadata if available
            match_title = rss_episode_title
            video_path = yt_downloader.download_latest(
                youtube_channel, Config.DOWNLOAD_DIR, match_title=match_title
            )
            if video_path:
                logger.info("Downloaded YouTube video: %s", video_path.name)
                audio_file = video_path

    if is_video_file(audio_file):
        logger.info("Video input detected: %s", audio_file.name)
        ctx.source_video_path = audio_file
        ctx.has_video_source = True
        ctx.video_metadata = probe_video(str(audio_file))
        if ctx.video_metadata:
            logger.info(
                "Video: %dx%d, %.1fs, %s",
                ctx.video_metadata["width"],
                ctx.video_metadata["height"],
                ctx.video_metadata["duration"],
                ctx.video_metadata["codec"],
            )

        # Extract audio track for the rest of the pipeline
        extracted_path = Config.DOWNLOAD_DIR / f"{audio_file.stem}_extracted.wav"
        extracted = extract_audio(str(audio_file), str(extracted_path))
        if not extracted:
            raise Exception(f"Failed to extract audio from video: {audio_file}")
        audio_file = Path(extracted)
        logger.info("Using extracted audio: %s", audio_file)

    ctx.audio_file = audio_file
    ctx.episode_folder = episode_folder
    ctx.episode_number = episode_number
    ctx.episode_output_dir = episode_output_dir

    return ctx
