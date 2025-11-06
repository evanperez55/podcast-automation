"""Test script for video converter."""

from video_converter import VideoConverter
from pathlib import Path

print("=" * 60)
print("TESTING VIDEO CONVERTER")
print("=" * 60)
print()

try:
    # Initialize converter
    print("[1/3] Initializing video converter...")
    converter = VideoConverter()
    print("[OK] Video converter initialized")
    print(f"[OK] Using logo: {converter.logo_path}")
    print()

    # Find a test clip
    clips_dir = Path("clips/ep_25_raw_20251104_225120")
    if clips_dir.exists():
        clips = list(clips_dir.glob("*.wav"))
        if clips:
            test_clip = clips[0]
            print(f"[2/3] Converting test clip to video...")
            print(f"[INFO] Test clip: {test_clip.name}")
            print()

            # Create vertical video (for Reels/TikTok/Shorts)
            print("[INFO] Creating vertical video (9:16 for Shorts/Reels)...")
            vertical_video = converter.audio_to_video(
                audio_path=str(test_clip),
                output_path=str(test_clip.with_suffix('.mp4')),
                format_type='vertical'
            )

            if vertical_video:
                print()
                print("[3/3] Video created successfully!")
                print(f"[OK] Video file: {vertical_video}")
                print()
                print("=" * 60)
                print("SUCCESS! Video converter is working!")
                print("=" * 60)
                print()
                print("The video has:")
                print("  - Your podcast logo as static background")
                print("  - The audio clip")
                print("  - 1080x1920 resolution (vertical for Reels/Shorts)")
                print()
                print(f"Check it out: {vertical_video}")
                print()
            else:
                print("[ERROR] Video creation failed")
        else:
            print("[ERROR] No clips found in directory")
    else:
        print(f"[ERROR] Clips directory not found: {clips_dir}")
        print("[INFO] Run 'python main.py ep25' first to generate clips")

except FileNotFoundError as e:
    print("[ERROR]:")
    print(f"  {e}")

except Exception as e:
    print("[ERROR]:")
    print(f"  {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
