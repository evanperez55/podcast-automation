"""Chapter marker generation: ID3 CHAP/CTOC frames and Podcasting 2.0 JSON."""

import json
import os

import mutagen.id3
import mutagen.mp3

from logger import logger


class ChapterGenerator:
    """Generate and embed chapter markers for podcast episodes."""

    def __init__(self):
        self.enabled = os.getenv("CHAPTERS_ENABLED", "true").lower() == "true"

    def embed_id3_chapters(self, mp3_path: str, chapters: list) -> bool:
        """
        Write ID3 CHAP and CTOC frames into an existing MP3 file.

        Args:
            mp3_path: Absolute path to the MP3 file.
            chapters: List of chapter dicts with start_seconds (float) and title (str).

        Returns:
            True on success, False if chapters is empty or module disabled.
        """
        if not self.enabled:
            logger.info("Chapter embedding disabled (CHAPTERS_ENABLED=false)")
            return False
        if not chapters:
            logger.warning("No chapters to embed in %s", mp3_path)
            return False

        mp3_info = mutagen.mp3.MP3(mp3_path)
        total_ms = int(mp3_info.info.length * 1000)

        try:
            audio = mutagen.id3.ID3(mp3_path)
        except mutagen.id3.ID3NoHeaderError:
            audio = mutagen.id3.ID3()
            audio.save(mp3_path)
            audio = mutagen.id3.ID3(mp3_path)

        audio.delall("CHAP")
        audio.delall("CTOC")

        child_ids = [f"chp{i}" for i in range(len(chapters))]
        audio.add(
            mutagen.id3.CTOC(
                element_id="toc",
                flags=mutagen.id3.CTOCFlags.TOP_LEVEL | mutagen.id3.CTOCFlags.ORDERED,
                child_element_ids=child_ids,
                sub_frames=[],
            )
        )

        for i, ch in enumerate(chapters):
            start_ms = int(ch["start_seconds"] * 1000)
            if i + 1 < len(chapters):
                end_ms = int(chapters[i + 1]["start_seconds"] * 1000)
            else:
                end_ms = total_ms
            title = ch["title"][:45]
            audio.add(
                mutagen.id3.CHAP(
                    element_id=f"chp{i}",
                    start_time=start_ms,
                    end_time=end_ms,
                    sub_frames=[mutagen.id3.TIT2(text=title)],
                )
            )

        audio.save()
        logger.info("Embedded %d chapter(s) in %s", len(chapters), mp3_path)
        return True

    def generate_chapters_json(self, chapters: list, output_path: str):
        """
        Write a Podcasting 2.0 chapters JSON file.

        Args:
            chapters: List of chapter dicts with start_seconds and title.
            output_path: Absolute path to write the JSON file.

        Returns:
            output_path on success, None if chapters is empty.
        """
        if not chapters:
            logger.warning("No chapters to write to JSON")
            return None

        payload = {
            "version": "1.2.0",
            "chapters": [
                {"startTime": ch["start_seconds"], "title": ch["title"]}
                for ch in chapters
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("Chapters JSON written to %s", output_path)
        return output_path
