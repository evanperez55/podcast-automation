"""Video converter for creating social media videos from audio clips."""

import subprocess
from pathlib import Path
from typing import Optional, List
from config import Config
from logger import logger
from video_utils import get_h264_encoder_args


class VideoConverter:
    """Convert audio files to video with static image background."""

    def __init__(self, logo_path: Optional[str] = None):
        """
        Initialize video converter.

        Args:
            logo_path: Path to logo/artwork image (defaults to assets/podcast_logo.jpg)
        """
        if logo_path:
            self.logo_path = logo_path
        elif Config.CLIENT_LOGO_PATH and Path(Config.CLIENT_LOGO_PATH).exists():
            self.logo_path = str(Config.CLIENT_LOGO_PATH)
        else:
            self.logo_path = str(Config.ASSETS_DIR / "podcast_logo.jpg")

        # Verify logo exists
        if not Path(self.logo_path).exists():
            raise FileNotFoundError(
                f"Logo file not found: {self.logo_path}\n"
                f"Please add your podcast logo to: {Config.ASSETS_DIR}/podcast_logo.jpg"
            )

        # Verify ffmpeg is available
        self.ffmpeg_path = Config.FFMPEG_PATH

    def audio_to_video(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        format_type: str = "horizontal",
        resolution: Optional[tuple] = None,
    ) -> Optional[str]:
        """
        Convert audio file to video with static logo image.

        Args:
            audio_path: Path to audio file (WAV or MP3)
            output_path: Path for output video (defaults to same name with .mp4)
            format_type: 'horizontal' (16:9 for YouTube), 'vertical' (9:16 for Reels/TikTok), or 'square' (1:1)
            resolution: Custom resolution tuple (width, height), overrides format_type

        Returns:
            Path to created video file, or None if failed
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.error("Audio file not found: %s", audio_path)
            return None

        # Determine output path
        if not output_path:
            output_path = audio_path.with_suffix(".mp4")
        output_path = Path(output_path)

        # Determine resolution based on format type using Config values
        if resolution:
            width, height = resolution
        elif format_type == "horizontal":
            width, height = Config.HORIZONTAL_RESOLUTION
        elif format_type == "vertical":
            width, height = Config.VERTICAL_RESOLUTION
        elif format_type == "square":
            width, height = Config.SQUARE_RESOLUTION
        else:
            width, height = Config.HORIZONTAL_RESOLUTION

        logger.info("Converting audio to %s video (%dx%d)", format_type, width, height)
        logger.debug("Input: %s", audio_path.name)
        logger.debug("Output: %s", output_path.name)

        # FFmpeg command to create video from audio + static image
        encoder_args = get_h264_encoder_args(preset="medium", crf=18, profile="high")
        command = [
            self.ffmpeg_path,
            "-loop",
            "1",  # Loop the image
            "-i",
            str(self.logo_path),  # Input image
            "-i",
            str(audio_path),  # Input audio
            *encoder_args,
        ]
        # -tune stillimage only works with libx264, not NVENC
        if not Config.USE_NVENC:
            command.extend(["-tune", "stillimage"])
        command.extend(
            [
                "-c:a",
                "aac",  # Audio codec
                "-b:a",
                "192k",  # Audio bitrate
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",  # Scale and pad
                "-shortest",  # End when audio ends
                "-movflags",
                "+faststart",  # Moov atom at front — enables progressive playback
                "-y",  # Overwrite output file
                str(output_path),
            ]
        )

        try:
            # Run ffmpeg (longer timeout for full episodes)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=7200,  # 2 hour timeout for long episodes
            )

            if result.returncode == 0:
                logger.info("Video created: %s", output_path)
                return str(output_path)
            else:
                logger.error("FFmpeg failed: %s", result.stderr)
                return None

        except subprocess.TimeoutExpired:
            logger.error("Video conversion timed out")
            return None
        except Exception as e:
            logger.error("Video conversion failed: %s", e)
            return None

    def audio_to_video_with_subtitles(
        self,
        audio_path: str,
        srt_path: str,
        output_path: Optional[str] = None,
        format_type: str = "vertical",
        resolution: Optional[tuple] = None,
    ) -> Optional[str]:
        """
        Convert audio file to video with static logo and burned-in subtitles.

        Args:
            audio_path: Path to audio file
            srt_path: Path to SRT subtitle file
            output_path: Path for output video
            format_type: Video format type
            resolution: Custom resolution tuple

        Returns:
            Path to created video file, or None if failed
        """
        audio_path = Path(audio_path)
        srt_path = Path(srt_path)

        if not audio_path.exists():
            logger.error("Audio file not found: %s", audio_path)
            return None
        if not srt_path.exists():
            logger.warning(
                "SRT file not found: %s, falling back to no subtitles", srt_path
            )
            return self.audio_to_video(
                str(audio_path), output_path, format_type, resolution
            )

        if not output_path:
            output_path = audio_path.with_suffix(".mp4")
        output_path = Path(output_path)

        if resolution:
            width, height = resolution
        elif format_type == "horizontal":
            width, height = Config.HORIZONTAL_RESOLUTION
        elif format_type == "vertical":
            width, height = Config.VERTICAL_RESOLUTION
        elif format_type == "square":
            width, height = Config.SQUARE_RESOLUTION
        else:
            width, height = Config.HORIZONTAL_RESOLUTION

        logger.info(
            "Converting audio to %s video with subtitles (%dx%d)",
            format_type,
            width,
            height,
        )

        # Handle Windows path escaping for FFmpeg subtitle filter
        srt_str = str(srt_path).replace("\\", "/").replace(":", "\\:")

        # Build video filter with scale, pad, and subtitle burn-in
        subtitle_style = "FontSize=24,FontName=Arial,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2"
        vf_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"subtitles='{srt_str}':force_style='{subtitle_style}'"
        )

        encoder_args = get_h264_encoder_args(preset="medium", crf=18, profile="high")
        command = [
            self.ffmpeg_path,
            "-loop",
            "1",
            "-i",
            str(self.logo_path),
            "-i",
            str(audio_path),
            *encoder_args,
        ]
        # -tune stillimage only works with libx264, not NVENC
        if not Config.USE_NVENC:
            command.extend(["-tune", "stillimage"])
        command.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-vf",
                vf_filter,
                "-shortest",
                "-movflags",
                "+faststart",
                "-y",
                str(output_path),
            ]
        )

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=7200
            )

            if result.returncode == 0:
                logger.info("Video with subtitles created: %s", output_path)
                return str(output_path)
            else:
                logger.warning(
                    "Subtitle burn failed, falling back to no subtitles: %s",
                    result.stderr[:200],
                )
                return self.audio_to_video(
                    str(audio_path), str(output_path), format_type, resolution
                )

        except subprocess.TimeoutExpired:
            logger.error("Video conversion with subtitles timed out")
            return None
        except Exception as e:
            logger.warning("Subtitle video conversion failed, falling back: %s", e)
            return self.audio_to_video(
                str(audio_path), str(output_path), format_type, resolution
            )

    def convert_clips_to_videos(
        self,
        clip_paths: List[str],
        format_type: str = "vertical",
        output_dir: Optional[str] = None,
        srt_paths: Optional[List[Optional[str]]] = None,
    ) -> List[str]:
        """
        Convert multiple audio clips to videos in parallel.

        Args:
            clip_paths: List of paths to audio clips
            format_type: 'horizontal', 'vertical', or 'square'
            output_dir: Directory for output videos (defaults to same as clips)
            srt_paths: Optional list of SRT file paths (one per clip, None for no subtitles)

        Returns:
            List of paths to created video files (preserves input order)
        """
        from concurrent.futures import ThreadPoolExecutor

        def _convert_one(i, clip_path):
            clip_path = Path(clip_path)
            if output_dir:
                out = Path(output_dir) / clip_path.with_suffix(".mp4").name
            else:
                out = clip_path.with_suffix(".mp4")

            srt_path = None
            if srt_paths and i < len(srt_paths):
                srt_path = srt_paths[i]

            if srt_path:
                return self.audio_to_video_with_subtitles(
                    audio_path=str(clip_path),
                    srt_path=srt_path,
                    output_path=str(out),
                    format_type=format_type,
                )
            return self.audio_to_video(
                audio_path=str(clip_path),
                output_path=str(out),
                format_type=format_type,
            )

        max_workers = min(len(clip_paths), Config.MAX_NVENC_SESSIONS)
        video_paths = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_convert_one, i, cp) for i, cp in enumerate(clip_paths)
            ]
            for f in futures:
                result = f.result()
                if result:
                    video_paths.append(result)

        logger.info("Created %d/%d videos", len(video_paths), len(clip_paths))
        return video_paths

    def create_episode_video(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        format_type: str = "horizontal",
    ) -> Optional[str]:
        """
        Create a video for a full episode.

        Args:
            audio_path: Path to full episode audio
            output_path: Path for output video
            format_type: Video format (default 'horizontal' for YouTube)

        Returns:
            Path to created video file, or None if failed
        """
        logger.info("Creating full episode video...")
        logger.info("This may take a few minutes for long episodes...")

        return self.audio_to_video(
            audio_path=audio_path, output_path=output_path, format_type=format_type
        )


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Get duration of a video file in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds, or None if failed
    """
    try:
        command = [
            Config.FFPROBE_PATH,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        result = subprocess.run(command, capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            return float(result.stdout.strip())
        return None

    except Exception:
        return None
