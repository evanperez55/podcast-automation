"""Test script to upload Episode 25 files to Dropbox."""

from dropbox_handler import DropboxHandler
from pathlib import Path

print("Testing Dropbox Upload Functionality")
print("=" * 60)
print()

# Initialize Dropbox handler
handler = DropboxHandler()

# Episode 25 files
mp3_file = Path("output/ep_25_raw_20251104_225120_censored.mp3")
clips_dir = Path("clips/ep_25_raw_20251104_225120")

# Test 1: Upload censored MP3
print("TEST 1: Uploading censored MP3 to finished_files...")
print("-" * 60)
if mp3_file.exists():
    result = handler.upload_finished_episode(
        mp3_file,
        episode_name="ep_25_censored.mp3"
    )
    if result:
        print(f"[SUCCESS] Uploaded to: {result}")
    else:
        print("[FAILED] Upload failed")
else:
    print(f"[ERROR] File not found: {mp3_file}")

print()

# Test 2: Upload clips
print("TEST 2: Uploading clips to Dropbox...")
print("-" * 60)
if clips_dir.exists():
    clip_files = list(clips_dir.glob("*.wav"))
    print(f"Found {len(clip_files)} clip files")

    results = handler.upload_clips(clip_files, episode_folder_name="ep_25")

    if results:
        print(f"[SUCCESS] Uploaded {len(results)} clips:")
        for path in results:
            print(f"   - {path}")
    else:
        print("[FAILED] Upload failed")
else:
    print(f"[ERROR] Clips directory not found: {clips_dir}")

print()
print("=" * 60)
print("Upload testing complete!")
