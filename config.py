"""Configuration management for podcast automation."""

import os
import shutil
import subprocess
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()


def _detect_ffmpeg():
    """Auto-detect FFmpeg from PATH, fall back to env var or default."""
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    found = shutil.which("ffmpeg")
    if found:
        return found
    return "C:\\ffmpeg\\bin\\ffmpeg.exe"


def _detect_ffprobe():
    """Auto-detect FFprobe from PATH, fall back to env var or default."""
    env_path = os.getenv("FFPROBE_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    found = shutil.which("ffprobe")
    if found:
        return found
    return "C:\\ffmpeg\\bin\\ffprobe.exe"


_nvenc_cache = None


def _detect_nvenc(ffmpeg_path: str) -> bool:
    """Check if h264_nvenc encoder is available in FFmpeg.

    Args:
        ffmpeg_path: Path to the FFmpeg binary.

    Returns:
        True if h264_nvenc is listed in FFmpeg encoders, False otherwise.
    """
    global _nvenc_cache
    if _nvenc_cache is not None:
        return _nvenc_cache

    try:
        result = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        _nvenc_cache = "h264_nvenc" in result.stdout
    except Exception:
        _nvenc_cache = False

    return _nvenc_cache


class Config:
    """Central configuration for podcast automation."""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Episode source (dropbox | rss | local)
    EPISODE_SOURCE = os.getenv("EPISODE_SOURCE", "dropbox")
    RSS_FEED_URL = os.getenv("RSS_FEED_URL", None)
    RSS_EPISODE_INDEX = int(os.getenv("RSS_EPISODE_INDEX", "0"))

    # Video source — YouTube channel URL for downloading episode video
    # When set, ingest downloads video from YouTube for stacked speaker clips
    VIDEO_SOURCE_YOUTUBE_CHANNEL = os.getenv("VIDEO_SOURCE_YOUTUBE_CHANNEL", None)

    # Video layout for vertical clip generation (auto | split | blurred)
    # split: stacked left/right halves (for side-by-side speaker videos like Zoom)
    # blurred: full video on blurred background (default, works for any video)
    # auto: same as blurred
    VIDEO_LAYOUT = os.getenv("VIDEO_LAYOUT", "auto")

    # Dropbox - Short-lived access token (deprecated)
    DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

    # Dropbox - OAuth credentials (recommended for auto-refresh)
    DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
    DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
    DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

    # Dropbox paths
    DROPBOX_FOLDER_PATH = os.getenv(
        "DROPBOX_FOLDER_PATH", "/Fake Problems Podcast/new_raw_files"
    )
    DROPBOX_FINISHED_FOLDER = os.getenv(
        "DROPBOX_FINISHED_FOLDER", "/Fake Problems Podcast/finished_files"
    )
    DROPBOX_EDITED_FOLDER = os.getenv(
        "DROPBOX_EDITED_FOLDER", "/Fake Problems Podcast/edited_files"
    )

    # YouTube
    YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")

    # Spotify (RSS-only, no API credentials needed)

    # Twitter (pay-per-use credits ~$0.01/tweet)
    TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "true").lower() == "true"
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

    # Bluesky
    BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
    BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")

    # Reddit
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
    REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "PodcastAutomation/1.0")
    REDDIT_SUBREDDITS = [
        s.strip() for s in os.getenv("REDDIT_SUBREDDITS", "").split(",") if s.strip()
    ]

    # Instagram
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

    # TikTok
    TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
    TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
    TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")

    # Google Docs Topic Tracker
    GOOGLE_DOC_ID = os.getenv("GOOGLE_DOC_ID")

    # Discord Notifications
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

    # Scheduling (delay in hours before uploading to each platform, 0 = immediate)
    SCHEDULE_YOUTUBE_DELAY_HOURS = int(os.getenv("SCHEDULE_YOUTUBE_DELAY_HOURS", "0"))
    SCHEDULE_TWITTER_DELAY_HOURS = int(os.getenv("SCHEDULE_TWITTER_DELAY_HOURS", "0"))
    SCHEDULE_INSTAGRAM_DELAY_HOURS = int(
        os.getenv("SCHEDULE_INSTAGRAM_DELAY_HOURS", "0")
    )
    SCHEDULE_TIKTOK_DELAY_HOURS = int(os.getenv("SCHEDULE_TIKTOK_DELAY_HOURS", "0"))

    # Smart scheduling — research-based posting hour defaults (24h, local time)
    SCHEDULE_YOUTUBE_POSTING_HOUR = int(
        os.getenv("SCHEDULE_YOUTUBE_POSTING_HOUR", "14")
    )
    SCHEDULE_TWITTER_POSTING_HOUR = int(
        os.getenv("SCHEDULE_TWITTER_POSTING_HOUR", "10")
    )
    SCHEDULE_INSTAGRAM_POSTING_HOUR = int(
        os.getenv("SCHEDULE_INSTAGRAM_POSTING_HOUR", "12")
    )
    SCHEDULE_TIKTOK_POSTING_HOUR = int(os.getenv("SCHEDULE_TIKTOK_POSTING_HOUR", "12"))

    # Content Calendar
    CONTENT_CALENDAR_ENABLED = os.getenv("CONTENT_CALENDAR_ENABLED", "true") == "true"
    TOPIC_DATA_DIR = Path("topic_data")

    # Blog Post Generator
    BLOG_ENABLED = os.getenv("BLOG_ENABLED", "true").lower() == "true"
    BLOG_USE_OPENAI = os.getenv("BLOG_USE_OPENAI", "true").lower() == "true"

    # Website Landing Page Generator
    WEBSITE_ENABLED = os.getenv("WEBSITE_ENABLED", "true").lower() == "true"
    WEBSITE_GITHUB_REPO = os.getenv(
        "WEBSITE_GITHUB_REPO", "fakeproblemspodcast/fakeproblemspodcast.github.io"
    )
    WEBSITE_GITHUB_BRANCH = os.getenv("WEBSITE_GITHUB_BRANCH", "main")
    WEBSITE_URL = os.getenv("WEBSITE_URL", "fakeproblemspodcast.com")

    # Episode Webpage Generator (GitHub Pages per-episode pages)
    PAGES_ENABLED = os.getenv("PAGES_ENABLED", "true").lower() == "true"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_PAGES_REPO = os.getenv("GITHUB_PAGES_REPO", "")
    GITHUB_PAGES_BRANCH = os.getenv("GITHUB_PAGES_BRANCH", "main")
    SITE_BASE_URL = os.getenv("SITE_BASE_URL", "")

    # Chapter Generator
    CHAPTERS_ENABLED = os.getenv("CHAPTERS_ENABLED", "true").lower() == "true"

    # Content Compliance Checker
    COMPLIANCE_ENABLED = os.getenv("COMPLIANCE_ENABLED", "true").lower() == "true"

    # Compilation Generator
    COMPILATION_ENABLED = os.getenv("COMPILATION_ENABLED", "true").lower() == "true"

    # Subtitle Clip Generator
    USE_SUBTITLE_CLIPS = os.getenv("USE_SUBTITLE_CLIPS", "true").lower() == "true"
    SUBTITLE_FONT_SIZE = int(os.getenv("SUBTITLE_FONT_SIZE", "48"))
    SUBTITLE_FONT_COLOR = os.getenv("SUBTITLE_FONT_COLOR", "#FFFFFF")
    SUBTITLE_BG_COLOR = os.getenv("SUBTITLE_BG_COLOR", "#000000")
    SUBTITLE_ACCENT_COLOR = os.getenv("SUBTITLE_ACCENT_COLOR", "#e94560")

    # YouTube Analytics
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@fakeproblemspodcast")

    # Daily Content Generator (OpenAI mode)
    DAILY_CONTENT_USE_OPENAI = (
        os.getenv("DAILY_CONTENT_USE_OPENAI", "true").lower() == "true"
    )

    # Thumbnail Generation
    THUMBNAIL_FONT = os.getenv("THUMBNAIL_FONT")
    THUMBNAIL_BG_COLOR = os.getenv("THUMBNAIL_BG_COLOR", "#1a1a2e")
    THUMBNAIL_TEXT_COLOR = os.getenv("THUMBNAIL_TEXT_COLOR", "#ffffff")
    THUMBNAIL_BADGE_COLOR = os.getenv("THUMBNAIL_BADGE_COLOR", "#e94560")

    # Quote Card Generation
    QUOTE_CARD_ENABLED = os.getenv("QUOTE_CARD_ENABLED", "true").lower() == "true"
    QUOTE_CARD_BG_COLOR = os.getenv("QUOTE_CARD_BG_COLOR", "#1a1a2e")
    QUOTE_CARD_TEXT_COLOR = os.getenv("QUOTE_CARD_TEXT_COLOR", "#ffffff")
    QUOTE_CARD_ACCENT_COLOR = os.getenv("QUOTE_CARD_ACCENT_COLOR", "#e94560")

    # Analytics Feedback Loop
    ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

    # Daily Content Generator
    DAILY_CONTENT_ENABLED = os.getenv("DAILY_CONTENT_ENABLED", "true").lower() == "true"

    # Audiogram Waveforms
    USE_AUDIOGRAM = os.getenv("USE_AUDIOGRAM", "true").lower() == "true"
    AUDIOGRAM_BG_COLOR = os.getenv("AUDIOGRAM_BG_COLOR", "0x1a1a2e")
    AUDIOGRAM_WAVE_COLOR = os.getenv("AUDIOGRAM_WAVE_COLOR", "0xe94560")

    # HuggingFace (for pyannote speaker diarization)
    HF_TOKEN = os.getenv("HF_TOKEN")

    # Podcast Settings
    PODCAST_NAME = os.getenv("PODCAST_NAME", "Fake Problems Podcast")
    BEEP_SOUND_PATH = os.getenv("BEEP_SOUND_PATH", "./assets/beep.wav")

    # FFmpeg path (auto-detected from PATH, env, or default)
    FFMPEG_PATH = _detect_ffmpeg()
    FFPROBE_PATH = _detect_ffprobe()

    # NVENC hardware encoding (auto-detect GPU, override with NVENC_ENABLED env var)
    _nvenc_env = os.getenv("NVENC_ENABLED")
    if _nvenc_env is not None:
        USE_NVENC = _nvenc_env.lower() == "true"
    else:
        USE_NVENC = _detect_nvenc(FFMPEG_PATH)

    # Content Filtering Rules
    # First names and full names of hosts to censor
    NAMES_TO_REMOVE = [
        # Default host names — override per client in clients/*.yaml
        "Host1",
        "Host2",
        "Host3",
    ]

    # Words to censor - use ACTUAL spellings so they match the transcript
    # These are searched directly in the Whisper transcript (case-insensitive)
    WORDS_TO_CENSOR = [
        # Homophobic slurs
        "fag",
        "fags",
        "faggot",
        "faggots",
        "dyke",
        "dykes",
        # Racial slurs
        "nigga",
        "niggas",
        "nigger",
        "niggers",
        "chink",
        "chinks",
        "spic",
        "spics",
        "wetback",
        "wetbacks",
        "kike",
        "kikes",
        "gook",
        "gooks",
        # Ableist slurs
        "retard",
        "retards",
        "retarded",
    ]

    # Audio Settings
    MP3_BITRATE = os.getenv("MP3_BITRATE", "192k")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "distil-large-v3")
    CLIP_FADE_MS = int(os.getenv("CLIP_FADE_MS", "100"))
    LUFS_TARGET = float(os.getenv("LUFS_TARGET", "-16"))

    # Noise Reduction (RNNoise via FFmpeg arnndn — removes constant hiss/hum)
    DENOISE_ENABLED = os.getenv("DENOISE_ENABLED", "true").lower() == "true"
    DENOISE_MODEL_PATH = os.getenv(
        "DENOISE_MODEL_PATH",
        str(Path(__file__).parent / "assets" / "rnnoise" / "sh.rnnn"),
    )

    # Clip Settings
    CLIP_MIN_DURATION = 15  # seconds
    CLIP_MAX_DURATION = int(os.getenv("CLIP_MAX_DURATION", "60"))  # seconds
    CLIP_TARGET_DURATION = int(
        os.getenv("CLIP_TARGET_DURATION", "30")
    )  # ideal clip length for YouTube Shorts (15-30s sweet spot)
    NUM_CLIPS = int(
        os.getenv("NUM_CLIPS", "8")
    )  # clips per episode (volume > perfection for discovery)
    CLIP_AUDIO_TOP_N = int(
        os.getenv("CLIP_AUDIO_TOP_N", "10")
    )  # Top-N high-energy segments to pass to GPT-4o

    # Video Resolution Settings
    HORIZONTAL_RESOLUTION = (1280, 720)
    VERTICAL_RESOLUTION = (720, 1280)
    SQUARE_RESOLUTION = (720, 720)

    # Ollama Settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    # OpenAI Model Settings
    OPENAI_ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4.1-mini")
    OPENAI_BLOG_MODEL = os.getenv("OPENAI_BLOG_MODEL", "gpt-4.1-mini")
    # Compliance uses mini by default: gpt-4o tier-1 TPM (30k) is too tight
    # for full-episode transcripts (~30k+ tokens per request).
    OPENAI_COMPLIANCE_MODEL = os.getenv("OPENAI_COMPLIANCE_MODEL", "gpt-4o-mini")

    # NVENC Parallel Encoding Sessions (default 3, newer drivers support 5)
    MAX_NVENC_SESSIONS = int(os.getenv("MAX_NVENC_SESSIONS", "3"))

    # Working Directories
    BASE_DIR = Path(__file__).parent
    DOWNLOAD_DIR = BASE_DIR / "downloads"
    OUTPUT_DIR = BASE_DIR / "output"
    CLIPS_DIR = BASE_DIR / "clips"
    ASSETS_DIR = BASE_DIR / "assets"
    CLIENT_LOGO_PATH = None  # Set by client config; None = use default logo

    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.DOWNLOAD_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.CLIPS_DIR.mkdir(exist_ok=True)
        cls.ASSETS_DIR.mkdir(exist_ok=True)

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        required = {
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True
