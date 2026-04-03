"""Content Calendar module for Fake Problems Podcast.

Generates a per-episode multi-slot distribution plan spreading content
across D-1/D0/D+2/D+4/D+6, persists state to topic_data/content_calendar.json,
and provides slot query/update methods.

Replaces same-day dump uploads with a deliberate weekly spread for better
engagement.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from config import Config
from posting_time_optimizer import PostingTimeOptimizer

logger = logging.getLogger(__name__)

# 2-week content calendar for bi-weekly episodes
# Clips 1-2 go public on YouTube at D+0 (pipeline upload)
# Clips 3-8 are uploaded private, made public on their scheduled day
_CLIP_OFFSETS = [1, 3, 5, 7, 9, 11]  # D+1,3,5,7,9,11 for clips 3-8
_QUOTE_OFFSETS = [2, 4, 6]  # D+2,4,6 interleaved with clips
_MAX_CLIP_SLOTS = 6
_MAX_QUOTE_SLOTS = 3

# Mapping from slot type / platform to Config fallback hour attribute
_PLATFORM_HOUR_ATTR = {
    "youtube": "SCHEDULE_YOUTUBE_POSTING_HOUR",
    "twitter": "SCHEDULE_TWITTER_POSTING_HOUR",
    "instagram": "SCHEDULE_INSTAGRAM_POSTING_HOUR",
    "tiktok": "SCHEDULE_TIKTOK_POSTING_HOUR",
}


class ContentCalendar:
    """Manage per-episode distribution slot plans.

    Slots span D-1 (teaser) through D+6 (third clip), stored in
    topic_data/content_calendar.json.
    """

    def __init__(self) -> None:
        self.enabled: bool = Config.CONTENT_CALENDAR_ENABLED
        self.calendar_path = Config.TOPIC_DATA_DIR / "content_calendar.json"
        self._optimizer = PostingTimeOptimizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_episode(
        self,
        episode_number: int,
        release_date: datetime,
        analysis: dict,
        video_clip_paths: Optional[list[str]] = None,
        full_episode_video_path: Optional[str] = None,
    ) -> dict:
        """Generate a distribution slot plan for an episode.

        Idempotent: if the episode key already exists, the existing entry is
        returned unchanged.

        Args:
            episode_number: Episode identifier (e.g. 29).
            release_date: The canonical release date/time (D0).
            analysis: Result dict from content analysis containing best_clips.
            video_clip_paths: Paths to generated clip video files (capped at 3).
            full_episode_video_path: Optional path to full episode video.

        Returns:
            The episode entry dict stored in the calendar.
        """
        episode_key = f"ep_{episode_number}"
        data = self.load_all()

        # Idempotency guard
        if episode_key in data:
            logger.info(
                "ContentCalendar: episode %s already planned, returning existing",
                episode_key,
            )
            return data[episode_key]

        slots: dict[str, dict] = {}

        # Determine teaser eligibility: need at least one best_clip with hook_caption
        best_clips = analysis.get("best_clips") or []
        has_teaser = bool(best_clips and best_clips[0].get("hook_caption"))

        # Teaser slot: D-1, twitter only
        if has_teaser:
            slots["teaser"] = self._build_slot(
                slot_type="teaser",
                day_offset=-1,
                release_date=release_date,
                platforms=["twitter"],
                clip_index=None,
                content={
                    "caption": best_clips[0]["hook_caption"],
                },
            )

        # Episode slot: D0, youtube + twitter
        slots["episode"] = self._build_slot(
            slot_type="episode",
            day_offset=0,
            release_date=release_date,
            platforms=["youtube", "twitter"],
            clip_index=None,
            content={
                "title": f"Episode {episode_number}",
                "video_path": full_episode_video_path,
            },
        )

        # Clip slots: clips 3-8 get staggered across 2 weeks
        # (clips 1-2 are uploaded public on D+0 by the pipeline)
        all_clip_paths = video_clip_paths or []
        stagger_clips = all_clip_paths[2:]  # skip first 2 (already public)
        for idx, clip_path in enumerate(stagger_clips[:_MAX_CLIP_SLOTS]):
            clip_num = idx + 3  # clip_3 through clip_8
            slot_name = f"clip_{clip_num}"
            day_offset = _CLIP_OFFSETS[idx]
            caption = ""
            clip_idx_in_analysis = clip_num - 1  # 0-indexed into best_clips
            if clip_idx_in_analysis < len(best_clips):
                caption = best_clips[clip_idx_in_analysis].get("hook_caption", "")
            slots[slot_name] = self._build_slot(
                slot_type=slot_name,
                day_offset=day_offset,
                release_date=release_date,
                platforms=["youtube", "twitter", "bluesky"],
                clip_index=clip_idx_in_analysis,
                content={
                    "caption": caption,
                    "clip_path": clip_path,
                },
            )

        # Quote card slots: D+2, D+4, D+6 (interleaved with clips)
        best_quotes = analysis.get("best_quotes", [])
        for idx, quote_data in enumerate(best_quotes[:_MAX_QUOTE_SLOTS]):
            slot_name = f"quote_{idx + 1}"
            day_offset = _QUOTE_OFFSETS[idx]
            slots[slot_name] = self._build_slot(
                slot_type=slot_name,
                day_offset=day_offset,
                release_date=release_date,
                platforms=["twitter", "bluesky"],
                clip_index=None,
                content={
                    "quote_text": quote_data.get("quote", ""),
                    "timestamp": quote_data.get("timestamp", ""),
                },
            )

        entry: dict[str, Any] = {
            "episode_number": episode_number,
            "release_date": release_date.isoformat(),
            "planned_at": datetime.now().isoformat(),
            "slots": slots,
        }

        data[episode_key] = entry
        self.save(data)
        logger.info("ContentCalendar: planned %d slots for %s", len(slots), episode_key)
        return entry

    def get_pending_slots(self, episode_data: dict) -> list[dict]:
        """Return slots that are pending and past their scheduled_at time.

        Args:
            episode_data: A single episode entry dict from the calendar.

        Returns:
            List of slot dicts (with slot_name injected as 'slot_name' key)
            where status=='pending' and scheduled_at <= now.
        """
        now = datetime.now()
        pending = []
        for slot_name, slot in (episode_data.get("slots") or {}).items():
            if slot.get("status") != "pending":
                continue
            scheduled_str = slot.get("scheduled_at", "")
            try:
                scheduled_at = datetime.fromisoformat(scheduled_str)
            except (ValueError, TypeError):
                continue
            if scheduled_at <= now:
                pending.append({**slot, "slot_name": slot_name})
        return pending

    def mark_slot_uploaded(
        self,
        episode_key: str,
        slot_name: str,
        upload_results: dict,
    ) -> None:
        """Mark a slot as successfully uploaded.

        Args:
            episode_key: e.g. 'ep_29'.
            slot_name: Slot identifier, e.g. 'episode' or 'clip_1'.
            upload_results: Dict of upload metadata (e.g. video_id).
        """
        data = self.load_all()
        if episode_key not in data:
            logger.warning(
                "ContentCalendar.mark_slot_uploaded: unknown episode %s", episode_key
            )
            return
        if slot_name not in data[episode_key]["slots"]:
            logger.warning(
                "ContentCalendar.mark_slot_uploaded: unknown slot %s in %s",
                slot_name,
                episode_key,
            )
            return
        data[episode_key]["slots"][slot_name].update(
            {
                "status": "uploaded",
                "uploaded_at": datetime.now().isoformat(),
                "upload_results": upload_results,
            }
        )
        self.save(data)

    def mark_slot_failed(
        self,
        episode_key: str,
        slot_name: str,
        error: str,
    ) -> None:
        """Mark a slot as failed with an error message.

        Args:
            episode_key: e.g. 'ep_29'.
            slot_name: Slot identifier, e.g. 'episode' or 'clip_1'.
            error: Human-readable error description.
        """
        data = self.load_all()
        if episode_key not in data:
            logger.warning(
                "ContentCalendar.mark_slot_failed: unknown episode %s", episode_key
            )
            return
        if slot_name not in data[episode_key]["slots"]:
            logger.warning(
                "ContentCalendar.mark_slot_failed: unknown slot %s in %s",
                slot_name,
                episode_key,
            )
            return
        current_retries = data[episode_key]["slots"][slot_name].get("retry_count", 0)
        data[episode_key]["slots"][slot_name].update(
            {
                "status": "failed",
                "error": error,
                "retry_count": current_retries + 1,
            }
        )
        self.save(data)

    def update_slot_content(
        self,
        episode_key: str,
        slot_name: str,
        content_updates: dict,
    ) -> None:
        """Merge additional content keys into an existing slot.

        Args:
            episode_key: e.g. 'ep_30'.
            slot_name: Slot identifier, e.g. 'clip_1'.
            content_updates: Dict of keys to merge into slot["content"].
        """
        data = self.load_all()
        if episode_key not in data:
            return
        slots = data[episode_key].get("slots", {})
        if slot_name not in slots:
            return
        slots[slot_name].setdefault("content", {}).update(content_updates)
        self.save(data)

    def get_all_pending_slots(self) -> list[dict]:
        """Return all pending or retryable failed slots across all episodes that are past due.

        Returns:
            List of slot dicts augmented with 'episode_key' and 'slot_name'.
        """
        now = datetime.now()
        # Grace window: treat slots within 5 minutes of now as due
        grace = now + timedelta(minutes=5)
        results = []
        for ep_key, ep_data in self.load_all().items():
            for slot_name, slot in (ep_data.get("slots") or {}).items():
                if slot.get("status") not in ("pending", "failed"):
                    continue
                if slot.get("status") == "failed" and slot.get("retry_count", 0) >= 3:
                    continue
                scheduled_str = slot.get("scheduled_at", "")
                if not scheduled_str:
                    continue
                try:
                    scheduled = datetime.fromisoformat(scheduled_str)
                    # Strip timezone info to avoid naive vs aware comparison crash
                    if scheduled.tzinfo is not None:
                        scheduled = scheduled.replace(tzinfo=None)
                except (ValueError, TypeError):
                    continue
                if scheduled <= grace:
                    results.append(
                        {
                            "episode_key": ep_key,
                            "slot_name": slot_name,
                            **slot,
                        }
                    )
        return results

    def load_all(self) -> dict:
        """Load the full calendar from disk.

        Returns:
            Dict mapping episode keys to entry dicts. Empty dict if file
            doesn't exist.
        """
        if not self.calendar_path.exists():
            return {}
        try:
            return json.loads(self.calendar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(
                "ContentCalendar: failed to load %s: %s", self.calendar_path, exc
            )
            return {}

    def save(self, data: dict) -> None:
        """Atomically write the calendar to disk via .tmp + Path.replace().

        Args:
            data: The full calendar dict to persist.
        """
        self.calendar_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.calendar_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp_path.replace(self.calendar_path)

    def get_calendar_display(
        self,
        episode_number: int,
        release_date: datetime,
    ) -> list[dict]:
        """Return a slot preview list for dry-run display.

        Does NOT persist anything.

        Args:
            episode_number: Episode identifier.
            release_date: The canonical release date (D0).

        Returns:
            List of dicts with keys: label, dt (datetime), type, platforms.
        """
        display = []
        slots_info = [
            ("teaser", -1, "twitter"),
            ("episode", 0, "youtube"),
            ("clip_3", 1, "youtube"),
            ("quote_1", 2, "twitter"),
            ("clip_4", 3, "youtube"),
            ("quote_2", 4, "twitter"),
            ("clip_5", 5, "youtube"),
            ("quote_3", 6, "twitter"),
            ("clip_6", 7, "youtube"),
            ("clip_7", 9, "youtube"),
            ("clip_8", 11, "youtube"),
        ]
        for slot_type, day_offset, primary_platform in slots_info:
            dt = self._slot_datetime(release_date, day_offset, primary_platform)
            display.append(
                {
                    "label": f"ep_{episode_number} / {slot_type}",
                    "dt": dt,
                    "type": slot_type,
                    "platforms": [primary_platform],
                }
            )
        return display

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _slot_datetime(
        self,
        release_date: datetime,
        day_offset: int,
        platform: str,
    ) -> datetime:
        """Compute the scheduled datetime for a slot.

        Uses PostingTimeOptimizer's hour when available; falls back to the
        configured posting hour for the platform.

        Args:
            release_date: The D0 reference date.
            day_offset: Days relative to D0 (negative = before release).
            platform: Primary platform for this slot.

        Returns:
            datetime with the appropriate hour set.
        """
        optimal = self._optimizer.get_optimal_publish_at(platform)
        if optimal is not None:
            hour = optimal.hour
        else:
            attr = _PLATFORM_HOUR_ATTR.get(
                platform.lower(), "SCHEDULE_YOUTUBE_POSTING_HOUR"
            )
            hour = getattr(Config, attr, 14)

        base = release_date + timedelta(days=day_offset)
        return base.replace(hour=hour, minute=0, second=0, microsecond=0)

    def _build_slot(
        self,
        slot_type: str,
        day_offset: int,
        release_date: datetime,
        platforms: list[str],
        clip_index: Optional[int],
        content: dict,
    ) -> dict:
        """Construct a slot dict.

        Args:
            slot_type: Slot identifier string ('teaser', 'episode', 'clip_1', etc.).
            day_offset: Days relative to D0.
            release_date: D0 reference datetime.
            platforms: List of platform names.
            clip_index: Index into clip list (0-based), or None.
            content: Slot-specific content payload.

        Returns:
            Slot dict ready to insert into the calendar.
        """
        primary_platform = platforms[0] if platforms else "youtube"
        scheduled_at = self._slot_datetime(release_date, day_offset, primary_platform)
        return {
            "slot_type": slot_type,
            "day_offset": day_offset,
            "scheduled_at": scheduled_at.isoformat(),
            "platforms": platforms,
            "clip_index": clip_index,
            "content": content,
            "status": "pending",
            "uploaded_at": None,
            "upload_results": {},
        }
