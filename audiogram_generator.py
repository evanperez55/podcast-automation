"""Audiogram waveform video generator for podcast clips.

Generates MP4 videos with waveform visualization from audio files,
optionally with burned-in subtitles. Supports vertical, horizontal,
and square output formats for multi-platform distribution.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from config import Config
from logger import logger


class AudiogramGenerator:
    """Generate audiogram waveform videos from audio files using FFmpeg."""

    def __init__(self):
        self.enabled = os.getenv("USE_AUDIOGRAM", "true").lower() == "true"
        self.bg_color = os.getenv("AUDIOGRAM_BG_COLOR", "0x1a1a2e")
        self.wave_color = os.getenv("AUDIOGRAM_WAVE_COLOR", "0xe94560")
        self.ffmpeg_path = Config.FFMPEG_PATH
        self.logo_path = Config.ASSETS_DIR / "podcast_logo.png"

    def create_audiogram(
        self,
        audio_path: str,
        format_type: str = "vertical",
        srt_path: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Create an audiogram video with waveform visualization from an audio file.

        Args:
            audio_path: Path to the source audio file.
            format_type: Output format - "vertical" (720x1280), "horizontal" (1280x720),
                         or "square" (720x720).
            srt_path: Optional path to an SRT subtitle file to burn in.
            output_path: Optional output file path. If None, derived from audio_path
                         with "_audiogram.mp4" suffix.

        Returns:
            The output file path on success, or None on failure.
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        # Resolve dimensions from format type
        resolution_map = {
            "vertical": Config.VERTICAL_RESOLUTION,
            "horizontal": Config.HORIZONTAL_RESOLUTION,
            "square": Config.SQUARE_RESOLUTION,
        }

        if format_type not in resolution_map:
            logger.error(
                f"Invalid format_type '{format_type}'. "
                f"Must be one of: {', '.join(resolution_map.keys())}"
            )
            return None

        width, height = resolution_map[format_type]

        # Derive output path if not provided
        if output_path is None:
            output_path = str(audio_path.parent / f"{audio_path.stem}_audiogram.mp4")

        output_path = str(output_path)

        logger.info(
            f"Creating {format_type} audiogram ({width}x{height}) "
            f"from {audio_path.name}"
        )

        # Build and run FFmpeg command
        cmd = self._build_ffmpeg_command(
            audio_path, output_path, width, height, srt_path=srt_path
        )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"FFmpeg audiogram failed (exit {result.returncode})")
                logger.error(f"FFmpeg stderr: {result.stderr}")
                return None

            logger.info(f"Audiogram created: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg audiogram timed out after 300 seconds")
            return None
        except Exception as e:
            logger.error(f"Audiogram generation error: {e}")
            return None

    def _build_ffmpeg_command(
        self,
        audio_path: str,
        output_path: str,
        width: int,
        height: int,
        srt_path: Optional[str] = None,
    ) -> list:
        """Build the FFmpeg command list for audiogram generation.

        Args:
            audio_path: Path to the source audio file.
            output_path: Path for the output video file.
            width: Output video width in pixels.
            height: Output video height in pixels.
            srt_path: Optional path to an SRT subtitle file.

        Returns:
            List of command arguments for subprocess.run.
        """
        wave_height = height // 3
        use_logo = self.logo_path.exists()

        # Build filter_complex chain
        # Input 0: logo image or lavfi color source
        # Input 1: audio file
        if use_logo:
            filters = [
                f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={self.bg_color},"
                f"setsar=1,fps=25[bg]",
                f"[1:a]showwaves=s={width}x{wave_height}:mode=cline:rate=25"
                f":colors={self.wave_color}[waves]",
                "[bg][waves]overlay=(W-w)/2:(H-h)/2[video]",
            ]
        else:
            filters = [
                f"[1:a]showwaves=s={width}x{wave_height}:mode=cline:rate=25"
                f":colors={self.wave_color}[waves]",
                "[0:v][waves]overlay=(W-w)/2:(H-h)/2[video]",
            ]

        if srt_path:
            # Escape backslashes and colons in the subtitle path for FFmpeg
            escaped_srt = str(srt_path).replace("\\", "/").replace(":", "\\:")
            filters.append(
                f"[video]subtitles='{escaped_srt}'"
                f":force_style='FontSize=24,PrimaryColour=&Hffffff&"
                f",Alignment=2,MarginV=40'[final]"
            )
            map_label = "[final]"
        else:
            map_label = "[video]"

        filter_complex_string = ";".join(filters)

        # Build input args: logo image or lavfi color as input 0
        if use_logo:
            input_args = [
                "-loop",
                "1",
                "-i",
                str(self.logo_path),
            ]
        else:
            input_args = [
                "-f",
                "lavfi",
                "-i",
                f"color=c={self.bg_color}:s={width}x{height}:r=25",
            ]

        cmd = [
            self.ffmpeg_path,
            "-y",
            *input_args,
            "-i",
            str(audio_path),
            "-filter_complex",
            filter_complex_string,
            "-map",
            map_label,
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        return cmd

    def create_audiogram_clips(
        self,
        clip_paths: List[str],
        format_type: str = "vertical",
        srt_paths: Optional[List[str]] = None,
    ) -> List[str]:
        """Batch process multiple audio clips into audiogram videos.

        Args:
            clip_paths: List of audio file paths to process.
            format_type: Output format for all clips.
            srt_paths: Optional list of SRT file paths, one per clip.
                       Must match the length of clip_paths if provided.

        Returns:
            List of successfully created output file paths.
        """
        results = []

        for i, clip_path in enumerate(clip_paths):
            srt_path = srt_paths[i] if srt_paths and i < len(srt_paths) else None

            output = self.create_audiogram(
                audio_path=clip_path,
                format_type=format_type,
                srt_path=srt_path,
            )

            if output is not None:
                results.append(output)

        logger.info(
            f"Audiogram batch complete: {len(results)}/{len(clip_paths)} succeeded"
        )

        return results
