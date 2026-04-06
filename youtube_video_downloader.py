"""YouTube video downloader — fetches podcast episode videos via yt-dlp.

Downloads the latest (or matched) video from a YouTube channel for use as
a video source in the pipeline, enabling stacked speaker view clip generation.
"""

import re
from pathlib import Path
from typing import Optional

from logger import logger


class YouTubeVideoDownloader:
    """Downloads podcast episode videos from YouTube channels using yt-dlp."""

    def __init__(self):
        """Initialize downloader. Always enabled when yt-dlp is importable."""
        try:
            import yt_dlp  # noqa: F401

            self.enabled = True
        except ImportError:
            self.enabled = False
            logger.warning("yt-dlp not installed — YouTube video download disabled")

    def download_latest(
        self,
        channel_url: str,
        output_dir: Path,
        match_title: Optional[str] = None,
    ) -> Optional[Path]:
        """Download the latest video from a YouTube channel.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@handle).
            output_dir: Directory to save the downloaded video.
            match_title: Optional substring to match against video titles.
                If provided, downloads the first video whose title contains
                this string (case-insensitive). If None, downloads the latest.

        Returns:
            Path to the downloaded video file, or None on failure.
        """
        if not self.enabled:
            return None

        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)

        # First, list recent videos to find the right one
        videos_url = channel_url.rstrip("/") + "/videos"

        list_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": 10,
        }

        try:
            with yt_dlp.YoutubeDL(list_opts) as ydl:
                info = ydl.extract_info(videos_url, download=False)
        except Exception as e:
            logger.warning("Failed to list videos from %s: %s", channel_url, e)
            return None

        entries = info.get("entries", [])
        if not entries:
            logger.warning("No videos found on channel: %s", channel_url)
            return None

        # Find the target video
        target = None
        if match_title:
            pattern = re.compile(re.escape(match_title), re.IGNORECASE)
            for entry in entries:
                title = entry.get("title", "")
                if pattern.search(title):
                    target = entry
                    logger.info("Matched video: %s", title)
                    break
            if not target:
                logger.warning(
                    "No video matching '%s' found, using latest", match_title
                )
                target = entries[0]
        else:
            target = entries[0]

        video_url = (
            target.get("url") or f"https://www.youtube.com/watch?v={target['id']}"
        )
        video_title = target.get("title", "episode")
        logger.info("Downloading video: %s", video_title)

        # Sanitize filename
        safe_name = re.sub(r"[^\w\s-]", "", video_title).strip()
        safe_name = re.sub(r"[\s]+", "_", safe_name).lower()[:80]

        download_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": str(output_dir / f"{safe_name}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": False,
        }

        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                result = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(result)
                # yt-dlp may change extension after merge
                final_path = Path(filename).with_suffix(".mp4")
                if not final_path.exists():
                    # Try the exact filename
                    final_path = Path(filename)
                if final_path.exists():
                    logger.info(
                        "Downloaded video: %s (%.1f MB)",
                        final_path.name,
                        final_path.stat().st_size / 1024 / 1024,
                    )
                    return final_path
                logger.warning("Download completed but file not found: %s", final_path)
                return None
        except Exception as e:
            logger.warning("Failed to download video from %s: %s", video_url, e)
            return None

    def download_url(
        self,
        video_url: str,
        output_dir: Path,
    ) -> Optional[Path]:
        """Download a specific YouTube video by URL.

        Args:
            video_url: Direct YouTube video URL.
            output_dir: Directory to save the downloaded video.

        Returns:
            Path to the downloaded video file, or None on failure.
        """
        if not self.enabled:
            return None

        import yt_dlp

        output_dir.mkdir(parents=True, exist_ok=True)

        download_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
        }

        try:
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                result = ydl.extract_info(video_url, download=True)
                filename = ydl.prepare_filename(result)
                final_path = Path(filename).with_suffix(".mp4")
                if not final_path.exists():
                    final_path = Path(filename)
                if final_path.exists():
                    logger.info(
                        "Downloaded video: %s (%.1f MB)",
                        final_path.name,
                        final_path.stat().st_size / 1024 / 1024,
                    )
                    return final_path
                logger.warning("Download completed but file not found: %s", final_path)
                return None
        except Exception as e:
            logger.warning("Failed to download video %s: %s", video_url, e)
            return None
