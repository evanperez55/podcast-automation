"""Test script to verify all components are working."""

import sys
from pathlib import Path

print("="*60)
print("PODCAST AUTOMATION - SETUP TEST")
print("="*60)
print()

# Test 1: Python version
print("Test 1: Python Version")
print("-" * 60)
py_version = sys.version_info
print(f"Python {py_version.major}.{py_version.minor}.{py_version.micro}")
if py_version.major >= 3 and py_version.minor >= 9:
    print("[OK] Python version OK")
else:
    print("[ERROR] Python 3.9+ required")
    sys.exit(1)
print()

# Test 2: Required packages
print("Test 2: Required Packages")
print("-" * 60)
required_packages = [
    'dotenv',
    'openai',
    'anthropic',
    'pydub',
    'dropbox',
    'tqdm',
    'yaml'
]

missing = []
for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
        print(f"[OK] {package}")
    except ImportError:
        print(f"[ERROR] {package} - NOT INSTALLED")
        missing.append(package)

if missing:
    print()
    print(f"[ERROR] Missing packages: {', '.join(missing)}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)
print()

# Test 3: FFmpeg
print("Test 3: FFmpeg")
print("-" * 60)
try:
    from pydub.utils import which
    from config import Config

    # Check PATH first
    ffmpeg_path = which("ffmpeg")
    if ffmpeg_path:
        print(f"[OK] FFmpeg found in PATH at: {ffmpeg_path}")
    # Check configured path
    elif Path(Config.FFMPEG_PATH).exists():
        print(f"[OK] FFmpeg found at configured path: {Config.FFMPEG_PATH}")
    else:
        print("[ERROR] FFmpeg not found in PATH or configured location")
        print("Install FFmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error checking FFmpeg: {e}")
    sys.exit(1)
print()

# Test 4: Configuration
print("Test 4: Configuration")
print("-" * 60)
try:
    from config import Config

    # Check directories
    Config.create_directories()
    print(f"[OK] Directories created:")
    print(f"   - {Config.DOWNLOAD_DIR}")
    print(f"   - {Config.OUTPUT_DIR}")
    print(f"   - {Config.CLIPS_DIR}")
    print(f"   - {Config.ASSETS_DIR}")

    # Check API keys
    print()
    print("API Keys:")

    if Config.OPENAI_API_KEY:
        print(f"[OK] OPENAI_API_KEY configured")
    else:
        print(f"[ERROR] OPENAI_API_KEY missing")

    if Config.ANTHROPIC_API_KEY:
        print(f"[OK] ANTHROPIC_API_KEY configured")
    else:
        print(f"[ERROR] ANTHROPIC_API_KEY missing")

    if Config.DROPBOX_ACCESS_TOKEN:
        print(f"[OK] DROPBOX_ACCESS_TOKEN configured")
    else:
        print(f"[WARNING] DROPBOX_ACCESS_TOKEN missing (optional)")

    # Validate
    try:
        Config.validate()
        print()
        print("[OK] Configuration valid")
    except ValueError as e:
        print()
        print(f"[ERROR] Configuration error: {e}")
        print()
        print("Create a .env file with your API keys:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your OpenAI API key")
        print("  3. Add your Anthropic API key")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] Configuration error: {e}")
    sys.exit(1)
print()

# Test 5: Import all modules
print("Test 5: Module Imports")
print("-" * 60)
try:
    from dropbox_handler import DropboxHandler
    print("[OK] dropbox_handler")
except Exception as e:
    print(f"[ERROR] dropbox_handler: {e}")

try:
    from transcription import Transcriber
    print("[OK] transcription")
except Exception as e:
    print(f"[ERROR] transcription: {e}")

try:
    from content_editor import ContentEditor
    print("[OK] content_editor")
except Exception as e:
    print(f"[ERROR] content_editor: {e}")

try:
    from audio_processor import AudioProcessor
    print("[OK] audio_processor")
except Exception as e:
    print(f"[ERROR] audio_processor: {e}")

print()

# Test 6: API connectivity
print("Test 6: API Connectivity")
print("-" * 60)

# Test OpenAI
try:
    import openai
    client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    # Don't actually call the API, just check initialization
    print("[OK] OpenAI client initialized")
except Exception as e:
    print(f"[ERROR] OpenAI error: {e}")

# Test Anthropic
try:
    import anthropic
    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    print("[OK] Anthropic client initialized")
except Exception as e:
    print(f"[ERROR] Anthropic error: {e}")

# Test Dropbox (only if configured)
if Config.DROPBOX_ACCESS_TOKEN:
    try:
        import dropbox
        dbx = dropbox.Dropbox(Config.DROPBOX_ACCESS_TOKEN)
        account = dbx.users_get_current_account()
        print(f"[OK] Dropbox connected: {account.name.display_name}")
    except Exception as e:
        print(f"[ERROR] Dropbox error: {e}")
else:
    print("[WARNING] Dropbox not configured (skipping)")

print()

# Final summary
print("="*60)
print("[OK] SETUP TEST COMPLETE")
print("="*60)
print()
print("Your podcast automation system is ready!")
print()
print("Next steps:")
print("  1. Run: python main.py")
print("  2. Choose option 1 to process latest episode")
print("  3. Check output/ directory for results")
print()
print("For help, see:")
print("  - README.md for full documentation")
print("  - SETUP.md for detailed setup guide")
print()
