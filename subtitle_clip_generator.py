"""Subtitle clip generator for podcast clips.

Generates vertical 9:16 MP4 videos with Hormozi-style word-by-word burned-in
captions using pysubs2 ASS generation and FFmpeg. Active words are highlighted
with an accent color as they are spoken.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

import pysubs2

from client_config import resolve_client_logo_or_raise
from config import Config
from logger import logger
from subtitle_generator import SubtitleGenerator
from video_utils import get_h264_encoder_args


def normalize_word_timestamps(words: List[Dict]) -> List[Dict]:
    """Close gaps, resolve overlaps, interpolate unaligned words.

    Args:
        words: List of {'word': str, 'start': float, 'end': float}
               Some entries may have start=end=0 (unaligned words).

    Returns:
        Normalized list with no gap > 150ms between consecutive words,
        no overlapping timestamps, and interpolated times for unaligned words.
    """
    if not words:
        return words

    result = [w.copy() for w in words]

    # Pass 1: interpolate missing timestamps from neighbors
    for i, w in enumerate(result):
        if w.get("start", 0) == 0 and w.get("end", 0) == 0:
            prev_end = result[i - 1]["end"] if i > 0 else 0
            next_start = None
            for j in range(i + 1, len(result)):
                if result[j].get("start", 0) > 0:
                    next_start = result[j]["start"]
                    break
            if next_start is None:
                next_start = prev_end + 0.5
            w["start"] = prev_end
            w["end"] = (
                (prev_end + next_start) / 2 if prev_end < next_start else prev_end + 0.1
            )

    # Pass 2: close sub-150ms gaps by extending end time
    for i in range(len(result) - 1):
        gap = result[i + 1]["start"] - result[i]["end"]
        if 0 < gap < 0.15:
            result[i]["end"] = result[i + 1]["start"]

    # Pass 3: resolve overlaps
    for i in range(len(result) - 1):
        if result[i]["end"] > result[i + 1]["start"]:
            result[i]["end"] = result[i + 1]["start"] - 0.001

    return result


def _group_into_cards(words: List[Dict], max_words: int = 3) -> List[List[Dict]]:
    """Group normalized words into display cards of max_words each.

    Args:
        words: List of word dicts with 'word', 'start', 'end'
        max_words: Maximum words per card (default 3 for Hormozi-style)

    Returns:
        List of cards, each card being a list of word dicts
    """
    cards = []
    for i in range(0, len(words), max_words):
        cards.append(words[i : i + max_words])
    return cards


class SubtitleClipGenerator:
    """Generate vertical subtitle clip videos from audio files using pysubs2 + FFmpeg.

    Produces Hormozi-style word-by-word captions where the active word is
    highlighted with an accent color and surrounding words are white.
    """

    def __init__(self):
        self.enabled = os.getenv("USE_SUBTITLE_CLIPS", "true").lower() == "true"
        self.ffmpeg_path = Config.FFMPEG_PATH
        self.logo_path = resolve_client_logo_or_raise(
            Config.ASSETS_DIR / "podcast_logo.png", module="SubtitleClipGenerator"
        )
        self.font_size = int(os.getenv("SUBTITLE_FONT_SIZE", "72"))
        self.font_color = os.getenv("SUBTITLE_FONT_COLOR", "white")
        self.accent_color = os.getenv("SUBTITLE_ACCENT_COLOR", "0x00e0ff")
        self.bg_color = os.getenv("SUBTITLE_BG_COLOR", "0x1a1a2e")
        self.fonts_dir = str(Config.ASSETS_DIR / "fonts")

    @staticmethod
    def _escape_ffmpeg_filter_path(path: str) -> str:
        """Convert a path to FFmpeg filter-safe form.

        Handles Windows drive letter colons which conflict with FFmpeg's filter
        graph option separator syntax.

        C:\\Users\\foo\\file.ass  ->  C\\:/Users/foo/file.ass

        Args:
            path: File path to escape

        Returns:
            FFmpeg filter-safe path string
        """
        # Convert backslashes to forward slashes
        path = path.replace("\\", "/")
        # Escape the drive letter colon (Windows only)
        if len(path) >= 2 and path[1] == ":":
            path = path[0] + "\\:" + path[2:]
        return path

    @staticmethod
    @staticmethod
    def _parse_hex_color(rgb_hex: str) -> tuple:
        """Parse hex color string to (R, G, B) ints for pysubs2.Color."""
        hex_val = rgb_hex.lstrip("0x").lstrip("#").zfill(6)
        return int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)

    @staticmethod
    def _to_bgr_hex(rgb_hex: str) -> str:
        """Convert RGB hex color to BGR hex string for ASS color tags.

        ASS format uses &HBBGGRR& (BGR order, no alpha for primary color tag).

        Args:
            rgb_hex: Color in '0xRRGGBB' or '#RRGGBB' format

        Returns:
            6-character BGR hex string (e.g., 'ffe000' for cyan 0x00e0ff)
        """
        # Strip prefix
        hex_val = rgb_hex.lstrip("0x").lstrip("#")
        # Ensure 6 characters
        hex_val = hex_val.zfill(6)
        r = hex_val[0:2]
        g = hex_val[2:4]
        b = hex_val[4:6]
        return f"{b}{g}{r}"

    def _generate_ass_file(
        self,
        clip_words: List[Dict],
        output_path: str,
        width: int,
        height: int,
        video_source: bool = False,
        hook_text: str = None,
    ) -> str:
        """Generate an ASS subtitle file with per-word accent color highlights.

        Groups words into cards of up to 3. For each word in a card, creates one
        SSAEvent showing the full card with that word highlighted in accent color
        and surrounding words in white.

        Args:
            clip_words: List of clip-relative word dicts with 'word', 'start', 'end'
            output_path: Path to write the ASS file
            width: Video width in pixels
            height: Video height in pixels
            video_source: If True, position subtitles higher for blurred-background
                layout where video occupies the upper portion of the canvas.
            hook_text: Optional hook text to display in the first 2 seconds as a
                scroll-stopping overlay (e.g., "Why can't lobsters die?").

        Returns:
            The output_path string
        """
        subs = pysubs2.SSAFile()
        subs.info["PlayResX"] = str(width)
        subs.info["PlayResY"] = str(height)

        # For video-source clips with stacked split layout, subtitles go in
        # the bottom section below the two speaker panels
        margin_v = 100 if video_source else 80

        # Define base style — large bold white, black outline
        style = pysubs2.SSAStyle(
            fontname="Anton",
            fontsize=self.font_size,
            bold=True,
            primarycolor=pysubs2.Color(255, 255, 255, 0),  # white, fully opaque
            outlinecolor=pysubs2.Color(0, 0, 0, 0),  # black outline
            backcolor=pysubs2.Color(0, 0, 0, 128),  # semi-transparent shadow
            outline=3,
            shadow=1,
            alignment=pysubs2.Alignment.BOTTOM_CENTER,
            marginv=margin_v,
        )
        subs.styles["Default"] = style

        # Hook text style — centered, larger, accent color, appears first 2 seconds
        if hook_text:
            hook_style = pysubs2.SSAStyle(
                fontname="Anton",
                fontsize=int(self.font_size * 1.2),
                bold=True,
                primarycolor=pysubs2.Color(
                    *self._parse_hex_color(self.accent_color), 0
                ),
                outlinecolor=pysubs2.Color(0, 0, 0, 0),
                backcolor=pysubs2.Color(0, 0, 0, 160),
                outline=4,
                shadow=2,
                # Hook sits in the top band so it never lands on the centered
                # client logo (which clip backgrounds place in the middle of
                # the canvas via aspect-fit). 150px from the top gives enough
                # clearance from the top edge while staying well above logo.
                alignment=pysubs2.Alignment.TOP_CENTER,
                marginv=150,
            )
            subs.styles["Hook"] = hook_style
            hook_event = pysubs2.SSAEvent(
                start=0,
                end=2000,  # 2 seconds
                text=hook_text.upper(),
                style="Hook",
            )
            subs.events.append(hook_event)

        accent_bgr = self._to_bgr_hex(self.accent_color)

        # Group words into cards of max 3
        cards = _group_into_cards(clip_words, max_words=3)

        for card in cards:
            for active_idx, active_word in enumerate(card):
                word_start_ms = int(active_word["start"] * 1000)
                word_end_ms = int(active_word["end"] * 1000)

                # Build line text with ASS inline color override for active word
                parts = []
                for j, w in enumerate(card):
                    text = w["word"].upper()
                    # Escape literal braces — ASS uses { } for inline override tags
                    text = text.replace("{", r"\{").replace("}", r"\}")
                    if j == active_idx:
                        # Scale up + accent color for active word, then reset
                        parts.append(
                            f"{{\\fscx120\\fscy120\\c&H{accent_bgr}&}}{text}"
                            f"{{\\fscx100\\fscy100\\c&HFFFFFF&}}"
                        )
                    else:
                        parts.append(text)

                line_text = " ".join(parts)
                event = pysubs2.SSAEvent(
                    start=word_start_ms,
                    end=word_end_ms,
                    text=line_text,
                )
                subs.events.append(event)

        subs.save(output_path)
        return output_path

    def _build_ffmpeg_command(
        self,
        audio_path: str,
        ass_path: str,
        output_path: str,
        width: int,
        height: int,
    ) -> list:
        """Build the FFmpeg command list for subtitle clip generation.

        Creates a vertical canvas (branded background + optional logo) with ASS
        subtitle burn-in. Audio is copied without re-encoding.

        Args:
            audio_path: Path to the source audio file
            ass_path: Path to the ASS subtitle file
            output_path: Path for the output MP4 file
            width: Output video width in pixels
            height: Output video height in pixels

        Returns:
            List of command arguments for subprocess.run
        """
        escaped_ass = self._escape_ffmpeg_filter_path(ass_path)
        fonts_dir_escaped = self._escape_ffmpeg_filter_path(self.fonts_dir)
        use_logo = Path(self.logo_path).exists()

        if use_logo:
            vf = (
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color},"
                f"setsar=1,fps=25[bg];"
                f"[bg]subtitles='{escaped_ass}':fontsdir='{fonts_dir_escaped}'[final]"
            )
            input_args = ["-loop", "1", "-i", str(self.logo_path)]
        else:
            vf = (
                f"color=c={self.bg_color}:s={width}x{height}:r=25[bg];"
                f"[bg]subtitles='{escaped_ass}':fontsdir='{fonts_dir_escaped}'[final]"
            )
            input_args = [
                "-f",
                "lavfi",
                "-i",
                f"color=c={self.bg_color}:s={width}x{height}:r=25",
            ]

        encoder_args = get_h264_encoder_args(preset="medium", crf=18, profile="high")
        return [
            self.ffmpeg_path,
            "-y",
            *input_args,
            "-i",
            str(audio_path),
            "-filter_complex",
            vf,
            "-map",
            "[final]",
            "-map",
            "1:a",
            *encoder_args,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    def create_subtitle_clip(
        self,
        audio_path: str,
        srt_path: Optional[str],
        transcript_data: dict,
        clip_info: dict,
        output_path: Optional[str] = None,
        format_type: str = "vertical",
    ) -> Optional[str]:
        """Create a single subtitle clip MP4 from an audio clip.

        Uses word-level timestamps from transcript_data (not the SRT file) to
        generate per-word ASS captions. The srt_path parameter is accepted for
        interface compatibility but not used for word timing.

        Args:
            audio_path: Path to the source audio clip file
            srt_path: Ignored — word timing comes from transcript_data
            transcript_data: Full transcript dict with 'words' list
            clip_info: Dict with 'start_seconds' and 'end_seconds' for the clip
            output_path: Optional output path; derived from audio_path if None
            format_type: Output format — "vertical" (720x1280)

        Returns:
            Output file path on success, or None on failure
        """
        audio_path_obj = Path(audio_path)

        if not audio_path_obj.exists():
            logger.error("Audio file not found: %s", audio_path)
            return None

        # Resolve dimensions
        width, height = 720, 1280  # vertical 9:16

        # Derive output path if not provided
        if output_path is None:
            stem = audio_path_obj.stem
            output_path = str(audio_path_obj.parent / f"{stem}_subtitle.mp4")

        # Extract word-level timing from transcript data
        sub_gen = SubtitleGenerator()
        clip_words = sub_gen.extract_words_for_clip(
            transcript_data=transcript_data,
            clip_start=clip_info.get("start_seconds", 0.0),
            clip_end=clip_info.get("end_seconds", 0.0),
        )

        clip_words = normalize_word_timestamps(clip_words)

        # Generate ASS subtitle file alongside the audio clip
        hook_text = clip_info.get("hook_caption")
        ass_path = str(audio_path_obj.parent / f"{audio_path_obj.stem}_captions.ass")
        self._generate_ass_file(
            clip_words, ass_path, width, height, hook_text=hook_text
        )

        # Build and run FFmpeg
        cmd = self._build_ffmpeg_command(
            audio_path, ass_path, output_path, width, height
        )

        logger.info(
            "Creating subtitle clip: %s -> %s",
            audio_path_obj.name,
            Path(output_path).name,
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=300,
            )

            if "substituting font" in result.stderr.lower():
                logger.warning(
                    "libass substituted a fallback font — check assets/fonts/ and fontsdir setting"
                )

            if result.returncode != 0:
                logger.error("FFmpeg subtitle clip failed (exit %d)", result.returncode)
                logger.error("FFmpeg stderr: %s", result.stderr)
                return None

            logger.info("Subtitle clip created: %s", output_path)
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg subtitle clip timed out after 300 seconds")
            return None
        except Exception as e:
            logger.error("Subtitle clip generation error: %s", e)
            return None

    def create_subtitle_clips(
        self,
        clip_paths: List[str],
        srt_paths: List[Optional[str]],
        transcript_data: dict,
        best_clips: List[dict],
        format_type: str = "vertical",
    ) -> List[str]:
        """Batch process multiple audio clips into subtitle clip MP4s.

        Args:
            clip_paths: List of audio file paths to process
            srt_paths: List of SRT file paths (accepted for compatibility, not used)
            transcript_data: Full transcript with 'words' list
            best_clips: List of clip info dicts with 'start_seconds'/'end_seconds'
            format_type: Output format for all clips

        Returns:
            List of successfully created output file paths (None results excluded)
        """
        from concurrent.futures import ThreadPoolExecutor

        def _process_clip(idx):
            srt_path = srt_paths[idx] if srt_paths and idx < len(srt_paths) else None
            clip_info = best_clips[idx] if best_clips and idx < len(best_clips) else {}
            output = self.create_subtitle_clip(
                audio_path=clip_paths[idx],
                srt_path=srt_path,
                transcript_data=transcript_data,
                clip_info=clip_info,
                format_type=format_type,
            )
            logger.info(
                "Subtitle clip %d/%d %s",
                idx + 1,
                len(clip_paths),
                "succeeded" if output else "failed",
            )
            return output

        with ThreadPoolExecutor(max_workers=Config.MAX_NVENC_SESSIONS) as executor:
            futures = [
                executor.submit(_process_clip, i) for i in range(len(clip_paths))
            ]
            results = [r for r in (f.result() for f in futures) if r is not None]

        logger.info(
            f"Subtitle clip batch complete: {len(results)}/{len(clip_paths)} succeeded"
        )

        return results
