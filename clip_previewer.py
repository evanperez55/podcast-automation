"""Clip preview and approval module for the podcast automation pipeline."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from logger import logger


class ClipPreviewer:
    """Interactive clip preview and approval workflow."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve

    def preview_clips(
        self, clip_paths: List[str], clip_info: List[Dict[str, Any]]
    ) -> List[int]:
        """Display clip details and prompt user for approval.

        Args:
            clip_paths: List of file paths to clip audio files.
            clip_info: List of dicts with clip metadata (duration_seconds,
                       suggested_title, description, etc.).

        Returns:
            List of approved clip indices (0-based).
        """
        if self.auto_approve:
            logger.info("Auto-approving all %d clips", len(clip_paths))
            return list(range(len(clip_paths)))

        skipped: set[int] = set()

        while True:
            self._display_clip_table(clip_paths, clip_info, skipped)

            action = input(
                "Enter action: [A]pprove all, [S]kip N (e.g. S2), "
                "[P]lay N (e.g. P1), [Q]uit: "
            ).strip()

            if not action:
                continue

            command = action[0].lower()

            if command == "a":
                approved = [i for i in range(len(clip_paths)) if i not in skipped]
                logger.info("Approved %d clips", len(approved))
                return approved

            elif command == "s":
                idx = self._parse_index(action, len(clip_paths))
                if idx is not None:
                    skipped.add(idx)
                    logger.info("Skipped clip %d", idx + 1)
                else:
                    print("Invalid clip number. Try again.")

            elif command == "p":
                idx = self._parse_index(action, len(clip_paths))
                if idx is not None:
                    self._play_clip(clip_paths[idx])
                else:
                    print("Invalid clip number. Try again.")

            elif command == "q":
                logger.info("User quit clip approval -- skipping all clips")
                return []

            else:
                print("Unknown action. Try again.")

    def _display_clip_table(
        self,
        clip_paths: List[str],
        clip_info: List[Dict[str, Any]],
        skipped: set[int],
    ) -> None:
        """Print a formatted table of clips."""
        print("\n" + "=" * 80)
        print(f"{'#':<4} {'File':<25} {'Dur':<8} {'Title':<20} {'Description'}")
        print("-" * 80)

        for i, (path, info) in enumerate(zip(clip_paths, clip_info)):
            if i in skipped:
                continue

            filename = Path(path).name
            duration = info.get("duration_seconds", "?")
            title = info.get("suggested_title", "Untitled")
            description = info.get("description", "")
            desc_snippet = description[:60] + ("..." if len(description) > 60 else "")

            print(
                f"{i + 1:<4} {filename:<25} {str(duration):<8} "
                f"{title:<20} {desc_snippet}"
            )

        print("=" * 80)

    def _parse_index(self, action: str, total: int) -> Optional[int]:
        """Parse a 1-based clip index from an action string like 'S2' or 'P1'.

        Returns:
            0-based index if valid, None otherwise.
        """
        try:
            num = int(action[1:])
            if 1 <= num <= total:
                return num - 1
        except (ValueError, IndexError):
            pass
        return None

    def _play_clip(self, clip_path: str) -> None:
        """Open the audio file using the system default player.

        Args:
            clip_path: Path to the audio file to play.
        """
        try:
            if os.name == "nt":
                subprocess.Popen(
                    ["start", "", str(clip_path)],
                    shell=True,  # noqa: S603
                )
            elif os.uname().sysname == "Darwin":
                subprocess.Popen(["open", str(clip_path)])  # noqa: S603
            else:
                subprocess.Popen(["xdg-open", str(clip_path)])  # noqa: S603

            logger.info("Playing clip: %s", clip_path)
        except Exception as exc:
            logger.warning("Could not play clip %s: %s", clip_path, exc)

    def filter_clips(
        self,
        clip_paths: List[str],
        clip_info: List[Dict[str, Any]],
        approved_indices: List[int],
    ) -> tuple:
        """Filter clip_paths and clip_info to only include approved indices.

        Args:
            clip_paths: Full list of clip file paths.
            clip_info: Full list of clip metadata dicts.
            approved_indices: 0-based indices of approved clips.

        Returns:
            Tuple of (filtered_clip_paths, filtered_clip_info).
        """
        filtered_paths = [clip_paths[i] for i in approved_indices]
        filtered_info = [clip_info[i] for i in approved_indices]
        return filtered_paths, filtered_info
