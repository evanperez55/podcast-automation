"""Configuration management for podcast automation."""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Central configuration for podcast automation."""

    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    # Dropbox
    DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
    DROPBOX_FOLDER_PATH = os.getenv('DROPBOX_FOLDER_PATH', '/Fake Problems Podcast/new_raw_files')
    DROPBOX_FINISHED_FOLDER = os.getenv('DROPBOX_FINISHED_FOLDER', '/Fake Problems Podcast/finished_files')
    DROPBOX_EDITED_FOLDER = os.getenv('DROPBOX_EDITED_FOLDER', '/Fake Problems Podcast/edited_files')

    # YouTube
    YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID')
    YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET')

    # Spotify
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_SHOW_ID = os.getenv('SPOTIFY_SHOW_ID')

    # Twitter
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')

    # Instagram
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID')

    # TikTok
    TIKTOK_CLIENT_KEY = os.getenv('TIKTOK_CLIENT_KEY')
    TIKTOK_CLIENT_SECRET = os.getenv('TIKTOK_CLIENT_SECRET')
    TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN')

    # Podcast Settings
    PODCAST_NAME = os.getenv('PODCAST_NAME', 'Fake Problems Podcast')
    BEEP_SOUND_PATH = os.getenv('BEEP_SOUND_PATH', './assets/beep.wav')

    # FFmpeg path (for Windows compatibility)
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'C:\\ffmpeg\\bin\\ffmpeg.exe')
    FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'C:\\ffmpeg\\bin\\ffprobe.exe')

    # Content Filtering Rules
    NAMES_TO_REMOVE = ['Joey', 'Evan', 'Dom']
    SLURS_TO_REMOVE = [
        # Racial slurs (list common ones - Claude will help identify more)
        'n-word', 'n****r', 'n***a',
        # Homophobic slurs
        'f****t', 'f*g', 'd*ke',
        # Add more as needed
    ]

    # Clip Settings
    CLIP_MIN_DURATION = 15  # seconds
    CLIP_MAX_DURATION = 30  # seconds
    NUM_CLIPS = 3  # Number of clips to generate per episode

    # Working Directories
    BASE_DIR = Path(__file__).parent
    DOWNLOAD_DIR = BASE_DIR / 'downloads'
    OUTPUT_DIR = BASE_DIR / 'output'
    CLIPS_DIR = BASE_DIR / 'clips'
    ASSETS_DIR = BASE_DIR / 'assets'

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
            'OPENAI_API_KEY': cls.OPENAI_API_KEY,
            'ANTHROPIC_API_KEY': cls.ANTHROPIC_API_KEY,
        }

        missing = [key for key, value in required.items() if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True
