"""Post scheduling module for staggered multi-platform uploads."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from config import Config
from logger import logger


class UploadScheduler:
    """Manages scheduled uploads across platforms with configurable delays."""

    def __init__(self):
        self.youtube_delay = Config.SCHEDULE_YOUTUBE_DELAY_HOURS
        self.twitter_delay = Config.SCHEDULE_TWITTER_DELAY_HOURS
        self.instagram_delay = Config.SCHEDULE_INSTAGRAM_DELAY_HOURS
        self.tiktok_delay = Config.SCHEDULE_TIKTOK_DELAY_HOURS

    def is_scheduling_enabled(self) -> bool:
        """Return True if any platform has a delay configured."""
        return any(
            delay > 0
            for delay in [
                self.youtube_delay,
                self.twitter_delay,
                self.instagram_delay,
                self.tiktok_delay,
            ]
        )

    def create_schedule(
        self,
        episode_folder: str,
        episode_number: str,
        analysis: Dict[str, Any],
        video_clip_paths: Optional[List[str]] = None,
        full_episode_video_path: Optional[str] = None,
        mp3_path: Optional[str] = None,
    ) -> dict:
        """Create a schedule dict with per-platform publish times and metadata.

        Args:
            episode_folder: Name of the episode folder under output/.
            episode_number: Episode identifier (e.g. "ep25").
            analysis: Content analysis dict from content_editor.
            video_clip_paths: Paths to generated video clips.
            full_episode_video_path: Path to the full episode video.
            mp3_path: Path to the final MP3 file.

        Returns:
            Schedule dict with platform entries for all platforms with delay > 0.
        """
        now = datetime.now()
        platforms: Dict[str, Any] = {}

        if self.youtube_delay > 0:
            platforms["youtube"] = {
                "status": "pending",
                "publish_at": (now + timedelta(hours=self.youtube_delay)).isoformat(),
                "delay_hours": self.youtube_delay,
                "full_episode_video_path": full_episode_video_path,
                "episode_title": analysis.get("episode_title"),
                "episode_summary": analysis.get("episode_summary"),
                "show_notes": analysis.get("show_notes"),
                "chapters": analysis.get("chapters"),
                "social_captions": analysis.get("social_captions", {}).get("youtube"),
            }

        if self.twitter_delay > 0:
            platforms["twitter"] = {
                "status": "pending",
                "publish_at": (now + timedelta(hours=self.twitter_delay)).isoformat(),
                "delay_hours": self.twitter_delay,
                "video_clip_paths": video_clip_paths,
                "social_captions": analysis.get("social_captions", {}).get("twitter"),
            }

        if self.instagram_delay > 0:
            platforms["instagram"] = {
                "status": "pending",
                "publish_at": (now + timedelta(hours=self.instagram_delay)).isoformat(),
                "delay_hours": self.instagram_delay,
                "video_clip_paths": video_clip_paths,
                "social_captions": analysis.get("social_captions", {}).get("instagram"),
            }

        if self.tiktok_delay > 0:
            platforms["tiktok"] = {
                "status": "pending",
                "publish_at": (now + timedelta(hours=self.tiktok_delay)).isoformat(),
                "delay_hours": self.tiktok_delay,
                "video_clip_paths": video_clip_paths,
                "social_captions": analysis.get("social_captions", {}).get("tiktok"),
            }

        schedule = {
            "episode_number": episode_number,
            "episode_folder": episode_folder,
            "created_at": now.isoformat(),
            "platforms": platforms,
        }

        logger.info(
            f"Created upload schedule for {episode_number} "
            f"with {len(platforms)} platform(s)"
        )
        return schedule

    def save_schedule(self, episode_folder: str, schedule: dict) -> Path:
        """Write schedule to output/{episode_folder}/upload_schedule.json atomically.

        Writes to a .tmp file first, then renames to avoid partial reads.

        Args:
            episode_folder: Name of the episode folder under output/.
            schedule: The schedule dict to persist.

        Returns:
            Path to the saved schedule file.
        """
        output_dir = Config.OUTPUT_DIR / episode_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        schedule_path = output_dir / "upload_schedule.json"
        tmp_path = output_dir / "upload_schedule.json.tmp"

        tmp_path.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
        tmp_path.replace(schedule_path)

        logger.info(f"Saved upload schedule to {schedule_path}")
        return schedule_path

    def load_schedule(self, episode_folder: str) -> Optional[dict]:
        """Read upload_schedule.json from output/{episode_folder}/.

        Args:
            episode_folder: Name of the episode folder under output/.

        Returns:
            The schedule dict, or None if the file does not exist.
        """
        schedule_path = Config.OUTPUT_DIR / episode_folder / "upload_schedule.json"

        if not schedule_path.exists():
            logger.debug(f"No schedule found at {schedule_path}")
            return None

        schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
        logger.debug(f"Loaded upload schedule from {schedule_path}")
        return schedule

    def get_pending_uploads(self, schedule: dict) -> List[dict]:
        """Return platform entries that are pending and past their publish time.

        Args:
            schedule: A schedule dict as created by create_schedule.

        Returns:
            List of platform entry dicts, each with an added "platform" key.
        """
        now = datetime.now()
        pending = []

        for platform, entry in schedule.get("platforms", {}).items():
            if entry.get("status") != "pending":
                continue
            publish_at = datetime.fromisoformat(entry["publish_at"])
            if publish_at <= now:
                pending.append({**entry, "platform": platform})

        return pending

    def mark_uploaded(self, schedule: dict, platform: str, result: Any) -> dict:
        """Mark a platform as uploaded in the schedule.

        Args:
            schedule: The schedule dict to update.
            platform: Platform name (youtube, twitter, instagram, tiktok).
            result: Upload result data to store.

        Returns:
            The updated schedule dict.
        """
        if platform in schedule.get("platforms", {}):
            schedule["platforms"][platform]["status"] = "uploaded"
            schedule["platforms"][platform]["upload_result"] = result
            schedule["platforms"][platform]["uploaded_at"] = datetime.now().isoformat()
            logger.info(f"Marked {platform} as uploaded for schedule")

        return schedule

    def mark_failed(self, schedule: dict, platform: str, error: str) -> dict:
        """Mark a platform upload as failed in the schedule.

        Args:
            schedule: The schedule dict to update.
            platform: Platform name (youtube, twitter, instagram, tiktok).
            error: Error message describing the failure.

        Returns:
            The updated schedule dict.
        """
        if platform in schedule.get("platforms", {}):
            schedule["platforms"][platform]["status"] = "failed"
            schedule["platforms"][platform]["error"] = error
            schedule["platforms"][platform]["failed_at"] = datetime.now().isoformat()
            logger.error("Marked %s as failed: %s", platform, error)
        return schedule

    def get_youtube_publish_at(self) -> Optional[str]:
        """Get the ISO datetime string for YouTube's publishAt scheduling parameter.

        Returns:
            ISO datetime string (now + youtube_delay) if delay > 0, else None.
        """
        if self.youtube_delay > 0:
            publish_at = (
                datetime.now() + timedelta(hours=self.youtube_delay)
            ).isoformat()
            logger.debug(f"YouTube publishAt: {publish_at}")
            return publish_at
        return None
