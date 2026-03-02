"""Subtitle/caption generator for clip videos."""

from pathlib import Path
from typing import List, Dict, Optional
from logger import logger


class SubtitleGenerator:
    """Generate SRT subtitles for video clips from transcript data."""

    MAX_WORDS_PER_LINE = 5
    MAX_LINE_DURATION = 2.5  # seconds
    PUNCTUATION_BREAKS = {".", "!", "?", ",", ";", ":"}

    def extract_words_for_clip(
        self, transcript_data: dict, clip_start: float, clip_end: float
    ) -> List[Dict]:
        """
        Extract words from transcript within clip time range,
        offset to clip-relative timestamps.

        Args:
            transcript_data: Full transcript with 'words' list
            clip_start: Clip start time in seconds (absolute)
            clip_end: Clip end time in seconds (absolute)

        Returns:
            List of word dicts with clip-relative 'start' and 'end'
        """
        words = transcript_data.get("words", [])
        clip_words = []

        for w in words:
            w_start = w.get("start", 0)
            w_end = w.get("end", w_start + 0.1)

            if w_start >= clip_start and w_end <= clip_end + 0.5:
                clip_words.append(
                    {
                        "word": w.get("word", "").strip(),
                        "start": round(w_start - clip_start, 3),
                        "end": round(w_end - clip_start, 3),
                    }
                )

        return clip_words

    def group_words_into_lines(self, words: List[Dict]) -> List[Dict]:
        """
        Group words into subtitle lines.

        Rules:
        - Max 5 words per line
        - Max 2.5s per line
        - Break at punctuation

        Args:
            words: List of word dicts with 'word', 'start', 'end'

        Returns:
            List of line dicts with 'text', 'start', 'end'
        """
        if not words:
            return []

        lines = []
        current_words = []
        line_start = None

        for w in words:
            if not w.get("word"):
                continue

            if line_start is None:
                line_start = w["start"]

            current_words.append(w["word"])
            line_end = w["end"]
            duration = line_end - line_start

            # Check if we should break
            should_break = False
            if len(current_words) >= self.MAX_WORDS_PER_LINE:
                should_break = True
            elif duration >= self.MAX_LINE_DURATION:
                should_break = True
            elif w["word"] and w["word"][-1] in self.PUNCTUATION_BREAKS:
                should_break = True

            if should_break and current_words:
                lines.append(
                    {
                        "text": " ".join(current_words),
                        "start": line_start,
                        "end": line_end,
                    }
                )
                current_words = []
                line_start = None

        # Flush remaining words
        if current_words:
            lines.append(
                {
                    "text": " ".join(current_words),
                    "start": line_start,
                    "end": words[-1]["end"],
                }
            )

        return lines

    def generate_srt(self, lines: List[Dict]) -> str:
        """
        Generate SRT format string from subtitle lines.

        Args:
            lines: List of line dicts with 'text', 'start', 'end'

        Returns:
            SRT formatted string
        """
        srt_parts = []
        for i, line in enumerate(lines, 1):
            start_ts = self._seconds_to_srt_time(line["start"])
            end_ts = self._seconds_to_srt_time(line["end"])
            srt_parts.append(f"{i}\n{start_ts} --> {end_ts}\n{line['text']}\n")

        return "\n".join(srt_parts)

    def generate_clip_srt(
        self,
        transcript_data: dict,
        clip_start: float,
        clip_end: float,
        output_path: str,
    ) -> Optional[str]:
        """
        End-to-end: generate SRT file for a clip.

        Args:
            transcript_data: Full transcript data
            clip_start: Clip start time (absolute seconds)
            clip_end: Clip end time (absolute seconds)
            output_path: Path to write SRT file

        Returns:
            Path to SRT file, or None if no words found
        """
        words = self.extract_words_for_clip(transcript_data, clip_start, clip_end)
        if not words:
            logger.warning("No words found for clip %.1f-%.1f", clip_start, clip_end)
            return None

        lines = self.group_words_into_lines(words)
        srt_content = self.generate_srt(lines)

        output_path = Path(output_path)
        output_path.write_text(srt_content, encoding="utf-8")
        logger.debug("SRT generated: %s (%d lines)", output_path.name, len(lines))
        return str(output_path)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format HH:MM:SS,mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
