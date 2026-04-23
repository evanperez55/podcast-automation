"""Video utility functions for FFmpeg-based video operations.

Provides video probing, audio extraction, clip cutting, and audio muxing
for video podcast input support.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from config import Config
from logger import logger


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}

# NVENC preset mapping: libx264 preset name -> NVENC p-level
_NVENC_PRESET_MAP = {"ultrafast": "p1", "fast": "p2", "medium": "p4", "slow": "p6"}

# Cache probe results — avoids redundant ffprobe calls when cutting N clips from same video
_probe_cache: dict = {}


_BT709_COLOR_FLAGS = [
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-colorspace",
    "bt709",
    "-color_range",
    "tv",
]


def _libx264_args(preset="medium", crf=18, profile="high"):
    """Return libx264 software encoder args (fallback)."""
    args = [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        *_BT709_COLOR_FLAGS,
    ]
    if profile:
        args.extend(["-profile:v", profile])
    return args


def get_h264_encoder_args(preset="medium", crf=18, profile="high"):
    """Return FFmpeg encoder args, using NVENC if available.

    Falls back to libx264 if NVENC was detected at startup but fails at
    runtime (driver mismatch, session limit, etc.).  The fallback is
    sticky for the process lifetime to avoid retrying on every clip.

    Args:
        preset: libx264-style preset name (ultrafast/fast/medium/slow).
        crf: Constant quality value (maps to -cq for NVENC).
        profile: H.264 profile (e.g., "high", "main").

    Returns:
        List of FFmpeg command-line arguments for the video encoder.
    """
    if Config.USE_NVENC:
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            _NVENC_PRESET_MAP.get(preset, "p4"),
            "-cq",
            str(crf),
            "-profile:v",
            profile,
            "-pix_fmt",
            "yuv420p",
            *_BT709_COLOR_FLAGS,
        ]
    else:
        return _libx264_args(preset, crf, profile)


def disable_nvenc_and_get_fallback_args(preset="medium", crf=18, profile="high"):
    """Disable NVENC for the rest of this process and return libx264 args.

    Called when an FFmpeg NVENC command fails at runtime (e.g., driver
    mismatch, session limit exceeded).  Sets Config.USE_NVENC = False so
    all subsequent calls to get_h264_encoder_args use libx264.

    Returns:
        List of libx264 FFmpeg command-line arguments.
    """
    Config.USE_NVENC = False
    logger.warning(
        "NVENC failed at runtime — falling back to libx264 for remaining encodes"
    )
    return _libx264_args(preset, crf, profile)


def is_video_file(file_path: Path) -> bool:
    """Check if a file path has a video extension."""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def probe_video(video_path: str) -> Optional[dict]:
    """Get video metadata using ffprobe.

    Results are cached per path to avoid redundant ffprobe subprocess calls
    when cutting multiple clips from the same source video.

    Args:
        video_path: Path to video file.

    Returns:
        Dict with width, height, duration, fps, codec, or None on failure.
    """
    cache_key = str(video_path)
    if cache_key in _probe_cache:
        return _probe_cache[cache_key]

    cmd = [
        Config.FFPROBE_PATH,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,codec_name:format=duration",
        "-of",
        "json",
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("ffprobe failed: %s", result.stderr.strip())
            return None

        data = json.loads(result.stdout)
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})

        # Parse frame rate (e.g., "30/1" or "30000/1001")
        fps_str = stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 0
        else:
            fps = float(fps_str)

        meta = {
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
            "fps": round(fps, 2),
            "codec": stream.get("codec_name", "unknown"),
            "duration": float(fmt.get("duration", 0)),
        }
        _probe_cache[cache_key] = meta
        return meta
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to probe video: %s", e)
        return None


def extract_audio(video_path: str, output_path: str) -> Optional[str]:
    """Extract audio track from a video file.

    Args:
        video_path: Path to source video.
        output_path: Path for extracted WAV audio.

    Returns:
        Output path on success, None on failure.
    """
    cmd = [
        Config.FFMPEG_PATH,
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-y",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.warning("Audio extraction failed: %s", result.stderr.strip()[:200])
            return None

        if not Path(output_path).exists():
            logger.warning("Audio extraction produced no output file")
            return None

        logger.info("Extracted audio: %s", output_path)
        return output_path
    except subprocess.TimeoutExpired:
        logger.warning("Audio extraction timed out (10 min limit)")
        return None
    except Exception as e:
        logger.warning("Audio extraction error: %s", e)
        return None


def cut_video_clip(
    video_path: str,
    start: float,
    end: float,
    output_path: str,
    crop_vertical: bool = False,
    ass_path: Optional[str] = None,
) -> Optional[str]:
    """Cut a segment from a video file, optionally reformatting to 9:16 vertical.

    For horizontal source video (16:9), uses a blurred-background layout:
    the original video is scaled and overlaid on a blurred, zoomed copy that
    fills the 720x1280 canvas. This preserves all visual content while
    eliminating dead black space.

    For already-vertical or square source video, center-crops to 9:16.

    When ass_path is provided, subtitles are burned in the same FFmpeg pass
    to ensure correct positioning on the composited canvas.

    Args:
        video_path: Path to source video.
        start: Start time in seconds.
        end: End time in seconds.
        output_path: Path for output clip.
        crop_vertical: If True, reformat to 9:16 aspect ratio.
        ass_path: Optional path to ASS subtitle file to burn in.

    Returns:
        Output path on success, None on failure.
    """
    duration = end - start
    if duration <= 0:
        logger.warning("Invalid clip duration: start=%s, end=%s", start, end)
        return None

    cmd = [
        Config.FFMPEG_PATH,
        "-ss",
        str(start),
        "-i",
        str(video_path),
        "-t",
        str(duration),
    ]

    if crop_vertical:
        # Detect source aspect ratio to choose strategy
        meta = probe_video(video_path)
        src_w = meta["width"] if meta else 1280
        src_h = meta["height"] if meta else 720

        # Check if client config requests split layout (side-by-side speakers)
        video_layout = getattr(Config, "VIDEO_LAYOUT", "auto")

        if src_w > src_h and video_layout == "split":
            # Stacked split layout for side-by-side speaker videos (e.g., Zoom)
            # 1. Remove black letterbox bars via fillborders detection
            # 2. Split into left/right halves
            # 3. Scale each to 720 wide (no speaker crop)
            # 4. Stack vertically, pad to 720x1280 for subtitles
            fc = (
                "[0:v]scale=720:1280,gblur=sigma=50,setsar=1[bg];"
                "[0:v]crop=iw:in_h*0.5:0:(in_h*0.25),"
                "split=2[left_src][right_src];"
                "[left_src]crop=iw/2:ih:0:0,"
                "scale=720:600,setsar=1[left];"
                "[right_src]crop=iw/2:ih:iw/2:0,"
                "scale=720:600,setsar=1[right];"
                "[left][right]vstack=inputs=2,setsar=1[fg];"
                "[bg][fg]overlay=0:0"
            )
            if ass_path:
                from subtitle_clip_generator import SubtitleClipGenerator

                escaped_ass = SubtitleClipGenerator._escape_ffmpeg_filter_path(ass_path)
                fonts_dir = str(Path(Config.ASSETS_DIR) / "fonts")
                escaped_fonts = SubtitleClipGenerator._escape_ffmpeg_filter_path(
                    fonts_dir
                )
                fc += (
                    f"[composed];"
                    f"[composed]subtitles='{escaped_ass}':"
                    f"fontsdir='{escaped_fonts}'"
                )
            cmd.extend(["-filter_complex", fc, "-map", "0:a"])
        elif src_w > src_h:
            # Blurred background layout for any horizontal source
            # Full video scaled to fit width, overlaid on blurred+zoomed copy
            # that fills the 720x1280 canvas. Keeps all content visible.
            fc = (
                "[0:v]scale=720:-2[fg];"
                "[0:v]scale=720:1280,gblur=sigma=40[bg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
            if ass_path:
                from subtitle_clip_generator import SubtitleClipGenerator

                escaped_ass = SubtitleClipGenerator._escape_ffmpeg_filter_path(ass_path)
                fonts_dir = str(Path(Config.ASSETS_DIR) / "fonts")
                escaped_fonts = SubtitleClipGenerator._escape_ffmpeg_filter_path(
                    fonts_dir
                )
                fc += (
                    f"[composed];"
                    f"[composed]subtitles='{escaped_ass}':"
                    f"fontsdir='{escaped_fonts}'"
                )
            cmd.extend(["-filter_complex", fc, "-map", "0:a"])
        else:
            # Vertical or square source: center-crop to 9:16
            vf = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=720:1280"
            if ass_path:
                from subtitle_clip_generator import SubtitleClipGenerator

                escaped_ass = SubtitleClipGenerator._escape_ffmpeg_filter_path(ass_path)
                fonts_dir = str(Path(Config.ASSETS_DIR) / "fonts")
                escaped_fonts = SubtitleClipGenerator._escape_ffmpeg_filter_path(
                    fonts_dir
                )
                vf += f",subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'"
            cmd.extend(["-vf", vf])
    elif ass_path:
        from subtitle_clip_generator import SubtitleClipGenerator

        escaped_ass = SubtitleClipGenerator._escape_ffmpeg_filter_path(ass_path)
        fonts_dir = str(Path(Config.ASSETS_DIR) / "fonts")
        escaped_fonts = SubtitleClipGenerator._escape_ffmpeg_filter_path(fonts_dir)
        cmd.extend(["-vf", f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'"])

    encoder_args = get_h264_encoder_args(preset="fast", crf=23, profile="high")
    cmd.extend(
        [
            *encoder_args,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ]
    )

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            stderr = result.stderr.strip()[:300]
            # NVENC runtime failure — retry with libx264 fallback
            if Config.USE_NVENC and (
                "nvenc" in stderr.lower()
                or "nvcuda" in stderr.lower()
                or "session" in stderr.lower()
            ):
                fallback_args = disable_nvenc_and_get_fallback_args(
                    preset="fast", crf=23, profile="high"
                )
                # Rebuild command with libx264
                nvenc_idx = next(
                    (i for i, a in enumerate(cmd) if a in ("h264_nvenc", "-cq")),
                    None,
                )
                if nvenc_idx is not None:
                    # Replace encoder section: find -c:v and replace through -pix_fmt
                    cv_idx = cmd.index("-c:v")
                    pf_idx = cmd.index("yuv420p")
                    cmd[cv_idx : pf_idx + 1] = fallback_args
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=300
                    )
                    if result.returncode != 0:
                        logger.warning(
                            "Video clip cut failed (libx264 fallback): %s",
                            result.stderr.strip()[:200],
                        )
                        return None
                else:
                    logger.warning("Video clip cut failed: %s", stderr)
                    return None
            else:
                logger.warning("Video clip cut failed: %s", stderr)
                return None

        if not Path(output_path).exists():
            logger.warning("Video clip cut produced no output file")
            return None

        logger.info("Cut video clip: %.1f-%.1fs -> %s", start, end, output_path)
        return output_path
    except subprocess.TimeoutExpired:
        logger.warning("Video clip cut timed out (5 min limit)")
        return None
    except Exception as e:
        logger.warning("Video clip cut error: %s", e)
        return None


def mux_audio_to_video(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> Optional[str]:
    """Replace a video's audio track with a different audio file.

    Used to mux censored audio back onto the original video for the
    full episode upload.

    Args:
        video_path: Path to source video (video track used).
        audio_path: Path to replacement audio (e.g., censored WAV/MP3).
        output_path: Path for output video.

    Returns:
        Output path on success, None on failure.
    """
    cmd = [
        Config.FFMPEG_PATH,
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        "-y",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.warning("Audio mux failed: %s", result.stderr.strip()[:200])
            return None

        if not Path(output_path).exists():
            logger.warning("Audio mux produced no output file")
            return None

        logger.info("Muxed censored audio to video: %s", output_path)
        return output_path
    except subprocess.TimeoutExpired:
        logger.warning("Audio mux timed out (10 min limit)")
        return None
    except Exception as e:
        logger.warning("Audio mux error: %s", e)
        return None


def burn_subtitles_on_video(
    video_path: str,
    ass_path: str,
    output_path: str,
) -> Optional[str]:
    """Burn ASS subtitles onto a video clip.

    Args:
        video_path: Path to source video clip.
        ass_path: Path to ASS subtitle file.
        output_path: Path for output video with burned-in subtitles.

    Returns:
        Output path on success, None on failure.
    """
    from subtitle_clip_generator import SubtitleClipGenerator

    escaped_ass = SubtitleClipGenerator._escape_ffmpeg_filter_path(ass_path)
    fonts_dir = str(Path(Config.ASSETS_DIR) / "fonts")
    escaped_fonts = SubtitleClipGenerator._escape_ffmpeg_filter_path(fonts_dir)

    vf = f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'"

    encoder_args = get_h264_encoder_args(preset="medium", crf=18, profile="high")
    cmd = [
        Config.FFMPEG_PATH,
        "-i",
        str(video_path),
        "-vf",
        vf,
        *encoder_args,
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        "-y",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("Subtitle burn failed: %s", result.stderr.strip()[:200])
            return None

        if not Path(output_path).exists():
            logger.warning("Subtitle burn produced no output file")
            return None

        logger.info("Burned subtitles onto video: %s", output_path)
        return output_path
    except subprocess.TimeoutExpired:
        logger.warning("Subtitle burn timed out (5 min limit)")
        return None
    except Exception as e:
        logger.warning("Subtitle burn error: %s", e)
        return None
