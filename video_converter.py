"""Video converter for creating social media videos from audio clips."""

import subprocess
from pathlib import Path
from typing import Optional, List
from config import Config


class VideoConverter:
    """Convert audio files to video with static image background."""

    def __init__(self, logo_path: Optional[str] = None):
        """
        Initialize video converter.

        Args:
            logo_path: Path to logo/artwork image (defaults to assets/podcast_logo.jpg)
        """
        self.logo_path = logo_path or str(Config.ASSETS_DIR / 'podcast_logo.jpg')

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
        format_type: str = 'horizontal',
        resolution: Optional[tuple] = None
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
            print(f"[ERROR] Audio file not found: {audio_path}")
            return None

        # Determine output path
        if not output_path:
            output_path = audio_path.with_suffix('.mp4')
        output_path = Path(output_path)

        # Determine resolution based on format type
        if resolution:
            width, height = resolution
        elif format_type == 'horizontal':
            width, height = 1920, 1080  # YouTube, Twitter
        elif format_type == 'vertical':
            width, height = 1080, 1920  # Reels, TikTok, Shorts
        elif format_type == 'square':
            width, height = 1080, 1080  # Instagram square
        else:
            width, height = 1920, 1080  # Default to horizontal

        print(f"[INFO] Converting audio to {format_type} video ({width}x{height})")
        print(f"[INFO] Input: {audio_path.name}")
        print(f"[INFO] Output: {output_path.name}")

        # FFmpeg command to create video from audio + static image
        command = [
            self.ffmpeg_path,
            '-loop', '1',  # Loop the image
            '-i', str(self.logo_path),  # Input image
            '-i', str(audio_path),  # Input audio
            '-c:v', 'libx264',  # Video codec
            '-tune', 'stillimage',  # Optimize for still image
            '-c:a', 'aac',  # Audio codec
            '-b:a', '192k',  # Audio bitrate
            '-pix_fmt', 'yuv420p',  # Pixel format (compatible with most players)
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',  # Scale and pad
            '-shortest',  # End when audio ends
            '-y',  # Overwrite output file
            str(output_path)
        ]

        try:
            # Run ffmpeg
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print(f"[OK] Video created: {output_path}")
                return str(output_path)
            else:
                print(f"[ERROR] FFmpeg failed:")
                print(result.stderr)
                return None

        except subprocess.TimeoutExpired:
            print("[ERROR] Video conversion timed out")
            return None
        except Exception as e:
            print(f"[ERROR] Video conversion failed: {e}")
            return None

    def convert_clips_to_videos(
        self,
        clip_paths: List[str],
        format_type: str = 'vertical',
        output_dir: Optional[str] = None
    ) -> List[str]:
        """
        Convert multiple audio clips to videos.

        Args:
            clip_paths: List of paths to audio clips
            format_type: 'horizontal', 'vertical', or 'square'
            output_dir: Directory for output videos (defaults to same as clips)

        Returns:
            List of paths to created video files
        """
        video_paths = []

        for clip_path in clip_paths:
            clip_path = Path(clip_path)

            # Determine output path
            if output_dir:
                output_path = Path(output_dir) / clip_path.with_suffix('.mp4').name
            else:
                output_path = clip_path.with_suffix('.mp4')

            # Convert to video
            video_path = self.audio_to_video(
                audio_path=str(clip_path),
                output_path=str(output_path),
                format_type=format_type
            )

            if video_path:
                video_paths.append(video_path)

        print(f"\n[OK] Created {len(video_paths)}/{len(clip_paths)} videos")
        return video_paths

    def create_episode_video(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        format_type: str = 'horizontal'
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
        print("\n[INFO] Creating full episode video...")
        print("[INFO] This may take a few minutes for long episodes...")

        return self.audio_to_video(
            audio_path=audio_path,
            output_path=output_path,
            format_type=format_type
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
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return float(result.stdout.strip())
        return None

    except Exception:
        return None
